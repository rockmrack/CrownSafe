#!/usr/bin/env pwsh
<#
.SYNOPSIS
Comprehensive validation of all visual recognition fixes

.DESCRIPTION
This script validates:
1. Python syntax and imports
2. All visual recognition endpoints
3. Error handling scenarios
4. Integration points
5. Expected error types and responses
#>

param(
    [string]$BaseUrl = "https://babyshield.cureviax.ai"
)

$ErrorActionPreference = "Continue"  # Don't stop on individual test failures

function Write-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Details = ""
    )
    
    if ($Passed) {
        Write-Host "✅ $TestName" -ForegroundColor Green
        if ($Details) { Write-Host "   └─ $Details" -ForegroundColor Gray }
    } else {
        Write-Host "❌ $TestName" -ForegroundColor Red
        if ($Details) { Write-Host "   └─ $Details" -ForegroundColor Yellow }
    }
}

function Test-PythonSyntax {
    Write-Host "`n🐍 PYTHON SYNTAX VALIDATION" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    
    $pythonFiles = @(
        "agents/visual/visual_search_agent/agent_logic.py",
        "api/visual_agent_endpoints.py", 
        "api/advanced_features_endpoints.py"
    )
    
    $allPassed = $true
    
    foreach ($file in $pythonFiles) {
        if (Test-Path $file) {
            try {
                $result = python -m py_compile $file 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-TestResult -TestName "Syntax: $file" -Passed $true
                } else {
                    Write-TestResult -TestName "Syntax: $file" -Passed $false -Details $result
                    $allPassed = $false
                }
            } catch {
                Write-TestResult -TestName "Syntax: $file" -Passed $false -Details $_.Exception.Message
                $allPassed = $false
            }
        } else {
            Write-TestResult -TestName "File exists: $file" -Passed $false -Details "File not found"
            $allPassed = $false
        }
    }
    
    return $allPassed
}

function Test-ImportStructure {
    Write-Host "`n📦 IMPORT STRUCTURE VALIDATION" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    
    $testScript = @'
import sys
import os
sys.path.insert(0, os.getcwd())

try:
    from agents.visual.visual_search_agent.agent_logic import VisualSearchAgentLogic, _fetch_image_bytes, _is_s3_url
    print("✅ VisualSearchAgentLogic imports successful")
except Exception as e:
    print(f"❌ VisualSearchAgentLogic import failed: {e}")
    sys.exit(1)

try:
    import httpx
    import base64
    from urllib.parse import urlparse
    print("✅ Required dependencies available")
except Exception as e:
    print(f"❌ Dependencies missing: {e}")
    sys.exit(1)

# Test agent initialization
try:
    agent = VisualSearchAgentLogic("test-agent")
    print("✅ Agent initialization successful")
except Exception as e:
    print(f"❌ Agent initialization failed: {e}")
    sys.exit(1)

print("✅ All imports and initialization successful")
'@
    
    $testScript | Out-File -FilePath "temp_import_test.py" -Encoding UTF8
    
    try {
        $result = python temp_import_test.py 2>&1
        $success = $LASTEXITCODE -eq 0
        
        if ($success) {
            Write-TestResult -TestName "Import Structure" -Passed $true -Details "All imports working"
        } else {
            Write-TestResult -TestName "Import Structure" -Passed $false -Details $result
        }
        
        return $success
    } finally {
        Remove-Item "temp_import_test.py" -ErrorAction SilentlyContinue
    }
}

function Test-VisualEndpoints {
    Write-Host "`n🔍 VISUAL RECOGNITION ENDPOINT TESTS" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    
    $allPassed = $true
    
    # Test 1: Visual Search Endpoint
    Write-Host "`n1. Testing /api/v1/visual/search..." -ForegroundColor Yellow
    
    $testImageUrl = "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format`&fit=crop`&w=600`&q=80"
    $body = @{ image_url = $testImageUrl } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod "$BaseUrl/api/v1/visual/search" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 60
        
        # Check response structure
        $hasStatus = $null -ne $response.status
        $hasProperErrorHandling = $null -ne $response.error_type
        
        if ($response.status -eq "COMPLETED") {
            Write-TestResult -TestName "Visual Search Success" -Passed $true -Details "Status: COMPLETED"
        } elseif ($response.status -eq "FAILED" -and $response.error_type -in @("image_fetch_failed", "api_key_missing")) {
            Write-TestResult -TestName "Visual Search Error Handling" -Passed $true -Details "Proper error type: $($response.error_type)"
        } else {
            Write-TestResult -TestName "Visual Search Response" -Passed $false -Details "Unexpected response: $($response | ConvertTo-Json -Compress)"
            $allPassed = $false
        }
        
    } catch {
        Write-TestResult -TestName "Visual Search Endpoint" -Passed $false -Details $_.Exception.Message
        $allPassed = $false
    }
    
    # Test 2: Invalid Image URL
    Write-Host "`n2. Testing error handling with invalid URL..." -ForegroundColor Yellow
    
    $invalidUrl = "https://invalid-domain-that-does-not-exist.com/image.jpg"
    $body = @{ image_url = $invalidUrl } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod "$BaseUrl/api/v1/visual/search" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30
        
        if ($response.status -eq "FAILED" -and $response.error_type -eq "image_fetch_failed") {
            Write-TestResult -TestName "Invalid URL Error Handling" -Passed $true -Details "Proper error type: image_fetch_failed"
        } else {
            Write-TestResult -TestName "Invalid URL Error Handling" -Passed $false -Details "Expected image_fetch_failed, got: $($response.error_type)"
            $allPassed = $false
        }
        
    } catch {
        Write-TestResult -TestName "Invalid URL Test" -Passed $false -Details $_.Exception.Message
        $allPassed = $false
    }
    
    # Test 3: Non-image URL
    Write-Host "`n3. Testing non-image URL handling..." -ForegroundColor Yellow
    
    $nonImageUrl = "https://httpbin.org/json"
    $body = @{ image_url = $nonImageUrl } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod "$BaseUrl/api/v1/visual/search" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30
        
        if ($response.status -eq "FAILED" -and $response.error_type -eq "image_fetch_failed") {
            Write-TestResult -TestName "Non-Image URL Error Handling" -Passed $true -Details "Properly rejected non-image content"
        } else {
            Write-TestResult -TestName "Non-Image URL Error Handling" -Passed $false -Details "Expected image_fetch_failed, got: $($response.error_type)"
            $allPassed = $false
        }
        
    } catch {
        Write-TestResult -TestName "Non-Image URL Test" -Passed $false -Details $_.Exception.Message
        $allPassed = $false
    }
    
    return $allPassed
}

function Test-SystemIntegration {
    Write-Host "`n🔗 SYSTEM INTEGRATION TESTS" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    
    $allPassed = $true
    
    # Test health endpoint
    try {
        $health = Invoke-RestMethod "$BaseUrl/healthz" -TimeoutSec 15
        Write-TestResult -TestName "Health Check" -Passed $true
    } catch {
        Write-TestResult -TestName "Health Check" -Passed $false -Details $_.Exception.Message
        $allPassed = $false
    }
    
    # Test barcode lookup (should still work)
    try {
        $barcode = Invoke-RestMethod "$BaseUrl/api/v1/lookup/barcode?code=012914632109" -TimeoutSec 15
        if ($barcode.ok) {
            Write-TestResult -TestName "Barcode Lookup Integration" -Passed $true
        } else {
            Write-TestResult -TestName "Barcode Lookup Integration" -Passed $false -Details $barcode.message
            $allPassed = $false
        }
    } catch {
        Write-TestResult -TestName "Barcode Lookup Integration" -Passed $false -Details $_.Exception.Message
        $allPassed = $false
    }
    
    return $allPassed
}

# ==================== MAIN EXECUTION ====================

Write-Host "🔍 COMPREHENSIVE VISUAL RECOGNITION VALIDATION" -ForegroundColor Magenta
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "Target: $BaseUrl" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan

$results = @{}

# Run all test suites
$results["Syntax"] = Test-PythonSyntax
$results["Imports"] = Test-ImportStructure
$results["Endpoints"] = Test-VisualEndpoints
$results["Integration"] = Test-SystemIntegration

# Summary
Write-Host "`n📊 VALIDATION SUMMARY" -ForegroundColor Magenta
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$totalPassed = 0
$totalTests = $results.Count

foreach ($testSuite in $results.Keys) {
    $passed = $results[$testSuite]
    if ($passed) {
        Write-Host "✅ $testSuite" -ForegroundColor Green
        $totalPassed++
    } else {
        Write-Host "❌ $testSuite" -ForegroundColor Red
    }
}

Write-Host "`nOverall Result: $totalPassed/$totalTests test suites passed" -ForegroundColor $(if ($totalPassed -eq $totalTests) { "Green" } else { "Yellow" })

if ($totalPassed -eq $totalTests) {
    Write-Host "`n🎉 ALL VALIDATIONS PASSED! Ready for deployment." -ForegroundColor Green
    Write-Host "Run '.\DEPLOY_VISUAL_FIXES.ps1' to deploy the fixes." -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "`n⚠️  SOME VALIDATIONS FAILED! Review the issues above before deploying." -ForegroundColor Yellow
    exit 1
}
