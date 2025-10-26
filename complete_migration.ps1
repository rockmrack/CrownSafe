# Complete Crown Safe Migration - Final Steps
# This script completes the database migration and prepares manual fix instructions

Write-Host "`n=== Crown Safe Migration - Final Steps ===" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Continue"
$workDir = "c:\Users\rossd\OneDrive\Documents\Crown Safe"

# Step 1: Check if OneDrive is running
Write-Host "[Step 1/4] Checking OneDrive status..." -ForegroundColor Yellow
$oneDrive = Get-Process -Name "OneDrive" -ErrorAction SilentlyContinue
if ($oneDrive) {
    Write-Host "  ⚠ OneDrive is running - this may cause file locking issues" -ForegroundColor Yellow
    Write-Host "  Recommendation: Pause OneDrive before continuing" -ForegroundColor Yellow
    Write-Host "  (Right-click OneDrive icon -> Pause syncing -> 2 hours)" -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "  Have you paused OneDrive? (y/n)"
    if ($response -ne "y") {
        Write-Host "  Please pause OneDrive and run this script again" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "  ✓ OneDrive is not running" -ForegroundColor Green
}

# Step 2: Attempt database migration
Write-Host ""
Write-Host "[Step 2/4] Attempting database migration..." -ForegroundColor Yellow
Set-Location "$workDir\db"
$env:DATABASE_URL = "sqlite:///c:/Users/rossd/OneDrive/Documents/Crown Safe/db/babyshield_dev.db"

Write-Host "  Running: alembic upgrade head" -ForegroundColor Gray
$migrationOutput = alembic upgrade head 2>&1
$migrationSuccess = $LASTEXITCODE -eq 0

if ($migrationSuccess) {
    Write-Host "  ✓ Database migration completed successfully!" -ForegroundColor Green
    $migrationOutput | Where-Object { $_ -match "Running upgrade|Dropped|Removed" } | ForEach-Object {
        Write-Host "    $_" -ForegroundColor Cyan
    }
}
else {
    Write-Host "  ✗ Migration failed (likely OneDrive locking)" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Alternative: Use the pre-migrated database from temp folder" -ForegroundColor Yellow
    Write-Host "  Run these commands:" -ForegroundColor Yellow
    Write-Host "    1. Pause OneDrive (right-click icon -> Pause 2 hours)" -ForegroundColor Gray
    Write-Host "    2. Remove-Item '$workDir\db\babyshield_dev.db' -Force" -ForegroundColor Gray
    Write-Host "    3. Copy-Item 'C:\Users\rossd\AppData\Local\Temp\babyshield_dev.db' '$workDir\db\babyshield_dev.db'" -ForegroundColor Gray
    Write-Host "    4. Resume OneDrive" -ForegroundColor Gray
}

# Step 3: Verify database tables (if migration succeeded)
if ($migrationSuccess) {
    Write-Host ""
    Write-Host "[Step 3/4] Verifying Crown Safe tables..." -ForegroundColor Yellow
    Set-Location $workDir
    
    $verifyScript = @"
import sqlite3
conn = sqlite3.connect('db/babyshield_dev.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'hair%' OR name LIKE 'brand%' OR name LIKE 'salon%' OR name LIKE 'product%' OR name LIKE 'ingredient%' OR name LIKE 'market%') ORDER BY name")
tables = [t[0] for t in cursor.fetchall()]
if len(tables) == 8:
    print('SUCCESS:8')
else:
    print(f'PARTIAL:{len(tables)}')
conn.close()
"@
    
    $verifyResult = python -c $verifyScript 2>&1
    if ($verifyResult -match "SUCCESS:8") {
        Write-Host "  ✓ All 8 Crown Safe tables present" -ForegroundColor Green
    }
    elseif ($verifyResult -match "PARTIAL:(\d+)") {
        Write-Host "  ⚠ Only $($Matches[1])/8 Crown Safe tables found" -ForegroundColor Yellow
    }
    else {
        Write-Host "  ℹ Could not verify tables (may need to check manually)" -ForegroundColor Gray
    }
}

# Step 4: Display manual fix instructions
Write-Host ""
Write-Host "[Step 4/4] Manual fix required: fix_upc_data function" -ForegroundColor Yellow
Write-Host ""
Write-Host "  ⚠ CRITICAL: The fix_upc_data function still has RecallDB queries" -ForegroundColor Red
Write-Host "  This will cause NameError when the server starts!" -ForegroundColor Red
Write-Host ""
Write-Host "  Manual fix steps (takes 3 minutes):" -ForegroundColor Yellow
Write-Host "  ======================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Open VS Code: code '$workDir\api\main_crownsafe.py'" -ForegroundColor White
Write-Host ""
Write-Host "  2. Press Ctrl+G and go to line 3845" -ForegroundColor White
Write-Host ""
Write-Host "  3. Select from line 3845 to line 3930 (entire function body)" -ForegroundColor White
Write-Host "     - Click at line 3845" -ForegroundColor Gray
Write-Host "     - Hold Shift and click at line 3930" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Replace selected text with:" -ForegroundColor White
Write-Host ""
Write-Host "    # REMOVED FOR CROWN SAFE: RecallDB no longer exists" -ForegroundColor Cyan
Write-Host "    logger.info('fix_upc_data: Disabled (RecallDB removed)')" -ForegroundColor Cyan
Write-Host "    " -ForegroundColor Cyan
Write-Host "    return {" -ForegroundColor Cyan
Write-Host "        'status': 'disabled'," -ForegroundColor Cyan
Write-Host "        'message': 'Crown Safe migration - RecallDB removed'," -ForegroundColor Cyan
Write-Host "        'enhanced_recalls': 0," -ForegroundColor Cyan
Write-Host "        'total_with_upc': 0," -ForegroundColor Cyan
Write-Host "        'total_recalls': 0," -ForegroundColor Cyan
Write-Host "        'upc_coverage_percent': 0," -ForegroundColor Cyan
Write-Host "        'agencies_optimized': 39," -ForegroundColor Cyan
Write-Host "        'impact': 'Feature disabled'," -ForegroundColor Cyan
Write-Host "    }" -ForegroundColor Cyan
Write-Host ""
Write-Host "  5. Save the file (Ctrl+S)" -ForegroundColor White
Write-Host ""
Write-Host "  6. Verify no more RecallDB queries:" -ForegroundColor White
Write-Host "     Press Ctrl+F, search for 'db.query(RecallDB)'" -ForegroundColor Gray
Write-Host "     Should find 0 results!" -ForegroundColor Gray
Write-Host ""

# Summary
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host ""
if ($migrationSuccess) {
    Write-Host "  ✓ Database migration: COMPLETE" -ForegroundColor Green
}
else {
    Write-Host "  ⚠ Database migration: NEEDS RETRY" -ForegroundColor Yellow
}
Write-Host "  ⚠ fix_upc_data function: NEEDS MANUAL FIX (3 min)" -ForegroundColor Yellow
Write-Host "  ℹ Router cleanup: OPTIONAL (15 min)" -ForegroundColor Gray
Write-Host ""
Write-Host "After manual fix, test server:" -ForegroundColor Yellow
Write-Host "  uvicorn api.main_crownsafe:app --reload --port 8001" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to open VS Code to main_crownsafe.py..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Open VS Code
Set-Location $workDir
code "api\main_crownsafe.py"

Write-Host ""
Write-Host "✓ VS Code opened - follow the steps above to fix fix_upc_data" -ForegroundColor Green
Write-Host ""
