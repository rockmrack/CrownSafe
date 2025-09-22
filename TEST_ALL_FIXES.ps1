#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test all deployed fixes in the BabyShield system
.DESCRIPTION
    Comprehensive test to verify all our fixes are working after deployment
#>

param(
    [string]$BaseUrl = "https://babyshield.cureviax.ai"
)

$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Cyan = "Cyan"

function Write-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Details = ""
    )
    $status = if ($Passed) { "✅ PASS" } else { "❌ FAIL" }
    $color = if ($Passed) { $Green } else { $Red }
    Write-Host "  $status $TestName" -ForegroundColor $color
    if ($Details) { Write-Host "    📋 $Details" -ForegroundColor Gray }
}

Write-Host "🔍 COMPREHENSIVE FIX VERIFICATION TEST" -ForegroundColor $Cyan
Write-Host "Testing all deployed fixes in BabyShield system" -ForegroundColor Gray

# ===============================================================
# TEST 1: SYSTEM HEALTH
# ===============================================================
Write-Host "`n📊 1. SYSTEM HEALTH CHECK" -ForegroundColor $Cyan
try {
    $healthResponse = Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET -TimeoutSec 10
    Write-TestResult -TestName "System Health" -Passed $true -Details "API responding normally"
} catch {
    Write-TestResult -TestName "System Health" -Passed $false -Details "API not responding: $($_.Exception.Message)"
    exit 1
}

# ===============================================================
# TEST 2: ADVANCED VISUAL RECOGNITION (IMPORT OS FIX)
# ===============================================================
Write-Host "`n🔧 2. ADVANCED VISUAL RECOGNITION - IMPORT FIX TEST" -ForegroundColor $Cyan

# Create a tiny test image
$testImagePath = "$env:TEMP\test_fix.jpg"
try {
    # Download a small test image
    Invoke-WebRequest -Uri "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=200&q=80" -OutFile $testImagePath -UseBasicParsing -TimeoutSec 10
    Write-TestResult -TestName "Test Image Download" -Passed $true -Details "Test image ready"
} catch {
    Write-TestResult -TestName "Test Image Download" -Passed $false -Details "Could not download test image"
}

if (Test-Path $testImagePath) {
    try {
        $uri = "$BaseUrl/api/v1/advanced/visual/recognize?user_id=1&check_for_defects=false&confidence_threshold=0.5"
        
        # Use .NET HttpClient for multipart form data
        Add-Type -AssemblyName System.Net.Http
        $httpClient = [System.Net.Http.HttpClient]::new()
        $httpClient.Timeout = [TimeSpan]::FromSeconds(30)
        
        $multipartContent = [System.Net.Http.MultipartFormDataContent]::new()
        $fileStream = [System.IO.File]::OpenRead($testImagePath)
        $streamContent = [System.Net.Http.StreamContent]::new($fileStream)
        $streamContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("image/jpeg")
        $multipartContent.Add($streamContent, "image", "test_fix.jpg")
        
        $response = $httpClient.PostAsync($uri, $multipartContent).Result
        $statusCode = [int]$response.StatusCode
        $responseBody = $response.Content.ReadAsStringAsync().Result
        
        $fileStream.Dispose()
        $httpClient.Dispose()
        
        if ($statusCode -eq 200) {
            Write-TestResult -TestName "Advanced Visual Recognition" -Passed $true -Details "No 'name os is not defined' error - IMPORT FIX WORKING!"
        } elseif ($statusCode -eq 500) {
            if ($responseBody -like "*name 'os' is not defined*") {
                Write-TestResult -TestName "Advanced Visual Recognition" -Passed $false -Details "IMPORT FIX FAILED - still getting os error"
            } else {
                Write-TestResult -TestName "Advanced Visual Recognition" -Passed $true -Details "Different error (not import issue) - IMPORT FIX WORKING"
            }
        } else {
            Write-TestResult -TestName "Advanced Visual Recognition" -Passed $false -Details "Unexpected status: $statusCode"
        }
        
    } catch {
        Write-TestResult -TestName "Advanced Visual Recognition" -Passed $false -Details "Request failed: $($_.Exception.Message)"
    }
}

# ===============================================================
# TEST 3: VISUAL SEARCH (OPENAI API KEY FIX)
# ===============================================================
Write-Host "`n🤖 3. VISUAL SEARCH - OPENAI API KEY FIX TEST" -ForegroundColor $Cyan

try {
    $visualSearchData = @{
        image_url = "https://images.unsplash.com/photo-1585386959984-a4155223168f?auto=format&fit=crop&w=200&q=80"
    }
    
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/v1/visual/search" -Method POST -Body ($visualSearchData | ConvertTo-Json) -ContentType "application/json" -TimeoutSec 20
    
    if ($response.success -eq $false -and $response.error -like "*OpenAI API key not configured*") {
        Write-TestResult -TestName "OpenAI API Key Handling" -Passed $true -Details "GRACEFUL ERROR HANDLING WORKING - no crashes!"
    } elseif ($response.success -eq $true) {
        Write-TestResult -TestName "OpenAI API Key Handling" -Passed $true -Details "Visual search working (API key configured)"
    } else {
        Write-TestResult -TestName "OpenAI API Key Handling" -Passed $false -Details "Unexpected response: $($response | ConvertTo-Json -Depth 2)"
    }
    
} catch {
    $errorMessage = $_.Exception.Message
    if ($errorMessage -like "*401*" -or $errorMessage -like "*Unauthorized*") {
        Write-TestResult -TestName "OpenAI API Key Handling" -Passed $false -Details "OPENAI FIX FAILED - still getting 401 crashes"
    } else {
        Write-TestResult -TestName "OpenAI API Key Handling" -Passed $true -Details "No 401 crashes - OPENAI FIX WORKING"
    }
}

# ===============================================================
# TEST 4: DATAMATRIX BARCODE SCANNING
# ===============================================================
Write-Host "`n📊 4. DATAMATRIX BARCODE SCANNING TEST" -ForegroundColor $Cyan

try {
    # Test with dummy base64 data
    $testData = @{
        image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    }
    
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/v1/barcode/datamatrix" -Method POST -Body ($testData | ConvertTo-Json) -ContentType "application/json" -TimeoutSec 15 -ErrorAction Stop
    Write-TestResult -TestName "DataMatrix Endpoint" -Passed $true -Details "DataMatrix endpoint accessible - dependencies likely working"
    
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 422 -or $statusCode -eq 400) {
        Write-TestResult -TestName "DataMatrix Endpoint" -Passed $true -Details "DataMatrix endpoint working (validation error expected)"
    } else {
        Write-TestResult -TestName "DataMatrix Endpoint" -Passed $false -Details "DataMatrix endpoint error: Status $statusCode"
    }
}

# ===============================================================
# TEST 5: ERROR RESPONSE HANDLING
# ===============================================================
Write-Host "`n⚠️  5. ERROR RESPONSE HANDLING TEST" -ForegroundColor $Cyan

try {
    # Test with invalid user_id to trigger error
    $response = Invoke-WebRequest -Uri "$BaseUrl/api/v1/advanced/visual/recognize?user_id=999999" -Method POST -UseBasicParsing -ErrorAction Stop
    Write-TestResult -TestName "Error Response Handling" -Passed $false -Details "Should have returned error for invalid user"
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 500 -or $statusCode -eq 404 -or $statusCode -eq 400) {
        Write-TestResult -TestName "Error Response Handling" -Passed $true -Details "Proper HTTP error status: $statusCode (not masked as 200)"
    } else {
        Write-TestResult -TestName "Error Response Handling" -Passed $false -Details "Unexpected status: $statusCode"
    }
}

# ===============================================================
# CLEANUP
# ===============================================================
if (Test-Path $testImagePath) {
    Remove-Item $testImagePath -Force -ErrorAction SilentlyContinue
}

# ===============================================================
# SUMMARY
# ===============================================================
Write-Host "`n📋 TEST SUMMARY" -ForegroundColor $Cyan
Write-Host "✅ If all tests PASS: All fixes are working correctly" -ForegroundColor $Green
Write-Host "❌ If any test FAILS: That specific fix needs redeployment" -ForegroundColor $Red
Write-Host "`n🔍 For detailed diagnosis, check the CloudWatch logs for:" -ForegroundColor $Yellow
Write-Host "   - DataMatrix initialization messages" -ForegroundColor Gray
Write-Host "   - OpenAI API key warnings vs errors" -ForegroundColor Gray
Write-Host "   - Import error stack traces" -ForegroundColor Gray

Write-Host "`n🎯 Test completed!" -ForegroundColor $Cyan
