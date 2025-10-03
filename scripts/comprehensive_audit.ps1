#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Comprehensive system audit for BabyShield Backend
.DESCRIPTION
    Scans for duplicates, import errors, naming issues, and configuration conflicts
#>

$ErrorActionPreference = "Continue"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  BABYSHIELD COMPREHENSIVE AUDIT" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1. CHECK FOR DUPLICATE PYTHON FILES
Write-Host "[1/8] Checking for duplicate Python files..." -ForegroundColor Yellow
$duplicatePy = Get-ChildItem -Recurse -Include "*.py" -ErrorAction SilentlyContinue | 
    Group-Object Name | 
    Where-Object Count -gt 1

if ($duplicatePy) {
    Write-Host "  [WARNING] Found duplicate Python files:" -ForegroundColor Red
    foreach ($dup in $duplicatePy) {
        Write-Host "    - $($dup.Name) ($($dup.Count) copies)" -ForegroundColor Yellow
        $dup.Group | ForEach-Object { Write-Host "      $($_.FullName)" -ForegroundColor Gray }
    }
} else {
    Write-Host "  [OK] No duplicate Python files found" -ForegroundColor Green
}

# 2. CHECK FOR DUPLICATE CONFIG FILES
Write-Host "`n[2/8] Checking for duplicate configuration files..." -ForegroundColor Yellow
$duplicateConfig = Get-ChildItem -Recurse -Include "*.json","*.yml","*.yaml","*.toml","*.ini" -ErrorAction SilentlyContinue | 
    Group-Object Name | 
    Where-Object Count -gt 1

if ($duplicateConfig) {
    Write-Host "  [WARNING] Found duplicate config files:" -ForegroundColor Red
    foreach ($dup in $duplicateConfig) {
        Write-Host "    - $($dup.Name) ($($dup.Count) copies)" -ForegroundColor Yellow
        $dup.Group | ForEach-Object { Write-Host "      $($_.FullName)" -ForegroundColor Gray }
    }
} else {
    Write-Host "  [OK] No duplicate config files found" -ForegroundColor Green
}

# 3. CHECK FOR BACKUP/TEMP FILES
Write-Host "`n[3/8] Checking for backup/temp files..." -ForegroundColor Yellow
$backupFiles = Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue | 
    Where-Object { $_.Name -match "\.(bak|old|backup|tmp|temp|~)$|~$" }

if ($backupFiles) {
    Write-Host "  [WARNING] Found backup/temp files:" -ForegroundColor Yellow
    $backupFiles | ForEach-Object { Write-Host "    - $($_.FullName)" -ForegroundColor Gray }
} else {
    Write-Host "  [OK] No backup/temp files found" -ForegroundColor Green
}

# 4. CHECK FOR NAMING INCONSISTENCIES (files with mixed case)
Write-Host "`n[4/8] Checking for naming inconsistencies..." -ForegroundColor Yellow
$mixedCase = Get-ChildItem -Recurse -File -Include "*.py" -ErrorAction SilentlyContinue | 
    Where-Object { $_.BaseName -cmatch "[A-Z]" -and $_.BaseName -cmatch "[a-z]" -and $_.BaseName -match "[A-Z][a-z]+[A-Z]" }

if ($mixedCase) {
    Write-Host "  [INFO] Found files with mixed case (may be intentional):" -ForegroundColor Yellow
    $mixedCase | Select-Object -First 10 | ForEach-Object { Write-Host "    - $($_.Name)" -ForegroundColor Gray }
    if ($mixedCase.Count -gt 10) {
        Write-Host "    ... and $($mixedCase.Count - 10) more" -ForegroundColor Gray
    }
} else {
    Write-Host "  [OK] No unusual naming patterns found" -ForegroundColor Green
}

# 5. CHECK FOR LARGE FILES (> 1MB)
Write-Host "`n[5/8] Checking for large files..." -ForegroundColor Yellow
$largeFiles = Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue | 
    Where-Object { $_.Length -gt 1MB } | 
    Sort-Object Length -Descending | 
    Select-Object -First 10

if ($largeFiles) {
    Write-Host "  [INFO] Found large files:" -ForegroundColor Yellow
    $largeFiles | ForEach-Object { 
        $sizeMB = [math]::Round($_.Length / 1MB, 2)
        Write-Host "    - $($_.Name) ($sizeMB MB)" -ForegroundColor Gray 
    }
} else {
    Write-Host "  [OK] No unusually large files found" -ForegroundColor Green
}

# 6. CHECK FOR DATABASE FILES IN REPO
Write-Host "`n[6/8] Checking for database files..." -ForegroundColor Yellow
$dbFiles = Get-ChildItem -Recurse -Include "*.db","*.sqlite","*.sqlite3" -ErrorAction SilentlyContinue

if ($dbFiles) {
    Write-Host "  [WARNING] Found database files (should not be in repo):" -ForegroundColor Red
    $dbFiles | ForEach-Object { Write-Host "    - $($_.FullName)" -ForegroundColor Yellow }
} else {
    Write-Host "  [OK] No database files found" -ForegroundColor Green
}

# 7. CHECK FOR MULTIPLE DOCKERFILES
Write-Host "`n[7/8] Checking for multiple Dockerfiles..." -ForegroundColor Yellow
$dockerfiles = Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue | 
    Where-Object { $_.Name -match "^Dockerfile" }

if ($dockerfiles.Count -gt 2) {
    Write-Host "  [INFO] Found multiple Dockerfiles:" -ForegroundColor Yellow
    $dockerfiles | ForEach-Object { Write-Host "    - $($_.FullName)" -ForegroundColor Gray }
} else {
    Write-Host "  [OK] Dockerfile count normal ($($dockerfiles.Count))" -ForegroundColor Green
}

# 8. CHECK FOR PYTHON IMPORT ERRORS (sample check)
Write-Host "`n[8/8] Checking Python syntax..." -ForegroundColor Yellow
$pyFiles = Get-ChildItem -Recurse -Include "*.py" -ErrorAction SilentlyContinue | Select-Object -First 5
$syntaxErrors = @()

foreach ($file in $pyFiles) {
    $result = python -m py_compile $file.FullName 2>&1
    if ($LASTEXITCODE -ne 0) {
        $syntaxErrors += $file.Name
    }
}

if ($syntaxErrors) {
    Write-Host "  [WARNING] Found files with syntax errors:" -ForegroundColor Red
    $syntaxErrors | ForEach-Object { Write-Host "    - $_" -ForegroundColor Yellow }
} else {
    Write-Host "  [OK] Sample files passed syntax check" -ForegroundColor Green
}

# SUMMARY
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  AUDIT SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$issues = 0
if ($duplicatePy) { $issues++ }
if ($duplicateConfig) { $issues++ }
if ($backupFiles) { $issues++ }
if ($dbFiles) { $issues++ }
if ($syntaxErrors) { $issues++ }

Write-Host "`nIssues Found: $issues" -ForegroundColor $(if ($issues -eq 0) { "Green" } else { "Yellow" })
Write-Host "`nRecommendations:" -ForegroundColor White

if ($dbFiles) {
    Write-Host "  - Add *.db to .gitignore" -ForegroundColor Yellow
}
if ($backupFiles) {
    Write-Host "  - Remove backup/temp files" -ForegroundColor Yellow
}
if ($duplicatePy -or $duplicateConfig) {
    Write-Host "  - Review and consolidate duplicate files" -ForegroundColor Yellow
}
if ($issues -eq 0) {
    Write-Host "  - Codebase looks clean!" -ForegroundColor Green
}

Write-Host ""

