# BabyShield Core Endpoints Test Script
$BASE = "https://babyshield.cureviax.ai"

Write-Host "🧪 Testing BabyShield Core Endpoints" -ForegroundColor Green
Write-Host "Base URL: $BASE" -ForegroundColor Cyan
Write-Host ""

# Test 1: Basic Health
Write-Host "1️⃣ Testing Basic Health..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Method GET -Uri "$BASE/healthz" -TimeoutSec 30
    Write-Host "✅ Basic Health: $($response.success)" -ForegroundColor Green
} catch {
    Write-Host "❌ Basic Health Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: API Health
Write-Host "`n2️⃣ Testing API Health..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/healthz" -TimeoutSec 30
    Write-Host "✅ API Health: $($response.success)" -ForegroundColor Green
} catch {
    Write-Host "❌ API Health Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Version Info
Write-Host "`n3️⃣ Testing Version Info..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/version" -TimeoutSec 30
    Write-Host "✅ Version Info: $($response.success)" -ForegroundColor Green
    Write-Host "   Version: $($response.data.version)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Version Info Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Safety Check (with test data)
Write-Host "`n4️⃣ Testing Safety Check..." -ForegroundColor Yellow
$safetyRequest = @{
    barcode = "123456789012"
    product_name = "Test Baby Product"
    user_id = 1
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/safety-check" -Body $safetyRequest -ContentType "application/json" -TimeoutSec 30
    Write-Host "✅ Safety Check: $($response.success)" -ForegroundColor Green
    Write-Host "   Status: $($response.data.status)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Safety Check Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Barcode Scan
Write-Host "`n5️⃣ Testing Barcode Scan..." -ForegroundColor Yellow
$scanRequest = @{
    barcode_data = "123456789012"
    barcode_type = "UPC"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/scan/barcode" -Body $scanRequest -ContentType "application/json" -TimeoutSec 30
    Write-Host "✅ Barcode Scan: $($response.success)" -ForegroundColor Green
} catch {
    Write-Host "❌ Barcode Scan Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 6: Recall Search
Write-Host "`n6️⃣ Testing Recall Search..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/recalls/search?q=baby&limit=5" -TimeoutSec 30
    Write-Host "✅ Recall Search: $($response.success)" -ForegroundColor Green
    Write-Host "   Results: $($response.data.items.Count) items" -ForegroundColor Gray
} catch {
    Write-Host "❌ Recall Search Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 7: Mobile Instant Check
Write-Host "`n7️⃣ Testing Mobile Instant Check..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/mobile/instant-check/123456789012?user_id=1" -TimeoutSec 30
    Write-Host "✅ Mobile Instant Check: $($response.success)" -ForegroundColor Green
} catch {
    Write-Host "❌ Mobile Instant Check Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🎯 Core Endpoints Test Complete!" -ForegroundColor Green
Write-Host "Check the results above for any ❌ failures that need attention." -ForegroundColor Cyan
