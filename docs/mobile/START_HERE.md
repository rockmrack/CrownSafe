# 📱 BabyShield Mobile App - Developer Package

**Welcome to the BabyShield mobile development team!**

This document contains everything you need to get started building the BabyShield mobile application.

---

## 📦 What's Included in This Package

You have received **8 files** in the `mobile-developer-package/` folder:

1. **THIS FILE** - Start here (you're reading it!)
2. **SETUP_GUIDE.md** - Complete repository and development setup
3. **.gitignore** - Copy this to your mobile project root
4. **mobile-ci.yml** - CI/CD pipeline (copy to `.github/workflows/`)
5. **release.yml** - Automated releases (copy to `.github/workflows/`)
6. **API_DOCUMENTATION.md** - Complete API reference with examples
7. **babyshield-api-types.ts** - TypeScript type definitions
8. **api-client.ts** - Working API client with authentication

---

## 🚀 Quick Start (15 Minutes)

### Step 1: Accept GitHub Invitation (1 min)

You should have received an email invitation to:
```
https://github.com/BabyShield/babyshield-mobile
```

Click the link and accept the invitation. You now have **Write** access to push code and create Pull Requests.

### Step 2: Clone the Repository (2 min)

```bash
# Clone the repository
git clone https://github.com/BabyShield/babyshield-mobile.git
cd babyshield-mobile

# Check your access
git remote -v
```

### Step 3: Choose Your Technology Stack (5 min)

We recommend one of these:

#### Option A: **React Native** (Recommended)
```bash
# Create new React Native project
npx react-native@latest init BabyShieldMobile --template react-native-template-typescript

# Install essential dependencies
npm install axios @react-native-async-storage/async-storage
npm install @react-navigation/native @react-navigation/stack
npm install react-native-camera react-native-permissions
```

#### Option B: **Expo** (Fastest Setup)
```bash
# Create new Expo project
npx create-expo-app BabyShieldMobile --template expo-template-blank-typescript

# Install dependencies
npx expo install axios @react-native-async-storage/async-storage
npx expo install expo-camera expo-barcode-scanner
npx expo install @react-navigation/native @react-navigation/stack
```

### Step 4: Set Up Your Project (5 min)

```bash
# Copy the .gitignore file
cp ../mobile-developer-package/.gitignore .

# Create types folder and copy types
mkdir -p src/types
cp ../mobile-developer-package/babyshield-api-types.ts src/types/

# Create API client folder
mkdir -p src/api
cp ../mobile-developer-package/api-client.ts src/api/

# Create environment variables
cat > .env.example << EOF
API_BASE_URL=https://babyshield.cureviax.ai
API_TIMEOUT=30000
EOF

# Copy for local development
cp .env.example .env
```

### Step 5: Create Your First Commit (2 min)

```bash
# Create a feature branch
git checkout -b dev/initial-setup

# Stage all files
git add .

# Commit
git commit -m "Initial mobile app setup

- Add React Native/Expo project structure
- Configure TypeScript
- Add API client and type definitions
- Set up navigation
- Configure linting"

# Push to GitHub
git push -u origin dev/initial-setup
```

### Step 6: Open Pull Request

1. Go to: https://github.com/BabyShield/babyshield-mobile
2. Click **"Compare & pull request"**
3. Title: `Initial mobile app setup`
4. Description: List what you've included
5. Click **"Create pull request"**
6. Request review from the project owner

---

## 📋 Project Structure

Organize your mobile app like this:

```
babyshield-mobile/
├── .env.example              # Example environment variables
├── .env                      # Your local config (gitignored)
├── .gitignore               # From our package
├── package.json
├── tsconfig.json
├── app.json                 # App configuration
│
├── src/
│   ├── api/                 # API client
│   │   ├── client.ts        # From our package
│   │   └── endpoints.ts     # Organize by feature
│   │
│   ├── types/               # TypeScript types
│   │   └── babyshield-api-types.ts  # From our package
│   │
│   ├── screens/             # App screens
│   │   ├── HomeScreen.tsx
│   │   ├── LoginScreen.tsx
│   │   ├── RegisterScreen.tsx
│   │   ├── ScanScreen.tsx
│   │   ├── ProductDetailScreen.tsx
│   │   └── AlertsScreen.tsx
│   │
│   ├── components/          # Reusable components
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   └── Card.tsx
│   │   ├── products/
│   │   │   └── ProductCard.tsx
│   │   └── alerts/
│   │       └── RecallAlert.tsx
│   │
│   ├── navigation/          # Navigation setup
│   │   └── AppNavigator.tsx
│   │
│   ├── hooks/               # Custom React hooks
│   │   ├── useAuth.ts
│   │   └── useAPI.ts
│   │
│   ├── context/             # React Context
│   │   └── AuthContext.tsx
│   │
│   ├── utils/               # Helper functions
│   │   └── validation.ts
│   │
│   └── assets/              # Images, fonts
│       ├── images/
│       └── fonts/
│
├── tests/                   # Tests
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── .github/                 # GitHub config
    └── workflows/
        ├── mobile-ci.yml    # From our package
        └── release.yml      # From our package
```

---

## 🔐 API Configuration

### Base URL
```
Production: https://babyshield.cureviax.ai
```

### Test Account

Use these credentials for development:
```
Email: test@babyshield.dev
Password: [Will be provided separately]
```

### Environment Variables

Create `.env` file (never commit this!):
```bash
# API Configuration
API_BASE_URL=https://babyshield.cureviax.ai
API_TIMEOUT=30000

# Authentication
AUTH_TOKEN_KEY=babyshield_auth_token
AUTH_REFRESH_KEY=babyshield_refresh_token

# Features
ENABLE_ANALYTICS=false
ENABLE_CRASH_REPORTING=false

# Development
DEBUG_MODE=true
LOG_LEVEL=debug
```

---

## 🔨 Core Features to Implement

### Phase 1: Authentication (Week 1)
- [ ] Login screen with email/password
- [ ] Registration screen
- [ ] Password reset flow
- [ ] Token storage (secure)
- [ ] Auto-login on app start
- [ ] Logout functionality

### Phase 2: Product Scanning (Week 2)
- [ ] Barcode scanner using camera
- [ ] Manual barcode entry
- [ ] Product search functionality
- [ ] Product details display
- [ ] Safety status indicators
- [ ] Recall alerts display

### Phase 3: User Features (Week 3)
- [ ] User profile screen
- [ ] Edit profile
- [ ] Notification preferences
- [ ] Watch list (saved products)
- [ ] Alert history
- [ ] Family members management

### Phase 4: Polish (Week 4)
- [ ] Error handling and messaging
- [ ] Loading states
- [ ] Offline support
- [ ] App icon and splash screen
- [ ] Push notifications
- [ ] Analytics integration

---

## 📖 Key API Endpoints

### Authentication
```typescript
// Login
POST /api/v1/auth/login
Body: { email: string, password: string }
Response: { access_token, refresh_token, user }

// Register
POST /api/v1/auth/register
Body: { email, password, first_name, last_name }
Response: { access_token, refresh_token, user }

// Refresh Token
POST /api/v1/auth/refresh
Body: { refresh_token: string }
Response: { access_token }
```

### Products & Scanning
```typescript
// Scan Barcode
POST /api/v1/barcode/scan
Body: { barcode: string, barcode_type?: string }
Response: { product, safety_status, recalls }

// Search Products
GET /api/v1/products/search?q={query}&limit=20
Response: { total, results: Product[] }

// Get Product Details
GET /api/v1/products/{product_id}
Response: Product with full details
```

### Recalls
```typescript
// Get Active Recalls
GET /api/v1/recalls/active?limit=50
Response: { total, recalls: Recall[] }

// Get User Alerts
GET /api/v1/users/me/alerts
Response: { total_alerts, alerts: RecallAlert[] }
```

**Full API documentation**: See `API_DOCUMENTATION.md`

---

## 💻 Usage Examples

### Example 1: Login Flow

```typescript
import apiClient from './api/client';

const handleLogin = async (email: string, password: string) => {
  try {
    const response = await apiClient.login({ email, password });
    
    // Token is automatically stored
    console.log('Logged in:', response.user);
    
    // Navigate to home screen
    navigation.navigate('Home');
  } catch (error) {
    console.error('Login failed:', error);
    Alert.alert('Error', 'Invalid email or password');
  }
};
```

### Example 2: Scan Barcode

```typescript
import apiClient from './api/client';

const handleBarcodeScan = async (barcode: string) => {
  try {
    const result = await apiClient.scanBarcode({ barcode });
    
    if (result.success && result.product) {
      console.log('Product found:', result.product.name);
      
      // Check if recalled
      if (result.safety_status.status === 'recalled') {
        Alert.alert(
          '⚠️ RECALLED PRODUCT',
          `This product has been recalled: ${result.recalls[0].title}`,
          [{ text: 'View Details', onPress: () => showRecallDetails(result.recalls[0]) }]
        );
      }
      
      // Navigate to product details
      navigation.navigate('ProductDetail', { product: result.product });
    }
  } catch (error) {
    console.error('Scan failed:', error);
    Alert.alert('Error', 'Could not scan barcode');
  }
};
```

### Example 3: Display Product List

```tsx
import { FlatList } from 'react-native';
import type { ProductSummary } from './types/babyshield-api-types';

const ProductListScreen = () => {
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [loading, setLoading] = useState(false);

  const searchProducts = async (query: string) => {
    setLoading(true);
    try {
      const results = await apiClient.searchProducts({ q: query, limit: 20 });
      setProducts(results.results);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <FlatList
      data={products}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => <ProductCard product={item} />}
      onRefresh={() => searchProducts(searchQuery)}
      refreshing={loading}
    />
  );
};
```

---

## 🧪 Testing

### Set Up Testing

```bash
# Install test dependencies
npm install --save-dev @testing-library/react-native jest

# Run tests
npm test

# Run with coverage
npm test -- --coverage
```

### Example Test

```typescript
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import LoginScreen from '../src/screens/LoginScreen';

describe('LoginScreen', () => {
  it('should login user with valid credentials', async () => {
    const { getByPlaceholderText, getByText } = render(<LoginScreen />);
    
    // Fill in form
    fireEvent.changeText(getByPlaceholderText('Email'), 'test@example.com');
    fireEvent.changeText(getByPlaceholderText('Password'), 'password123');
    
    // Submit
    fireEvent.press(getByText('Login'));
    
    // Wait for navigation
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('Home');
    });
  });
});
```

---

## 🚨 Important Security Rules

### ⚠️ NEVER Commit These:

- ❌ `.env` files with real API keys
- ❌ Authentication tokens
- ❌ User data or PII
- ❌ Private keys or certificates
- ❌ `google-services.json` or `GoogleService-Info.plist`
- ❌ Keystore files (except debug.keystore)

### ✅ ALWAYS Do:

- ✅ Use `.env` files (gitignored)
- ✅ Store tokens securely (Keychain/Keystore)
- ✅ Use environment variables
- ✅ Review `.gitignore` before first commit
- ✅ Use HTTPS only
- ✅ Validate user inputs
- ✅ Handle errors gracefully

---

## 🔄 Development Workflow

### Creating Feature Branches

```bash
# Always start from updated main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/user-authentication
# Or: dev/[your-name]/[feature-name]
```

### Making Changes

```bash
# Stage changes
git add .

# Commit with clear message
git commit -m "Add user authentication flow

- Implement login screen
- Add registration screen  
- Set up token storage
- Handle auth errors"

# Push to GitHub
git push -u origin feature/user-authentication
```

### Opening Pull Requests

1. Push your branch to GitHub
2. Open PR to `main` branch
3. Add description of changes:
   - What was added/changed
   - How to test it
   - Screenshots (if UI changes)
4. Request review
5. Address feedback
6. Merge when approved

### Branch Naming Convention

```
feature/[feature-name]    # New features
fix/[bug-name]            # Bug fixes
refactor/[area]           # Code refactoring
docs/[topic]              # Documentation
dev/[name]/[feature]      # Personal branches
```

Examples:
- `feature/barcode-scanner`
- `fix/login-crash-android`
- `refactor/api-client`
- `dev/john/product-details`

---

## 📞 Communication & Support

### When to Contact Project Owner

**Immediately** (Same Day):
- 🚨 Security issues or exposed credentials
- 🚨 Blocking technical issues
- 🚨 Clarification needed on requirements
- 🚨 Architecture decision required

**Within 24 Hours**:
- 📋 Feature clarifications
- 📋 API endpoint questions
- 📋 Design approvals needed
- 📋 PR ready for review

**Weekly**:
- 📊 Progress updates
- 📊 Upcoming feature discussion
- 📊 Blockers or concerns

### Response Time Expectations

- **PR Reviews**: Within 24 hours (business days)
- **Questions**: Within 4-8 hours
- **Emergency Issues**: Same day

---

## ✅ Checklist Before First PR

- [ ] Project builds successfully
- [ ] `.gitignore` is in place
- [ ] No sensitive data committed
- [ ] TypeScript configured
- [ ] Linting configured (ESLint, Prettier)
- [ ] API client integrated
- [ ] Basic navigation works
- [ ] Can test on device/simulator
- [ ] README updated with setup instructions
- [ ] Tests are passing

---

## 📚 Additional Resources

### Documentation
- **Full API Reference**: `API_DOCUMENTATION.md`
- **Setup Guide**: `SETUP_GUIDE.md`
- **TypeScript Types**: `babyshield-api-types.ts`
- **API Client**: `api-client.ts`

### External Resources
- **React Native**: https://reactnative.dev
- **Expo**: https://docs.expo.dev
- **TypeScript**: https://www.typescriptlang.org/docs
- **React Navigation**: https://reactnavigation.org

### Tools
- **API Testing**: Use Postman or curl
- **OpenAPI Spec**: https://babyshield.cureviax.ai/docs

---

## 🎯 Success Criteria

Your mobile app should:

1. ✅ **Authenticate users** securely
2. ✅ **Scan barcodes** using camera
3. ✅ **Display products** and safety status
4. ✅ **Show recall alerts** with details
5. ✅ **Work offline** (cached data)
6. ✅ **Handle errors** gracefully
7. ✅ **Pass all tests** in CI/CD
8. ✅ **Build successfully** for iOS and Android

---

## 🚀 Ready to Start!

### Next Steps:

1. ✅ Accept GitHub invitation
2. ✅ Clone repository
3. ✅ Choose technology stack (React Native/Expo)
4. ✅ Set up project structure
5. ✅ Copy provided files (.gitignore, types, API client)
6. ✅ Create first commit
7. ✅ Open Pull Request
8. ✅ Schedule kickoff call

---

## 📧 Contacts

- **Technical Questions**: dev@babyshield.dev
- **API Issues**: api-support@babyshield.dev
- **Emergency**: [Will be provided]

---

**Welcome aboard! Let's build something amazing! 🎉**

---

**Package Version**: 1.0  
**Last Updated**: October 10, 2025  
**Repository**: https://github.com/BabyShield/babyshield-mobile
