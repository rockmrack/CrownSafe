from pathlib import Path
import re

p = Path("api/baby_features_endpoints.py")
s = p.read_text(encoding="utf-8")

# Change absolute to relative for the HEAD route
s2 = re.sub(
    r'@router\.head\("/api/v1/baby/reports/download/\{report_id\}"\)',
    '@router.head("/reports/download/{report_id}")',
    s,
    count=1,
)

if s2 != s:
    p.write_text(s2, encoding="utf-8")
    print("Updated HEAD route to relative path.")
else:
    print("No change (already relative).")
