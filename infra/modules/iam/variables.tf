variable "name" { type = string }
variable "tags" { type = map(string) }
variable "github_repository" { type = string }
variable "source_bucket_arn" { type = string }
variable "database_master_secret_arn" { type = string }
variable "application_secret_arn" { type = string }
