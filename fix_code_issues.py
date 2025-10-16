"""
Script to fix all remaining code quality issues in babyshield-backend
Fixes: unused imports, unused loop variables, long lines, exception chaining
"""

import re

from pathlib import Path


def fix_unused_loop_variables(content):
    """Fix unused loop variables by prefixing with underscore"""
    # Pattern: for i in range(...):
    content = re.sub(r"(\s+for\s+)([a-z_][a-z0-9_]*)\s+(in\s+range\([^)]+\):)", r"\1_\2 \3", content)
    # Pattern: for i, var in enumerate(...):
    content = re.sub(
        r"(\s+for\s+)([a-z_][a-z0-9_]*),\s*([a-z_][a-z0-9_]*)\s+(in\s+enumerate)",
        r"\1\2, _\3 \4",
        content,
    )
    return content


def fix_long_comment_line(content):
    """Fix the specific long line in auth_endpoints.py"""
    content = content.replace(
        '        # response.set_cookie("access_token", access_token, httponly=True, secure=True, samesite="lax")',
        "        # response.set_cookie(\n"
        '        #     "access_token", access_token, httponly=True,\n'
        '        #     secure=True, samesite="lax"\n'
        "        # )",
    )
    return content


def fix_exception_chaining(content):
    """Add 'from None' to raise statements in except clauses"""
    # Find raise HTTPException within except blocks and add from None
    pattern = r"(except\s+\w+.*?:.*?)(raise\s+HTTPException\([^)]+\))"

    def add_from_none(match):
        prefix = match.group(1)
        raise_stmt = match.group(2)
        # Only add if 'from' not already present
        if "from " not in raise_stmt:
            return f"{prefix}{raise_stmt.rstrip()} from None"
        return match.group(0)

    content = re.sub(pattern, add_from_none, content, flags=re.DOTALL)
    return content


def remove_unused_imports(file_path, unused_imports):
    """Remove specified unused imports from a file"""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        skip = False
        for unused in unused_imports:
            if f"import {unused}" in line or f"{unused}," in line:
                # Check if it's the only import on the line
                if line.strip().startswith("from") or line.strip().startswith("import"):
                    # Remove the unused import
                    for u in unused_imports:
                        line = line.replace(f", {u}", "")
                        line = line.replace(f"{u}, ", "")
                        line = line.replace(f"import {u}", "")
                    # If line is now empty or just whitespace, skip it
                    if not line.strip() or line.strip() in ["from", "import", ","]:
                        skip = True
                        break
        if not skip:
            new_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


# Fix files
files_to_fix = [
    "api/auth_endpoints.py",
    "agents/recall_data_agent/connectors.py",
    "agents/recall_data_agent/agent_logic.py",
    "tests/security/test_security_vulnerabilities.py",
    "tests/integration/test_api_endpoints.py",
]

for file_path in files_to_fix:
    full_path = Path(file_path)
    if not full_path.exists():
        print(f"Skipping {file_path} - file not found")
        continue

    print(f"Fixing {file_path}...")

    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Apply fixes
    content = fix_unused_loop_variables(content)
    content = fix_long_comment_line(content)
    content = fix_exception_chaining(content)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  ✓ Fixed {file_path}")

# Remove unused imports
print("\nRemoving unused imports...")
remove_unused_imports("agents/recall_data_agent/connectors.py", ["Optional"])
remove_unused_imports("agents/recall_data_agent/agent_logic.py", ["List"])

print("\n✅ All fixes applied!")
print("\nRun 'ruff check .' to verify remaining issues.")
