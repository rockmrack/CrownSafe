# Pre-Production Test Plan
**Date:** October 8, 2025  
**Environment:** Production ECS (post-deployment)  
**Image:** `production-20251008-2229`  
**Current Test Coverage:** 116 tests (100% pass rate)

---

## 🎯 Executive Summary

This document outlines additional comprehensive tests required before full production release. While we have achieved 100% pass rate on 116 tests, production readiness requires testing against live infrastructure, real data, and actual user scenarios.

---

## 📊 Current Test Coverage Analysis

### ✅ What We've Tested (116 tests)
- **Conversation API** (17 tests): Edge cases, validation, error handling
- **Authentication & Security** (24 tests): SQL injection, XSS, path traversal
- **Database Robustness** (20 tests): Connections, transactions, concurrent access
- **API Response Format** (27 tests): Headers, structures, content types
- **Performance** (17 tests): Response times, load handling, streaming
- **Integration** (21 tests): Cross-component validation, workflows

### ⚠️ What We Haven't Tested Yet
- **Live Production Database**: Real schema, migrations, data
- **External API Integrations**: OpenAI, AWS services, third-party APIs
- **Real User Workflows**: Registration → Login → API calls → Data retrieval
- **Barcode Scanning**: Real product lookups via UPC/EAN codes
- **Recall Data**: Actual recall queries across 39 agencies
- **Premium Features**: Subscription flows, payment processing
- **Mobile App Integration**: iOS/Android real device testing
- **Load at Scale**: Sustained traffic, concurrent users
- **Disaster Recovery**: Backup/restore, failover scenarios

---

## 🧪 Recommended Test Categories

### **Category 1: Production Infrastructure Tests** (Priority: CRITICAL)

#### 1.1 Database Production Tests
**Objective:** Verify production database is properly configured and accessible

**Tests to run:**
```bash
# Test 1: Database Connection
curl -X GET https://babyshield.cureviax.ai/healthz/database

# Test 2: Database Migration Status
curl -X GET https://babyshield.cureviax.ai/api/admin/migrations/status

# Test 3: Table Existence Check
# (Internal query - verify all required tables exist)

# Test 4: Database Performance
# Run 100 concurrent read queries and measure latency
```

**Expected Results:**
- Database connection successful (< 100ms)
- All migrations applied
- All required tables exist
- Query performance < 50ms p95

**Test File to Create:** `tests/production/test_database_prod.py`

---

#### 1.2 External Service Integration Tests
**Objective:** Verify all external services are accessible and functional

**Services to Test:**
- ✅ **AWS S3**: Image upload/retrieval
- ✅ **AWS SES**: Email delivery
- ✅ **OpenAI API**: Chat completions
- ✅ **Google Cloud Vision**: Barcode recognition
- ✅ **Firebase**: Push notifications
- ✅ **Redis**: Caching layer
- ✅ **Stripe**: Payment processing (if enabled)

**Tests to run:**
```bash
# Test 1: S3 Upload
curl -X POST https://babyshield.cureviax.ai/api/test/s3-upload \
  -H "Content-Type: application/json" \
  -d '{"test_file": "production_test.txt"}'

# Test 2: Email Send
curl -X POST https://babyshield.cureviax.ai/api/test/send-email \
  -H "Content-Type: application/json" \
  -d '{"to": "test@babyshield.dev", "subject": "Production Test"}'

# Test 3: OpenAI Integration
curl -X POST https://babyshield.cureviax.ai/api/conversation \
  -H "Content-Type: application/json" \
  -d '{"message": "Is this product safe for my baby?", "product_name": "Gerber Rice Cereal"}'
```

**Expected Results:**
- All services respond successfully
- No authentication errors
- Proper error handling for service failures

**Test File to Create:** `tests/production/test_external_services_prod.py`

---

### **Category 2: Real User Workflow Tests** (Priority: HIGH)

#### 2.1 User Registration & Authentication Flow
**Objective:** Test complete user journey from signup to authenticated API access

**Workflow:**
```
1. Register new user
2. Verify email (if required)
3. Login and get JWT token
4. Make authenticated API calls
5. Refresh token
6. Logout
```

**Tests to run:**
```bash
# Test 1: Registration
curl -X POST https://babyshield.cureviax.ai/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "prod-test-'$(date +%s)'@babyshield.dev",
    "password": "SecureP@ss123!",
    "name": "Production Test User"
  }'

# Test 2: Login
TOKEN=$(curl -X POST https://babyshield.cureviax.ai/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "prod-test@example.com", "password": "SecureP@ss123!"}' \
  | jq -r '.access_token')

# Test 3: Authenticated Request
curl -X GET https://babyshield.cureviax.ai/api/user/profile \
  -H "Authorization: Bearer $TOKEN"

# Test 4: Token Refresh
curl -X POST https://babyshield.cureviax.ai/api/auth/refresh \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Results:**
- User registration successful
- Email verification (if enabled) works
- JWT tokens issued correctly
- Authenticated endpoints accessible
- Token refresh works

**Test File to Create:** `tests/production/test_user_workflows_prod.py`

---

#### 2.2 Barcode Scanning & Product Lookup
**Objective:** Test real barcode scanning with actual products

**Test Products:**
- UPC: `041220976522` (Gerber Rice Cereal)
- UPC: `074570331062` (Similac Infant Formula)
- UPC: `070074564524` (Pampers Diapers)
- EAN: `5060523340309` (UK baby product)
- Invalid UPC: `999999999999`

**Tests to run:**
```bash
# Test 1: Valid UPC Lookup
curl -X POST https://babyshield.cureviax.ai/api/barcode/scan \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"barcode": "041220976522"}'

# Test 2: Barcode with Recall
curl -X POST https://babyshield.cureviax.ai/api/barcode/scan \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"barcode": "RECALLED_UPC_IF_KNOWN"}'

# Test 3: Invalid Barcode
curl -X POST https://babyshield.cureviax.ai/api/barcode/scan \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"barcode": "999999999999"}'

# Test 4: Image-Based Barcode Recognition
curl -X POST https://babyshield.cureviax.ai/api/barcode/scan-image \
  -H "Authorization: Bearer $TOKEN" \
  -F "image=@test_barcode_image.jpg"
```

**Expected Results:**
- Valid barcodes return product information
- Recalled products flagged correctly
- Invalid barcodes return proper error messages
- Image recognition works for clear barcode photos
- Response time < 2 seconds

**Test File to Create:** `tests/production/test_barcode_scanning_prod.py`

---

#### 2.3 Recall Data Retrieval
**Objective:** Verify recall data from 39 agencies is accessible

**Tests to run:**
```bash
# Test 1: Recent Recalls
curl -X GET "https://babyshield.cureviax.ai/api/recalls/recent?limit=10"

# Test 2: Search Recalls by Keyword
curl -X GET "https://babyshield.cureviax.ai/api/recalls/search?q=baby+formula"

# Test 3: Recalls by Agency
curl -X GET "https://babyshield.cureviax.ai/api/recalls?agency=FDA"

# Test 4: Recall Details
curl -X GET "https://babyshield.cureviax.ai/api/recalls/RECALL_ID"

# Test 5: User's Product Recalls
curl -X GET "https://babyshield.cureviax.ai/api/user/recalls" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Results:**
- Recall data returns successfully
- Search functionality works
- Agency filtering accurate
- User-specific recalls show saved products
- Data is recent (< 24 hours old)

**Test File to Create:** `tests/production/test_recall_data_prod.py`

---

### **Category 3: Performance & Load Tests** (Priority: HIGH)

#### 3.1 Load Testing
**Objective:** Verify system handles expected production load

**Load Test Scenarios:**

1. **Baseline Load** (100 concurrent users, 5 minutes)
   - Target: < 500ms response time (p95)
   - Target: 0% error rate

2. **Peak Load** (500 concurrent users, 5 minutes)
   - Target: < 1000ms response time (p95)
   - Target: < 1% error rate

3. **Sustained Load** (200 concurrent users, 30 minutes)
   - Target: No memory leaks
   - Target: Consistent performance

4. **Spike Load** (0 → 1000 users in 30 seconds)
   - Target: System handles spike gracefully
   - Target: Auto-scaling triggers

**Tools:** Apache JMeter, Locust, or k6

**Test Script Example (k6):**
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 }, // Ramp up
    { duration: '5m', target: 100 }, // Sustain
    { duration: '2m', target: 0 },   // Ramp down
  ],
};

export default function () {
  let response = http.get('https://babyshield.cureviax.ai/healthz');
  check(response, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
}
```

**Expected Results:**
- System stable under load
- Response times within SLA
- No memory leaks
- Auto-scaling works
- Database connections managed properly

**Test File to Create:** `tests/performance/load_test_production.js`

---

#### 3.2 Stress Testing
**Objective:** Find system breaking point

**Stress Test Scenarios:**
1. **Database Stress**: 1000 concurrent database queries
2. **API Stress**: 2000 requests/second
3. **Memory Stress**: Large payload uploads (10MB+)
4. **Connection Stress**: Exhaust connection pools

**Expected Results:**
- System degrades gracefully
- Error messages clear
- Recovery is automatic
- No data corruption

**Test File to Create:** `tests/performance/stress_test_production.js`

---

### **Category 4: Security & Compliance Tests** (Priority: CRITICAL)

#### 4.1 Security Penetration Testing
**Objective:** Verify production security posture

**Security Tests:**

1. **Authentication Bypass Attempts**
   - Test JWT token manipulation
   - Test expired token handling
   - Test missing authentication headers

2. **Authorization Tests**
   - Test accessing other users' data
   - Test admin endpoints without admin role
   - Test API rate limiting

3. **Input Validation**
   - SQL injection attempts (already tested)
   - XSS attempts (already tested)
   - Path traversal (already tested)
   - Command injection
   - XXE attacks
   - SSRF attempts

4. **TLS/SSL Configuration**
   - Verify HTTPS only
   - Check TLS version (1.2+)
   - Verify certificate validity
   - Test mixed content

**Tools:** OWASP ZAP, Burp Suite, SQLMap

**Test Commands:**
```bash
# Test 1: TLS Configuration
nmap --script ssl-enum-ciphers -p 443 babyshield.cureviax.ai

# Test 2: HTTP Security Headers
curl -I https://babyshield.cureviax.ai/healthz

# Test 3: OWASP ZAP Scan
zap-cli quick-scan https://babyshield.cureviax.ai
```

**Expected Results:**
- No critical vulnerabilities
- All security headers present
- HTTPS enforced
- Rate limiting active

**Test File to Create:** `tests/security/test_penetration_prod.py`

---

#### 4.2 GDPR & Privacy Compliance Tests
**Objective:** Verify data privacy compliance

**Privacy Tests:**
1. **Data Export**: User can export all their data
2. **Data Deletion**: User can delete their account and all data
3. **Consent Management**: Privacy settings respected
4. **Data Encryption**: PII encrypted at rest and in transit
5. **Audit Logging**: All data access logged

**Tests to run:**
```bash
# Test 1: Data Export
curl -X GET "https://babyshield.cureviax.ai/api/user/export-data" \
  -H "Authorization: Bearer $TOKEN"

# Test 2: Data Deletion Request
curl -X POST "https://babyshield.cureviax.ai/api/user/delete-account" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"confirm": true}'

# Test 3: Privacy Settings
curl -X GET "https://babyshield.cureviax.ai/api/user/privacy-settings" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Results:**
- Data export includes all user data
- Deletion request queued and executed
- Privacy settings enforced
- Audit trail created

**Test File to Create:** `tests/compliance/test_gdpr_compliance_prod.py`

---

### **Category 5: Mobile App Integration Tests** (Priority: MEDIUM)

#### 5.1 iOS App Integration
**Objective:** Verify API works correctly with iOS app

**Tests:**
1. Push notification registration
2. Barcode camera scanning
3. Offline mode data sync
4. App store receipt validation (if premium features)
5. Deep linking

**Test Approach:** Use iOS simulator or real device with TestFlight build

---

#### 5.2 Android App Integration
**Objective:** Verify API works correctly with Android app

**Tests:**
1. Firebase Cloud Messaging setup
2. Camera API integration
3. Background sync
4. Google Play billing (if premium features)
5. App links

**Test Approach:** Use Android emulator or real device with internal testing track

---

### **Category 6: Monitoring & Observability Tests** (Priority: HIGH)

#### 6.1 Logging & Tracing Tests
**Objective:** Verify production logging is working

**Tests:**
```bash
# Test 1: X-Trace-Id Propagation
curl -v https://babyshield.cureviax.ai/healthz | grep X-Trace-Id

# Test 2: Error Logging
curl -X POST https://babyshield.cureviax.ai/api/test/trigger-error

# Test 3: CloudWatch Logs
aws logs tail /aws/ecs/babyshield-backend --follow

# Test 4: Metrics Dashboard
# Check CloudWatch dashboards for anomalies
```

**Expected Results:**
- X-Trace-Id in all responses
- Errors logged to CloudWatch
- Structured logging format
- Metrics captured

---

#### 6.2 Alerting Tests
**Objective:** Verify alerts trigger correctly

**Alert Scenarios to Test:**
1. **High Error Rate**: Trigger 10 errors in 1 minute
2. **High Latency**: Create slow endpoint response
3. **Database Connection Loss**: Simulate database outage
4. **High Memory Usage**: Trigger memory spike
5. **Service Unhealthy**: Make healthz return unhealthy

**Expected Results:**
- Alerts trigger within 5 minutes
- Proper escalation
- Recovery notifications sent

---

### **Category 7: Disaster Recovery Tests** (Priority: CRITICAL)

#### 7.1 Backup & Restore Tests
**Objective:** Verify data can be recovered

**Tests:**
1. **Database Backup**: Verify RDS automated backups
2. **Point-in-Time Recovery**: Test PITR functionality
3. **Snapshot Restore**: Restore from snapshot to test environment
4. **S3 Backup**: Verify user uploads backed up

**Test Commands:**
```bash
# Test 1: Create manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier babyshield-prod \
  --db-snapshot-identifier prod-test-$(date +%Y%m%d)

# Test 2: Restore to test instance
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier babyshield-restore-test \
  --db-snapshot-identifier prod-test-20251008
```

**Expected Results:**
- Backups exist and are recent
- Restore completes successfully
- Data integrity verified

---

#### 7.2 Failover Tests
**Objective:** Verify system resilience

**Failover Scenarios:**
1. **Database Failover**: Trigger RDS Multi-AZ failover
2. **Container Failure**: Kill running ECS task
3. **AZ Failure**: Simulate availability zone outage
4. **Service Degradation**: Disable non-critical services

**Expected Results:**
- Automatic failover occurs
- Downtime < 30 seconds
- No data loss
- Users experience minimal disruption

---

## 📋 Test Execution Plan

### **Phase 1: Immediate Tests (Day 1)** ⚡
**Priority:** CRITICAL  
**Duration:** 2-4 hours

1. ✅ Database connectivity and migration status
2. ✅ External service integrations (OpenAI, AWS)
3. ✅ User registration and authentication flow
4. ✅ Barcode scanning with real products
5. ✅ Recall data retrieval
6. ✅ Security headers and TLS configuration
7. ✅ Monitoring and logging verification

**Action:** Run tests immediately after ECS deployment

---

### **Phase 2: Extended Tests (Days 2-3)** 📊
**Priority:** HIGH  
**Duration:** 1-2 days

1. ✅ Load testing (100-500 concurrent users)
2. ✅ Stress testing (find breaking point)
3. ✅ Mobile app integration (iOS & Android)
4. ✅ Premium features testing
5. ✅ Privacy compliance (GDPR)
6. ✅ Alert testing
7. ✅ Performance profiling

**Action:** Schedule during low-traffic hours

---

### **Phase 3: Disaster Recovery Tests (Week 2)** 🚨
**Priority:** CRITICAL (but scheduled)  
**Duration:** 4-8 hours

1. ✅ Backup verification
2. ✅ Point-in-time recovery
3. ✅ Failover simulation
4. ✅ Full system recovery drill

**Action:** Schedule maintenance window, notify users

---

### **Phase 4: Security Audit (Week 2-3)** 🔒
**Priority:** CRITICAL  
**Duration:** 3-5 days

1. ✅ Third-party security audit
2. ✅ Penetration testing
3. ✅ Compliance audit (GDPR, CCPA, HIPAA if applicable)
4. ✅ Vulnerability scanning

**Action:** Engage external security firm

---

## 🛠️ Test Files to Create

I recommend creating these test files immediately:

### **Priority 1: Critical (Create Today)**
```
tests/production/
├── __init__.py
├── test_database_prod.py           # Database connectivity & performance
├── test_external_services_prod.py  # AWS, OpenAI, Google Vision
├── test_user_workflows_prod.py     # Registration → Login → API
├── test_barcode_scanning_prod.py   # Real product lookups
└── test_security_prod.py           # TLS, headers, auth
```

### **Priority 2: High (Create This Week)**
```
tests/performance/
├── load_test_production.js         # k6 load test
├── stress_test_production.js       # k6 stress test
└── benchmark_suite.py              # Python performance benchmarks

tests/compliance/
├── test_gdpr_compliance_prod.py    # GDPR requirements
└── test_audit_logging_prod.py      # Audit trail verification
```

### **Priority 3: Medium (Create Next Week)**
```
tests/mobile/
├── test_ios_integration.py         # iOS-specific tests
└── test_android_integration.py     # Android-specific tests

tests/disaster_recovery/
├── test_backup_restore.py          # Backup/restore verification
└── test_failover.py                # Failover scenarios
```

---

## 📊 Success Criteria

Before declaring **"PRODUCTION READY"**, we need:

### **Must Have (Blocking)** 🚫
- [ ] All Phase 1 tests passing (100%)
- [ ] Database migrations verified
- [ ] External services working
- [ ] User workflows functional
- [ ] Security headers present
- [ ] TLS properly configured
- [ ] Load test passes (100 users, < 500ms p95)
- [ ] No critical security vulnerabilities

### **Should Have (High Priority)** ⚠️
- [ ] Mobile app integration tested
- [ ] Stress test identifies limits
- [ ] GDPR compliance verified
- [ ] Monitoring and alerting confirmed
- [ ] Load test passes (500 users, < 1s p95)

### **Nice to Have (Medium Priority)** ✨
- [ ] Disaster recovery tested
- [ ] Third-party security audit complete
- [ ] Performance optimization complete
- [ ] Documentation updated

---

## 🎯 Recommended Immediate Actions

### **Action 1: Run Production Smoke Tests**
```bash
cd tests/production
pytest test_database_prod.py -v
pytest test_external_services_prod.py -v
pytest test_user_workflows_prod.py -v
pytest test_barcode_scanning_prod.py -v
pytest test_security_prod.py -v
```

### **Action 2: Monitor Production Metrics**
```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=babyshield-backend-task-service-0l41s2a9 \
  --start-time 2025-10-08T00:00:00Z \
  --end-time 2025-10-08T23:59:59Z \
  --period 300 \
  --statistics Average,Maximum
```

### **Action 3: Test Critical User Flows**
1. Open production app
2. Register new test user
3. Scan a real barcode
4. Check recall information
5. Verify email notifications

### **Action 4: Load Test with k6**
```bash
# Install k6
brew install k6  # macOS
# or
choco install k6  # Windows

# Run basic load test
k6 run tests/performance/load_test_production.js
```

---

## 📈 Test Metrics to Track

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| API Response Time (p50) | < 200ms | < 500ms |
| API Response Time (p95) | < 500ms | < 1000ms |
| API Response Time (p99) | < 1000ms | < 2000ms |
| Error Rate | < 0.1% | < 1% |
| Database Query Time | < 50ms | < 200ms |
| Barcode Scan Time | < 2s | < 5s |
| Concurrent Users Supported | 500+ | 100+ |
| Uptime | 99.9% | 99% |
| TLS Grade | A+ | A |
| Security Scan Result | 0 critical | 0 high |

---

## 🚨 Risk Assessment

### **High Risk Areas** (Test First)
1. **Database migrations** - Could corrupt data
2. **External API failures** - OpenAI, Google Vision downtime
3. **Authentication tokens** - JWT issues could lock out users
4. **Barcode scanning** - Core feature failure
5. **Recall data sync** - Outdated data = safety risk

### **Medium Risk Areas**
1. **Mobile app compatibility** - OS version differences
2. **Performance under load** - Traffic spikes
3. **Email delivery** - SES reputation
4. **Premium features** - Payment processing

### **Low Risk Areas**
1. **Documentation endpoints** - Non-critical
2. **Static file serving** - CDN handles most
3. **Analytics** - Not user-facing

---

## 📞 Incident Response Plan

If critical issues found during testing:

### **Severity 1 (Critical)** 🚨
**Examples:** Database inaccessible, authentication broken, data loss

**Response:**
1. Rollback to previous image immediately
2. Notify all team members
3. Investigate root cause
4. Fix and re-test before deploying again

### **Severity 2 (High)** ⚠️
**Examples:** Slow performance, external service failure, minor data issues

**Response:**
1. Document the issue
2. Create hotfix if possible
3. Schedule maintenance window if needed
4. Monitor closely

### **Severity 3 (Medium)** ℹ️
**Examples:** UI bugs, minor feature issues, documentation errors

**Response:**
1. Create ticket for next sprint
2. Add to backlog
3. Not blocking for production

---

## ✅ Next Steps

1. **Review this plan** with your team
2. **Prioritize tests** based on your timeline
3. **Create test files** for Phase 1 (Priority 1)
4. **Run production smoke tests** immediately
5. **Monitor metrics** for first 24 hours
6. **Schedule load tests** for off-peak hours
7. **Plan disaster recovery drill** for Week 2
8. **Engage security audit firm** for Week 2-3

---

## 📚 Additional Resources

- **Load Testing Tutorial**: https://k6.io/docs/
- **OWASP Testing Guide**: https://owasp.org/www-project-web-security-testing-guide/
- **AWS Well-Architected**: https://aws.amazon.com/architecture/well-architected/
- **GDPR Checklist**: https://gdpr.eu/checklist/
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/

---

**Prepared by:** GitHub Copilot Agent  
**Date:** October 8, 2025  
**Version:** 1.0  
**Status:** Ready for Review
