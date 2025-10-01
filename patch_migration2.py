import re, pathlib
p = pathlib.Path(r".\migrations\versions\2024_08_22_0100_001_create_recalls_enhanced_table.py")
t = p.read_text(encoding="utf-8")
def inject_guard(src, func):
    pat = rf"(def\s+{func}\s*\(\s*\)\s*:\s*\n)"
    if re.search(pat + r"[ \t]*bind\s*=\s*op\.get_bind\(\)", src):
        print(f"{func}: guard already present"); return src
    return re.sub(pat, r"\1    bind = op.get_bind()\n    if bind.dialect.name != 'postgresql':\n        return\n", src, count=1)
t2 = inject_guard(t, "upgrade")
t2 = inject_guard(t2, "downgrade")
if t2 != t:
    p.write_text(t2, encoding="utf-8"); print("Patched migration file.")
else:
    print("No change (already patched).")
