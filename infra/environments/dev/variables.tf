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
