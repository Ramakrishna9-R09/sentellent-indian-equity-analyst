variable "name" { type = string }
variable "tags" { type = map(string) }
variable "cluster_arn" { type = string }
variable "worker_task_definition_arn" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "ecs_security_group_id" { type = string }
variable "task_execution_role_arn" { type = string }
variable "application_task_role_arn" { type = string }

variable "schedule_expression" {
  type    = string
  default = "rate(5 minutes)"
}
