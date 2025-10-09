import re, pathlib, glob

paths = [pathlib.Path(p) for p in glob.glob("api/**/*.py", recursive=True)]


def patch_file(p: pathlib.Path) -> bool:
    s = p.read_text(encoding="utf-8")
    if "model_number" not in s:
        return False

    changed = False

    # Ensure import of AppModel (insert after the last top-level import)
    if "from api.pydantic_base import AppModel" not in s:
        lines = s.splitlines(True)
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith(("from ", "import ")):
                insert_idx = i + 1
            elif line.strip() and not line.startswith(("#", '"""', "'''")):
                break
        lines.insert(insert_idx, "from api.pydantic_base import AppModel\n")
        s = "".join(lines)
        changed = True

    # Replace class Foo(BaseModel): ... (only when that class block contains model_number:)
    pattern = re.compile(
        r"(class\s+\w+\(\s*BaseModel\s*\)\s*:\s*)([\s\S]*?)(?=^class\s+\w+\(|\Z)", re.M
    )
    flag = [False]

    def repl(m):
        body = m.group(2)
        if re.search(r"\bmodel_number\s*:", body):
            flag[0] = True
            return m.group(1).replace("BaseModel", "AppModel") + body
        return m.group(0)

    s2 = pattern.sub(repl, s)
    if flag[0] or changed:
        p.write_text(s2, encoding="utf-8")
        return True
    return False


count = 0
for p in paths:
    try:
        if p.is_file() and patch_file(p):
            print("Patched:", p)
            count += 1
    except Exception as e:
        print("Skip:", p, "-", e)

print("Done. Files patched:", count)
