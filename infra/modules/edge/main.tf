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
