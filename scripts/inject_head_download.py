import pathlib, re

p = pathlib.Path("api/baby_features_endpoints.py")
s = p.read_text(encoding="utf-8")

# 1) ensure imports
if "from fastapi import Response" not in s:
    s = re.sub(r"(from fastapi import[^\n]*)", r"\1, Response", s, count=1)
if "from sqlalchemy import text" not in s:
    if "\nfrom sqlalchemy import " in s:
        s = s.replace("\nfrom sqlalchemy import ", "\nfrom sqlalchemy import text, ")
    else:
        s = s.replace("\nimport sqlalchemy as sa", "\nimport sqlalchemy as sa\nfrom sqlalchemy import text")
if "import os" not in s:
    s = "import os\n" + s
if "import pathlib" not in s:
    s = "import pathlib\n" + s

# 2) add helper to resolve file path (only if missing)
helper = """
def _resolve_report_path_for_head(report_id: str, user, db):
    \"\"\"Best-effort path resolution used by the HEAD route.\"\"\"
    storage_path = None
    try:
        uid = getattr(user, "id", getattr(user, "user_id", None))
        row = db.execute(text(
            "SELECT storage_path FROM report_records WHERE report_id = :rid AND user_id = :uid"
        ), {"rid": report_id, "uid": uid}).fetchone()
        if row and row[0]:
            storage_path = row[0]
    except Exception:
        pass

    if not storage_path or not os.path.isfile(storage_path):
        base_dir = pathlib.Path(__file__).resolve().parents[1] / "generated_reports"
        cand = base_dir / f"report_{report_id}.pdf"
        if cand.is_file():
            storage_path = str(cand)

    return storage_path
"""

if "_resolve_report_path_for_head(" not in s:
    # put helper near the end, before the new route
    s += "\n" + helper + "\n"

# 3) add the HEAD route (if missing)
route_sig = '@router.head("/api/v1/baby/reports/download/{report_id}")'
if route_sig not in s:
    head_route = f"""
{route_sig}
async def head_download_report(
    report_id: str,
    user = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    storage_path = _resolve_report_path_for_head(report_id, user, db)
    if not storage_path or not os.path.isfile(storage_path):
        raise HTTPException(status_code=404, detail="Report not found")
    size = os.path.getsize(storage_path)
    headers = {{
        "Content-Type": "application/pdf",
        "Content-Disposition": f'attachment; filename="babyshield_report_{{report_id}}.pdf"',
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Content-Length": str(size),
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
    }}
    return Response(status_code=200, headers=headers)
"""
    s += "\n" + head_route + "\n"

p.write_text(s, encoding="utf-8")
print("HEAD route injected (or already present).")
