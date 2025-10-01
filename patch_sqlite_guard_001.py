from pathlib import Path
p = Path(r".\migrations\versions\2024_08_22_0100_001_create_recalls_enhanced_table.py")
s = p.read_text(encoding="utf-8")
anchor = "    # Check if table already exists (for idempotency)"
guard  = (
    "    bind = op.get_bind()\n"
    "    if bind.dialect.name != 'postgresql':\n"
    "        print('Skipping Postgres-only migration on', bind.dialect.name)\n"
    "        return\n\n"
)
if guard not in s:
    if anchor in s:
        s = s.replace(anchor, guard + anchor)
        p.write_text(s, encoding="utf-8")
        print("Guard inserted.")
    else:
        print("Anchor not found; no change.")
else:
    print("Guard already present.")
