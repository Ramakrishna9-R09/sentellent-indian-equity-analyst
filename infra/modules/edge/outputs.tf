output "alb_dns_name" { value = aws_lb.this.dns_name }
output "web_target_group_arn" { value = aws_lb_target_group.web.arn }
output "api_target_group_arn" { value = aws_lb_target_group.api.arn }
output "cloudfront_domain_name" { value = aws_cloudfront_distribution.this.domain_name }
