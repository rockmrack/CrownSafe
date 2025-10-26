#!/usr/bin/env python3
"""
Disable baby/recall code in main_crownsafe.py
This script comments out all baby/recall import and router registration lines
"""

import re


def disable_baby_recall_code():
    main_file = r"c:\Users\rossd\OneDrive\Documents\Crown Safe\api\main_crownsafe.py"

    with open(main_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Patterns to disable
    patterns_to_comment = [
        # Recall alert system
        (
            r"(\n# Include Recall Alert System\ntry:\n    from api\.recall_alert_system import recall_alert_router\n\n    app\.include_router\(recall_alert_router\)\n    logging\.info\([^\n]+\)\nexcept Exception as e:\n    logging\.error\([^\n]+\))",
            r"\n# ===== LEGACY BABY RECALL CODE - DISABLED FOR CROWN SAFE =====\n# Include Recall Alert System\n# try:\n#     from api.recall_alert_system import recall_alert_router\n#\n#     app.include_router(recall_alert_router)\n#     logging.info([DISABLED])\n# except Exception as e:\n#     logging.error([DISABLED])",
        ),
        # Recall search system
        (
            r"(\n# Include Recall Search System\ntry:\n    from api\.recalls_endpoints import router as recalls_router\n\n    app\.include_router\(recalls_router\)\n    logging\.info\([^\n]+\)\nexcept Exception as e:\n    logging\.error\([^\n]+\))",
            r"\n# Include Recall Search System\n# try:\n#     from api.recalls_endpoints import router as recalls_router\n#\n#     app.include_router(recalls_router)\n#     logging.info([DISABLED])\n# except Exception as e:\n#     logging.error([DISABLED])\n# ===== END LEGACY BABY RECALL CODE =====",
        ),
        # Recall detail endpoints
        (
            r"(\n# Include recall detail endpoints\ntry:\n    from api\.recall_detail_endpoints import router as recall_detail_router\n\n    app\.include_router\(recall_detail_router\)\n    logging\.info\([^\n]+\)\nexcept Exception as e:\n    logging\.error\([^\n]+\))",
            r"\n# ===== LEGACY BABY RECALL CODE - DISABLED FOR CROWN SAFE =====\n# Include recall detail endpoints\n# try:\n#     from api.recall_detail_endpoints import router as recall_detail_router\n#\n#     app.include_router(recall_detail_router)\n#     logging.info([DISABLED])\n# except Exception as e:\n#     logging.error([DISABLED])\n# ===== END LEGACY BABY RECALL CODE =====",
        ),
        # Premium features
        (
            r'(\ntry:\n    from api\.premium_features_endpoints import router as premium_router\n\n    app\.include_router\(premium_router\)\n    logging\.info\("Premium Features endpoints registered"\)\nexcept ImportError as e:\n    logging\.warning\([^\n]+\))',
            r'\n# ===== LEGACY BABY CODE - DISABLED FOR CROWN SAFE =====\n# try:\n#     from api.premium_features_endpoints import router as premium_router\n#\n#     app.include_router(premium_router)\n#     logging.info("Premium Features endpoints registered")\n# except ImportError as e:\n#     logging.warning([DISABLED])',
        ),
        # Baby features
        (
            r"(\ntry:\n    from api\.baby_features_endpoints import router as baby_router\n\n    app\.include_router\(baby_router\)\n    logging\.info\([^\n]+Baby[^\n]+\)\nexcept \(ImportError, FileNotFoundError\) as e:\n    logging\.warning\([^\n]+\)\n    # Continue without baby features[^\n]*)",
            r"\n# try:\n#     from api.baby_features_endpoints import router as baby_router\n#\n#     app.include_router(baby_router)\n#     logging.info([DISABLED Baby])\n# except (ImportError, FileNotFoundError) as e:\n#     logging.warning([DISABLED])\n#     # Continue without baby features\n# ===== END LEGACY BABY CODE =====",
        ),
    ]

    for pattern, replacement in patterns_to_comment:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    # Backup original
    with open(main_file + ".backup", "w", encoding="utf-8") as f:
        f.write(content)

    # Write modified
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(content)

    print("✓ Disabled baby/recall code in main_crownsafe.py")
    print("✓ Backup saved to main_crownsafe.py.backup")


if __name__ == "__main__":
    disable_baby_recall_code()
