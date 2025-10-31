# agents/chat/chat_agent/agent_logic.py
from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, ValidationError


class EvidenceItem(BaseModel):
    type: Literal["recall", "regulation", "guideline", "datasheet", "label"] = "regulation"
    source: str  # e.g., "EU Safety Gate", "CPSC", "FDA"
    id: str | None = None
    url: str | None = None


class EmergencyNotice(BaseModel):
    level: Literal["red", "amber"]
    reason: str
    cta: str  # e.g., "Open Emergency Guidance"


class ExplanationResponse(BaseModel):
    """Structured output for the 'Explain This Result' feature.
    Keep this minimal for Phase 0; expand in Phase 1.
    """

    summary: str = Field(..., description="2–3 line plain-language explanation.")
    reasons: list[str] = Field(
        default_factory=list,
        description="Bulleted reasons behind the verdict.",
    )
    checks: list[str] = Field(
        default_factory=list,
        description="Concrete checks for the user to perform.",
    )
    flags: list[str] = Field(
        default_factory=list,
        description="Machine-readable tags (e.g., 'soft_cheese','contains_peanuts').",
    )
    disclaimer: str = Field(..., description="Short non-diagnostic disclaimer.")

    # NEW (optional)
    jurisdiction: dict[str, str | None] | None = Field(
        default=None,
        description='Applied region context, e.g., {"code":"EU","label":"EU Safety Gate"}',
    )
    evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description="Cited sources backing claims.",
    )
    suggested_questions: list[str] = Field(
        default_factory=list,
        description="Follow-up questions parents commonly ask.",
    )
    emergency: EmergencyNotice | None = Field(
        default=None,
        description="Emergency notice for urgent situations.",
    )


Intent = Literal[
    "pregnancy_risk",
    "allergy_question",
    "ingredient_info",
    "age_appropriateness",
    "alternative_products",
    "recall_details",
    "unclear_intent",
]


class LLMClient(Protocol):
    """Minimal LLM protocol so we can inject any provider.
    Your existing OpenAI client can adapt to this easily.
    Implementations should raise on non-2xx or parse failures.
    """

    def chat_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        response_schema: dict[str, Any],
        timeout: float = 8.0,
    ) -> dict[str, Any]: ...


_PHASE0_SYSTEM_PROMPT = (
    "You are the BabyShield Synthesizer. Your job is to explain a completed safety scan to a "
    "parent.\n"
    "RULES:\n"
    "1) Use ONLY the provided scan_data facts. Do not speculate, do not browse the web.\n"
    "2) No medical advice. If something sounds clinical, add a plain-language caveat "
    "and direct to emergency guidance when relevant.\n"
    "3) Be concise, warm, and clear (Year-6 reading level). Prefer checklists over paragraphs.\n"
    "4) Return STRICTLY the JSON that matches the schema. No extra keys, no prose outside JSON.\n"
    "5) Include a jurisdiction tag if provided in context (e.g., EU, US, UK) and cite evidence "
    "for any regulatory or recall statements.\n"
    "6) If tool_facts include evidence, copy it into the output evidence verbatim. Do not invent "
    "sources.\n"
    "7) If tool_facts include alternatives, present at most 3 concise options with plain reasons. "
    "Do not imply endorsement, prices, or availability. Include evidence if provided.\n"
    "8) If no recalls, no critical flags, and tool_facts are empty/minimal, include 2–4 concise "
    "suggested_questions parents commonly ask for this category (e.g., 'Is this safe in "
    "pregnancy?', 'Any allergy concerns?', 'What age is this for?').\n"
    "9) If the user text or tool_facts indicate an urgent scenario (e.g., choking, battery "
    "ingestion, chemical ingestion, severe reaction), set emergency with level and a plain "
    "reason. Never provide medical advice; direct to Emergency Guidance.\n"
    "10) Keep suggested_questions short (max ~45 chars) and actionable; do not ask multiple "
    "questions at once.\n"
)

# JSON Schema to hard-enforce structure in providers that support JSON-mode
_EXPLANATION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string", "minLength": 1},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "checks": {"type": "array", "items": {"type": "string"}},
        "flags": {"type": "array", "items": {"type": "string"}},
        "disclaimer": {"type": "string", "minLength": 1},
        "jurisdiction": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"code": {"type": "string"}, "label": {"type": "string"}},
            "required": [],
        },
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "recall",
                            "regulation",
                            "guideline",
                            "datasheet",
                            "label",
                        ],
                    },
                    "source": {"type": "string"},
                    "id": {"type": "string"},
                    "url": {"type": "string"},
                },
                "required": ["source"],
            },
        },
        "suggested_questions": {"type": "array", "items": {"type": "string"}},
        "emergency": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "level": {"type": "string", "enum": ["red", "amber"]},
                "reason": {"type": "string"},
                "cta": {"type": "string"},
            },
            "required": ["level", "reason", "cta"],
        },
    },
    "required": ["summary", "disclaimer"],
}

_ROUTER_SYSTEM_PROMPT = (
    "You are the BabyShield Router. Classify a parent's question about a scanned product "
    "into ONE intent from this closed set:\n"
    "pregnancy_risk, allergy_question, ingredient_info, age_appropriateness, "
    "alternative_products, recall_details.\n"
    "If unclear or out of scope, return unclear_intent. Output JSON only."
)

_ROUTER_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "intent": {
            "type": "string",
            "enum": [
                "pregnancy_risk",
                "allergy_question",
                "ingredient_info",
                "age_appropriateness",
                "alternative_products",
                "recall_details",
                "unclear_intent",
            ],
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["intent"],
}


class ChatAgentLogic:
    """Phase 0 Synthesizer.
    - Accepts completed scan JSON.
    - Produces strictly structured JSON (ExplanationResponse).
    """

    def __init__(self, llm: LLMClient, *, model: str = "gpt-4o-mini") -> None:
        self.llm = llm
        self.model = model

    def synthesize_result(self, scan_data: dict[str, Any]) -> dict[str, Any]:
        """Turn final scan_data into parent-friendly, structured output.

        Args:
            scan_data: The full, completed scan result (dict) fetched by scan_id.
        Returns:
            Dict matching ExplanationResponse schema.
        Raises:
            ValueError on invalid or non-parseable model output.

        """
        user_prompt = (
            "Given the following scan_data (JSON), explain the result to a parent.\n\n"
            "scan_data JSON:\n"
            f"{scan_data}\n\n"
            "Return ONLY JSON matching the provided schema. Populate:\n"
            "- summary: 2–3 lines, plain language.\n"
            "- reasons: bullet points of why.\n"
            "- checks: what the parent should verify on the label/packaging.\n"
            "- flags: short machine tags (e.g., 'soft_cheese','contains_peanuts').\n"
            "- disclaimer: short non-diagnostic note.\n"
            "- jurisdiction: if provided in context, include the region info "
            '(e.g., {"code":"EU","label":"EU Safety Gate"}).\n'
            "- evidence: cite any regulatory sources, recalls, or guidelines that support your "
            "statements.\n"
        )

        raw: dict[str, Any] = self.llm.chat_json(
            model=self.model,
            system=_PHASE0_SYSTEM_PROMPT,
            user=user_prompt,
            response_schema=_EXPLANATION_JSON_SCHEMA,
            timeout=1.5,  # was 8.0 for phase0; hardened default
        )

        try:
            validated = ExplanationResponse.model_validate(raw).model_dump()
        except ValidationError as ve:
            # Surface a clear error for the API layer to transform into 5xx/4xx with trace_id
            raise ValueError(f"ExplanationResponse validation failed: {ve}") from ve

        return validated

    def classify_intent(self, query: str | None) -> Intent:
        """Fast heuristic pass, then cheap LLM fallback.
        Returns one of the fixed intents or 'unclear_intent'.
        """
        q = (query or "").lower()

        # Heuristics (fast path; keeps P50 < 5ms)
        kw = [
            (
                "pregnancy_risk",
                ["pregnan", "trimester", "breastfeed", "listeria"],
            ),
            (
                "allergy_question",
                ["allerg", "peanut", "nuts", "lactose", "gluten", "soy"],
            ),
            (
                "ingredient_info",
                [
                    "ingredient",
                    "made of",
                    "contains",
                    "contain",
                    "what's in",
                    "component",
                    "components",
                    "bpa",
                ],
            ),
            (
                "age_appropriateness",
                [
                    "newborn",
                    "month",
                    "month-old",
                    "age",
                    "years",
                    "suitable for",
                ],
            ),
            (
                "alternative_products",
                [
                    "alternative",
                    "safer option",
                    "safer options",
                    "instead",
                    "recommend",
                    "better option",
                ],
            ),
            (
                "recall_details",
                ["recall", "batch", "lot", "notice", "safety gate", "cpsc"],
            ),
        ]
        for intent, keys in kw:
            if any(k in q for k in keys):
                return intent  # type: ignore[return-value]

        # LLM fallback (closed-world JSON)
        try:
            raw = self.llm.chat_json(
                model="gpt-4o-mini",  # cheap/fast; adjust if you prefer
                system=_ROUTER_SYSTEM_PROMPT,
                user=f"Question: {query}",
                response_schema=_ROUTER_JSON_SCHEMA,
                timeout=0.30,  # router budget
            )
            intent = raw.get("intent", "unclear_intent")
            conf = float(raw.get("confidence", 0.0) or 0.0)
            if intent not in _ROUTER_JSON_SCHEMA["properties"]["intent"]["enum"]:
                return "unclear_intent"
            # require minimal confidence; otherwise treat as unclear
            return intent if conf >= 0.5 else "unclear_intent"
        except Exception:
            return "unclear_intent"
