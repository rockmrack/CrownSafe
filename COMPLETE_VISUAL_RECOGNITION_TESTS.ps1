param()
$ErrorActionPreference='Stop'
$Base="https://babyshield.cureviax.ai"
function OK($m){Write-Host "[OK]  $m" -ForegroundColor Green}
function FAIL($m){Write-Host "[FAIL] $m" -ForegroundColor Red}
$allOk=$true

# 1) System health
try{ $r=Invoke-WebRequest -Uri "$Base/healthz" -UseBasicParsing -TimeoutSec 20; if($r.StatusCode -eq 200){OK "healthz"}else{FAIL "healthz HTTP $($r.StatusCode)";$allOk=$false} }catch{FAIL "healthz $_";$allOk=$false}
try{ $obj=Invoke-RestMethod -Uri "$Base/readyz" -TimeoutSec 20; if($obj.status -eq "ready" -and $obj.database -eq "connected"){OK "readyz"}else{FAIL "readyz bad payload";$allOk=$false} }catch{FAIL "readyz $_";$allOk=$false}
Write-Host "[SKIP] openapi lookup/barcode not required" -ForegroundColor Yellow

# 2) Recalls endpoints
try{ $rec=Invoke-RestMethod -Uri "$Base/api/v1/recalls?limit=3" -TimeoutSec 30; if($rec -and $rec.Count -ge 1){OK "recalls list"}else{FAIL "recalls list empty";$allOk=$false} }catch{FAIL "recalls list $_";$allOk=$false}
try{ $body=@{query="pacifier";limit=3}|ConvertTo-Json -Compress; $adv=Invoke-RestMethod -Uri "$Base/api/v1/search/advanced" -Method POST -ContentType "application/json" -Body $body -TimeoutSec 45; if($adv.success -or $adv.ok -or $adv.data.items.Count -ge 1){OK "advanced search"}else{FAIL "advanced search empty";$allOk=$false} }catch{FAIL "advanced search $_";$allOk=$false}

# 3) Barcode lookup
try{ $lk=Invoke-RestMethod -Uri "$Base/api/v1/lookup/barcode?code=012914632109" -TimeoutSec 30; if($lk.ok -and $lk.data.items.Count -ge 1){OK "lookup/barcode 012914632109"}else{FAIL "lookup/barcode no items";$allOk=$false} }catch{FAIL "lookup/barcode $_";$allOk=$false}

# 4) Visual search (image_url)
try{ $u='https://images.unsplash.com/photo-1585386959984-a4155223168f?auto=format&fit=crop&w=800&q=60'; $b=@{image_url=$u}|ConvertTo-Json -Compress; $resp=Invoke-WebRequest -Uri "$Base/api/v1/visual/search" -Method POST -ContentType "application/json" -Body $b -TimeoutSec 45 -UseBasicParsing; if($resp.StatusCode -eq 200){ $o=$resp.Content|ConvertFrom-Json; if(-not($o.error -is [string] -and $o.error -match "not configured")){OK "visual/search"} else {FAIL "visual/search key not configured";$allOk=$false} } else {FAIL "visual/search HTTP $($resp.StatusCode)";$allOk=$false} }catch{FAIL "visual/search $_";$allOk=$false}

# 5) Advanced visual recognize (multipart; low threshold)
try{
  $tmp=Join-Path $env:TEMP 'vr_full.jpg'
  Invoke-WebRequest -UseBasicParsing -OutFile $tmp -Uri 'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=1000&q=80'
  Add-Type -AssemblyName System.Net.Http
  $hc=[System.Net.Http.HttpClient]::new()
  $mp=[System.Net.Http.MultipartFormDataContent]::new()
  $fs=[System.IO.File]::OpenRead($tmp)
  $sc=[System.Net.Http.StreamContent]::new($fs)
  $sc.Headers.ContentType=[System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('image/jpeg')
  $mp.Add($sc,'image','vr_full.jpg')
  $uri="$Base/api/v1/advanced/visual/recognize?user_id=1&check_for_defects=true&confidence_threshold=0.2"
  $r=$hc.PostAsync($uri,$mp).Result
  $code=[int]$r.StatusCode
  $txt=$r.Content.ReadAsStringAsync().Result
  $fs.Dispose(); $hc.Dispose()
  if($code -ne 200){ FAIL "advanced/visual/recognize HTTP $code"; $allOk=$false }
  else{
    $o=$null; try{$o=$txt|ConvertFrom-Json}catch{}
    if($o -and $o.status -in @('ok','low_confidence')){ OK "advanced/visual/recognize ($($o.status))" } else { FAIL "advanced/visual/recognize unexpected body"; $allOk=$false }
  }
}catch{ FAIL "advanced/visual/recognize $_"; $allOk=$false }

# 6) Concurrency sanity (5x healthz)
try{
  $jobs=1..5 | % { Start-Job -ScriptBlock { param($u) (Invoke-WebRequest -Uri ($u+'/healthz') -UseBasicParsing -TimeoutSec 15).StatusCode } -ArgumentList $Base }
  Wait-Job -Job $jobs | Out-Null
  $codes= $jobs | Receive-Job
  $jobs | Remove-Job | Out-Null
  if(($codes | Where-Object {$_ -ne 200}).Count -eq 0){ OK "concurrency healthz x5" } else { FAIL "concurrency healthz not all 200"; $allOk=$false }
}catch{ FAIL "concurrency $_"; $allOk=$false }

if($allOk){Write-Host "ALL TESTS PASSED" -ForegroundColor Green; exit 0} else {Write-Host "ONE OR MORE TESTS FAILED" -ForegroundColor Yellow; exit 1}