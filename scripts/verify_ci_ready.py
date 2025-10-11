#!/usr/bin/env python3
"""
Verification script to confirm all fixes are in place
Run this locally to verify the setup before CI runs
"""

import os
import sys
from pathlib import Path

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def check(condition, success_msg, fail_msg):
    """Check a condition and print result"""
    if condition:
        print(f"{GREEN}✓{RESET} {success_msg}")
        return True
    else:
        print(f"{RED}✗{RESET} {fail_msg}")
        return False


def main():
    """Run all verification checks"""
    print("=" * 60)
    print("BabyShield Backend - Pre-CI Verification")
    print("=" * 60)
    print()

    all_passed = True
    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent

    # Check 1: Migration file exists
    print("📋 Checking Database Migrations...")
    migration_file = (
        project_root
        / "db"
        / "migrations"
        / "versions"
        / "2024_08_22_0100_001_create_recalls_enhanced_table.py"
    )
    all_passed &= check(
        migration_file.exists(),
        f"Migration file exists: {migration_file.name}",
        f"Migration file NOT found: {migration_file}",
    )

    # Check 2: Alembic config exists
    alembic_ini = project_root / "db" / "alembic.ini"
    all_passed &= check(
        alembic_ini.exists(),
        f"Alembic config exists: {alembic_ini}",
        f"Alembic config NOT found: {alembic_ini}",
    )

    # Check 3: Init script exists
    init_script = project_root / "scripts" / "init_test_database.py"
    all_passed &= check(
        init_script.exists(),
        f"Init script exists: {init_script.name}",
        f"Init script NOT found: {init_script}",
    )

    # Check 4: Init script uses correct path
    if init_script.exists():
        content = init_script.read_text()
        uses_correct_path = "db/alembic.ini" in content
        all_passed &= check(
            uses_correct_path,
            "Init script uses correct Alembic path (db/alembic.ini)",
            "Init script does NOT use correct path",
        )

    # Check 5: Migration creates recalls_enhanced table
    if migration_file.exists():
        try:
            content = migration_file.read_text(encoding="utf-8")
            creates_table = '"recalls_enhanced"' in content and "op.create_table" in content
            all_passed &= check(
                creates_table,
                "Migration creates recalls_enhanced table",
                "Migration does NOT create recalls_enhanced table",
            )
        except UnicodeDecodeError:
            print(f"{YELLOW}⚠{RESET} Could not read migration file (encoding issue)")

    # Check 6: Formatting check
    print()
    print("🎨 Checking Code Formatting...")
    try:
        import subprocess

        result = subprocess.run(
            ["ruff", "format", ".", "--check"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
        )
        all_passed &= check(
            result.returncode == 0,
            "All files properly formatted (ruff check passed)",
            f"Files need formatting: {result.stdout}",
        )
    except FileNotFoundError:
        print(f"{YELLOW}⚠{RESET} ruff not found, skipping formatting check")

    # Check 7: Git status
    print()
    print("📦 Checking Git Status...")
    try:
        import subprocess

        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=str(project_root)
        )
        is_clean = len(result.stdout.strip()) == 0
        all_passed &= check(
            is_clean,
            "Working directory is clean (no uncommitted changes)",
            f"Uncommitted changes detected:\n{result.stdout}",
        )
    except FileNotFoundError:
        print(f"{YELLOW}⚠{RESET} git not found, skipping status check")

    # Check 8: Branch sync
    print()
    print("🔄 Checking Branch Synchronization...")
    try:
        import subprocess

        # Get local main commit
        local_result = subprocess.run(
            ["git", "rev-parse", "main"], capture_output=True, text=True, cwd=str(project_root)
        )
        local_commit = local_result.stdout.strip()

        # Get remote main commit
        remote_result = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
        )
        remote_commit = remote_result.stdout.strip()

        is_synced = local_commit == remote_commit
        all_passed &= check(
            is_synced,
            f"Local and remote main are synced ({local_commit[:7]})",
            f"Local ({local_commit[:7]}) differs from remote ({remote_commit[:7]})",
        )
    except FileNotFoundError:
        print(f"{YELLOW}⚠{RESET} git not found, skipping sync check")

    # Final summary
    print()
    print("=" * 60)
    if all_passed:
        print(f"{GREEN}✅ ALL CHECKS PASSED!{RESET}")
        print("The repository is ready for CI. Next push should succeed.")
    else:
        print(f"{RED}❌ SOME CHECKS FAILED{RESET}")
        print("Please address the issues above before pushing to CI.")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
