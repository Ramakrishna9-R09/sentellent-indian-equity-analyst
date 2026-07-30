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
        Resource = [var.worker_task_definition_arn]
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
  schedule_expression = var.schedule_expression
  tags                = var.tags
}

resource "aws_cloudwatch_event_target" "worker" {
  rule      = aws_cloudwatch_event_rule.worker.name
  target_id = "ingestion-worker"
  arn       = var.cluster_arn
  role_arn  = aws_iam_role.eventbridge_worker.arn
  ecs_target {
    task_count          = 1
    task_definition_arn = var.worker_task_definition_arn
    launch_type         = "FARGATE"
    network_configuration {
      subnets          = var.private_subnet_ids
      security_groups  = [var.ecs_security_group_id]
      assign_public_ip = false
    }
  }
}
