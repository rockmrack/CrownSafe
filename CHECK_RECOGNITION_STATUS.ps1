param()

$Base = "https://babyshield.cureviax.ai"

$tests = @(
  @{ Name="healthz GET";          Method="GET";  Uri="$Base/healthz" },
  @{ Name="readyz GET";           Method="GET";  Uri="$Base/readyz" },
  @{ Name="lookup/barcode GET";   Method="GET";  Uri="$Base/api/v1/lookup/barcode?code=012914632109" },
  @{ Name="visual/search POST";   Method="POST"; Uri="$Base/api/v1/visual/search"; Body=@{ image_url="https://images.unsplash.com/photo-1585386959984-a4155223168f?auto=format&fit=crop&w=600&q=60" }; ContentType="application/json" }
)

function Test-Endp {
  param($t)
  try {
    if ($t.Method -eq "POST") {
      $json = $t.Body | ConvertTo-Json -Compress
      $r = Invoke-RestMethod -Method Post -Uri $t.Uri -ContentType $t.ContentType -Body $json -TimeoutSec 30
      Write-Host "[OK]  $($t.Name)" -ForegroundColor Green
      return @{ name=$t.Name; ok=$true }
    } else {
      $r = Invoke-WebRequest -Method Get -Uri $t.Uri -TimeoutSec 30 -UseBasicParsing
      Write-Host "[OK]  $($t.Name) $($r.StatusCode)" -ForegroundColor Green
      return @{ name=$t.Name; ok=$true }
    }
  } catch {
    $status = $null
    try { $status = $_.Exception.Response.StatusCode.value__ } catch {}
    if (-not $status) { $status = "ERR" }
    Write-Host "[FAIL] $($t.Name) status=$status" -ForegroundColor Red
    return @{ name=$t.Name; ok=$false; status=$status; err=$_.Exception.Message }
  }
}

$results = foreach ($t in $tests) { Test-Endp $t }

$fail = $results | Where-Object { -not $_.ok }
if ($fail) { exit 1 } else { exit 0 }