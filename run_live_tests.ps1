# Live Test Runner
# Instructions for running live integration tests against production database

Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "  BabyShield Backend - Live Integration Test Runner" -ForegroundColor Cyan
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if AWS CLI is available
Write-Host "STEP 1: Checking AWS CLI..." -ForegroundColor Yellow
$awsInstalled = Get-Command aws -ErrorAction SilentlyContinue
if (-not $awsInstalled) {
    Write-Host "❌ AWS CLI not found. Install it from: https://aws.amazon.com/cli/" -ForegroundColor Red
    Write-Host ""
    Write-Host "OR manually set the database URL:" -ForegroundColor Yellow
    Write-Host '  $env:PROD_DATABASE_URL = "postgresql://user:pass@host:5432/db"' -ForegroundColor White
    exit 1
}
Write-Host "✅ AWS CLI found" -ForegroundColor Green
Write-Host ""

# Step 2: Get database credentials from AWS Secrets Manager
Write-Host "STEP 2: Fetching production database credentials from AWS..." -ForegroundColor Yellow
Write-Host "(This requires AWS credentials configured with access to Secrets Manager)" -ForegroundColor Gray
Write-Host ""

try {
    $secret = aws secretsmanager get-secret-value `
        --secret-id "babyshield/prod/database" `
        --region "eu-north-1" `
        --query "SecretString" `
        --output text 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        # Parse JSON secret
        $secretObj = $secret | ConvertFrom-Json
        $dbUrl = $secretObj.DATABASE_URL
        
        Write-Host "✅ Retrieved database credentials" -ForegroundColor Green
        Write-Host "   Host: $($secretObj.DB_HOST)" -ForegroundColor Gray
        Write-Host "   Database: $($secretObj.DB_NAME)" -ForegroundColor Gray
        Write-Host ""
        
        # Set environment variable
        $env:PROD_DATABASE_URL = $dbUrl
        Write-Host "✅ Set PROD_DATABASE_URL environment variable" -ForegroundColor Green
        Write-Host ""
    }
    else {
        Write-Host "⚠️  Could not fetch from AWS Secrets Manager" -ForegroundColor Yellow
        Write-Host "   Error: $secret" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please manually set the database URL:" -ForegroundColor Yellow
        Write-Host '  $env:PROD_DATABASE_URL = "postgresql://USERNAME:PASSWORD@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/postgres"' -ForegroundColor White
        Write-Host ""
        Write-Host "Then run: pytest tests/live/ -v -s -m live" -ForegroundColor Cyan
        exit 1
    }
}
catch {
    Write-Host "⚠️  Error accessing AWS Secrets Manager: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please manually set the database URL:" -ForegroundColor Yellow
    Write-Host '  $env:PROD_DATABASE_URL = "postgresql://USERNAME:PASSWORD@HOST:5432/DATABASE"' -ForegroundColor White
    exit 1
}

# Step 3: Run live tests
Write-Host "STEP 3: Running live integration tests..." -ForegroundColor Yellow
Write-Host ""

pytest tests/live/test_manual_model_number_entry.py -v -s -m live

Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "  Test run complete!" -ForegroundColor Cyan
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To run all live tests:" -ForegroundColor Yellow
Write-Host "  pytest tests/live/ -v -s -m live" -ForegroundColor White
Write-Host ""
Write-Host "To run specific test:" -ForegroundColor Yellow
Write-Host "  pytest tests/live/test_manual_model_number_entry.py::test_manual_model_number_entry_with_recall -v -s" -ForegroundColor White
Write-Host ""
