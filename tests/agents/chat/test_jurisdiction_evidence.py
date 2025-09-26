from unittest.mock import Mock
from agents.chat.chat_agent.agent_logic import ChatAgentLogic, ExplanationResponse, EvidenceItem

class MockLLMClient:
    def chat_json(self, **kwargs):
        # Mock response with jurisdiction and evidence
        return {
            "summary": "This product appears safe based on our checks.",
            "reasons": ["No recalls found in EU Safety Gate", "Meets EU safety standards"],
            "checks": ["Verify CE marking on packaging", "Check expiration date"],
            "flags": ["eu_compliant"],
            "disclaimer": "Not medical advice. Consult healthcare provider for specific concerns.",
            "jurisdiction": {"code": "EU", "label": "EU Safety Gate"},
            "evidence": [
                {"type": "regulation", "source": "EU Safety Gate", "id": "REG-2024-001"},
                {"type": "guideline", "source": "EFSA", "url": "https://efsa.europa.eu/guidelines"}
            ]
        }

def test_explanation_response_with_jurisdiction_and_evidence():
    """Test that ExplanationResponse can handle jurisdiction and evidence fields"""
    # Test data
    data = {
        "summary": "Product is safe for use.",
        "reasons": ["No safety concerns found"],
        "checks": ["Check packaging"],
        "flags": ["safe"],
        "disclaimer": "Not medical advice.",
        "jurisdiction": {"code": "EU", "label": "EU Safety Gate"},
        "evidence": [
            {"type": "regulation", "source": "EU Safety Gate", "id": "REG-001"},
            {"type": "guideline", "source": "EFSA"}
        ]
    }
    
    # Should validate successfully
    response = ExplanationResponse(**data)
    
    assert response.summary == "Product is safe for use."
    assert response.jurisdiction == {"code": "EU", "label": "EU Safety Gate"}
    assert len(response.evidence) == 2
    assert response.evidence[0].type == "regulation"
    assert response.evidence[0].source == "EU Safety Gate"
    assert response.evidence[0].id == "REG-001"

def test_explanation_response_without_optional_fields():
    """Test that ExplanationResponse works without optional fields (backwards compatibility)"""
    # Minimal data (only required fields)
    data = {
        "summary": "Product is safe for use.",
        "disclaimer": "Not medical advice."
    }
    
    # Should validate successfully
    response = ExplanationResponse(**data)
    
    assert response.summary == "Product is safe for use."
    assert response.disclaimer == "Not medical advice."
    assert response.jurisdiction is None
    assert response.evidence == []
    assert response.reasons == []
    assert response.checks == []
    assert response.flags == []

def test_evidence_item_validation():
    """Test EvidenceItem validation"""
    # Valid evidence item
    evidence = EvidenceItem(source="EU Safety Gate", type="regulation", id="REG-001")
    assert evidence.source == "EU Safety Gate"
    assert evidence.type == "regulation"
    assert evidence.id == "REG-001"
    assert evidence.url is None
    
    # Minimal evidence item (only required field)
    minimal = EvidenceItem(source="CPSC")
    assert minimal.source == "CPSC"
    assert minimal.type == "regulation"  # default value
    assert minimal.id is None
    assert minimal.url is None

def test_chat_agent_with_jurisdiction_context():
    """Test that ChatAgentLogic can handle jurisdiction context"""
    agent = ChatAgentLogic(llm=MockLLMClient())
    
    # Scan data with jurisdiction context
    scan_data = {
        "product_name": "Baby Formula",
        "jurisdiction": {"code": "EU", "label": "EU Safety Gate"},
        "scan_id": "test-123"
    }
    
    result = agent.synthesize_result(scan_data)
    
    # Should include jurisdiction and evidence from mock
    assert "jurisdiction" in result
    assert result["jurisdiction"]["code"] == "EU"
    assert result["jurisdiction"]["label"] == "EU Safety Gate"
    assert "evidence" in result
    assert len(result["evidence"]) == 2
    assert result["evidence"][0]["source"] == "EU Safety Gate"
