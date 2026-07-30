output "cluster_name" { value = aws_ecs_cluster.this.name }
output "cluster_arn" { value = aws_ecs_cluster.this.arn }
output "api_service_name" { value = aws_ecs_service.api.name }
output "web_service_name" { value = aws_ecs_service.web.name }
output "worker_task_definition_arn" { value = aws_ecs_task_definition.worker.arn }
