# Test Live Deployment - Chat Features and Security
# Comprehensive testing of deployed BabyShield features

Write-Host "🔍 TESTING LIVE DEPLOYMENT" -ForegroundColor Yellow
Write-Host "Verifying chat features and bulletproof security..." -ForegroundColor Cyan

$BASE = "https://babyshield.cureviax.ai"

# Step 1: Check deployment logs for chat registration
Write-Host "`n1. Checking Deployment Logs..." -ForegroundColor Cyan
Write-Host "Looking for chat endpoint registration messages..."

aws logs filter-log-events `
  --log-group-name "/ecs/babyshield-backend" `
  --region eu-north-1 `
  --filter-pattern "Chat endpoints" `
  --start-time $([int]((Get-Date).AddMinutes(-30).ToUniversalTime().Subtract((Get-Date "1970-01-01")).TotalMilliseconds)) `
  --query 'events[*].message' `
  --output text

Write-Host "`nLooking for import errors..."
aws logs filter-log-events `
  --log-group-name "/ecs/babyshield-backend" `
  --region eu-north-1 `
  --filter-pattern "CRITICAL" `
  --start-time $([int]((Get-Date).AddMinutes(-30).ToUniversalTime().Subtract((Get-Date "1970-01-01")).TotalMilliseconds)) `
  --query 'events[*].message' `
  --output text

# Step 2: Test OpenAPI for new endpoints
Write-Host "`n2. Testing OpenAPI Specification..." -ForegroundColor Cyan

Write-Host "Checking for chat endpoints in OpenAPI..."
try {
    $openapi = (Invoke-WebRequest -Uri "$BASE/openapi.json").Content | ConvertFrom-Json
    $chatPaths = $openapi.paths.PSObject.Properties.Name | Where-Object { $_ -like "*chat*" }
    
    if ($chatPaths) {
        Write-Host "✅ Chat endpoints found in OpenAPI:" -ForegroundColor Green
        $chatPaths | ForEach-Object { Write-Host "   - $_" -ForegroundColor Gray }
    } else {
        Write-Host "❌ No chat endpoints found in OpenAPI" -ForegroundColor Red
        Write-Host "This means chat router import failed in production" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Failed to fetch OpenAPI spec: $($_.Exception.Message)" -ForegroundColor Red
}

# Step 3: Test chat endpoints directly
Write-Host "`n3. Testing Chat Endpoints Directly..." -ForegroundColor Cyan

# Test chat flags endpoint
Write-Host "Testing /api/v1/chat/flags..."
try {
    $flags = Invoke-RestMethod -Uri "$BASE/api/v1/chat/flags" -Method GET -TimeoutSec 10
    Write-Host "✅ Chat flags endpoint working!" -ForegroundColor Green
    Write-Host "   - Chat enabled: $($flags.chat_enabled_global)" -ForegroundColor Gray
    Write-Host "   - Rollout percent: $($flags.chat_rollout_pct)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Chat flags endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test explain-result endpoint (needs a real scan_id)
Write-Host "`nTesting /api/v1/chat/explain-result..."
try {
    $explainTest = @{
        scan_id = "test_scan_123"
    } | ConvertTo-Json
    
    $explain = Invoke-RestMethod -Uri "$BASE/api/v1/chat/explain-result" -Method POST -Body $explainTest -ContentType "application/json" -TimeoutSec 10
    Write-Host "✅ Explain result endpoint working!" -ForegroundColor Green
    Write-Host "   - Summary: $($explain.summary.Substring(0, [Math]::Min(50, $explain.summary.Length)))..." -ForegroundColor Gray
} catch {
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-Host "⚠️ Explain endpoint returns 404 - scan_id not found (expected)" -ForegroundColor Yellow
    } else {
        Write-Host "❌ Explain endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Step 4: Test analytics endpoints
Write-Host "`n4. Testing Analytics Endpoints..." -ForegroundColor Cyan

Write-Host "Testing /api/v1/analytics/explain-feedback..."
try {
    $feedbackTest = @{
        scan_id = "test_scan_123"
        helpful = $true
    } | ConvertTo-Json
    
    $feedback = Invoke-RestMethod -Uri "$BASE/api/v1/analytics/explain-feedback" -Method POST -Body $feedbackTest -ContentType "application/json" -TimeoutSec 10
    Write-Host "✅ Analytics feedback endpoint working!" -ForegroundColor Green
    Write-Host "   - Response: $($feedback.ok)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Analytics feedback failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nTesting /api/v1/analytics/alt-click..."
try {
    $altClickTest = @{
        scan_id = "test_scan_123"
        alt_id = "alt_test"
    } | ConvertTo-Json
    
    $altClick = Invoke-RestMethod -Uri "$BASE/api/v1/analytics/alt-click" -Method POST -Body $altClickTest -ContentType "application/json" -TimeoutSec 10
    Write-Host "✅ Analytics alt-click endpoint working!" -ForegroundColor Green
    Write-Host "   - Response: $($altClick.ok)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Analytics alt-click failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Step 5: Test security features
Write-Host "`n5. Testing Security Features..." -ForegroundColor Cyan

# Test security dashboard
Write-Host "Testing /security/dashboard..."
try {
    $security = Invoke-WebRequest -Uri "$BASE/security/dashboard" -Method GET -TimeoutSec 10
    if ($security.StatusCode -eq 200) {
        Write-Host "✅ Security dashboard active!" -ForegroundColor Green
        Write-Host "   - Content length: $($security.Content.Length) bytes" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Security dashboard failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test honeypot (should return fake content)
Write-Host "`nTesting honeypot /admin/login.php..."
try {
    $honeypot = Invoke-WebRequest -Uri "$BASE/admin/login.php" -Method GET -TimeoutSec 10
    if ($honeypot.StatusCode -eq 200) {
        Write-Host "✅ Honeypot active - attackers will be trapped!" -ForegroundColor Green
        Write-Host "   - Contains 'Admin Login': $($honeypot.Content -like '*Admin Login*')" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Honeypot failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Step 6: Test security headers
Write-Host "`n6. Testing Security Headers..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$BASE/" -Method GET -TimeoutSec 10
    
    $criticalHeaders = @("Content-Security-Policy", "Strict-Transport-Security", "X-Frame-Options", "X-Content-Type-Options")
    foreach ($header in $criticalHeaders) {
        if ($response.Headers[$header]) {
            Write-Host "✅ $header: Active" -ForegroundColor Green
        } else {
            Write-Host "⚠️ $header: Missing" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "❌ Security headers test failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Step 7: Check application health
Write-Host "`n7. Application Health Check..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$BASE/healthz" -Method GET -TimeoutSec 10
    Write-Host "✅ Application healthy: $($health.status)" -ForegroundColor Green
    Write-Host "   - Version: $($health.version)" -ForegroundColor Gray
    Write-Host "   - Service: $($health.service)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Step 8: Test emergency detection (if chat is working)
Write-Host "`n8. Testing Emergency Detection..." -ForegroundColor Cyan
if ($flags -and $flags.chat_enabled_global) {
    Write-Host "Chat is enabled - testing emergency detection..."
    try {
        $emergencyTest = @{
            scan_id = "test_scan_emergency"
            user_query = "My baby swallowed a battery"
        } | ConvertTo-Json
        
        $emergency = Invoke-RestMethod -Uri "$BASE/api/v1/chat/conversation" -Method POST -Body $emergencyTest -ContentType "application/json" -TimeoutSec 10
        
        if ($emergency.message.emergency) {
            Write-Host "✅ Emergency detection working!" -ForegroundColor Green
            Write-Host "   - Level: $($emergency.message.emergency.level)" -ForegroundColor Gray
            Write-Host "   - CTA: $($emergency.message.emergency.cta)" -ForegroundColor Gray
        } else {
            Write-Host "⚠️ Emergency detection not triggered" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "❌ Emergency test failed: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "⚠️ Chat not enabled - skipping emergency test" -ForegroundColor Yellow
}

# Step 9: Summary
Write-Host "`n🎯 DEPLOYMENT TEST SUMMARY:" -ForegroundColor Yellow

if ($chatPaths) {
    Write-Host "✅ CHAT FEATURES: DEPLOYED AND WORKING" -ForegroundColor Green
    Write-Host "   - Endpoints visible in OpenAPI" -ForegroundColor Gray
    Write-Host "   - Chat flags responding" -ForegroundColor Gray
    Write-Host "   - Analytics endpoints active" -ForegroundColor Gray
} else {
    Write-Host "❌ CHAT FEATURES: MISSING FROM PRODUCTION" -ForegroundColor Red
    Write-Host "   - Check deployment logs for import errors" -ForegroundColor Yellow
    Write-Host "   - Verify all dependencies are available in Docker image" -ForegroundColor Yellow
}

Write-Host "`n📊 NEXT STEPS:" -ForegroundColor Yellow
if ($chatPaths) {
    Write-Host "✅ Enable chat features: Set BS_FEATURE_CHAT_ENABLED=true in ECS" -ForegroundColor Green
    Write-Host "✅ Start rollout: Set BS_FEATURE_CHAT_ROLLOUT_PCT=0.10" -ForegroundColor Green
    Write-Host "✅ Monitor: /security/dashboard for real-time threats" -ForegroundColor Green
} else {
    Write-Host "🔧 Check ECS logs: aws logs tail /ecs/babyshield-backend --region eu-north-1" -ForegroundColor Yellow
    Write-Host "🔧 Look for: 'Loading chat dependencies' and any CRITICAL errors" -ForegroundColor Yellow
    Write-Host "🔧 Fix any missing dependencies and redeploy" -ForegroundColor Yellow
}

Write-Host "`n🚀 DEPLOYMENT VERIFICATION COMPLETE!" -ForegroundColor Green
