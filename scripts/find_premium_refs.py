#!/usr/bin/env python3
# find_premium_refs.py
# Search recursively for "is_premium" or "premium_only" and print file:line#:matched-text

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent  # project root (adjust if needed)
PATTERNS = ("is_premium", "premium_only")  # strings to look for
IGNORES = {".git", ".venv", "__pycache__"}  # directories to skip


def search_file(path: Path):
    """Yield (line_number, line_text) for each matching line in a single file."""
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            for n, line in enumerate(fh, 1):  # 1-based line numbers
                if any(pat in line for pat in PATTERNS):
                    yield n, line.rstrip("\n")
    except (IsADirectoryError, PermissionError):
        pass  # skip things we can’t read


def walk_tree(root: Path):
    for p in root.rglob("*"):
        # skip directories we don’t care about
        if any(part in IGNORES for part in p.parts):
            continue
        if p.is_file():
            for n, text in search_file(p):
                print(f"{p}:{n}:{text}")


if __name__ == "__main__":
    walk_tree(ROOT_DIR)
