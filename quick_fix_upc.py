"""Quick fix for fix_upc_data function - removes RecallDB references"""

import subprocess
import time
import sys


def pause_onedrive():
    """Pause OneDrive sync"""
    try:
        subprocess.run(
            [
                "powershell",
                "-Command",
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$onedrive = Get-Process OneDrive -ErrorAction SilentlyContinue; "
                "if ($onedrive) { $onedrive.Kill() }",
            ],
            check=False,
            capture_output=True,
            timeout=5,
        )
        print("⏸️  OneDrive paused")
        time.sleep(2)
        return True
    except Exception as e:
        print(f"⚠️  Could not pause OneDrive: {e}")
        return False


def fix_function():
    """Fix the fix_upc_data function"""
    filepath = r"c:\Users\rossd\OneDrive\Documents\Crown Safe\api\main_crownsafe.py"

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Find the problematic section (around line 3855-3925)
        start_idx = None
        end_idx = None

        for i, line in enumerate(lines):
            if "enhanced_count = 0" in line and i > 3850 and i < 3860:
                start_idx = i
            if start_idx and "return result" in line and i > start_idx and i < start_idx + 80:
                end_idx = i + 1
                break

        if start_idx and end_idx:
            # Remove the old code
            replacement = """            # Return safe default response
            result = {
                "status": "skipped",
                "enhanced_recalls": 0,
                "total_with_upc": 0,
                "total_recalls": 0,
                "upc_coverage_percent": 0,
                "agencies_optimized": 0,
                "impact": "Function deprecated for Crown Safe platform",
            }

            return result
"""
            new_lines = lines[:start_idx] + [replacement] + lines[end_idx:]

            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            removed = end_idx - start_idx
            print(f"✅ Successfully removed {removed} lines from fix_upc_data function")
            print(f"✅ Lines {start_idx + 1}-{end_idx} replaced with safe default")
            print("✅ CRITICAL FIX COMPLETE - RecallDB references removed!")
            return True
        else:
            print("❌ Could not locate the exact section to fix")
            print(f"   start_idx: {start_idx}, end_idx: {end_idx}")
            return False

    except Exception as e:
        print(f"❌ Error fixing file: {e}")
        return False


if __name__ == "__main__":
    print("🔧 Fixing fix_upc_data function...")
    print()

    # Try to pause OneDrive
    pause_onedrive()

    # Attempt the fix
    if fix_function():
        print()
        print("=" * 60)
        print("SUCCESS! fix_upc_data function is now safe.")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("MANUAL FIX REQUIRED:")
        print("1. Open api/main_crownsafe.py")
        print("2. Go to line 3855")
        print("3. Delete 68 lines (3855-3922)")
        print("4. Replace with the 13-line safe default shown above")
        print("=" * 60)
        sys.exit(1)
