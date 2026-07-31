output "alb_dns_name" { value = aws_lb.this.dns_name }
output "alb_arn_suffix" { value = aws_lb.this.arn_suffix }
output "web_target_group_arn" { value = aws_lb_target_group.web.arn }
output "api_target_group_arn" { value = aws_lb_target_group.api.arn }
output "cloudfront_domain_name" { value = var.enable_cloudfront ? aws_cloudfront_distribution.this[0].domain_name : aws_lb.this.dns_name }

output "live_domain" {
  value = local.apex_domain != null ? local.apex_domain : (var.enable_cloudfront ? aws_cloudfront_distribution.this[0].domain_name : aws_lb.this.dns_name)
}

output "acm_certificate_arn" {
  value = local.enable_https ? aws_acm_certificate.this[0].arn : null
}

output "acm_validation_cnames" {
  value = local.enable_https ? [
    for option in aws_acm_certificate.this[0].domain_validation_options : {
      name  = option.resource_record_name
      type  = option.resource_record_type
      value = option.resource_record_value
    }
  ] : []
}

output "route53_name_servers" {
  value = local.manage_route53 ? aws_route53_zone.this[0].name_servers : []
}
