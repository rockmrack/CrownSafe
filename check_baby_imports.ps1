# Remove baby-specific agent imports from main_crownsafe.py
# Lines to comment out:
# - Lines 2385-2416: Pregnancy safety check
# - Lines 2418-2449: Allergy sensitivity check  
# - Lines 2451-2491: Alternatives agent

# NOTE: Since Crown Safe is for hair products (not baby products),
# these pregnancy/allergy/alternatives features don't apply.

Write-Host "====================================================================="
Write-Host "  COMMENT OUT BABY-SPECIFIC AGENT IMPORTS"
Write-Host "====================================================================="
Write-Host ""

$file = "api\main_crownsafe.py"
$content = Get-Content $file -Raw

# Check if sections exist
if ($content -match "PregnancyProductSafetyAgentLogic") {
    Write-Host "Found pregnancy agent import - needs manual removal" -ForegroundColor Yellow
}

if ($content -match "AllergySensitivityAgentLogic") {
    Write-Host "Found allergy agent import - needs manual removal" -ForegroundColor Yellow
}

if ($content -match "AlternativesAgentLogic") {
    Write-Host "Found alternatives agent import - needs manual removal" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "ACTION REQUIRED:" -ForegroundColor Cyan
Write-Host "Due to encoding issues in the file, these sections must be" -ForegroundColor White
Write-Host "manually commented out or removed in your editor:" -ForegroundColor White
Write-Host ""
Write-Host "1. Lines 2385-2416: Pregnancy safety check" -ForegroundColor White
Write-Host "2. Lines 2418-2449: Allergy sensitivity check" -ForegroundColor White
Write-Host "3. Lines 2451-2491: Alternatives agent" -ForegroundColor White
Write-Host ""
Write-Host "These features are baby-specific and don't apply to Crown Safe" -ForegroundColor Yellow
Write-Host "(hair product safety for 3C-4C hair types)" -ForegroundColor Yellow
Write-Host ""
