# Data Processing Agreement (DPA) Checklist

## Overview
This checklist ensures compliance with data protection regulations when using third-party services.

**Last Updated:** January 1, 2024

---

## ✅ Google (Firebase Crashlytics) DPA

### Required Steps

- [ ] **1. Review Google Cloud Platform Terms**
  - URL: https://cloud.google.com/terms
  - Review date: ___________
  - Reviewed by: ___________

- [ ] **2. Accept Firebase Terms of Service**
  - URL: https://firebase.google.com/terms
  - Acceptance date: ___________
  - Account email: ___________

- [ ] **3. Sign Google Cloud Data Processing Terms**
  - URL: https://cloud.google.com/terms/data-processing-terms
  - Signature date: ___________
  - Signatory: ___________

- [ ] **4. Configure Data Residency**
  - [ ] Select data location in Firebase Console
  - [ ] Document chosen regions: ___________
  - [ ] Verify compliance with local laws

- [ ] **5. Review Standard Contractual Clauses (SCCs)**
  - [ ] Review Google's SCCs
  - [ ] Verify adequacy for your jurisdiction
  - [ ] Document acceptance date: ___________

- [ ] **6. Configure Data Retention**
  - [ ] Set Crashlytics data retention to 90 days
  - [ ] Document retention policy
  - [ ] Configure automatic deletion

- [ ] **7. Implement Privacy Controls**
  - [ ] Crashlytics OFF by default in app
  - [ ] Clear opt-in mechanism
  - [ ] User control in settings
  - [ ] No PII in crash reports

- [ ] **8. Document Sub-processors**
  - [ ] List Google's sub-processors
  - [ ] Review quarterly for changes
  - [ ] Document in privacy policy

### Data Collected by Crashlytics

| Data Type | Collected | Purpose | Can Disable |
|-----------|-----------|---------|-------------|
| Crash stack traces | Yes (opt-in) | Debug crashes | Yes |
| Device model | Yes | Compatibility | Yes |
| OS version | Yes | Compatibility | Yes |
| App version | Yes | Version tracking | Yes |
| Installation UUID | Yes | Crash grouping | Yes |
| Timestamp | Yes | Timeline | Yes |
| User ID | No | N/A | N/A |
| Email | No | N/A | N/A |
| Location | No | N/A | N/A |

---

## ✅ AWS DPA

### Required Steps

- [ ] **1. Review AWS Customer Agreement**
  - URL: https://aws.amazon.com/agreement/
  - Review date: ___________

- [ ] **2. Accept AWS Data Processing Addendum**
  - URL: https://d1.awsstatic.com/legal/aws-gdpr/AWS_GDPR_DPA.pdf
  - Covered automatically under AWS Customer Agreement
  - Document date: ___________

- [ ] **3. Configure Data Residency**
  - [ ] Select EU regions for EU data
  - [ ] Current region: eu-north-1 (Stockholm)
  - [ ] Enable encryption at rest

- [ ] **4. Security Configuration**
  - [ ] Enable CloudTrail logging
  - [ ] Configure S3 bucket encryption
  - [ ] Enable GuardDuty
  - [ ] Set up security alerts

---

## ✅ Apple App Store DPA

### Required Steps

- [ ] **1. Apple Developer Program License Agreement**
  - Accept in Apple Developer account
  - Date: ___________

- [ ] **2. App Store Connect Agreement**
  - Review and accept terms
  - Date: ___________

- [ ] **3. Sign in with Apple**
  - [ ] Review privacy requirements
  - [ ] Implement relay service handling
  - [ ] Document user consent flow

---

## ✅ Google Play Store DPA

### Required Steps

- [ ] **1. Google Play Developer Distribution Agreement**
  - URL: https://play.google.com/about/developer-distribution-agreement.html
  - Accept date: ___________

- [ ] **2. Google Play Data Safety Form**
  - [ ] Complete in Play Console
  - [ ] Match privacy policy
  - [ ] Update quarterly

- [ ] **3. Sign in with Google**
  - [ ] Review OAuth scopes
  - [ ] Minimize data collection
  - [ ] Document consent flow

---

## 📋 Compliance Documentation

### Required Documents

- [ ] **Privacy Policy**
  - [ ] Updated with all processors
  - [ ] Available at: /legal/privacy
  - [ ] Last update: ___________

- [ ] **Terms of Service**
  - [ ] Include data processing terms
  - [ ] Available at: /legal/terms
  - [ ] Last update: ___________

- [ ] **Cookie Policy** (if website)
  - [ ] Document all cookies
  - [ ] Available at: /legal/cookies
  - [ ] Last update: ___________

- [ ] **Data Retention Policy**
  - [ ] Document retention periods
  - [ ] Deletion procedures
  - [ ] Archive requirements

- [ ] **Incident Response Plan**
  - [ ] 72-hour breach notification
  - [ ] Contact procedures
  - [ ] Documentation requirements

### Regular Reviews

- [ ] **Quarterly DPA Review**
  - Q1: ___________
  - Q2: ___________
  - Q3: ___________
  - Q4: ___________

- [ ] **Annual Privacy Audit**
  - Date: ___________
  - Auditor: ___________
  - Findings: ___________

- [ ] **Sub-processor Updates**
  - Check monthly
  - Document changes
  - Update privacy policy

---

## 🔒 Security Requirements

### Technical Measures

- [ ] **Encryption**
  - [ ] TLS 1.3 minimum
  - [ ] AES-256 at rest
  - [ ] Key rotation policy

- [ ] **Access Control**
  - [ ] MFA required
  - [ ] Role-based access
  - [ ] Regular access reviews

- [ ] **Monitoring**
  - [ ] Security logging
  - [ ] Anomaly detection
  - [ ] Regular audits

### Organizational Measures

- [ ] **Training**
  - [ ] Privacy training for team
  - [ ] Security best practices
  - [ ] Incident response drills

- [ ] **Policies**
  - [ ] Data classification
  - [ ] Acceptable use
  - [ ] Incident response

---

## 📱 App Store Compliance

### Apple App Store

- [ ] **App Privacy Details**
  - [ ] Data types declared
  - [ ] Purposes specified
  - [ ] Linked to user: No
  - [ ] Tracking: No

- [ ] **Required Labels**
  ```
  Contact Info: Not collected
  Health & Fitness: Search only
  Identifiers: Device ID (optional)
  Usage Data: Crash logs (opt-in)
  Diagnostics: Crash data (opt-in)
  ```

### Google Play Store

- [ ] **Data Safety Section**
  - [ ] Data collection declared
  - [ ] Encryption confirmed
  - [ ] Deletion available
  - [ ] No sharing

- [ ] **Required Declarations**
  ```
  Personal Info: Not collected
  App Activity: Product searches
  App Performance: Crash logs (opt-in)
  Device IDs: Installation ID
  ```

---

## ⚠️ Critical Requirements

1. **User Consent**
   - Explicit opt-in for Crashlytics
   - Clear privacy controls
   - Easy data deletion

2. **Data Minimization**
   - No email collection
   - No unnecessary data
   - Anonymous where possible

3. **Transparency**
   - Clear privacy policy
   - Accessible legal links
   - Regular updates

4. **Security**
   - Encryption everywhere
   - Regular security reviews
   - Incident response ready

---

## 📅 Important Dates

| Milestone | Due Date | Status |
|-----------|----------|---------|
| Initial DPA signing | _________ | ⬜ |
| Privacy policy update | _________ | ⬜ |
| App store submission | _________ | ⬜ |
| First audit | _________ | ⬜ |
| Annual review | _________ | ⬜ |

---

## 📞 Contacts

**Data Protection Officer:**
- Email: dpo@babyshield.app
- Response time: 72 hours

**Legal Team:**
- Email: legal@babyshield.app
- Response time: 5 business days

**Security Team:**
- Email: security@babyshield.app
- Incident hotline: [PHONE]

---

**Document Version:** 1.0.0  
**Last Review:** January 1, 2024  
**Next Review:** April 1, 2024
