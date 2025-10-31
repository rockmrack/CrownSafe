"""Script to remove baby/recall router registrations from main_crownsafe.py."""

import re


def remove_router_blocks(content):
    """Remove recall alert, recall search, recall detail, and baby feature router blocks."""
    # Pattern 1: Remove Recall Alert System block
    pattern1 = r'# Include Recall Alert System\ntry:.*?except Exception as e:\n    logging\.error\(f"Failed to register recall alert system: \{e\}"\)\n\n'  # noqa: E501
    content = re.sub(pattern1, "", content, flags=re.DOTALL)

    # Pattern 2: Remove Recall Search System block
    pattern2 = r'# Include Recall Search System\ntry:.*?except Exception as e:\n    logging\.error\(f"Failed to register recall search system: \{e\}"\)\n\n'  # noqa: E501
    content = re.sub(pattern2, "", content, flags=re.DOTALL)

    # Pattern 3: Remove recall detail endpoints block
    pattern3 = r'# Include recall detail endpoints\ntry:.*?except Exception as e:\n    logging\.error\(f"Failed to register recall detail endpoints: \{e\}"\)\n\n'  # noqa: E501
    content = re.sub(pattern3, "", content, flags=re.DOTALL)

    # Pattern 4: Remove Baby Safety Features block
    pattern4 = r"# Include Baby Safety Features.*?\ntry:.*?except \(ImportError, FileNotFoundError\) as e:.*?# Continue without baby features.*?\n\n"  # noqa: E501
    return re.sub(pattern4, "", content, flags=re.DOTALL)



if __name__ == "__main__":
    import os

    # Get the script's directory and navigate to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    file_path = os.path.join(project_root, "api", "main_crownsafe.py")

    # Read file
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"Original file size: {len(content)} chars")

    # Remove router blocks
    new_content = remove_router_blocks(content)

    print(f"New file size: {len(new_content)} chars")
    print(f"Removed: {len(content) - len(new_content)} chars")

    # Write to a new file in the scripts directory
    output_filename = "main_crownsafe_cleaned.py"
    output_path = os.path.join(script_dir, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ Cleaned content written to: {output_path}")
    print("Please manually copy this file to api/main_crownsafe.py")
