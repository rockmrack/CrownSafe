# Script to migrate database by temporarily pausing OneDrive
# This works around OneDrive's file locking during SQLite writes

Write-Host "=== Crown Safe Database Migration with OneDrive Pause ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Pause OneDrive
Write-Host "[1/5] Pausing OneDrive..." -ForegroundColor Yellow
try {
    $oneDriveProcesses = Get-Process -Name "OneDrive" -ErrorAction SilentlyContinue
    if ($oneDriveProcesses) {
        foreach ($process in $oneDriveProcesses) {
            $process.Kill()
            Start-Sleep -Milliseconds 500
        }
        Write-Host "  ✓ OneDrive paused" -ForegroundColor Green
    }
    else {
        Write-Host "  ℹ OneDrive not running" -ForegroundColor Gray
    }
}
catch {
    Write-Host "  ⚠ Could not pause OneDrive: $_" -ForegroundColor Red
    Write-Host "  Continuing anyway..." -ForegroundColor Gray
}

Start-Sleep -Seconds 2

# Step 2: Verify database is accessible
Write-Host ""
Write-Host "[2/5] Verifying database access..." -ForegroundColor Yellow
$dbPath = "c:\Users\rossd\OneDrive\Documents\Crown Safe\db\babyshield_dev.db"
if (Test-Path $dbPath) {
    Write-Host "  ✓ Database found: $dbPath" -ForegroundColor Green
}
else {
    Write-Host "  ✗ Database not found!" -ForegroundColor Red
    exit 1
}

# Step 3: Run migration
Write-Host ""
Write-Host "[3/5] Running Alembic migration..." -ForegroundColor Yellow
Set-Location "c:\Users\rossd\OneDrive\Documents\Crown Safe\db"
$env:DATABASE_URL = "sqlite:///c:/Users/rossd/OneDrive/Documents/Crown Safe/db/babyshield_dev.db"

try {
    alembic upgrade head 2>&1 | ForEach-Object {
        if ($_ -match "Running upgrade") {
            Write-Host "  $_" -ForegroundColor Cyan
        }
        elseif ($_ -match "Dropped|Removed") {
            Write-Host "  $_" -ForegroundColor Magenta
        }
        elseif ($_ -match "ERROR|Error|error") {
            Write-Host "  $_" -ForegroundColor Red
        }
        else {
            Write-Host "  $_" -ForegroundColor Gray
        }
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Migration completed successfully!" -ForegroundColor Green
    }
    else {
        Write-Host "  ✗ Migration failed with exit code $LASTEXITCODE" -ForegroundColor Red
        throw "Migration failed"
    }
}
catch {
    Write-Host "  ✗ Migration error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "[5/5] Restarting OneDrive..." -ForegroundColor Yellow
    Start-Process "$env:LOCALAPPDATA\Microsoft\OneDrive\OneDrive.exe"
    exit 1
}

# Step 4: Verify Crown Safe tables
Write-Host ""
Write-Host "[4/5] Verifying Crown Safe tables..." -ForegroundColor Yellow
Set-Location "c:\Users\rossd\OneDrive\Documents\Crown Safe"
python check_db_tables.py | ForEach-Object {
    if ($_ -match "✓") {
        Write-Host "  $_" -ForegroundColor Green
    }
    elseif ($_ -match "✗") {
        Write-Host "  $_" -ForegroundColor Red
    }
    else {
        Write-Host "  $_" -ForegroundColor Gray
    }
}

# Step 5: Restart OneDrive
Write-Host ""
Write-Host "[5/5] Restarting OneDrive..." -ForegroundColor Yellow
try {
    Start-Process "$env:LOCALAPPDATA\Microsoft\OneDrive\OneDrive.exe"
    Write-Host "  ✓ OneDrive restarted" -ForegroundColor Green
}
catch {
    Write-Host "  ⚠ Could not restart OneDrive automatically" -ForegroundColor Yellow
    Write-Host "  Please restart OneDrive manually" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Migration Process Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Fix remaining fix_upc_data function (see MANUAL_FIX_FUNCTION6.md)"
Write-Host "  2. Test server startup: uvicorn api.main_crownsafe:app --reload --port 8001"
Write-Host "  3. Fix router registrations (see MANUAL_ROUTER_EDIT_INSTRUCTIONS.md)"
Write-Host ""
