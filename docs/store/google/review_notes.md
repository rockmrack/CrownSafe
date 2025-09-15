# Google Play Store Review Notes - BabyShield

**App Name:** BabyShield Recall Scanner  
**Developer:** Cureviax Research LLC  
**Package Name:** ai.cureviax.babyshield  
**Version:** 1.0.0 (1)  

---

## 🔑 AUTHENTICATION

### Login Required: YES
- **OAuth Providers:** Google Sign-In / Sign in with Apple
- **Data Stored:**
  - Internal user UUID (our system)
  - Provider subject ID (from OAuth)
- **NO email addresses stored**
- **No test account needed** - Use your Google account

---

## 🧪 TESTING INSTRUCTIONS

### Quick Test Flow:

1. **Sign In**
   ```
   → Tap "Sign in with Google" or "Sign in with Apple"
   → Complete OAuth authentication
   → App opens to home screen
   ```

2. **Search Products**
   ```
   Test searches:
   - "pacifier" → Multiple baby product recalls
   - "doll" → Toy safety recalls
   - "formula" → FDA food recalls
   ```

3. **Scan Barcode** (Optional)
   ```
   → Tap camera button
   → Grant camera permission
   → Point at any product barcode
   → View safety status
   ```

4. **View Details**
   ```
   → Tap any recall result
   → Tap source link
   → Opens official government page
   ```

5. **Privacy Controls**
   ```
   → Settings → Privacy
   → Toggle crash reporting (opt-in)
   → Delete account option
   → Export data option
   ```

---

## 📱 KEY FEATURES

- **Real-time recall data** from FDA, CPSC, EU Safety Gate
- **Barcode scanning** for instant checks
- **Advanced filtering** by severity and category
- **Offline support** with cached data
- **Privacy-first** - no tracking or ads

---

## 🔒 DATA & PRIVACY

### Data Collection:
✅ **User IDs** (internal UUID + provider ID)  
❌ **Email addresses** (NOT stored)  
✅ **Crash logs** (opt-in only via Firebase Crashlytics)  
❌ **Personal information** (NOT collected)  
❌ **Location** (NOT used)  
❌ **Analytics** (NO tracking)  

### Data Safety:
- **Encryption:** HTTPS/TLS for all communication
- **Data deletion:** Available in-app
- **GDPR/CCPA compliant**
- **No third-party sharing**
- **No ads or tracking**

### Legal Compliance:
- Privacy Policy: https://babyshield.cureviax.ai/legal/privacy
- Terms: https://babyshield.cureviax.ai/legal/terms
- Data Deletion: https://babyshield.cureviax.ai/legal/data-deletion

---

## ⚠️ CONTENT & DISCLAIMERS

### Medical Disclaimer:
**Informational safety data only - NOT medical advice**
- Follow official recall instructions
- Contact manufacturers for remedies
- Consult healthcare providers for medical concerns

### Content Rating: Everyone
- No violence
- No sexual content
- No gambling
- No profanity
- No user-generated content
- Safe for all ages

---

## 📋 PERMISSIONS

### Required:
- **INTERNET** - Fetch recall data
- **ACCESS_NETWORK_STATE** - Check connectivity

### Optional:
- **CAMERA** - Barcode scanning only

---

## 🌍 DISTRIBUTION

- **Countries:** All
- **Languages:** English (en-US)
- **Devices:** Phones (8.0+)
- **Tablets:** Supported but not optimized
- **Android TV:** NO
- **Wear OS:** NO
- **Android Auto:** NO

---

## 💰 MONETIZATION

- **Price:** FREE
- **In-app purchases:** NONE
- **Subscriptions:** NONE
- **Ads:** NONE

---

## 📞 SUPPORT

**Email:** support@babyshield.cureviax.ai  
**Phone:** +1-561-581-3322  
**Hours:** Mon-Fri 9AM-5PM EST  

**Developer:**  
Cureviax Research LLC  
1111B S Governors Ave STE 34726  
Dover, DE 19904  
United States  

---

## 🚀 PRODUCTION DETAILS

- **Backend API:** https://babyshield.cureviax.ai/api/v1/
- **Status:** Live and operational
- **Data Sources:** FDA, CPSC, EU Safety Gate (official APIs)
- **Updates:** Real-time from government sources
- **Infrastructure:** AWS (us-east-1)

---

## 🔧 TECHNICAL SPECS

```json
{
  "minSdkVersion": 26,
  "targetSdkVersion": 34,
  "minAndroidVersion": "8.0 (Oreo)",
  "architecture": ["arm64-v8a", "armeabi-v7a", "x86", "x86_64"],
  "appBundle": true,
  "format": "AAB"
}
```

---

## ✅ REVIEW CHECKLIST

- [ ] OAuth sign-in works
- [ ] Search returns results
- [ ] Barcode scanner functions
- [ ] External links work
- [ ] Privacy settings accessible
- [ ] No crashes
- [ ] Disclaimers visible

---

## 📝 COMPLIANCE NOTES

### COPPA Compliance:
- App not directed at children under 13
- No collection of personal information from children
- Safe for all ages to use

### Accessibility:
- Standard Android accessibility features supported
- Screen reader compatible
- High contrast text

### Security:
- No custom encryption (HTTPS/TLS only)
- No VPN functionality
- OAuth 2.0 for authentication
- API keys secured

---

## 🎯 APP CATEGORY

**Primary:** Tools  
**Secondary:** Health & Fitness  

**Why Tools?** BabyShield is a utility for checking product safety, similar to a barcode scanner or product lookup tool.

---

## 📊 EXPECTED BEHAVIOR

1. **First Launch:** OAuth sign-in required
2. **Home Screen:** Search bar and recent recalls
3. **Search Results:** List of matching recalls
4. **Detail View:** Full recall information with source link
5. **Settings:** Privacy controls and app info

---

## 🚨 KNOWN ISSUES

None in current release.

---

## 📱 DEVICE TESTING

Tested on:
- Pixel 7 (Android 14)
- Samsung Galaxy S23 (Android 14)
- OnePlus 11 (Android 13)
- Xiaomi 13 (Android 13)

---

Thank you for reviewing BabyShield. Our mission is to help families stay safe with instant access to product recall information. For any questions during review, please contact support@babyshield.cureviax.ai immediately.
