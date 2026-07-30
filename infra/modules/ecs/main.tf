locals {
  common_environment = [
    { name = "ENVIRONMENT", value = var.environment },
    { name = "AWS_REGION", value = var.region },
    { name = "DATABASE_HOST", value = var.database_endpoint },
    { name = "DATABASE_PORT", value = "5432" },
    { name = "DATABASE_NAME", value = var.database_name },
    { name = "WEB_APP_URL", value = format("https://%s", var.cloudfront_domain_name) },
    { name = "GOOGLE_REDIRECT_URI", value = format("https://%s/api/auth/google/callback", var.cloudfront_domain_name) },
    { name = "SESSION_COOKIE_SECURE", value = "true" },
    { name = "DEV_BYPASS_AUTH", value = "false" },
    { name = "NEWS_LOOKBACK_DAYS", value = "14" },
    { name = "NEWS_FEED_URLS", value = "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms,https://www.moneycontrol.com/rss/MCtopnews.xml" },
    { name = "SOURCE_ARCHIVE_BUCKET", value = var.source_bucket_name }
  ]
  common_secrets = [
    { name = "DATABASE_USER", valueFrom = format("%s:username::", var.database_master_secret_arn) },
    { name = "DATABASE_PASSWORD", valueFrom = format("%s:password::", var.database_master_secret_arn) },
    { name = "GOOGLE_CLIENT_ID", valueFrom = format("%s:google_client_id::", var.application_secret_arn) },
    { name = "GOOGLE_CLIENT_SECRET", valueFrom = format("%s:google_client_secret::", var.application_secret_arn) },
    { name = "OPENAI_API_KEY", valueFrom = format("%s:openai_api_key::", var.application_secret_arn) }
  ]
}

resource "aws_ecs_cluster" "this" {
  name = format("%s-cluster", var.name)
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = var.tags
}

resource "aws_cloudwatch_log_group" "api" {
  name              = format("/ecs/%s/api", var.name)
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "web" {
  name              = format("/ecs/%s/web", var.name)
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = format("/ecs/%s/worker", var.name)
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_ecs_task_definition" "api" {
  family                   = format("%s-api", var.name)
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.application_task_role_arn
  container_definitions = jsonencode([{
    name         = "api"
    image        = var.api_image
    essential    = true
    portMappings = [{ containerPort = 8000, hostPort = 8000, protocol = "tcp" }]
    environment  = local.common_environment
    secrets      = local.common_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.api.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "api"
      }
    }
  }])
  tags = var.tags
}

resource "aws_ecs_task_definition" "web" {
  family                   = format("%s-web", var.name)
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.application_task_role_arn
  container_definitions = jsonencode([{
    name         = "web"
    image        = var.web_image
    essential    = true
    portMappings = [{ containerPort = 3000, hostPort = 3000, protocol = "tcp" }]
    environment  = [{ name = "NEXT_PUBLIC_API_BASE_URL", value = "/api" }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.web.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "web"
      }
    }
  }])
  tags = var.tags
}

resource "aws_ecs_task_definition" "worker" {
  family                   = format("%s-worker", var.name)
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.application_task_role_arn
  container_definitions = jsonencode([{
    name        = "worker"
    image       = var.api_image
    essential   = true
    command     = ["python", "-m", "app.worker", "--once"]
    environment = local.common_environment
    secrets     = local.common_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.worker.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "worker"
      }
    }
  }])
  tags = var.tags
}

resource "aws_ecs_service" "api" {
  name                               = format("%s-api", var.name)
  cluster                            = aws_ecs_cluster.this.id
  task_definition                    = aws_ecs_task_definition.api.arn
  desired_count                      = var.api_desired_count
  launch_type                        = "FARGATE"
  health_check_grace_period_seconds  = 60
  enable_execute_command             = true
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = var.api_target_group_arn
    container_name   = "api"
    container_port   = 8000
  }
  tags = var.tags
}

resource "aws_ecs_service" "web" {
  name                               = format("%s-web", var.name)
  cluster                            = aws_ecs_cluster.this.id
  task_definition                    = aws_ecs_task_definition.web.arn
  desired_count                      = var.web_desired_count
  launch_type                        = "FARGATE"
  health_check_grace_period_seconds  = 60
  enable_execute_command             = true
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = var.web_target_group_arn
    container_name   = "web"
    container_port   = 3000
  }
  tags = var.tags
}

data "aws_iam_policy_document" "events_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eventbridge_worker" {
  name               = format("%s-eventbridge-worker", var.name)
  assume_role_policy = data.aws_iam_policy_document.events_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "eventbridge_worker" {
  name = "run-ingestion-task"
  role = aws_iam_role.eventbridge_worker.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecs:RunTask"]
        Resource = [aws_ecs_task_definition.worker.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [var.task_execution_role_arn, var.application_task_role_arn]
      }
    ]
  })
}

resource "aws_cloudwatch_event_rule" "worker" {
  name                = format("%s-refresh-news", var.name)
  description         = "Run idempotent Sentellent ticker-refresh worker"
  schedule_expression = var.worker_schedule_expression
  tags                = var.tags
}

resource "aws_cloudwatch_event_target" "worker" {
  rule      = aws_cloudwatch_event_rule.worker.name
  target_id = "ingestion-worker"
  arn       = aws_ecs_cluster.this.arn
  role_arn  = aws_iam_role.eventbridge_worker.arn
  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.worker.arn
    launch_type         = "FARGATE"
    network_configuration {
      subnets          = var.private_subnet_ids
      security_groups  = [var.ecs_security_group_id]
      assign_public_ip = false
    }
  }
}
