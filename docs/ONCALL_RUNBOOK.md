# BabyShield API On-Call Runbook

## Quick Reference

**Service:** BabyShield API  
**Environment:** Production  
**URL:** https://babyshield.cureviax.ai  
**AWS Region:** eu-north-1  
**Monitoring:** Prometheus + Grafana  
**Alerts:** PagerDuty / Slack #babyshield-alerts  

### Key Endpoints
- Health Check: `GET /api/v1/monitoring/healthz`
- Readiness: `GET /api/v1/monitoring/readyz`
- Metrics: `GET /metrics`
- SLO Status: `GET /api/v1/monitoring/slo`

### SLO Targets
- **Uptime:** 99.9% (43.2 minutes downtime/month)
- **Latency p95:** < 800ms
- **Error Rate:** < 0.1%

---

## Alert Response Procedures

### 🔴 CRITICAL: ServiceDown

**Alert:** `up{job="babyshield-api"} == 0`

**Impact:** Complete service outage

**Response:**

1. **Verify** the outage:
   ```bash
   curl -I https://babyshield.cureviax.ai/api/v1/monitoring/healthz
   ```

2. **Check AWS ECS**:
   ```bash
   aws ecs describe-services --cluster babyshield-cluster --services babyshield-backend --region eu-north-1
   ```

3. **Check task health**:
   ```bash
   aws ecs list-tasks --cluster babyshield-cluster --service-name babyshield-backend --region eu-north-1
   aws ecs describe-tasks --cluster babyshield-cluster --tasks <TASK_ARN> --region eu-north-1
   ```

4. **Check CloudWatch logs**:
   ```bash
   aws logs tail /ecs/babyshield-backend --follow --region eu-north-1
   ```

5. **Restart service** if needed:
   ```bash
   aws ecs update-service --cluster babyshield-cluster --service babyshield-backend --force-new-deployment --region eu-north-1
   ```

6. **Scale up** if under load:
   ```bash
   aws ecs update-service --cluster babyshield-cluster --service babyshield-backend --desired-count 3 --region eu-north-1
   ```

**Root Causes:**
- Container crash
- Memory/CPU limits exceeded
- Database connection issues
- Network issues

---

### 🟡 WARNING: HighLatencyP95

**Alert:** `p95 latency > 800ms`

**Impact:** Degraded user experience

**Response:**

1. **Check current latency**:
   ```bash
   curl -w "@curl-format.txt" -o /dev/null -s https://babyshield.cureviax.ai/api/v1/search/advanced -X POST -H "Content-Type: application/json" -d '{"product":"test"}'
   ```

2. **Check database performance**:
   ```sql
   -- In RDS Query Editor
   SELECT 
     query,
     mean_exec_time,
     calls
   FROM pg_stat_statements 
   ORDER BY mean_exec_time DESC 
   LIMIT 10;
   ```

3. **Check cache hit rate**:
   ```bash
   curl https://babyshield.cureviax.ai/metrics | grep cache_hits
   ```

4. **Check concurrent connections**:
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```

5. **Quick fixes**:
   - Clear Redis cache if corrupted
   - Restart stalled workers
   - Increase connection pool size
   - Scale horizontally

**Root Causes:**
- Slow database queries
- Cache misses
- External API delays
- Resource contention

---

### 🟡 WARNING: HighErrorRate

**Alert:** `5xx errors > 1%`

**Impact:** Users experiencing failures

**Response:**

1. **Check error logs**:
   ```bash
   aws logs filter-log-events --log-group-name /ecs/babyshield-backend --filter-pattern "ERROR" --start-time $(date -u -d '5 minutes ago' +%s)000 --region eu-north-1
   ```

2. **Check specific error types**:
   ```bash
   curl https://babyshield.cureviax.ai/metrics | grep error_total
   ```

3. **Check database status**:
   ```bash
   aws rds describe-db-instances --db-instance-identifier babyshield-db --region eu-north-1
   ```

4. **Check Redis status**:
   ```bash
   redis-cli -h <REDIS_HOST> ping
   ```

5. **Common fixes**:
   - Restart failed background jobs
   - Fix database connection pool
   - Clear corrupted cache
   - Roll back recent deployment

**Root Causes:**
- Database connectivity
- Dependency failures
- Bug in recent deployment
- Resource exhaustion

---

### 🟡 WARNING: RateLimitExhausted

**Alert:** `rate_limit_remaining < 10`

**Impact:** User approaching rate limit

**Response:**

1. **Identify user**:
   ```bash
   curl https://babyshield.cureviax.ai/metrics | grep rate_limit_remaining
   ```

2. **Check for abuse**:
   ```bash
   aws logs filter-log-events --log-group-name /ecs/babyshield-backend --filter-pattern "<USER_ID>" --region eu-north-1
   ```

3. **Temporary increase** (if legitimate):
   ```python
   # In Redis
   redis-cli
   > HSET rate_limit:<user_id> limit 10000
   > EXPIRE rate_limit:<user_id> 3600
   ```

4. **Block if abuse detected**:
   ```python
   # Add to blocklist
   redis-cli
   > SADD blocked_users <user_id>
   ```

---

### 🟡 WARNING: DatabaseConnectionPoolExhausted

**Alert:** `database_connections_active > 90`

**Impact:** Risk of connection failures

**Response:**

1. **Check active connections**:
   ```sql
   SELECT 
     pid,
     usename,
     application_name,
     client_addr,
     state,
     query_start,
     state_change
   FROM pg_stat_activity
   WHERE state != 'idle'
   ORDER BY query_start;
   ```

2. **Kill long-running queries**:
   ```sql
   -- Queries running > 5 minutes
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'active'
   AND query_start < NOW() - INTERVAL '5 minutes'
   AND usename = 'app_user';
   ```

3. **Restart application** to reset pool:
   ```bash
   aws ecs update-service --cluster babyshield-cluster --service babyshield-backend --force-new-deployment --region eu-north-1
   ```

4. **Increase pool size** (temporary):
   ```bash
   # Update environment variable
   aws ecs update-service --cluster babyshield-cluster --service babyshield-backend --task-definition <NEW_TASK_DEF> --region eu-north-1
   ```

---

### 🟡 WARNING: HighMemoryUsage

**Alert:** `memory_usage > 7GB`

**Impact:** Risk of OOM kill

**Response:**

1. **Check memory consumers**:
   ```bash
   # SSH into container
   docker exec -it <container_id> /bin/bash
   ps aux --sort=-%mem | head -10
   ```

2. **Check for memory leaks**:
   ```python
   # In application logs
   grep "memory" /var/log/app.log
   ```

3. **Force garbage collection**:
   ```python
   # Via admin endpoint
   curl -X POST https://babyshield.cureviax.ai/admin/gc
   ```

4. **Restart if needed**:
   ```bash
   aws ecs update-service --cluster babyshield-cluster --service babyshield-backend --force-new-deployment --region eu-north-1
   ```

---

### 🔴 CRITICAL: SyntheticProbeFailure

**Alert:** `probe_success == 0`

**Impact:** Key endpoints not responding

**Response:**

1. **Check specific probe**:
   ```bash
   curl https://babyshield.cureviax.ai/api/v1/monitoring/probe/healthz
   curl https://babyshield.cureviax.ai/api/v1/monitoring/probe/search
   ```

2. **Check dependencies**:
   ```bash
   curl https://babyshield.cureviax.ai/api/v1/monitoring/readyz
   ```

3. **Follow ServiceDown runbook** if all probes failing

---

## Common Procedures

### Rolling Restart

Safe restart without downtime:

```bash
# Scale up
aws ecs update-service --cluster babyshield-cluster --service babyshield-backend --desired-count 4 --region eu-north-1

# Wait for new tasks
sleep 60

# Force new deployment
aws ecs update-service --cluster babyshield-cluster --service babyshield-backend --force-new-deployment --region eu-north-1

# Scale back down
aws ecs update-service --cluster babyshield-cluster --service babyshield-backend --desired-count 2 --region eu-north-1
```

### Database Maintenance

```sql
-- Analyze tables
ANALYZE;

-- Vacuum (careful in production)
VACUUM ANALYZE;

-- Reindex (blocks writes!)
REINDEX TABLE recalls_enhanced;
```

### Cache Clear

```bash
# Redis
redis-cli
> FLUSHDB  # Clear current database
> INFO memory

# Application cache
curl -X POST https://babyshield.cureviax.ai/admin/cache/clear
```

### Emergency Rollback

```bash
# Get previous task definition
aws ecs describe-task-definition --task-definition babyshield-backend --region eu-north-1

# Update service with previous version
aws ecs update-service --cluster babyshield-cluster --service babyshield-backend --task-definition babyshield-backend:PREVIOUS_VERSION --region eu-north-1
```

---

## Monitoring Links

### Dashboards
- **Grafana:** https://monitoring.cureviax.ai/d/babyshield
- **CloudWatch:** https://console.aws.amazon.com/cloudwatch/home?region=eu-north-1
- **AWS ECS Console:** https://console.aws.amazon.com/ecs/home?region=eu-north-1

### Logs
- **CloudWatch Logs:** `/ecs/babyshield-backend`
- **Application Logs:** https://monitoring.cureviax.ai/explore

### Metrics
- **Prometheus:** https://prometheus.cureviax.ai
- **Application Metrics:** https://babyshield.cureviax.ai/metrics

---

## Escalation Path

### Severity Levels

**SEV-1 (Critical):**
- Complete outage
- Data loss/corruption
- Security breach
- **Response Time:** 15 minutes
- **Escalate:** Immediately

**SEV-2 (High):**
- Partial outage
- SLO violation
- Major feature broken
- **Response Time:** 30 minutes
- **Escalate:** After 1 hour

**SEV-3 (Medium):**
- Performance degradation
- Non-critical feature broken
- **Response Time:** 2 hours
- **Escalate:** After 4 hours

**SEV-4 (Low):**
- Minor issues
- Cosmetic problems
- **Response Time:** Next business day
- **Escalate:** If not resolved in 2 days

### Contacts

**Primary On-Call:** Check PagerDuty schedule

**Escalation:**
1. Primary On-Call Engineer
2. Secondary On-Call Engineer
3. Team Lead
4. Engineering Manager
5. VP Engineering

**External Dependencies:**
- AWS Support: [Support Case](https://console.aws.amazon.com/support)
- Database Admin: #database-team
- Security Team: #security-incidents

---

## Post-Incident

### Required Actions

1. **Acknowledge** alert in PagerDuty
2. **Update** status page if user-facing
3. **Document** in incident channel
4. **Fix** the immediate issue
5. **Monitor** for 30 minutes after fix
6. **Write** post-mortem (SEV-1/2)

### Post-Mortem Template

```markdown
## Incident Post-Mortem

**Date:** YYYY-MM-DD
**Severity:** SEV-X
**Duration:** XX minutes
**Impact:** X% of users affected

### Timeline
- HH:MM - Alert fired
- HH:MM - Engineer acknowledged
- HH:MM - Root cause identified
- HH:MM - Fix deployed
- HH:MM - Incident resolved

### Root Cause
[What broke and why]

### Resolution
[How it was fixed]

### Action Items
- [ ] Fix root cause
- [ ] Add monitoring
- [ ] Update runbook
- [ ] Add tests

### Lessons Learned
[What we learned]
```

---

## Useful Commands

### Quick Health Check
```bash
#!/bin/bash
echo "=== BabyShield Health Check ==="
echo -n "API: "
curl -s -o /dev/null -w "%{http_code}" https://babyshield.cureviax.ai/api/v1/monitoring/healthz
echo ""
echo -n "Database: "
curl -s https://babyshield.cureviax.ai/api/v1/monitoring/readyz | jq -r '.checks.database'
echo -n "Redis: "
curl -s https://babyshield.cureviax.ai/api/v1/monitoring/readyz | jq -r '.checks.redis'
echo -n "SLO Status: "
curl -s https://babyshield.cureviax.ai/api/v1/monitoring/slo | jq -r '.overall_status'
```

### Performance Check
```bash
#!/bin/bash
echo "=== Performance Metrics ==="
curl -s https://babyshield.cureviax.ai/metrics | grep -E "http_request_duration_seconds|error_total|rate_limit" | head -20
```

### Database Stats
```sql
-- Connection stats
SELECT 
  max_conn,
  used,
  res_for_super,
  max_conn - used - res_for_super AS available
FROM 
  (SELECT count(*) used FROM pg_stat_activity) t1,
  (SELECT setting::int res_for_super FROM pg_settings WHERE name='superuser_reserved_connections') t2,
  (SELECT setting::int max_conn FROM pg_settings WHERE name='max_connections') t3;

-- Slow queries
SELECT 
  query,
  calls,
  total_exec_time,
  mean_exec_time,
  max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## Prevention Checklist

### Daily
- [ ] Check SLO dashboard
- [ ] Review error logs
- [ ] Check synthetic probe status

### Weekly
- [ ] Review alerts fired
- [ ] Check resource trends
- [ ] Update capacity planning

### Monthly
- [ ] Review post-mortems
- [ ] Update runbooks
- [ ] Test disaster recovery
- [ ] Review SLO targets

---

## Notes

- All times in UTC
- Metrics retained for 30 days
- Logs retained for 90 days
- Backups every 6 hours
- DR region: us-east-1

**Last Updated:** 2024-12-31  
**Version:** 1.0.0
