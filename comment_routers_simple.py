#!/usr/bin/env python3
"""Simple script to comment out legacy router registrations."""


def comment_routers():
    # Read the file
    with open("api/main_crownsafe.py", "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Track if we're inside a block to comment
    in_recall_alert_block = False
    in_recall_search_block = False
    in_recall_detail_block = False
    in_premium_block = False
    in_baby_block = False

    new_lines = []
    skip_next = 0

    for i, line in enumerate(lines):
        if skip_next > 0:
            skip_next -= 1
            continue

        # Check for start of blocks to comment
        if "# Include Recall Alert System" in line and "REMOVED FOR CROWN SAFE" not in line:
            new_lines.append(
                "# REMOVED FOR CROWN SAFE: Recall Alert System is BabyShield-specific (baby product recalls)\n"
            )
            new_lines.append("# " + line)
            in_recall_alert_block = True
            continue
        elif "# Include Recall Search System" in line and "REMOVED FOR CROWN SAFE" not in line:
            new_lines.append(
                "# REMOVED FOR CROWN SAFE: Recall Search System is BabyShield-specific (baby product recalls)\n"
            )
            new_lines.append("# " + line)
            in_recall_search_block = True
            continue
        elif "# Include recall detail endpoints" in line and "REMOVED FOR CROWN SAFE" not in line:
            new_lines.append(
                "# REMOVED FOR CROWN SAFE: Recall Detail endpoints are BabyShield-specific (baby product recalls)\n"
            )
            new_lines.append("# " + line)
            in_recall_detail_block = True
            continue
        elif "# Include Premium Features" in line and "REMOVED FOR CROWN SAFE" not in line:
            new_lines.append(
                "# REMOVED FOR CROWN SAFE: Premium Features are BabyShield-specific (pregnancy & baby allergy checking)\n"
            )
            new_lines.append("# " + line)
            in_premium_block = True
            continue
        elif "# Include Baby Safety Features" in line and "REMOVED FOR CROWN SAFE" not in line:
            new_lines.append(
                "# REMOVED FOR CROWN SAFE: Baby Safety Features are BabyShield-specific (family members, pregnancy tracking)\n"
            )
            new_lines.append("# " + line)
            in_baby_block = True
            continue

        # If we're in a block, comment out lines until we hit a blank line followed by another block
        if any(
            [in_recall_alert_block, in_recall_search_block, in_recall_detail_block, in_premium_block, in_baby_block]
        ):
            # Check if this is the end of the block (next comment or blank line + comment)
            if line.strip().startswith("#") and not line.strip().startswith("# ") and line.strip() != "#":
                # Hit next section comment - exit block mode
                in_recall_alert_block = False
                in_recall_search_block = False
                in_recall_detail_block = False
                in_premium_block = False
                in_baby_block = False
                new_lines.append(line)
            elif line.strip() and not line.strip().startswith("#"):
                # Non-empty, non-comment line - comment it
                new_lines.append("# " + line)
            else:
                # Empty or already commented
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Write back
    output_path = "api/main_crownsafe_modified.py"
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"✅ Created modified file: {output_path}")
    print("Review the changes, then rename to main_crownsafe.py")


if __name__ == "__main__":
    comment_routers()
