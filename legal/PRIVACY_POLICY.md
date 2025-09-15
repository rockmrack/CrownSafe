# Privacy Policy

**Last Updated:** January 1, 2024  
**Effective Date:** January 1, 2024

## 1. Introduction

Welcome to BabyShield ("we," "our," or "us"). We are committed to protecting your privacy and ensuring the safety of your family's data. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our mobile application and services.

**Company Information:**
- **Company Name:** BabyShield Inc.
- **Address:** [YOUR COMPANY ADDRESS]
- **Email:** privacy@babyshield.app
- **Data Protection Officer:** dpo@babyshield.app

## 2. Information We Collect

### 2.1 Information You Provide Directly

We collect minimal information necessary to provide our services:

- **Account Information:** When you use OAuth (Sign in with Apple/Google), we store only:
  - Internal user ID (UUID)
  - OAuth provider identifier (encrypted)
  - Provider name (Apple or Google)
  - Account creation timestamp
  - **Note:** We do NOT store your email address

- **Product Scans:** When you scan barcodes:
  - Barcode data (UPC/EAN codes)
  - Scan timestamp
  - Search queries
  - **Note:** We do NOT store or access photos from your device

- **User Preferences:**
  - Language preference
  - Notification settings
  - Crashlytics opt-in status (OFF by default)

### 2.2 Information Collected Automatically

- **Device Information:**
  - Device type and model
  - Operating system version
  - App version
  - Device identifier (anonymized)
  - Time zone

- **Usage Data:**
  - Features used
  - Interaction with recalls
  - Search patterns
  - Performance metrics

- **Crash Reports** (ONLY if you opt-in):
  - Stack traces
  - Device state at crash time
  - **Note:** No personal information included

### 2.3 Information We Do NOT Collect

- Email addresses (unless explicitly provided for support)
- Phone numbers
- Physical addresses
- Payment information (handled by Apple/Google)
- Photos or camera roll access
- Contacts
- Location data
- Health records (beyond product safety queries)

## 3. How We Use Your Information

We use the collected information to:

1. **Provide Core Services:**
   - Match products with recall databases
   - Display safety information
   - Send critical safety alerts

2. **Improve Our Services:**
   - Analyze usage patterns
   - Fix bugs and crashes (with consent)
   - Optimize search algorithms

3. **Ensure Security:**
   - Prevent abuse and fraud
   - Enforce rate limits
   - Maintain service integrity

4. **Legal Compliance:**
   - Comply with applicable laws
   - Respond to legal requests
   - Protect rights and safety

## 4. Data Sharing and Disclosure

### 4.1 We Do NOT Sell Your Data
We never sell, rent, or trade your personal information.

### 4.2 Limited Sharing
We may share information only in these circumstances:

- **Service Providers:** 
  - AWS (hosting)
  - Google Cloud Vision (image analysis - no PII)
  - Firebase Crashlytics (crash reports - opt-in only)
  
- **Legal Requirements:**
  - Court orders
  - Government requests (with valid legal basis)
  - To protect safety

- **Business Transfers:**
  - In case of merger or acquisition (with notice)

### 4.3 Third-Party Data Processing

| Provider | Purpose | Data Shared | DPA Status |
|----------|---------|------------|------------|
| AWS | Hosting | All app data (encrypted) | ✅ Signed |
| Google Cloud | Image analysis | Product images only | ✅ Signed |
| Firebase | Crash reporting | Crash data (opt-in) | ✅ Signed |
| Apple/Google | Authentication | OAuth tokens only | ✅ Platform terms |

## 5. Data Security

We implement industry-standard security measures:

- **Encryption:** TLS 1.3 for data in transit
- **Storage:** AES-256 encryption at rest
- **Access Control:** Role-based access, MFA required
- **Monitoring:** 24/7 security monitoring
- **Compliance:** SOC 2 Type II (in progress)

## 6. Your Rights and Choices

### 6.1 Access and Portability
You can request a copy of your data at any time through:
- In-app: Settings → Privacy → Export My Data
- API: POST /api/v1/user/data/export

### 6.2 Deletion
You can delete your account and all associated data:
- In-app: Settings → Privacy → Delete My Account
- API: POST /api/v1/user/data/delete

### 6.3 Opt-Out Options
- **Crashlytics:** Settings → Crash Reporting (OFF by default)
- **Notifications:** Settings → Notifications
- **Account:** Delete account removes all data

### 6.4 Regional Rights

**California Residents (CCPA):**
- Right to know what data we collect
- Right to delete your data
- Right to opt-out of sale (we don't sell data)
- Right to non-discrimination

**EU/UK Residents (GDPR):**
- Right to access
- Right to rectification
- Right to erasure
- Right to data portability
- Right to object
- Right to restrict processing

## 7. Children's Privacy

BabyShield is designed for parents and caregivers. We do not knowingly collect information from children under 13. If you believe we have collected information from a child, please contact us immediately at privacy@babyshield.app.

## 8. Data Retention

We retain your data only as long as necessary:

- **Active accounts:** Until deletion requested
- **Inactive accounts:** Anonymized after 2 years
- **Crash reports:** 90 days
- **Search logs:** 30 days (anonymized)
- **Deleted accounts:** Permanently removed within 30 days

## 9. International Data Transfers

Your data may be transferred to and processed in:
- United States (primary)
- European Union (backup)

We ensure appropriate safeguards through:
- Standard Contractual Clauses (SCCs)
- Data Processing Agreements (DPAs)

## 10. Updates to This Policy

We may update this Privacy Policy. We will notify you of material changes via:
- In-app notification
- Email (if provided)
- App store update notes

## 11. Contact Us

For privacy questions or concerns:

**Email:** privacy@babyshield.app  
**Data Protection Officer:** dpo@babyshield.app  
**Mailing Address:**  
BabyShield Inc.  
[YOUR ADDRESS]  
Attn: Privacy Team

**Response Time:** Within 30 days

## 12. Cookie Policy

Our mobile app does not use cookies. Our website uses only essential cookies for:
- Session management
- Security (CSRF tokens)
- Load balancing

## 13. Supervisory Authority

EU residents may lodge complaints with their local supervisory authority.

---

**Document Version:** 1.0.0  
**Language:** English (translations available)  
**Jurisdiction:** [YOUR JURISDICTION]
