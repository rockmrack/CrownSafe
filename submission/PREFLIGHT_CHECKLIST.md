# App Store Submission Preflight Checklist

## 🚀 Launch Readiness Assessment

**App Name:** BabyShield  
**Version:** 1.0.0  
**Build Number:** 100  
**Target Date:** _____________  
**Submission Lead:** _____________

---

## 📱 TestFlight (iOS) Configuration

### Build Preparation
- [ ] **Xcode Archive Created**
  - [ ] Release scheme selected
  - [ ] Archive validated
  - [ ] No compiler warnings
  - [ ] Bitcode enabled (optional)

- [ ] **Signing & Certificates**
  - [ ] Distribution certificate valid
  - [ ] Provisioning profile up to date
  - [ ] App ID configured correctly
  - [ ] Push notification entitlements (if used)
  - [ ] Sign in with Apple configured

- [ ] **App Store Connect Setup**
  - [ ] App created in App Store Connect
  - [ ] Bundle ID matches exactly
  - [ ] App information complete
  - [ ] Tax and banking configured
  - [ ] User roles assigned

### TestFlight Distribution
- [ ] **Build Upload**
  ```bash
  # Using Xcode
  Product → Archive → Distribute App → App Store Connect → Upload
  
  # Or using command line
  xcrun altool --upload-app -f BabyShield.ipa \
    -u developer@babyshield.app \
    -p @keychain:AC_PASSWORD \
    --type ios
  ```

- [ ] **TestFlight Configuration**
  - [ ] Build appears in TestFlight (wait 5-30 min)
  - [ ] Export compliance completed
  - [ ] Beta App Description added
  - [ ] Beta App Review submitted
  - [ ] Test groups created
  - [ ] Internal testers added (up to 100)
  - [ ] External testers invited (up to 10,000)

### TestFlight Test Information
```yaml
What to Test:
  - Product barcode scanning
  - Recall search functionality
  - Sign in with Apple
  - Push notifications
  - Offline mode
  - Privacy settings
  
Test Accounts:
  - Email: beta@babyshield.app
  - Password: (Provided separately)
  
Beta Feedback Email: feedback@babyshield.app
Marketing URL: https://babyshield.app
```

---

## 🤖 Google Play Internal Testing

### Build Preparation
- [ ] **Android App Bundle (AAB) Created**
  ```bash
  # Build release AAB
  ./gradlew bundleRelease
  
  # Or using Android Studio
  Build → Generate Signed Bundle → Android App Bundle
  ```

- [ ] **Signing Configuration**
  - [ ] Upload key generated
  - [ ] Play App Signing enrolled
  - [ ] Keystore backed up securely
  - [ ] SHA-1/SHA-256 fingerprints noted

- [ ] **Play Console Setup**
  - [ ] App created in Play Console
  - [ ] Package name matches exactly
  - [ ] Content rating questionnaire completed
  - [ ] App category selected
  - [ ] Target audience defined
  - [ ] Ads declaration completed

### Internal Testing Track
- [ ] **Release Management**
  - [ ] AAB uploaded to Internal Testing
  - [ ] Release notes provided
  - [ ] Version code incremented
  - [ ] Target SDK version current (33+)

- [ ] **Testing Configuration**
  - [ ] Internal testing track created
  - [ ] Testers list configured (up to 100)
  - [ ] Test link generated and shared
  - [ ] Feedback email configured
  - [ ] Pre-launch report reviewed

### Internal Testing Setup
```yaml
Track: Internal Testing
Testers: 
  - qa@babyshield.app
  - beta-team@babyshield.app
  
Test Duration: 7 days minimum
Feedback Channel: play-beta@babyshield.app
```

---

## 📝 Store Listing Review

### Apple App Store Listing

- [ ] **App Information**
  - [ ] App name: "BabyShield - Recall Alerts"
  - [ ] Subtitle: "Scan & Search Product Recalls" (30 chars)
  - [ ] Primary category: Health & Fitness
  - [ ] Secondary category: Medical
  - [ ] Age rating: 4+

- [ ] **Localized Information**
  - [ ] Description proofread (4000 chars max)
  - [ ] Keywords optimized (100 chars max)
  - [ ] What's New completed
  - [ ] Support URL active: https://babyshield.app/support
  - [ ] Privacy Policy URL: https://babyshield.app/privacy

- [ ] **Review Information**
  - [ ] Demo account provided
  - [ ] Review notes detailed
  - [ ] Contact information current
  - [ ] Attachment: API documentation

### Google Play Store Listing

- [ ] **Store Presence**
  - [ ] App name: "BabyShield - Product Safety"
  - [ ] Short description: Under 80 chars ✓
  - [ ] Full description: Under 4000 chars ✓
  - [ ] Recent changes documented

- [ ] **Store Listing Details**
  - [ ] App category: Health & Fitness
  - [ ] Content rating: Everyone
  - [ ] Email: support@babyshield.app
  - [ ] Website: https://babyshield.app
  - [ ] Privacy Policy: https://babyshield.app/privacy

- [ ] **Graphic Assets**
  - [ ] App icon: 512x512 PNG
  - [ ] Feature graphic: 1024x500 PNG
  - [ ] Phone screenshots: 2-8 images
  - [ ] Tablet screenshots: Optional
  - [ ] Promo video: Optional YouTube link

---

## 📸 Screenshots Finalization

### iOS Screenshots (Required Sizes)

- [ ] **iPhone 6.7" (1290 x 2796)**
  - [ ] 01_home_scan.png - Home screen with scan button
  - [ ] 02_barcode_scanning.png - Active barcode scanning
  - [ ] 03_recall_results.png - Recall search results
  - [ ] 04_recall_details.png - Detailed recall information
  - [ ] 05_safety_settings.png - Privacy and safety settings

- [ ] **iPhone 6.5" (1242 x 2688)** or **iPhone 5.5" (1242 x 2208)**
  - [ ] Same 5 screenshots as above
  - [ ] Properly sized for display

- [ ] **iPad 12.9" (2048 x 2732)** - Optional but recommended
  - [ ] 2-5 screenshots showing tablet layout

### Android Screenshots

- [ ] **Phone Screenshots (1080 x 1920 minimum)**
  - [ ] 01_home_screen.png - Main interface
  - [ ] 02_scanning.png - Barcode scanning feature
  - [ ] 03_search_results.png - Search functionality
  - [ ] 04_recall_info.png - Detailed information
  - [ ] 05_settings.png - App settings
  - [ ] 06_privacy.png - Privacy controls (recommended)
  - [ ] 07_notifications.png - Alert settings (optional)
  - [ ] 08_family.png - Family management (optional)

- [ ] **Tablet Screenshots (Optional)**
  - [ ] 7" tablet (600 x 1024)
  - [ ] 10" tablet (800 x 1280)

### Screenshot Requirements
- [ ] No status bar notifications visible
- [ ] No personal/test data shown
- [ ] Consistent device frames (if used)
- [ ] High-quality, non-compressed images
- [ ] Localized text where applicable
- [ ] Showcase key features prominently

---

## 🎨 Feature Graphic Verification

### Google Play Feature Graphic (1024 x 500)
- [ ] **Design Elements**
  - [ ] App name clearly visible
  - [ ] Key value proposition shown
  - [ ] Brand colors consistent
  - [ ] No embedded text in margins
  - [ ] Safe area respected (text/logo centered)

- [ ] **Technical Requirements**
  - [ ] Exactly 1024 x 500 pixels
  - [ ] PNG format, no transparency
  - [ ] File size under 1MB
  - [ ] sRGB color space
  - [ ] No rounded corners (system adds them)

---

## 🔍 API Validation Against Production

### Pre-Validation Setup
```bash
# Set production URL
export API_URL="https://babyshield.cureviax.ai"

# Verify API is accessible
curl -X GET "$API_URL/api/v1/healthz"
```

### Run Validation Script
```bash
# Execute comprehensive validation
python scripts/validate_store_readiness.py

# Expected output:
✅ Health check: 200 OK
✅ Version endpoint: 200 OK
✅ Search API: 200 OK
✅ Agencies list: 200 OK
✅ Privacy endpoint: 200 OK
✅ Security headers: Present
✅ Rate limiting: Active
✅ CORS configured: Yes
```

### Validation Report
- [ ] All endpoints responding (200 OK)
- [ ] Response times < 2 seconds
- [ ] Security headers present
- [ ] SSL certificate valid
- [ ] API version documented
- [ ] Rate limiting active
- [ ] Error handling working

---

## 📬 Postman Collection Testing

### Collection Execution
```bash
# Install Newman (Postman CLI)
npm install -g newman

# Run collection against production
newman run docs/api/postman/BabyShield_v1.postman_collection.json \
  --environment docs/api/postman/production.postman_environment.json \
  --reporters cli,json,html \
  --reporter-json-export postman_results.json \
  --reporter-html-export postman_results.html
```

### Test Results Requirements
- [ ] **All Tests Passing**
  - [ ] Authentication flows: PASS
  - [ ] Search endpoints: PASS
  - [ ] Recall details: PASS
  - [ ] Privacy endpoints: PASS
  - [ ] Error scenarios: PASS

- [ ] **Performance Metrics**
  - [ ] Average response time < 500ms
  - [ ] P95 response time < 2000ms
  - [ ] No timeout errors
  - [ ] No 5xx errors

### Export Test Results
```bash
# Generate submission report
cat > submission/api_test_report.md << EOF
# API Test Results
Date: $(date)
Environment: Production (https://babyshield.cureviax.ai)

## Summary
- Total Requests: XXX
- Passed: XXX
- Failed: 0
- Average Response Time: XXXms

## Endpoints Tested
[Attach newman report]
EOF
```

---

## 📦 Submission Package Assembly

### Required Files Structure
```
submission_pack_YYYYMMDD/
├── builds/
│   ├── ios/
│   │   ├── BabyShield_1.0.0_100.ipa
│   │   └── dSYMs/
│   └── android/
│       ├── app-release.aab
│       └── mapping.txt
├── metadata/
│   ├── apple/
│   │   ├── metadata.json
│   │   ├── review_notes.md
│   │   └── export_compliance.json
│   └── google/
│       ├── listing.json
│       ├── review_notes.md
│       └── data_safety.csv
├── assets/
│   ├── screenshots/
│   ├── icons/
│   └── graphics/
├── validation/
│   ├── api_validation_results.json
│   ├── postman_results.html
│   ├── security_scan_results.pdf
│   └── preflight_checklist_signed.pdf
├── legal/
│   ├── privacy_policy.html
│   ├── terms_of_service.html
│   └── dpa_checklist_complete.pdf
└── README.md
```

### Package Creation Script
```bash
#!/bin/bash
# create_submission_pack.sh

PACK_DATE=$(date +%Y%m%d)
PACK_DIR="submission_pack_${PACK_DATE}"

echo "Creating submission package: ${PACK_DIR}"

# Create directory structure
mkdir -p ${PACK_DIR}/{builds,metadata,assets,validation,legal}
mkdir -p ${PACK_DIR}/builds/{ios,android}
mkdir -p ${PACK_DIR}/metadata/{apple,google}
mkdir -p ${PACK_DIR}/assets/{screenshots,icons,graphics}

# Copy builds
cp path/to/BabyShield.ipa ${PACK_DIR}/builds/ios/
cp path/to/app-release.aab ${PACK_DIR}/builds/android/

# Copy metadata
cp -r docs/store/* ${PACK_DIR}/metadata/

# Copy assets
cp -r assets/store/* ${PACK_DIR}/assets/

# Copy validation results
cp validation/*.{json,html,pdf} ${PACK_DIR}/validation/

# Copy legal documents
cp legal/*.{html,pdf} ${PACK_DIR}/legal/

# Create README
cat > ${PACK_DIR}/README.md << EOF
# BabyShield Submission Package
Date: ${PACK_DATE}
Version: 1.0.0 (Build 100)

## Contents
- iOS build (TestFlight ready)
- Android build (Internal testing ready)
- Complete store metadata
- All required assets
- API validation results
- Legal documentation

## Submission Checklist
- [ ] TestFlight build uploaded
- [ ] Play Console build uploaded
- [ ] Store listings reviewed
- [ ] Screenshots verified
- [ ] API tests passing
- [ ] Legal docs current
EOF

# Create archive
zip -r ${PACK_DIR}.zip ${PACK_DIR}/

echo "✅ Submission package created: ${PACK_DIR}.zip"
```

---

## ✅ Final Preflight Verification

### Technical Requirements
- [ ] **iOS Requirements Met**
  - [ ] iOS 13.0+ minimum
  - [ ] Universal app (iPhone + iPad)
  - [ ] 64-bit support
  - [ ] IPv6 compatible
  - [ ] No deprecated APIs

- [ ] **Android Requirements Met**
  - [ ] API level 23+ (Android 6.0)
  - [ ] Target SDK 33+ (Android 13)
  - [ ] 64-bit support
  - [ ] Android App Bundle format
  - [ ] R8/ProGuard configured

### Content & Legal
- [ ] **Privacy Compliance**
  - [ ] Privacy policy accessible
  - [ ] Data deletion available
  - [ ] Consent mechanisms working
  - [ ] COPPA compliant (no child data)
  - [ ] GDPR/CCPA compliant

- [ ] **Content Guidelines**
  - [ ] No misleading claims
  - [ ] Medical disclaimer included
  - [ ] Appropriate age rating
  - [ ] No prohibited content
  - [ ] Accurate app description

### Pre-Submission Testing
- [ ] **Functional Testing**
  - [ ] Fresh install works
  - [ ] Upgrade from previous version works
  - [ ] All features functional
  - [ ] Offline mode works
  - [ ] Push notifications work
  - [ ] Deep links work

- [ ] **Device Testing**
  - [ ] Latest iOS version
  - [ ] Oldest supported iOS version
  - [ ] Latest Android version
  - [ ] Oldest supported Android version
  - [ ] Various screen sizes
  - [ ] Tablet layouts (if applicable)

---

## 🚨 Common Rejection Reasons to Avoid

### Apple App Store
- ❌ Crashes or bugs during review
- ❌ Incomplete or placeholder content
- ❌ Misleading app description
- ❌ Privacy policy issues
- ❌ Sign in with Apple not implemented correctly
- ❌ Requesting unnecessary permissions
- ❌ Not following Human Interface Guidelines

### Google Play Store
- ❌ Policy violations (health claims)
- ❌ Missing privacy policy
- ❌ Incorrect data safety declarations
- ❌ Crashes or ANRs
- ❌ Inappropriate content rating
- ❌ Misleading app description
- ❌ Excessive permissions

---

## 📞 Submission Contacts

**iOS Submission Lead:** _____________  
**Android Submission Lead:** _____________  
**Technical Contact:** _____________  
**Legal Contact:** _____________  
**Marketing Contact:** _____________  

---

## 🎯 Go/No-Go Decision

### Approval Gates
- [ ] Technical Lead Approval: _________ Date: _______
- [ ] Legal Review Complete: _________ Date: _______
- [ ] Marketing Sign-off: _________ Date: _______
- [ ] Executive Approval: _________ Date: _______

### Final Submission
- [ ] **iOS Submission**
  - Date Submitted: _____________
  - Submitted By: _____________
  - Tracking ID: _____________

- [ ] **Android Submission**
  - Date Submitted: _____________
  - Submitted By: _____________
  - Tracking ID: _____________

---

## 📋 Post-Submission Monitoring

- [ ] Monitor review status daily
- [ ] Respond to reviewer feedback within 24 hours
- [ ] Prepare hotfix process if needed
- [ ] Plan launch announcement
- [ ] Monitor crash reports
- [ ] Track user feedback

---

**Checklist Version:** 1.0.0  
**Last Updated:** January 2024  
**Next Review:** Before each major release
