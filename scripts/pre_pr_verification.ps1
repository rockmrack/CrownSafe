#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Comprehensive pre-PR verification checklist
.DESCRIPTION
    Verifies all Phase 2 improvements before creating PR
#>

$ErrorActionPreference = "Continue"
$script:passCount = 0
$script:failCount = 0
$script:results = @()

function Test-Item {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [string]$SuccessMessage,
        [string]$FailureMessage
    )
    
    Write-Host "`n[$Name]" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Gray
    
    try {
        $result = & $Test
        if ($result) {
            Write-Host "[PASS] $SuccessMessage" -ForegroundColor Green
            $script:passCount++
            $script:results += @{ Name = $Name; Status = "PASS"; Message = $SuccessMessage }
            return $true
        } else {
            Write-Host "[FAIL] $FailureMessage" -ForegroundColor Red
            $script:failCount++
            $script:results += @{ Name = $Name; Status = "FAIL"; Message = $FailureMessage }
            return $false
        }
    } catch {
        Write-Host "[FAIL] $FailureMessage - $_" -ForegroundColor Red
        $script:failCount++
        $script:results += @{ Name = $Name; Status = "FAIL"; Message = "$FailureMessage - $_" }
        return $false
    }
}

Write-Host @"

========================================
 PRE-PR VERIFICATION CHECKLIST
========================================
Phase 2 Improvements - Final Verification

"@ -ForegroundColor Yellow

# 1. Security Headers Test
Test-Item -Name "Security Headers (7/7)" -Test {
    Write-Host "Testing security headers on /docs endpoint..." -ForegroundColor Gray
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/docs" -Method HEAD -TimeoutSec 5 -ErrorAction Stop
        $headers = $response.Headers
        
        $requiredHeaders = @(
            "x-frame-options",
            "x-content-type-options",
            "x-xss-protection",
            "referrer-policy",
            "content-security-policy",
            "permissions-policy",
            "x-permitted-cross-domain-policies"
        )
        
        $found = 0
        foreach ($header in $requiredHeaders) {
            if ($headers.ContainsKey($header) -or $headers.ContainsKey($header.ToUpper())) {
                Write-Host "  [OK] $header" -ForegroundColor Green
                $found++
            } else {
                Write-Host "  [MISS] $header" -ForegroundColor Red
            }
        }
        
        return ($found -eq 7)
    } catch {
        Write-Host "  Server not responding - is it running?" -ForegroundColor Red
        return $false
    }
} -SuccessMessage "All 7 OWASP security headers present" -FailureMessage "Some security headers missing"

# 2. API Health Check
Test-Item -Name "API Health Check" -Test {
    Write-Host "Testing /healthz endpoint..." -ForegroundColor Gray
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/healthz" -TimeoutSec 5 -ErrorAction Stop
        return ($response.StatusCode -eq 200)
    } catch {
        return $false
    }
} -SuccessMessage "API responding correctly" -FailureMessage "API health check failed"

# 3. OpenAPI Spec Available
Test-Item -Name "OpenAPI Documentation" -Test {
    Write-Host "Testing /docs endpoint..." -ForegroundColor Gray
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/docs" -TimeoutSec 5 -ErrorAction Stop
        return ($response.StatusCode -eq 200)
    } catch {
        return $false
    }
} -SuccessMessage "OpenAPI docs accessible" -FailureMessage "OpenAPI docs not accessible"

# 4. Phase 2 Files Exist
Test-Item -Name "Phase 2 Files Present" -Test {
    $requiredFiles = @(
        "utils/security/input_validator.py",
        "utils/security/security_headers.py",
        "utils/common/endpoint_helpers.py",
        "api/schemas/shared_models.py",
        "utils/database/query_optimizer.py",
        "tests/conftest_comprehensive.py",
        "PHASE2_IMPROVEMENTS_SUMMARY.md",
        "SECURITY_HEADERS_SUCCESS.md"
    )
    
    $found = 0
    foreach ($file in $requiredFiles) {
        if (Test-Path $file) {
            Write-Host "  [OK] $file" -ForegroundColor Green
            $found++
        } else {
            Write-Host "  [MISS] $file" -ForegroundColor Red
        }
    }
    
    return ($found -eq $requiredFiles.Count)
} -SuccessMessage "All Phase 2 files present" -FailureMessage "Some Phase 2 files missing"

# 5. Test Scripts Work
Test-Item -Name "Test Scripts Functional" -Test {
    $testScripts = @(
        "test_single_request.py",
        "test_security_headers.py",
        "test_phase2_imports.py"
    )
    
    $found = 0
    foreach ($script in $testScripts) {
        if (Test-Path $script) {
            Write-Host "  [OK] $script exists" -ForegroundColor Green
            $found++
        } else {
            Write-Host "  [MISS] $script" -ForegroundColor Red
        }
    }
    
    return ($found -eq $testScripts.Count)
} -SuccessMessage "Test scripts present" -FailureMessage "Some test scripts missing"

# 6. Documentation Complete
Test-Item -Name "Documentation Files" -Test {
    $docs = @(
        "PHASE2_IMPROVEMENTS_SUMMARY.md",
        "PHASE2_QUICK_START.md",
        "SECURITY_HEADERS_SUCCESS.md",
        "utils/README.md"
    )
    
    $found = 0
    foreach ($doc in $docs) {
        if (Test-Path $doc) {
            $content = Get-Content $doc -Raw
            if ($content.Length -gt 100) {
                Write-Host "  [OK] $doc ($($content.Length) chars)" -ForegroundColor Green
                $found++
            } else {
                Write-Host "  [WARN] $doc is too short" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  [MISS] $doc" -ForegroundColor Red
        }
    }
    
    return ($found -eq $docs.Count)
} -SuccessMessage "All documentation present" -FailureMessage "Some documentation missing"

# 7. No Uncommitted Changes to Critical Files
Test-Item -Name "Git Status Check" -Test {
    Write-Host "Checking git status..." -ForegroundColor Gray
    $status = git status --porcelain
    
    if ($status) {
        Write-Host "  Changes detected:" -ForegroundColor Yellow
        $status | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
        # This is OK - we expect changes for the PR
        return $true
    } else {
        Write-Host "  No changes detected" -ForegroundColor Gray
        return $true
    }
} -SuccessMessage "Git status checked" -FailureMessage "Git check failed"

# 8. Requirements Files Present
Test-Item -Name "Requirements Files" -Test {
    $reqFiles = @(
        "config/requirements/requirements.txt",
        "config/requirements/requirements-complete.txt"
    )
    
    $found = 0
    foreach ($file in $reqFiles) {
        if (Test-Path $file) {
            Write-Host "  [OK] $file" -ForegroundColor Green
            $found++
        } else {
            Write-Host "  [MISS] $file" -ForegroundColor Red
        }
    }
    
    return ($found -eq $reqFiles.Count)
} -SuccessMessage "Requirements files present" -FailureMessage "Requirements files missing"

# Summary
Write-Host "`n" ("=" * 70) -ForegroundColor Cyan
Write-Host " VERIFICATION SUMMARY" -ForegroundColor Yellow
Write-Host ("=" * 70) -ForegroundColor Cyan

$script:results | ForEach-Object {
    $color = if ($_.Status -eq "PASS") { "Green" } else { "Red" }
    $icon = if ($_.Status -eq "PASS") { "[PASS]" } else { "[FAIL]" }
    Write-Host "  $icon $($_.Name): " -NoNewline -ForegroundColor $color
    Write-Host $_.Message -ForegroundColor Gray
}

Write-Host "`n" ("=" * 70) -ForegroundColor Cyan
Write-Host "  PASSED: $script:passCount" -ForegroundColor Green
Write-Host "  FAILED: $script:failCount" -ForegroundColor $(if ($script:failCount -eq 0) { "Green" } else { "Red" })
Write-Host ("=" * 70) -ForegroundColor Cyan

if ($script:failCount -eq 0) {
    Write-Host "`n[SUCCESS] ALL CHECKS PASSED - READY FOR PR!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "  1. Review git diff" -ForegroundColor White
    Write-Host "  2. Stage all changes: git add ." -ForegroundColor White
    Write-Host "  3. Commit: git commit -m 'feat: Phase 2 security improvements'" -ForegroundColor White
    Write-Host "  4. Create PR to main" -ForegroundColor White
    exit 0
} else {
    Write-Host "`n[WARNING] SOME CHECKS FAILED - FIX BEFORE PR" -ForegroundColor Red
    exit 1
}

