variable "aws_region" {
  type        = string
  description = "AWS region used for the Terraform state resources."
  default     = "ap-south-1"
}

variable "state_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket name for Terraform state."
}

variable "lock_table_name" {
  type        = string
  description = "DynamoDB table name used for Terraform state locking."
  default     = "sentellent-terraform-locks"
}
