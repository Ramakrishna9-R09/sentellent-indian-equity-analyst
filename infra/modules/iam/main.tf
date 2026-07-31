data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]
  tags            = var.tags
}

data "aws_iam_policy_document" "github_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = flatten(concat(
        [
          format("repo:%s:ref:refs/heads/main", var.github_repository),
          format("repo:%s:environment:*", var.github_repository),
        ],
        [for repo in [split("/", var.github_repository)] : [
          format("repo:%s@*/%s@*:ref:refs/heads/main", repo[0], repo[1]),
          format("repo:%s@*/%s@*:environment:*", repo[0], repo[1]),
        ]],
      ))
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name               = format("%s-github-deploy", var.name)
  assume_role_policy = data.aws_iam_policy_document.github_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "github_deploy" {
  name = "terraform-deploy-services"
  role = aws_iam_role.github_deploy.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "application-autoscaling:*",
        "cloudfront:*",
        "cloudwatch:*",
        "dynamodb:*",
        "ec2:*",
        "ecr:*",
        "ecs:*",
        "elasticloadbalancing:*",
        "events:*",
        "iam:*",
        "logs:*",
        "rds:*",
        "s3:*",
        "secretsmanager:*",
        "sns:*",
        "sts:GetCallerIdentity"
      ]
      Resource = "*"
    }]
  })
}

data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "task_execution" {
  name               = format("%s-task-execution", var.name)
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "task_execution_secrets" {
  name = "read-task-definition-secrets"
  role = aws_iam_role.task_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [var.database_master_secret_arn, var.application_secret_arn]
    }]
  })
}

resource "aws_iam_role" "application" {
  name               = format("%s-application", var.name)
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "application" {
  name = "application-data-access"
  role = aws_iam_role.application.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [var.source_bucket_arn, format("%s/*", var.source_bucket_arn)]
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [var.database_master_secret_arn, var.application_secret_arn]
      }
    ]
  })
}
