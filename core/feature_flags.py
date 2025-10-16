# core/feature_flags.py
from __future__ import annotations
import os
import hashlib
from typing import Optional


def env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


FEATURE_CHAT_ENABLED = env_bool("BS_FEATURE_CHAT_ENABLED", False)  # global kill switch
FEATURE_CHAT_ROLLOUT_PCT = env_float("BS_FEATURE_CHAT_ROLLOUT_PCT", 0.10)  # 10% by default


def _bucket(user_key: str) -> float:
    h = hashlib.sha1(user_key.encode("utf-8")).hexdigest()
    # 0..9999 -> 0.0000..0.9999
    return int(h[:4], 16) / 65535.0


def chat_enabled_for(user_id: Optional[str], device_id: Optional[str] = None) -> bool:
    if not FEATURE_CHAT_ENABLED:
        return False
    # sticky key (prefer user_id, else device_id, else off)
    key = str(user_id or device_id or "")
    if not key:
        return False
    return _bucket(key) < max(0.0, min(1.0, FEATURE_CHAT_ROLLOUT_PCT))
