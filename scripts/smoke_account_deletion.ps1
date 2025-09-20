param(
  [string]$BASE = "https://babyshield.cureviax.ai",
  [string]$TOKEN_FRESH = ""
)

if (-not $TOKEN_FRESH) { Write-Error "Provide -TOKEN_FRESH (valid, <5min old)."; exit 1 }

function Head($url){ (Invoke-WebRequest -Uri $url -Method Head -UseBasicParsing -ErrorAction Stop).StatusCode }

# 1) Public page exists
$code1 = Head("$BASE/legal/account-deletion")
if ($code1 -ne 200){ Write-Error "account-deletion page not 200 ($code1)"; exit 2 }

# 2) Legacy redirect
$r = Invoke-WebRequest -Uri "$BASE/legal/data-deletion" -MaximumRedirection 0 -ErrorAction SilentlyContinue
if ($r.StatusCode -ne 301 -or -not $r.Headers.Location.EndsWith("/legal/account-deletion")){
  Write-Error "legacy redirect not 301 -> /legal/account-deletion"; exit 3
}

# 3) Unauthorized delete blocked
$r3 = Invoke-WebRequest -Uri "$BASE/api/v1/account" -Method Delete -UseBasicParsing -ErrorAction SilentlyContinue
if ($r3.StatusCode -lt 401 -or $r3.StatusCode -gt 403){ Write-Error "unauth delete not 401/403"; exit 4 }

# 4) Authenticated delete returns 204
$r4 = Invoke-WebRequest -Uri "$BASE/api/v1/account" -Method Delete -Headers @{Authorization="Bearer $TOKEN_FRESH"} -UseBasicParsing -ErrorAction SilentlyContinue
if ($r4.StatusCode -ne 204){ Write-Error "auth delete not 204 ($($r4.StatusCode))"; exit 5 }

Write-Host "OK: deletion flow smoke passed."
exit 0
