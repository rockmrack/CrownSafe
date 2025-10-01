from pathlib import Path
import re

p = Path("api/baby_features_endpoints.py")
s = p.read_text(encoding="utf-8")

# 1) Ensure HEAD path is relative (respects the router prefix)
s = re.sub(
    r'@router\.head\("/api/v1/baby/reports/download/\{report_id\}"\)',
    '@router.head("/reports/download/{report_id}")',
    s,
)

# 2) Discover the GET handler name for the download route
m = re.search(
    r'@router\.get\("/reports/download/\{report_id\}"\)\s*def\s+(\w+)\(',
    s
)
get_fn = m.group(1) if m else "download_report"

# 3) Replace the HEAD handler body to delegate to the GET handler
def repl_head(match):
    # Rebuild a clean, minimal HEAD handler that calls the GET one
    return (
        '@router.head("/reports/download/{report_id}")\n'
        f'def head_download_report(report_id: str, user=Depends(get_current_active_user)):\n'
        f'    return {get_fn}(report_id, user)\n'
    )

s2 = re.sub(
    r'@router\.head\("/reports/download/\{report_id\}"\)[\s\S]*?^def\s+\w+\(.*?\):[\s\S]*?(?=^@router\.|\Z)',
    repl_head,
    s,
    flags=re.M
)

# If there was no explicit HEAD route, inject one that delegates
if s2 == s:
    insert_after = re.search(
        r'@router\.get\("/reports/download/\{report_id\}"\)[\s\S]*?\ndef\s+(\w+)\([\s\S]*?\n\)',
        s
    )
    if insert_after:
        pos = insert_after.end()
        s2 = s[:pos] + (
            f'\n\n@router.head("/reports/download/{{report_id}}")\n'
            f'def head_download_report(report_id: str, user=Depends(get_current_active_user)):\n'
            f'    return {get_fn}(report_id, user)\n'
        ) + s[pos:]

Path("api/baby_features_endpoints.py").write_text(s2, encoding="utf-8")
print("HEAD now delegates to GET:", get_fn)
