from agents.chat.chat_agent.agent_logic import ChatAgentLogic


class DummyLLM:
    def chat_json(self, **_: dict) -> dict:
        return {"intent": "unclear_intent", "confidence": 0.0}


class ConfidentLLM:
    def __init__(self, intent: str, confidence: float = 0.8):
        self.intent = intent
        self.confidence = confidence

    def chat_json(self, **_: dict) -> dict:
        return {"intent": self.intent, "confidence": self.confidence}


class FailingLLM:
    def chat_json(self, **_: dict) -> dict:
        raise Exception("LLM API failed")


def _agent():
    return ChatAgentLogic(llm=DummyLLM())


def test_pregnancy():
    assert _agent().classify_intent("Is this safe in second trimester?") == "pregnancy_risk"


def test_allergy():
    assert _agent().classify_intent("My son has a peanut allergy, is this ok?") == "allergy_question"


def test_ingredients():
    assert _agent().classify_intent("What ingredients does it contain?") == "ingredient_info"


def test_age():
    assert _agent().classify_intent("Is it suitable for a 3-month-old?") == "age_appropriateness"


def test_alternatives():
    assert _agent().classify_intent("Any safer alternatives you recommend?") == "alternative_products"


def test_recall():
    assert _agent().classify_intent("Show recall details for this batch") == "recall_details"


def test_heuristic_variants():
    """Test various keyword variations for heuristic matching"""
    agent = _agent()

    # Pregnancy variants
    assert agent.classify_intent("I'm pregnant, is this safe?") == "pregnancy_risk"
    assert agent.classify_intent("Safe during breastfeeding?") == "pregnancy_risk"

    # Allergy variants
    assert agent.classify_intent("Contains nuts?") == "allergy_question"
    assert agent.classify_intent("Gluten free?") == "allergy_question"

    # Age variants
    assert agent.classify_intent("Good for newborns?") == "age_appropriateness"
    assert agent.classify_intent("2 years old safe?") == "age_appropriateness"


def test_llm_fallback_confident():
    """Test LLM fallback with confident response"""
    agent = ChatAgentLogic(llm=ConfidentLLM("pregnancy_risk", 0.9))
    result = agent.classify_intent("Some unclear question about safety")
    assert result == "pregnancy_risk"


def test_llm_fallback_low_confidence():
    """Test LLM fallback with low confidence returns unclear_intent"""
    agent = ChatAgentLogic(llm=ConfidentLLM("pregnancy_risk", 0.3))
    result = agent.classify_intent("Some unclear question about safety")
    assert result == "unclear_intent"


def test_llm_fallback_invalid_intent():
    """Test LLM fallback with invalid intent returns unclear_intent"""
    agent = ChatAgentLogic(llm=ConfidentLLM("invalid_intent", 0.9))
    result = agent.classify_intent("Some unclear question about safety")
    assert result == "unclear_intent"


def test_llm_fallback_failure():
    """Test LLM fallback gracefully handles exceptions"""
    agent = ChatAgentLogic(llm=FailingLLM())
    result = agent.classify_intent("Some unclear question about safety")
    assert result == "unclear_intent"


def test_empty_query():
    """Test empty or None query handling"""
    agent = _agent()
    assert agent.classify_intent("") == "unclear_intent"
    assert agent.classify_intent(None) == "unclear_intent"
