# core/metrics.py
from __future__ import annotations
import os

try:
    from prometheus_client import Counter, Histogram  # type: ignore

    PROM = True
except ImportError:
    # prometheus_client is optional - graceful fallback
    PROM = False

if PROM:
    CHAT_REQ = Counter(
        "bs_chat_requests_total", "Chat requests", ["endpoint", "intent", "ok", "circuit"]
    )
    CHAT_LAT = Histogram(
        "bs_chat_total_latency_ms",
        "Total latency (ms)",
        buckets=(50, 100, 200, 400, 800, 1600, 3200, 6400),
    )
    TOOL_LAT = Histogram(
        "bs_chat_tool_latency_ms",
        "Tool latency (ms)",
        ["intent"],
        buckets=(10, 50, 100, 200, 400, 800, 1600),
    )
    SYN_LAT = Histogram(
        "bs_chat_synth_latency_ms", "Synth latency (ms)", buckets=(50, 100, 200, 400, 800, 1600)
    )
    CHAT_FALLBACK = Counter(
        "bs_chat_fallback_total", "LLM/template fallback used", ["endpoint", "reason"]
    )
    CHAT_BLOCKED = Counter(
        "bs_chat_blocked_total", "Requests blocked by feature flag", ["endpoint"]
    )
    EXPLAIN_FB = Counter("bs_explain_feedback_total", "Explain feedback", ["helpful", "reason"])
    ALT_SHOWN = Counter("bs_alternatives_shown_total", "Alternatives shown in responses", ["count"])
    ALT_CLICKED = Counter("bs_alternative_clicked_total", "Alternative clicked", ["id"])
    CHAT_UNCLEAR = Counter("bs_chat_unclear_total", "Unclear-intent responses")
    CHAT_EMERG = Counter("bs_chat_emergency_total", "Emergency-path responses")
else:

    class _N:
        def labels(self, *_a, **_k):
            return self

        def observe(self, *_a, **_k):
            pass

        def inc(self, *_a, **_k):
            pass

    CHAT_REQ = (
        CHAT_LAT
    ) = (
        TOOL_LAT
    ) = (
        SYN_LAT
    ) = (
        CHAT_FALLBACK
    ) = CHAT_BLOCKED = EXPLAIN_FB = ALT_SHOWN = ALT_CLICKED = CHAT_UNCLEAR = CHAT_EMERG = _N()


def inc_req(endpoint: str, intent: str, ok: bool, circuit: bool):
    CHAT_REQ.labels(endpoint, intent, "1" if ok else "0", "1" if circuit else "0").inc()


def obs_total(ms: int):
    CHAT_LAT.observe(float(ms))


def obs_tool(intent: str, ms: int):
    TOOL_LAT.labels(intent).observe(float(ms))


def obs_synth(ms: int):
    SYN_LAT.observe(float(ms))


def inc_fallback(endpoint: str, reason: str):
    CHAT_FALLBACK.labels(endpoint, reason).inc()


def inc_blocked(endpoint: str):
    CHAT_BLOCKED.labels(endpoint).inc()


def inc_explain_feedback(helpful: bool, reason: str | None):
    EXPLAIN_FB.labels("1" if helpful else "0", reason or "none").inc()


def inc_alternatives_shown(count: int):
    """Record how many alternatives were shown (0, 1, 2, 3+)"""
    count_bucket = "3+" if count >= 3 else str(count)
    ALT_SHOWN.labels(count_bucket).inc()


def inc_alternative_clicked(alt_id: str):
    """Record when a specific alternative is clicked"""
    ALT_CLICKED.labels(alt_id).inc()


def inc_unclear():
    """Record unclear intent response"""
    CHAT_UNCLEAR.inc()


def inc_emergency():
    """Record emergency path response"""
    CHAT_EMERG.inc()
