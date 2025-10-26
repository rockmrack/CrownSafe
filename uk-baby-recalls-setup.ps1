<# =======================
 uk-baby-recalls-setup.ps1  (ingestion only)
 - Ingests OPSS, FSA, MHRA, DVSA (child seats) from 2024-01-01 → today
 - Upserts into public.recalls(recall_id, product_name, country, recall_date, url, source_agency, doc_type)
 - Creates baby-only materialized view + API view
 Notes:
 - Set $env:PGPASSWORD first to avoid prompts
 - Requires: psql (v16), AWS CLI, internet
 ======================= #>

[CmdletBinding()]
param(
  [string]$DbHost   = "babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com",
  [string]$DbUser   = "babyshield_user",
  [string]$DbName   = "babyshield_db",
  [int]   $DbPort   = 5432,
  [string]$Region   = "eu-north-1",
  [string]$DbInstanceId = "babyshield-prod-db",
  [string]$FromDate = "2024-01-01"
)

$ErrorActionPreference = "Stop"

# --- Paths & helpers ---
$PSql = "C:\Program Files\PostgreSQL\16\bin\psql.exe"
if (-not (Test-Path $PSql)) {
  throw "psql not found at: $PSql  (Install: winget install -e --id PostgreSQL.PostgreSQL.16)"
}
function Invoke-PSql([string]$Sql) {
  & $PSql -h $DbHost -U $DbUser -d $DbName -p $DbPort -v ON_ERROR_STOP=1 -W -c $Sql
}
$TMP = $env:TEMP
if (-not (Test-Path $TMP)) { $TMP = "$env:USERPROFILE\AppData\Local\Temp" }

Write-Host "== Opening RDS SG to your current IP (tcp/$DbPort) =="
try {
  $SgId = (aws rds describe-db-instances --db-instance-identifier $DbInstanceId --region $Region --query "DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId" --output text)
  $MyIp = (Invoke-RestMethod -Uri "https://checkip.amazonaws.com").Trim()
  aws ec2 authorize-security-group-ingress --group-id $SgId --protocol tcp --port $DbPort --cidr "$MyIp/32" --region $Region | Out-Null
} catch { Write-Host "(ingress may already exist) $_" -ForegroundColor Yellow }

# ========= DB prep =========
Write-Host "== DB prep: columns, indexes, tag guidance =="
Invoke-PSql "ALTER TABLE public.recalls ADD COLUMN IF NOT EXISTS doc_type VARCHAR(20) DEFAULT 'RECALL';"
Invoke-PSql "CREATE UNIQUE INDEX IF NOT EXISTS uniq_recalls_recallid_agency_all ON public.recalls(recall_id, source_agency);"
Invoke-PSql "CREATE INDEX IF NOT EXISTS idx_recalls_filter ON public.recalls (doc_type, source_agency, recall_date DESC);"
Invoke-PSql "UPDATE public.recalls SET doc_type='GUIDANCE'
             WHERE source_agency IN ('UK OPSS','UK_OPSS','OPSS')
               AND (url ILIKE '%gov.uk/guidance/%' OR url ILIKE '%gov.uk/government/publications/%' OR url ILIKE '%gov.uk/publications/%')
               AND url NOT ILIKE '%product-safety-alerts-reports-recalls%';"

# ========= OPSS ingest =========
Write-Host "== OPSS ingest via GOV.UK Search API =="
$opssResults=@(); $start=0
do {
  $opssUrl = "https://www.gov.uk/api/search.json?count=100&order=-public_timestamp&filter_content_store_document_type=product_safety_alert_report_recall&filter_organisations=office-for-product-safety-and-standards&filter_public_timestamp=from:$FromDate&fields[]=link&fields[]=title&fields[]=public_timestamp&fields[]=content_id&start=$start"
  $r = Invoke-RestMethod -Uri $opssUrl -TimeoutSec 30
  $batch = @($r.results); if(!$batch){break}
  $opssResults += $batch; $start += $batch.Count
} while ($batch.Count -gt 0)

$opssRows = $opssResults | ForEach-Object {
  [PSCustomObject]@{
    recall_id     = if ($_.content_id) { $_.content_id } else { $_.link }
    product_name  = $_.title
    country       = 'UK'
    recall_date   = ([datetime]$_.public_timestamp).ToString('yyyy-MM-dd')
    url           = "https://www.gov.uk$($_.link)"
    source_agency = 'UK OPSS'
    doc_type      = 'RECALL'
  }
}
$opssCsv = Join-Path $TMP "opss_recalls.csv"
$opssRows | Export-Csv -Path $opssCsv -NoTypeInformation -Force -Encoding UTF8
Invoke-PSql "CREATE TABLE IF NOT EXISTS public.opss_stage (recall_id text, product_name text, country text, recall_date text, url text, source_agency text, doc_type text); TRUNCATE public.opss_stage;"
& $PSql -h $DbHost -U $DbUser -d $DbName -p $DbPort -W -c "\copy public.opss_stage (recall_id,product_name,country,recall_date,url,source_agency,doc_type) FROM '$opssCsv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
Invoke-PSql "INSERT INTO public.recalls (recall_id, product_name, country, recall_date, url, source_agency, doc_type)
             SELECT recall_id, product_name, country, to_date(recall_date,'YYYY-MM-DD'), url, source_agency, doc_type
             FROM public.opss_stage
             ON CONFLICT (recall_id, source_agency) DO UPDATE
             SET product_name=EXCLUDED.product_name, recall_date=EXCLUDED.recall_date, url=EXCLUDED.url, doc_type=EXCLUDED.doc_type;"

# ========= FSA ingest =========
Write-Host "== FSA ingest via data.food.gov.uk =="
$fromDT = Get-Date $FromDate
$fsaAll=@(); $offset=0
do {
  $u = "https://data.food.gov.uk/food-alerts/id?_sort=-modified&_limit=1000&_offset=$offset"
  $r = Invoke-RestMethod -Uri $u -TimeoutSec 30
  $batch = @($r.items); if (-not $batch) { break }
  $fsaAll += $batch; $offset += $batch.Count
} while ($batch.Count -eq 1000)
$fsaRows = $fsaAll | Where-Object { $_.modified -and ([datetime]$_.modified) -ge $fromDT } | ForEach-Object {
  $rid  = if ($_.notation) { $_.notation } elseif ($_.id) { $_.id } elseif ($_.PSObject.Properties.Name -contains '@id') { $_.'@id' } else { $_.alertURL }
  $date = if ($_.created)  { $_.created  } else { $_.modified }
  $link = if ($_.alertURL) { $_.alertURL } elseif ($_.PSObject.Properties.Name -contains '@id') { $_.'@id' } else { $null }
  [PSCustomObject]@{
    recall_id     = $rid
    product_name  = $_.title
    country       = 'UK'
    recall_date   = ([datetime]$date).ToString('yyyy-MM-dd')
    url           = $link
    source_agency = 'UK FSA'
    doc_type      = 'RECALL'
  }
}
$fsaCsv = Join-Path $TMP "fsa_alerts.csv"
$fsaRows | Export-Csv -Path $fsaCsv -NoTypeInformation -Force -Encoding UTF8
Invoke-PSql "CREATE TABLE IF NOT EXISTS public.fsa_stage (recall_id text, product_name text, country text, recall_date text, url text, source_agency text, doc_type text); TRUNCATE public.fsa_stage;"
& $PSql -h $DbHost -U $DbUser -d $DbName -p $DbPort -W -c "\copy public.fsa_stage (recall_id,product_name,country,recall_date,url,source_agency,doc_type) FROM '$fsaCsv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
Invoke-PSql "INSERT INTO public.recalls (recall_id, product_name, country, recall_date, url, source_agency, doc_type)
             SELECT recall_id, product_name, country, to_date(recall_date,'YYYY-MM-DD'), url, source_agency, doc_type
             FROM public.fsa_stage
             ON CONFLICT (recall_id, source_agency) DO UPDATE
             SET product_name=EXCLUDED.product_name, recall_date=EXCLUDED.recall_date, url=EXCLUDED.url, doc_type=EXCLUDED.doc_type;"

# ========= MHRA ingest =========
Write-Host "== MHRA ingest via GOV.UK Search API =="
$mhraResults=@(); $start=0
do {
  $url = "https://www.gov.uk/api/search.json?count=100&order=-public_timestamp&filter_content_store_document_type=medical_safety_alert&filter_organisations=medicines-and-healthcare-products-regulatory-agency&filter_public_timestamp=from:$FromDate&fields[]=link&fields[]=title&fields[]=public_timestamp&fields[]=content_id&start=$start"
  $r = Invoke-RestMethod -Uri $url -TimeoutSec 30
  $batch = @($r.results); if(!$batch){break}
  $mhraResults += $batch; $start += $batch.Count
} while ($batch.Count -gt 0)
$mhraRows = $mhraResults | ForEach-Object {
  [PSCustomObject]@{
    recall_id     = $_.content_id
    product_name  = $_.title
    country       = 'UK'
    recall_date   = ([datetime]$_.public_timestamp).ToString('yyyy-MM-dd')
    url           = "https://www.gov.uk$($_.link)"
    source_agency = 'UK MHRA'
    doc_type      = 'RECALL'
  }
}
$mhraCsv = Join-Path $TMP "mhra_alerts.csv"
$mhraRows | Export-Csv -Path $mhraCsv -NoTypeInformation -Force -Encoding UTF8
Invoke-PSql "CREATE TABLE IF NOT EXISTS public.mhra_stage (recall_id text, product_name text, country text, recall_date text, url text, source_agency text, doc_type text); TRUNCATE public.mhra_stage;"
& $PSql -h $DbHost -U $DbUser -d $DbName -p $DbPort -W -c "\copy public.mhra_stage (recall_id,product_name,country,recall_date,url,source_agency,doc_type) FROM '$mhraCsv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
Invoke-PSql "INSERT INTO public.recalls (recall_id, product_name, country, recall_date, url, source_agency, doc_type)
             SELECT recall_id, product_name, country, to_date(recall_date,'YYYY-MM-DD'), url, source_agency, doc_type
             FROM public.mhra_stage
             ON CONFLICT (recall_id, source_agency) DO UPDATE
             SET product_name=EXCLUDED.product_name, recall_date=EXCLUDED.recall_date, url=EXCLUDED.url, doc_type=EXCLUDED.doc_type;"

# ========= DVSA ingest (child seats) =========
Write-Host "== DVSA ingest (child restraints) from CSV =="
$dvsa = Join-Path $TMP "dvsa_recalls.csv"
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$headers = @{
  'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
  'Accept'     = 'text/csv,application/octet-stream;q=0.9,*/*;q=0.8'
  'Referer'    = 'https://www.check-vehicle-recalls.service.gov.uk/'
}
Invoke-WebRequest -Uri 'https://www.check-vehicle-recalls.service.gov.uk/' -WebSession $session -Headers $headers -TimeoutSec 30 | Out-Null
Start-Sleep -Milliseconds 600
Invoke-WebRequest -Uri 'https://www.check-vehicle-recalls.service.gov.uk/documents/RecallsFile.csv' -WebSession $session -Headers $headers -TimeoutSec 60 -OutFile $dvsa

$all = Import-Csv -Path $dvsa
$child = $all | Where-Object {
  ($_.{'Recalls Model Information'} -match '(?i)\b(child|infant|booster|car ?seat|restraint|isofix|i-?size|r129|r44)\b') -or
  ($_.Model                          -match '(?i)\b(child|infant|booster|car ?seat|restraint|isofix|i-?size|r129|r44)\b') -or
  ($_.Concern                        -match '(?i)\b(child|infant|booster|car ?seat|restraint)\b') -or
  ($_.Defect                         -match '(?i)\b(child|infant|booster|car ?seat|restraint)\b') -or
  ($_.Make                           -match '(?i)\b(BRITAX|R(Ö|O)MER|CYBEX|MAXI[- ]?COSI|JOIE|BESAFE|GRACO|COSATTO|SILVER\s?CROSS|RECARO|MOTHERCARE|NUNA|CHICCO|BUGABOO|CONCORD)\b')
}
$gb = [System.Globalization.CultureInfo]::GetCultureInfo('en-GB')
$dvsaRows = $child | ForEach-Object {
  $dateStr = $_.'Launch Date'
  $dateIso = $null
  try { $dateIso = ([datetime]::ParseExact($dateStr,'dd/MM/yyyy',$gb)).ToString('yyyy-MM-dd') } catch {}
  if (-not $dateIso) { try { $dateIso = ([datetime]::Parse($dateStr,$gb)).ToString('yyyy-MM-dd') } catch {} }
  $parts = @($_.Make, $_.Model, $_.'Recalls Model Information') | Where-Object { $_ -and $_.Trim() -ne '' }
  $name  = if ($parts.Count) { ($parts -join ' ') } else { $_.Concern }
  [PSCustomObject]@{
    recall_id     = $_.'Recalls Number'
    product_name  = $name
    country       = 'UK'
    recall_date   = $dateIso
    url           = 'https://www.check-vehicle-recalls.service.gov.uk/'
    source_agency = 'UK DVSA'
    doc_type      = 'RECALL'
  }
} | Where-Object { $_.recall_id -and $_.recall_date }

$dvsaCsv = Join-Path $TMP "dvsa_child_recalls.csv"
$dvsaRows | Sort-Object recall_date -Descending | Export-Csv -Path $dvsaCsv -NoTypeInformation -Force -Encoding UTF8

Invoke-PSql "CREATE TABLE IF NOT EXISTS public.dvsa_stage (recall_id text, product_name text, country text, recall_date text, url text, source_agency text, doc_type text); TRUNCATE public.dvsa_stage;"
& $PSql -h $DbHost -U $DbUser -d $DbName -p $DbPort -W -c "\copy public.dvsa_stage (recall_id,product_name,country,recall_date,url,source_agency,doc_type) FROM '$dvsaCsv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
Invoke-PSql "WITH d AS (
               SELECT DISTINCT ON (recall_id, source_agency)
                      recall_id, product_name, country, to_date(recall_date,'YYYY-MM-DD') AS recall_date, url, source_agency, doc_type
               FROM public.dvsa_stage
               WHERE recall_id IS NOT NULL
               ORDER BY recall_id, source_agency, to_date(recall_date,'YYYY-MM-DD') DESC
             )
             INSERT INTO public.recalls (recall_id, product_name, country, recall_date, url, source_agency, doc_type)
             SELECT recall_id, product_name, country, recall_date, url, source_agency, doc_type
             FROM d
             ON CONFLICT (recall_id, source_agency) DO UPDATE
             SET product_name=EXCLUDED.product_name, recall_date=EXCLUDED.recall_date, url=EXCLUDED.url, doc_type=EXCLUDED.doc_type;"

# ========= Baby-only surface =========
Write-Host "== Create/refresh baby-only materialized view & API view =="
Invoke-PSql "DROP MATERIALIZED VIEW IF EXISTS public.uk_baby_recalls;
             CREATE MATERIALIZED VIEW public.uk_baby_recalls AS
             SELECT * FROM public.recalls
             WHERE doc_type='RECALL' AND (
               (source_agency IN ('UK OPSS','UK FSA','UK MHRA') AND (
                 product_name ILIKE ANY(ARRAY['%baby%','%infant%','%child%','%children%','%toddler%','%pram%','%pushchair%','%stroller%','%cot%','%crib%','%car seat%','%booster%','%high chair%','%pacifier%','%soother%','%teether%','%sleeping bag%','%playpen%','%monitor%','%bottle%','%formula%'])
               ))
               OR (source_agency='UK DVSA' AND product_name ILIKE ANY(ARRAY[
                 '%BRITAX%','%RÖMER%','%ROMER%','%CYBEX%','%MAXI COSI%','%MAXI-COSI%','%JOIE%','%BESAFE%','%GRACO%','%COSATTO%','%SILVER CROSS%','%RECARO%','%MOTHERCARE%','%NUNA%','%CHICCO%','%BUGABOO%','%CONCORD%',
                 '%CAR SEAT%','%BOOSTER%','%CHILD SEAT%','%CHILD RESTRAINT%','%ISOFIX%','%I-SIZE%','%I SIZE%','%R129%','%R44%'
               ]))
             );
             CREATE UNIQUE INDEX IF NOT EXISTS uk_baby_recalls_uniq ON public.uk_baby_recalls(source_agency, recall_id);
             REFRESH MATERIALIZED VIEW public.uk_baby_recalls;"

Invoke-PSql "CREATE OR REPLACE VIEW public.api_uk_baby_recalls AS
             SELECT recall_id AS id, product_name AS title, url, source_agency AS agency, recall_date::date AS date
             FROM public.uk_baby_recalls
             WHERE recall_date >= (current_date - interval '2 years');"

# ========= Sanity checks =========
Write-Host "== Sanity checks =="
& $PSql -h $DbHost -U $DbUser -d $DbName -p $DbPort -W -c "SELECT source_agency, COUNT(*) AS items FROM public.recalls WHERE doc_type='RECALL' AND source_agency IN ('UK OPSS','UK FSA','UK MHRA','UK DVSA') GROUP BY 1 ORDER BY items DESC;"
& $PSql -h $DbHost -U $DbUser -d $DbName -p $DbPort -W -c "SELECT source_agency, COUNT(*) FROM public.uk_baby_recalls GROUP BY 1 ORDER BY 2 DESC;"
& $PSql -h $DbHost -U $DbUser -d $DbName -p $DbPort -W -c "SELECT * FROM public.api_uk_baby_recalls ORDER BY date DESC LIMIT 20;"

Write-Host "`nIngestion finished ✅" -ForegroundColor Green
