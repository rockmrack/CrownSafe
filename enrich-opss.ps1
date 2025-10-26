[CmdletBinding()]
param(
  [string]$DbHost   = "babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com",
  [string]$DbUser   = "babyshield_user",
  [string]$DbName   = "babyshield_db",
  [int]   $DbPort   = 5432,
  [string]$FromDate = "2024-01-01",
  [int]   $MaxParallel = 15
)
$ErrorActionPreference = "Stop"
$PSql = "C:\Program Files\PostgreSQL\16\bin\psql.exe"
if (-not (Test-Path $PSql)) { throw "psql not found at $PSql" }

function Invoke-PSql([string]$Sql){ & $PSql -h $DbHost -U $DbUser -d $DbName -p $DbPort -v ON_ERROR_STOP=1 -w -c $Sql }

# --- helpers: strip HTML and extract <dd> after labelled <dt> ---
function StripTags([string]$s){
  if([string]::IsNullOrWhiteSpace($s)){ return $null }
  $t = [regex]::Replace($s, '<[^>]+>', ' ')
  $t = ($t -replace '\s+',' ').Trim()
  return [System.Net.WebUtility]::HtmlDecode($t)
}
function GetField($html, $label){
  $rx  = [regex]::new("<dt[^>]*>\s*$label\s*:\s*</dt>\s*<dd[^>]*>(.*?)</dd>", 'IgnoreCase,Singleline')
  $m   = $rx.Match($html)
  if($m.Success){ return StripTags($m.Groups[1].Value) }
  return $null
}

# 1) Export candidates
$csv = Join-Path $env:TEMP "opss_urls_$([Guid]::NewGuid().ToString('n')).csv"
Invoke-PSql "\copy (SELECT recall_id,url FROM public.recalls WHERE source_agency='UK OPSS' AND recall_date >= to_date('$FromDate','YYYY-MM-DD')) TO '$csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
$rows = Import-Csv -Path $csv

# 2) Parallel scrape
$ua = @{ 'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36' }
$jobs = @()
$results = New-Object System.Collections.Concurrent.ConcurrentBag[object]

foreach($r in $rows){
  while(($jobs | Where-Object { $_.State -eq 'Running' }).Count -ge $MaxParallel){
    $done = Wait-Job -Any $jobs
    if($done){ $out = Receive-Job $done -ErrorAction SilentlyContinue; if($out){ $results.Add($out) } ; Remove-Job $done }
  }
  $jobs += Start-Job -ScriptBlock {
    param($recall_id,$url,$uaHash)
    try{
      $resp = Invoke-WebRequest -Uri $url -Headers $uaHash -TimeoutSec 40 -UseBasicParsing
      $html = $resp.Content
      $pc = GetField $html 'Product category'
      $mt = GetField $html 'Measure type'
      $rl = GetField $html 'Risk level'
      [PSCustomObject]@{recall_id=$recall_id; product_category=$pc; measure_type=$mt; risk_level=$rl}
    } catch {
      [PSCustomObject]@{recall_id=$recall_id; product_category=$null; measure_type=$null; risk_level=$null}
    }
  } -ArgumentList $r.recall_id,$r.url,$ua
}

# drain
foreach($j in $jobs){
  $null = Wait-Job $j
  $out = Receive-Job $j -ErrorAction SilentlyContinue
  if($out){ $results.Add($out) }
  Remove-Job $j
}

# 3) Stage → bulk update (PERMANENT staging table across connections)
Invoke-PSql "CREATE TABLE IF NOT EXISTS public.opss_enrich_stage (recall_id text PRIMARY KEY, product_category text, measure_type text, risk_level text);
             TRUNCATE public.opss_enrich_stage;"

$stage = Join-Path $env:TEMP "opss_enriched_$([Guid]::NewGuid().ToString('n')).csv"
$results | Where-Object { $_.recall_id } | Select-Object recall_id, product_category, measure_type, risk_level | Export-Csv -Path $stage -NoTypeInformation -Encoding UTF8
& $PSql -h $DbHost -U $DbUser -d $DbName -p $DbPort -w -c "\copy public.opss_enrich_stage (recall_id,product_category,measure_type,risk_level) FROM '$stage' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"

Invoke-PSql @"
UPDATE public.recalls r
SET product_category = COALESCE(NULLIF(s.product_category,''), r.product_category),
    measure_type     = COALESCE(NULLIF(s.measure_type,''),     r.measure_type),
    risk_level       = COALESCE(NULLIF(s.risk_level,''),       r.risk_level)
FROM public.opss_enrich_stage s
WHERE r.source_agency='UK OPSS' AND r.recall_id = s.recall_id
  AND (s.product_category IS NOT NULL OR s.measure_type IS NOT NULL OR s.risk_level IS NOT NULL);
"@

# 4) report
$cnt = (& $PSql -h $DbHost -U $DbUser -d $DbName -p $DbPort -w -t -A -c "SELECT COUNT(*) FROM public.recalls WHERE source_agency='UK OPSS' AND product_category IS NOT NULL AND recall_date >= to_date('$FromDate','YYYY-MM-DD');").Trim()
Write-Host "OPSS enrichment complete. Rows with category now set (>= $FromDate): $cnt" -ForegroundColor Green

