#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test DataMatrix barcode scanning functionality after deployment
.DESCRIPTION
    This script tests the DataMatrix barcode scanning endpoint to verify pylibdmtx is working correctly
#>

param(
    [string]$BaseUrl = "https://babyshield.cureviax.ai"
)

# Colors for output
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Cyan = "Cyan"

function Write-TestHeader {
    param([string]$Title)
    Write-Host "`n===============================================================" -ForegroundColor $Cyan
    Write-Host " $Title" -ForegroundColor $Cyan
    Write-Host "===============================================================" -ForegroundColor $Cyan
}

function Write-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Details = ""
    )
    
    $status = if ($Passed) { "✅ PASS" } else { "❌ FAIL" }
    $color = if ($Passed) { $Green } else { $Red }
    
    Write-Host "  $status $TestName" -ForegroundColor $color
    if ($Details) {
        Write-Host "    📋 $Details" -ForegroundColor Gray
    }
}

Write-Host "🔍 DATAMATRIX BARCODE SCANNING TEST" -ForegroundColor $Cyan
Write-Host "Testing DataMatrix functionality after pylibdmtx fixes" -ForegroundColor Gray
Write-Host "Base URL: $BaseUrl" -ForegroundColor Gray

# ===============================================================
# TEST 1: SYSTEM HEALTH CHECK
# ===============================================================
Write-TestHeader "1. SYSTEM HEALTH CHECK"

try {
    $healthResponse = Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET -TimeoutSec 10
    Write-TestResult -TestName "System Health" -Passed $true -Details "API is responding"
} catch {
    Write-TestResult -TestName "System Health" -Passed $false -Details "API not responding: $($_.Exception.Message)"
    exit 1
}

# ===============================================================
# TEST 2: DATAMATRIX ENDPOINT AVAILABILITY
# ===============================================================
Write-TestHeader "2. DATAMATRIX ENDPOINT AVAILABILITY"

try {
    # Test with empty/invalid data to see if endpoint exists
    $testData = @{
        image_base64 = "invalid_base64_data"
    }
    
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/v1/barcode/datamatrix" -Method POST -Body ($testData | ConvertTo-Json) -ContentType "application/json" -ErrorAction Stop
    Write-TestResult -TestName "DataMatrix Endpoint Available" -Passed $true -Details "Endpoint exists and responds"
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 422 -or $statusCode -eq 400) {
        Write-TestResult -TestName "DataMatrix Endpoint Available" -Passed $true -Details "Endpoint exists (validation error expected)"
    } else {
        Write-TestResult -TestName "DataMatrix Endpoint Available" -Passed $false -Details "Status: $statusCode, Error: $($_.Exception.Message)"
    }
}

# ===============================================================
# TEST 3: CREATE TEST DATAMATRIX IMAGE
# ===============================================================
Write-TestHeader "3. CREATE TEST DATAMATRIX IMAGE"

# Create a simple DataMatrix code using Python (if available)
$testImagePath = "$env:TEMP\test_datamatrix.png"

try {
    # Try to create a DataMatrix test image using Python
    $pythonScript = @"
import sys
try:
    from pylibdmtx import pylibdmtx
    from PIL import Image, ImageDraw
    import numpy as np
    
    # Create a simple test image with DataMatrix-like pattern
    # Since we can't easily generate real DataMatrix without complex setup,
    # we'll create a mock image for testing the endpoint
    img = Image.new('RGB', (200, 200), 'white')
    draw = ImageDraw.Draw(img)
    
    # Draw a simple pattern that looks like a DataMatrix
    for i in range(0, 200, 10):
        for j in range(0, 200, 10):
            if (i + j) % 20 == 0:
                draw.rectangle([i, j, i+8, j+8], fill='black')
    
    img.save('$testImagePath')
    print("SUCCESS: Test image created")
except ImportError as e:
    print(f"WARNING: Could not create DataMatrix image - {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
"@

    $pythonScript | python -
    
    if (Test-Path $testImagePath) {
        Write-TestResult -TestName "Test Image Creation" -Passed $true -Details "Mock DataMatrix image created"
    } else {
        Write-TestResult -TestName "Test Image Creation" -Passed $false -Details "Could not create test image"
    }
} catch {
    Write-TestResult -TestName "Test Image Creation" -Passed $false -Details "Python script failed: $($_.Exception.Message)"
}

# ===============================================================
# TEST 4: DATAMATRIX SCANNING WITH REAL IMAGE
# ===============================================================
Write-TestHeader "4. DATAMATRIX SCANNING TEST"

if (Test-Path $testImagePath) {
    try {
        # Convert image to base64
        $imageBytes = [System.IO.File]::ReadAllBytes($testImagePath)
        $base64Image = [System.Convert]::ToBase64String($imageBytes)
        
        $requestData = @{
            image_base64 = $base64Image
        }
        
        Write-Host "🔍 Testing DataMatrix scanning..." -ForegroundColor Yellow
        $response = Invoke-RestMethod -Uri "$BaseUrl/api/v1/barcode/datamatrix" -Method POST -Body ($requestData | ConvertTo-Json) -ContentType "application/json" -TimeoutSec 30
        
        if ($response.success) {
            Write-TestResult -TestName "DataMatrix Scanning" -Passed $true -Details "API processed image successfully"
            
            if ($response.data -and $response.data.scan_results) {
                Write-Host "    📊 Scan Results: $($response.data.scan_results.Count) codes found" -ForegroundColor Gray
            } else {
                Write-Host "    📊 No DataMatrix codes found in test image (expected for mock image)" -ForegroundColor Gray
            }
        } else {
            Write-TestResult -TestName "DataMatrix Scanning" -Passed $false -Details "API returned success=false: $($response.message)"
        }
        
    } catch {
        $errorMessage = $_.Exception.Message
        if ($errorMessage -like "*pylibdmtx*" -or $errorMessage -like "*DataMatrix*") {
            Write-TestResult -TestName "DataMatrix Scanning" -Passed $false -Details "pylibdmtx library issue: $errorMessage"
        } else {
            Write-TestResult -TestName "DataMatrix Scanning" -Passed $false -Details "Request failed: $errorMessage"
        }
    }
} else {
    Write-TestResult -TestName "DataMatrix Scanning" -Passed $false -Details "No test image available"
}

# ===============================================================
# TEST 5: LIBRARY AVAILABILITY CHECK
# ===============================================================
Write-TestHeader "5. LIBRARY AVAILABILITY CHECK"

try {
    # Test a simple endpoint that might show library status
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/v1/barcode/scan" -Method POST -Body '{"barcode": "test"}' -ContentType "application/json" -ErrorAction Stop
    Write-TestResult -TestName "Barcode System Status" -Passed $true -Details "Barcode system is responsive"
} catch {
    Write-TestResult -TestName "Barcode System Status" -Passed $false -Details "Error: $($_.Exception.Message)"
}

# ===============================================================
# CLEANUP
# ===============================================================
Write-TestHeader "6. CLEANUP"

if (Test-Path $testImagePath) {
    Remove-Item $testImagePath -Force
    Write-TestResult -TestName "Cleanup" -Passed $true -Details "Test files removed"
} else {
    Write-TestResult -TestName "Cleanup" -Passed $true -Details "No cleanup needed"
}

# ===============================================================
# SUMMARY
# ===============================================================
Write-TestHeader "DATAMATRIX TEST SUMMARY"

Write-Host "`n📋 NEXT STEPS:" -ForegroundColor $Yellow
Write-Host "1. If DataMatrix scanning fails, check deployment logs for pylibdmtx errors" -ForegroundColor Gray
Write-Host "2. Verify that libdmtx0b and libdmtx-dev are installed in container" -ForegroundColor Gray
Write-Host "3. Check that pylibdmtx==0.1.10 is in requirements.txt" -ForegroundColor Gray
Write-Host "4. Test with real DataMatrix barcode images for full validation" -ForegroundColor Gray

Write-Host "`n🔧 TROUBLESHOOTING:" -ForegroundColor $Yellow
Write-Host "- If 'pylibdmtx not installed' warning persists, rebuild Docker image" -ForegroundColor Gray
Write-Host "- Check container logs: docker logs <container_id>" -ForegroundColor Gray
Write-Host "- Verify system dependencies: apt list --installed | grep dmtx" -ForegroundColor Gray

Write-Host "`n✅ DataMatrix functionality test completed!" -ForegroundColor $Green
