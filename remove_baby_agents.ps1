# Crown Safe - Remove BabyShield-specific agents
# These agents are for baby product recalls, not hair product safety

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "  CROWN SAFE - REMOVE BABY/RECALL-SPECIFIC AGENTS" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

$agentsToRemove = @(
    "agents\recall_data_agent",
    "agents\premium\pregnancy_product_safety_agent",
    "agents\premium\allergy_sensitivity_agent", 
    "agents\value_add\alternatives_agent",
    "agents\engagement\community_alert_agent",
    "agents\business",
    "agents\governance",
    "agents\processing",
    "agents\reporting",
    "agents\research"
)

$agentsToKeep = @(
    "agents\chat",
    "agents\command\commander_agent",
    "agents\planning\planner_agent",
    "agents\routing\router_agent",
    "agents\visual\visual_search_agent",
    "agents\ingredient_analysis_agent",
    "agents\hazard_analysis_agent",
    "agents\product_identifier_agent"
)

Write-Host "AGENTS TO KEEP (Crown Safe-relevant):" -ForegroundColor Green
foreach ($agent in $agentsToKeep) {
    if (Test-Path $agent) {
        Write-Host "  ✓ $agent" -ForegroundColor Green
    }
    else {
        Write-Host "  ⚠ $agent (not found)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "AGENTS TO REMOVE (Baby/Recall-specific):" -ForegroundColor Red
foreach ($agent in $agentsToRemove) {
    if (Test-Path $agent) {
        Write-Host "  ❌ $agent" -ForegroundColor Red
    }
    else {
        Write-Host "  ⊗ $agent (already removed)" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "Do you want to proceed with removal? (Y/N): " -NoNewline -ForegroundColor Yellow
$confirmation = Read-Host

if ($confirmation -ne 'Y' -and $confirmation -ne 'y') {
    Write-Host "Aborted by user." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Removing baby/recall-specific agents..." -ForegroundColor Cyan

$removed = 0
$notFound = 0

foreach ($agent in $agentsToRemove) {
    if (Test-Path $agent) {
        try {
            Remove-Item -Path $agent -Recurse -Force
            Write-Host "  ✓ Removed: $agent" -ForegroundColor Green
            $removed++
        }
        catch {
            Write-Host "  ✗ Failed to remove: $agent - $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    else {
        Write-Host "  ⊗ Not found: $agent" -ForegroundColor DarkGray
        $notFound++
    }
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "  CLEANUP COMPLETE" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "  Removed: $removed agents" -ForegroundColor Green
Write-Host "  Not found: $notFound agents" -ForegroundColor DarkGray
Write-Host "  Kept: $($agentsToKeep.Count) Crown Safe agents" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Update api/main_crownsafe.py to remove imports to deleted agents" -ForegroundColor White
Write-Host "2. Test Crown Safe functionality: python test_endpoints.py" -ForegroundColor White
Write-Host "3. Verify chat agent still works: python test_chat_agent.py" -ForegroundColor White
Write-Host ""
