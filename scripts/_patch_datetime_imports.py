"""Utility script to replace deprecated datetime UTC imports with timezone.utc."""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = "UTC = timezone.utc"

updated_files: list[str] = []

for path in ROOT.rglob("*.py"):
    if path.name == "datetime.py":
        continue

    text = path.read_text()
    if "from datetime import" not in text or "UTC" not in text:
        continue

    lines = text.splitlines()
    modified = False

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("from datetime import") or "UTC" not in stripped:
            continue

        if "#" in line:
            before_comment, comment = line.split("#", 1)
            comment = "#" + comment
        else:
            before_comment, comment = line, ""

        prefix, imports_part = before_comment.split("import", 1)
        items = [item.strip() for item in imports_part.split(",") if item.strip()]

        if "UTC" not in items:
            continue

        items = [item for item in items if item != "UTC"]
        if "timezone" not in items:
            items.append("timezone")

        new_import = f"{prefix}import {', '.join(items)}"
        if comment:
            new_import = f"{new_import} {comment}"

        lines[idx] = new_import

        if TARGET not in text:
            lines.insert(idx + 1, TARGET)

        modified = True
        break

    if modified:
        path.write_text("\n".join(lines) + "\n")
        updated_files.append(str(path.relative_to(ROOT)))

if updated_files:
    print("Updated", len(updated_files), "files:")
    for rel_path in updated_files:
        print(" -", rel_path)
else:
    print("No files updated.")
