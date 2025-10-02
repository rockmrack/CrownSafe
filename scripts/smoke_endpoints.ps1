# scripts/smoke_endpoints.ps1
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$BASE,
  [string]$Csv = "smoke/endpoints.smoke.csv",
  [string]$Email = $env:SMOKE_TEST_EMAIL,
  [string]$Password = $env:SMOKE_TEST_PASSWORD
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $Csv)) { throw "CSV not found: $Csv" }
$rows = Import-Csv $Csv

# Login once if any row needs auth
$needsAuth = $rows | Where-Object { $_.AUTH -match '^(1|true|yes)$' }
$token = $null
if ($needsAuth) {
  Write-Host "Authenticating..."
  # Use hashtable for automatic URL encoding of special characters
  $formData = @{
    username = $Email
    password = $Password
    grant_type = 'password'
  }
  $login = Invoke-RestMethod -Uri "$BASE/api/v1/auth/token" -Method Post -ContentType 'application/x-www-form-urlencoded' -Body $formData
  $token = $login.access_token
  if (-not $token) { $token = $login.token }
  if (-not $token -and $login.data) { $token = $login.data.access_token }
  if (-not $token) { throw "No token in response: $($login | ConvertTo-Json -Compress)" }
  Write-Host "Authentication successful"
}

Write-Host "`nRunning smoke tests against: $BASE"
Write-Host "Testing $($rows.Count) endpoints...`n"

$results = foreach ($r in $rows) {
  $method = $r.METHOD.ToUpper()
  $url    = "$BASE$($r.PATH)"
  $expect = [int]$r.EXPECT
  $body   = $r.BODY
  $auth   = $r.AUTH -match '^(1|true|yes)$'
  $hdrs   = @{ Accept = 'application/json' }
  if ($auth -and $token) { $hdrs['Authorization'] = "Bearer $token" }

  Write-Host "Testing: $method $($r.PATH) (expect $expect)" -NoNewline

  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  try {
    if ($body -and $method -in 'POST','PUT','PATCH') {
      $resp = Invoke-WebRequest -Uri $url -Method $method -Headers $hdrs -ContentType 'application/json' -Body $body -ErrorAction Stop
    } else {
      $resp = Invoke-WebRequest -Uri $url -Method $method -Headers $hdrs -ErrorAction Stop
    }
    $code = [int]$resp.StatusCode; $err = ''
  } catch {
    $code = try { [int]$_.Exception.Response.StatusCode.value__ } catch { -1 }
    $err  = $_.Exception.Message
  }
  $sw.Stop()

  $ok = $code -eq $expect
  if ($ok) {
    Write-Host " OK ($($sw.ElapsedMilliseconds)ms)" -ForegroundColor Green
  } else {
    Write-Host " FAIL (got $code, $($sw.ElapsedMilliseconds)ms)" -ForegroundColor Red
    if ($err) { Write-Host "  Error: $err" -ForegroundColor Red }
  }

  [pscustomobject]@{
    Method = $method; Path = $r.PATH; Expect = $expect; Got = $code; Ok = $ok
    Ms = [int]$sw.ElapsedMilliseconds; Error = $err
  }
}

Write-Host "`n=== Smoke Test Results ==="
$results | Format-Table -Auto

# Create smoke directory if it doesn't exist
$smokeDir = Split-Path $Csv -Parent
if ($smokeDir -and -not (Test-Path $smokeDir)) {
  New-Item -ItemType Directory -Path $smokeDir -Force | Out-Null
}

# Save results
$resultPath = Join-Path (Split-Path $Csv -Parent) "endpoints_smoke_results.csv"
$results | Export-Csv $resultPath -NoTypeInformation
Write-Host "Results saved to: $resultPath"

# Summary
$passed = ($results | Where-Object { $_.Ok }).Count
$failed = ($results | Where-Object { -not $_.Ok }).Count
$total = $results.Count

Write-Host "`nSummary: $passed/$total passed, $failed failed"

if ($failed -gt 0) {
  Write-Host "SMOKE TEST FAILED" -ForegroundColor Red
  exit 1
}

Write-Host "ALL SMOKE TESTS PASSED" -ForegroundColor Green

