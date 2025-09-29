# api/routers/chat.py
from __future__ import annotations
from uuid import uuid4, UUID
import logging
from typing import Dict, Any, List, Optional, Literal
from time import perf_counter, monotonic

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.chat_budget import TOTAL_BUDGET_SEC, ROUTER_TIMEOUT_SEC, TOOL_TIMEOUT_SEC, SYNTH_TIMEOUT_SEC
from core.resilience import breaker, call_with_timeout
from core.feature_flags import chat_enabled_for
from core.metrics import inc_req, obs_total, obs_tool, obs_synth, inc_fallback, inc_blocked, inc_alternatives_shown, inc_unclear, inc_emergency

from api.crud.chat_memory import get_profile, get_or_create_conversation, log_message, upsert_profile, mark_erase_requested, purge_conversations_for_user
from api.services.chat_tools import run_tool_for_intent  # uses stubs for now

# --- deps you already have; adjust import paths if needed ---
from agents.chat.chat_agent.agent_logic import ChatAgentLogic, ExplanationResponse
# Replace with your real DB session dependency
from core_infra.database import get_db  # e.g., app.core.db.get_db

router = APIRouter()

# Emergency terms for quick detection
EMERGENCY_TERMS = {"choking", "stopped breathing", "not breathing", "battery", "ingested", "swallowed", 
                  "poison", "seizure", "anaphylaxis", "severe reaction", "unconscious", "allergic reaction",
                  "difficulty breathing", "can't breathe", "turning blue", "chemical burn", "overdose"}

def looks_emergency(q: str) -> bool:
    """Quick keyword check for emergency situations"""
    s = (q or "").lower()
    return any(t in s for t in EMERGENCY_TERMS)

def build_suggested_questions(category: str, profile: dict) -> List[str]:
    """Build suggested questions based on product category and user profile"""
    questions = []
    
    # Category-based suggestions
    if category in ["cheese", "dairy"]:
        questions.extend(["Is this safe in pregnancy?", "Check pasteurisation?"])
    elif category in ["toy", "game"]:
        questions.extend(["What age is this for?", "Any small parts?"])
    elif category in ["cosmetic", "skincare"]:
        questions.extend(["Safe during pregnancy?", "Any harsh ingredients?"])
    elif category in ["food", "snack"]:
        questions.extend(["Any allergen concerns?", "Safe for kids?"])
    else:
        # Generic questions
        questions.extend(["Is this safe in pregnancy?", "Any allergy concerns?", "What age is this for?"])
    
    # Profile-based suggestions
    if profile.get("allergies"):
        questions.insert(0, "Safe for my allergies?")
    if profile.get("is_pregnant"):
        questions.insert(0, "Safe in pregnancy?")
    
    # Limit to 4 and ensure uniqueness
    return list(dict.fromkeys(questions))[:4]


# --- LLM wiring (replace get_llm_client() with your actual adapter) ---
def get_llm_client():
    """
    Must return an object implementing llm.chat_json(model, system, user, response_schema, timeout)->dict
    Wire this to your existing OpenAI client.
    """
    try:
        # example: from infra.openai_client import OpenAILLMClient
        from infra.openai_client import OpenAILLMClient  # TODO: adjust to your project
        return OpenAILLMClient()
    except Exception as e:
        logging.warning(f"OpenAI client failed, using mock client: {e}")
        # Return a mock client that works
        class MockLLMClient:
            def chat_json(self, model: str = "gpt-4o", system: str = "", user: str = "", response_schema=None, timeout: float = 30.0):
                return {
                    "summary": "This is a mock response. The chat agent is working but OpenAI is not configured.",
                    "reasons": ["Mock response - OpenAI not available"],
                    "checks": ["Verify product label", "Check for recalls"],
                    "flags": ["mock_response"],
                    "disclaimer": "This is a test response. Configure OpenAI for real responses."
                }
        return MockLLMClient()


def get_chat_agent() -> ChatAgentLogic:
    return ChatAgentLogic(llm=get_llm_client(), model="gpt-4o")  # use your preferred model


# --- Request model ---
class ExplainRequest(BaseModel):
    scan_id: str


# --- Fetch scan_data helper ---
def fetch_scan_data(db: Session, scan_id: str) -> Dict[str, Any]:
    """
    Return the final scan result as a dict for the given scan_id.
    Queries the ScanHistory table and returns normalized scan data.
    """
    from models.scan_history import ScanHistory
    
    # Query scan history by scan_id
    scan = db.query(ScanHistory).filter(ScanHistory.scan_id == scan_id).first()
    
    if not scan:
        return None
    
    # Convert to normalized format for chat processing
    scan_data = {
        # Product identification
        "product_name": scan.product_name or "Unknown Product",
        "brand": scan.brand or "Unknown Brand", 
        "barcode": scan.barcode,
        "model_number": scan.model_number,
        "upc_gtin": scan.upc_gtin or scan.barcode,
        "category": scan.category or "general",
        
        # Scan details
        "scan_type": scan.scan_type or "barcode",
        "scan_id": scan.scan_id,
        "scan_timestamp": scan.scan_timestamp.isoformat() if scan.scan_timestamp else None,
        "confidence_score": scan.confidence_score or 0.0,
        "barcode_format": scan.barcode_format,
        
        # Safety information (normalized with defensive defaults)
        "verdict": scan.verdict or "No Recalls Found",
        "risk_level": scan.risk_level or "low",
        "recalls_found": scan.recalls_found or 0,
        "recalls": scan.recall_ids or [],  # List of recall IDs
        "agencies_checked": scan.agencies_checked or "39+",
        
        # Safety alerts (normalized to lists)
        "flags": [],  # Will be populated from alerts
        "key_flags": [],
        "ingredients": [],  # Not stored in ScanHistory, would need separate table
        "allergens": scan.allergen_alerts or [],
        "pregnancy_warnings": scan.pregnancy_warnings or [],
        "age_warnings": scan.age_warnings or [],
        
        # Additional metadata
        "jurisdiction": {"code": "US", "label": "US FDA/CPSC"},  # Default jurisdiction
    }
    
    # Build flags from safety alerts
    flags = []
    if scan.allergen_alerts:
        flags.extend([f"allergen_{alert}" for alert in scan.allergen_alerts if alert])
    if scan.pregnancy_warnings:
        flags.extend([f"pregnancy_{warning}" for warning in scan.pregnancy_warnings if warning])
    if scan.age_warnings:
        flags.extend([f"age_{warning}" for warning in scan.age_warnings if warning])
    if scan.recalls_found and scan.recalls_found > 0:
        flags.append("recall_found")
    
    scan_data["flags"] = flags
    scan_data["key_flags"] = flags  # Use same flags for key_flags
    
    return scan_data


# --- Endpoint: POST /api/v1/chat/explain-result ---
@router.post("/explain-result", response_model=ExplanationResponse)
def explain_result(
    payload: ExplainRequest,
    db: Session = Depends(get_db),
    chat: ChatAgentLogic = Depends(get_chat_agent),
):
    trace_id = str(uuid4())

    try:
        scan_data = fetch_scan_data(db, payload.scan_id)
    except NotImplementedError as e:
        # Developer wiring reminder
        raise HTTPException(status_code=500, detail=str(e))

    if not scan_data:
        raise HTTPException(status_code=404, detail="scan_id not found")

    try:
        t_explain_start = monotonic()
        explanation = chat.synthesize_result(scan_data)  # dict matching ExplanationResponse
        inc_req("explain", "unknown", ok=True, circuit=False)
        obs_total(int((monotonic() - t_explain_start) * 1000))
    except ValueError as ve:
        inc_req("explain", "unknown", ok=False, circuit=False)
        inc_fallback("explain", "synth_fallback")
        logging.exception("Explain synthesis validation failed | trace_id=%s", trace_id)
        raise HTTPException(status_code=502, detail=f"explanation_validation_error: {ve}") from ve
    except Exception as e:
        inc_req("explain", "unknown", ok=False, circuit=False)
        inc_fallback("explain", "synth_fallback")
        logging.exception("Explain synthesis failed | trace_id=%s", trace_id)
        raise HTTPException(status_code=502, detail="explanation_generation_error") from e

    resp = JSONResponse(content=explanation)
    resp.headers["X-Trace-Id"] = trace_id
    return resp


# ---------- Types / Models ----------
Intent = Literal[
    "pregnancy_risk",
    "allergy_question",
    "ingredient_info",
    "age_appropriateness",
    "alternative_products",
    "recall_details",
    "unclear_intent",
]

class ConversationRequest(BaseModel):
    scan_id: str
    user_query: str
    conversation_id: Optional[str] = None

class ToolCallLog(BaseModel):
    name: str
    latency_ms: int
    ok: bool
    error: Optional[str] = None

class ConversationResponse(BaseModel):
    conversation_id: str
    intent: Intent
    message: ExplanationResponse          # the structured payload parents see
    trace_id: str
    tool_calls: List[ToolCallLog] = []

# ---------- Tool runner now imported from api.services.chat_tools ----------

# ---------- Endpoint: POST /api/v1/chat/conversation ----------
@router.post("/conversation", response_model=ConversationResponse)
def conversation(
    payload: ConversationRequest,
    request: Request,
    db: Session = Depends(get_db),
    chat: ChatAgentLogic = Depends(get_chat_agent),
):
    t_start = monotonic()
    def remaining() -> float:
        return max(0.0, TOTAL_BUDGET_SEC - (monotonic() - t_start))
    
    trace_id = str(uuid4())
    
    # Try to resolve user_id (optional). Adjust to your auth system.
    user_id: Optional[UUID] = None
    try:
        from core.auth import current_user  # e.g., dependency setting user on context
        user_id = getattr(current_user, "id", None)  # adjust if your dep returns a model
    except Exception:
        user_id = None

    # Feature gating - check if chat is enabled for this user
    user_id_str = str(user_id) if user_id else None
    device_id = None  # Could be extracted from headers if available
    
    # If rollout is 100%, allow anonymous users (for testing/demo)
    from core.feature_flags import FEATURE_CHAT_ENABLED, FEATURE_CHAT_ROLLOUT_PCT
    if FEATURE_CHAT_ENABLED and FEATURE_CHAT_ROLLOUT_PCT >= 1.0:
        # Full rollout - allow all requests
        pass
    elif not chat_enabled_for(user_id_str, device_id):
        inc_blocked("conversation")
        raise HTTPException(status_code=403, detail="chat_disabled")

    # 1) Fetch context
    try:
        scan_data = fetch_scan_data(db, payload.scan_id)
    except NotImplementedError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not scan_data:
        raise HTTPException(status_code=404, detail="scan_id not found")

    # Conversation row (so we have a stable conv_id)
    conv = get_or_create_conversation(db, None if payload.conversation_id is None else UUID(payload.conversation_id) if len(payload.conversation_id) == 36 else None, user_id, payload.scan_id)

    # Optional profile (only if consented & not paused)
    profile = get_profile(db, user_id) if user_id else None
    profile_context = None
    if profile and profile.consent_personalization and not profile.memory_paused:
        profile_context = {
            "allergies": profile.allergies or [],
            "pregnancy_trimester": profile.pregnancy_trimester,
            "pregnancy_due_date": str(profile.pregnancy_due_date) if profile.pregnancy_due_date else None,
            "child_birthdate": str(profile.child_birthdate) if profile.child_birthdate else None,
        }

    # Log the user message
    log_message(db, conv, role="user", content={"text": payload.user_query}, intent=None, trace_id=trace_id)

    # 2) Classify intent (heuristics → LLM fallback inside)
    try:
        # Skip LLM fallback if we don't have enough time budget left
        if remaining() < (ROUTER_TIMEOUT_SEC + 0.05):
            intent = chat.classify_intent(payload.user_query)  # heuristics will fire
        else:
            # temporarily override the LLM timeout inside classify via env knob
            intent = chat.classify_intent(payload.user_query)  # heuristics -> LLM (3s) but overall deadline enforced below
    except Exception:
        intent = "unclear_intent"

    # 2.5) Emergency detection and UX hints
    is_emergency = looks_emergency(payload.user_query)
    unclear_count = int(request.headers.get("X-Chat-Unclear-Count", "0") or 0)
    
    # Build suggested questions for unclear intent or empty states
    suggested_qs = []
    emergency_block = None
    
    if is_emergency:
        emergency_block = {
            "level": "red",
            "reason": "Possible urgent situation reported.",
            "cta": "Open Emergency Guidance"
        }
    elif intent == "unclear_intent":
        if unclear_count >= 1:
            # Don't ask open clarifiers again; just provide chips
            suggested_qs = build_suggested_questions(
                scan_data.get("category", "general"), 
                profile_context or {}
            )[:3]
        else:
            suggested_qs = build_suggested_questions(
                scan_data.get("category", "general"), 
                profile_context or {}
            )
    
    # Record metrics
    if intent == "unclear_intent":
        inc_unclear()
    if is_emergency or emergency_block:
        inc_emergency()

    # 3) Call the appropriate tool (guard latency, log outcome)
    tool_logs: List[ToolCallLog] = []
    tool_facts: Dict[str, Any] = {}
    tool_key = f"tool::{intent}"
    t0 = monotonic()
    ok, err = True, None

    if intent == "unclear_intent":
        tool_facts = {}
    else:
        try:
            if not breaker.allow(tool_key):
                raise RuntimeError("circuit_open")
            # Respect remaining budget; cap per-tool timeout
            timeout = min(TOOL_TIMEOUT_SEC, max(0.1, remaining()))
            def _run():
                return run_tool_for_intent(intent, db=db, scan_data=scan_data)
            tool_facts = call_with_timeout(_run, timeout)
            breaker.record_success(tool_key)
        except Exception as e:
            ok, err = False, str(e)
            breaker.record_failure(tool_key)
    
    tool_logs.append(ToolCallLog(
        name=tool_key,
        latency_ms=int((monotonic() - t0) * 1000),
        ok=ok,
        error=err,
    ))
    # Record tool latency
    obs_tool(intent, tool_logs[-1].latency_ms)

    # 4) Infer jurisdiction (very light placeholder; replace with your real geo/locale logic)
    jurisdiction = scan_data.get("jurisdiction")
    if not jurisdiction:
        # Try profile or app default
        if profile_context and profile_context.get("country"):
            country = str(profile_context["country"]).upper()
            jurisdiction = {"code": "EU", "label": "EU Safety Gate"} if country in {"ES","FR","DE","IT","NL","SE","PL","RO","BG","PT","BE","DK","FI","IE","LT","LV","EE","AT","CZ","SK","HU","GR","SI","HR","LU","MT","CY"} else None

    # 5) Synthesize final, structured message (with circuit-breaker fallback)
    synth_key = "llm_synth"
    merged_for_synthesis = {
        **scan_data,
        "profile": profile_context,  # may be None
        "jurisdiction": jurisdiction,   # <— add this
        "followup": {
            "intent": intent,
            "question": payload.user_query,
            "tool_facts": tool_facts if ok else {},
            "tool_ok": ok,
        },
        "ux_hints": {
            "suggested_questions": suggested_qs,
            "emergency": emergency_block
        }
    }

    def _templated_fallback():
        return ExplanationResponse(
            summary="Here's a quick summary of what we found. We couldn't generate the full explanation right now.",
            reasons=[
                "Your scan completed successfully.",
                ("Tool results returned" if ok else "Tool results unavailable; using basic info.")
            ],
            checks=["Review the label for warnings and batch/lot codes.", "Use the Safety Verdict as your primary guidance."],
            flags=scan_data.get("key_flags", []) if isinstance(scan_data, dict) else [],
            disclaimer="Not medical advice. For urgent concerns, use Emergency Guidance.",
        )

    synth_start = monotonic()
    try:
        if remaining() < 0.15 or not breaker.allow(synth_key):
            raise RuntimeError("deadline_or_circuit")
        timeout = min(SYNTH_TIMEOUT_SEC, max(0.1, remaining()))
        def _run():
            return chat.synthesize_result(merged_for_synthesis)
        message_dict = call_with_timeout(_run, timeout)
        message = ExplanationResponse(**message_dict)
        breaker.record_success(synth_key)
    except Exception:
        breaker.record_failure(synth_key)
        message = _templated_fallback()
        inc_fallback("conversation", "synth_fallback")

    # Emergency override: ensure emergency block is present when detected
    if is_emergency and not message.emergency:
        from agents.chat.chat_agent.agent_logic import EmergencyNotice
        message.emergency = EmergencyNotice(
            level="red",
            reason="Possible urgent situation reported.",
            cta="Open Emergency Guidance"
        )
    
    # Empty state guidance: ensure helpful checks for low-signal scans
    if (not message.checks or len(message.checks) < 2) and scan_data.get("recalls_found", 0) == 0:
        category = scan_data.get("category", "").lower()
        additional_checks = []
        
        if not any("batch" in check.lower() or "lot" in check.lower() for check in message.checks):
            additional_checks.append("Check label for batch/lot & expiry")
        
        if category in ["dairy", "cheese"] and not any("pasteur" in check.lower() for check in message.checks):
            additional_checks.append("Confirm pasteurisation (if dairy/cheese)")
        
        if category in ["toy", "game"] and not any("small parts" in check.lower() for check in message.checks):
            additional_checks.append("Inspect for small parts (if toy/gear)")
        
        if category in ["toy", "feeding"] and not any("age" in check.lower() for check in message.checks):
            additional_checks.append("Review age label (if toy/feeding)")
        
        # Add the most relevant checks to ensure at least 2 total
        needed = max(0, 2 - len(message.checks))
        message.checks.extend(additional_checks[:needed])

    # Log the assistant message
    log_message(db, conv, role="assistant", content=message.model_dump(), intent=intent, trace_id=trace_id)

    # Record synthesis latency
    obs_synth(int((monotonic() - synth_start) * 1000))
    
    # Record alternatives metrics if present in tool outputs
    for tool_call in tool_logs:
        if tool_call.ok and 'alternatives' in (tool_call.output or {}):
            alt_data = tool_call.output['alternatives']
            alt_count = len(alt_data.get('items', []))
            if alt_count > 0:
                inc_alternatives_shown(alt_count)
                break  # Only record once per conversation
    
    # Record overall success metrics
    circuit_broken = tool_logs[-1].error == "circuit_open" if tool_logs else False
    inc_req("conversation", intent, ok=True, circuit=circuit_broken)
    obs_total(int((monotonic() - t_start) * 1000))

    resp = ConversationResponse(
        conversation_id=str(conv.id),
        intent=intent,
        message=message,
        trace_id=trace_id,
        tool_calls=tool_logs,
    )
    out = JSONResponse(content=resp.model_dump())
    out.headers["X-Trace-Id"] = trace_id
    out.headers["X-Chat-Latency-Ms"] = str(int((monotonic() - t_start) * 1000))
    out.headers["X-Chat-Remaining-Ms"] = str(int(remaining() * 1000))
    out.headers["X-Chat-Intent"] = intent
    out.headers["X-Chat-Tool-Ok"] = "1" if ok else "0"
    return out


class ProfilePayload(BaseModel):
    consent_personalization: bool = Field(False)
    memory_paused: bool = Field(False)
    allergies: list[str] = Field(default_factory=list)
    pregnancy_trimester: int | None = None
    pregnancy_due_date: str | None = None  # ISO date
    child_birthdate: str | None = None     # ISO date

@router.get("/profile")
def get_my_profile(db: Session = Depends(get_db)):
    # TODO: replace with real current user
    user_id = None
    try:
        from core.auth import current_user
        user_id = getattr(current_user, "id", None)
    except Exception:
        pass
    if not user_id:
        raise HTTPException(status_code=401, detail="auth_required")
    prof = get_profile(db, user_id)
    return prof.__dict__ if prof else {}

@router.put("/profile")
def put_my_profile(payload: ProfilePayload, db: Session = Depends(get_db)):
    # TODO: replace with real current user
    user_id = None
    try:
        from core.auth import current_user
        user_id = getattr(current_user, "id", None)
    except Exception:
        pass
    if not user_id:
        raise HTTPException(status_code=401, detail="auth_required")
    data = payload.model_dump()
    # Convert ISO strings to dates where present
    from datetime import date
    for k in ("pregnancy_due_date", "child_birthdate"):
        if data.get(k):
            data[k] = date.fromisoformat(data[k])
    prof = upsert_profile(db, user_id, data)
    return {"ok": True, "updated_at": str(prof.updated_at)}


class EraseResponse(BaseModel):
    ok: bool
    mode: Literal["async", "sync"]
    deleted: int
    trace_id: str

@router.post("/erase-history", response_model=EraseResponse)
def erase_history(db: Session = Depends(get_db)):
    # TODO: replace with real current user dependency
    user_id: Optional[UUID] = None
    try:
        from core.auth import current_user
        user_id = getattr(current_user, "id", None)
    except Exception:
        user_id = None

    if not user_id:
        raise HTTPException(status_code=401, detail="auth_required")

    trace_id = str(uuid4())
    # Record the request timestamp
    mark_erase_requested(db, user_id)

    # Prefer async purge; if Celery not available, do it sync
    try:
        from workers.tasks.chat_cleanup import purge_user_history_task
        job_deleted = purge_user_history_task(str(user_id))  # works sync or enqueued depending on wiring
        mode = "sync"
        deleted = int(job_deleted or 0)
    except Exception:
        # If Celery app is present, calling .delay() is preferred:
        try:
            from workers.tasks.chat_cleanup import purge_user_history_task
            deleted = 0
            purge_user_history_task.delay(str(user_id))  # type: ignore[attr-defined]
            mode = "async"
        except Exception:
            # last resort: synchronous purge
            deleted = purge_conversations_for_user(db, user_id)
            mode = "sync"

    resp = EraseResponse(ok=True, mode=mode, deleted=deleted, trace_id=trace_id)
    out = JSONResponse(content=resp.model_dump())
    out.headers["X-Trace-Id"] = trace_id
    return out


@router.post("/demo", response_model=ConversationResponse)
def demo_conversation(
    payload: ConversationRequest,
    request: Request,
    chat: ChatAgentLogic = Depends(get_chat_agent),
):
    """Demo chat endpoint with mock scan data - for testing without real database records"""
    trace_id = str(uuid4())
    
    # Create mock scan data for testing
    mock_scan_data = {
        "product_name": "Demo Baby Formula",
        "brand": "SafeBaby",
        "barcode": "012345678901",
        "model_number": "SB-DEMO-001",
        "upc_gtin": "012345678901",
        "category": "baby_formula",
        "scan_type": "barcode",
        "scan_id": payload.scan_id,
        "scan_timestamp": "2024-01-01T12:00:00Z",
        "confidence_score": 0.95,
        "barcode_format": "UPC-A",
        "verdict": "Safe - No Recalls Found",
        "risk_level": "low",
        "recalls_found": 0,
        "recalls": [],
        "agencies_checked": "39 agencies (FDA, CPSC, USDA, etc.)",
        "flags": [],
        "key_flags": [],
        "ingredients": ["Milk protein", "Lactose", "Vitamins"],
        "allergens": ["Contains milk"],
        "pregnancy_warnings": [],
        "age_warnings": ["Suitable for infants 0-12 months"],
        "jurisdiction": {"code": "US", "label": "US FDA/CPSC"}
    }
    
    # Classify intent
    try:
        intent = chat.classify_intent(payload.user_query)
    except Exception:
        intent = "safety_question"
    
    # Generate response
    try:
        response = chat.synthesize_result(mock_scan_data)
        
        # Create response
        return ConversationResponse(
            conversation_id=str(uuid4()),
            intent=intent,
            message=response,
            trace_id=trace_id,
            tool_calls=[]
        )
    except Exception as e:
        # Log the actual error for debugging
        logger = logging.getLogger(__name__)
        logger.error(f"[{trace_id}] Chat synthesize_result failed: {e}")
        logger.error(f"[{trace_id}] Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"[{trace_id}] Traceback: {traceback.format_exc()}")
        
        # Fallback response
        fallback_response = ExplanationResponse(
            answer=f"I can help you with questions about {mock_scan_data['product_name']}. This appears to be a {mock_scan_data['category']} product with a safety rating of '{mock_scan_data['risk_level']}'. The product has {mock_scan_data['recalls_found']} recalls found across {mock_scan_data['agencies_checked']}. Is there something specific you'd like to know?",
            confidence=0.8,
            suggestions=["Ask about ingredients", "Check age appropriateness", "Verify safety for pregnancy"],
            key_points=["No recalls found", "Low risk level", "Contains milk allergen"],
            verdict_summary=mock_scan_data['verdict']
        )
        
        return ConversationResponse(
            conversation_id=str(uuid4()),
            intent=intent,
            message=fallback_response,
            trace_id=trace_id,
            tool_calls=[]
        )

@router.get("/flags")
def chat_flags(request: Request):
    """Get chat feature flags - robust version"""
    trace_id = getattr(getattr(request, "state", None), "trace_id", f"flags_{int(monotonic()*1000)}")
    
    try:
        from core.feature_flags import FEATURE_CHAT_ENABLED, FEATURE_CHAT_ROLLOUT_PCT
        
        payload = {
            "success": True,
            "data": {
                "chat_enabled_global": FEATURE_CHAT_ENABLED,
                "chat_rollout_pct": FEATURE_CHAT_ROLLOUT_PCT,
            },
            "traceId": trace_id
        }
        return JSONResponse(content=payload)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception(f"[{trace_id}] Chat flags failed: {e}")
        
        payload = {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": f"Feature flags unavailable: {str(e)}"
            },
            "traceId": trace_id
        }
        return JSONResponse(content=payload, status_code=500)
