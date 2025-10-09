from pathlib import Path
import re

tpl_dir = Path(r".\agents\reporting\report_builder_agent\templates")
for p in tpl_dir.glob("*.html"):
    s = p.read_text(encoding="utf-8")
    if '{% from "macros/logo.html" import render_logo %}' not in s:
        s = '{% from "macros/logo.html" import render_logo %}\n' + s
    # Replace any <img ... src="(file://...|{{ logo_src }}|)" ...> with the guarded macro
    s = re.sub(
        r'<img[^>]+src\s*=\s*"(?:file:[^"]*|{{\s*logo_src\s*}}|)"[^>]*>',
        "{{ render_logo(logo_src, width=160, style='margin-bottom:12px;') }}",
        s,
    )
    p.write_text(s, encoding="utf-8")
print("Templates patched.")
