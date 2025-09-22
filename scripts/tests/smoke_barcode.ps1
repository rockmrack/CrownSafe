param([string]$Base="https://babyshield.cureviax.ai")
$ErrorActionPreference='Stop'
$failed = $false   # <- ensure clean default

function OK($m){Write-Host "[OK]  $m" -ForegroundColor Green}
function FAIL($m){Write-Host "[FAIL] $m" -ForegroundColor Red; $script:failed=$true}

# 1) Known-good barcode (page1 + page2)
$code='012914632109'
$r1=Invoke-RestMethod -Uri "$Base/api/v1/lookup/barcode?code=$code&limit=5" -TimeoutSec 30
if($r1.ok -and $r1.data.items.Count -ge 1){ OK "lookup $code page1 items=$($r1.data.items.Count) hasMore=$($r1.data.hasMore)" } else { FAIL "lookup $code page1" }
if($r1.data.hasMore){
  $cursor=[uri]::EscapeDataString($r1.data.nextCursor)
  $r2=Invoke-RestMethod -Uri "$Base/api/v1/lookup/barcode?code=$code&limit=5&nextCursor=$cursor" -TimeoutSec 30
  if($r2.ok -and $r2.data.items.Count -ge 1){ OK "lookup $code page2 items=$($r2.data.items.Count) hasMore=$($r2.data.hasMore)" } else { FAIL "lookup $code page2" }
}

# 2) Another known barcode
$code2='818771010108'
try{
  $r=Invoke-RestMethod -Uri "$Base/api/v1/lookup/barcode?code=$code2&limit=5" -TimeoutSec 30
  if($r.ok){ OK "lookup $code2 ok=true (items=$($r.data.items.Count))" } else { FAIL "lookup $code2 ok=false" }
}catch{ FAIL "lookup $code2 exception: $($_.Exception.Message)" }

# 3) Nonexistent barcode (graceful)
$bad='0000000000000'
try{
  $r=Invoke-RestMethod -Uri "$Base/api/v1/lookup/barcode?code=$bad&limit=5" -TimeoutSec 30
  if(($r.ok -eq $true) -or ($r.ok -eq $false -and $r.message)){ OK "lookup $bad graceful" } else { FAIL "lookup $bad unexpected shape" }
}catch{ FAIL "lookup $bad exception: $($_.Exception.Message)" }

if($failed){ exit 1 } else { Write-Host "BARCODE TESTS PASSED" -ForegroundColor Green; exit 0 }