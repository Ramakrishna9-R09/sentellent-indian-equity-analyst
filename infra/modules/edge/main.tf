locals {
  apex_domain    = var.domain_name == "" ? null : replace(var.domain_name, "/^www\\./", "")
  enable_https   = local.apex_domain != null
  manage_route53 = local.enable_https && var.manage_dns_in_route53
}

resource "aws_lb" "this" {
  name               = substr(replace(format("%s-alb", var.name), "_", "-"), 0, 32)
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.public_subnet_ids
  idle_timeout       = 60
  tags               = var.tags
}

resource "aws_lb_target_group" "web" {
  name        = substr(replace(format("%s-web", var.name), "_", "-"), 0, 32)
  port        = 3000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check {
    enabled             = true
    path                = "/"
    matcher             = "200-399"
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
  tags = var.tags
}

resource "aws_lb_target_group" "api" {
  name        = substr(replace(format("%s-api", var.name), "_", "-"), 0, 32)
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check {
    enabled             = true
    path                = "/health"
    matcher             = "200"
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
  tags = var.tags
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
  condition {
    path_pattern { values = ["/api/*", "/health", "/ready", "/docs", "/openapi.json"] }
  }
}

resource "aws_acm_certificate" "this" {
  count                     = local.enable_https ? 1 : 0
  domain_name               = local.apex_domain
  subject_alternative_names = ["www.${local.apex_domain}"]
  validation_method         = "DNS"
  lifecycle {
    create_before_destroy = true
  }
  tags = var.tags
}

resource "aws_route53_zone" "this" {
  count = local.manage_route53 ? 1 : 0
  name  = local.apex_domain
  tags  = var.tags
}

resource "aws_route53_record" "acm_validation" {
  count   = local.manage_route53 ? length(aws_acm_certificate.this[0].domain_validation_options) : 0
  zone_id = aws_route53_zone.this[0].zone_id
  name    = aws_acm_certificate.this[0].domain_validation_options[count.index].resource_record_name
  type    = aws_acm_certificate.this[0].domain_validation_options[count.index].resource_record_type
  records = [aws_acm_certificate.this[0].domain_validation_options[count.index].resource_record_value]
  ttl     = 60
}

resource "aws_route53_record" "app" {
  count   = local.manage_route53 ? 1 : 0
  zone_id = aws_route53_zone.this[0].zone_id
  name    = local.apex_domain
  type    = "A"
  alias {
    name                   = aws_lb.this.dns_name
    zone_id                = aws_lb.this.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "www" {
  count   = local.manage_route53 ? 1 : 0
  zone_id = aws_route53_zone.this[0].zone_id
  name    = "www.${local.apex_domain}"
  type    = "A"
  alias {
    name                   = aws_lb.this.dns_name
    zone_id                = aws_lb.this.zone_id
    evaluate_target_health = true
  }
}

resource "aws_acm_certificate_validation" "this" {
  count                   = local.enable_https ? 1 : 0
  certificate_arn         = aws_acm_certificate.this[0].arn
  validation_record_fqdns = local.manage_route53 ? aws_route53_record.acm_validation[*].fqdn : []
  timeouts {
    create = "60m"
  }
}

resource "aws_lb_listener" "https" {
  count             = local.enable_https ? 1 : 0
  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.this[0].arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
  depends_on = [aws_acm_certificate_validation.this[0]]
  tags       = var.tags
}

resource "aws_lb_listener_rule" "api_https" {
  count        = local.enable_https ? 1 : 0
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 10
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
  condition {
    path_pattern { values = ["/api/*", "/health", "/ready", "/docs", "/openapi.json"] }
  }
}

resource "aws_cloudfront_distribution" "this" {
  count           = var.enable_cloudfront ? 1 : 0
  enabled         = true
  is_ipv6_enabled = true
  comment         = format("%s public application", var.name)
  price_class     = "PriceClass_200"

  origin {
    domain_name = aws_lb.this.dns_name
    origin_id   = "sentellent-alb"
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "sentellent-alb"
    viewer_protocol_policy = "redirect-to-https"
    forwarded_values {
      query_string = true
      headers      = ["Origin", "Access-Control-Request-Headers", "Access-Control-Request-Method"]
      cookies { forward = "all" }
    }
  }

  ordered_cache_behavior {
    path_pattern           = "/api/*"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "sentellent-alb"
    viewer_protocol_policy = "redirect-to-https"
    forwarded_values {
      query_string = true
      headers = [
        "Authorization",
        "Content-Type",
        "Origin",
        "Access-Control-Request-Headers",
        "Access-Control-Request-Method",
      ]
      cookies { forward = "all" }
    }
    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  ordered_cache_behavior {
    path_pattern           = "/_next/static/*"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "sentellent-alb"
    viewer_protocol_policy = "redirect-to-https"
    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
    min_ttl     = 0
    default_ttl = 86400
    max_ttl     = 31536000
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate { cloudfront_default_certificate = true }
  tags = var.tags
}
