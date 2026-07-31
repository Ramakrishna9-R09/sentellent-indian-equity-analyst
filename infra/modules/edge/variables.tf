variable "name" { type = string }
variable "tags" { type = map(string) }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "alb_security_group_id" { type = string }
variable "region" {
  type    = string
  default = "ap-south-1"
}

variable "enable_cloudfront" {
  type    = bool
  default = true
}

variable "domain_name" {
  type        = string
  default     = ""
  description = "Public domain served over HTTPS directly on the ALB (no CloudFront). Empty disables the HTTPS listener."
}

variable "manage_dns_in_route53" {
  type        = bool
  default     = false
  description = "Create a Route53 hosted zone plus ACM-validation and A/ALIAS records. Set false to paste records into the registrar's DNS panel manually."
}
