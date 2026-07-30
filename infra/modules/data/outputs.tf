output "database_endpoint" { value = aws_db_instance.this.address }
output "database_name" { value = aws_db_instance.this.db_name }
output "database_master_secret_arn" { value = aws_db_instance.this.master_user_secret[0].secret_arn }
output "application_secret_arn" { value = aws_secretsmanager_secret.application.arn }
output "source_bucket_arn" { value = aws_s3_bucket.source_archive.arn }
output "source_bucket_name" { value = aws_s3_bucket.source_archive.id }
