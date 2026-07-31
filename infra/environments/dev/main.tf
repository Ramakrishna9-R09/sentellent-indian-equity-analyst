locals {
  name = format("%s-%s", var.project_name, var.environment)
  tags = {
    Application = "Sentellent Equity Analyst"
    Environment = var.environment
  }
}

module "network" {
  source   = "../../modules/network"
  name     = local.name
  vpc_cidr = var.vpc_cidr
  tags     = local.tags
}

module "registry" {
  source = "../../modules/registry"
  name   = local.name
  tags   = local.tags
}

module "data" {
  source                = "../../modules/data"
  name                  = local.name
  tags                  = local.tags
  private_subnet_ids    = module.network.private_subnet_ids
  rds_security_group_id = module.network.rds_security_group_id
  db_instance_class     = var.db_instance_class
  db_engine_version     = var.db_engine_version
  multi_az              = var.enable_multi_az
  deletion_protection   = var.deletion_protection
}

module "edge" {
  source                = "../../modules/edge"
  name                  = local.name
  tags                  = local.tags
  vpc_id                = module.network.vpc_id
  public_subnet_ids     = module.network.public_subnet_ids
  alb_security_group_id = module.network.alb_security_group_id
  enable_cloudfront     = var.enable_cloudfront
}

module "iam" {
  source                     = "../../modules/iam"
  name                       = local.name
  tags                       = local.tags
  github_repository          = var.github_repository
  source_bucket_arn          = module.data.source_bucket_arn
  database_master_secret_arn = module.data.database_master_secret_arn
  application_secret_arn     = module.data.application_secret_arn
}

module "ecs" {
  source                     = "../../modules/ecs"
  name                       = local.name
  environment                = var.environment
  region                     = var.aws_region
  tags                       = local.tags
  api_image                  = var.api_image
  web_image                  = var.web_image
  private_subnet_ids         = module.network.private_subnet_ids
  ecs_security_group_id      = module.network.ecs_security_group_id
  api_target_group_arn       = module.edge.api_target_group_arn
  web_target_group_arn       = module.edge.web_target_group_arn
  cloudfront_domain_name     = module.edge.cloudfront_domain_name
  enable_cloudfront          = var.enable_cloudfront
  database_endpoint          = module.data.database_endpoint
  database_name              = module.data.database_name
  database_master_secret_arn = module.data.database_master_secret_arn
  application_secret_arn     = module.data.application_secret_arn
  source_bucket_name         = module.data.source_bucket_name
  task_execution_role_arn    = module.iam.task_execution_role_arn
  application_task_role_arn  = module.iam.application_task_role_arn
}

module "scheduler" {
  source                     = "../../modules/scheduler"
  name                       = local.name
  tags                       = local.tags
  cluster_arn                = module.ecs.cluster_arn
  worker_task_definition_arn = module.ecs.worker_task_definition_arn
  private_subnet_ids         = module.network.private_subnet_ids
  ecs_security_group_id      = module.network.ecs_security_group_id
  task_execution_role_arn    = module.iam.task_execution_role_arn
  application_task_role_arn  = module.iam.application_task_role_arn
}

module "observability" {
  source                  = "../../modules/observability"
  name                    = local.name
  tags                    = local.tags
  region                  = var.aws_region
  alarm_email             = var.alarm_email
  ecs_cluster_name        = module.ecs.cluster_name
  api_service_name        = module.ecs.api_service_name
  web_service_name        = module.ecs.web_service_name
  alb_arn_suffix          = module.edge.alb_arn_suffix
  rds_instance_identifier = module.data.rds_instance_identifier
  event_rule_name         = module.scheduler.event_rule_name
}
