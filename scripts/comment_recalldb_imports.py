#!/usr/bin/env python3
"""Comment out RecallDB imports in main_crownsafe.py
Handles UTF-8 encoding properly
"""

import sys


def comment_out_imports():
    """Comment out all RecallDB imports in main_crownsafe.py"""
    file_path = "api/main_crownsafe.py"

    # Target line numbers (1-indexed from grep results)
    target_lines = [2726, 2880, 3251, 3315, 3444, 4059]

    print(f"Reading {file_path}...")

    try:
        # Read file with UTF-8 encoding
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        print(f"Total lines: {len(lines)}")
        modified_count = 0

        # Comment out RecallDB imports at specific lines (convert to 0-indexed)
        for line_num_1indexed in target_lines:
            line_num = line_num_1indexed - 1  # Convert to 0-indexed

            if line_num < len(lines):
                line = lines[line_num]

                # Check if line contains RecallDB import and isn't already commented
                if "from core_infra.database import" in line and "RecallDB" in line:
                    if not line.strip().startswith("#"):
                        # Preserve indentation and comment out
                        indent = len(line) - len(line.lstrip())
                        lines[line_num] = " " * indent + "# " + line.lstrip()
                        modified_count += 1
                        print(f"✅ Commented line {line_num_1indexed}: {line.strip()[:60]}...")
                    else:
                        print(f"⏭️  Line {line_num_1indexed} already commented")
                else:
                    print(f"⚠️  Line {line_num_1indexed} doesn't match expected pattern")
            else:
                print(f"❌ Line {line_num_1indexed} out of range")

        if modified_count > 0:
            # Write back
            print(f"\nWriting changes back to {file_path}...")
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            print(f"✅ Successfully commented out {modified_count} RecallDB imports")
            return True
        else:
            print("⚠️  No changes made - all imports already commented or not found")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = comment_out_imports()
    sys.exit(0 if success else 1)
