# External Penetration Testing Checklist

**Target:** BabyShield API & Mobile Application  
**Scope:** Production Environment  
**Date:** January 2024

---

## 🎯 Testing Scope

### In Scope
- ✅ API endpoints (https://babyshield.cureviax.ai/api/*)
- ✅ Authentication mechanisms
- ✅ Authorization controls
- ✅ Data validation
- ✅ Session management
- ✅ Mobile app (iOS/Android)
- ✅ Web dashboard

### Out of Scope
- ❌ Social engineering
- ❌ Physical security
- ❌ Third-party services (Apple/Google OAuth)
- ❌ Denial of Service attacks
- ❌ AWS infrastructure

---

## 1️⃣ Authentication Testing

### OAuth Implementation
- [ ] Test OAuth flow manipulation
- [ ] Verify state parameter validation
- [ ] Check redirect URI validation
- [ ] Test token refresh mechanism
- [ ] Verify token expiration
- [ ] Test logout functionality
- [ ] Check for token leakage in logs
- [ ] Test concurrent sessions

### Session Management
- [ ] Session fixation attacks
- [ ] Session timeout testing
- [ ] Cookie security flags (Secure, HttpOnly, SameSite)
- [ ] JWT signature verification
- [ ] Token replay attacks
- [ ] Cross-device session handling

**Expected Results:**
- Tokens expire in 24 hours
- No session fixation vulnerabilities
- Secure cookie flags set

---

## 2️⃣ Authorization Testing

### Access Control
- [ ] Horizontal privilege escalation
- [ ] Vertical privilege escalation
- [ ] IDOR (Insecure Direct Object References)
- [ ] Force browsing
- [ ] API endpoint authorization
- [ ] Resource ownership verification

### Test Scenarios
```
GET /api/v1/user/{other_user_id}/data
Expected: 403 Forbidden

DELETE /api/v1/user/data/delete
Without token: 401 Unauthorized
With expired token: 401 Unauthorized
With valid token: 200 OK
```

---

## 3️⃣ Input Validation

### SQL Injection
- [ ] Search parameters
- [ ] Filter parameters
- [ ] Sort parameters
- [ ] Pagination parameters

**Test Payloads:**
```sql
' OR '1'='1
'; DROP TABLE users; --
' UNION SELECT * FROM users --
```

### XSS (Cross-Site Scripting)
- [ ] Reflected XSS
- [ ] Stored XSS
- [ ] DOM-based XSS

**Test Payloads:**
```javascript
<script>alert('XSS')</script>
<img src=x onerror=alert('XSS')>
javascript:alert('XSS')
```

### Command Injection
- [ ] OS command injection
- [ ] LDAP injection
- [ ] XML injection
- [ ] XXE (XML External Entity)

### Other Injection Types
- [ ] NoSQL injection
- [ ] Header injection
- [ ] Path traversal
- [ ] File upload vulnerabilities

---

## 4️⃣ API Security

### Rate Limiting
- [ ] Verify rate limits enforced
- [ ] Test rate limit bypass
- [ ] Check per-endpoint limits
- [ ] Test distributed attacks

**Expected Limits:**
- Anonymous: 60 req/min
- Authenticated: 100 req/min
- Search: 30 req/min

### API Abuse
- [ ] Mass data extraction
- [ ] Excessive data exposure
- [ ] Lack of resource limiting
- [ ] Missing pagination limits

### Error Handling
- [ ] Information disclosure in errors
- [ ] Stack traces exposed
- [ ] Debug mode detection
- [ ] Version disclosure

---

## 5️⃣ Data Security

### Sensitive Data Exposure
- [ ] Check for PII in responses
- [ ] Verify data minimization
- [ ] Test data masking
- [ ] Check for sensitive data in URLs
- [ ] Verify encryption in transit
- [ ] Test for data leaks in logs

### Data Validation
- [ ] Email addresses not stored
- [ ] Only internal user_id used
- [ ] Provider sub properly isolated
- [ ] No credit card data
- [ ] No SSN/government IDs

---

## 6️⃣ Security Headers

### Required Headers
- [ ] Strict-Transport-Security
- [ ] X-Content-Type-Options: nosniff
- [ ] X-Frame-Options: DENY
- [ ] X-XSS-Protection: 1; mode=block
- [ ] Content-Security-Policy
- [ ] Referrer-Policy
- [ ] Permissions-Policy

### CORS Testing
- [ ] Origin validation
- [ ] Credentials handling
- [ ] Wildcard usage
- [ ] Pre-flight requests

---

## 7️⃣ Mobile Application

### iOS Specific
- [ ] Jailbreak detection bypass
- [ ] Certificate pinning bypass
- [ ] Keychain data security
- [ ] URL scheme hijacking
- [ ] App Transport Security
- [ ] Binary protection (PIE, stack canaries)

### Android Specific
- [ ] Root detection bypass
- [ ] Certificate pinning bypass
- [ ] Shared preferences security
- [ ] Intent hijacking
- [ ] Exported components
- [ ] Binary protection (obfuscation)

### Common Mobile Tests
- [ ] Man-in-the-middle attacks
- [ ] Local data storage
- [ ] Insecure communication
- [ ] Code tampering
- [ ] Reverse engineering
- [ ] Side channel leaks

---

## 8️⃣ Business Logic

### Application Logic
- [ ] Race conditions
- [ ] Time-of-check/Time-of-use
- [ ] Workflow bypass
- [ ] Price manipulation (if applicable)
- [ ] Negative testing
- [ ] Boundary testing

### Search Functionality
- [ ] Search result manipulation
- [ ] Information disclosure
- [ ] Resource exhaustion
- [ ] Cache poisoning

---

## 9️⃣ Infrastructure

### SSL/TLS
- [ ] Certificate validation
- [ ] Cipher suite strength
- [ ] Protocol versions
- [ ] Certificate pinning
- [ ] HSTS implementation

### DNS Security
- [ ] DNS hijacking
- [ ] Subdomain takeover
- [ ] Zone transfer
- [ ] DNS cache poisoning

---

## 🔟 Compliance Checks

### Privacy
- [ ] GDPR compliance
- [ ] CCPA compliance
- [ ] COPPA compliance
- [ ] Data retention policies
- [ ] Right to deletion
- [ ] Data export functionality

### Security Standards
- [ ] OWASP Top 10 coverage
- [ ] OWASP Mobile Top 10
- [ ] PCI DSS (if payment processing)
- [ ] NIST guidelines

---

## 🛠️ Testing Tools

### Recommended Tools
- **Burp Suite Pro** - Web application testing
- **OWASP ZAP** - API security testing
- **Postman** - API functional testing
- **SQLMap** - SQL injection testing
- **Nikto** - Web server scanning
- **MobSF** - Mobile security framework
- **Frida** - Dynamic instrumentation
- **Charles Proxy** - Mobile traffic analysis

### Automated Scanners
- **Nessus** - Vulnerability scanning
- **Qualys** - Web application scanning
- **Acunetix** - Web vulnerability scanner
- **AppScan** - Application security testing

---

## 📊 Risk Rating

### Severity Levels
- **Critical** - Immediate exploitation, data breach risk
- **High** - Significant impact, should fix immediately
- **Medium** - Moderate impact, fix in next release
- **Low** - Minor impact, fix when convenient
- **Informational** - Best practice recommendation

### CVSS Scoring
Use CVSS 3.1 for vulnerability scoring:
- Attack Vector (AV)
- Attack Complexity (AC)
- Privileges Required (PR)
- User Interaction (UI)
- Scope (S)
- Confidentiality (C)
- Integrity (I)
- Availability (A)

---

## 📋 Reporting Template

### Executive Summary
- Testing dates
- Scope covered
- High-level findings
- Risk assessment
- Recommendations

### Technical Details
For each finding:
1. **Title** - Clear vulnerability name
2. **Severity** - Critical/High/Medium/Low
3. **Description** - What was found
4. **Impact** - Business impact
5. **Proof of Concept** - Reproduction steps
6. **Recommendation** - How to fix
7. **References** - OWASP, CVE, etc.

### Evidence
- Screenshots
- Request/Response pairs
- Code snippets
- Video demonstrations

---

## ✅ Pre-Test Checklist

### Legal
- [ ] Written authorization obtained
- [ ] Scope clearly defined
- [ ] Rules of engagement agreed
- [ ] NDA signed
- [ ] Insurance verified

### Technical
- [ ] Test environment identified
- [ ] Credentials provided
- [ ] API documentation reviewed
- [ ] Contact person designated
- [ ] Escalation process defined

### Communication
- [ ] Status update schedule
- [ ] Finding notification process
- [ ] Emergency contact list
- [ ] Report delivery date

---

## 🚨 Stop Conditions

Testing should stop if:
- System becomes unavailable
- Data corruption detected
- Unintended data exposure
- Third-party service affected
- Production impact observed

**Emergency Contact:**
- Security Team: security@babyshield.app
- On-call: +1-XXX-XXX-XXXX
- Escalation: cto@babyshield.app

---

## 📈 Post-Test Activities

### Immediate
1. Remove test accounts
2. Clear test data
3. Reset rate limits
4. Review logs for issues
5. Document all findings

### Follow-up
1. Remediation planning
2. Patch verification
3. Re-testing of fixes
4. Security awareness training
5. Process improvements

---

## 📚 References

- OWASP Testing Guide v4
- OWASP API Security Top 10
- OWASP Mobile Security Testing Guide
- NIST SP 800-115
- PTES (Penetration Testing Execution Standard)
- CWE (Common Weakness Enumeration)

---

**Document Version:** 1.0  
**Last Updated:** January 2024  
**Next Review:** After pentest completion  
**Classification:** Confidential
