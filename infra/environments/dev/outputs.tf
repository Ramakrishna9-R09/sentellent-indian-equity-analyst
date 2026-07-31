output "live_url" {
  value = var.domain_name != "" ? format("https://%s", replace(var.domain_name, "/^www\\./", "")) : format("%s://%s", var.enable_cloudfront ? "https" : "http", module.edge.cloudfront_domain_name)
}

output "live_domain" { value = module.edge.live_domain }
output "acm_certificate_arn" { value = module.edge.acm_certificate_arn }
output "acm_validation_cnames" { value = module.edge.acm_validation_cnames }
output "route53_name_servers" { value = module.edge.route53_name_servers }

output "ecr_api_repository" { value = module.registry.api_url }
output "ecr_web_repository" { value = module.registry.web_url }
output "github_deploy_role_arn" { value = module.iam.github_deploy_role_arn }
output "ecs_cluster_name" { value = module.ecs.cluster_name }
output "api_service_name" { value = module.ecs.api_service_name }
output "web_service_name" { value = module.ecs.web_service_name }
output "worker_task_definition_arn" { value = module.ecs.worker_task_definition_arn }
output "private_subnet_ids" { value = module.network.private_subnet_ids }
output "ecs_security_group_id" { value = module.network.ecs_security_group_id }
output "application_secret_arn" { value = module.data.application_secret_arn }
output "event_rule_name" { value = module.scheduler.event_rule_name }
output "dashboard_name" { value = module.observability.dashboard_name }
