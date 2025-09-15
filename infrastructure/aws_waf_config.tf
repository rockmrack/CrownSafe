# =====================================================
# AWS WAF Configuration for BabyShield API
# =====================================================
# This Terraform configuration sets up AWS WAF with managed rules
# and custom rules for protecting the BabyShield API

# WAF Web ACL
resource "aws_wafv2_web_acl" "babyshield_waf" {
  name  = "babyshield-api-waf"
  scope = "REGIONAL"  # Use CLOUDFRONT for CloudFront distributions

  default_action {
    allow {}
  }

  # =====================================================
  # AWS Managed Rule Groups
  # =====================================================

  # Core Rule Set - OWASP Top 10 protection
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"

        # Exclude specific rules if they cause false positives
        excluded_rule {
          name = "SizeRestrictions_BODY"  # If you need large request bodies
        }

        excluded_rule {
          name = "GenericRFI_BODY"  # If causing issues with legitimate requests
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "AWSManagedRulesCommonRuleSetMetric"
      sampled_requests_enabled  = true
    }
  }

  # Known Bad Inputs Rule Set
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "AWSManagedRulesKnownBadInputsRuleSetMetric"
      sampled_requests_enabled  = true
    }
  }

  # SQL Injection Protection
  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "AWSManagedRulesSQLiRuleSetMetric"
      sampled_requests_enabled  = true
    }
  }

  # Linux-specific protection (if using Linux servers)
  rule {
    name     = "AWSManagedRulesLinuxRuleSet"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesLinuxRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "AWSManagedRulesLinuxRuleSetMetric"
      sampled_requests_enabled  = true
    }
  }

  # Anonymous IP blocking
  rule {
    name     = "AWSManagedRulesAnonymousIPList"
    priority = 5

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAnonymousIPList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "AWSManagedRulesAnonymousIPListMetric"
      sampled_requests_enabled  = true
    }
  }

  # Amazon IP Reputation list
  rule {
    name     = "AWSManagedRulesAmazonIpReputationList"
    priority = 6

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "AWSManagedRulesAmazonIpReputationListMetric"
      sampled_requests_enabled  = true
    }
  }

  # =====================================================
  # Custom Rules
  # =====================================================

  # Rate limiting rule - 2000 requests per 5 minutes per IP
  rule {
    name     = "RateLimitRule"
    priority = 10

    action {
      block {
        custom_response {
          response_code = 429
          custom_response_body_key = "rate_limit_body"
        }
      }
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "RateLimitRuleMetric"
      sampled_requests_enabled  = true
    }
  }

  # Geo-blocking rule (optional - block specific countries)
  rule {
    name     = "GeoBlockingRule"
    priority = 11

    action {
      block {}
    }

    statement {
      geo_match_statement {
        # Block countries with high attack rates (customize as needed)
        country_codes = ["CN", "RU", "KP"]  # China, Russia, North Korea
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "GeoBlockingRuleMetric"
      sampled_requests_enabled  = true
    }
  }

  # Admin endpoint IP allowlist
  rule {
    name     = "AdminEndpointIPAllowlist"
    priority = 12

    action {
      block {}
    }

    statement {
      and_statement {
        statement {
          byte_match_statement {
            search_string = "/admin"
            field_to_match {
              uri_path {}
            }
            text_transformation {
              priority = 0
              type     = "LOWERCASE"
            }
            positional_constraint = "STARTS_WITH"
          }
        }

        statement {
          not_statement {
            statement {
              ip_set_reference_statement {
                arn = aws_wafv2_ip_set.admin_allowlist.arn
              }
            }
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "AdminEndpointIPAllowlistMetric"
      sampled_requests_enabled  = true
    }
  }

  # Block requests with suspicious user agents
  rule {
    name     = "BlockSuspiciousUserAgents"
    priority = 13

    action {
      block {}
    }

    statement {
      byte_match_statement {
        search_string = "bot"
        field_to_match {
          single_header {
            name = "user-agent"
          }
        }
        text_transformation {
          priority = 0
          type     = "LOWERCASE"
        }
        positional_constraint = "CONTAINS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "BlockSuspiciousUserAgentsMetric"
      sampled_requests_enabled  = true
    }
  }

  # Size constraint rule - limit request body size
  rule {
    name     = "SizeConstraintRule"
    priority = 14

    action {
      block {}
    }

    statement {
      size_constraint_statement {
        field_to_match {
          body {}
        }
        comparison_operator = "GT"
        size               = 10485760  # 10 MB
        text_transformation {
          priority = 0
          type     = "NONE"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "SizeConstraintRuleMetric"
      sampled_requests_enabled  = true
    }
  }

  # XSS Protection Rule
  rule {
    name     = "XSSProtectionRule"
    priority = 15

    action {
      block {}
    }

    statement {
      xss_match_statement {
        field_to_match {
          body {}
        }
        text_transformation {
          priority = 0
          type     = "HTML_ENTITY_DECODE"
        }
        text_transformation {
          priority = 1
          type     = "URL_DECODE"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "XSSProtectionRuleMetric"
      sampled_requests_enabled  = true
    }
  }

  # Visibility configuration
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name               = "babyshield-api-waf"
    sampled_requests_enabled  = true
  }

  # Custom response bodies
  custom_response_body {
    key          = "rate_limit_body"
    content      = jsonencode({
      error = "Too many requests. Please try again later."
    })
    content_type = "APPLICATION_JSON"
  }

  tags = {
    Name        = "babyshield-api-waf"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# =====================================================
# IP Sets
# =====================================================

# Admin IP Allowlist
resource "aws_wafv2_ip_set" "admin_allowlist" {
  name               = "babyshield-admin-allowlist"
  description        = "IP addresses allowed to access admin endpoints"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"

  # Add your admin IP addresses here
  addresses = [
    "203.0.113.0/24",   # Example: Office network
    "198.51.100.14/32", # Example: Admin home IP
    "192.0.2.44/32",    # Example: Monitoring service
  ]

  tags = {
    Name = "babyshield-admin-allowlist"
  }
}

# Blocked IP Set (for manual blocking)
resource "aws_wafv2_ip_set" "blocked_ips" {
  name               = "babyshield-blocked-ips"
  description        = "Manually blocked IP addresses"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"

  addresses = []  # Add IPs to block as needed

  tags = {
    Name = "babyshield-blocked-ips"
  }
}

# =====================================================
# Rule Groups (for reusable rules)
# =====================================================

resource "aws_wafv2_rule_group" "api_protection" {
  name     = "babyshield-api-protection"
  scope    = "REGIONAL"
  capacity = 100

  rule {
    name     = "BlockSQLInjection"
    priority = 1

    action {
      block {}
    }

    statement {
      sqli_match_statement {
        field_to_match {
          all_query_arguments {}
        }
        text_transformation {
          priority = 0
          type     = "URL_DECODE"
        }
        text_transformation {
          priority = 1
          type     = "HTML_ENTITY_DECODE"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "BlockSQLInjectionMetric"
      sampled_requests_enabled  = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name               = "babyshield-api-protection"
    sampled_requests_enabled  = true
  }

  tags = {
    Name = "babyshield-api-protection"
  }
}

# =====================================================
# Logging Configuration
# =====================================================

resource "aws_cloudwatch_log_group" "waf_log_group" {
  name              = "/aws/wafv2/babyshield"
  retention_in_days = 30

  tags = {
    Name = "babyshield-waf-logs"
  }
}

resource "aws_wafv2_web_acl_logging_configuration" "waf_logging" {
  resource_arn            = aws_wafv2_web_acl.babyshield_waf.arn
  log_destination_configs = [aws_cloudwatch_log_group.waf_log_group.arn]

  # Redact sensitive fields from logs
  redacted_fields {
    single_header {
      name = "authorization"
    }
  }

  redacted_fields {
    single_header {
      name = "cookie"
    }
  }

  redacted_fields {
    single_header {
      name = "x-api-key"
    }
  }
}

# =====================================================
# Associate WAF with ALB
# =====================================================

resource "aws_wafv2_web_acl_association" "waf_alb_association" {
  resource_arn = aws_lb.babyshield_alb.arn  # Reference to your ALB
  web_acl_arn  = aws_wafv2_web_acl.babyshield_waf.arn
}

# =====================================================
# CloudWatch Alarms
# =====================================================

resource "aws_cloudwatch_metric_alarm" "waf_blocked_requests" {
  alarm_name          = "babyshield-waf-blocked-requests"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name        = "BlockedRequests"
  namespace          = "AWS/WAFV2"
  period             = "300"
  statistic          = "Sum"
  threshold          = "100"
  alarm_description  = "This metric monitors blocked requests"
  alarm_actions      = [aws_sns_topic.security_alerts.arn]

  dimensions = {
    WebACL = aws_wafv2_web_acl.babyshield_waf.name
    Region = var.aws_region
    Rule   = "ALL"
  }
}

resource "aws_cloudwatch_metric_alarm" "waf_rate_limit" {
  alarm_name          = "babyshield-waf-rate-limit-triggered"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name        = "BlockedRequests"
  namespace          = "AWS/WAFV2"
  period             = "60"
  statistic          = "Sum"
  threshold          = "50"
  alarm_description  = "Rate limiting is blocking requests"
  alarm_actions      = [aws_sns_topic.security_alerts.arn]

  dimensions = {
    WebACL = aws_wafv2_web_acl.babyshield_waf.name
    Region = var.aws_region
    Rule   = "RateLimitRule"
  }
}

# =====================================================
# Outputs
# =====================================================

output "waf_web_acl_id" {
  value       = aws_wafv2_web_acl.babyshield_waf.id
  description = "The ID of the WAF Web ACL"
}

output "waf_web_acl_arn" {
  value       = aws_wafv2_web_acl.babyshield_waf.arn
  description = "The ARN of the WAF Web ACL"
}

output "admin_ip_set_arn" {
  value       = aws_wafv2_ip_set.admin_allowlist.arn
  description = "The ARN of the admin IP allowlist"
}
