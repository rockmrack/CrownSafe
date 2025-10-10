# 📦 BabyShield Mobile Developer Resources

**Complete Package for Front-End Developer**  
**Date**: October 10, 2025  
**Version**: 1.0

---

## 📋 What's Included

This package contains everything your mobile front-end developer needs to get started:

### 1. **Repository Setup Guide** (`MOBILE_FRONTEND_SETUP.md`)
   - Complete GitHub repository setup instructions
   - Branch protection rules
   - Access management
   - Developer workflow guidelines
   - Professional Git conventions

### 2. **.gitignore Template** (`.gitignore.template`)
   - Comprehensive exclusion rules
   - Covers React Native, Expo, Flutter
   - iOS and Android specific ignores
   - Security-focused (prevents secret commits)
   - Ready to copy to mobile repo

### 3. **GitHub Actions Workflows**
   - **`github-workflows-mobile-ci.yml`**: Full CI pipeline
     - Linting (ESLint, Prettier)
     - TypeScript type checking
     - Unit and integration tests
     - Android and iOS builds
     - Security scanning
     - Code coverage reports
   
   - **`github-workflows-release.yml`**: Automated releases
     - Android AAB builds
     - iOS IPA builds
     - TestFlight deployment
     - Play Store deployment
     - GitHub release creation

### 4. **API Documentation** (`MOBILE_API_DOCUMENTATION.md`)
   - Complete REST API reference
   - All endpoints documented
   - Request/response examples
   - Error handling guide
   - Rate limiting details
   - Authentication flows
   - TypeScript examples included

### 5. **TypeScript Type Definitions** (`babyshield-api-types.ts`)
   - 400+ lines of type-safe definitions
   - All API models typed
   - Type guards included
   - Helper types for forms
   - Full IntelliSense support
   - Production-ready

### 6. **API Client Example** (`api-client-example.ts`)
   - Complete, working API client
   - Token management built-in
   - Automatic token refresh
   - Rate limit handling
   - Error handling
   - Offline caching
   - Usage examples included
   - Ready to customize

---

## 🚀 Quick Start for Developer

### Step 1: Send These Files

Send your developer these files from `docs/mobile/`:

```
docs/mobile/
├── MOBILE_FRONTEND_SETUP.md          # Main setup guide
├── .gitignore.template               # Copy to mobile repo
├── github-workflows-mobile-ci.yml    # CI/CD pipeline
├── github-workflows-release.yml      # Release automation
├── MOBILE_API_DOCUMENTATION.md       # API reference
├── babyshield-api-types.ts           # TypeScript types
├── api-client-example.ts             # API client code
└── README_MOBILE_RESOURCES.md        # This file
```

### Step 2: Follow Setup Guide

Have your developer follow these steps in order:

1. **Read**: `MOBILE_FRONTEND_SETUP.md` (main guide)
2. **Copy**: `.gitignore.template` → mobile repo as `.gitignore`
3. **Copy**: `github-workflows-*.yml` → mobile repo `.github/workflows/`
4. **Copy**: `babyshield-api-types.ts` → mobile repo `src/types/`
5. **Copy**: `api-client-example.ts` → mobile repo `src/api/` (customize as needed)
6. **Reference**: `MOBILE_API_DOCUMENTATION.md` when integrating

### Step 3: Repository Creation

**You do this**:
1. Create private repo: `babyshield-mobile`
2. Add developer with Write access
3. Set up branch protection on `main`

**Developer does this**:
1. Initialize project locally
2. Copy `.gitignore` from template
3. Push initial code to feature branch
4. Open Pull Request
5. You review and merge

---

## 📝 Developer Checklist

Give this to your developer:

- [ ] **Environment Setup**
  - [ ] Node.js 18+ installed
  - [ ] React Native / Expo / Flutter set up
  - [ ] iOS / Android dev environment configured
  - [ ] Git configured with SSH keys

- [ ] **Repository Access**
  - [ ] Received GitHub invitation
  - [ ] Cloned repository
  - [ ] Can push to feature branches

- [ ] **Project Configuration**
  - [ ] Copied `.gitignore` template
  - [ ] Created `.env.example` file
  - [ ] Set up linting (ESLint, Prettier)
  - [ ] Configured TypeScript

- [ ] **API Integration**
  - [ ] Copied TypeScript types
  - [ ] Set up API client
  - [ ] Tested authentication flow
  - [ ] Verified barcode scanning endpoint

- [ ] **Development Workflow**
  - [ ] Understands branch naming
  - [ ] Knows commit message format
  - [ ] Can create Pull Requests
  - [ ] CI/CD workflows configured

- [ ] **Testing**
  - [ ] Unit tests set up
  - [ ] Can build Android APK
  - [ ] Can build iOS app
  - [ ] Tested on real devices

---

## 🔧 Installation Commands

### For React Native Project

```bash
# Create new React Native project
npx react-native@latest init BabyShieldMobile --template react-native-template-typescript

# Install essential dependencies
cd BabyShieldMobile
npm install axios @react-native-async-storage/async-storage
npm install @react-navigation/native @react-navigation/stack
npm install react-native-vector-icons
npm install react-native-camera react-native-permissions

# Install dev dependencies
npm install --save-dev @types/react @types/react-native
npm install --save-dev eslint prettier @typescript-eslint/parser
npm install --save-dev jest @testing-library/react-native
```

### For Expo Project

```bash
# Create new Expo project
npx create-expo-app BabyShieldMobile --template expo-template-blank-typescript

# Install dependencies
cd BabyShieldMobile
npx expo install axios @react-native-async-storage/async-storage
npx expo install expo-camera expo-barcode-scanner
npx expo install @react-navigation/native @react-navigation/stack
npx expo install expo-router
```

---

## 🔐 Environment Variables

Create `.env.example` in mobile repo:

```bash
# API Configuration
API_BASE_URL=https://babyshield.cureviax.ai
API_TIMEOUT=30000

# Environment
NODE_ENV=development

# Features
ENABLE_ANALYTICS=false
ENABLE_CRASH_REPORTING=false

# Development
DEBUG_MODE=true
LOG_LEVEL=debug

# Authentication
AUTH_TOKEN_KEY=babyshield_auth_token
AUTH_REFRESH_KEY=babyshield_refresh_token
```

Create `.env` (gitignored) with actual values:

```bash
# Copy from .env.example and fill in real values
API_BASE_URL=https://babyshield.cureviax.ai
# Add any API keys here (NEVER commit this file!)
```

---

## 📖 API Quick Reference

### Base URL
```
Production: https://babyshield.cureviax.ai
Staging: https://staging-babyshield.cureviax.ai (if available)
```

### Key Endpoints

| Category     | Endpoint                  | Method | Purpose             |
| ------------ | ------------------------- | ------ | ------------------- |
| **Auth**     | `/api/v1/auth/register`   | POST   | Create account      |
| **Auth**     | `/api/v1/auth/login`      | POST   | Login user          |
| **Auth**     | `/api/v1/auth/refresh`    | POST   | Refresh token       |
| **Products** | `/api/v1/barcode/scan`    | POST   | Scan barcode        |
| **Products** | `/api/v1/products/search` | GET    | Search products     |
| **Products** | `/api/v1/products/:id`    | GET    | Get product details |
| **Recalls**  | `/api/v1/recalls/active`  | GET    | Get active recalls  |
| **User**     | `/api/v1/users/me`        | GET    | Get user profile    |
| **Family**   | `/api/v1/family/members`  | GET    | Get family members  |

**Full documentation**: See `MOBILE_API_DOCUMENTATION.md`

---

## 🧪 Testing Strategy

### Test Coverage Goals
- **Unit Tests**: 80%+ coverage
- **Integration Tests**: Key user flows
- **E2E Tests**: Critical paths only

### Test Structure
```
tests/
├── unit/
│   ├── api/
│   │   └── api-client.test.ts
│   ├── components/
│   │   └── BarcodeScanner.test.tsx
│   └── utils/
│       └── validation.test.ts
├── integration/
│   ├── auth-flow.test.ts
│   └── barcode-scan.test.ts
└── e2e/
    ├── login.e2e.ts
    └── scan-product.e2e.ts
```

---

## 🎨 Design Guidelines

### Color Palette (Example - Customize)
```typescript
export const colors = {
  primary: '#007AFF',      // Blue
  secondary: '#5856D6',    // Purple
  success: '#34C759',      // Green
  warning: '#FF9500',      // Orange
  danger: '#FF3B30',       // Red
  background: '#FFFFFF',
  text: '#000000',
  textSecondary: '#8E8E93',
};
```

### Typography
```typescript
export const fonts = {
  regular: 'System',
  medium: 'System-Medium',
  bold: 'System-Bold',
  sizes: {
    small: 12,
    medium: 16,
    large: 20,
    xlarge: 24,
  },
};
```

---

## 🚢 Deployment Process

### Android Release

1. **Build APK/AAB**
   ```bash
   cd android
   ./gradlew bundleRelease
   ```

2. **Deploy to Play Store**
   - Upload to Google Play Console
   - Internal testing → Closed testing → Production
   - Monitor crash reports

### iOS Release

1. **Build Archive**
   ```bash
   cd ios
   xcodebuild archive -workspace BabyShield.xcworkspace -scheme BabyShield
   ```

2. **Deploy to TestFlight**
   - Upload via Xcode or Transporter
   - Add beta testers
   - Submit for App Store review

---

## 🤝 Communication

### When to Contact You

**Immediately**:
- Security issues or data leaks
- Production app crashes
- Cannot access repository
- Blocked on architecture decisions

**Within 24 hours**:
- Feature clarifications needed
- API endpoint questions
- Design approval needed
- PR ready for review

**Weekly status update**:
- Progress summary
- Upcoming features
- Blockers or concerns

### Preferred Communication
- **Urgent**: Phone/WhatsApp
- **Daily**: Slack/Discord
- **Code review**: GitHub PR comments
- **Planning**: Weekly video call

---

## 📚 Additional Resources

### Documentation
- **React Native Docs**: https://reactnative.dev
- **Expo Docs**: https://docs.expo.dev
- **TypeScript Handbook**: https://www.typescriptlang.org/docs
- **API Reference**: `MOBILE_API_DOCUMENTATION.md`

### Tools & Services
- **API Testing**: Postman (import OpenAPI spec)
- **Error Tracking**: Sentry
- **Analytics**: Firebase Analytics / Mixpanel
- **CI/CD**: GitHub Actions (already configured)

---

## ✅ Success Criteria

Your mobile app should:

1. **Authenticate users** securely with JWT tokens
2. **Scan barcodes** using camera (UPC, EAN, QR codes)
3. **Display product safety** status and recalls
4. **Send push notifications** for recall alerts
5. **Work offline** with local caching
6. **Handle errors gracefully** with user-friendly messages
7. **Pass all CI checks** (linting, tests, builds)
8. **Meet performance standards** (< 3s app launch)

---

## 🎯 Next Steps

1. **Send files to developer** (all files in `docs/mobile/`)
2. **Create GitHub repository** (`babyshield-mobile`)
3. **Add developer as collaborator**
4. **Set up branch protection**
5. **Schedule kickoff call** to discuss:
   - Timeline and milestones
   - Technology stack choice
   - Design mockups review
   - API walkthrough
   - Questions and concerns

---

## 📞 Support Contacts

- **Technical Questions**: dev@babyshield.dev
- **API Issues**: api-support@babyshield.dev
- **Repository Access**: admin@babyshield.dev
- **Emergency**: [Your Phone Number]

---

**Last Updated**: October 10, 2025  
**Package Version**: 1.0  
**Maintained By**: BabyShield Backend Team

---

## 📄 License

All code examples and templates in this package are provided for BabyShield mobile app development. Proprietary and confidential.
