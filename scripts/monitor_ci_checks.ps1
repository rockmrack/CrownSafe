#!/usr/bin/env pwsh
# CI Check Monitoring Script
# Monitors GitHub Actions workflow status for the current branch

param(
    [string]$Branch = "main",
    [string]$Owner = "BabyShield",
    [string]$Repo = "babyshield-backend",
    [int]$RefreshInterval = 30,  # seconds
    [switch]$Once
)

$ErrorActionPreference = "Stop"

# Build authenticated headers for GitHub API
function Get-GitHubHeaders {
    $headers = @{
        "Accept" = "application/vnd.github+json"
        "User-Agent" = "PowerShell"
        "X-GitHub-Api-Version" = "2022-11-28"
    }
    
    # Try to get GitHub token from environment
    $token = $env:GITHUB_TOKEN
    if (-not $token) {
        $token = $env:GH_TOKEN
    }
    
    if ($token) {
        $headers["Authorization"] = "Bearer $token"
    }
    
    return $headers
}

function Get-WorkflowRuns {
    param(
        [string]$Owner,
        [string]$Repo,
        [string]$Branch
    )
    
    try {
        $url = "https://api.github.com/repos/$Owner/$Repo/actions/runs?branch=$Branch&per_page=10"
        $headers = Get-GitHubHeaders
        $response = Invoke-RestMethod -Uri $url -Method Get -Headers $headers
        
        return $response.workflow_runs
    }
    catch {
        Write-Host "Error fetching workflow runs: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

function Show-Status {
    param(
        [Parameter(Mandatory=$true)]
        $Runs,
        [Parameter(Mandatory=$true)]
        [string]$Owner,
        [Parameter(Mandatory=$true)]
        [string]$Repo,
        [Parameter(Mandatory=$true)]
        [string]$Branch
    )
    
    Clear-Host
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "GitHub CI Status Monitor" -ForegroundColor Cyan
    Write-Host "Repository: $Owner/$Repo" -ForegroundColor Cyan
    Write-Host "Branch: $Branch" -ForegroundColor Cyan
    Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host ""
    
    if ($null -eq $Runs -or $Runs.Count -eq 0) {
        Write-Host "No workflow runs found for branch: $Branch" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "This might mean:" -ForegroundColor Yellow
        Write-Host "  1. No commits on this branch yet" -ForegroundColor Gray
        Write-Host "  2. No workflows configured" -ForegroundColor Gray
        Write-Host "  3. Workflows haven't started yet" -ForegroundColor Gray
        return
    }
    
    $latestRuns = $Runs | Select-Object -First 5
    
    foreach ($run in $latestRuns) {
        $statusColor = switch ($run.status) {
            "completed" {
                switch ($run.conclusion) {
                    "success" { "Green" }
                    "failure" { "Red" }
                    "cancelled" { "Yellow" }
                    default { "Gray" }
                }
            }
            "in_progress" { "Cyan" }
            "queued" { "Yellow" }
            default { "Gray" }
        }
        
        $statusIcon = switch ($run.status) {
            "completed" {
                switch ($run.conclusion) {
                    "success" { "[PASS]" }
                    "failure" { "[FAIL]" }
                    "cancelled" { "[SKIP]" }
                    default { "[DONE]" }
                }
            }
            "in_progress" { "[RUN ]" }
            "queued" { "[WAIT]" }
            default { "[????]" }
        }
        
        Write-Host "$statusIcon " -NoNewline -ForegroundColor $statusColor
        Write-Host "$($run.name)" -ForegroundColor White
        Write-Host "       SHA: $($run.head_sha.Substring(0,7))" -ForegroundColor Gray
        Write-Host "       Status: $($run.status)" -NoNewline -ForegroundColor Gray
        if ($run.conclusion) {
            Write-Host " / $($run.conclusion)" -ForegroundColor $statusColor
        } else {
            Write-Host ""
        }
        Write-Host "       Started: $($run.created_at)" -ForegroundColor Gray
        Write-Host "       URL: $($run.html_url)" -ForegroundColor Blue
        Write-Host ""
    }
    
    # Summary
    $total = $latestRuns.Count
    $success = ($latestRuns | Where-Object { $_.conclusion -eq "success" }).Count
    $failed = ($latestRuns | Where-Object { $_.conclusion -eq "failure" }).Count
    $inProgress = ($latestRuns | Where-Object { $_.status -eq "in_progress" }).Count
    $queued = ($latestRuns | Where-Object { $_.status -eq "queued" }).Count
    
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Summary (last $total runs):" -ForegroundColor White
    Write-Host "  Success: $success" -ForegroundColor Green
    Write-Host "  Failed: $failed" -ForegroundColor Red
    Write-Host "  In Progress: $inProgress" -ForegroundColor Cyan
    Write-Host "  Queued: $queued" -ForegroundColor Yellow
    Write-Host "======================================" -ForegroundColor Cyan
    
    # Check if all latest runs are successful
    if ($success -eq $total -and $total -gt 0 -and $inProgress -eq 0 -and $queued -eq 0) {
        Write-Host ""
        Write-Host "ALL CHECKS PASSED! Ready for merge/deployment." -ForegroundColor Green
        Write-Host ""
    } elseif ($failed -gt 0) {
        Write-Host ""
        Write-Host "SOME CHECKS FAILED! Review failures before deploying." -ForegroundColor Red
        Write-Host ""
    } elseif ($inProgress -gt 0 -or $queued -gt 0) {
        Write-Host ""
        Write-Host "Checks are running... waiting for completion." -ForegroundColor Yellow
        Write-Host ""
    }
}

# Main loop
Write-Host "Starting CI monitor for $Owner/$Repo (branch: $Branch)..." -ForegroundColor Cyan
Write-Host ""

# Check for GitHub token
if (-not $env:GITHUB_TOKEN -and -not $env:GH_TOKEN) {
    Write-Host "Warning: No GITHUB_TOKEN or GH_TOKEN found in environment." -ForegroundColor Yellow
    Write-Host "         API requests will be subject to low rate limits." -ForegroundColor Yellow
    Write-Host "         For private repos, authentication is required." -ForegroundColor Yellow
    Write-Host ""
}

do {
    $runs = Get-WorkflowRuns -Owner $Owner -Repo $Repo -Branch $Branch
    Show-Status -Runs $runs -Owner $Owner -Repo $Repo -Branch $Branch
    
    if (-not $Once) {
        Write-Host "Press Ctrl+C to exit. Refreshing in $RefreshInterval seconds..." -ForegroundColor Gray
        Start-Sleep -Seconds $RefreshInterval
    }
} while (-not $Once)
