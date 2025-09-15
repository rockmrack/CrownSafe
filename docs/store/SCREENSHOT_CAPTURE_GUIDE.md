# 📸 Screenshot Capture Guide - BabyShield

## 🎯 Overview

This guide provides step-by-step instructions for capturing app store screenshots that maximize conversion and meet platform requirements.

---

## 📱 iOS Screenshot Capture

### Required Devices/Simulators

| Device | Size | Simulator | Priority |
|--------|------|-----------|----------|
| iPhone 15 Pro Max | 6.7" | iPhone 15 Pro Max | **Required** |
| iPhone 14 Pro | 6.1" | iPhone 14 Pro | **Required** |
| iPhone 8 Plus | 5.5" | iPhone 8 Plus | Optional |
| iPad Pro 12.9" | 12.9" | iPad Pro (6th gen) | Optional |

### Xcode Simulator Setup

1. **Open Xcode**
   ```bash
   open -a Xcode
   ```

2. **Launch Simulator**
   - Xcode → Open Developer Tool → Simulator
   - Device → iOS → iPhone 15 Pro Max

3. **Configure Simulator**
   ```
   Device → Erase All Content and Settings
   Settings → General → Language & Region → English (US)
   Settings → Display & Brightness → Light Mode
   Settings → Notifications → Disable all
   ```

4. **Set Status Bar** (9:41 AM)
   ```bash
   xcrun simctl status_bar booted override \
     --time "9:41" \
     --batteryState charged \
     --batteryLevel 100 \
     --wifiBars 3 \
     --cellularBars 4
   ```

### Screenshot Scenarios

#### Screenshot 1: Home Screen
**Setup:**
- Sign in with test account
- Ensure recent recalls visible
- Clean, uncluttered view

**Elements to Show:**
- App logo/branding
- Search bar prominent
- 3-4 recent recalls
- Navigation tabs
- Welcome message

**Script:**
```
1. Launch app fresh
2. Sign in
3. Wait for data load
4. Capture immediately
```

#### Screenshot 2: Search Results
**Setup:**
- Search for "pacifier"
- Show variety of results
- Different severity levels

**Elements to Show:**
- Active search term
- 5-6 results visible
- Severity badges (Critical, High, Medium)
- Agency labels (FDA, CPSC)
- Filter button

**Script:**
```
1. Tap search bar
2. Type "pacifier"
3. Wait for results
4. Ensure mix of severities
5. Capture
```

#### Screenshot 3: Barcode Scanner
**Setup:**
- Camera permission granted
- Scanner overlay visible
- Instructions shown

**Elements to Show:**
- Camera viewfinder
- Scanning overlay/frame
- "Point at barcode" instruction
- Manual search option
- Flash toggle

**Script:**
```
1. Tap scan button
2. Allow camera (if prompted)
3. Point at sample barcode
4. Capture before scan completes
```

#### Screenshot 4: Recall Detail
**Setup:**
- High-severity recall
- Complete information visible
- Official source link

**Elements to Show:**
- Product name and image
- Severity badge
- Hazard description
- Remedy information
- "View on FDA/CPSC" button
- Share button

**Script:**
```
1. From search results
2. Tap a Critical/High severity item
3. Scroll to show key info
4. Capture with action button visible
```

#### Screenshot 5: Settings/Privacy
**Setup:**
- Privacy dashboard
- Account options visible

**Elements to Show:**
- Privacy settings section
- Crash reporting toggle (OFF)
- Delete account option
- Export data option
- App version
- Legal links

**Script:**
```
1. Navigate to Settings
2. Expand Privacy section
3. Show all privacy controls
4. Capture full view
```

### Capture Commands

**Using Simulator:**
```bash
# Method 1: Simulator UI
Device → Screenshot (⌘+S)

# Method 2: Command Line
xcrun simctl io booted screenshot screenshot.png

# Method 3: Fastlane Snapshot
fastlane snapshot
```

---

## 🤖 Android Screenshot Capture

### Required Devices/Emulators

| Device | Type | Emulator | Priority |
|--------|------|----------|----------|
| Pixel 7 | Phone | Pixel 7 API 34 | **Required** |
| Pixel C | Tablet 10" | Pixel C API 34 | Optional |
| Nexus 7 | Tablet 7" | Nexus 7 API 34 | Optional |

### Android Studio Emulator Setup

1. **Create Emulator**
   ```
   Tools → AVD Manager → Create Virtual Device
   Phone → Pixel 7 → Next
   System Image → API 34 → Next
   AVD Name: "Pixel_7_Screenshots"
   ```

2. **Configure Emulator**
   ```
   Settings → System → Languages → English (US)
   Settings → Display → Light theme
   Settings → Notifications → Disable all
   Developer Options → Demo mode → Enable
   ```

3. **Set Clean Status Bar**
   ```bash
   adb shell settings put global sysui_demo_allowed 1
   adb shell am broadcast -a com.android.systemui.demo -e command enter
   adb shell am broadcast -a com.android.systemui.demo -e command clock -e hhmm 0941
   adb shell am broadcast -a com.android.systemui.demo -e command battery -e level 100 -e plugged false
   adb shell am broadcast -a com.android.systemui.demo -e command network -e wifi show -e level 4
   adb shell am broadcast -a com.android.systemui.demo -e command network -e mobile show -e level 4 -e datatype none
   adb shell am broadcast -a com.android.systemui.demo -e command notifications -e visible false
   ```

### Capture Commands

**Using Android Studio:**
```bash
# Method 1: Emulator UI
More → Screenshot

# Method 2: ADB
adb screenshot /sdcard/screenshot.png
adb pull /sdcard/screenshot.png

# Method 3: Fastlane Screengrab
fastlane screengrab
```

---

## 🎨 Screenshot Design Best Practices

### Visual Hierarchy

1. **Primary Focus** (40% of attention)
   - Main feature/action
   - Clear value proposition

2. **Supporting Elements** (30%)
   - Navigation
   - Secondary features

3. **Context** (30%)
   - Status bar
   - Background elements

### Color Guidelines

```css
/* Brand Colors */
Primary: #667EEA
Secondary: #48BB78
Danger: #F56565
Warning: #ED8936
Background: #FFFFFF
Text: #2D3748

/* Ensure 4.5:1 contrast ratio */
```

### Typography

- **Headings:** 600 weight, 1.2x size
- **Body:** 400 weight, readable at 50% zoom
- **Buttons:** 500 weight, high contrast

### Content Guidelines

#### DO ✅
- Show real data (approved samples)
- Include diverse product types
- Display actual UI elements
- Maintain consistent time (9:41)
- Use proper capitalization
- Show success states

#### DON'T ❌
- Include personal information
- Show error states (unless demonstrating recovery)
- Use placeholder/Lorem Ipsum text
- Include development UI
- Show incomplete features
- Display outdated UI

---

## 📐 Technical Specifications

### Image Requirements

| Platform | Format | Color Space | Max Size | Compression |
|----------|--------|-------------|----------|-------------|
| iOS | PNG/JPG | sRGB | 10MB | Lossless preferred |
| Android | PNG/JPG | sRGB | 8MB | 85% quality |

### Exact Dimensions

**iOS (Required):**
- iPhone 6.7": 1290 × 2796 px
- iPhone 6.5": 1242 × 2688 px

**iOS (Optional):**
- iPhone 5.5": 1242 × 2208 px
- iPad 12.9": 2048 × 2732 px

**Android:**
- Phone: Min 320px, Max 3840px (any dimension)
- Recommended: 1080 × 1920 px or higher
- Aspect ratio: 16:9 or 9:16

---

## 🔧 Screenshot Optimization Tools

### Image Optimization

```bash
# Optimize PNG (lossless)
optipng -o7 screenshot.png

# Optimize JPG
jpegoptim --max=85 screenshot.jpg

# Batch optimize
find . -name "*.png" -exec optipng -o7 {} \;
```

### Device Frames

**Figma Template:**
```
1. Import screenshot
2. Apply device frame
3. Add shadow/background
4. Export at exact size
```

**Online Tools:**
- [MockUPhone](https://mockuphone.com)
- [Shotbot](https://app.shotbot.io)
- [AppLaunchpad](https://theapplaunchpad.com)

### Localization Prep

```bash
# Create language folders
mkdir -p screenshots/{en,es,fr,de,ja,zh}/ios
mkdir -p screenshots/{en,es,fr,de,ja,zh}/android

# Name with locale
iphone67-01-home-en.png
iphone67-01-home-es.png
```

---

## ✅ Quality Checklist

### Before Capture
- [ ] App updated to latest version
- [ ] Test data loaded
- [ ] Notifications cleared
- [ ] Status bar configured
- [ ] Light mode selected
- [ ] English language set

### During Capture
- [ ] Consistent time shown (9:41)
- [ ] Battery at 100%
- [ ] WiFi/cellular bars full
- [ ] No notifications visible
- [ ] Proper data shown
- [ ] Key features highlighted

### After Capture
- [ ] Correct dimensions
- [ ] File size under limit
- [ ] No personal data
- [ ] Text readable
- [ ] Colors accurate
- [ ] Properly named

### Final Review
- [ ] All required sizes captured
- [ ] Consistent style across set
- [ ] Features clearly demonstrated
- [ ] Conversion-optimized order
- [ ] Store guidelines met
- [ ] Legal compliance verified

---

## 📋 Screenshot File Naming

### Convention
```
[platform]-[device]-[number]-[scene]-[locale].[ext]

Examples:
ios-iphone67-01-home-en.png
ios-iphone65-02-search-en.png
android-phone-01-home-en.png
android-tablet10-01-home-en.png
```

### Organization
```
assets/
└── store/
    └── screenshots/
        ├── ios/
        │   ├── iphone67-01-home.png
        │   ├── iphone67-02-search.png
        │   └── ...
        └── android/
            ├── phone-01-home.png
            ├── phone-02-search.png
            └── ...
```

---

## 🚀 Advanced Techniques

### A/B Testing Variants

Create multiple sets for testing:
- **Set A:** Feature-focused
- **Set B:** Benefit-focused
- **Set C:** Problem/solution

### Seasonal Updates

Prepare seasonal variants:
- Holiday themes
- Back-to-school
- Summer safety
- New Year campaigns

### Performance Tracking

Monitor screenshot performance:
- Conversion rates
- Click-through rates
- User feedback
- Store featuring impact

---

## 📚 Resources

### Official Guidelines
- [Apple Screenshot Specifications](https://developer.apple.com/app-store/product-page/)
- [Google Play Screenshot Guidelines](https://support.google.com/googleplay/android-developer/answer/9866151)

### Tools
- **Figma:** Design and layout
- **Sketch:** macOS design tool
- **Adobe XD:** Cross-platform design
- **Canva:** Quick edits and text overlay

### Automation
- **Fastlane Snapshot:** iOS automation
- **Fastlane Screengrab:** Android automation
- **Maestro:** Cross-platform UI testing

---

## 💡 Pro Tips

1. **Test on Real Devices** when possible for authentic look
2. **Capture Extra Screenshots** for marketing materials
3. **Save Layered Files** (PSD/Figma) for easy updates
4. **Create Templates** for consistent future updates
5. **Document Your Process** for team collaboration
6. **Version Control** your screenshots with Git LFS

---

## 🆘 Troubleshooting

### Common Issues

**Simulator shows wrong time:**
```bash
# Reset and override again
xcrun simctl shutdown all
xcrun simctl boot "iPhone 15 Pro Max"
xcrun simctl status_bar booted override --time "9:41"
```

**Android emulator slow:**
```bash
# Enable hardware acceleration
emulator -avd Pixel_7_Screenshots -gpu host
```

**Screenshots wrong size:**
```bash
# Check device scale
# iOS: Window → Physical Size
# Android: Settings → Advanced → Device Frame
```

---

## ✨ Final Notes

Remember: Screenshots are your app's first impression. They should:
- Tell a story
- Show value immediately
- Look professional
- Build trust
- Drive downloads

Take time to get them right - they're worth the investment!
