#!/usr/bin/env python3
"""
Temporary script to comment out legacy router registrations for Crown Safe migration.
"""

import re


def comment_out_router_blocks(file_path):
    """Comment out the 5 legacy BabyShield router registration blocks."""

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern to match each router registration block
    # These blocks all have similar structure: try/except with app.include_router

    replacements = [
        # 1. Recall Alert System
        (
            r'# Include Recall Alert System\ntry:\n    from api\.recall_alert_system import recall_alert_router\n\n    app\.include_router\(recall_alert_router\)\n    logging\.info\(".*?Recall Alert System registered"\)\nexcept Exception as e:\n    logging\.error\(f"Failed to register recall alert system: \{e\}"\)',  # noqa: E501
            '# REMOVED FOR CROWN SAFE: Recall Alert System is BabyShield-specific (baby product recalls)\n# # Include Recall Alert System\n# try:\n#     from api.recall_alert_system import recall_alert_router\n#\n#     app.include_router(recall_alert_router)\n#     # logging.info("Recall Alert System registered")\n# except Exception as e:\n#     logging.error(f"Failed to register recall alert system: {e}")',  # noqa: E501
        ),
        # 2. Recall Search System
        (
            r'# Include Recall Search System\ntry:\n    from api\.recalls_endpoints import router as recalls_router\n\n    app\.include_router\(recalls_router\)\n    logging\.info\(".*?Recall Search System registered"\)\nexcept Exception as e:\n    logging\.error\(f"Failed to register recall search system: \{e\}"\)',  # noqa: E501
            '# REMOVED FOR CROWN SAFE: Recall Search System is BabyShield-specific (baby product recalls)\n# # Include Recall Search System\n# try:\n#     from api.recalls_endpoints import router as recalls_router\n#\n#     app.include_router(recalls_router)\n#     # logging.info("Recall Search System registered")\n# except Exception as e:\n#     logging.error(f"Failed to register recall search system: {e}")',  # noqa: E501
        ),
        # 3. Recall Detail endpoints
        (
            r'# Include recall detail endpoints\ntry:\n    from api\.recall_detail_endpoints import router as recall_detail_router\n\n    app\.include_router\(recall_detail_router\)\n    logging\.info\(".*?Recall detail endpoints registered"\)\nexcept Exception as e:\n    logging\.error\(f"Failed to register recall detail endpoints: \{e\}"\)',  # noqa: E501
            '# REMOVED FOR CROWN SAFE: Recall Detail endpoints are BabyShield-specific (baby product recalls)\n# # Include recall detail endpoints\n# try:\n#     from api.recall_detail_endpoints import router as recall_detail_router\n#\n#     app.include_router(recall_detail_router)\n#     # logging.info("Recall detail endpoints registered")\n# except Exception as e:\n#     logging.error(f"Failed to register recall detail endpoints: {e}")',  # noqa: E501
        ),
        # 4. Premium Features
        (
            r'# Include Premium Features \(Pregnancy & Allergy\) endpoints - LEGACY BABY CODE\ntry:\n    from api\.premium_features_endpoints import router as premium_router\n\n    app\.include_router\(premium_router\)\n    logging\.info\("Premium Features endpoints registered"\)\nexcept ImportError as e:\n    logging\.warning\(f"Premium features \(baby allergy checking\) not available: \{e\}"\)\n# logging\.info\(".*?Premium Features.*?"\)',  # noqa: E501
            '# REMOVED FOR CROWN SAFE: Premium Features are BabyShield-specific (pregnancy & baby allergy checking)\n# # Include Premium Features (Pregnancy & Allergy) endpoints - LEGACY BABY CODE\n# try:\n#     from api.premium_features_endpoints import router as premium_router\n#\n#     app.include_router(premium_router)\n#     logging.info("Premium Features endpoints registered")\n# except ImportError as e:\n#     logging.warning(f"Premium features (baby allergy checking) not available: {e}")',  # noqa: E501
        ),
        # 5. Baby Safety Features
        (
            r'# Include Baby Safety Features \(Alternatives, Notifications, Reports\) endpoints\ntry:\n    from api\.baby_features_endpoints import router as baby_router\n\n    app\.include_router\(baby_router\)\n    logging\.info\(".*?Baby Safety Features.*?"\)\nexcept \(ImportError, FileNotFoundError\) as e:\n    logging\.warning\(f"Baby Safety Features not available \(missing dependency pylibdmtx\): \{e\}"\)\n    # Continue without baby features - they\'re optional',  # noqa: E501
            '# REMOVED FOR CROWN SAFE: Baby Safety Features are BabyShield-specific (family members, pregnancy tracking)\n# # Include Baby Safety Features (Alternatives, Notifications, Reports) endpoints\n# try:\n#     from api.baby_features_endpoints import router as baby_router\n#\n#     app.include_router(baby_router)\n#     # logging.info("Baby Safety Features endpoints registered")\n# except (ImportError, FileNotFoundError) as e:\n#     logging.warning(f"Baby Safety Features not available (missing dependency pylibdmtx): {e}")\n#     # Continue without baby features - they\'re optional',  # noqa: E501
        ),
    ]

    # Apply each replacement
    modified = content
    for pattern, replacement in replacements:
        modified = re.sub(pattern, replacement, modified, flags=re.MULTILINE)

    # Write back to a different file handle
    with open(file_path, "w", encoding="utf-8", newline="\n") as f_out:
        f_out.write(modified)

    print("✅ Commented out 5 legacy router registrations")


if __name__ == "__main__":
    comment_out_router_blocks("api/main_crownsafe.py")
