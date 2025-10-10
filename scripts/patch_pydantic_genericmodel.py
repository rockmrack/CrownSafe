import pathlib
import re
import glob

paths = [pathlib.Path(p) for p in glob.glob("api/**/*.py", recursive=True)]
changed = 0

for p in paths:
    s = p.read_text(encoding="utf-8")
    if "GenericModel" not in s and "pydantic.generics" not in s:
        continue

    s2 = s
    s2 = re.sub(
        r"from\s+pydantic\.generics\s+import\s+GenericModel",
        "from pydantic import BaseModel",
        s2,
    )
    s2 = re.sub(r"\bGenericModel\b", "BaseModel", s2)

    if s2 != s:
        p.write_text(s2, encoding="utf-8")
        print("Patched:", p)
        changed += 1

print("Done. Files patched:", changed)
