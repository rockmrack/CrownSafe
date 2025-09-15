# BabyShield Backend API Endpoints Documentation
## Complete List for Frontend Development

Last Updated: January 9, 2025

---

## 🌐 Environment Configuration

### Domain Architecture
- **API Domain**: `.ai` - All API endpoints (`babyshield.cureviax.ai`)
- **Website Domain**: `.com` - Web pages, email links (`babyshield.cureviax.com`)

### Environment URLs

#### Production
- API Base URL: `https://babyshield.cureviax.ai`
- WebSocket URL: `wss://babyshield.cureviax.ai/ws`
- Website URL: `https://babyshield.cureviax.com`

#### Staging
- API Base URL: `https://staging.babyshield.cureviax.ai`
- WebSocket URL: `wss://staging.babyshield.cureviax.ai/ws`
- Website URL: `https://www.babyshield.cureviax.com` (if available)

#### Development
- API Base URL: `http://localhost:8001`
- WebSocket URL: `ws://localhost:8001/ws`

### Email Configuration
- Support Email: `support@babyshield.cureviax.com`
- Email Domain: Always `@babyshield.cureviax.com`
- Email Links: Always point to `.com` domain pages

### CORS Configuration
Backend allows requests from:
- `https://babyshield.cureviax.com`
- `https://staging.babyshield.cureviax.com`

---

## 🔐 Authentication & User Management

### Authentication (`/api/v1/auth`)
- **POST** `/api/v1/auth/register` - Register new user account
- **POST** `/api/v1/auth/token` - Login and get access token
- **POST** `/api/v1/auth/refresh` - Refresh access token
- **GET** `/api/v1/auth/me` - Get current user profile
- **PUT** `/api/v1/auth/me` - Update user profile
- **POST** `/api/v1/auth/logout` - Logout user
- **POST** `/api/v1/auth/password-reset` - Request password reset (deprecated)
- **POST** `/api/v1/auth/password-reset/confirm` - Confirm password reset (deprecated)
- **GET** `/api/v1/auth/verify` - Verify email/account

### Password Reset (`/api/v1/auth`)
- **POST** `/api/v1/auth/password-reset/request` - Request password reset email
- **POST** `/api/v1/auth/password-reset/confirm` - Confirm reset with new password
- **POST** `/api/v1/auth/password-reset/validate` - Validate reset token

### OAuth (`/api/v1/oauth`)
- **POST** `/api/v1/oauth/login` - OAuth login (Google/Apple)
- **POST** `/api/v1/oauth/logout` - OAuth logout
- **POST** `/api/v1/oauth/revoke` - Revoke OAuth token
- **GET** `/api/v1/oauth/providers` - Get available OAuth providers

---

## 📱 Core Product Safety Features

### Main Safety Check
- **POST** `/api/v1/safety-check` - Comprehensive product safety check (main endpoint)

### Barcode Scanning (`/api/v1/scan`)
- **POST** `/api/v1/scan/barcode` - Scan standard barcode (EAN/UPC)
- **POST** `/api/v1/scan/image` - Extract barcode from image
- **POST** `/api/v1/scan/qr` - Scan QR code
- **POST** `/api/v1/scan/datamatrix` - Scan DataMatrix code
- **POST** `/api/v1/scan/gs1` - Scan GS1 barcode with lot/serial
- **POST** `/api/v1/scan/verify` - Verify product authenticity
- **POST** `/api/v1/scan/generate-qr` - Generate QR code

### Mobile Scanning (`/api/v1/mobile`)
- **POST** `/api/v1/mobile/scan` - Mobile-optimized product scan
- **POST** `/api/v1/mobile/scan/results` - Get formatted scan results page
- **GET** `/api/v1/mobile/instant-check/{barcode}` - Quick barcode check
- **GET** `/api/v1/mobile/quick-check/{barcode}` - Alternative quick check
- **GET** `/mobile/stats` - Mobile app usage statistics

### Visual Recognition (`/api/v1/visual`)
- **POST** `/api/v1/visual/upload` - Upload image for processing
- **POST** `/api/v1/visual/analyze` - Analyze uploaded image
- **GET** `/api/v1/visual/status/{job_id}` - Check processing status
- **POST** `/api/v1/visual/mfv/confirm` - Confirm manual verification
- **GET** `/api/v1/visual/review/queue` - Get review queue
- **POST** `/api/v1/visual/review/{review_id}/claim` - Claim review task
- **POST** `/api/v1/visual/review/{review_id}/resolve` - Resolve review
- **POST** `/api/v1/visual/suggest-product` - AI-powered product suggestion from image

### Enhanced Barcode Bridge (`/api/v1/barcode`)
- **POST** `/api/v1/barcode/scan` - Enhanced barcode scanning with caching
- **GET** `/api/v1/barcode/cache/status` - Check cache status
- **DELETE** `/api/v1/barcode/cache/clear` - Clear barcode cache
- **GET** `/api/v1/barcode/test/barcodes` - Get test barcodes

---

## 🔍 Search & Discovery

### Product Search
- **POST** `/api/v1/search/advanced` - Advanced product search
- **POST** `/api/v1/search/bulk` - Bulk product search
- **GET** `/api/v1/autocomplete/products` - Product name autocomplete
- **GET** `/api/v1/autocomplete/brands` - Brand name autocomplete

### Agency Data (`/api/v1`)
- **GET** `/api/v1/agencies` - List all safety agencies
- **GET** `/api/v1/fda` - Search FDA database
- **GET** `/api/v1/cpsc` - Search CPSC database
- **GET** `/api/v1/eu_safety_gate` - Search EU Safety Gate
- **GET** `/api/v1/uk_opss` - Search UK OPSS database

### Recall Details
- **GET** `/api/v1/recall/{recall_id}` - Get specific recall details

---

## 👶 Baby Safety Features (`/api/v1/baby`)

### Product Alternatives
- **POST** `/api/v1/baby/alternatives` - Find safer product alternatives

### Safety Analysis
- **POST** `/api/v1/baby/hazards/analyze` - Analyze product hazards
- **GET** `/api/v1/baby/community/alerts` - Get community safety alerts

### Onboarding
- **POST** `/api/v1/baby/onboarding/setup` - Setup user preferences

### Reports
- **POST** `/api/v1/baby/reports/generate` - Generate safety report
- **GET** `/api/v1/baby/reports/download/{report_id}` - Download report PDF
- **HEAD** `/api/v1/baby/reports/download/{report_id}` - Check report availability

### Notifications
- **POST** `/api/v1/baby/notifications/send` - Send push notification
- **POST** `/api/v1/baby/notifications/bulk` - Send bulk notifications

---

## 📊 User Dashboard (`/api/v1/dashboard`)

- **GET** `/api/v1/dashboard/overview` - Dashboard overview stats
- **GET** `/api/v1/dashboard/activity` - Recent user activity
- **GET** `/api/v1/dashboard/product-categories` - Product category breakdown
- **GET** `/api/v1/dashboard/safety-insights` - Safety insights and tips
- **GET** `/api/v1/dashboard/recent-recalls` - Recent recalls affecting user
- **GET** `/api/v1/dashboard/achievements` - User achievements/badges

---

## 📜 Scan History (`/api/v1/user`)

- **GET** `/api/v1/user/scan-history` - Get user's scan history
- **GET** `/api/v1/user/scan-history/{job_id}` - Get specific scan details
- **DELETE** `/api/v1/user/scan-history/{job_id}` - Delete scan from history
- **GET** `/api/v1/user/scan-statistics` - Get scan statistics

---

## 🔔 Notifications (`/api/v1/notifications`)

### Device Management
- **POST** `/api/v1/notifications/device/register` - Register device for push
- **DELETE** `/api/v1/notifications/device/{token}` - Unregister device
- **GET** `/api/v1/notifications/devices` - List registered devices

### Notification Management
- **GET** `/api/v1/notifications/history` - Get notification history
- **POST** `/api/v1/notifications/mark-read/{notification_id}` - Mark as read
- **POST** `/api/v1/notifications/mark-all-read` - Mark all as read
- **PUT** `/api/v1/notifications/preferences` - Update preferences
- **POST** `/api/v1/notifications/test` - Send test notification
- **GET** `/api/v1/notifications/{notification_id}` - Get specific notification
- **POST** `/api/v1/notifications/setup` - Setup notifications

---

## 🚨 Recall Alerts (`/api/v1/recall-alerts`)

- **POST** `/api/v1/recall-alerts/test-alert` - Send test recall alert
- **GET** `/api/v1/recall-alerts/check-now` - Manually check for recalls
- **POST** `/api/v1/recall-alerts/preferences` - Update alert preferences
- **GET** `/api/v1/recall-alerts/history/{user_id}` - Get alert history

---

## 📈 Product Monitoring (`/api/v1/monitoring`)

- **POST** `/api/v1/monitoring/products/add` - Add product to monitoring
- **GET** `/api/v1/monitoring/products` - List monitored products
- **DELETE** `/api/v1/monitoring/products/{product_id}` - Remove from monitoring
- **PUT** `/api/v1/monitoring/products/{product_id}/frequency` - Update check frequency
- **POST** `/api/v1/monitoring/products/{product_id}/check-now` - Check product now
- **POST** `/api/v1/monitoring/auto-add-scans` - Auto-add scanned products
- **GET** `/api/v1/monitoring/status` - Get monitoring status
- **GET** `/api/v1/monitoring/agencies` - Get agency monitoring status
- **GET** `/api/v1/monitoring/system` - Get system monitoring metrics

---

## 💎 Premium Features (`/api/v1/premium`)

### Pregnancy Safety
- **POST** `/api/v1/premium/pregnancy/check` - Check product safety for pregnancy

### Allergy Management
- **POST** `/api/v1/premium/allergy/check` - Check for allergens

### Family Management
- **GET** `/api/v1/premium/family/members` - List family members
- **POST** `/api/v1/premium/family/members` - Add family member
- **PUT** `/api/v1/premium/family/members/{member_id}` - Update family member
- **DELETE** `/api/v1/premium/family/members/{member_id}` - Remove family member

### Comprehensive Safety
- **POST** `/api/v1/premium/safety/comprehensive` - Full safety analysis

---

## 🔬 Advanced Features (`/api/v1/advanced`)

- **POST** `/api/v1/advanced/research` - Web research on product
- **POST** `/api/v1/advanced/guidelines` - Get safety guidelines
- **POST** `/api/v1/advanced/visual/recognize` - Visual product recognition
- **POST** `/api/v1/advanced/monitor/setup` - Setup advanced monitoring
- **GET** `/api/v1/advanced/monitor/{monitoring_id}/status` - Check monitor status
- **DELETE** `/api/v1/advanced/monitor/{monitoring_id}` - Delete monitor

---

## 💳 Subscriptions (`/api/v1/subscriptions`)

- **POST** `/api/v1/subscriptions/activate` - Activate subscription
- **GET** `/api/v1/subscriptions/status` - Get subscription status
- **GET** `/api/v1/subscriptions/entitlement` - Get entitlements
- **POST** `/api/v1/subscriptions/cancel` - Cancel subscription
- **GET** `/api/v1/subscriptions/history` - Get subscription history
- **GET** `/api/v1/subscriptions/products` - Get available products
- **GET** `/api/v1/subscriptions/admin/metrics` - Admin metrics (internal)
- **POST** `/api/v1/subscriptions/admin/cleanup` - Admin cleanup (internal)

---

## 📊 Analytics & Insights

- **GET** `/api/v1/analytics/recalls` - Recall analytics
- **GET** `/api/v1/analytics/counts` - Various count statistics

---

## 🏥 Safety Hub

- **GET** `/api/v1/safety-hub/articles` - Get featured safety articles

---

## 📝 Safety Reports (`/api/v1/safety-reports`)

- **POST** `/api/v1/safety-reports/generate-90-day` - Generate 90-day summary
- **POST** `/api/v1/safety-reports/generate-quarterly-nursery` - Generate nursery audit
- **GET** `/api/v1/safety-reports/my-reports` - List user's reports
- **GET** `/api/v1/safety-reports/report/{report_id}` - Get specific report
- **POST** `/api/v1/safety-reports/track-scan` - Track scan for reports

---

## 🔗 Share Results (`/api/v1/share`)

- **POST** `/api/v1/share/create` - Create shareable link
- **GET** `/api/v1/share/view/{token}` - View shared result
- **POST** `/api/v1/share/email` - Share via email
- **DELETE** `/api/v1/share/revoke/{token}` - Revoke share link
- **GET** `/api/v1/share/my-shares` - List user's shares
- **GET** `/api/v1/share/qr/{token}` - Get QR code for share
- **GET** `/api/v1/share/preview/{token}` - Preview share content

---

## 🚨 Incident Reporting (`/api/v1/incidents`)

- **POST** `/api/v1/incidents/submit` - Submit incident report
- **GET** `/api/v1/incidents/clusters` - View incident clusters
- **GET** `/api/v1/incidents/stats` - Get incident statistics
- **GET** `/api/v1/incidents/report-page` - Get report form HTML
- **GET** `/report-incident` - Direct access to incident report page

---

## 🔒 Privacy & Data Management (`/api/v1/user/data`)

- **POST** `/api/v1/user/data/export` - Request data export (GDPR)
- **POST** `/api/v1/user/data/delete` - Request data deletion
- **GET** `/api/v1/user/data/export/status/{request_id}` - Check export status
- **GET** `/api/v1/user/data/delete/status/{request_id}` - Check deletion status
- **GET** `/api/v1/user/data/download/{request_id}` - Download exported data

---

## ⚖️ Legal & Compliance (`/api/v1/compliance`)

### COPPA Compliance
- **POST** `/api/v1/compliance/coppa/verify-age` - Age verification
- **POST** `/api/v1/compliance/coppa/parental-consent` - Parental consent
- **GET** `/api/v1/compliance/coppa/consent-status/{user_id}` - Consent status

### Children's Code
- **POST** `/api/v1/compliance/childrens-code/assess` - Assess compliance

### GDPR
- **POST** `/api/v1/compliance/gdpr/data-request` - GDPR data request
- **GET** `/api/v1/compliance/gdpr/request-status/{request_id}` - Request status
- **POST** `/api/v1/compliance/gdpr/retention-policy` - Retention policy

### Legal Documents
- **POST** `/api/v1/compliance/legal/document` - Generate legal document
- **POST** `/api/v1/compliance/legal/consent/update` - Update consent
- **GET** `/api/v1/compliance/privacy/dashboard/{user_id}` - Privacy dashboard

---

## 📋 Feedback & Support (`/api/v1/feedback`)

- **POST** `/api/v1/feedback/submit` - Submit feedback
- **GET** `/api/v1/feedback/ticket/{ticket_number}` - Get ticket status
- **POST** `/api/v1/feedback/ticket/{ticket_number}/satisfy` - Rate satisfaction
- **GET** `/api/v1/feedback/categories` - Get feedback categories
- **GET** `/api/v1/feedback/health` - Support system health
- **GET** `/api/v1/feedback/admin/stats` - Admin statistics
- **POST** `/api/v1/feedback/admin/bulk_update` - Bulk update tickets

---

## 🌍 Localization (`/api/v1/i18n`)

- **GET** `/api/v1/i18n/languages` - Get supported languages
- **GET** `/api/v1/i18n/translations/{lang}` - Get translations
- **PUT** `/api/v1/i18n/user-language` - Set user language

---

## 📊 Risk Assessment (`/api/v1/risk`)

- **POST** `/api/v1/risk/assess` - Assess product risk
- **GET** `/api/v1/risk/stats` - Risk statistics

---

## 🏥 Health & System Status

### Health Checks
- **GET** `/health` - Basic health check
- **GET** `/healthz` - Kubernetes health probe
- **GET** `/readyz` - Readiness probe
- **GET** `/api/v1/monitoring/healthz` - Detailed health
- **GET** `/api/v1/monitoring/readyz` - Detailed readiness
- **GET** `/api/v1/monitoring/livez` - Liveness probe

### System Monitoring
- **GET** `/api/v1/monitoring/slo` - Service level objectives
- **GET** `/api/v1/monitoring/probe/{probe_name}` - Specific probe
- **GET** `/api/v1/monitoring/probe` - All probes

---

## 🛠️ System & Admin

### Cache Management
- **GET** `/cache/stats` - Cache statistics
- **POST** `/cache/warm` - Warm up cache

### System Operations
- **GET** `/` - Root endpoint
- **GET** `/test` - Test endpoint
- **GET** `/openapi.json` - OpenAPI specification
- **POST** `/system/fix-upc-data` - Fix UPC data (admin)

### Admin Privacy (`/api/v1/admin/privacy`)
- **GET** `/api/v1/admin/privacy/requests` - List privacy requests
- **GET** `/api/v1/admin/privacy/requests/{request_id}` - Get request details
- **PATCH** `/api/v1/admin/privacy/requests/{request_id}` - Update request
- **GET** `/api/v1/admin/privacy/statistics` - Privacy statistics
- **POST** `/api/v1/admin/privacy/requests/{request_id}/process` - Process request
- **GET** `/api/v1/admin/privacy/export-template` - Export template

### Admin Ingestion (`/api/v1/admin`)
- **POST** `/api/v1/admin/ingest` - Trigger data ingestion
- **GET** `/api/v1/admin/runs` - List ingestion runs
- **GET** `/api/v1/admin/runs/{run_id}` - Get run details
- **DELETE** `/api/v1/admin/runs/{run_id}/cancel` - Cancel run
- **POST** `/api/v1/admin/reindex` - Reindex data
- **GET** `/api/v1/admin/freshness` - Check data freshness
- **GET** `/api/v1/admin/stats` - Admin statistics

---

## 📝 Additional Privacy Routes (`/api/v1/privacy`)

- **POST** `/api/v1/privacy/data/export` - Export personal data
- **POST** `/api/v1/privacy/data/delete` - Delete personal data
- **GET** `/api/v1/privacy/privacy/summary` - Privacy summary
- **POST** `/api/v1/privacy/privacy/verify/{token}` - Verify privacy token
- **GET** `/api/v1/privacy/privacy/status/{request_id}` - Request status
- **POST** `/api/v1/privacy/data/rectify` - Rectify data
- **POST** `/api/v1/privacy/data/restrict` - Restrict processing
- **POST** `/api/v1/privacy/data/object` - Object to processing

---

## 🔧 Settings (`/api/v1/settings`)

- **GET** `/api/v1/settings/preferences` - Get user preferences
- **PUT** `/api/v1/settings/preferences` - Update preferences
- **GET** `/api/v1/settings/notifications` - Get notification settings
- **PUT** `/api/v1/settings/notifications` - Update notification settings

---

## 📱 V2 API Endpoints (Future/Beta)

- **POST** `/api/v2/search/advanced` - Advanced search v2
- **GET** `/api/v2/recall/{recall_id}` - Recall details v2

---

## Notes for Frontend Developer:

1. **Authentication**: Most endpoints require Bearer token in Authorization header
   ```
   Authorization: Bearer <access_token>
   ```

2. **Response Format**: All endpoints return standardized JSON:
   ```json
   {
     "success": true/false,
     "data": {...},
     "error": {...},
     "message": "..."
   }
   ```

3. **Rate Limiting**: Most endpoints have rate limits (varies by endpoint)

4. **Base URL** (API Endpoints): 
   - Production: `https://babyshield.cureviax.ai`
   - Staging: `https://staging.babyshield.cureviax.ai`
   - Development: `http://localhost:8001`

5. **File Uploads**: Use multipart/form-data for image uploads

6. **Pagination**: List endpoints support `?page=1&limit=20` parameters

7. **Error Codes**:
   - 400: Bad Request
   - 401: Unauthorized
   - 403: Forbidden
   - 404: Not Found
   - 429: Rate Limited
   - 500: Server Error

8. **WebSocket**: Real-time updates at `wss://babyshield.cureviax.ai/ws`

9. **API Version**: Current stable version is v1, v2 endpoints are beta

10. **Required Headers**:
    - `Content-Type: application/json` (for JSON payloads)
    - `X-App-Version: <app_version>` (recommended)
    - `X-Device-ID: <device_id>` (for mobile apps)

---

## Contact & Resources

For API issues or questions:
- Support Email: support@babyshield.cureviax.com
- Slack: #api-support
- Website: https://babyshield.cureviax.com
- API Documentation: https://babyshield.cureviax.ai/docs
- OpenAPI Spec: https://babyshield.cureviax.ai/openapi.json

## Important Domain Separation

- **API Endpoints**: All API calls use `.ai` domain (`https://babyshield.cureviax.ai`)
- **Website & Email**: All web pages and email links use `.com` domain (`https://babyshield.cureviax.com`)
- **Support Emails**: Always sent from `@babyshield.cureviax.com`

---

Last verified: January 9, 2025
Total endpoints: 213+
