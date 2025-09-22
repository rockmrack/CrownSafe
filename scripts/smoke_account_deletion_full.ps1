param(
  [string]$BASE = "https://babyshield.cureviax.ai",
  [string]$EMAIL,
  [string]$PASSWORD,
  [string]$PUSH_TOKEN = "ps-test-token-" + ([guid]::NewGuid().ToString("N"))
)

if (-not $EMAIL -or -not $PASSWORD) { Write-Error "Provide -EMAIL and -PASSWORD (test account)."; exit 1 }

function Head($url){ (Invoke-WebRequest -Uri $url -Method Get -UseBasicParsing -ErrorAction Stop).StatusCode }

function FormPost($url, $pairs) {
  $body = ($pairs.GetEnumerator() | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join "&"
  return Invoke-RestMethod -Uri $url -Method Post -ContentType 'application/x-www-form-urlencoded' -Body $body -ErrorAction Stop
}

# 0) Public pages
if ((Head "$BASE/legal/account-deletion") -ne 200) { Write-Error "/legal/account-deletion not 200"; exit 2 }
$r0 = Invoke-WebRequest -Uri "$BASE/legal/data-deletion" -MaximumRedirection 0 -ErrorAction SilentlyContinue
if ($r0.StatusCode -ne 301 -or -not $r0.Headers.Location.EndsWith("/legal/account-deletion")) { Write-Error "legacy /legal/data-deletion not 301?/legal/account-deletion"; exit 3 }

# 1) Login (form-urlencoded to /auth/token)
$login = FormPost "$BASE/api/v1/auth/token" @{ username=$EMAIL; password=$PASSWORD }
$TOKEN = $login.access_token
if (-not $TOKEN) { Write-Error "No access_token from /api/v1/auth/token"; exit 4 }

# 2) Unregister device (idempotent; ignore non-2xx)
try {
  Invoke-RestMethod -Uri "$BASE/api/v1/devices/unregister" -Method Post -ContentType 'application/json' `
    -Headers @{ Authorization = "Bearer $TOKEN" } -Body (@{ token=$PUSH_TOKEN } | ConvertTo-Json -Compress) | Out-Null
} catch {}

# 3) Delete account (expect 204)
$r3 = Invoke-WebRequest -Uri "$BASE/api/v1/account" -Method Delete -Headers @{ Authorization="Bearer $TOKEN" } -UseBasicParsing -ErrorAction SilentlyContinue
if ($r3.StatusCode -ne 204) {
  $msg = try { ($r3.Content | ConvertFrom-Json).detail } catch { "" }
  Write-Error ("Delete failed: {0} {1}" -f $r3.StatusCode, $msg); exit 5
}

# 4) Token reuse must fail (401/403)
$r4 = Invoke-WebRequest -Uri "$BASE/api/v1/auth/me" -Headers @{ Authorization="Bearer $TOKEN" } -UseBasicParsing -ErrorAction SilentlyContinue
if ($r4.StatusCode -lt 401 -or $r4.StatusCode -gt 403) { Write-Error "Reused token not rejected (got $($r4.StatusCode))"; exit 6 }

# 5) Legacy endpoint must NOT be 2xx (send empty JSON to avoid 405)
$r5 = Invoke-WebRequest -Uri "$BASE/api/v1/user/data/delete" -Method Post -ContentType 'application/json' `
      -Body '{}' -UseBasicParsing -ErrorAction SilentlyContinue
if ($r5.StatusCode -lt 400) { Write-Error "Legacy endpoint unexpectedly OK (got $($r5.StatusCode))"; exit 7 }

Write-Host "OK: end-to-end account deletion flow passed."
exit 0
