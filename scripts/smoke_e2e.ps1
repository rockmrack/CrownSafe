# BabyShield backend smoke tests (PowerShell)
# Usage: ./scripts/smoke_e2e.ps1 -Base https://babyshield.cureviax.ai

param(
  [string]$Base = "http://localhost:8001"
)

Write-Host "=== BabyShield smoke tests against $Base ===" -ForegroundColor Cyan

# Helpers
function New-Email {
  $ts = (Get-Date).ToString("yyyyMMddHHmmss");
  return "smoke+$ts@ex.com"
}

function Assert-Status($resp, [int]$code, [string]$name){
  if ($resp.StatusCode -ne $code) {
    Write-Error "$name failed: expected $code got $($resp.StatusCode) body=$($resp.Content)"; exit 1
  } else { Write-Host "$name -> $code" -ForegroundColor Green }
}

try {
  # 1) Auth: register, token, me
  $email = New-Email; $password = "P@ssw0rd!"
  $reg = Invoke-WebRequest -Uri "$Base/api/v1/auth/register" -Method POST -ContentType "application/json" -Body (@{ email=$email; password=$password; confirm_password=$password } | ConvertTo-Json)
  Assert-Status $reg 200 "register"

  $login = Invoke-WebRequest -Uri "$Base/api/v1/auth/token" -Method POST -ContentType "application/x-www-form-urlencoded" -Body "username=$email&password=$password&grant_type=password"
  Assert-Status $login 200 "login"
  $access = (ConvertFrom-Json $login.Content).access_token
  $headers = @{ Authorization = "Bearer $access" }

  $me = Invoke-WebRequest -Uri "$Base/api/v1/auth/me" -Headers $headers -Method GET
  Assert-Status $me 200 "auth/me"
  $meJson = $me.Content | ConvertFrom-Json
  Write-Host ("me.id={0}" -f $meJson.id)

  # 2) Health/ready
  $health = Invoke-WebRequest -Uri "$Base/health" -Method GET
  Assert-Status $health 200 "health"
  $healthz = Invoke-WebRequest -Uri "$Base/healthz" -Method GET
  Assert-Status $healthz 200 "healthz"
  $readyz = Invoke-WebRequest -Uri "$Base/readyz" -Method GET
  Assert-Status $readyz 200 "readyz"

  # 3) Rate limiting quick probe (best-effort; skip failure)
  $rl429 = 0
  for ($i=0; $i -lt 25; $i++) {
    $r = Invoke-WebRequest -Uri "$Base/api/v1/auth/me" -Headers $headers -Method GET -ErrorAction SilentlyContinue
    if ($r.StatusCode -eq 429) { $rl429++ }
    Start-Sleep -Milliseconds 50
  }
  Write-Host ("rate-limit 429 count: {0}" -f $rl429)

  # 4) Scan QR (text)
  $qr = Invoke-WebRequest -Uri "$Base/api/v1/scan/qr" -Headers $headers -Method POST -ContentType "application/json" -Body (@{ text = "https://example.com" } | ConvertTo-Json)
  Assert-Status $qr 200 "scan/qr"

  # 5) Generate Product Safety report
  $payload = @{ 
    user_id = $meJson.id; report_type = "product_safety"; format = "pdf"; 
    product_name = "Yoto Mini Player"; barcode = "850016249012"; model_number = "YM001"; lot_or_serial = "L0T456"
  } | ConvertTo-Json
  $gen = Invoke-WebRequest -Uri "$Base/api/v1/baby/reports/generate" -Headers $headers -Method POST -ContentType "application/json" -Body $payload
  Assert-Status $gen 200 "reports/generate"
  $genJson = $gen.Content | ConvertFrom-Json
  $rid = $genJson.report_id
  $dlUrl = if ($genJson.download_url -match '^https?://') { $genJson.download_url } else { "$Base$($genJson.download_url)" }
  Write-Host ("report_id={0}" -f $rid)

  # 6) Download and validate PDF header
  $out = Join-Path $PSScriptRoot "report.pdf"
  curl.exe -s -L "$dlUrl" -o "$out" | Out-Null
  if (-not (Test-Path "$out")) { Write-Error "download failed"; exit 1 }
  $sig = (Get-Content -Encoding Byte -TotalCount 4 "$out" | ForEach-Object {[char]$_}) -join ''
  if ($sig -ne '%PDF') { Write-Error "invalid PDF header: '$sig'"; exit 1 } else { Write-Host "PDF header OK (%PDF)" -ForegroundColor Green }

  # 7) ETag/conditional GET (best-effort)
  $first = Invoke-WebRequest -Uri "$dlUrl" -Method GET -Headers @{ Range = "bytes=0-0" } -ErrorAction SilentlyContinue
  if ($first.StatusCode -in 200,206) {
    $etag = $first.Headers.ETag
    if ($etag) {
      $second = Invoke-WebRequest -Uri "$dlUrl" -Method GET -Headers @{ 'If-None-Match' = $etag } -ErrorAction SilentlyContinue
      if ($second.StatusCode -eq 304) { Write-Host "ETag 304 OK" -ForegroundColor Green }
    }
  }

  Write-Host "=== Smoke tests completed successfully ===" -ForegroundColor Green
} catch {
  Write-Error $_.Exception.Message
  exit 1
}


