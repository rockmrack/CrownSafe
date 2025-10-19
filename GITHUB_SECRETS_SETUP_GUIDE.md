# 🔐 GitHub Secrets Configuration Guide

**Date:** October 19, 2025  
**Purpose:** Configure required GitHub Secrets for CI/CD workflows  
**Repository:** BabyShield/babyshield-backend

---

## 🚨 REQUIRED SECRETS FOR CI/CD

### Missing Secrets Causing Failures

The following CI/CD workflows require GitHub Secrets that are currently not configured:

#### 1. **SMOKE_TEST_EMAIL** (REQUIRED)
- **Used in:** `.github/workflows/ci.yml` - Account Deletion Smoke Test
- **Purpose:** Test account email for smoke testing account deletion functionality
- **Example Value:** `test-account@babyshield-test.com`
- **Type:** Test account (not production)

#### 2. **SMOKE_TEST_PASSWORD** (REQUIRED)
- **Used in:** `.github/workflows/ci.yml` - Account Deletion Smoke Test
- **Purpose:** Password for test account
- **Example Value:** `TestPassword123!Secure`
- **Type:** Strong password for test account
- **Security:** Should be a unique test password, not reused elsewhere

---

## 📋 HOW TO ADD GITHUB SECRETS

### Step-by-Step Instructions

#### **Method 1: Via GitHub Web UI** (Recommended)

1. **Navigate to Repository Settings**
   ```
   https://github.com/BabyShield/babyshield-backend/settings/secrets/actions
   ```

2. **Click "New repository secret"**

3. **Add SMOKE_TEST_EMAIL:**
   - Name: `SMOKE_TEST_EMAIL`
   - Secret: `[your-test-email@example.com]`
   - Click "Add secret"

4. **Add SMOKE_TEST_PASSWORD:**
   - Name: `SMOKE_TEST_PASSWORD`
   - Secret: `[your-secure-test-password]`
   - Click "Add secret"

#### **Method 2: Via GitHub CLI** (Alternative)

```bash
# Set SMOKE_TEST_EMAIL
gh secret set SMOKE_TEST_EMAIL --body "test-account@babyshield-test.com"

# Set SMOKE_TEST_PASSWORD
gh secret set SMOKE_TEST_PASSWORD --body "YourSecureTestPassword123!"
```

---

## 🧪 TEST ACCOUNT SETUP

### Creating Test Account

**IMPORTANT:** Create a dedicated test account for CI/CD smoke tests.

#### **Recommended Test Account:**

1. **Email:** Use a dedicated test email (e.g., Gmail with +tag)
   ```
   yourname+babyshield-ci@gmail.com
   ```

2. **Register Account:** 
   ```bash
   curl -X POST https://babyshield.cureviax.ai/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "email": "yourname+babyshield-ci@gmail.com",
       "password": "TestPassword123!Secure",
       "confirm_password": "TestPassword123!Secure"
     }'
   ```

3. **Verify Account:** (if email verification required)

4. **Add to GitHub Secrets:** (see steps above)

---

## ⚠️ SECURITY BEST PRACTICES

### Do's ✅

- ✅ **Use dedicated test accounts** - Never use production accounts
- ✅ **Use strong passwords** - Minimum 12 characters, mixed case, numbers, symbols
- ✅ **Rotate secrets regularly** - Change test passwords every 90 days
- ✅ **Limit scope** - Test account should have minimal permissions
- ✅ **Monitor usage** - Check GitHub Actions logs for suspicious activity

### Don'ts ❌

- ❌ **Never commit secrets to code** - Always use GitHub Secrets
- ❌ **Never use personal accounts** - Use dedicated test accounts
- ❌ **Never reuse passwords** - Test password should be unique
- ❌ **Never share secrets** - Each team member should have their own test account for local testing
- ❌ **Never use production credentials** - Test accounts only

---

## 🔍 WORKFLOW DETAILS

### Where Secrets Are Used

#### **File:** `.github/workflows/ci.yml`

```yaml
- name: Validate secrets exist
  shell: pwsh
  run: |
    if (-not "$env:SMOKE_TEST_EMAIL") { 
      Write-Error "Missing SMOKE_TEST_EMAIL"; 
      exit 1 
    }
    if (-not "$env:SMOKE_TEST_PASSWORD") { 
      Write-Error "Missing SMOKE_TEST_PASSWORD"; 
      exit 1 
    }

- name: Account Deletion Smoke Test
  shell: pwsh
  env:
    SMOKE_TEST_EMAIL: ${{ secrets.SMOKE_TEST_EMAIL }}
    SMOKE_TEST_PASSWORD: ${{ secrets.SMOKE_TEST_PASSWORD }}
  run: |
    ./scripts/smoke_endpoints.ps1 `
      -BASE "https://babyshield.cureviax.ai" `
      -Csv "smoke/endpoints.smoke.csv"
```

### Test Scenarios

The smoke tests validate:
1. ✅ User registration with test account
2. ✅ User login with test credentials
3. ✅ Account deletion functionality
4. ✅ Data purge verification
5. ✅ Cleanup operations

---

## 📊 VERIFICATION CHECKLIST

After adding secrets, verify they work:

### **Step 1: Check Secrets Are Set**
```bash
# List repository secrets (names only, not values)
gh secret list
```

**Expected Output:**
```
SMOKE_TEST_EMAIL        Updated YYYY-MM-DD
SMOKE_TEST_PASSWORD     Updated YYYY-MM-DD
```

### **Step 2: Trigger Workflow**
```bash
# Manually trigger CI workflow
gh workflow run ci.yml
```

### **Step 3: Monitor Workflow**
```bash
# Watch workflow status
gh run watch
```

### **Step 4: Check for Errors**
```bash
# View workflow logs
gh run view --log
```

**Success Indicators:**
- ✅ No "Missing SMOKE_TEST_EMAIL" error
- ✅ No "Missing SMOKE_TEST_PASSWORD" error
- ✅ Account deletion tests pass
- ✅ Workflow completes successfully

---

## 🐛 TROUBLESHOOTING

### Error: "Missing SMOKE_TEST_EMAIL"

**Cause:** Secret not configured in GitHub repository settings

**Solution:**
1. Go to repository Settings > Secrets and variables > Actions
2. Add `SMOKE_TEST_EMAIL` secret with test email
3. Re-run workflow

### Error: "Missing SMOKE_TEST_PASSWORD"

**Cause:** Secret not configured in GitHub repository settings

**Solution:**
1. Go to repository Settings > Secrets and variables > Actions
2. Add `SMOKE_TEST_PASSWORD` secret with test password
3. Re-run workflow

### Error: "Authentication failed" (401)

**Cause:** Test account credentials are incorrect or account doesn't exist

**Solution:**
1. Verify test account exists in production
2. Register account if needed (see Test Account Setup)
3. Update GitHub secrets with correct credentials
4. Re-run workflow

### Error: "Account not found" (404)

**Cause:** Test account was deleted or doesn't exist

**Solution:**
1. Create new test account (see Test Account Setup)
2. Update GitHub secrets with new credentials
3. Re-run workflow

---

## 🔄 SECRET ROTATION SCHEDULE

### Recommended Rotation

| Secret | Rotation Frequency | Next Due |
|--------|-------------------|----------|
| SMOKE_TEST_EMAIL | When account compromised | As needed |
| SMOKE_TEST_PASSWORD | Every 90 days | Jan 17, 2026 |

### Rotation Process

1. **Create new test account** (optional - or just change password)
2. **Update GitHub secrets:**
   ```bash
   gh secret set SMOKE_TEST_EMAIL --body "new-test@example.com"
   gh secret set SMOKE_TEST_PASSWORD --body "NewSecurePassword123!"
   ```
3. **Trigger test workflow** to verify
4. **Document rotation** in team notes
5. **Archive old credentials** securely

---

## 📚 ADDITIONAL SECRETS (OPTIONAL)

### Future Secrets You May Need

These are not currently required but may be needed for future workflows:

#### **AWS Credentials** (for deployment workflows)
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`

#### **Database Credentials** (for migration workflows)
- `DATABASE_URL`
- `DATABASE_PASSWORD`

#### **API Keys** (for external integrations)
- `OPENAI_API_KEY`
- `GOOGLE_CLOUD_VISION_API_KEY`

#### **Notification Services**
- `SLACK_WEBHOOK_URL`
- `DISCORD_WEBHOOK_URL`

---

## ✅ IMMEDIATE ACTION ITEMS

### **URGENT: Add These Secrets Now**

- [ ] **Add SMOKE_TEST_EMAIL to GitHub Secrets**
  - Go to: https://github.com/BabyShield/babyshield-backend/settings/secrets/actions
  - Add secret with test email

- [ ] **Add SMOKE_TEST_PASSWORD to GitHub Secrets**
  - Go to: https://github.com/BabyShield/babyshield-backend/settings/secrets/actions
  - Add secret with test password

- [ ] **Verify test account exists in production**
  - Register at https://babyshield.cureviax.ai if needed
  - Confirm login works

- [ ] **Re-run failed CI workflow**
  - Go to: https://github.com/BabyShield/babyshield-backend/actions
  - Click "Re-run all jobs"

- [ ] **Monitor workflow success**
  - Check all jobs pass
  - Verify no secret-related errors

---

## 📞 SUPPORT

### If You Need Help

**GitHub Actions Issues:**
- Check workflow logs: `gh run view --log`
- Re-run failed jobs: `gh run rerun <run-id>`

**Secret Management Issues:**
- GitHub Docs: https://docs.github.com/en/actions/security-guides/encrypted-secrets
- Team Contact: dev@babyshield.dev

**Test Account Issues:**
- Registration: POST https://babyshield.cureviax.ai/api/v1/auth/register
- Reset Password: POST https://babyshield.cureviax.ai/api/v1/auth/password-reset

---

## 📋 SUMMARY

### Current Status: ❌ **SECRETS MISSING**

**Required Actions:**
1. Add `SMOKE_TEST_EMAIL` to GitHub Secrets ⏳
2. Add `SMOKE_TEST_PASSWORD` to GitHub Secrets ⏳
3. Create test account if needed ⏳
4. Re-run CI workflow ⏳

### Once Complete: ✅ **CI/CD READY**

**Expected Result:**
- ✅ All CI workflows pass
- ✅ Smoke tests execute successfully
- ✅ No secret-related errors
- ✅ Automated testing functional

---

**Last Updated:** October 19, 2025  
**Document Owner:** DevOps Team  
**Next Review:** January 17, 2026
