from pathlib import Path, re
p = Path("api/baby_features_endpoints.py")
s = p.read_text(encoding="utf-8")

# Find the GET download handler name and whether it's async
m = re.search(r'@router\.get\("/reports/download/\{report_id\}"\)\s*(async\s+)?def\s+(\w+)\(', s)
is_async = bool(m and m.group(1))
get_fn = m.group(2) if m else "download_report"

# Replace the HEAD block to be async and delegate (await if needed)
def repl_head(_):
    return (
        '@router.head("/reports/download/{report_id}")\n'
        'async def head_download_report(report_id: str, user=Depends(get_current_active_user)):\n'
        f'    res = {get_fn}(report_id, user)\n'
        '    import inspect\n'
        '    if inspect.isawaitable(res):\n'
        '        res = await res\n'
        '    return res\n'
    )

s2 = re.sub(
    r'@router\.head\("/reports/download/\{report_id\}"\)[\s\S]*?^def\s+\w+\(.*?\):[\s\S]*?(?=^@router\.|\Z)',
    repl_head, s, flags=re.M
)

# If there was no explicit HEAD block (shouldn’t happen now), inject one after the GET def.
if s2 == s:
    m2 = re.search(r'(@router\.get\("/reports/download/\{report_id\}"\)[\s\S]*?\n)(async\s+)?def\s+\w+\([\s\S]*?\n\)', s)
    if m2:
        insert_at = m2.end()
        head_block = (
            f'\n\n@router.head("/reports/download/{{report_id}}")\n'
            f'async def head_download_report(report_id: str, user=Depends(get_current_active_user)):\n'
            f'    res = {get_fn}(report_id, user)\n'
            f'    import inspect\n'
            f'    if inspect.isawaitable(res):\n'
            f'        res = await res\n'
            f'    return res\n'
        )
        s2 = s[:insert_at] + head_block + s[insert_at:]

p.write_text(s2, encoding="utf-8")
print("Patched: HEAD is async and delegates to", get_fn)
