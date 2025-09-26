# CloudWatch Chat Monitoring Setup

This document provides an alternative monitoring setup using AWS CloudWatch for teams not using Prometheus/Grafana.

## Overview

CloudWatch monitoring for BabyShield Chat relies on:
- **Log Metric Filters** to extract metrics from application logs
- **CloudWatch Alarms** for alerting on key thresholds
- **CloudWatch Dashboards** for visualization

## Prerequisites

1. Your application logs should include structured logging with:
   - `trace_id` for request tracing
   - `endpoint` (conversation, explain)
   - `intent` classification results
   - `status_code` for HTTP responses
   - `latency_ms` for request timing
   - Error indicators (`"chat_disabled"`, `"circuit_open"`, `"synth_fallback"`)

2. CloudWatch Logs agent configured to send application logs to a log group (e.g., `/aws/ecs/babyshield-api`)

## Log Metric Filters

Create the following metric filters in your CloudWatch log group:

### 1. Request Count Metrics

```bash
# Total chat requests
aws logs put-metric-filter \
  --log-group-name "/aws/ecs/babyshield-api" \
  --filter-name "ChatRequests" \
  --filter-pattern '[timestamp, level, msg="*chat*", endpoint, intent, status_code, ...]' \
  --metric-transformations \
    metricName=ChatRequestsTotal,metricNamespace=BabyShield/Chat,metricValue=1,defaultValue=0

# Success requests (2xx)
aws logs put-metric-filter \
  --log-group-name "/aws/ecs/babyshield-api" \
  --filter-name "ChatRequestsSuccess" \
  --filter-pattern '[timestamp, level, msg="*chat*", endpoint, intent, status_code=2*, ...]' \
  --metric-transformations \
    metricName=ChatRequestsSuccess,metricNamespace=BabyShield/Chat,metricValue=1,defaultValue=0

# Error requests (4xx/5xx)
aws logs put-metric-filter \
  --log-group-name "/aws/ecs/babyshield-api" \
  --filter-name "ChatRequestsError" \
  --filter-pattern '[timestamp, level, msg="*chat*", endpoint, intent, status_code=4*, ...] [timestamp, level, msg="*chat*", endpoint, intent, status_code=5*, ...]' \
  --metric-transformations \
    metricName=ChatRequestsError,metricNamespace=BabyShield/Chat,metricValue=1,defaultValue=0
```

### 2. Feature Gating Metrics

```bash
# Blocked requests (403 chat_disabled)
aws logs put-metric-filter \
  --log-group-name "/aws/ecs/babyshield-api" \
  --filter-name "ChatBlocked" \
  --filter-pattern '[timestamp, level, msg="*chat_disabled*", ...]' \
  --metric-transformations \
    metricName=ChatBlocked,metricNamespace=BabyShield/Chat,metricValue=1,defaultValue=0
```

### 3. Circuit Breaker & Fallback Metrics

```bash
# Circuit breaker open
aws logs put-metric-filter \
  --log-group-name "/aws/ecs/babyshield-api" \
  --filter-name "ChatCircuitOpen" \
  --filter-pattern '[timestamp, level, msg="*circuit_open*", ...]' \
  --metric-transformations \
    metricName=ChatCircuitOpen,metricNamespace=BabyShield/Chat,metricValue=1,defaultValue=0

# Synthesis fallback used
aws logs put-metric-filter \
  --log-group-name "/aws/ecs/babyshield-api" \
  --filter-name "ChatFallback" \
  --filter-pattern '[timestamp, level, msg="*synth_fallback*", ...]' \
  --metric-transformations \
    metricName=ChatFallback,metricNamespace=BabyShield/Chat,metricValue=1,defaultValue=0
```

### 4. Latency Metrics

```bash
# Request latency (requires custom log parsing)
aws logs put-metric-filter \
  --log-group-name "/aws/ecs/babyshield-api" \
  --filter-name "ChatLatency" \
  --filter-pattern '[timestamp, level, msg="*chat*", endpoint, intent, status_code, latency_ms, ...]' \
  --metric-transformations \
    metricName=ChatLatency,metricNamespace=BabyShield/Chat,metricValue=$latency_ms,defaultValue=0
```

## CloudWatch Alarms

### Error Rate Alarms

```bash
# High error rate warning (>1% for 15 minutes)
aws cloudwatch put-metric-alarm \
  --alarm-name "ChatHighErrorRateWarn" \
  --alarm-description "Chat error rate >1% for 15m" \
  --metric-name ChatRequestsError \
  --namespace BabyShield/Chat \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 3 \
  --threshold 0.01 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:babyshield-alerts-warning

# High error rate critical (>2% for 5 minutes)
aws cloudwatch put-metric-alarm \
  --alarm-name "ChatHighErrorRateCritical" \
  --alarm-description "Chat error rate >2% for 5m" \
  --metric-name ChatRequestsError \
  --namespace BabyShield/Chat \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 0.02 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:babyshield-alerts-critical
```

### Latency Alarms

```bash
# High p95 latency (>2.8s for 10 minutes)
aws cloudwatch put-metric-alarm \
  --alarm-name "ChatHighLatencyP95" \
  --alarm-description "Chat p95 latency > 2.8s" \
  --metric-name ChatLatency \
  --namespace BabyShield/Chat \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 2800 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:babyshield-alerts-critical
```

### Circuit Breaker Alarms

```bash
# Circuit breaker frequently opening
aws cloudwatch put-metric-alarm \
  --alarm-name "ChatCircuitOpenRate" \
  --alarm-description "Circuit breaker frequently opening (>1%)" \
  --metric-name ChatCircuitOpen \
  --namespace BabyShield/Chat \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 0.01 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:babyshield-alerts-warning
```

### Fallback Spike Alarms

```bash
# Fallback usage spike
aws cloudwatch put-metric-alarm \
  --alarm-name "ChatFallbackSpike" \
  --alarm-description "Fallbacks >5% of requests" \
  --metric-name ChatFallback \
  --namespace BabyShield/Chat \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 0.05 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:babyshield-alerts-warning
```

### Zero Traffic Alarms

```bash
# No chat traffic
aws cloudwatch put-metric-alarm \
  --alarm-name "ChatNoTraffic" \
  --alarm-description "Chat seeing near-zero traffic" \
  --metric-name ChatRequestsTotal \
  --namespace BabyShield/Chat \
  --statistic Sum \
  --period 1800 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:babyshield-alerts-info
```

## CloudWatch Dashboard

Create a dashboard to visualize chat metrics:

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["BabyShield/Chat", "ChatRequestsTotal"],
          [".", "ChatRequestsSuccess"],
          [".", "ChatRequestsError"]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "Chat Request Volume"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["BabyShield/Chat", "ChatLatency"]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Chat Latency (ms)"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["BabyShield/Chat", "ChatBlocked"],
          [".", "ChatCircuitOpen"],
          [".", "ChatFallback"]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "Chat Issues (Blocked, Circuit, Fallback)"
      }
    }
  ]
}
```

## Required Application Logging

To support these metric filters, ensure your application logs include:

```python
# In api/routers/chat.py, add structured logging
import logging
import json

logger = logging.getLogger(__name__)

def log_chat_request(endpoint: str, intent: str, status_code: int, latency_ms: int, trace_id: str, **kwargs):
    """Log structured chat request data for CloudWatch metric filters"""
    log_data = {
        "event_type": "chat_request",
        "endpoint": endpoint,
        "intent": intent,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "trace_id": trace_id,
        **kwargs
    }
    logger.info(f"CHAT_METRIC {json.dumps(log_data)}")

# Usage in endpoints:
try:
    # ... chat processing ...
    log_chat_request("conversation", intent, 200, latency_ms, trace_id)
except HTTPException as e:
    log_chat_request("conversation", intent, e.status_code, latency_ms, trace_id, error=e.detail)
```

## Runbook Actions

### High Error Rate
1. Check CloudWatch Logs for error patterns
2. Reduce `BS_FEATURE_CHAT_ROLLOUT_PCT` to limit impact
3. Investigate specific error traces using `trace_id`
4. Consider setting `BS_FEATURE_CHAT_ENABLED=false` if critical

### High Latency
1. Check ECS/ALB target group health
2. Review circuit breaker status
3. Scale ECS service if CPU/memory high
4. Investigate LLM provider performance

### Circuit Breaker Issues
1. Check tool timeout configurations
2. Review LLM provider status
3. Consider increasing timeout budgets if safe
4. Investigate specific failing intents

### Fallback Spikes
1. Check OpenAI/LLM provider health dashboard
2. Review recent prompt or model changes
3. Investigate specific failing synthesis calls
4. Consider temporary rollback if widespread

### Feature Gating Issues
1. Verify environment variables: `BS_FEATURE_CHAT_*`
2. Check user_id/device_id are being passed correctly
3. Review rollout percentage calculation
4. Test `/api/v1/chat/flags` endpoint

## Cost Optimization

- Use log sampling for high-volume metrics
- Set appropriate retention periods for log groups
- Use composite alarms to reduce SNS notification costs
- Consider using CloudWatch Insights for complex log analysis instead of multiple metric filters
