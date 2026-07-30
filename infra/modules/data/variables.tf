variable "name" { type = string }
variable "tags" { type = map(string) }
variable "private_subnet_ids" { type = list(string) }
variable "rds_security_group_id" { type = string }
variable "db_engine_version" {
  type    = string
  default = null
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "db_backup_days" {
  type    = number
  default = 0
}

variable "multi_az" {
  type    = bool
  default = false
}

variable "deletion_protection" {
  type    = bool
  default = false
}

variable "source_retention_days" {
  type    = number
  default = 90
}
