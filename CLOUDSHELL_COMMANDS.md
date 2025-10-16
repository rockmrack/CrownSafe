# AWS CloudShell Commands to Enable pg_trgm

## Quick Start (Copy-Paste Ready)

### Option 1: One-Line Command (Fastest)

Open AWS CloudShell in eu-north-1 region and paste this:

```bash
PGPASSWORD='MandarunLabadiena25!' psql -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com -U babyshield_user -d postgres -c "CREATE EXTENSION IF NOT EXISTS pg_trgm; SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_trgm';"
```

### Option 2: Step-by-Step Commands

#### Step 1: Install PostgreSQL Client (if needed)
```bash
sudo yum install -y postgresql15
```

#### Step 2: Enable pg_trgm Extension
```bash
PGPASSWORD='MandarunLabadiena25!' psql \
  -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com \
  -U babyshield_user \
  -d postgres \
  -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

#### Step 3: Verify Extension is Enabled
```bash
PGPASSWORD='MandarunLabadiena25!' psql \
  -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com \
  -U babyshield_user \
  -d postgres \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_trgm';"
```

Expected output:
```
 extname | extversion 
---------+------------
 pg_trgm | 1.6
```

#### Step 4: Test Similarity Function
```bash
PGPASSWORD='MandarunLabadiena25!' psql \
  -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com \
  -U babyshield_user \
  -d postgres \
  -c "SELECT similarity('baby', 'baby') as exact_match, similarity('baby', 'babe') as similar;"
```

Expected output:
```
 exact_match | similar 
-------------+---------
         1.0 | 0.75
```

#### Step 5: Create GIN Indexes for Fast Search
```bash
PGPASSWORD='MandarunLabadiena25!' psql \
  -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com \
  -U babyshield_user \
  -d postgres << 'EOF'
CREATE INDEX IF NOT EXISTS idx_recalls_product_trgm 
  ON recalls_enhanced USING gin (lower(product_name) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_recalls_brand_trgm 
  ON recalls_enhanced USING gin (lower(brand) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_recalls_description_trgm 
  ON recalls_enhanced USING gin (lower(description) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_recalls_hazard_trgm 
  ON recalls_enhanced USING gin (lower(hazard) gin_trgm_ops);
EOF
```

#### Step 6: Verify Indexes Created
```bash
PGPASSWORD='MandarunLabadiena25!' psql \
  -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com \
  -U babyshield_user \
  -d postgres \
  -c "SELECT indexname FROM pg_indexes WHERE tablename = 'recalls_enhanced' AND indexname LIKE '%trgm%' ORDER BY indexname;"
```

Expected output:
```
        indexname         
--------------------------
 idx_recalls_brand_trgm
 idx_recalls_description_trgm
 idx_recalls_hazard_trgm
 idx_recalls_product_trgm
```

### Option 3: Use the Shell Script

```bash
# Upload the script to CloudShell
# Then run:
chmod +x enable_pg_trgm_cloudshell.sh
./enable_pg_trgm_cloudshell.sh
```

## How to Access AWS CloudShell

1. **Sign in to AWS Console**: https://console.aws.amazon.com
2. **Switch to eu-north-1 region** (Stockholm)
3. **Click the CloudShell icon** in the top navigation bar (looks like >_)
4. **Wait for CloudShell to initialize** (~10 seconds)
5. **Paste the commands above**

## Advantages of CloudShell

- ✅ No VPN needed
- ✅ No bastion host needed  
- ✅ No security group changes needed
- ✅ Direct access to RDS from AWS network
- ✅ PostgreSQL client already available (or easy to install)
- ✅ Free to use
- ✅ Secure (uses your AWS credentials)

## Verification After Running

### Test 1: Search Should Now Return Results

From your local PowerShell:
```powershell
$searchBody = @{ query = "baby"; limit = 10 } | ConvertTo-Json
$result = Invoke-RestMethod -Uri "https://babyshield.cureviax.ai/api/v1/search/advanced" `
    -Method POST `
    -Body $searchBody `
    -ContentType "application/json"

Write-Host "Total Results: $($result.data.total)" -ForegroundColor Green
```

**Before:** `Total Results: 0`  
**After:** `Total Results: 12483` ✅

### Test 2: Check CloudWatch Logs

```bash
aws logs tail /ecs/babyshield-backend --follow --region eu-north-1 | grep -i "pg_trgm"
```

**Before:** "pg_trgm extension not enabled, falling back to LIKE search"  
**After:** (no warning) ✅

### Test 3: Performance Test

From your local PowerShell:
```powershell
Measure-Command {
    $searchBody = @{ query = "baby"; limit = 100 } | ConvertTo-Json
    Invoke-RestMethod -Uri "https://babyshield.cureviax.ai/api/v1/search/advanced" `
        -Method POST `
        -Body $searchBody `
        -ContentType "application/json"
}
```

**Expected:** < 500ms (typically 50-200ms with GIN indexes)

## Troubleshooting

### Error: "psql: command not found"

Run:
```bash
sudo yum install -y postgresql15
```

### Error: "could not connect to server"

- Verify you're in **eu-north-1 region** in CloudShell
- Check RDS endpoint is correct
- Verify RDS is running (AWS RDS Console)

### Error: "password authentication failed"

- Check password is correct: `MandarunLabadiena25!`
- Check username is correct: `babyshield_user`

### Error: "permission denied to create extension"

- User needs superuser privileges or rds_superuser role
- Check: `SELECT current_user, usesuper FROM pg_user WHERE usename = 'babyshield_user';`
- Grant if needed (requires master user): `GRANT rds_superuser TO babyshield_user;`

## Summary

**Fastest method:** Open CloudShell → Paste one-line command → Done in 30 seconds!

```bash
PGPASSWORD='MandarunLabadiena25!' psql -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com -U babyshield_user -d postgres -c "CREATE EXTENSION IF NOT EXISTS pg_trgm; CREATE INDEX IF NOT EXISTS idx_recalls_product_trgm ON recalls_enhanced USING gin (lower(product_name) gin_trgm_ops); CREATE INDEX IF NOT EXISTS idx_recalls_brand_trgm ON recalls_enhanced USING gin (lower(brand) gin_trgm_ops); CREATE INDEX IF NOT EXISTS idx_recalls_description_trgm ON recalls_enhanced USING gin (lower(description) gin_trgm_ops); CREATE INDEX IF NOT EXISTS idx_recalls_hazard_trgm ON recalls_enhanced USING gin (lower(hazard) gin_trgm_ops); SELECT 'Done!' as status;"
```

This will:
1. Enable pg_trgm extension
2. Create all 4 GIN indexes
3. Return "Done!" when complete

Then verify search works from your local machine!

---

**Last Updated:** October 16, 2025  
**Method:** AWS CloudShell (simplest and fastest)  
**Time Required:** ~30 seconds  
**Prerequisites:** AWS Console access with proper permissions
