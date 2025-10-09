# core/chat_budget.py
import os


def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except Exception:
        return default


# Per-request total target (p95)
TOTAL_BUDGET_SEC = _f("BS_CHAT_TOTAL_BUDGET_SEC", 2.8)

# Component budgets
ROUTER_TIMEOUT_SEC = _f("BS_CHAT_ROUTER_TIMEOUT_SEC", 0.30)
TOOL_TIMEOUT_SEC = _f("BS_CHAT_TOOL_TIMEOUT_SEC", 2.00)
SYNTH_TIMEOUT_SEC = _f("BS_CHAT_SYNTH_TIMEOUT_SEC", 1.50)
