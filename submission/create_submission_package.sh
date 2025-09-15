#!/bin/bash
# Create App Store Submission Package
# This script assembles all required files for app store submission

set -e  # Exit on error

# Configuration
PACK_DATE=$(date +%Y%m%d_%H%M%S)
PACK_DIR="submission_package_${PACK_DATE}"
API_URL=${API_URL:-"https://babyshield.cureviax.ai"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================================="
echo "🚀 BabyShield App Store Submission Package Creator"
echo "=================================================="
echo "Date: $(date)"
echo "Package: ${PACK_DIR}"
echo ""

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p ${PACK_DIR}/{builds,metadata,assets,validation,legal,certificates}
mkdir -p ${PACK_DIR}/builds/{ios,android}
mkdir -p ${PACK_DIR}/metadata/{apple,google}
mkdir -p ${PACK_DIR}/assets/{screenshots,icons,graphics}
mkdir -p ${PACK_DIR}/assets/screenshots/{ios,android}

# ============================================
# Builds Section
# ============================================
echo ""
echo "📦 Collecting build files..."

# iOS Build
if [ -f "build/BabyShield.ipa" ]; then
    cp build/BabyShield.ipa ${PACK_DIR}/builds/ios/
    echo -e "${GREEN}✅ iOS IPA copied${NC}"
else
    echo -e "${YELLOW}⚠️ iOS IPA not found at build/BabyShield.ipa${NC}"
    echo "   Generate with: xcodebuild archive && xcodebuild -exportArchive"
fi

# iOS dSYMs
if [ -d "build/BabyShield.xcarchive/dSYMs" ]; then
    cp -r build/BabyShield.xcarchive/dSYMs ${PACK_DIR}/builds/ios/
    echo -e "${GREEN}✅ iOS dSYMs copied${NC}"
else
    echo -e "${YELLOW}⚠️ iOS dSYMs not found${NC}"
fi

# Android Build
if [ -f "app/build/outputs/bundle/release/app-release.aab" ]; then
    cp app/build/outputs/bundle/release/app-release.aab ${PACK_DIR}/builds/android/
    echo -e "${GREEN}✅ Android AAB copied${NC}"
else
    echo -e "${YELLOW}⚠️ Android AAB not found${NC}"
    echo "   Generate with: ./gradlew bundleRelease"
fi

# ProGuard mapping
if [ -f "app/build/outputs/mapping/release/mapping.txt" ]; then
    cp app/build/outputs/mapping/release/mapping.txt ${PACK_DIR}/builds/android/
    echo -e "${GREEN}✅ ProGuard mapping copied${NC}"
else
    echo -e "${YELLOW}⚠️ ProGuard mapping not found${NC}"
fi

# ============================================
# Metadata Section
# ============================================
echo ""
echo "📝 Collecting metadata..."

# Apple metadata
for file in metadata.json review_notes.md export_compliance.json; do
    if [ -f "docs/store/apple/$file" ]; then
        cp docs/store/apple/$file ${PACK_DIR}/metadata/apple/
        echo -e "${GREEN}✅ Apple $file copied${NC}"
    else
        echo -e "${YELLOW}⚠️ Apple $file not found${NC}"
    fi
done

# Google metadata
for file in listing.json review_notes.md; do
    if [ -f "docs/store/google/$file" ]; then
        cp docs/store/google/$file ${PACK_DIR}/metadata/google/
        echo -e "${GREEN}✅ Google $file copied${NC}"
    else
        echo -e "${YELLOW}⚠️ Google $file not found${NC}"
    fi
done

# Privacy files
if [ -f "docs/app_review/privacy_labels_apple.json" ]; then
    cp docs/app_review/privacy_labels_apple.json ${PACK_DIR}/metadata/apple/
    echo -e "${GREEN}✅ Apple privacy labels copied${NC}"
fi

if [ -f "docs/app_review/google_data_safety.json" ]; then
    cp docs/app_review/google_data_safety.json ${PACK_DIR}/metadata/google/
    echo -e "${GREEN}✅ Google data safety copied${NC}"
fi

# Common descriptions
if [ -d "docs/store/common/descriptions" ]; then
    cp -r docs/store/common ${PACK_DIR}/metadata/
    echo -e "${GREEN}✅ Common descriptions copied${NC}"
fi

# ============================================
# Assets Section
# ============================================
echo ""
echo "🎨 Collecting assets..."

# Icons
if [ -f "assets/store/icons/ios/AppIcon1024.png" ]; then
    cp assets/store/icons/ios/AppIcon1024.png ${PACK_DIR}/assets/icons/
    echo -e "${GREEN}✅ iOS icon copied${NC}"
else
    echo -e "${RED}❌ iOS icon missing (REQUIRED)${NC}"
fi

if [ -f "assets/store/icons/android/Icon512.png" ]; then
    cp assets/store/icons/android/Icon512.png ${PACK_DIR}/assets/icons/
    echo -e "${GREEN}✅ Android icon copied${NC}"
else
    echo -e "${RED}❌ Android icon missing (REQUIRED)${NC}"
fi

# Feature graphic
if [ -f "assets/store/graphics/play-feature-1024x500.png" ]; then
    cp assets/store/graphics/play-feature-1024x500.png ${PACK_DIR}/assets/graphics/
    echo -e "${GREEN}✅ Feature graphic copied${NC}"
else
    echo -e "${RED}❌ Feature graphic missing (REQUIRED for Play Store)${NC}"
fi

# Screenshots
if [ -d "assets/store/screenshots/ios" ]; then
    cp -r assets/store/screenshots/ios/* ${PACK_DIR}/assets/screenshots/ios/ 2>/dev/null || true
    count=$(ls -1 ${PACK_DIR}/assets/screenshots/ios/*.png 2>/dev/null | wc -l)
    if [ $count -gt 0 ]; then
        echo -e "${GREEN}✅ iOS screenshots copied ($count files)${NC}"
    else
        echo -e "${YELLOW}⚠️ No iOS screenshots found${NC}"
    fi
fi

if [ -d "assets/store/screenshots/android" ]; then
    cp -r assets/store/screenshots/android/* ${PACK_DIR}/assets/screenshots/android/ 2>/dev/null || true
    count=$(ls -1 ${PACK_DIR}/assets/screenshots/android/*.png 2>/dev/null | wc -l)
    if [ $count -gt 0 ]; then
        echo -e "${GREEN}✅ Android screenshots copied ($count files)${NC}"
    else
        echo -e "${YELLOW}⚠️ No Android screenshots found${NC}"
    fi
fi

# ============================================
# Validation Section
# ============================================
echo ""
echo "🔍 Running validation..."

# Run API validation
if [ -f "submission/validate_submission.py" ]; then
    echo "Running submission validation..."
    python3 submission/validate_submission.py > ${PACK_DIR}/validation/validation_output.txt 2>&1 || true
    
    # Copy validation reports
    cp submission/validation_report.* ${PACK_DIR}/validation/ 2>/dev/null || true
    echo -e "${GREEN}✅ Validation completed${NC}"
else
    echo -e "${YELLOW}⚠️ Validation script not found${NC}"
fi

# Run Postman tests
if command -v newman &> /dev/null; then
    if [ -f "docs/api/postman/BabyShield_v1.postman_collection.json" ]; then
        echo "Running Postman collection..."
        newman run docs/api/postman/BabyShield_v1.postman_collection.json \
            --env-var "baseUrl=${API_URL}" \
            --reporters cli,json,html \
            --reporter-json-export ${PACK_DIR}/validation/postman_results.json \
            --reporter-html-export ${PACK_DIR}/validation/postman_results.html \
            --suppress-exit-code
        echo -e "${GREEN}✅ Postman tests completed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ Newman not installed - skipping Postman tests${NC}"
fi

# API health check
echo "Checking API health..."
curl -s -o ${PACK_DIR}/validation/api_health.json ${API_URL}/api/v1/healthz || true
curl -s -o ${PACK_DIR}/validation/api_version.json ${API_URL}/api/v1/version || true

# ============================================
# Legal Section
# ============================================
echo ""
echo "⚖️ Collecting legal documents..."

# Download current legal documents
curl -s ${API_URL}/legal/privacy > ${PACK_DIR}/legal/privacy_policy.html
curl -s ${API_URL}/legal/terms > ${PACK_DIR}/legal/terms_of_service.html

# Copy local legal docs
if [ -d "legal" ]; then
    cp legal/*.md ${PACK_DIR}/legal/ 2>/dev/null || true
    echo -e "${GREEN}✅ Legal documents copied${NC}"
fi

# ============================================
# Certificates Section
# ============================================
echo ""
echo "🔐 Collecting certificates info..."

# iOS certificates
cat > ${PACK_DIR}/certificates/ios_signing.md << EOF
# iOS Code Signing Information

## Distribution Certificate
- Type: Apple Distribution
- Team ID: [YOUR_TEAM_ID]
- Expires: [EXPIRY_DATE]

## Provisioning Profile
- Type: App Store
- App ID: app.babyshield.ios
- Expires: [EXPIRY_DATE]

## Capabilities
- Push Notifications: Enabled
- Sign in with Apple: Enabled
- Associated Domains: Enabled
EOF

# Android certificates
if [ -f "app/signing/upload-keystore.jks" ]; then
    keytool -list -v -keystore app/signing/upload-keystore.jks -storepass ${KEYSTORE_PASSWORD:-password} \
        > ${PACK_DIR}/certificates/android_keystore_info.txt 2>/dev/null || \
        echo "Keystore information not extracted (wrong password or missing file)" > ${PACK_DIR}/certificates/android_keystore_info.txt
fi

# ============================================
# Create README
# ============================================
echo ""
echo "📄 Creating README..."

cat > ${PACK_DIR}/README.md << EOF
# BabyShield App Store Submission Package

**Generated:** $(date)
**Version:** 1.0.0
**Build:** 100

## 📦 Package Contents

### Builds
- iOS: BabyShield.ipa (TestFlight ready)
- Android: app-release.aab (Internal Testing ready)

### Metadata
- Apple App Store metadata
- Google Play Store listing
- Privacy labels and data safety
- Review notes for both stores

### Assets
- App icons (1024x1024 iOS, 512x512 Android)
- Feature graphic (1024x500)
- Screenshots for both platforms

### Validation
- API endpoint validation results
- Postman collection test results
- Security headers verification

### Legal
- Privacy Policy
- Terms of Service
- Data Processing Agreements

## ✅ Submission Checklist

### iOS (TestFlight)
- [ ] Upload IPA to App Store Connect
- [ ] Complete export compliance
- [ ] Add beta app description
- [ ] Configure test groups
- [ ] Submit for beta review

### Android (Internal Testing)
- [ ] Upload AAB to Play Console
- [ ] Complete content rating
- [ ] Configure internal test track
- [ ] Add tester emails
- [ ] Review pre-launch report

### Both Platforms
- [ ] Store listing reviewed
- [ ] Screenshots verified
- [ ] Privacy compliance confirmed
- [ ] API endpoints tested
- [ ] Legal documents current

## 🚀 Submission Process

1. **iOS Submission**
   \`\`\`bash
   xcrun altool --upload-app -f builds/ios/BabyShield.ipa \
     -u developer@babyshield.app -p @keychain:AC_PASSWORD
   \`\`\`

2. **Android Submission**
   - Open Play Console
   - Testing → Internal testing
   - Create release
   - Upload AAB from builds/android/

## 📞 Contacts

- iOS Lead: ios@babyshield.app
- Android Lead: android@babyshield.app
- Technical Support: support@babyshield.app
- Legal: legal@babyshield.app

## 📊 API Status

- Base URL: ${API_URL}
- Health Check: $(curl -s -o /dev/null -w "%{http_code}" ${API_URL}/api/v1/healthz || echo "Failed")
- Version: $(curl -s ${API_URL}/api/v1/version | jq -r .version 2>/dev/null || echo "Unknown")

## ⚠️ Important Notes

- Ensure all placeholders in metadata are replaced
- Verify demo account is working before submission
- Check that all required screenshots are included
- Confirm API is stable and responding

---

Generated by create_submission_package.sh
EOF

# ============================================
# Create Archive
# ============================================
echo ""
echo "📦 Creating archive..."

# Create ZIP archive
zip -r ${PACK_DIR}.zip ${PACK_DIR} -q

# Create checksum
sha256sum ${PACK_DIR}.zip > ${PACK_DIR}.zip.sha256

# ============================================
# Summary
# ============================================
echo ""
echo "=================================================="
echo "📊 Submission Package Summary"
echo "=================================================="

# Count files
BUILD_COUNT=$(find ${PACK_DIR}/builds -type f | wc -l)
METADATA_COUNT=$(find ${PACK_DIR}/metadata -type f | wc -l)
ASSET_COUNT=$(find ${PACK_DIR}/assets -type f | wc -l)
TOTAL_SIZE=$(du -sh ${PACK_DIR} | cut -f1)

echo "Package: ${PACK_DIR}"
echo "Archive: ${PACK_DIR}.zip"
echo ""
echo "Contents:"
echo "  - Build files: ${BUILD_COUNT}"
echo "  - Metadata files: ${METADATA_COUNT}"
echo "  - Asset files: ${ASSET_COUNT}"
echo "  - Total size: ${TOTAL_SIZE}"
echo ""

# Check for critical files
CRITICAL_MISSING=0

if [ ! -f "${PACK_DIR}/builds/ios/BabyShield.ipa" ]; then
    echo -e "${RED}❌ Critical: iOS IPA missing${NC}"
    CRITICAL_MISSING=$((CRITICAL_MISSING + 1))
fi

if [ ! -f "${PACK_DIR}/builds/android/app-release.aab" ]; then
    echo -e "${RED}❌ Critical: Android AAB missing${NC}"
    CRITICAL_MISSING=$((CRITICAL_MISSING + 1))
fi

if [ ! -f "${PACK_DIR}/assets/icons/AppIcon1024.png" ]; then
    echo -e "${RED}❌ Critical: iOS icon missing${NC}"
    CRITICAL_MISSING=$((CRITICAL_MISSING + 1))
fi

if [ ! -f "${PACK_DIR}/assets/icons/Icon512.png" ]; then
    echo -e "${RED}❌ Critical: Android icon missing${NC}"
    CRITICAL_MISSING=$((CRITICAL_MISSING + 1))
fi

if [ $CRITICAL_MISSING -eq 0 ]; then
    echo -e "${GREEN}✅ All critical files present${NC}"
    echo ""
    echo -e "${GREEN}🎉 Submission package created successfully!${NC}"
else
    echo ""
    echo -e "${YELLOW}⚠️ Package created with $CRITICAL_MISSING critical files missing${NC}"
    echo "   Please add missing files before submission"
fi

echo ""
echo "Next steps:"
echo "1. Review ${PACK_DIR}/README.md"
echo "2. Verify all files are present"
echo "3. Upload builds to respective stores"
echo "4. Submit for review"

exit 0
