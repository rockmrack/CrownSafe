# Remove all baby/recall-related code from Crown Safe
# Run this script to clean up legacy BabyShield code

Write-Host "Crown Safe Code Cleanup" -ForegroundColor Cyan
Write-Host "Removing all baby product recall-related files..." -ForegroundColor Yellow
Write-Host ""

# API endpoint files to remove
$apiFiles = @(
    "api\recall_detail_endpoints.py",
    "api\recall_alert_system.py",
    "api\recalls_endpoints.py",
    "api\baby_features_endpoints.py",
    "api\premium_features_endpoints.py"
)

# Scripts to remove
$scriptFiles = @(
    "scripts\ingest_recalls.py",
    "scripts\seed_recall_db.py",
    "scripts\test_recall_connectors.py",
    "scripts\test_recall_data_agent.py",
    "scripts\test_recall_connectors_live.py",
    "scripts\test_live_recall_scenario.py",
    "scripts\test_baby_features_api.py"
)

# Root level recall scripts
$rootScripts = @(
    "verify_production_recalls.py",
    "test_recall_connectors_quick.py",
    "test_recall_agent_simple.py",
    "test_recall_agent_full.py",
    "find_recalls.py",
    "check_recalls.py",
    "check_uk_recalls_azure.py"
)

# Worker files
$workerFiles = @(
    "workers\recall_tasks.py"
)

# Database model files
$dbFiles = @(
    "core_infra\enhanced_database_schema.py",
    "db\data_models\recall.py"
)

# Documentation files
$docFiles = @(
    "BABY_CODE_REMOVAL_PLAN.md"
)

# Migration files (keep but document they're legacy)
$migrationFiles = @(
    "db\migrations\versions\2024_08_22_0100_001_create_recalls_enhanced_table.py"
)

function Remove-FilesSafely {
    param([string[]]$files, [string]$category)
    
    Write-Host "Removing $category..." -ForegroundColor Green
    
    foreach ($file in $files) {
        if (Test-Path $file) {
            try {
                Remove-Item $file -Force
                Write-Host "  ✓ Deleted: $file" -ForegroundColor DarkGreen
            }
            catch {
                Write-Host "  ✗ Failed to delete: $file (may be open)" -ForegroundColor Red
                Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor DarkRed
            }
        }
        else {
            Write-Host "  - Not found: $file" -ForegroundColor Gray
        }
    }
    Write-Host ""
}

# Execute cleanup
Remove-FilesSafely -files $apiFiles -category "API Endpoints"
Remove-FilesSafely -files $scriptFiles -category "Scripts"
Remove-FilesSafely -files $rootScripts -category "Root Scripts"
Remove-FilesSafely -files $workerFiles -category "Worker Tasks"
Remove-FilesSafely -files $dbFiles -category "Database Models"
Remove-FilesSafely -files $docFiles -category "Documentation"

Write-Host "Migration files (marked as legacy, not deleted):" -ForegroundColor Yellow
foreach ($file in $migrationFiles) {
    if (Test-Path $file) {
        Write-Host "  - $file" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Cleanup complete!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Review core_infra\database.py to remove RecallDB models"
Write-Host "  2. Clean api\main_crownsafe.py to remove recall imports"
Write-Host "  3. Run tests to verify no broken imports"
