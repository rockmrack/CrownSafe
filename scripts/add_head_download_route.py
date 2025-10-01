import os, pathlib, re
p = pathlib.Path("api/baby_features_endpoints.py")
s = p.read_text(encoding="utf-8")

if "@router.head(\"/api/v1/baby/reports/download/{report_id}\")" in s:
    print("HEAD route already present")
else:
    # ensure imports
    if "from fastapi import Response" not in s:
        s = re.sub(r"(from fastapi import [^\n]+)", r"\1, Response", s, count=1)
    if "from sqlalchemy import text" not in s:
        if "\nfrom sqlalchemy import " in s:
            s = s.replace("\nfrom sqlalchemy import ", "\nfrom sqlalchemy import text, ")
        else:
            s = s.replace("\nimport sqlalchemy as sa", "\nimport sqlalchemy as sa\nfrom sqlalchemy import text")
    if "import os" not in s:
        s = "import os\n" + s

    head_func = '''
@router.head("/api/v1/baby/reports/download/{report_id}")
async def head_download_report(
    report_id: str,
    user = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # lookup via report_records if present
    storage_path = None
    try:
        row = db.execute(text(
            "SELECT storage_path FROM report_records WHERE report_id = :rid AND user_id = :uid"
        ), {"rid": report_id, "uid": getattr(user, "id", getattr(user, "user_id", None))}).fetchone()
        if row and row[0]:
            storage_path = row[0]
    except Exception:
        pass

    if not storage_path or not os.path.isfile(storage_path):
        base_dir = pathlib.Path(__file__).resolve().parents[1] / "generated_reports"
        candidate = base_dir / f"report_{report_id}.pdf"
        if candidate.is_file():
            storage_path = str(candidate)

    if not storage_path or not os.path.isfile(storage_path):
        raise HTTPException(status_code=404, detail="Report not found")

    size = os.path.getsize(storage_path)
    headers = {
        "Content-Type": "application/pdf",
        "Content-Disposition": f'attachment; filename="babyshield_report_{report_id}.pdf"',
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Content-Length": str(size),
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
    }
    return Response(status_code=200, headers=headers)
'''
    s += "\n" + head_func
    p.write_text(s, encoding="utf-8")
    print("Added explicit HEAD handler")
