import re, pathlib

p = pathlib.Path(r".\api\baby_features_endpoints.py")
s = p.read_text(encoding="utf-8")

# 1) Detect the dependency used by the GET download route
get_pat = re.compile(
    r'@router\.get\("/reports/download/\{report_id\}"\)[\s\S]*?def\s+\w+\((?P<params>[\s\S]*?)\):',
    re.M
)
m = get_pat.search(s)
dep_name = None
if m:
    params = m.group("params")
    mdep = re.search(r"user\s*=\s*Depends\(\s*(\w+)\s*\)", params)
    if mdep:
        dep_name = mdep.group(1)

# 2) Fallback if not found: prefer get_current_active_user if present in file
if not dep_name:
    if "get_current_active_user" in s:
        dep_name = "get_current_active_user"
    else:
        dep_name = "get_current_user"  # last resort

# 3) Replace the HEAD route's dependency with the chosen one
head_pat = re.compile(
    r'(@router\.head\("/reports/download/\{report_id\}"\)[\s\S]*?def\s+\w+\()\s*report_id:\s*str,\s*[\s\S]*?user\s*=\s*Depends\(\s*\w+\s*\)([\s\S]*?\):)',
    re.M
)
s2, n = head_pat.subn(rf'\1report_id: str, db: Session = Depends(get_db), user=Depends({dep_name})\2', s)

if n:
    p.write_text(s2, encoding="utf-8")
    print(f"Patched HEAD dependency to use: {dep_name}")
else:
    print("No change (HEAD route not matched)")
