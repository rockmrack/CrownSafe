# Crown Safe - Remove BabyShield-Specific Agents
# Date: October 26, 2025

Write-Host ""
Write-Host "CROWN SAFE - AGENT CLEANUP" -ForegroundColor Cyan
Write-Host ""

$agentsToRemove = @(
    "agents\research\drugbank_agent",
    "agents\research\guideline_agent",
    "agents\research\patient_data_agent",
    "agents\research\policy_analysis_agent",
    "agents\research\clinical_trials_agent",
    "agents\research\drug_safety_agent",
    "agents\research\patient_stratification_agent",
    "agents\governance\coppa_compliance_agent",
    "agents\governance\childrenscode_compliance_agent",
    "agents\premium\allergy_sensitivity_agent",
    "agents\premium\pregnancy_product_safety_agent"
)

Write-Host "AGENTS TO REMOVE (11 total):" -ForegroundColor Yellow
foreach ($agent in $agentsToRemove) {
    Write-Host "  - $agent" -ForegroundColor Red
}
Write-Host ""

$confirmation = Read-Host "Continue? (yes/no)"
if ($confirmation -ne "yes") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
$removedCount = 0
$skippedCount = 0

foreach ($agentPath in $agentsToRemove) {
    $fullPath = Join-Path (Get-Location) $agentPath
    
    if (Test-Path $fullPath) {
        Write-Host "Removing: $agentPath" -ForegroundColor Yellow
        Remove-Item -Path $fullPath -Recurse -Force
        Write-Host "  Done" -ForegroundColor Green
        $removedCount++
    }
    else {
        Write-Host "Skipping: $agentPath (not found)" -ForegroundColor Gray
        $skippedCount++
    }
}

Write-Host ""
Write-Host "SUMMARY:" -ForegroundColor Cyan
Write-Host "Removed: $removedCount" -ForegroundColor Green
Write-Host "Skipped: $skippedCount" -ForegroundColor Gray
Write-Host ""
