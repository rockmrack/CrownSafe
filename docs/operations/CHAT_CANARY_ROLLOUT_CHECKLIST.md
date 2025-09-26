# Chat Feature Canary Rollout Checklist

This checklist provides step-by-step instructions for safely rolling out the BabyShield Chat feature using feature flags and monitoring.

## Pre-Rollout Setup

### ✅ 1. Monitoring Infrastructure
- [ ] Prometheus/Grafana dashboard deployed and accessible
- [ ] Alert rules loaded (`infra/prometheus/chat.rules.yml`)
- [ ] Alertmanager routing configured for chat alerts
- [ ] Test alerts fire correctly (induce a failure to verify)
- [ ] Alternative: CloudWatch metric filters and alarms configured

### ✅ 2. Feature Flag Configuration
- [ ] Environment variables set in ECS task definition:
  - `BS_FEATURE_CHAT_ENABLED=false` (start disabled)
  - `BS_FEATURE_CHAT_ROLLOUT_PCT=0.10` (10% initial rollout)
- [ ] Verify `/api/v1/chat/flags` endpoint returns correct values
- [ ] Test feature gating: requests should return 403 when disabled

### ✅ 3. Application Health
- [ ] All existing endpoints working normally
- [ ] No regressions in core barcode/visual recognition features
- [ ] Database migrations applied (chat memory tables)
- [ ] LLM client properly configured with API keys

## Rollout Phases

### Phase 1: Enable with 10% Rollout

#### Deploy Configuration
```bash
# Update ECS task definition environment variables:
BS_FEATURE_CHAT_ENABLED=true
BS_FEATURE_CHAT_ROLLOUT_PCT=0.10
```

#### Monitoring Checklist (First 30 minutes)
- [ ] **RPS**: Chat requests appearing in metrics (should be ~10% of total users)
- [ ] **Error Rate**: < 1% (target: < 0.5%)
- [ ] **p95 Latency**: < 2.8s (target: < 2.0s)
- [ ] **Circuit Rate**: < 1% (target: < 0.1%)
- [ ] **Fallback Rate**: < 5% (target: < 2%)
- [ ] **Blocked Rate**: ~90% (expected due to 10% rollout)

#### Success Criteria
- [ ] No critical alerts fired
- [ ] Error rate remains stable
- [ ] User feedback positive (if available)
- [ ] No impact on existing features

#### Rollback Triggers
- [ ] Error rate > 2% for 5+ minutes → **IMMEDIATE ROLLBACK**
- [ ] p95 latency > 2.8s for 10+ minutes → **ROLLBACK**
- [ ] Circuit breaker > 1% for 10+ minutes → **INVESTIGATE + POSSIBLE ROLLBACK**
- [ ] Any critical alert → **INVESTIGATE IMMEDIATELY**

### Phase 2: Increase to 25% Rollout

#### Prerequisites
- [ ] Phase 1 stable for 24+ hours
- [ ] No unresolved issues or alerts
- [ ] Performance metrics within targets

#### Deploy Configuration
```bash
BS_FEATURE_CHAT_ROLLOUT_PCT=0.25
```

#### Monitoring Checklist (First 60 minutes)
- [ ] **RPS**: Proportional increase in chat traffic
- [ ] **Error Rate**: Still < 1%
- [ ] **Latency**: No degradation from increased load
- [ ] **Resource Usage**: ECS CPU/memory within limits
- [ ] **Database**: No connection pool exhaustion

### Phase 3: Increase to 50% Rollout

#### Prerequisites
- [ ] Phase 2 stable for 48+ hours
- [ ] Confidence in system stability
- [ ] No performance degradation

#### Deploy Configuration
```bash
BS_FEATURE_CHAT_ROLLOUT_PCT=0.50
```

#### Additional Monitoring
- [ ] **LLM Provider**: Check OpenAI usage quotas and rate limits
- [ ] **Cost Impact**: Monitor increased LLM API costs
- [ ] **Database Load**: Ensure chat memory tables performing well

### Phase 4: Full Rollout (100%)

#### Prerequisites
- [ ] Phase 3 stable for 72+ hours
- [ ] All metrics consistently within targets
- [ ] Business approval for full rollout
- [ ] Cost impact acceptable

#### Deploy Configuration
```bash
BS_FEATURE_CHAT_ROLLOUT_PCT=1.0
```

#### Final Validation
- [ ] **Blocked Rate**: Should drop to ~0%
- [ ] **Total RPS**: Full chat traffic load
- [ ] **End-to-End**: Test all intents working correctly
- [ ] **Mobile Integration**: Verify UI shows chat features

## Emergency Procedures

### Immediate Rollback (Critical Issues)
```bash
# Option 1: Kill switch (fastest)
BS_FEATURE_CHAT_ENABLED=false

# Option 2: Reduce rollout to 0%
BS_FEATURE_CHAT_ROLLOUT_PCT=0.0

# Option 3: Reduce to previous stable percentage
BS_FEATURE_CHAT_ROLLOUT_PCT=0.10  # or last known good value
```

### Partial Rollback (Performance Issues)
```bash
# Reduce rollout by half
BS_FEATURE_CHAT_ROLLOUT_PCT=0.05  # if was 0.10
BS_FEATURE_CHAT_ROLLOUT_PCT=0.125 # if was 0.25
```

### Investigation Steps
1. **Check Grafana Dashboard**: Look for anomalies in all panels
2. **Review Recent Deployments**: Any code changes or infrastructure updates?
3. **Check External Dependencies**: OpenAI API status, database health
4. **Examine Logs**: Search for error patterns using `trace_id`
5. **Resource Monitoring**: ECS CPU/memory, database connections
6. **User Impact**: Customer support reports or mobile app crashes

## Key Metrics Targets

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Error Rate | < 0.5% | > 1% | > 2% |
| p95 Latency | < 2.0s | > 2.5s | > 2.8s |
| Circuit Rate | < 0.1% | > 0.5% | > 1% |
| Fallback Rate | < 2% | > 5% | > 10% |
| Tool Latency | < 500ms | > 800ms | > 1200ms |
| Synth Latency | < 1.5s | > 2.0s | > 2.5s |

## Communication Plan

### Internal Team
- [ ] Notify engineering team before each phase
- [ ] Share rollout schedule and monitoring dashboard
- [ ] Establish on-call rotation during rollout
- [ ] Document any issues and resolutions

### External Stakeholders
- [ ] Product team updated on rollout progress
- [ ] Customer support aware of new feature
- [ ] Business stakeholders informed of cost implications
- [ ] Mobile team coordinated for UI updates

## Post-Rollout Tasks

### After Successful 100% Rollout
- [ ] Remove feature flag code (optional, can keep for future use)
- [ ] Update documentation and runbooks
- [ ] Conduct retrospective on rollout process
- [ ] Optimize monitoring thresholds based on actual usage
- [ ] Plan for next feature rollouts using lessons learned

### Monitoring Maintenance
- [ ] Review and adjust alert thresholds monthly
- [ ] Archive old rollout documentation
- [ ] Update cost budgets and forecasts
- [ ] Plan capacity scaling for chat feature growth

## Troubleshooting Common Issues

### High Error Rate
- **Symptoms**: Error rate > 2%
- **Likely Causes**: LLM API issues, database problems, code bugs
- **Actions**: Check logs for specific errors, verify external services, rollback if persistent

### High Latency
- **Symptoms**: p95 > 2.8s
- **Likely Causes**: LLM slow responses, database queries, resource constraints
- **Actions**: Check ECS scaling, LLM provider status, database performance

### Circuit Breaker Activation
- **Symptoms**: Circuit rate > 1%
- **Likely Causes**: Timeout configurations too strict, external service issues
- **Actions**: Review timeout budgets, check tool performance, investigate specific intents

### No Traffic
- **Symptoms**: RPS near zero despite rollout > 0%
- **Likely Causes**: Mobile not updated, feature flag misconfiguration, user ID issues
- **Actions**: Check `/flags` endpoint, verify mobile integration, test with known user IDs

### Cost Overrun
- **Symptoms**: LLM API costs higher than expected
- **Likely Causes**: More usage than projected, inefficient prompts, retry loops
- **Actions**: Review usage patterns, optimize prompts, implement additional rate limiting
