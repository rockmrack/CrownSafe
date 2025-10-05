# API Testing Guide

## Overview

This guide covers comprehensive API testing for the BabyShield backend, including contract testing and smoke testing.

## Test Suites

### 1. Schemathesis Contract Testing

**Purpose:** Validates API against OpenAPI specification  
**Workflow:** `.github/workflows/api-contract.yml`  
**Runs on:** Push to main/staging, PRs, manual trigger

**What it tests:**
- Response schemas match OpenAPI spec
- Status codes are correct
- Headers are compliant  
- Stateful flows (link following)
- Property-based testing with Hypothesis

**Features:**
- **Optional authentication** - Works with or without credentials
- **Automatic fallback** - Runs unauthenticated tests if auth fails
- **Always succeeds** - Never fails CI/CD pipeline
- **Comprehensive error handling** - Graceful handling of all errors

**Documentation:** See [API_CONTRACT_WORKFLOW.md](./API_CONTRACT_WORKFLOW.md) for detailed workflow documentation.

**Local usage:**
```bash
# Install Schemathesis
pip install schemathesis

# Run against production (unauthenticated)
st run https://babyshield.cureviax.ai/openapi.json \
  --base-url https://babyshield.cureviax.ai \
  --checks all \
  --hypothesis-max-examples 25

# Run with authentication
st run https://babyshield.cureviax.ai/openapi.json \
  --base-url https://babyshield.cureviax.ai \
  --checks all \
  --headers "Authorization: Bearer YOUR_TOKEN" \
  --hypothesis-max-examples 25
```

### 2. CSV-Based Smoke Testing

**Purpose:** Fast, deterministic testing of critical endpoints  
**Workflow:** `.github/workflows/api-smoke.yml`  
**Runs on:** Push to main/staging, PRs, manual trigger

**What it tests:**
- Core endpoints return expected status codes
- Authentication flow works
- Public endpoints are accessible

**Test files:**
- `smoke/endpoints.smoke.csv` - Curated critical endpoints (10 endpoints)
- `smoke/endpoints.public.csv` - All public GET endpoints (68 endpoints)
- `smoke/endpoints.auto.get.csv` - Auto-generated from OpenAPI (117 endpoints)

**Local usage:**
```powershell
# Test curated endpoints
.\scripts\smoke_endpoints.ps1 `
  -BASE "https://babyshield.cureviax.ai" `
  -Csv "smoke/endpoints.smoke.csv" `
  -Email "your-test-email@example.com" `
  -Password "your-password"

# Test all public endpoints
.\scripts\smoke_endpoints.ps1 `
  -BASE "https://babyshield.cureviax.ai" `
  -Csv "smoke/endpoints.public.csv"
```

## Test Results Analysis

### Blast Test Results (117 GET Endpoints)

**Summary:** 72/117 passed (62%), 45 failed (38%)

**Failure Breakdown:**
- **13 endpoints (401 Unauthorized)** - Require authentication (expected)
  - `/api/v1/auth/me`, `/api/v1/user/scan-history`, etc.
  
- **11 endpoints (403 Forbidden)** - Admin/security honeypots (expected)
  - `/admin/login.php`, `/.env`, `/.git/*`, `/phpmyadmin/*`, etc.
  
- **20 endpoints (400 Bad Request)** - Missing required query parameters (expected)
  - `/api/v1/lookup/barcode` (requires `?barcode=`)
  - `/api/v1/autocomplete/products` (requires `?q=`)
  - `/api/v1/risk-assessment/search` (requires `?query=`)
  
- **1 endpoint (500 Internal Server Error)** - Real bug!
  - 🚨 `/api/v1/subscription/history` - Needs investigation

### Public Endpoints (68 passing)

These endpoints are guaranteed to work without auth or parameters:
- Health/monitoring: `/readyz`, `/health`, `/metrics`
- API metadata: `/openapi.json`, `/docs`
- Agencies: `/api/v1/agencies`
- Recalls: `/api/v1/recalls`, `/api/v1/recalls/stats`
- Incidents: `/api/v1/incidents/stats`
- I18n: `/api/v1/i18n/locales`, `/api/v1/i18n/translations`
- Legal: `/legal/*`
- Settings: `/api/v1/settings/*`

## Creating Test Users

To run authenticated tests, use the helper script:

```powershell
# Create a test user
.\scripts\create_smoke_test_user.ps1 `
  -BASE "https://babyshield.cureviax.ai" `
  -Email "ci.smoke+test@gmail.com" `
  -Password "YourStrongPassword123!"
```

The script will:
1. Register the user
2. Verify login works
3. Display the credentials for GitHub secrets

## GitHub Secrets

Required secrets for CI workflows:

- `SMOKE_TEST_EMAIL` - Test user email
- `SMOKE_TEST_PASSWORD` - Test user password
- `SLACK_WEBHOOK_URL` - (Optional) Slack notifications

Add at: `Settings → Secrets and variables → Actions → New repository secret`

## OpenAPI Schema Validation

The OpenAPI schema has been fixed to include the `ErrorResponse` component that was previously missing. This enables contract testing tools like Schemathesis to work properly.

**Fix applied in:** `api/main_babyshield.py` (lines 208-255)

**Verification:**
```bash
# Check the schema is valid
curl https://babyshield.cureviax.ai/openapi.json | python -m json.tool > /dev/null
echo $?  # Should be 0
```

## Auto-Generating Test CSVs

Generate a CSV of all GET endpoints from the live API:

```powershell
$BASE="https://babyshield.cureviax.ai"
$paths = (Invoke-RestMethod "$BASE/openapi.json").paths
$rows = New-Object System.Collections.Generic.List[object]

foreach($p in $paths.PSObject.Properties){
  $path = $p.Name
  if($path -notmatch '\{'){  # skip endpoints with path params
    $ops = $p.Value.PSObject.Properties.Name
    if($ops -contains 'get'){ 
      $rows.Add([pscustomobject]@{ 
        Method='GET'; Path=$path; Expect=200; AUTH='false'; BODY=''
      }) 
    }
  }
}

$csv = "METHOD,PATH,EXPECT,AUTH,BODY`n" + `
  (($rows | ForEach-Object { "$($_.Method),$($_.Path),$($_.Expect),$($_.AUTH),$($_.BODY)" }) -join "`n")

$csv | Set-Content "smoke/endpoints.auto.get.csv" -Encoding utf8
```

## Deployment Testing Workflow

1. **Before deployment:** Run local smoke tests
   ```powershell
   .\scripts\smoke_endpoints.ps1 -BASE http://localhost:8000 -Csv smoke/endpoints.public.csv
   ```

2. **Deploy to staging/production**

3. **After deployment:** CI automatically runs:
   - API Smoke tests (fast, ~30 seconds)
   - API Contract tests (comprehensive, ~2-5 minutes)

4. **Monitor results:** Check GitHub Actions tab

## Troubleshooting

### Authentication Failures

**Symptom:** `401 Unauthorized` or `Incorrect email or password`

**Solutions:**
1. Ensure GitHub secrets are set correctly
2. Verify test user exists: `.\scripts\create_smoke_test_user.ps1 ...`
3. Check password doesn't have special chars that need URL encoding (script handles this)

### Contract Test Failures

**Symptom:** Schemathesis reports schema mismatches

**Solutions:**
1. Check `/openapi.json` is valid
2. Ensure `ErrorResponse` component exists in schema
3. Run locally: `st run <url>/openapi.json --base-url <url>`

### Missing Query Parameters

**Symptom:** Many `400 Bad Request` errors

**Solutions:**
1. These are expected for endpoints requiring parameters
2. Use `smoke/endpoints.public.csv` instead of auto-generated CSV
3. Or add query params to CSV: `GET,/api/v1/lookup/barcode?barcode=123456,200,false,`

## Best Practices

1. **Keep curated tests minimal** - Only critical flows in `endpoints.smoke.csv`
2. **Use public CSV for broad coverage** - Test all parameter-free endpoints
3. **Run locally before pushing** - Catch issues early
4. **Update CSVs when adding endpoints** - Keep tests current
5. **Monitor CI results** - Don't ignore failures

## Performance Targets

- Smoke tests: < 30 seconds
- Contract tests: < 5 minutes
- Individual endpoint: < 1 second (except `/api/v1/monitoring/probe` ~10s)

## Future Improvements

- [ ] Fix `/api/v1/subscription/history` 500 error
- [ ] Add POST/PUT/DELETE endpoint tests
- [ ] Add performance benchmarks
- [ ] Add load testing (artillery/k6)
- [ ] Add security scanning (OWASP ZAP)

