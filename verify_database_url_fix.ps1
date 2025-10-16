# Verify DATABASE_URL Configuration
# Run this to check if the fix was properly applied

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  DATABASE_URL Configuration Check" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

# Get task def :185 (old)
Write-Host "[1/3] Checking OLD task definition (:185)..." -ForegroundColor Cyan
$old = aws ecs describe-task-definition --task-definition babyshield-backend-task:185 --region eu-north-1 | ConvertFrom-Json
$oldEnv = $old.taskDefinition.containerDefinitions[0].environment
$oldDbUrl = ($oldEnv | Where-Object { $_.name -eq 'DATABASE_URL' }).value

Write-Host "OLD (rev :185):" -ForegroundColor Yellow
if ($oldDbUrl -match '/([^/\?]+)(\?.*)?$') {
    $oldDb = $matches[1]
    Write-Host "  Database: $oldDb" -ForegroundColor White
}

# Get task def :186 (new)
Write-Host "`n[2/3] Checking NEW task definition (:186)..." -ForegroundColor Cyan
$new = aws ecs describe-task-definition --task-definition babyshield-backend-task:186 --region eu-north-1 | ConvertFrom-Json
$newEnv = $new.taskDefinition.containerDefinitions[0].environment
$newDbUrl = ($newEnv | Where-Object { $_.name -eq 'DATABASE_URL' }).value

Write-Host "NEW (rev :186):" -ForegroundColor Yellow
if ($newDbUrl -match '/([^/\?]+)(\?.*)?$') {
    $newDb = $matches[1]
    Write-Host "  Database: $newDb" -ForegroundColor White
}

# Compare
Write-Host "`n[3/3] Comparison:" -ForegroundColor Cyan
if ($oldDb -eq $newDb) {
    Write-Host "  ❌ NO CHANGE! Both point to: $oldDb" -ForegroundColor Red
    Write-Host "`n  PROBLEM: The DATABASE_URL was NOT updated!" -ForegroundColor Red
    Write-Host "  You need to:" -ForegroundColor Yellow
    Write-Host "    1. Go back to AWS Console" -ForegroundColor White
    Write-Host "    2. Edit task definition :186 (or create new revision)" -ForegroundColor White
    Write-Host "    3. Change DATABASE_URL from /$oldDb to /babyshield_db" -ForegroundColor White
    Write-Host "    4. Save and update service`n" -ForegroundColor White
}
else {
    Write-Host "  ✅ CHANGED!" -ForegroundColor Green
    Write-Host "    Old: $oldDb" -ForegroundColor Red
    Write-Host "    New: $newDb" -ForegroundColor Green
    
    if ($newDb -eq 'babyshield_db') {
        Write-Host "`n  ✅ Perfect! Now points to babyshield_db (correct database)" -ForegroundColor Green
        Write-Host "  Wait for service restart, then search should work.`n" -ForegroundColor Yellow
    }
    else {
        Write-Host "`n  ⚠️ Changed but to unexpected database: $newDb" -ForegroundColor Yellow
        Write-Host "  Should be: babyshield_db`n" -ForegroundColor White
    }
}

Write-Host "========================================`n" -ForegroundColor Cyan
