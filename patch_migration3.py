import re, pathlib
p = pathlib.Path(r".\migrations\versions\2024_08_22_0100_001_create_recalls_enhanced_table.py")
t = p.read_text(encoding="utf-8")

def inject_guard(src, func):
    # Match: def upgrade() -> None:   (return annotation optional)
    pat = re.compile(rf"(def\s+{func}\s*\([^)]*\)\s*:\s*\n)")
    if "bind.dialect.name != 'postgresql'" in src and f"def {func}" in src:
        print(f"{func}: guard already present"); return src
    return pat.sub(
        r"\1    bind = op.get_bind()\n"
        r"    if bind.dialect.name != 'postgresql':\n"
        r"        print('Skipping Postgres-only migration on', bind.dialect.name)\n"
        r"        return\n",
        src, count=1
    )

t2 = inject_guard(t, "upgrade")
t2 = inject_guard(t2, "downgrade")

if t2 != t:
    p.write_text(t2, encoding="utf-8")
    print("Patched 001 migration.")
else:
    print("No change")
