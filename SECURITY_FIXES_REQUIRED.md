# Security Fixes Required - Action Items

## ✅ FIXED IN THIS PR

### 1. ✅ Firebase Service Account Key Removed
- **File:** `secrets/serviceAccountKey.json`
- **Action:** Removed from git tracking
- **Status:** COMPLETE
- **Next:** Manually revoke in Google Cloud Console

### 2. ✅ .gitignore Updated
- **Added patterns:**
  - `secrets/`
  - `serviceAccountKey.json`
  - `*.pem`, `*.key`, `*.crt`
  - `*_secret.json`, `*_credentials.json`
  - `.env.production`, `.env.staging`
- **Status:** COMPLETE

### 3. ✅ Duplicate Files Removed
- **Removed:**
  - `security/monitoring_dashboard.py` (duplicate)
  - `services/dev_override.py` (duplicate)
  - `services/search_service.py` (duplicate)
- **Kept:** Active versions in `api/` directories
- **Status:** COMPLETE

---

## ⚠️ REQUIRES MANUAL REVIEW (Do Not Auto-Fix)

### 4. ⚠️ Dangerous Function Usage

**Files with eval() - MANUAL REVIEW NEEDED:**

1. **`scripts/run_synth_eval.py:20`**
   ```python
   scan_data = eval(scan_text)  # nosec - controlled CI fixture only
   ```
   - **Context:** CI fixture, marked nosec
   - **Risk:** LOW (controlled environment)
   - **Action:** Keep as-is (CI only), do NOT fix automatically

2. **`scripts/analyze_memory_planner_test.py:445`**
   ```python
   extracted_entities = eval(match.group(1))
   ```
   - **Risk:** MEDIUM
   - **Recommended:** Replace with `ast.literal_eval()` or JSON parsing
   - **Action:** MANUAL code review required

**Files with shell=True - MANUAL REVIEW NEEDED:**

1. **`scripts/restart_check2.py:10`**
   ```python
   subprocess.run(f"taskkill /F /FI \"WINDOWTITLE eq {agent}*\"", shell=True, ...)
   ```
   - **Risk:** HIGH (command injection if agent is user-controlled)
   - **Recommended:** Use subprocess with list args, not shell=True
   - **Action:** MANUAL code review required

2. **`scripts/setup_and_test.py:20`**
   ```python
   result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
   ```
   - **Risk:** MEDIUM (depends on cmd source)
   - **Recommended:** Use shell=False with command list
   - **Action:** MANUAL code review required

---

### 5. ⚠️ Environment Variable Logging

**Files that may log sensitive data:**
- `agents/*/agent_logic.py` (multiple instances)
- `api/main_babyshield.py` (lines 140, 227, 334, 347, 847)

**Recommendation:** Audit each instance to ensure:
- No passwords/API keys are logged
- Use structured logging with secret redaction
- Mask sensitive values before logging

**Action:** MANUAL code review and selective fixes required

---

### 6. ⚠️ DEBUG Mode Configuration

**File:** `config/docker/docker-compose.dev.yml:16`
```yaml
- DEBUG=true
```

**Current Status:** This is DEVELOPMENT configuration (correct)

**Action Required:**
- ✅ Verify production environment has `DEBUG=false`
- ✅ Add validation to prevent DEBUG=true in production
- ⚠️ Do NOT change dev config automatically

---

## 🔒 POST-DEPLOYMENT ACTIONS REQUIRED

### 7. Revoke Firebase Service Account Key

**MANUAL ACTION REQUIRED:**

1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts?project=babyshield-8f552
2. Find service account: `firebase-adminsdk-fbsvc@babyshield-8f552.iam.gserviceaccount.com`
3. Click on service account
4. Go to "Keys" tab
5. Find key with ID: `f9d6fbee209506ae0c7d96f3c93ce233048013f6`
6. Click "Delete" and confirm

**THEN:**
7. Create new service account with minimal permissions
8. Download new key and store securely (NOT in git)
9. Update environment variables in production
10. Audit Firebase logs for unauthorized access

---

### 8. Audit Firebase Access Logs

**MANUAL ACTION REQUIRED:**

1. Go to Google Cloud Console → Logging
2. Filter logs for service account: `firebase-adminsdk-fbsvc@babyshield-8f552.iam.gserviceaccount.com`
3. Check for access from unknown IPs/locations
4. Look for suspicious database queries
5. Check for unauthorized Cloud Function deployments

**Time Range to Check:**
- From: First commit of `serviceAccountKey.json` to git
- To: Now

---

### 9. Security Scanning Setup

**Add to CI/CD pipeline:**

```yaml
# Add to .github/workflows/security-scan.yml
- name: Run Bandit Security Scan
  run: |
    pip install bandit
    bandit -r . -f json -o bandit-report.json
    
- name: Check for Secrets
  run: |
    pip install detect-secrets
    detect-secrets scan --baseline .secrets.baseline
    
- name: Dependency Vulnerability Scan
  run: |
    pip install safety
    safety check --json
```

---

## 📋 SUMMARY

Category | Status | Action
----------|--------|--------
Firebase Key Removed | ✅ FIXED | Manual revocation required
.gitignore Updated | ✅ FIXED | Complete
Duplicate Files | ✅ FIXED | Complete
eval() Usage | ⚠️ REVIEW | Manual code review
shell=True Usage | ⚠️ REVIEW | Manual code review
Env Var Logging | ⚠️ REVIEW | Manual audit
DEBUG Config | ⚠️ VERIFY | Verify production
Firebase Audit | ⚠️ TODO | Post-deployment
Security Scanning | ⚠️ TODO | CI/CD enhancement

---

**This PR fixes immediate critical issues. Additional items require manual review to avoid breaking functionality.**

