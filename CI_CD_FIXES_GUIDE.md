# CI/CD Fixes Guide

This guide addresses the three main CI/CD failures and provides solutions.

## ✅ Issue 1: Code Formatting (FIXED)

**Problem:** 467 files needed reformatting, 2 files failed to reformat, exit code 123.

**Solution Applied:**
1. ✅ Fixed FamilyMember model import error
2. ✅ Ran `ruff format .` successfully
3. ✅ Committed changes

**Status:** RESOLVED ✅

## ⚠️ Issue 2: Missing GitHub Secrets

**Problem:** `SMOKE_TEST_EMAIL` and `SMOKE_TEST_PASSWORD` environment variables missing.

**Root Cause:** The workflow `.github/workflows/ci.yml` expects these secrets for the smoke test job, but they are not configured in the repository.

### Solution: Set GitHub Secrets

#### Option A: Via GitHub Web UI

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

   **Secret 1:**
   - Name: `SMOKE_TEST_EMAIL`
   - Value: `test-account@crownsafe-test.com` (or your test account email)

   **Secret 2:**
   - Name: `SMOKE_TEST_PASSWORD`
   - Value: Your secure test password (e.g., `TestPassword123!Secure`)

#### Option B: Via GitHub CLI

```bash
# Install GitHub CLI if not already installed
# https://cli.github.com/

# Authenticate
gh auth login

# Set secrets
gh secret set SMOKE_TEST_EMAIL --body "test-account@crownsafe-test.com"
gh secret set SMOKE_TEST_PASSWORD --body "YourSecureTestPassword123!"

# Verify secrets were set
gh secret list
```

#### Option C: Skip Authentication Tests (Temporary)

If you don't want to set up test credentials, you can modify the workflow to skip authentication-dependent tests:

**File:** `.github/workflows/ci.yml`

```yaml
# Change this job condition from true to false
smoke-account-deletion:
  if: ${{ false }}  # Disable until secrets are configured
  name: Smoke — Account Deletion
  # ... rest of job
```

### Verification

After setting secrets, verify they work:

```bash
# Trigger workflow manually
gh workflow run ci.yml

# Check workflow status
gh run list --workflow=ci.yml --limit 1

# View logs
gh run view --log
```

**Expected Result:** No "Missing SMOKE_TEST_EMAIL" error

## ✅ Issue 3: FamilyMember Import Error (FIXED)

**Problem:** `ImportError: cannot import name 'FamilyMember' from 'core_infra.database'`

**Solution Applied:**
1. ✅ Added `FamilyMember` model to `core_infra/database.py`
2. ✅ Added `Allergy` model to `core_infra/database.py`
3. ✅ Updated database schema to support family member tracking
4. ✅ Committed changes

**Code Added:**
```python
class FamilyMember(Base):
    """Family member profile for multi-user household management"""
    __tablename__ = "family_members"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)

class Allergy(Base):
    """Allergy tracking for family members"""
    __tablename__ = "allergies"
    id = Column(Integer, primary_key=True, index=True)
    allergen = Column(String, nullable=False)
    member_id = Column(Integer, nullable=False)
```

**Status:** RESOLVED ✅

## Summary of Fixes

| Issue               | Status  | Action Required                              |
| ------------------- | ------- | -------------------------------------------- |
| Code Formatting     | ✅ FIXED | None - Already committed                     |
| FamilyMember Import | ✅ FIXED | None - Already committed                     |
| GitHub Secrets      | ⚠️ TODO  | Set SMOKE_TEST_EMAIL and SMOKE_TEST_PASSWORD |

## Next Steps

### 1. Set GitHub Secrets (Required)

Follow **Option A** or **Option B** above to set the required secrets.

### 2. Re-run Failed Workflows

After setting secrets, trigger the workflows again:

```bash
# Via GitHub CLI
gh workflow run ci.yml
gh workflow run ci-smoke-schedule.yml

# Or via GitHub Web UI
# Go to Actions → Select workflow → Run workflow
```

### 3. Monitor Workflow Status

```bash
# Check latest runs
gh run list --limit 5

# Watch a specific run
gh run watch <run-id>

# View detailed logs
gh run view <run-id> --log
```

## Troubleshooting

### Secrets Not Working After Setting

1. **Verify secrets are set:**
   ```bash
   gh secret list
   ```
   Should show:
   ```
   SMOKE_TEST_EMAIL        Updated YYYY-MM-DD
   SMOKE_TEST_PASSWORD     Updated YYYY-MM-DD
   ```

2. **Check secret names are exact:**
   - Must be `SMOKE_TEST_EMAIL` (not `smoke_test_email`)
   - Must be `SMOKE_TEST_PASSWORD` (not `smoke_test_password`)

3. **Ensure secrets are available in workflow:**
   ```yaml
   env:
     SMOKE_TEST_EMAIL: ${{ secrets.SMOKE_TEST_EMAIL }}
     SMOKE_TEST_PASSWORD: ${{ secrets.SMOKE_TEST_PASSWORD }}
   ```

### Workflow Still Failing

1. **Check workflow file syntax:**
   ```bash
   gh workflow view ci.yml
   ```

2. **Review error logs:**
   ```bash
   gh run list --workflow=ci.yml --limit 1
   gh run view <run-id> --log
   ```

3. **Test locally before pushing:**
   ```bash
   # Set environment variables locally
   export SMOKE_TEST_EMAIL="test@example.com"
   export SMOKE_TEST_PASSWORD="TestPass123"
   
   # Run the test script
   pytest ci_smoke/test_ci_smoke.py
   ```

## Additional Resources

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [Workflow Troubleshooting](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows)

---

**Last Updated:** October 31, 2025  
**Status:** 2 of 3 issues resolved, secrets setup pending
