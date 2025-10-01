import os, re, pathlib

p = pathlib.Path("api/baby_features_endpoints.py")
s = p.read_text(encoding="utf-8")

# Ensure imports
if "from fastapi import" in s and "Response" not in s:
    s = s.replace("from fastapi import ", "from fastapi import Response, ", 1)
elif "from fastapi import Response" not in s:
    s = "from fastapi import Response\n" + s

if "from sqlalchemy.orm import Session" not in s:
    s = s.replace("from sqlalchemy.orm import", "from sqlalchemy.orm import Session,", 1) if "from sqlalchemy.orm import" in s else "from sqlalchemy.orm import Session\n" + s

if "import os" not in s:
    s = "import os\n" + s

# Replace the HEAD route block
pat = re.compile(
    r'@router\.head\("/reports/download/\{report_id\}"\)[\s\S]*?^def\s+[a-zA-Z_]\w*\s*\([\s\S]*?\):[\s\S]*?(?=^\s*@router\.|^\Z)',
    re.M,
)

new_block = r'''
@router.head("/reports/download/{report_id}")
def head_report_download(
    report_id: str,
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    """
    HEAD for report download — emit accurate headers (incl. Content-Length)
    without sending the body.
    """
    # Try DB record first
    rec = None
    try:
        rec = db.query(ReportRecord).filter(ReportRecord.report_id == report_id).first()  # type: ignore[name-defined]
    except Exception:
        rec = None

    path = getattr(rec, "storage_path", "") or os.path.join(
        os.getcwd(), "generated_reports", f"report_{report_id}.pdf"
    )
    size = os.path.getsize(path) if os.path.exists(path) else 0
    filename = f"babyshield_report_{report_id}.pdf"

    # Mirror GET headers
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Content-Length"] = str(size)

    return Response(status_code=200)
'''.strip()

s2, n = pat.subn(new_block, s)
if n == 0:
    print("HEAD route pattern not found; no change.")
else:
    p.write_text(s2, encoding="utf-8")
    print("Patched HEAD route with accurate Content-Length.")
