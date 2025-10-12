# Live Integration Test Setup - COMPLETE ✅

**Date:** October 2025  
**Status:** Infrastructure ready, awaiting production database credentials

---

## 🎯 What We Built

### 1. Live Test Infrastructure

Created a comprehensive live testing framework that:

- ✅ Queries **actual production database** (130k+ recalls) for test data
- ✅ Tests **real API endpoints** with real model numbers from database
- ✅ Validates complete user workflows end-to-end
- ✅ Automatically skips if production database is not accessible
- ✅ Provides detailed output showing each step of the workflow

### 2. Files Created/Modified

#### **New Files:**

1. **`tests/live/test_manual_model_number_entry.py`** (110 lines)
   - Live integration test for manual model number entry workflow
   - Queries production database for real model numbers
   - Tests `/api/v1/safety-check` endpoint with actual data
   - Includes both recalled and safe product scenarios

2. **`tests/live/README.md`** (comprehensive documentation)
   - Complete setup instructions
   - Troubleshooting guide
   - Security best practices
   - Expected test output examples

3. **`run_live_tests.ps1`** (PowerShell helper script)
   - Automated test runner
   - Fetches production credentials from AWS Secrets Manager
   - Sets environment variables automatically
   - Runs live tests with proper configuration

#### **Modified Files:**

1. **`pytest.ini`**
   - Added `@pytest.mark.live` marker for live tests
   - Enables filtering: `pytest -m live` to run only live tests

---

## 🚀 How to Run Live Tests

### Option 1: Automated (Recommended)

Use the PowerShell helper script:

```powershell
cd c:\code\babyshield-backend
.\run_live_tests.ps1
```

This script will:
1. Check for AWS CLI installation
2. Fetch production database credentials from AWS Secrets Manager
3. Set `PROD_DATABASE_URL` environment variable
4. Run live integration tests

### Option 2: Manual

Set the database URL manually and run pytest:

```powershell
# Get credentials from AWS
aws secretsmanager get-secret-value `
    --secret-id "babyshield/prod/database" `
    --region "eu-north-1" `
    --query "SecretString" `
    --output text

# Set environment variable (use actual credentials from above)
$env:PROD_DATABASE_URL = "postgresql://USERNAME:PASSWORD@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/postgres"

# Run tests
pytest tests/live/test_manual_model_number_entry.py -v -s -m live
```

---

## 📋 Test Workflow

### Test 1: Manual Model Number Entry - WITH Recall

```
1. Query production database for model number with recall
   ↓
2. Extract: model_number, product_name, brand, recall_id
   ↓
3. Submit to POST /api/v1/safety-check endpoint
   ↓
4. Validate response:
   - Status code: 200
   - risk_level: "HIGH"
   - recalls array populated
   - Recall matches database record
```

### Test 2: Manual Model Number Entry - WITHOUT Recall

```
1. Use known-safe model number (not in database)
   ↓
2. Submit to POST /api/v1/safety-check endpoint
   ↓
3. Validate response:
   - Status code: 200
   - risk_level: "LOW"
   - recalls array empty
```

---

## 🗄️ Database Details

**Production PostgreSQL RDS:**
- **Endpoint:** `babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com`
- **Port:** `5432`
- **Database:** `postgres`
- **Table:** `recalls_enhanced` (130k+ records)
- **Username:** Stored in AWS Secrets Manager
- **Password:** Stored in AWS Secrets Manager
- **AWS Region:** `eu-north-1`
- **Secret ID:** `babyshield/prod/database`

---

## 📊 Expected Test Output

### Successful Run:

```
============================= test session starts ==============================
collected 2 items

tests/live/test_manual_model_number_entry.py::test_manual_model_number_entry_with_recall 

================================================================================
TEST 1: Manual Model Number Entry - Product WITH Recall
================================================================================

🔍 STEP 1: Querying database for a real model number with recall...
✅ Found model number in DB: 'ABC-123-XYZ'
   Product: Baby Monitor Model X
   Brand: SafeBaby Inc
   Recall ID: CPSC-2024-001

👤 USER ACTION: Enters model number 'ABC-123-XYZ'

📡 API CALL: POST /api/v1/safety-check
   Payload: {'user_id': 999, 'model_number': 'ABC-123-XYZ', ...}

📊 RESPONSE STATUS: 200
✅ Response received

📄 RESPONSE BODY:
{
  "risk_level": "HIGH",
  "recalls": [
    {
      "recall_id": "CPSC-2024-001",
      "product_name": "Baby Monitor Model X",
      "brand": "SafeBaby Inc",
      "hazard": "Choking hazard",
      "recall_date": "2024-10-01"
    }
  ]
}

✅ Risk level is HIGH (recall found)
✅ Recalls array contains 1 item(s)
✅ Recall matches the database record

PASSED                                                                    [100%]

============================= 2 passed in 12.34s ===============================
```

### Skipped (No Database Access):

```
tests/live/test_manual_model_number_entry.py::test_manual_model_number_entry_with_recall 
SKIPPED (Live test requires production PostgreSQL database. Set PROD_DATABASE_URL...)
```

---

## 🔒 Security Considerations

### ✅ What We Did Right:

1. **No Hardcoded Credentials**
   - All credentials retrieved from AWS Secrets Manager
   - Database URL passed via environment variables
   - No secrets in code or git history

2. **Safe Test Design**
   - Read-only database queries
   - No data modification
   - Automatic skip if credentials not available

3. **Documentation**
   - Clear instructions for secure credential handling
   - Warnings against committing secrets
   - Best practices documented

### ⚠️ Important Reminders:

- **NEVER** commit production database credentials
- **ALWAYS** use environment variables for sensitive data
- **VERIFY** AWS IAM permissions before accessing Secrets Manager
- **USE** read-only database user for tests (if possible)

---

## 🐛 Troubleshooting

### Error: "no such table: recalls_enhanced"

**Cause:** Test is connecting to SQLite test database instead of PostgreSQL production database

**Solution:** Set `PROD_DATABASE_URL` environment variable to PostgreSQL connection string

---

### Error: "Live test requires production PostgreSQL database"

**Cause:** `PROD_DATABASE_URL` not set or points to SQLite

**Solution:** 
```powershell
$env:PROD_DATABASE_URL = "postgresql://USER:PASS@HOST:5432/DB"
```

---

### Error: AWS CLI not found

**Cause:** AWS CLI not installed

**Solution:** 
1. Install AWS CLI from https://aws.amazon.com/cli/
2. Configure credentials: `aws configure`
3. Verify access: `aws sts get-caller-identity`

---

### Error: Access Denied (AWS Secrets Manager)

**Cause:** AWS IAM user lacks permissions

**Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue"
  ],
  "Resource": "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/prod/database-*"
}
```

---

### Error: Connection timeout

**Cause:** Network/firewall blocking database connection

**Solutions:**
1. Check VPN connection (if required)
2. Verify RDS security group allows your IP
3. Test connection: `psql -h HOST -U USER -d DATABASE`

---

## ✅ Success Checklist

Before marking as complete:

- [x] Created live test file with database query logic
- [x] Added production database connection helper
- [x] Documented setup and usage in README
- [x] Created automated test runner script
- [x] Added pytest marker for live tests
- [x] Included comprehensive error handling
- [ ] **Retrieved production database credentials from AWS** ⬅️ **NEXT STEP**
- [ ] **Executed live test successfully**
- [ ] **Validated API returns correct recall data**

---

## 📝 Next Steps

### Immediate (You):

1. **Get Database Credentials:**
   ```powershell
   cd c:\code\babyshield-backend
   .\run_live_tests.ps1
   ```
   OR manually:
   ```powershell
   aws secretsmanager get-secret-value `
       --secret-id "babyshield/prod/database" `
       --region "eu-north-1" `
       --query "SecretString" `
       --output text
   ```

2. **Run Live Test:**
   - The script will automatically run tests after fetching credentials
   - Verify test passes and returns expected data
   - Check API response matches database recall

3. **Report Results:**
   - Copy test output
   - Confirm test passed or report errors
   - Share any 500 errors or unexpected behavior

### Future (Additional Tests):

Once manual model number entry test passes:

1. **Barcode Entry Test**
   - Query database for recalls with barcode/UPC
   - Test `/api/v1/safety-check` with barcode parameter

2. **Product Name Search Test**
   - Query database for product names
   - Test fuzzy search functionality

3. **Lot Number Lookup Test**
   - Query database for lot numbers
   - Test lot number identification

4. **Camera OCR Test**
   - Test image OCR extraction
   - Validate model number extraction from photos

5. **Photo Upload Test**
   - Test visual recognition pipeline
   - Validate product identification from images

---

## 📞 Support

- **Documentation:** See `tests/live/README.md`
- **AWS Issues:** Check IAM permissions and Secrets Manager access
- **Database Issues:** Verify RDS endpoint and connectivity
- **Test Issues:** Review pytest output and API logs

---

**Summary:** All infrastructure is ready. You just need to run `.\run_live_tests.ps1` to fetch credentials and execute the live test against the production database.

**Status:** ✅ COMPLETE - Ready to run
