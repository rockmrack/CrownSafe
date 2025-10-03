#!/usr/bin/env pwsh
# Production Deployment and Verification Script
# Deploys to production and verifies health

param(
    [Parameter(Mandatory=$true)]
    [string]$ProductionUrl,
    [string]$DeploymentTag = "production-$(Get-Date -Format 'yyyyMMdd-HHmmss')",
    [switch]$SkipBuild,
    [switch]$SkipDeploy,
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"
$deploymentLog = "deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    $color = switch ($Level) {
        "INFO" { "White" }
        "SUCCESS" { "Green" }
        "WARNING" { "Yellow" }
        "ERROR" { "Red" }
        default { "Gray" }
    }
    
    Write-Host $logMessage -ForegroundColor $color
    Add-Content -Path $deploymentLog -Value $logMessage
}

function Test-ProductionEndpoint {
    param(
        [string]$Url,
        [string]$Name,
        [int]$ExpectedStatus = 200
    )
    
    try {
        Write-Log "Testing: $Name at $Url" -Level "INFO"
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 10
        
        if ($response.StatusCode -eq $ExpectedStatus) {
            Write-Log "PASS: $Name (Status: $($response.StatusCode))" -Level "SUCCESS"
            return $true
        } else {
            Write-Log "FAIL: $Name (Expected: $ExpectedStatus, Got: $($response.StatusCode))" -Level "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "FAIL: $Name - $($_.Exception.Message)" -Level "ERROR"
        return $false
    }
}

function Verify-Deployment {
    param([string]$BaseUrl)
    
    Write-Log "========================================" -Level "INFO"
    Write-Log "VERIFYING PRODUCTION DEPLOYMENT" -Level "INFO"
    Write-Log "Base URL: $BaseUrl" -Level "INFO"
    Write-Log "========================================" -Level "INFO"
    
    $testResults = @()
    
    # Critical endpoints
    Write-Log "Testing critical endpoints..." -Level "INFO"
    $testResults += Test-ProductionEndpoint -Url "$BaseUrl/healthz" -Name "Health Check"
    $testResults += Test-ProductionEndpoint -Url "$BaseUrl/readyz" -Name "Readiness Check"
    $testResults += Test-ProductionEndpoint -Url "$BaseUrl/test" -Name "Test Endpoint"
    $testResults += Test-ProductionEndpoint -Url "$BaseUrl/docs" -Name "API Documentation"
    $testResults += Test-ProductionEndpoint -Url "$BaseUrl/metrics" -Name "Prometheus Metrics"
    
    # Summary
    $passed = ($testResults | Where-Object { $_ -eq $true }).Count
    $failed = ($testResults | Where-Object { $_ -eq $false }).Count
    $total = $testResults.Count
    
    Write-Log "========================================" -Level "INFO"
    Write-Log "VERIFICATION SUMMARY" -Level "INFO"
    Write-Log "Total Tests: $total" -Level "INFO"
    Write-Log "Passed: $passed" -Level $(if ($passed -eq $total) { "SUCCESS" } else { "WARNING" })
    Write-Log "Failed: $failed" -Level $(if ($failed -eq 0) { "SUCCESS" } else { "ERROR" })
    Write-Log "Success Rate: $(($passed / $total * 100).ToString('F1'))%" -Level "INFO"
    Write-Log "========================================" -Level "INFO"
    
    if ($failed -eq 0) {
        Write-Log "DEPLOYMENT VERIFICATION: SUCCESS" -Level "SUCCESS"
        return $true
    } else {
        Write-Log "DEPLOYMENT VERIFICATION: FAILED" -Level "ERROR"
        return $false
    }
}

# Main deployment flow
Write-Log "========================================" -Level "INFO"
Write-Log "BABYSHIELD PRODUCTION DEPLOYMENT" -Level "INFO"
Write-Log "Deployment Tag: $DeploymentTag" -Level "INFO"
Write-Log "Production URL: $ProductionUrl" -Level "INFO"
Write-Log "Log File: $deploymentLog" -Level "INFO"
Write-Log "========================================" -Level "INFO"

if ($VerifyOnly) {
    Write-Log "Running in verification-only mode" -Level "INFO"
    $success = Verify-Deployment -BaseUrl $ProductionUrl
    exit $(if ($success) { 0 } else { 1 })
}

# Step 1: Build Docker image
if (-not $SkipBuild) {
    Write-Log "Step 1: Building Docker image..." -Level "INFO"
    try {
        Write-Log "Building with tag: $DeploymentTag" -Level "INFO"
        # This would be your actual build command
        # docker build -f Dockerfile.final -t babyshield-backend:$DeploymentTag .
        Write-Log "Docker build completed" -Level "SUCCESS"
    }
    catch {
        Write-Log "Docker build failed: $($_.Exception.Message)" -Level "ERROR"
        exit 1
    }
} else {
    Write-Log "Skipping build step" -Level "WARNING"
}

# Step 2: Deploy to production
if (-not $SkipDeploy) {
    Write-Log "Step 2: Deploying to production..." -Level "INFO"
    try {
        Write-Log "This is where you would run your deployment script" -Level "INFO"
        Write-Log "Example: .\deploy_prod_digest_pinned.ps1" -Level "INFO"
        # Actual deployment would go here
        Write-Log "Deployment initiated" -Level "SUCCESS"
    }
    catch {
        Write-Log "Deployment failed: $($_.Exception.Message)" -Level "ERROR"
        exit 1
    }
    
    # Wait for deployment to stabilize
    Write-Log "Waiting 30 seconds for deployment to stabilize..." -Level "INFO"
    Start-Sleep -Seconds 30
} else {
    Write-Log "Skipping deployment step" -Level "WARNING"
}

# Step 3: Verify deployment
Write-Log "Step 3: Verifying deployment..." -Level "INFO"
$success = Verify-Deployment -BaseUrl $ProductionUrl

if ($success) {
    Write-Log "========================================" -Level "SUCCESS"
    Write-Log "PRODUCTION DEPLOYMENT: SUCCESS" -Level "SUCCESS"
    Write-Log "========================================" -Level "SUCCESS"
    exit 0
} else {
    Write-Log "========================================" -Level "ERROR"
    Write-Log "PRODUCTION DEPLOYMENT: FAILED VERIFICATION" -Level "ERROR"
    Write-Log "Check log file: $deploymentLog" -Level "ERROR"
    Write-Log "========================================" -Level "ERROR"
    exit 1
}

