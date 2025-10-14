"""
Dev override service for entitlement bypass during QA/testing
"""

import os


def dev_entitled(user_id: int, feature: str) -> bool:
    """
    Check if user/feature combination is entitled via dev override.

    Args:
        user_id: User ID to check
        feature: Feature name to check

    Returns:
        True if entitled via dev override, False otherwise
    """
    # Allow-all kill switch (use only in staging; careful in prod)
    if os.getenv("ENTITLEMENTS_ALLOW_ALL", "").strip().lower() in {"1", "true", "yes"}:
        return True

    allow = {s.strip() for s in os.getenv("ENTITLEMENTS_ALLOWLIST", "").split(",") if s.strip()}
    feats = {s.strip() for s in os.getenv("ENTITLEMENTS_FEATURES", "").split(",") if s.strip()}
    return str(user_id) in allow and (not feats or feature in feats)
