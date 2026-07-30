resource "aws_s3_bucket" "source_archive" {
  bucket_prefix = format("%s-sources-", var.name)
  tags          = var.tags
}

resource "aws_s3_bucket_public_access_block" "source_archive" {
  bucket                  = aws_s3_bucket.source_archive.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "source_archive" {
  bucket = aws_s3_bucket.source_archive.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "source_archive" {
  bucket = aws_s3_bucket.source_archive.id
  rule {
    id     = "expire-raw-source-snapshots"
    status = "Enabled"
    filter {}
    expiration { days = var.source_retention_days }
  }
}

resource "aws_db_subnet_group" "this" {
  name       = format("%s-rds", var.name)
  subnet_ids = var.private_subnet_ids
  tags       = var.tags
}

resource "aws_db_instance" "this" {
  identifier                      = format("%s-rag", var.name)
  allocated_storage               = var.db_allocated_storage
  max_allocated_storage           = var.db_allocated_storage * 2
  storage_type                    = "gp3"
  engine                          = "postgres"
  engine_version                  = var.db_engine_version
  instance_class                  = var.db_instance_class
  db_name                         = "sentellent"
  username                        = "sentellent"
  port                            = 5432
  manage_master_user_password     = true
  backup_retention_period         = var.db_backup_days
  deletion_protection             = var.deletion_protection
  skip_final_snapshot             = !var.deletion_protection
  publicly_accessible             = false
  multi_az                        = var.multi_az
  storage_encrypted               = true
  db_subnet_group_name            = aws_db_subnet_group.this.name
  vpc_security_group_ids          = [var.rds_security_group_id]
  auto_minor_version_upgrade      = true
  copy_tags_to_snapshot           = true
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  tags                            = var.tags
}

resource "aws_secretsmanager_secret" "application" {
  name                    = format("%s/application", var.name)
  recovery_window_in_days = 0
  tags                    = var.tags
}
