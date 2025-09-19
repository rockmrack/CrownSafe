# BabyShield Supplemental Endpoints Test Script
$BASE = "https://babyshield.cureviax.ai"

Write-Host "🧪 Testing BabyShield Supplemental Endpoints" -ForegroundColor Green
Write-Host "Base URL: $BASE" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health Check
Write-Host "1️⃣ Testing Health Check..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/supplemental/health" -TimeoutSec 30
    Write-Host "✅ Health Check: $($response.success)" -ForegroundColor Green
    Write-Host "   Services: $($response.data.services | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Health Check Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Data Sources
Write-Host "`n2️⃣ Testing Data Sources..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/supplemental/data-sources" -TimeoutSec 30
    Write-Host "✅ Data Sources: $($response.success)" -ForegroundColor Green
    Write-Host "   Available sources: $($response.data.PSObject.Properties.Name -join ', ')" -ForegroundColor Gray
} catch {
    Write-Host "❌ Data Sources Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Food Data (with test product)
Write-Host "`n3️⃣ Testing Food Data..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/supplemental/food-data/baby-formula" -TimeoutSec 30
    Write-Host "✅ Food Data: $($response.success)" -ForegroundColor Green
    Write-Host "   Processing time: $($response.data.processing_time_ms)ms" -ForegroundColor Gray
} catch {
    Write-Host "❌ Food Data Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Cosmetic Data
Write-Host "`n4️⃣ Testing Cosmetic Data..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/supplemental/cosmetic-data/baby-lotion" -TimeoutSec 30
    Write-Host "✅ Cosmetic Data: $($response.success)" -ForegroundColor Green
    Write-Host "   Processing time: $($response.data.processing_time_ms)ms" -ForegroundColor Gray
} catch {
    Write-Host "❌ Cosmetic Data Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Chemical Data
Write-Host "`n5️⃣ Testing Chemical Data..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/supplemental/chemical-data/parabens" -TimeoutSec 30
    Write-Host "✅ Chemical Data: $($response.success)" -ForegroundColor Green
    Write-Host "   Processing time: $($response.data.processing_time_ms)ms" -ForegroundColor Gray
} catch {
    Write-Host "❌ Chemical Data Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 6: Enhanced Safety Report (POST)
Write-Host "`n6️⃣ Testing Enhanced Safety Report..." -ForegroundColor Yellow
$safetyRequest = @{
    product_identifier = "baby-formula-123"
    product_name = "Test Baby Formula"
    include_food_data = $true
    include_cosmetic_data = $false
    include_chemical_data = $false
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/supplemental/safety-report" -Body $safetyRequest -ContentType "application/json" -TimeoutSec 30
    Write-Host "✅ Enhanced Safety Report: $($response.success)" -ForegroundColor Green
    Write-Host "   Processing time: $($response.data.processing_time_ms)ms" -ForegroundColor Gray
} catch {
    Write-Host "❌ Enhanced Safety Report Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🎯 Test Summary Complete!" -ForegroundColor Green
Write-Host "Check the results above for any ❌ failures that need attention." -ForegroundColor Cyan
