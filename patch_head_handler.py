import re, pathlib

p = pathlib.Path(r".\api\baby_features_endpoints.py")
s = p.read_text(encoding="utf-8")

pattern = re.compile(
    r"@router\.head\(\"/reports/download/\{report_id\}\"\)[\s\S]*?def\s+\w+\([\s\S]*?\):[\s\S]*?(?=\n@router|$)",
    re.M
)

new_block = r"""
@router.head("/reports/download/{report_id}")
def head_report_download(
    report_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Look up stored path for this report
    try:
        rec = db.query(ReportRecord).filter(ReportRecord.report_id == report_id).first()
    except Exception:
        rec = None

    fname = f"babyshield_report_{report_id}.pdf"
    path = getattr(rec, "storage_path", "") or ""
    size = os.path.getsize(path) if path and os.path.exists(path) else 0

    headers = {
        "Content-Type": "application/pdf",
        "Content-Disposition": f'attachment; filename="{fname}"',
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Content-Length": str(size),
    }
    return Response(status_code=200, headers=headers, media_type="application/pdf")
"""

# Ensure required imports exist
if "from fastapi import Response" not in s:
    s = s.replace("from fastapi import", "from fastapi import Response,")
if "import os" not in s:
    s = "import os\n" + s

s2 = pattern.sub(new_block.strip()+"\n", s)
if s2 != s:
    p.write_text(s2, encoding="utf-8")
    print("HEAD handler updated.")
else:
    print("No change (already updated).")
