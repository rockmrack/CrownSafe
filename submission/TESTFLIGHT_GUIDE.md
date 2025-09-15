# TestFlight Setup & Distribution Guide

## 📱 iOS Beta Testing with TestFlight

### Prerequisites
- [ ] Apple Developer Account ($99/year)
- [ ] App Store Connect access
- [ ] Xcode 14+ installed
- [ ] Valid distribution certificate
- [ ] App-specific password for CI/CD

---

## 🔨 Build Configuration

### 1. Xcode Project Settings

```yaml
Build Settings:
  Bundle Identifier: app.babyshield.ios
  Version: 1.0.0
  Build: 100
  
Deployment Target: iOS 13.0
Device Family: iPhone, iPad
  
Capabilities:
  - Push Notifications
  - Sign in with Apple
  - Background Modes (Remote notifications)
  
Code Signing:
  Team: [Your Team ID]
  Provisioning Profile: Automatic
  Code Signing Identity: Apple Distribution
```

### 2. Archive Creation

```bash
# Clean build folder
xcodebuild clean -project BabyShield.xcodeproj -scheme BabyShield

# Create archive
xcodebuild archive \
  -project BabyShield.xcodeproj \
  -scheme BabyShield \
  -configuration Release \
  -archivePath build/BabyShield.xcarchive

# Export IPA
xcodebuild -exportArchive \
  -archivePath build/BabyShield.xcarchive \
  -exportPath build/ipa \
  -exportOptionsPlist ExportOptions.plist
```

### 3. ExportOptions.plist

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>method</key>
    <string>app-store</string>
    <key>teamID</key>
    <string>[YOUR_TEAM_ID]</string>
    <key>uploadBitcode</key>
    <true/>
    <key>compileBitcode</key>
    <false/>
    <key>uploadSymbols</key>
    <true/>
    <key>signingStyle</key>
    <string>automatic</string>
</dict>
</plist>
```

---

## 📤 Upload to App Store Connect

### Method 1: Xcode Upload
1. Open Xcode
2. Window → Organizer
3. Select your archive
4. Click "Distribute App"
5. Choose "App Store Connect"
6. Upload

### Method 2: Command Line (xcrun)

```bash
# Validate first
xcrun altool --validate-app \
  -f build/ipa/BabyShield.ipa \
  -u developer@babyshield.app \
  -p @keychain:AC_PASSWORD \
  --type ios

# Upload
xcrun altool --upload-app \
  -f build/ipa/BabyShield.ipa \
  -u developer@babyshield.app \
  -p @keychain:AC_PASSWORD \
  --type ios
```

### Method 3: Transporter App
1. Download Transporter from Mac App Store
2. Sign in with Apple ID
3. Drag IPA file to Transporter
4. Click "Deliver"

---

## ⚙️ TestFlight Configuration

### 1. App Information

```yaml
Beta App Information:
  App Name: BabyShield Beta
  
  Description: |
    Welcome to BabyShield Beta!
    
    Help us test the latest features:
    • Enhanced barcode scanning
    • Faster recall search
    • Improved offline mode
    • New privacy controls
    
    Please report any issues via the feedback button.
  
  Feedback Email: beta@babyshield.app
  Marketing URL: https://babyshield.app/beta
```

### 2. Build Configuration

```yaml
Build Settings:
  Export Compliance:
    Uses Encryption: Yes
    Exempt: Yes (HTTPS only)
    
  Beta App Review:
    Sign-in Required: Optional
    Demo Account:
      Email: demo@babyshield.app
      Password: DemoPass123!
    
  Localizations:
    - English (US) - Primary
    - Spanish (ES) - Optional
```

### 3. Test Groups Setup

#### Internal Testing (Up to 100 testers)
```yaml
Group Name: Internal Team
Testers:
  - dev@babyshield.app
  - qa@babyshield.app
  - product@babyshield.app
  
Auto-deploy: Latest build
Feedback: Enabled
```

#### External Testing (Up to 10,000 testers)
```yaml
Group Name: Beta Users
  
Distribution:
  - Public Link: Enabled
  - Link Limit: 1000 testers
  - Expiration: 90 days
  
Requirements:
  - iOS 13.0+
  - All device types
  
Review Status: Required (first build only)
```

---

## 👥 Tester Management

### Adding Internal Testers
1. App Store Connect → Users and Access
2. Add user with "Developer" or "App Manager" role
3. TestFlight → Internal Group → Add Testers

### Adding External Testers

#### Option 1: Email Invitation
```csv
# testers.csv
First Name,Last Name,Email
John,Doe,john@example.com
Jane,Smith,jane@example.com
```

#### Option 2: Public Link
```
https://testflight.apple.com/join/[UNIQUE_CODE]
```

Share via:
- Email campaigns
- Social media
- Website
- QR code

### Tester Communication Template

```markdown
Subject: You're Invited to Test BabyShield Beta!

Hi [Name],

You've been selected to test the latest version of BabyShield before its official release!

**How to Join:**
1. Click this link on your iPhone/iPad: [TestFlight Link]
2. Install TestFlight if prompted
3. Accept the invitation
4. Install BabyShield Beta

**What to Test:**
- Scan product barcodes
- Search for recalls
- Test offline mode
- Try all app features

**Reporting Issues:**
- Use the built-in feedback option
- Include screenshots when possible
- Describe steps to reproduce

Thank you for helping us improve BabyShield!

Best regards,
The BabyShield Team
```

---

## 📊 Beta Metrics & Feedback

### Monitoring Dashboard

```yaml
Key Metrics:
  - Install rate
  - Session count
  - Crash rate
  - Feedback submissions
  
Crash Reports:
  Location: App Analytics → Crashes
  Symbolication: Automatic with dSYMs
  
Feedback:
  Location: TestFlight → Feedback
  Response Time: < 24 hours
```

### Feedback Response Template

```markdown
Hi [Tester Name],

Thank you for your feedback about [issue/feature].

[Response to feedback]

We've logged this as [ticket number] and will address it in the next build.

Please continue testing and let us know if you encounter other issues.

Best,
BabyShield Team
```

---

## 🔄 Build Distribution Workflow

### 1. Development Build
```bash
# Increment build number
agvtool next-version -all

# Create archive
xcodebuild archive ...

# Upload to TestFlight
xcrun altool --upload-app ...
```

### 2. Processing (5-30 minutes)
- Wait for processing email
- Check App Store Connect

### 3. Internal Distribution
- Auto-distributed to internal testers
- No review required

### 4. External Distribution
- Submit for Beta App Review (first time)
- Add to external groups
- Monitor feedback

### 5. Iteration
- Address feedback
- Upload new build
- Repeat

---

## 🚨 Common Issues & Solutions

### Issue: Missing Export Compliance
```yaml
Solution:
  Info.plist:
    ITSAppUsesNonExemptEncryption: NO
```

### Issue: Invalid Bundle ID
```yaml
Solution:
  - Verify App ID in Developer Portal
  - Check provisioning profile
  - Match bundle ID exactly
```

### Issue: Build Not Appearing
```yaml
Solutions:
  - Wait 30+ minutes for processing
  - Check email for errors
  - Verify upload succeeded
  - Check build number is incremented
```

### Issue: Beta App Review Rejected
```yaml
Common Reasons:
  - Incomplete test information
  - Demo account not working
  - Crashes during review
  - Guideline violations
  
Solutions:
  - Provide detailed test notes
  - Verify demo account
  - Test on clean device
  - Review App Store Guidelines
```

---

## 📱 TestFlight App Features

### For Testers
- Automatic updates
- Previous builds access
- Send feedback with screenshots
- Crash reporting
- Build expiration notices

### For Developers
- Install/crash analytics
- Tester activity
- Feedback aggregation
- Build management
- Group controls

---

## 🎯 Best Practices

### Release Cadence
- Internal: Daily/weekly builds
- External: Weekly/bi-weekly builds
- Release notes for each build
- Clear testing instructions

### Build Naming
```
Version: 1.0.0
Build: 100  // Internal
Build: 101  // External Beta 1
Build: 102  // External Beta 2
Build: 150  // Release Candidate
```

### Communication
- Welcome email for new testers
- Release notes with each build
- Respond to feedback quickly
- Thank active testers
- Share roadmap updates

---

## 📋 Pre-Release Checklist

- [ ] Build number incremented
- [ ] Release notes written
- [ ] Crash-free on test devices
- [ ] Demo account working
- [ ] Export compliance set
- [ ] Test information updated
- [ ] Previous feedback addressed
- [ ] Analytics events verified
- [ ] Push notifications tested
- [ ] Deep links working

---

## 🚀 From TestFlight to App Store

When ready for release:

1. **Select Build**
   - Choose tested build from TestFlight
   - Typically 2-3 beta cycles

2. **Prepare for Release**
   - Stop external testing (optional)
   - Update store metadata
   - Submit for review

3. **Post-Release**
   - Monitor crash reports
   - Respond to reviews
   - Plan next beta cycle

---

**Last Updated:** January 2024  
**Next Review:** Before major release
