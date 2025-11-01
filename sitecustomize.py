"""Runtime compatibility helpers for environments running Python < 3.11.

This module is automatically imported by the Python interpreter when it is
present on the import path. We use it to backfill a handful of standard library
APIs that the BabyShield codebase expects but which are only available in newer
Python releases.
"""

from __future__ import annotations

import datetime as _datetime
import typing as _typing
from datetime import timezone as _timezone

# Python 3.11 exposes datetime.UTC. Earlier versions only provide timezone.utc.
if not hasattr(_datetime, "UTC"):
    _datetime.UTC = _timezone.utc  # type: ignore[attr-defined]

# Python 3.11 adds typing.Never. Provide a best-effort fallback when running on
# Python 3.10 so imports continue to work at runtime.
if not hasattr(_typing, "Never"):
    try:
        from typing_extensions import Never as _never_type  # type: ignore
    except Exception:  # pragma: no cover - typing_extensions may be absent
        from typing import TypeVar

        Never = TypeVar("Never")
        _never_type = Never

    _typing.Never = _never_type  # type: ignore[attr-defined]
