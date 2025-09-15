# Required Store Assets - BabyShield

## 🎨 APPLE APP STORE ASSETS

### App Icon
| Asset | Size | Format | Requirements |
|-------|------|--------|--------------|
| AppIcon1024.png | 1024x1024 | PNG | No transparency, no alpha channel, sRGB color space |

**Location:** `assets/store/icons/ios/AppIcon1024.png`

### Screenshots (iPhone)

#### iPhone 6.7" (Required)
| Asset | Size | Format | Min/Max |
|-------|------|--------|---------|
| iphone67-01-home.png | 1290x2796 | PNG/JPG | Min: 3, Max: 10 |
| iphone67-02-search.png | 1290x2796 | PNG/JPG | |
| iphone67-03-scanner.png | 1290x2796 | PNG/JPG | |
| iphone67-04-detail.png | 1290x2796 | PNG/JPG | |
| iphone67-05-filter.png | 1290x2796 | PNG/JPG | |

**Location:** `assets/store/screenshots/ios/iphone67-*.png`

#### iPhone 6.5" (Required)
| Asset | Size | Format | Min/Max |
|-------|------|--------|---------|
| iphone65-01-home.png | 1242x2688 | PNG/JPG | Min: 3, Max: 10 |
| iphone65-02-search.png | 1242x2688 | PNG/JPG | |
| iphone65-03-scanner.png | 1242x2688 | PNG/JPG | |

**Location:** `assets/store/screenshots/ios/iphone65-*.png`

#### iPhone 5.5" (Optional)
| Asset | Size | Format | Status |
|-------|------|--------|--------|
| iphone55-*.png | 1242x2208 | PNG/JPG | Not required |

#### iPad (Optional)
| Asset | Size | Format | Status |
|-------|------|--------|--------|
| ipad129-*.png | 2048x2732 | PNG/JPG | Not required |

---

## 🤖 GOOGLE PLAY STORE ASSETS

### App Icon
| Asset | Size | Format | Requirements |
|-------|------|--------|--------------|
| Icon512.png | 512x512 | 32-bit PNG | With alpha, max 1024KB |

**Location:** `assets/store/icons/android/Icon512.png`

### Feature Graphic
| Asset | Size | Format | Requirements |
|-------|------|--------|--------------|
| play-feature-1024x500.png | 1024x500 | JPG or PNG | Max 1024KB, no alpha for JPG |

**Location:** `assets/store/graphics/play-feature-1024x500.png`

### Screenshots (Phone)
| Asset | Size | Format | Min/Max |
|-------|------|--------|---------|
| phone-01-home.png | 1080x1920+ | PNG/JPG | Min: 2, Max: 8 |
| phone-02-search.png | 1080x1920+ | PNG/JPG | |
| phone-03-scanner.png | 1080x1920+ | PNG/JPG | |
| phone-04-detail.png | 1080x1920+ | PNG/JPG | |
| phone-05-settings.png | 1080x1920+ | PNG/JPG | |

**Requirements:**
- Aspect ratio: 16:9 or 9:16
- Min dimension: 320px
- Max dimension: 3840px
- Format: JPG or 24-bit PNG

**Location:** `assets/store/screenshots/android/phone-*.png`

### Screenshots (Tablet) - Optional
| Type | Size | Status |
|------|------|--------|
| 7" Tablet | Variable | Optional |
| 10" Tablet | Variable | Optional |

---

## 📸 SCREENSHOT CONTENT GUIDELINES

### Required Elements Per Screenshot:

#### Screenshot 1: Home Screen
- [ ] App logo/branding
- [ ] Search bar prominent
- [ ] Recent recalls visible
- [ ] Sign-in status indicator
- [ ] Clean, uncluttered UI

#### Screenshot 2: Search Results
- [ ] Active search for "pacifier"
- [ ] Multiple results visible
- [ ] Severity badges
- [ ] Agency labels (FDA, CPSC)
- [ ] Filter options visible

#### Screenshot 3: Barcode Scanner
- [ ] Camera view active
- [ ] Barcode targeting overlay
- [ ] Clear instructions
- [ ] Permission prompt if applicable
- [ ] Manual search option visible

#### Screenshot 4: Recall Detail
- [ ] Full recall information
- [ ] Official source link
- [ ] Hazard description
- [ ] Remedy information
- [ ] Clear navigation

#### Screenshot 5: Settings/Privacy
- [ ] Privacy controls
- [ ] Crash reporting toggle
- [ ] Delete account option
- [ ] Export data option
- [ ] Version information

---

## 🎨 DESIGN SPECIFICATIONS

### Color Palette
```css
Primary: #667EEA (Purple)
Secondary: #48BB78 (Green)
Danger: #F56565 (Red)
Warning: #ED8936 (Orange)
Background: #FFFFFF
Text: #2D3748
```

### Typography
- **Headings:** SF Pro Display (iOS) / Roboto (Android)
- **Body:** SF Pro Text (iOS) / Roboto (Android)
- **Sizes:** 14pt body, 18pt subheads, 24pt headers

### Visual Style
- Clean, minimal design
- High contrast for accessibility
- Consistent padding/margins
- Material Design 3 (Android)
- Human Interface Guidelines (iOS)

---

## 📋 ASSET CREATION CHECKLIST

### Pre-Production
- [ ] Install latest app build
- [ ] Set up test data
- [ ] Configure optimal device settings
- [ ] Disable developer options
- [ ] Clear notifications

### Screenshot Capture
- [ ] Use real device or official simulator
- [ ] Capture at native resolution
- [ ] Include status bar (clean)
- [ ] No personal information visible
- [ ] No debug information
- [ ] Consistent time shown (9:41 AM for iOS)

### Post-Production
- [ ] Crop to exact dimensions
- [ ] Optimize file size
- [ ] Verify no alpha channel (iOS icon)
- [ ] Check color space (sRGB)
- [ ] Remove any sensitive data
- [ ] Add device frames (optional)

### Localization (Future)
- [ ] Prepare text overlays separately
- [ ] Create template layouts
- [ ] Document text strings
- [ ] Plan for RTL languages

---

## 🚫 WHAT TO AVOID

### Content
- ❌ Personal information (emails, names, addresses)
- ❌ Debug/development UI elements
- ❌ Placeholder or Lorem Ipsum text
- ❌ Copyrighted content without permission
- ❌ Competitor app references
- ❌ Misleading functionality

### Technical
- ❌ Incorrect dimensions
- ❌ Blurry or pixelated images
- ❌ Incorrect aspect ratios
- ❌ Alpha channel in app icon (iOS)
- ❌ File sizes over limits
- ❌ Wrong color space

### Design
- ❌ Outdated UI/UX
- ❌ Inconsistent styling
- ❌ Poor contrast
- ❌ Cluttered layouts
- ❌ Missing key features
- ❌ Off-brand colors

---

## 🔄 UPDATE SCHEDULE

| Asset Type | Update Frequency | Trigger |
|------------|-----------------|---------|
| App Icon | Major releases | Rebranding |
| Screenshots | Each release | UI changes |
| Feature Graphic | Quarterly | Marketing campaigns |
| Descriptions | Each release | Feature updates |

---

## 📦 EXPORT SETTINGS

### Figma/Sketch
```
Format: PNG
Scale: @3x (iOS) / xxxhdpi (Android)
Color Profile: sRGB
Include: Trim transparent pixels
Exclude: Alpha channel (for iOS icon)
```

### Photoshop
```
Save for Web
Format: PNG-24
Transparency: Off (iOS icon)
Convert to sRGB: Yes
Optimize: Yes
Metadata: None
```

### Screenshot Tools
- **iOS:** Xcode Simulator / Fastlane Snapshot
- **Android:** Android Studio Emulator / Fastlane Screengrab
- **Cross-platform:** App Store Screenshot Generator

---

## 📝 NAMING CONVENTION

```
Platform: ios/android
Type: icon/screenshot/graphic
Device: iphone67/phone/feature
Order: 01-99
Description: home/search/scanner
Extension: .png/.jpg

Example: ios/screenshot/iphone67/01-home.png
```

---

## ✅ FINAL CHECKLIST

### Before Submission
- [ ] All required assets present
- [ ] Correct dimensions verified
- [ ] File sizes within limits
- [ ] No personal data visible
- [ ] Consistent visual style
- [ ] Latest app version shown
- [ ] Legal compliance checked
- [ ] Backup copies saved

### Quality Assurance
- [ ] View on target devices
- [ ] Check in store preview
- [ ] Verify text readability
- [ ] Confirm color accuracy
- [ ] Test accessibility
- [ ] Review with team

---

## 📞 ASSET SUPPORT

For questions about store assets:
- **Designer:** [Designer Email]
- **Developer:** support@babyshield.cureviax.ai
- **Marketing:** [Marketing Email]

**Tools:**
- Figma workspace: [Link]
- Asset repository: [Link]
- Brand guidelines: [Link]
