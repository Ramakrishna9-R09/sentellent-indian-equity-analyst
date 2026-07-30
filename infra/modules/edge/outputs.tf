output "alb_dns_name" { value = aws_lb.this.dns_name }
output "alb_arn_suffix" { value = aws_lb.this.arn_suffix }
output "web_target_group_arn" { value = aws_lb_target_group.web.arn }
output "api_target_group_arn" { value = aws_lb_target_group.api.arn }
output "cloudfront_domain_name" { value = var.enable_cloudfront ? aws_cloudfront_distribution.this[0].domain_name : aws_lb.this.dns_name }
