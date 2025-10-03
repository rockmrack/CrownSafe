#!/usr/bin/env pwsh
# API Endpoint Testing Script
# Tests critical BabyShield API endpoints before production deployment

param(
    [string]$BaseUrl = "http://localhost:8001",
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$testResults = @()

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [hashtable]$Headers = @{},
        [object]$Body = $null,
        [int]$ExpectedStatus = 200
    )
    
    Write-Host "`nTesting: $Name" -ForegroundColor Cyan
    Write-Host "  URL: $Url" -ForegroundColor Gray
    
    try {
        $params = @{
            Uri = $Url
            Method = $Method
            Headers = $Headers
            UseBasicParsing = $true
        }
        
        if ($Body) {
            $params.Body = ($Body | ConvertTo-Json)
            $params.ContentType = "application/json"
        }
        
        $response = Invoke-WebRequest @params
        
        if ($response.StatusCode -eq $ExpectedStatus) {
            Write-Host "  Result: PASS" -ForegroundColor Green
            $script:testResults += @{
                Name = $Name
                Status = "PASS"
                StatusCode = $response.StatusCode
                Message = "Success"
            }
            return $true
        } else {
            Write-Host "  Result: FAIL (Expected $ExpectedStatus, got $($response.StatusCode))" -ForegroundColor Red
            $script:testResults += @{
                Name = $Name
                Status = "FAIL"
                StatusCode = $response.StatusCode
                Message = "Unexpected status code"
            }
            return $false
        }
    }
    catch {
        Write-Host "  Result: FAIL" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        $script:testResults += @{
            Name = $Name
            Status = "FAIL"
            StatusCode = $null
            Message = $_.Exception.Message
        }
        return $false
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BabyShield API Endpoint Testing" -ForegroundColor Cyan
Write-Host "Base URL: $BaseUrl" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Core Health Endpoints
Write-Host "`n=== CORE HEALTH ENDPOINTS ===" -ForegroundColor Yellow
Test-Endpoint -Name "Health Check" -Url "$BaseUrl/healthz"
Test-Endpoint -Name "Readiness Check" -Url "$BaseUrl/readyz"
Test-Endpoint -Name "Test Endpoint" -Url "$BaseUrl/test"

# Documentation Endpoints
Write-Host "`n=== DOCUMENTATION ENDPOINTS ===" -ForegroundColor Yellow
Test-Endpoint -Name "API Documentation (Swagger)" -Url "$BaseUrl/docs"
Test-Endpoint -Name "API Documentation (ReDoc)" -Url "$BaseUrl/redoc"
Test-Endpoint -Name "OpenAPI JSON" -Url "$BaseUrl/openapi.json"

# Monitoring Endpoints
Write-Host "`n=== MONITORING ENDPOINTS ===" -ForegroundColor Yellow
Test-Endpoint -Name "Prometheus Metrics" -Url "$BaseUrl/metrics"

# Public Endpoints (No Auth)
Write-Host "`n=== PUBLIC ENDPOINTS ===" -ForegroundColor Yellow
Test-Endpoint -Name "Root" -Url "$BaseUrl/"

# Print Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TEST SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$totalTests = $testResults.Count
$passedTests = ($testResults | Where-Object { $_.Status -eq "PASS" }).Count
$failedTests = ($testResults | Where-Object { $_.Status -eq "FAIL" }).Count

Write-Host "`nTotal Tests: $totalTests" -ForegroundColor White
Write-Host "Passed: $passedTests" -ForegroundColor Green
Write-Host "Failed: $failedTests" -ForegroundColor Red
Write-Host "Success Rate: $(($passedTests / $totalTests * 100).ToString('F1'))%" -ForegroundColor $(if ($failedTests -eq 0) { "Green" } else { "Yellow" })

if ($failedTests -gt 0) {
    Write-Host "`nFailed Tests:" -ForegroundColor Red
    $testResults | Where-Object { $_.Status -eq "FAIL" } | ForEach-Object {
        Write-Host "  - $($_.Name): $($_.Message)" -ForegroundColor Red
    }
}

Write-Host "`n========================================`n" -ForegroundColor Cyan

# Exit with appropriate code
if ($failedTests -eq 0) {
    Write-Host "All tests passed! Ready for production deployment." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some tests failed. Fix issues before deploying to production." -ForegroundColor Red
    exit 1
}

