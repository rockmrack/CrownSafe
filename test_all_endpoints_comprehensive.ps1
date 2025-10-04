#!/usr/bin/env pwsh
# ============================================
# BabyShield COMPREHENSIVE Endpoint Test Suite
# Tests ALL major endpoints (257 total endpoints)
# ============================================

$API_BASE = "https://babyshield.cureviax.ai"
$TestResults = @()
$PassCount = 0
$FailCount = 0
$SkipCount = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Endpoint,
        [hashtable]$Body = $null,
        [hashtable]$Headers = @{"Content-Type" = "application/json"},
        [int[]]$ExpectedStatus = @(200),
        [bool]$RequiresAuth = $false,
        [bool]$Skip = $false
    )
    
    if ($Skip) {
        Write-Host "[SKIP] $Name" -ForegroundColor Gray
        $script:SkipCount++
        return
    }
    
    Write-Host "[TEST] $Name" -ForegroundColor Cyan
    
    try {
        $params = @{
            Uri = "$API_BASE$Endpoint"
            Method = $Method
            Headers = $Headers
            TimeoutSec = 15
            ErrorAction = "Stop"
        }
        
        if ($Body) {
            $params.Body = ($Body | ConvertTo-Json -Depth 10 -Compress)
        }
        
        $response = Invoke-WebRequest @params
        
        if ($response.StatusCode -in $ExpectedStatus) {
            Write-Host "  [PASS] $($response.StatusCode)" -ForegroundColor Green
            $script:PassCount++
            $script:TestResults += [PSCustomObject]@{
                Category = $Name.Split(' - ')[0]
                Test = $Name
                Endpoint = $Endpoint
                Status = "PASS"
                StatusCode = $response.StatusCode
            }
        } else {
            Write-Host "  [FAIL] Expected $ExpectedStatus, got $($response.StatusCode)" -ForegroundColor Red
            $script:FailCount++
            $script:TestResults += [PSCustomObject]@{
                Category = $Name.Split(' - ')[0]
                Test = $Name
                Endpoint = $Endpoint
                Status = "FAIL"
                StatusCode = $response.StatusCode
            }
        }
    }
    catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -in $ExpectedStatus) {
            Write-Host "  [PASS] $statusCode (expected error)" -ForegroundColor Green
            $script:PassCount++
            $script:TestResults += [PSCustomObject]@{
                Category = $Name.Split(' - ')[0]
                Test = $Name
                Endpoint = $Endpoint
                Status = "PASS"
                StatusCode = $statusCode
            }
        } else {
            Write-Host "  [FAIL] $statusCode - $($_.Exception.Message)" -ForegroundColor Red
            $script:FailCount++
            $script:TestResults += [PSCustomObject]@{
                Category = $Name.Split(' - ')[0]
                Test = $Name
                Endpoint = $Endpoint
                Status = "FAIL"
                Error = $_.Exception.Message
            }
        }
    }
}

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  COMPREHENSIVE ENDPOINT TEST SUITE" -ForegroundColor Green
Write-Host "  Testing ALL major endpoints" -ForegroundColor Green
Write-Host "  API: $API_BASE" -ForegroundColor Yellow
Write-Host "============================================`n" -ForegroundColor Cyan

# ============================================
# CATEGORY 1: INFRASTRUCTURE & HEALTH
# ============================================
Write-Host "[CATEGORY 1] Infrastructure & Health" -ForegroundColor Magenta
Test-Endpoint "Infrastructure - Health Check" "GET" "/healthz"
Test-Endpoint "Infrastructure - Readiness Check" "GET" "/readyz"
Test-Endpoint "Infrastructure - API Docs" "GET" "/docs" -ExpectedStatus @(200)
Test-Endpoint "Infrastructure - OpenAPI Schema" "GET" "/openapi.json"
Test-Endpoint "Infrastructure - Metrics" "GET" "/metrics" -ExpectedStatus @(200, 404)
Test-Endpoint "Infrastructure - Cache Stats" "GET" "/cache/stats" -ExpectedStatus @(200, 404, 401)
Test-Endpoint "Infrastructure - Cache Warm" "POST" "/cache/warm" -ExpectedStatus @(200, 404, 401)
Test-Endpoint "Infrastructure - Mobile Stats" "GET" "/mobile/stats" -ExpectedStatus @(200, 404, 401)

# ============================================
# CATEGORY 2: AUTHENTICATION & USER MANAGEMENT
# ============================================
Write-Host "`n[CATEGORY 2] Authentication & User Management" -ForegroundColor Magenta
Test-Endpoint "Auth - Register (missing fields)" "POST" "/api/v1/auth/register" -ExpectedStatus @(400, 422) -Body @{}
Test-Endpoint "Auth - Login (missing fields)" "POST" "/api/v1/auth/token" -ExpectedStatus @(400, 422) -Body @{}
Test-Endpoint "Auth - Refresh (no token)" "POST" "/api/v1/auth/refresh" -ExpectedStatus @(401, 422)
Test-Endpoint "Auth - Me (no token)" "GET" "/api/v1/auth/me" -ExpectedStatus @(401, 422)
Test-Endpoint "Auth - Logout (no token)" "POST" "/api/v1/auth/logout" -ExpectedStatus @(401, 422, 405)
Test-Endpoint "Auth - Password Reset Request" "POST" "/api/v1/auth/password-reset/request" -ExpectedStatus @(200, 400, 422) -Body @{ email = "test@example.com" }
Test-Endpoint "Auth - Verify" "POST" "/api/v1/auth/verify" -ExpectedStatus @(200, 400, 422)

# ============================================
# CATEGORY 3: BARCODE & SCANNING
# ============================================
Write-Host "`n[CATEGORY 3] Barcode & Scanning" -ForegroundColor Magenta
Test-Endpoint "Barcode - Scan UPC" "POST" "/api/v1/barcode/scan" -Body @{ barcode = "074451716902"; scan_type = "upc" }
Test-Endpoint "Barcode - Scan Invalid" "POST" "/api/v1/barcode/scan" -ExpectedStatus @(200, 400, 422) -Body @{ barcode = "invalid"; scan_type = "upc" }
Test-Endpoint "Barcode - Cache Status" "GET" "/api/v1/barcode/cache/status" -ExpectedStatus @(200, 401, 404)
Test-Endpoint "Barcode - Test Barcodes" "GET" "/api/v1/barcode/test/barcodes" -ExpectedStatus @(200, 404)
Test-Endpoint "Barcode - Lookup" "GET" "/api/v1/lookup/barcode/074451716902" -ExpectedStatus @(200, 404)
Test-Endpoint "Mobile - Quick Check" "GET" "/api/v1/mobile/quick-check/074451716902" -ExpectedStatus @(200, 401, 404)
Test-Endpoint "Mobile - Instant Check" "GET" "/api/v1/mobile/instant-check/074451716902" -ExpectedStatus @(200, 401, 404)
Test-Endpoint "Mobile - Scan" "POST" "/api/v1/mobile/scan" -ExpectedStatus @(200, 400, 422) -Body @{ barcode = "074451716902" }
Test-Endpoint "Scan - Barcode" "POST" "/api/v1/scan/barcode" -ExpectedStatus @(200, 400, 422) -Body @{ barcode = "074451716902" }
Test-Endpoint "Scan - QR" "POST" "/api/v1/scan/qr" -ExpectedStatus @(200, 400, 422)
Test-Endpoint "Scan - DataMatrix" "POST" "/api/v1/scan/datamatrix" -ExpectedStatus @(200, 400, 422)
Test-Endpoint "Enhanced Scan - Health" "GET" "/api/v1/enhanced-scan/health" -ExpectedStatus @(200, 404)
Test-Endpoint "Enhanced Scan - Validate" "POST" "/api/v1/enhanced-scan/validate" -ExpectedStatus @(200, 400, 422)

# ============================================
# CATEGORY 4: PRODUCT SEARCH & RECALLS
# ============================================
Write-Host "`n[CATEGORY 4] Product Search & Recalls" -ForegroundColor Magenta
Test-Endpoint "Search - Advanced Baby Monitor" "POST" "/api/v1/search/advanced" -Body @{ product = "baby monitor"; limit = 5 }
Test-Endpoint "Search - Advanced Pacifier" "POST" "/api/v1/search/advanced" -Body @{ product = "pacifier"; limit = 5 }
Test-Endpoint "Search - Advanced Crib" "POST" "/api/v1/search/advanced" -Body @{ product = "crib"; limit = 5 }
Test-Endpoint "Search - Bulk" "POST" "/api/v1/search/bulk" -ExpectedStatus @(200, 400, 422) -Body @{ queries = @("stroller", "car seat") }
Test-Endpoint "Recalls - List" "GET" "/api/v1/recalls?limit=10" -ExpectedStatus @(200, 404)
Test-Endpoint "Recalls - Stats" "GET" "/api/v1/recalls/stats" -ExpectedStatus @(200, 404)
Test-Endpoint "Recall - By ID" "GET" "/api/v1/recall/CPSC-7809" -ExpectedStatus @(200, 404)
Test-Endpoint "Dashboard - Recent Recalls" "GET" "/api/v1/dashboard/recent-recalls" -ExpectedStatus @(200, 401)
Test-Endpoint "Safety Hub - Articles" "GET" "/api/v1/safety-hub/articles" -ExpectedStatus @(200, 404)
Test-Endpoint "Autocomplete - Products" "GET" "/api/v1/autocomplete/products?q=baby" -ExpectedStatus @(200, 404)
Test-Endpoint "Autocomplete - Brands" "GET" "/api/v1/autocomplete/brands?q=fisher" -ExpectedStatus @(200, 404)

# ============================================
# CATEGORY 5: AGENCIES & DATA SOURCES
# ============================================
Write-Host "`n[CATEGORY 5] Agencies & Data Sources" -ForegroundColor Magenta
Test-Endpoint "Agencies - List" "GET" "/api/v1/agencies"
Test-Endpoint "Agencies - CPSC" "GET" "/api/v1/cpsc" -ExpectedStatus @(200, 404)
Test-Endpoint "Agencies - FDA" "GET" "/api/v1/fda" -ExpectedStatus @(200, 404)
Test-Endpoint "Agencies - EU Safety Gate" "GET" "/api/v1/eu_safety_gate" -ExpectedStatus @(200, 404)
Test-Endpoint "Agencies - UK OPSS" "GET" "/api/v1/uk_opss" -ExpectedStatus @(200, 404)
Test-Endpoint "Supplemental - Data Sources" "GET" "/api/v1/supplemental/data-sources" -ExpectedStatus @(200, 404)
Test-Endpoint "Supplemental - Health" "GET" "/api/v1/supplemental/health" -ExpectedStatus @(200, 404)

# ============================================
# CATEGORY 6: CHAT & AI FEATURES
# ============================================
Write-Host "`n[CATEGORY 6] Chat & AI Features" -ForegroundColor Magenta
Test-Endpoint "Chat - Demo" "POST" "/api/v1/chat/demo" -ExpectedStatus @(200, 400, 422) -Body @{ message = "test" }
Test-Endpoint "Chat - Flags" "GET" "/api/v1/chat/flags" -ExpectedStatus @(200, 404)
Test-Endpoint "Chat - Explain Result" "POST" "/api/v1/chat/explain-result?scan_id=test&user_query=explain" -ExpectedStatus @(200, 400, 404, 422)
Test-Endpoint "Chat - Conversation" "POST" "/api/v1/chat/conversation" -ExpectedStatus @(200, 400, 422) -Body @{ message = "test" }

# ============================================
# CATEGORY 7: USER DASHBOARD & ANALYTICS
# ============================================
Write-Host "`n[CATEGORY 7] User Dashboard & Analytics" -ForegroundColor Magenta
Test-Endpoint "Dashboard - Overview (no auth)" "GET" "/api/v1/dashboard/overview" -ExpectedStatus @(200, 401)
Test-Endpoint "Dashboard - Activity (no auth)" "GET" "/api/v1/dashboard/activity" -ExpectedStatus @(200, 401)
Test-Endpoint "Dashboard - Achievements (no auth)" "GET" "/api/v1/dashboard/achievements" -ExpectedStatus @(200, 401)
Test-Endpoint "Dashboard - Safety Insights (no auth)" "GET" "/api/v1/dashboard/safety-insights" -ExpectedStatus @(200, 401)
Test-Endpoint "Dashboard - Product Categories" "GET" "/api/v1/dashboard/product-categories" -ExpectedStatus @(200, 401, 404)
Test-Endpoint "Analytics - Counts" "GET" "/api/v1/analytics/counts" -ExpectedStatus @(200, 404)
Test-Endpoint "Analytics - Recalls" "GET" "/api/v1/analytics/recalls" -ExpectedStatus @(200, 404)
Test-Endpoint "User - Scan Statistics (no auth)" "GET" "/api/v1/user/scan-statistics" -ExpectedStatus @(200, 401)

# ============================================
# CATEGORY 8: NOTIFICATIONS
# ============================================
Write-Host "`n[CATEGORY 8] Notifications" -ForegroundColor Magenta
Test-Endpoint "Notifications - History (no auth)" "GET" "/api/v1/notifications/history" -ExpectedStatus @(200, 401)
Test-Endpoint "Notifications - Preferences (no auth)" "GET" "/api/v1/notifications/preferences" -ExpectedStatus @(200, 401)
Test-Endpoint "Notifications - Devices (no auth)" "GET" "/api/v1/notifications/devices" -ExpectedStatus @(200, 401)
Test-Endpoint "Recall Alerts - Preferences (no auth)" "GET" "/api/v1/recall-alerts/preferences" -ExpectedStatus @(200, 401)

# ============================================
# CATEGORY 9: PRODUCT MONITORING
# ============================================
Write-Host "`n[CATEGORY 9] Product Monitoring" -ForegroundColor Magenta
Test-Endpoint "Monitoring - Status" "GET" "/api/v1/monitoring/status" -ExpectedStatus @(200, 404)
Test-Endpoint "Monitoring - Livez" "GET" "/api/v1/monitoring/livez" -ExpectedStatus @(200, 404)
Test-Endpoint "Monitoring - Readyz" "GET" "/api/v1/monitoring/readyz" -ExpectedStatus @(200, 404)
Test-Endpoint "Monitoring - System" "GET" "/api/v1/monitoring/system" -ExpectedStatus @(200, 404)
Test-Endpoint "Monitoring - Agencies" "GET" "/api/v1/monitoring/agencies" -ExpectedStatus @(200, 404)
Test-Endpoint "Monitoring - Products (no auth)" "GET" "/api/v1/monitoring/products" -ExpectedStatus @(200, 401, 404)

# ============================================
# CATEGORY 10: VISUAL RECOGNITION
# ============================================
Write-Host "`n[CATEGORY 10] Visual Recognition" -ForegroundColor Magenta
Test-Endpoint "Visual - Search" "POST" "/api/v1/visual/search" -ExpectedStatus @(200, 400, 422)
Test-Endpoint "Visual - Analyze" "POST" "/api/v1/visual/analyze" -ExpectedStatus @(200, 400, 422)
Test-Endpoint "Visual - Suggest Product" "POST" "/api/v1/visual/suggest-product" -ExpectedStatus @(200, 400, 422)
Test-Endpoint "Visual - Status" "GET" "/api/v1/visual/status/test-job-id" -ExpectedStatus @(200, 404)
Test-Endpoint "Advanced Visual - Recognize" "POST" "/api/v1/advanced/visual/recognize" -ExpectedStatus @(200, 400, 422)

# ============================================
# CATEGORY 11: SAFETY REPORTS
# ============================================
Write-Host "`n[CATEGORY 11] Safety Reports" -ForegroundColor Magenta
Test-Endpoint "Safety Reports - My Reports (no auth)" "GET" "/api/v1/safety-reports/my-reports" -ExpectedStatus @(200, 401)
Test-Endpoint "Safety Reports - Generate (no auth)" "POST" "/api/v1/safety-reports/generate" -ExpectedStatus @(200, 400, 401, 422)
Test-Endpoint "Safety Reports - Track Scan (no auth)" "POST" "/api/v1/safety-reports/track-scan" -ExpectedStatus @(200, 400, 401, 422)

# ============================================
# CATEGORY 12: SHARING & COLLABORATION
# ============================================
Write-Host "`n[CATEGORY 12] Sharing & Collaboration" -ForegroundColor Magenta
Test-Endpoint "Share - My Shares (no auth)" "GET" "/api/v1/share/my-shares" -ExpectedStatus @(200, 401)
Test-Endpoint "Share - Create (no auth)" "POST" "/api/v1/share/create" -ExpectedStatus @(200, 400, 401, 422)

# ============================================
# CATEGORY 13: SUBSCRIPTION & PREMIUM
# ============================================
Write-Host "`n[CATEGORY 13] Subscription & Premium" -ForegroundColor Magenta
Test-Endpoint "Subscription - Plans" "GET" "/api/v1/subscription/plans"
Test-Endpoint "Subscription - Products" "GET" "/api/v1/subscription/products"
Test-Endpoint "Subscription - Status (no auth)" "GET" "/api/v1/subscription/status" -ExpectedStatus @(200, 401)
Test-Endpoint "Subscription - History (no auth)" "GET" "/api/v1/subscription/history" -ExpectedStatus @(200, 401)
Test-Endpoint "Subscription - Entitlement (no auth)" "GET" "/api/v1/subscription/entitlement" -ExpectedStatus @(200, 401)
Test-Endpoint "Premium - Family Members (no auth)" "GET" "/api/v1/premium/family/members" -ExpectedStatus @(200, 401)

# ============================================
# CATEGORY 14: LEGAL & COMPLIANCE
# ============================================
Write-Host "`n[CATEGORY 14] Legal & Compliance" -ForegroundColor Magenta
Test-Endpoint "Legal - Privacy Summary (no auth)" "GET" "/api/v1/user/privacy/summary" -ExpectedStatus @(200, 401, 404)
Test-Endpoint "Legal - Documents List" "GET" "/legal/" -ExpectedStatus @(200, 404)
Test-Endpoint "Legal - Compliance Status" "GET" "/legal/compliance/status" -ExpectedStatus @(200, 404)
Test-Endpoint "Compliance - GDPR Retention Policy" "GET" "/api/v1/compliance/gdpr/retention-policy" -ExpectedStatus @(200, 404)
Test-Endpoint "Compliance - Legal Document" "GET" "/api/v1/compliance/legal/document?doc_type=privacy" -ExpectedStatus @(200, 400, 404)

# ============================================
# CATEGORY 15: INCIDENT REPORTING
# ============================================
Write-Host "`n[CATEGORY 15] Incident Reporting" -ForegroundColor Magenta
Test-Endpoint "Incidents - Stats" "GET" "/api/v1/incidents/stats" -ExpectedStatus @(200, 404)
Test-Endpoint "Incidents - Clusters" "GET" "/api/v1/incidents/clusters" -ExpectedStatus @(200, 404)
Test-Endpoint "Incidents - Submit (no auth)" "POST" "/api/v1/incidents/submit" -ExpectedStatus @(200, 400, 401, 422)

# ============================================
# CATEGORY 16: RISK ASSESSMENT
# ============================================
Write-Host "`n[CATEGORY 16] Risk Assessment" -ForegroundColor Magenta
Test-Endpoint "Risk - Stats" "GET" "/api/v1/risk-assessment/stats" -ExpectedStatus @(200, 404)
Test-Endpoint "Risk - Search" "GET" "/api/v1/risk-assessment/search?query=test" -ExpectedStatus @(200, 404)
Test-Endpoint "Risk - Assess" "POST" "/api/v1/risk-assessment/assess" -ExpectedStatus @(200, 400, 422)

# ============================================
# CATEGORY 17: INTERNATIONALIZATION (i18n)
# ============================================
Write-Host "`n[CATEGORY 17] Internationalization" -ForegroundColor Magenta
Test-Endpoint "i18n - Locales List" "GET" "/api/v1/i18n/locales" -ExpectedStatus @(200, 404)
Test-Endpoint "i18n - Translations" "GET" "/api/v1/i18n/translations" -ExpectedStatus @(200, 404)
Test-Endpoint "i18n - Accessibility Config" "GET" "/api/v1/i18n/a11y/config" -ExpectedStatus @(200, 404)
Test-Endpoint "i18n - Accessibility Labels" "GET" "/api/v1/i18n/a11y/labels" -ExpectedStatus @(200, 404)

# ============================================
# CATEGORY 18: FEEDBACK & SUPPORT
# ============================================
Write-Host "`n[CATEGORY 18] Feedback & Support" -ForegroundColor Magenta
Test-Endpoint "Feedback - Health" "GET" "/api/v1/feedback/health" -ExpectedStatus @(200, 404)
Test-Endpoint "Feedback - Categories" "GET" "/api/v1/feedback/categories" -ExpectedStatus @(200, 404)
Test-Endpoint "Feedback - Submit" "POST" "/api/v1/feedback/submit" -ExpectedStatus @(200, 400, 422)

# ============================================
# CATEGORY 19: BABY-SPECIFIC FEATURES
# ============================================
Write-Host "`n[CATEGORY 19] Baby-Specific Features" -ForegroundColor Magenta
Test-Endpoint "Baby - Alternatives" "GET" "/api/v1/baby/alternatives?product=test" -ExpectedStatus @(200, 404)
Test-Endpoint "Baby - Hazards Analyze" "POST" "/api/v1/baby/hazards/analyze" -ExpectedStatus @(200, 400, 422)
Test-Endpoint "Baby - Community Alerts (no auth)" "GET" "/api/v1/baby/community/alerts" -ExpectedStatus @(200, 401, 404)

# ============================================
# CATEGORY 20: ADVANCED FEATURES
# ============================================
Write-Host "`n[CATEGORY 20] Advanced Features" -ForegroundColor Magenta
Test-Endpoint "Advanced - Guidelines" "GET" "/api/v1/advanced/guidelines?category=safety" -ExpectedStatus @(200, 404)
Test-Endpoint "Advanced - Research" "POST" "/api/v1/advanced/research" -ExpectedStatus @(200, 400, 422)

# ============================================
# CATEGORY 21: SECURITY MONITORING
# ============================================
Write-Host "`n[CATEGORY 21] Security Monitoring" -ForegroundColor Magenta
Test-Endpoint "Security - Dashboard (no auth)" "GET" "/security/dashboard" -ExpectedStatus @(200, 401, 404)
Test-Endpoint "Security - Metrics (no auth)" "GET" "/security/metrics" -ExpectedStatus @(200, 401, 404)
Test-Endpoint "Security - Threats Live (no auth)" "GET" "/security/threats/live" -ExpectedStatus @(200, 401, 404)

# ============================================
# SUMMARY
# ============================================
$TotalTests = $PassCount + $FailCount + $SkipCount
$PassRate = if ($TotalTests -gt 0) { [math]::Round(($PassCount / ($PassCount + $FailCount)) * 100, 1) } else { 0 }

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  TEST SUMMARY" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Total Tests Run: $($PassCount + $FailCount)" -ForegroundColor White
Write-Host "Passed:          $PassCount" -ForegroundColor Green
Write-Host "Failed:          $FailCount" -ForegroundColor $(if ($FailCount -eq 0) { "Green" } else { "Red" })
Write-Host "Skipped:         $SkipCount" -ForegroundColor Gray
Write-Host "Pass Rate:       $PassRate%" -ForegroundColor $(if ($PassRate -ge 90) { "Green" } elseif ($PassRate -ge 70) { "Yellow" } else { "Red" })
Write-Host ""

if ($FailCount -eq 0) {
    Write-Host "[SUCCESS] All tests passed!" -ForegroundColor Green
} elseif ($PassRate -ge 90) {
    Write-Host "[EXCELLENT] $PassRate% pass rate" -ForegroundColor Green
} elseif ($PassRate -ge 70) {
    Write-Host "[GOOD] $PassRate% pass rate" -ForegroundColor Yellow
} else {
    Write-Host "[WARNING] $PassRate% pass rate - review failures" -ForegroundColor Red
}

Write-Host "`n============================================" -ForegroundColor Cyan

# Export results
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$TestResults | Export-Csv -Path "comprehensive_test_results_$timestamp.csv" -NoTypeInformation
Write-Host "Results exported to: comprehensive_test_results_$timestamp.csv" -ForegroundColor Gray

# Group by category and show summary
Write-Host "`nResults by Category:" -ForegroundColor Yellow
$TestResults | Group-Object Category | Sort-Object Name | ForEach-Object {
    $passed = ($_.Group | Where-Object { $_.Status -eq "PASS" }).Count
    $failed = ($_.Group | Where-Object { $_.Status -eq "FAIL" }).Count
    $rate = if (($passed + $failed) -gt 0) { [math]::Round(($passed / ($passed + $failed)) * 100) } else { 0 }
    $color = if ($rate -eq 100) { "Green" } elseif ($rate -ge 80) { "Yellow" } else { "Red" }
    Write-Host "  $($_.Name): $passed/$($_.Count) passed ($rate%)" -ForegroundColor $color
}

Write-Host ""

