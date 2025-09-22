param()
$ErrorActionPreference='Stop'
$Base="https://babyshield.cureviax.ai"

function OK($m){Write-Host "[OK]  $m" -ForegroundColor Green}
function FAIL($m){Write-Host "[FAIL] $m" -ForegroundColor Red}

$allOk=$true

# 1) Barcode lookup
try{
  $r=Invoke-RestMethod -Uri "$Base/api/v1/lookup/barcode?code=012914632109" -Method GET -TimeoutSec 30
  if($r.ok){ OK "lookup/barcode"; } else { FAIL "lookup/barcode ok=false"; $allOk=$false }
}catch{ FAIL "lookup/barcode exception: $($_.Exception.Message)"; $allOk=$false }

# 2) Visual search (accepts success=false as PASS if key is configured and HTTP 200)
try{
  $u='https://images.unsplash.com/photo-1585386959984-a4155223168f?auto=format&fit=crop&w=800&q=60'
  $body=@{image_url=$u}|ConvertTo-Json -Compress
  $resp=Invoke-WebRequest -Uri "$Base/api/v1/visual/search" -Method POST -ContentType 'application/json' -Body $body -TimeoutSec 45 -UseBasicParsing
  if($resp.StatusCode -ne 200){ FAIL "visual/search HTTP $($resp.StatusCode)"; $allOk=$false }
  else{
    $obj=$null; try{$obj=$resp.Content|ConvertFrom-Json}catch{}
    if($obj -and $obj.error -is [string] -and $obj.error -match 'not configured'){ FAIL "visual/search OpenAI key NOT configured"; $allOk=$false }
    else{ OK "visual/search (endpoint healthy)" }
  }
}catch{ FAIL "visual/search exception: $($_.Exception.Message)"; $allOk=$false }

# 3) Advanced visual recognize (multipart; low threshold)
try{
  $tmp=Join-Path $env:TEMP 'vr_test.jpg'
  Invoke-WebRequest -UseBasicParsing -OutFile $tmp -Uri 'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=1000&q=80'
  Add-Type -AssemblyName System.Net.Http
  $hc=[System.Net.Http.HttpClient]::new()
  $mp=[System.Net.Http.MultipartFormDataContent]::new()
  $fs=[System.IO.File]::OpenRead($tmp)
  $sc=[System.Net.Http.StreamContent]::new($fs)
  $sc.Headers.ContentType=[System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('image/jpeg')
  $mp.Add($sc,'image','vr_test.jpg')
  $uri="$Base/api/v1/advanced/visual/recognize?user_id=1&check_for_defects=true&confidence_threshold=0.2"
  $resp=$hc.PostAsync($uri,$mp).Result
  $code=[int]$resp.StatusCode
  $text=$resp.Content.ReadAsStringAsync().Result
  $fs.Dispose(); $hc.Dispose()
  if($code -ne 200){ FAIL "advanced/visual/recognize HTTP $code"; $allOk=$false }
  else{
    $obj=$null; try{$obj=$text|ConvertFrom-Json}catch{}
    if($obj -and $obj.status -in @('ok','low_confidence')){ OK "advanced/visual/recognize ($($obj.status))" } else { FAIL "advanced/visual/recognize unexpected body"; $allOk=$false }
  }
}catch{ FAIL "advanced/visual/recognize exception: $($_.Exception.Message)"; $allOk=$false }

if($allOk){Write-Host "ALL TESTS PASSED" -ForegroundColor Green; exit 0} else {Write-Host "ONE OR MORE TESTS FAILED" -ForegroundColor Yellow; exit 1}