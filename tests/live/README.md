# Live Integration Tests

This directory contains **live integration tests** that interact with the actual production database and real API endpoints.

## ⚠️ Prerequisites

### 1. Production Database Access

Live tests require access to the production PostgreSQL database with 130k+ recalls.

Set the `PROD_DATABASE_URL` environment variable:

```powershell
# PowerShell
$env:PROD_DATABASE_URL = "postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE"

# Example (use your actual credentials):
$env:PROD_DATABASE_URL = "postgresql://admin:your_password@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/postgres"
```

### 2. Required Packages

Ensure you have installed all dependencies:

```bash
pip install -r config/requirements/requirements.txt
```

## 🧪 Running Live Tests

### Run All Live Tests

```bash
pytest tests/live/ -v -s -m live
```

### Run Specific Test

```bash
# Manual model number entry
pytest tests/live/test_manual_model_number_entry.py -v -s

# With detailed output
pytest tests/live/test_manual_model_number_entry.py::test_manual_model_number_entry_with_recall -v -s
```

### Skip Live Tests in CI

Live tests are automatically skipped if `PROD_DATABASE_URL` is not set or points to SQLite:

```python
if not prod_url or prod_url.startswith("sqlite"):
    pytest.skip("Live test requires production PostgreSQL database.")
```

## 📋 Available Live Tests

### 1. `test_manual_model_number_entry.py`

Tests the manual model number entry workflow:

- **Test 1:** Model number WITH recall (HIGH risk)
- **Test 2:** Model number WITHOUT recall (LOW risk)

**What it does:**
1. Queries production database for real model numbers
2. Submits to `/api/v1/safety-check` endpoint
3. Validates response structure and recall data

### Coming Soon

- `test_barcode_entry.py` - Barcode scanning workflow
- `test_product_name_search.py` - Product name search workflow
- `test_lot_number_search.py` - Lot number lookup workflow
- `test_camera_ocr.py` - Camera OCR extraction workflow
- `test_photo_upload.py` - Photo upload identification workflow

## 🔒 Security Notes

- **Never commit** production database credentials
- Use environment variables for all sensitive data
- Production database URL should be stored in AWS Secrets Manager
- Tests should use read-only database access

## 🏗️ Database Connection Details

Production RDS Endpoint:
- **Host:** `babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com`
- **Port:** `5432`
- **Database:** `postgres`
- **Username:** (stored in AWS Secrets Manager)
- **Password:** (stored in AWS Secrets Manager)

## 📊 Expected Test Output

### Successful Test Run

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
  "recalls": [...],
  "product_info": {...}
}

✅ Risk level is HIGH (recall found)
✅ Recalls array contains 1 item(s)
✅ Recall matches the database record

PASSED
```

### Skipped Test (No Database Access)

```
tests/live/test_manual_model_number_entry.py::test_manual_model_number_entry_with_recall 
SKIPPED (Live test requires production PostgreSQL database. Set PROD_DATABASE_URL...)
```

## 🐛 Troubleshooting

### Test Skipped - SQLite Detected

**Problem:** Test is skipped even though you set `PROD_DATABASE_URL`

**Solution:** Ensure the URL starts with `postgresql://` (not `sqlite://`)

### Connection Timeout

**Problem:** Test hangs or times out connecting to database

**Solution:** 
- Verify you're on the correct network (VPN if required)
- Check database security group allows your IP
- Verify database endpoint and port are correct

### No Model Numbers Found

**Problem:** Test returns "No model numbers found in database"

**Solution:**
- Verify production database actually has data
- Check `recalls_enhanced` or `recalls` table exists
- Ensure `model_number` column has non-null values

### 500 Error from API

**Problem:** API returns 500 Internal Server Error

**Solution:**
- Check API logs for detailed error message
- Verify the API server is running and accessible
- Ensure database migrations are up to date
- Check that agents are properly configured

## 📞 Support

For issues with live tests:
- Check CloudWatch logs for production API errors
- Verify database connectivity with `psql` or pgAdmin
- Contact dev team for database credentials if needed

---

**Last Updated:** October 2025
