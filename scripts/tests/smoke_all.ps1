param([string]$Base="https://babyshield.cureviax.ai")
$ErrorActionPreference='Stop'

function Run-Test {
  param([string]$Name,[string]$Path,[object[]]$Args)
  if(-not (Test-Path $Path)){
    return [pscustomobject]@{ Name=$Name; Result="SKIP (missing)"; ExitCode=$null }
  }
  try{
    $exe = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
    if(-not $exe){ $exe = (Get-Command powershell -ErrorAction Stop).Source }
    $argList = @('-NoLogo','-NoProfile','-File', (Resolve-Path $Path).Path) + $Args
    $proc = Start-Process -FilePath $exe -ArgumentList $argList -Wait -PassThru
    $code = $proc.ExitCode
    if($code -eq 0){ return [pscustomobject]@{ Name=$Name; Result="OK";   ExitCode=$code } }
    else           { return [pscustomobject]@{ Name=$Name; Result="FAIL"; ExitCode=$code } }
  } catch {
    return [pscustomobject]@{ Name=$Name; Result=("ERROR: "+$_.Exception.Message); ExitCode=1 }
  }
}

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)  # repo root
$tests = @(
  @{ Name="Quick Status";              Path=Join-Path $root "CHECK_RECOGNITION_STATUS.ps1";           Args=@() },
  @{ Name="Barcode Smoke";             Path=Join-Path $PSScriptRoot "smoke_barcode.ps1";              Args=@($Base) },
  @{ Name="Recognition Capabilities";  Path=Join-Path $root "TEST_RECOGNITION_CAPABILITIES.ps1";      Args=@() },
  @{ Name="Complete Suite";            Path=Join-Path $root "COMPLETE_VISUAL_RECOGNITION_TESTS.ps1";  Args=@() }
)

$results = foreach($t in $tests){ Run-Test -Name $t.Name -Path $t.Path -Args $t.Args }
$results | ForEach-Object { "{0,-28} {1}" -f $_.Name, $_.Result } | Write-Host

$fail = $results | Where-Object { $_.ExitCode -ne $null -and $_.ExitCode -ne 0 }
if($fail){ exit 1 } else { exit 0 }