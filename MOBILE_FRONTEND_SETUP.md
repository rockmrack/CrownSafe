# 📱 BabyShield Mobile Front-End Repository Setup Guide

**Date**: October 10, 2025  
**Purpose**: Onboard front-end developer with professional Git workflow  
**Status**: Ready for implementation

---

## 🎯 Overview

This guide establishes a separate private repository for the BabyShield mobile front-end, following industry best practices for clean separation of concerns, independent deployment, and scalable team collaboration.

---

## 📋 Step 1: Create the Repository

### Option A: Via GitHub Web Interface (Recommended for First Time)

1. **Go to GitHub**: https://github.com/BabyShield
2. **Click**: "New repository" (green button)
3. **Configure**:
   - **Name**: `babyshield-mobile`
   - **Description**: `BabyShield mobile app front-end (React Native / Flutter / etc.)`
   - **Visibility**: ✅ **Private**
   - **Initialize**: ❌ Don't add README, .gitignore, or license (developer will push existing code)
4. **Click**: "Create repository"

### Option B: Via GitHub CLI (Automated)

```bash
# Install GitHub CLI if not already installed: https://cli.github.com/

# Create private repository
gh repo create BabyShield/babyshield-mobile \
  --private \
  --description "BabyShield mobile app front-end" \
  --disable-wiki \
  --disable-issues=false

# Confirm
gh repo view BabyShield/babyshield-mobile
```

---

## 👥 Step 2: Add Developer Access

### Via GitHub Web Interface

1. **Go to**: https://github.com/BabyShield/babyshield-mobile/settings/access
2. **Click**: "Add people"
3. **Enter**: Developer's GitHub username or email
4. **Select Role**: **Write** (allows push but not admin changes)
5. **Click**: "Add [username] to this repository"

### Via GitHub CLI

```bash
# Add collaborator with write access
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/BabyShield/babyshield-mobile/collaborators/DEVELOPER_USERNAME \
  -f permission='push'
```

Replace `DEVELOPER_USERNAME` with actual GitHub username.

---

## 🔒 Step 3: Set Up Branch Protection

### Protect `main` Branch

**Go to**: Settings → Branches → Add branch protection rule

**Branch name pattern**: `main`

**Enable These Rules**:
- ✅ **Require a pull request before merging**
  - Require approvals: **1**
  - Dismiss stale pull request approvals when new commits are pushed
  - Require review from Code Owners (optional - for later)
  
- ✅ **Require status checks to pass before merging** (add CI later)
  - Require branches to be up to date before merging
  
- ✅ **Require conversation resolution before merging**

- ✅ **Require linear history** (prevents messy merges)

- ✅ **Do not allow bypassing the above settings**

- ✅ **Restrict who can push to matching branches**
  - Add yourself as admin exception (optional)

- ✅ **Block force pushes**

- ✅ **Allow deletions**: ❌ (prevent accidental deletion)

**Click**: "Create" or "Save changes"

---

## 📝 Step 4: Developer Instructions

### Send This to Your Front-End Developer

```markdown
# BabyShield Mobile - Initial Repository Setup

Hi [Developer Name],

Welcome to the BabyShield mobile project! Please follow these steps to push your initial code to our GitHub repository.

## Repository Details
- **Repo**: https://github.com/BabyShield/babyshield-mobile
- **Access**: You've been added with Write permissions
- **Branch**: Create feature branches, merge via Pull Requests

## Initial Push Instructions

### 1. Navigate to Your Project
```bash
cd /path/to/your/mobile-app-folder
```

### 2. Initialize Git (if not already done)
```bash
git init
```

### 3. Add Remote Repository
```bash
git remote add origin https://github.com/BabyShield/babyshield-mobile.git
```

### 4. Create Your Development Branch
```bash
# Check current branch
git branch

# If on main/master, create feature branch
git checkout -b dev/initial-setup

# Or use your name
git checkout -b dev/[your-name]-initial
```

### 5. Stage All Files
```bash
git add .
```

**Important**: Review what's being added:
```bash
git status
```

**Exclude sensitive files**: Make sure `.env` files, API keys, and credentials are in `.gitignore`

### 6. Create Initial Commit
```bash
git commit -m "Initial mobile app setup

- Add [framework] mobile app structure
- Configure navigation and routing
- Set up API integration with BabyShield backend
- Add authentication flow
- Configure development environment"
```

### 7. Push to GitHub
```bash
# First push - set upstream
git push -u origin dev/[your-branch-name]
```

### 8. Create Pull Request
1. Go to: https://github.com/BabyShield/babyshield-mobile
2. Click: "Compare & pull request" (green button)
3. **Title**: "Initial mobile app setup"
4. **Description**: Summarize what's included:
   - Framework/technology used
   - Key features implemented
   - Dependencies added
   - Configuration details
5. Click: "Create pull request"
6. **Request review** from me

## Workflow for Future Changes

### Creating Feature Branches
```bash
# Always start from updated main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/[feature-name]
# Or: dev/[your-name]/[feature-name]
```

### Making Changes
```bash
# Stage changes
git add .

# Commit with clear message
git commit -m "Add [feature]: brief description"

# Push to GitHub
git push -u origin feature/[feature-name]
```

### Opening Pull Requests
1. Push your branch to GitHub
2. Open PR to `main` branch
3. Add description of changes
4. Request review
5. Address feedback
6. Merge when approved

## Branch Naming Convention

Use descriptive branch names:
- `feature/[feature-name]` - New features
- `fix/[bug-name]` - Bug fixes
- `refactor/[area]` - Code refactoring
- `docs/[topic]` - Documentation updates
- `dev/[name]/[feature]` - Personal development branches

**Examples**:
- `feature/user-authentication`
- `fix/login-crash-on-android`
- `refactor/api-client`
- `dev/john/barcode-scanner`

## Commit Message Guidelines

Write clear, concise commit messages:

```bash
# Good ✅
git commit -m "Add barcode scanning feature with camera integration"
git commit -m "Fix: Resolve crash on product search"
git commit -m "Refactor: Extract API calls to service layer"

# Bad ❌
git commit -m "updates"
git commit -m "fix"
git commit -m "changes"
```

## Important Notes

⚠️ **Never commit**:
- `.env` files with API keys
- Credentials or passwords
- Large binary files (videos, large images)
- `node_modules/` or dependency folders
- Build artifacts (`build/`, `dist/`, etc.)

✅ **Always commit**:
- Source code
- Configuration files (without secrets)
- Documentation
- Tests
- `.gitignore` file

## Need Help?

- **Git issues**: Contact me or check [Git documentation](https://git-scm.com/doc)
- **Repo access**: Let me know if you have permission issues
- **Code review**: I'll review your PRs within 24 hours

## Quick Reference

```bash
# Check status
git status

# View branches
git branch -a

# Switch branches
git checkout [branch-name]

# Pull latest changes
git pull origin main

# View commit history
git log --oneline -10

# Undo last commit (keep changes)
git reset --soft HEAD~1
```

Looking forward to your initial push!

Best regards,
BabyShield Team
```

---

## 🚀 Step 5: Post-Setup Tasks

### After Developer's Initial Push

1. **Review PR**: Check code quality, structure, dependencies
2. **Set up CI/CD**: Add GitHub Actions for:
   - Linting (ESLint, etc.)
   - Type checking (TypeScript)
   - Unit tests
   - Build verification
3. **Add CODEOWNERS**: Define review requirements
4. **Configure secrets**: Add API endpoints, keys to GitHub Secrets
5. **Documentation**: Ensure README.md has:
   - Setup instructions
   - Development workflow
   - API integration details
   - Testing guidelines

---

## 📂 Recommended Repository Structure

The mobile repo should follow this structure:

```
babyshield-mobile/
├── README.md                 # Project overview and setup
├── .gitignore               # Exclude sensitive/generated files
├── .env.example             # Example environment variables
├── package.json             # Dependencies (if React Native/Expo)
├── app.json                 # App configuration
├── tsconfig.json            # TypeScript config (if applicable)
├── .eslintrc.js             # Linting rules
├── .prettierrc              # Code formatting
│
├── src/                     # Source code
│   ├── api/                # API client and services
│   │   ├── client.ts       # Axios/fetch configuration
│   │   ├── auth.ts         # Authentication API
│   │   ├── products.ts     # Product search API
│   │   └── recalls.ts      # Recall alerts API
│   │
│   ├── components/         # Reusable UI components
│   │   ├── common/         # Buttons, inputs, etc.
│   │   ├── products/       # Product-related components
│   │   └── alerts/         # Alert/notification components
│   │
│   ├── screens/            # App screens/pages
│   │   ├── HomeScreen.tsx
│   │   ├── SearchScreen.tsx
│   │   ├── ProductDetailScreen.tsx
│   │   └── AlertsScreen.tsx
│   │
│   ├── navigation/         # Navigation configuration
│   ├── hooks/              # Custom React hooks
│   ├── context/            # React Context (state management)
│   ├── utils/              # Utility functions
│   ├── types/              # TypeScript type definitions
│   └── assets/             # Images, fonts, etc.
│
├── tests/                   # Test files
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docs/                    # Additional documentation
│   ├── API_INTEGRATION.md  # Backend API documentation
│   ├── SETUP.md            # Detailed setup guide
│   └── TESTING.md          # Testing guidelines
│
└── .github/                # GitHub configuration
    └── workflows/          # CI/CD workflows
        ├── lint.yml        # Linting checks
        ├── test.yml        # Run tests
        └── build.yml       # Build verification
```

---

## 🔗 Backend Integration

### API Configuration

The mobile app should connect to:
- **Production**: `https://babyshield.cureviax.ai`
- **Staging**: `https://staging-babyshield.cureviax.ai` (if available)
- **Local Dev**: `http://localhost:8001` (for developer testing)

### Environment Variables (`.env`)

```bash
# API Configuration
API_BASE_URL=https://babyshield.cureviax.ai
API_TIMEOUT=30000

# Authentication
AUTH_TOKEN_KEY=babyshield_auth_token
AUTH_REFRESH_KEY=babyshield_refresh_token

# Features
ENABLE_ANALYTICS=true
ENABLE_CRASH_REPORTING=true

# Development
DEBUG_MODE=false
LOG_LEVEL=info
```

### Authentication Flow

```typescript
// Example API integration
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token interceptor
apiClient.interceptors.request.use((config) => {
  const token = getStoredAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Example endpoints
export const authAPI = {
  login: (email: string, password: string) =>
    apiClient.post('/api/v1/auth/login', { email, password }),
  
  register: (userData: RegisterData) =>
    apiClient.post('/api/v1/auth/register', userData),
};

export const productsAPI = {
  search: (query: string) =>
    apiClient.get('/api/v1/products/search', { params: { q: query } }),
  
  scanBarcode: (barcode: string) =>
    apiClient.post('/api/v1/barcode/scan', { barcode }),
};

export const recallsAPI = {
  getActive: () =>
    apiClient.get('/api/v1/recalls/active'),
  
  getAlerts: (userId: string) =>
    apiClient.get(`/api/v1/users/${userId}/alerts`),
};
```

---

## 🔐 Security Best Practices

### For Developer to Follow

1. **Never commit secrets**:
   - Use `.env` files (add to `.gitignore`)
   - Use GitHub Secrets for CI/CD
   - Never hardcode API keys

2. **Secure authentication**:
   - Store tokens securely (Keychain/Keystore)
   - Implement token refresh logic
   - Clear tokens on logout

3. **API security**:
   - Always use HTTPS
   - Validate SSL certificates
   - Implement request timeout
   - Handle errors gracefully

4. **Data protection**:
   - Encrypt sensitive local data
   - Don't log sensitive information
   - Follow GDPR/privacy regulations

---

## 📊 CI/CD Setup (GitHub Actions)

### `.github/workflows/mobile-ci.yml`

```yaml
name: Mobile CI

on:
  pull_request:
    branches: [ main, develop ]
  push:
    branches: [ main, develop ]

jobs:
  lint:
    name: Lint Code
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint

  test:
    name: Run Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
      - run: npm ci
      - run: npm test

  build:
    name: Build App
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
```

---

## 📞 Communication Guidelines

### Code Review Process

1. **Developer pushes code** → Creates PR
2. **Automated checks run** → Linting, tests, build
3. **You review code** → Check quality, functionality
4. **Request changes** if needed → Developer updates
5. **Approve PR** → Developer or you merge
6. **Deploy** (if applicable) → Update app stores

### Response Time Expectations

- **PR reviews**: Within 24 hours on business days
- **Questions/blockers**: Within 4 hours
- **Emergency issues**: Immediate (use direct contact)

---

## 🎯 Success Checklist

After completing this setup, you should have:

- ✅ Private `babyshield-mobile` repository created
- ✅ Developer added with Write access
- ✅ `main` branch protected with PR requirements
- ✅ Developer has clear setup instructions
- ✅ Branch naming convention established
- ✅ Commit message guidelines defined
- ✅ Security best practices communicated
- ✅ API integration documented
- ✅ Repository structure recommended
- ✅ CI/CD pipeline planned

---

## 🔄 Alternative: Monorepo Approach

### When to Use Monorepo

**Consider monorepo if**:
- Front-end and back-end share TypeScript types
- You want synchronized version releases
- Shared utilities and configurations
- Small team with tight coupling

**Structure**:
```
babyshield-monorepo/
├── packages/
│   ├── mobile/          # Mobile app
│   ├── backend/         # FastAPI backend
│   └── shared/          # Shared types/utilities
├── package.json         # Root workspace config
└── turbo.json           # Build orchestration
```

**Recommendation**: Start with **separate repos** for simplicity. Migrate to monorepo only if you have strong coupling needs.

---

## 📚 Additional Resources

### For Developer
- **React Native Docs**: https://reactnative.dev/docs/getting-started
- **Git Best Practices**: https://git-scm.com/book/en/v2
- **GitHub Flow**: https://guides.github.com/introduction/flow/
- **Conventional Commits**: https://www.conventionalcommits.org/

### For You (Project Owner)
- **GitHub Branch Protection**: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches
- **Managing Collaborators**: https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-access-to-your-personal-repositories
- **GitHub Actions**: https://docs.github.com/en/actions

---

## 🎉 Ready to Go!

You now have a complete, professional setup guide for your mobile front-end developer. This follows industry best practices and will scale as your project grows.

**Next Steps**:
1. Create the repository (Step 1)
2. Add your developer (Step 2)
3. Set up branch protection (Step 3)
4. Send developer the instructions (Step 4)
5. Review their initial PR
6. Set up CI/CD after first push

Good luck with your mobile app development! 🚀

---

**Document Owner**: BabyShield Backend Team  
**Last Updated**: October 10, 2025  
**Version**: 1.0
