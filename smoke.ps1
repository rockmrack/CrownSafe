param([string]$BASE = $env:BS_BASE_URL)
if (-not $BASE -or $BASE -eq '') { $BASE = 'https://babyshield.cureviax.ai' }

$ErrorActionPreference = 'Stop'
$PASS=0;$FAIL=0

function Test-Step($name, [scriptblock]$code) {
  Write-Host "`n=== $name ===" -ForegroundColor Cyan
  try { & $code; $global:PASS++ }
  catch {
    $global:FAIL++
    Write-Host "❌ $name failed: $($_.Exception.Message)" -ForegroundColor Red
  }
}

# --- CORE ---
Test-Step 'Health' {
  $r = irm "$BASE/healthz" -TimeoutSec 20
  if ($r.status -ne 'ok') { throw "healthz status=$($r.status)" }
  $r | ConvertTo-Json -Compress | Write-Host
}

Test-Step 'Ready' {
  $r = irm "$BASE/readyz" -TimeoutSec 30
  if ($r.status -ne 'ready') { throw "readyz status=$($r.status)" }
  if (-not $r.recalls_enhanced_table.exists) { throw "recalls table missing" }
  $r | ConvertTo-Json -Compress | Write-Host
}

# --- SEARCH & PAGINATION ---
Test-Step 'Search p1 (cursor)' {
  $script:r1 = irm "$BASE/api/v1/search/advanced" -Method POST -ContentType 'application/json' `
    -Body (@{ query='toy'; limit=3 } | ConvertTo-Json -Compress) -TimeoutSec 60
  if ($r1.ok -ne $true) { throw "ok=false" }
  if (-not $r1.data.nextCursor) { throw "nextCursor missing" }
  "{0} items; nextCursor len={1}" -f $r1.data.items.Count, $r1.data.nextCursor.Length | Write-Host
}

Test-Step 'Search p2 (cursor uses nextCursor)' {
  $r2 = irm "$BASE/api/v1/search/advanced" -Method POST -ContentType 'application/json' `
    -Body (@{ query='toy'; limit=3; nextCursor=$r1.data.nextCursor } | ConvertTo-Json -Compress)
  if ($r2.data.offset -ne 3) { throw "expected offset=3 got $($r2.data.offset)" }
  "offset={0}; items={1}" -f $r2.data.offset, $r2.data.items.Count | Write-Host
}

Test-Step 'Search (multi-agency filter)' {
  $r = irm "$BASE/api/v1/search/advanced" -Method POST -ContentType 'application/json' `
    -Body (@{ query='baby'; agencies=@('CPSC','FDA','RAPEX'); limit=5 } | ConvertTo-Json -Compress)
  if ($r.ok -ne $true -or $r.data.items.Count -lt 1) { throw "no results" }
  "items={0}; total={1}" -f $r.data.items.Count, $r.data.total | Write-Host
}

Test-Step 'Search (date range)' {
  $r = irm "$BASE/api/v1/search/advanced" -Method POST -ContentType 'application/json' `
    -Body (@{ query='product'; date_from='2023-01-01'; date_to='2024-12-31'; limit=3 } | ConvertTo-Json -Compress)
  if ($r.ok -ne $true) { throw "ok=false" }
  "items={0}; total={1}" -f $r.data.items.Count, $r.data.total | Write-Host
}

Test-Step 'Search (large offset => hasMore=false)' {
  $r = irm "$BASE/api/v1/search/advanced" -Method POST -ContentType 'application/json' `
    -Body (@{ query='toy'; limit=3; offset=999999 } | ConvertTo-Json -Compress)
  if ($r.data.hasMore -ne $false) { throw "expected hasMore=false" }
  "hasMore={0}; items={1}" -f $r.data.hasMore, $r.data.items.Count | Write-Host
}

Test-Step 'Invalid cursor gracefully resets' {
  $r = irm "$BASE/api/v1/search/advanced" -Method POST -ContentType 'application/json' `
    -Body (@{ query='toy'; limit=3; nextCursor='bogus' } | ConvertTo-Json -Compress)
  if ($r.data.offset -ne 0 -or -not $r.data.nextCursor) { throw "did not reset to offset=0" }
  "offset={0}; nextCursor? {1}" -f $r.data.offset, ([bool]$r.data.nextCursor) | Write-Host
}

# --- RECALLS ---
Test-Step 'Recalls list (paging)' {
  $script:rec = irm "$BASE/api/v1/recalls?limit=5&offset=5"
  if ($rec.success -ne $true -or $rec.data.items.Count -ne 5) { throw "bad recalls page" }
  "items={0}; total={1}" -f $rec.data.items.Count, $rec.data.total | Write-Host
}

Test-Step 'Recalls stats' {
  $r = irm "$BASE/api/v1/recalls/stats"
  if ($r.success -ne $true -or $r.data.total_recalls -lt 1) { throw "stats empty" }
  "total_recalls={0}; recent_30d={1}" -f $r.data.total_recalls, $r.data.recent_recalls_30_days | Write-Host
}

Test-Step 'Recall detail (known good id)' {
  $rid = 'RAPEX-A12/0922/18'
  $r = irm "$BASE/api/v1/recall/$rid"
  if ($r.ok -ne $true) { throw "ok=false" }
  "id={0}; hazard={1}" -f $r.data.id, $r.data.hazard | Write-Host
}

# --- MOBILE / BARCODE / RISK ---
Test-Step 'Mobile instant-check' {
  $raw = curl.exe -sk "$BASE/api/v1/mobile/instant-check/012993441012?user_id=1"
  if (-not $raw) { throw "no body" }
  $j = $raw | ConvertFrom-Json
  if (-not $j.safe) { throw "safe=false" }
  $raw | Write-Host
}

Test-Step 'Barcode scan' {
  $r = irm "$BASE/api/v1/scan/barcode" -Method POST -ContentType 'application/json' `
    -Body (@{ barcode_data='012993441012' } | ConvertTo-Json -Compress)
  if ($r.success -ne $true) { throw "success=false" }
  "trace_id={0}; results={1}" -f $r.data.trace_id, $r.data.scan_results.Count | Write-Host
}

Test-Step 'Risk assess (barcode, query params)' {
  $r = irm "$BASE/api/v1/risk-assessment/assess/barcode?barcode=012993441012&product_type=cosmetic&age_group=infant&user_id=1" -Method POST
  if (-not $r.assessment_id) { throw "no assessment_id" }
  "risk_level={0}; score={1}" -f $r.risk_level, $r.risk_score | Write-Host
}

Test-Step 'Risk assess (product)' {
  $r = irm "$BASE/api/v1/risk-assessment/assess" -Method POST -ContentType 'application/json' `
    -Body (@{ user_id=1; product_name='Baby Toy'; product_type='cosmetic'; age_group='infant' } | ConvertTo-Json -Compress)
  if (-not $r.assessment_id) { throw "no assessment_id" }
  "risk_level={0}; score={1}" -f $r.risk_level, $r.risk_score | Write-Host
}

Test-Step 'Visual search' {
  $r = irm "$BASE/api/v1/visual/search" -Method POST -ContentType 'application/json' `
    -Body (@{ user_id=1; image_url='https://example.com/test.jpg' } | ConvertTo-Json -Compress)
  if ($r.success -ne $true -or $r.data.status -ne 'completed') { throw "visual search failed" }
  "confidence={0}" -f $r.data.confidence_score | Write-Host
}

# --- SUPPLEMENTAL ---
Test-Step 'Supplemental: cosmetic' {
  $r = irm "$BASE/api/v1/supplemental/cosmetic-data/shampoo"
  if ($r.success -ne $true) { throw "cosmetic-data failed" }
  "score={0}" -f $r.data.overall_safety_score | Write-Host
}

Test-Step 'Supplemental: chemical' {
  $r = irm "$BASE/api/v1/supplemental/chemical-data/benzene"
  if ($r.success -ne $true) { throw "chemical-data failed" }
  "score={0}" -f $r.data.overall_safety_score | Write-Host
}

Test-Step 'Supplemental: safety-report' {
  $r = irm "$BASE/api/v1/supplemental/safety-report" -Method POST -ContentType 'application/json' `
    -Body (@{ product_identifier='012993441012'; product_name='Any'; product_type='cosmetic' } | ConvertTo-Json -Compress)
  if ($r.success -ne $true) { throw "safety-report failed" }
  "score={0}" -f $r.data.overall_safety_score | Write-Host
}

# --- SECURITY / HEADERS / ARTIFACTS ---
Test-Step 'Block .git (security)' {
  try {
    iwr "$BASE/.git/config" -Method GET -TimeoutSec 15 | Out-Null
    throw "endpoint unexpectedly accessible"
  } catch {
    $code = $_.Exception.Response.StatusCode.value__
    if ($code -in 403,404) { "blocked ($($code))" | Write-Host } else { throw "unexpected code $code" }
  }
}

Test-Step 'QR code generation (download)' {
  $out = Join-Path $env:TEMP "qr_smoke.png"
  & curl.exe -sk -o "$out" "$BASE/api/v1/scan/generate-qr" | Out-Null
  if (-not (Test-Path $out)) { throw "file not written" }
  $len = (Get-Item $out).Length
  if ($len -le 0) { throw "empty file" }
  "saved $out ($len bytes)" | Write-Host
  # optionally: Remove-Item $out -Force
}

# --- SUMMARY ---
Write-Host "`n=== Summary ===" -ForegroundColor Yellow
Write-Host ("Passed: {0}" -f $PASS) -ForegroundColor Green
Write-Host ("Failed: {0}" -f $FAIL) -ForegroundColor Red
if ($env:CI) { exit ([int]($FAIL -gt 0)) } else { Write-Host "(Interactive run — not exiting)"; }
