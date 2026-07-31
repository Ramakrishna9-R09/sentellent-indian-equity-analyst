variable "name" { type = string }
variable "environment" { type = string }
variable "region" { type = string }
variable "tags" { type = map(string) }
variable "api_image" { type = string }
variable "web_image" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "ecs_security_group_id" { type = string }
variable "api_target_group_arn" { type = string }
variable "web_target_group_arn" { type = string }
variable "cloudfront_domain_name" { type = string }
variable "enable_cloudfront" {
  type    = bool
  default = true
}
variable "database_endpoint" { type = string }
variable "database_name" { type = string }
variable "database_master_secret_arn" { type = string }
variable "application_secret_arn" { type = string }
variable "source_bucket_name" { type = string }
variable "task_execution_role_arn" { type = string }
variable "application_task_role_arn" { type = string }
variable "api_desired_count" {
  type    = number
  default = 1
}

variable "web_desired_count" {
  type    = number
  default = 1
}
