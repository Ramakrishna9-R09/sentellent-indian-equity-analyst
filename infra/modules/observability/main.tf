# ---------------------------------------------------------------------------
# SNS topic for alarm notifications
# ---------------------------------------------------------------------------

resource "aws_sns_topic" "alarms" {
  name = format("%s-alarms", var.name)
  tags = var.tags
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alarm_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# ---------------------------------------------------------------------------
# CloudWatch Alarms
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "ecs_api_unhealthy" {
  alarm_name          = format("%s-api-unhealthy-tasks", var.name)
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 60
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "API service has no healthy running tasks."
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.api_service_name
  }
  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "ecs_web_unhealthy" {
  alarm_name          = format("%s-web-unhealthy-tasks", var.name)
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 60
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "Web service has no healthy running tasks."
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.web_service_name
  }
  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = format("%s-alb-5xx-rate", var.name)
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_ELB_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"
  alarm_description   = "ALB is returning more than 10 5xx errors in 5 minutes."
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }
  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "alb_target_response_time" {
  alarm_name          = format("%s-alb-latency", var.name)
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  extended_statistic  = "p95"
  threshold           = 5
  treat_missing_data  = "notBreaching"
  alarm_description   = "ALB p95 target response time exceeds 5 seconds."
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }
  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = format("%s-rds-cpu", var.name)
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization exceeds 80%."
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  dimensions = {
    DBInstanceIdentifier = var.rds_instance_identifier
  }
  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "rds_free_storage" {
  alarm_name          = format("%s-rds-low-storage", var.name)
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Minimum"
  threshold           = 2147483648 # 2 GB in bytes
  alarm_description   = "RDS free storage space is below 2 GB."
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  dimensions = {
    DBInstanceIdentifier = var.rds_instance_identifier
  }
  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = format("%s-rds-connections", var.name)
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = var.rds_max_connections_alarm
  alarm_description   = "RDS active connections exceed alarm threshold."
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  dimensions = {
    DBInstanceIdentifier = var.rds_instance_identifier
  }
  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "worker_invocation_failure" {
  alarm_name          = format("%s-worker-failures", var.name)
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FailedInvocations"
  namespace           = "AWS/Events"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_description   = "EventBridge worker schedule has failed invocations."
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  dimensions = {
    RuleName = var.event_rule_name
  }
  tags = var.tags
}

# ---------------------------------------------------------------------------
# CloudWatch Dashboard
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = format("%s-operations", var.name)
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 1
        properties = {
          markdown = "# Sentellent Equity Analyst — Operations Dashboard"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 1
        width  = 12
        height = 6
        properties = {
          title   = "ECS CPU Utilization"
          region  = var.region
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["ECS/ContainerInsights", "CpuUtilized", "ClusterName", var.ecs_cluster_name, "ServiceName", var.api_service_name, { label = "API" }],
            ["ECS/ContainerInsights", "CpuUtilized", "ClusterName", var.ecs_cluster_name, "ServiceName", var.web_service_name, { label = "Web" }]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 1
        width  = 12
        height = 6
        properties = {
          title   = "ECS Memory Utilization"
          region  = var.region
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["ECS/ContainerInsights", "MemoryUtilized", "ClusterName", var.ecs_cluster_name, "ServiceName", var.api_service_name, { label = "API" }],
            ["ECS/ContainerInsights", "MemoryUtilized", "ClusterName", var.ecs_cluster_name, "ServiceName", var.web_service_name, { label = "Web" }]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 7
        width  = 8
        height = 6
        properties = {
          title   = "ALB Request Count"
          region  = var.region
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", var.alb_arn_suffix, { stat = "Sum" }]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 7
        width  = 8
        height = 6
        properties = {
          title   = "ALB Latency (p50 / p95)"
          region  = var.region
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", var.alb_arn_suffix, { stat = "p50", label = "p50" }],
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", var.alb_arn_suffix, { stat = "p95", label = "p95" }]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 7
        width  = 8
        height = 6
        properties = {
          title   = "ALB HTTP Errors"
          region  = var.region
          view    = "timeSeries"
          stacked = true
          metrics = [
            ["AWS/ApplicationELB", "HTTPCode_ELB_4XX_Count", "LoadBalancer", var.alb_arn_suffix, { stat = "Sum", label = "4xx" }],
            ["AWS/ApplicationELB", "HTTPCode_ELB_5XX_Count", "LoadBalancer", var.alb_arn_suffix, { stat = "Sum", label = "5xx" }]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 13
        width  = 8
        height = 6
        properties = {
          title   = "RDS CPU Utilization"
          region  = var.region
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", var.rds_instance_identifier]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 13
        width  = 8
        height = 6
        properties = {
          title   = "RDS Connections"
          region  = var.region
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", var.rds_instance_identifier]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 13
        width  = 8
        height = 6
        properties = {
          title   = "RDS Free Storage (GB)"
          region  = var.region
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/RDS", "FreeStorageSpace", "DBInstanceIdentifier", var.rds_instance_identifier]
          ]
          period = 300
          yAxis = {
            left = { label = "Bytes" }
          }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 19
        width  = 12
        height = 6
        properties = {
          title   = "EventBridge Worker Invocations"
          region  = var.region
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/Events", "Invocations", "RuleName", var.event_rule_name, { stat = "Sum", label = "Invocations" }],
            ["AWS/Events", "FailedInvocations", "RuleName", var.event_rule_name, { stat = "Sum", label = "Failures" }]
          ]
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 19
        width  = 12
        height = 6
        properties = {
          title   = "RDS Read / Write IOPS"
          region  = var.region
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/RDS", "ReadIOPS", "DBInstanceIdentifier", var.rds_instance_identifier, { stat = "Average", label = "Read IOPS" }],
            ["AWS/RDS", "WriteIOPS", "DBInstanceIdentifier", var.rds_instance_identifier, { stat = "Average", label = "Write IOPS" }]
          ]
          period = 300
        }
      }
    ]
  })
}
