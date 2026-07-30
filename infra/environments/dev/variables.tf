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

variable "enable_cloudfront" {
  type        = bool
  description = "Keep the public entry point HTTPS-capable for OAuth and secure cookies."
  default     = true

  validation {
    condition     = var.enable_cloudfront
    error_message = "The dev environment requires CloudFront. Disabling it leaves only an HTTP ALB while OAuth, secure cookies, and the smoke test require HTTPS."
  }
}

variable "alarm_email" {
  type        = string
  description = "Email for CloudWatch alarm notifications. Leave empty to skip."
  default     = ""
}
