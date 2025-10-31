# Fix all datetime.utcnow() calls to datetime.now(timezone.utc)
# This script adds timezone import and replaces all utcnow() calls

$ErrorActionPreference = "Stop"

Write-Host "Finding Python files with datetime.utcnow()..." -ForegroundColor Cyan

# Get all Python files with datetime.utcnow()
$files = Get-ChildItem -Path . -Include *.py -Recurse | Where-Object {
    $content = Get-Content $_.FullName -Raw
    $content -match 'datetime\.utcnow\(\)'
}

Write-Host "Found $($files.Count) files to fix" -ForegroundColor Yellow

foreach ($file in $files) {
    Write-Host "Processing: $($file.Name)" -ForegroundColor Green
    
    $content = Get-Content $file.FullName -Raw
    
    # Check if timezone is already imported
    if ($content -notmatch 'from datetime import.*timezone') {
        # Add timezone to existing datetime import
        if ($content -match 'from datetime import ([^\n]+)') {
            $imports = $matches[1].Trim()
            if ($imports -notmatch 'timezone') {
                $newImports = "$imports, timezone"
                $content = $content -replace "from datetime import $imports", "from datetime import $newImports"
                Write-Host "  Added timezone import" -ForegroundColor Gray
            }
        }
    }
    
    # Replace all datetime.utcnow() with datetime.now(timezone.utc)
    $count = ([regex]::Matches($content, 'datetime\.utcnow\(\)')).Count
    $content = $content -replace 'datetime\.utcnow\(\)', 'datetime.now(timezone.utc)'
    
    # Write back to file
    Set-Content -Path $file.FullName -Value $content -NoNewline
    
    Write-Host "  Fixed $count occurrences" -ForegroundColor Gray
}

Write-Host "`nDone! Run 'ruff check . --select DTZ003' to verify" -ForegroundColor Cyan
