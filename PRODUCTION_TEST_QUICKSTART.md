# Production Test Quick Start Guide

## 🚀 Congratulations on Successful Deployment!

Your production image `production-20251008-2229` has been deployed to ECS. Now let's validate it's production-ready with comprehensive testing.

---

## ⚡ Quick Start - Run These Tests NOW

### Step 1: Production Database Tests (2-5 minutes)
```bash
# Run all database production tests
pytest tests/production/test_database_prod.py -v

# Or run specific critical tests only
pytest tests/production/test_database_prod.py::TestProductionDatabase::test_database_connection_success -v
pytest tests/production/test_database_prod.py::TestProductionDatabase::test_database_connection_speed -v
pytest tests/production/test_database_prod.py::TestProductionDatabase::test_database_migration_status -v
```

**Expected:** All tests should pass ✅

---

### Step 2: API Health Check (30 seconds)
```bash
# Test the deployed API
curl -v https://babyshield.cureviax.ai/healthz

# Check for X-Trace-Id header (our recent fix)
curl -I https://babyshield.cureviax.ai/healthz | grep X-Trace-Id

# Test API docs accessibility
curl https://babyshield.cureviax.ai/docs
```

**Expected Results:**
```
HTTP/2 200 
x-trace-id: [UUID]
content-type: application/json
```

---

### Step 3: Conversation API Test (1 minute)
```bash
# Test the conversation endpoint with real request
curl -X POST https://babyshield.cureviax.ai/api/conversation \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Is this product safe for my baby?",
    "product_name": "Gerber Rice Cereal"
  }'
```

**Expected:** Should return a helpful response with X-Trace-Id header

---

### Step 4: Monitor CloudWatch Logs (ongoing)
```bash
# Tail ECS logs
aws logs tail /aws/ecs/babyshield-backend --follow --region eu-north-1

# Or check specific log group
aws logs tail /ecs/babyshield-backend-task --follow --region eu-north-1
```

**Expected:** See startup logs, no errors, X-Trace-Id in request logs

---

## 📊 Current Test Status

### ✅ Completed (116 tests, 100% passing)
- Conversation API (17 tests)
- Authentication & Security (24 tests)
- Database Robustness (20 tests)
- API Response Format (27 tests)
- Performance Benchmarks (17 tests)
- Integration Tests (21 tests)

### 🔄 Ready to Run (Production validation)
- **Production Database Tests** ← **RUN FIRST**
- External Service Integration
- User Workflow Tests
- Barcode Scanning Tests
- Security Validation

### 📅 Scheduled (Next phases)
- Load Testing (Phase 2)
- Mobile Integration (Phase 2)
- Disaster Recovery (Phase 3)
- Security Audit (Phase 4)

---

## 🎯 Critical Tests to Run TODAY

Run these in order:

### Test 1: Database Connectivity ⚡ CRITICAL
```bash
pytest tests/production/test_database_prod.py::TestProductionDatabase::test_database_connection_success -v
```
**Why:** Ensures app can connect to production database

### Test 2: Database Performance ⚡ CRITICAL
```bash
pytest tests/production/test_database_prod.py::TestProductionDatabase::test_database_query_performance -v
```
**Why:** Verifies queries are fast (< 50ms)

### Test 3: Migration Status ⚡ CRITICAL
```bash
pytest tests/production/test_database_prod.py::TestProductionDatabase::test_database_migration_status -v
```
**Why:** Confirms all migrations applied correctly

### Test 4: X-Trace-Id Header ⚡ CRITICAL
```bash
curl -I https://babyshield.cureviax.ai/healthz | grep -i x-trace-id
```
**Why:** Our recent critical fix - must be present

### Test 5: API Response Time ⚡ CRITICAL
```bash
time curl -X GET https://babyshield.cureviax.ai/healthz
```
**Why:** Should respond in < 1 second

### Test 6: Conversation Endpoint ⚡ CRITICAL
```bash
pytest tests/api/test_conversation_smoke.py -v
```
**Why:** Core feature validation (already passed locally)

---

## 🔍 What to Check in CloudWatch

1. **CPU Utilization**: Should be < 50% at idle
2. **Memory Utilization**: Should be < 70% at idle
3. **Request Count**: Monitor for traffic patterns
4. **Error Rate**: Should be 0% or near 0%
5. **Response Time**: p95 should be < 500ms

**CloudWatch Dashboard:**
```bash
# Open CloudWatch console
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=babyshield-backend-task-service-0l41s2a9 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum \
  --region eu-north-1
```

---

## 🐛 Troubleshooting Common Issues

### Issue: Database connection fails
**Solution:**
1. Check security group allows ECS → RDS
2. Verify DATABASE_URL environment variable
3. Check RDS instance is running
4. Verify credentials are correct

### Issue: X-Trace-Id header missing
**Solution:**
1. This was fixed in production-20251008-2229
2. Verify you deployed the latest image
3. Check ECS task definition uses correct image
4. Restart ECS service if needed

### Issue: High response times
**Solution:**
1. Check database query performance
2. Monitor connection pool usage
3. Check for slow external API calls
4. Review CloudWatch metrics

### Issue: Conversation tests fail
**Solution:**
1. Verify OpenAI API key is set
2. Check OpenAI API quota
3. Ensure feature flags enabled
4. Review application logs

---

## 📈 Success Criteria Checklist

Before declaring production ready, verify:

- [ ] Database connection successful
- [ ] Database migrations up to date
- [ ] Query performance < 50ms
- [ ] API responds with 200 status
- [ ] X-Trace-Id header present
- [ ] Response time < 1 second
- [ ] No errors in CloudWatch logs
- [ ] CPU utilization < 50%
- [ ] Memory utilization < 70%
- [ ] All smoke tests passing

---

## 🎉 Next Steps After Initial Validation

### If all tests pass:
1. ✅ Monitor for 24 hours
2. ✅ Schedule load testing (Phase 2)
3. ✅ Plan mobile integration tests
4. ✅ Schedule security audit
5. ✅ Prepare for production launch

### If any test fails:
1. 🚨 Document the failure
2. 🚨 Check CloudWatch logs
3. 🚨 Consider rollback if critical
4. 🚨 Fix and redeploy
5. 🚨 Re-run all tests

---

## 📞 Need Help?

### Test Results Not as Expected?
1. Check `PRE_PRODUCTION_TEST_PLAN.md` for detailed guidance
2. Review CloudWatch logs for errors
3. Run tests with `-vv` flag for verbose output
4. Check environment variables are set correctly

### Performance Issues?
1. Review `tests/deep/test_performance_deep.py` results
2. Check database query plans
3. Monitor external API latency
4. Consider scaling ECS tasks

### Security Concerns?
1. Review `tests/deep/test_authentication_deep.py` results
2. Verify all security headers present
3. Check TLS configuration
4. Consider running OWASP ZAP scan

---

## 🔗 Documentation References

- **Full Test Plan**: `PRE_PRODUCTION_TEST_PLAN.md`
- **Test Results**: `100_PERCENT_TEST_RESULTS.md`
- **Deep Tests**: `DEEP_TEST_RESULTS_20251008.md`
- **Deployment Guide**: `MANUAL_ECS_DEPLOYMENT.md`
- **Deployment Summary**: `DEPLOYMENT_SUMMARY_20251008.md`

---

## ⏱️ Time Estimates

- **Database Tests**: 2-5 minutes
- **API Health Checks**: 30 seconds
- **Smoke Tests**: 2-3 minutes
- **CloudWatch Review**: 5-10 minutes
- **Total Initial Validation**: ~10-20 minutes

---

## 🎯 Recommended Command Sequence

Run this exact sequence for quickest validation:

```bash
# 1. Database tests (most critical)
pytest tests/production/test_database_prod.py -v

# 2. API health check
curl -I https://babyshield.cureviax.ai/healthz

# 3. X-Trace-Id verification (our recent fix)
curl -I https://babyshield.cureviax.ai/healthz | grep -i x-trace-id

# 4. Conversation smoke tests
pytest tests/api/test_conversation_smoke.py -v

# 5. Deep test suite (if time permits)
pytest tests/deep/ -v

# 6. Monitor logs
aws logs tail /aws/ecs/babyshield-backend --follow --region eu-north-1
```

---

**Status:** ✅ Ready to test production deployment  
**Image:** `production-20251008-2229`  
**Confidence:** Maximum (116/116 tests passing locally)  
**Next Action:** Run database tests to validate production environment

---

*This guide provides immediate actionable steps. For comprehensive testing strategy, see PRE_PRODUCTION_TEST_PLAN.md*
