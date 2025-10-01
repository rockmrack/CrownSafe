# scripts/smoke_account_deletion.ps1
# Smoke test: account deletion flow using token from CI

[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$BASE,
  [Parameter(Mandatory = $true)][string]$TOKEN_FRESH
)

$ErrorActionPreference = 'Stop'
Write-Host "Smoke(Account Deletion) → $BASE"

# 1) Health check (use GET, not HEAD)
try {
  $health = Invoke-RestMethod -Uri "$BASE/readyz" -Method Get -ErrorAction Stop
  Write-Host "readyz OK"
} catch {
  throw "Health check failed: $($_.Exception.Message)"
}

# 2) Delete current account (Bearer token)
$headers = @{ Authorization = "Bearer $TOKEN_FRESH" }
try {
  $resp = Invoke-WebRequest -Uri "$BASE/api/v1/account" -Method Delete -Headers $headers -ErrorAction Stop
  $code = [int]$resp.StatusCode
  if ($code -ne 200 -and $code -ne 204) {
    throw "Unexpected status for DELETE /api/v1/account: $code"
  }
  Write-Host "DELETE /api/v1/account → $code"
} catch {
  throw "Account delete failed: $($_.Exception.Message)"
}

# 3) Verify token no longer works (should get 401/403)
$stillValid = $true
try {
  Invoke-RestMethod -Uri "$BASE/api/v1/auth/me" -Method Get -Headers $headers -ErrorAction Stop | Out-Null
  $stillValid = $true
} catch {
  $stillValid = $false
  Write-Host "auth/me rejected after deletion (expected)."
}

if ($stillValid) { throw "Token still valid after deletion (expected failure)." }

Write-Host "Smoke(Account Deletion) PASSED."
