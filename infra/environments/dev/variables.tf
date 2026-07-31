variable "aws_region" {
  type        = string
  description = "AWS deployment region."
  default     = "ap-south-1"
}

variable "project_name" {
  type    = string
  default = "sentellent-equity-analyst"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "github_repository" {
  type        = string
  description = "GitHub owner/repository authorized to deploy from main."
}

variable "api_image" {
  type        = string
  description = "Immutable ECR API image URI passed by CI."
}

variable "web_image" {
  type        = string
  description = "Immutable ECR web image URI passed by CI."
}

variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "enable_multi_az" {
  type    = bool
  default = false
}

variable "deletion_protection" {
  type    = bool
  default = false
}

variable "db_backup_days" {
  type        = number
  description = "Number of days to retain automated RDS backups. 0 disables them."
  default     = 7
}

variable "enable_cloudfront" {
  type        = bool
  description = "Keep the public entry point HTTPS-capable for OAuth and secure cookies."
  default     = true
}

variable "domain_name" {
  type        = string
  description = "Public domain served over HTTPS directly on the ALB (no CloudFront). Empty disables the HTTPS listener."
  default     = ""
}

variable "manage_dns_in_route53" {
  type        = bool
  description = "Create a Route53 hosted zone plus ACM-validation and A/ALIAS records. Set false to paste records into the registrar's DNS panel manually."
  default     = false
}

variable "alarm_email" {
  type        = string
  description = "Email for CloudWatch alarm notifications. Leave empty to skip."
  default     = ""
}

variable "db_engine_version" {
  type        = string
  description = "PostgreSQL engine version for the RDS instance. Must match the deployed instance to avoid a destructive downgrade."
  default     = null
}
