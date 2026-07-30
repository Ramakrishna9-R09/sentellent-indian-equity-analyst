variable "name" { type = string }
variable "tags" { type = map(string) }
variable "region" { type = string }

variable "alarm_email" {
  type        = string
  description = "Email address to receive CloudWatch alarm notifications."
  default     = ""
}

variable "ecs_cluster_name" { type = string }
variable "api_service_name" { type = string }
variable "web_service_name" { type = string }
variable "alb_arn_suffix" { type = string }
variable "rds_instance_identifier" { type = string }
variable "event_rule_name" { type = string }

variable "rds_max_connections_alarm" {
  type        = number
  description = "Alarm when active RDS connections exceed this threshold."
  default     = 40
}
