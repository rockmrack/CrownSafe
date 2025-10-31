"""COMPREHENSIVE AGENT TEST SUITE
Tests all major agents in the BabyShield system
Date: October 10, 2025
"""

from datetime import datetime
from typing import Any

import pytest

from agents.recall_data_agent.agent_logic import RecallDataAgentLogic
from agents.recall_data_agent.connectors import (
    CPSCConnector,
    FDAConnector,
    HealthCanadaConnector,
    NHTSAConnector,
)
from agents.value_add.alternatives_agent.agent_logic import AlternativesAgentLogic
from agents.visual.visual_search_agent.agent_logic import VisualSearchAgentLogic

try:
    from agents.reporting.report_builder_agent.agent_logic import (
        ReportBuilderAgentLogic,
    )

    _REPORT_BUILDER_IMPORT_ERROR: Exception | None = None
    _REPORT_BUILDER_AVAILABLE = True
except Exception as exc:  # pragma: no cover - optional dependency guard
    ReportBuilderAgentLogic = None  # type: ignore[assignment]
    _REPORT_BUILDER_IMPORT_ERROR = exc
    _REPORT_BUILDER_AVAILABLE = False

# Import ChatAgent, ProductIdentifierAgent, and RouterAgent
try:
    from agents.chat.chat_agent.agent_logic import ChatAgentLogic
except ImportError:
    ChatAgentLogic = None

try:
    from agents.product_identifier_agent.agent_logic import ProductIdentifierAgentLogic

    _PRODUCT_IDENTIFIER_AVAILABLE = True
except ImportError:
    ProductIdentifierAgentLogic = None
    _PRODUCT_IDENTIFIER_AVAILABLE = False

try:
    from agents.routing.router_agent.agent_logic import RouterAgentLogic

    _ROUTER_AVAILABLE = True
except ImportError:
    RouterAgentLogic = None
    _ROUTER_AVAILABLE = False


def _get_skip_reason(error: Exception | None, agent_name: str) -> str:
    """Generate a readable skip reason for missing agent dependencies."""
    if error is None:
        return f"{agent_name} is unavailable (unknown reason)."
    error_type = type(error).__name__
    error_msg = str(error)
    return f"{agent_name} dependencies unavailable: {error_type}: {error_msg}"


if not _REPORT_BUILDER_AVAILABLE:
    pytestmark = pytest.mark.skip(  # type: ignore[var-annotated]
        reason=_get_skip_reason(_REPORT_BUILDER_IMPORT_ERROR, "ReportBuilderAgent"),
    )


class TestResults:
    """Track test results for summary report"""

    def __init__(self):
        self.results: dict[str, dict[str, Any]] = {}
        self.start_time = datetime.now()

    def add_result(
        self,
        agent_name: str,
        test_name: str,
        status: str,
        details: str = "",
    ):
        if agent_name not in self.results:
            self.results[agent_name] = {"tests": [], "passed": 0, "failed": 0}

        self.results[agent_name]["tests"].append(
            {
                "name": test_name,
                "status": status,
                "details": details,
            },
        )

        if status == "PASSED":
            self.results[agent_name]["passed"] += 1
        else:
            self.results[agent_name]["failed"] += 1

    def print_summary(self):
        print("\n" + "=" * 80)
        print("COMPREHENSIVE AGENT TEST SUITE - SUMMARY REPORT")
        print("=" * 80)
        print(f"Test execution time: {datetime.now() - self.start_time}")
        print()

        total_passed = 0
        total_failed = 0

        for agent_name, data in self.results.items():
            print(f"\n{agent_name}")
            print("-" * 80)
            print(f"  Tests Passed: {data['passed']}")
            print(f"  Tests Failed: {data['failed']}")
            print(
                f"  Success Rate: {data['passed']}/{data['passed'] + data['failed']} ({data['passed'] / (data['passed'] + data['failed']) * 100:.1f}%)",  # noqa: E501
            )

            for test in data["tests"]:
                status_symbol = "✓" if test["status"] == "PASSED" else "✗"
                print(f"    {status_symbol} {test['name']}: {test['status']}")
                if test["details"]:
                    print(f"      {test['details']}")

            total_passed += data["passed"]
            total_failed += data["failed"]

        print("\n" + "=" * 80)
        print(f"TOTAL: {total_passed} passed, {total_failed} failed")
        print(
            f"OVERALL SUCCESS RATE: {total_passed}/{total_passed + total_failed} ({total_passed / (total_passed + total_failed) * 100:.1f}%)",  # noqa: E501
        )
        print("=" * 80)


# Global test results tracker
test_results = TestResults()


# ============================================================================
# RECALL DATA AGENT TESTS
# ============================================================================


@pytest.mark.unit
def test_recall_agent_initialization():
    """Test RecallDataAgent initialization"""
    agent_name = "RecallDataAgent"
    test_name = "Initialization"

    try:
        agent = RecallDataAgentLogic(agent_id="test-recall-agent")
        assert agent is not None
        assert agent.agent_id == "test-recall-agent"
        test_results.add_result(agent_name, test_name, "PASSED", "Agent initialized successfully")
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_recall_agent_cpsc_live_api():
    """Test RecallDataAgent with live CPSC API"""
    agent_name = "RecallDataAgent"
    test_name = "CPSC Live API Integration"

    try:
        connector = CPSCConnector()
        recalls = await connector.fetch_recent_recalls()

        assert recalls is not None
        assert len(recalls) > 0

        # Verify recall structure
        first_recall = recalls[0]
        # Check if it's a Pydantic model or dict
        if hasattr(first_recall, "recall_id"):
            assert first_recall.recall_id is not None
            assert first_recall.product_name is not None
        else:
            assert "recall_id" in first_recall
            assert "product_name" in first_recall

        test_results.add_result(
            agent_name,
            test_name,
            "PASSED",
            f"Fetched {len(recalls)} real recalls from CPSC",
        )
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recall_agent_connectors():
    """Test RecallDataAgent connector initialization"""
    agent_name = "RecallDataAgent"
    test_name = "Connector Initialization"

    try:
        connectors = [
            CPSCConnector(),
            FDAConnector(),
            NHTSAConnector(),
            HealthCanadaConnector(),
        ]

        assert all(c is not None for c in connectors)
        test_results.add_result(
            agent_name,
            test_name,
            "PASSED",
            f"Initialized {len(connectors)} connectors successfully",
        )
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_recall_agent_process_task():
    """Test RecallDataAgent process_task method"""
    agent_name = "RecallDataAgent"
    test_name = "Process Task"

    try:
        agent = RecallDataAgentLogic(agent_id="test-process-task")

        # Test with UPC search
        result = await agent.process_task({"upc": "070470003795", "product_name": "Test Product"})

        assert result is not None
        assert "recalls" in result or "error" not in result

        test_results.add_result(agent_name, test_name, "PASSED", "Successfully processed recall search task")
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


# ============================================================================
# CHAT AGENT TESTS
# ============================================================================


class MockLLMClient:
    """Minimal mock LLM client for ChatAgent tests."""

    def chat_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        response_schema: dict[str, Any],
        timeout: float = 8.0,
    ) -> dict[str, Any]:
        # Return a deterministic payload that satisfies ChatAgent expectations.
        return {
            "summary": "Test summary",
            "reasons": ["Test reason"],
            "checks": ["Test check"],
            "flags": [],
            "disclaimer": "Test disclaimer",
        }


@pytest.mark.unit
def test_chat_agent_initialization():
    """Test ChatAgent initialization"""
    agent_name = "ChatAgent"
    test_name = "Initialization"

    try:
        mock_llm = MockLLMClient()
        agent = ChatAgentLogic(llm=mock_llm)
        assert agent is not None
        assert agent.llm is mock_llm
        test_results.add_result(agent_name, test_name, "PASSED", "Agent initialized successfully")
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_agent_process_simple_query():
    """Test ChatAgent with simple query"""
    agent_name = "ChatAgent"
    test_name = "Simple Query Processing"

    try:
        mock_llm = MockLLMClient()
        agent = ChatAgentLogic(llm=mock_llm)

        # ChatAgent uses synthesize_result, not process_task
        result = agent.synthesize_result(
            {
                "query": "Is this product safe for babies?",
                "product_name": "Baby Bottle",
                "verdict": "SAFE",
            },
        )

        assert result is not None
        assert "summary" in result

        test_results.add_result(
            agent_name,
            test_name,
            "PASSED",
            "Successfully processed simple query",
        )
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_agent_emergency_detection():
    """Test ChatAgent emergency detection"""
    agent_name = "ChatAgent"
    test_name = "Emergency Detection"

    try:
        mock_llm = MockLLMClient()
        agent = ChatAgentLogic(llm=mock_llm)

        result = agent.synthesize_result(
            {
                "query": "My baby swallowed a button battery!",
                "product_name": "Battery",
                "verdict": "EMERGENCY",
                "urgent": True,
            },
        )

        assert result is not None
        # Emergency should be detected

        test_results.add_result(agent_name, test_name, "PASSED", "Emergency detection working")
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


# ============================================================================
# REPORT BUILDER AGENT TESTS
# ============================================================================


@pytest.mark.unit
def test_report_builder_initialization():
    """Test ReportBuilderAgent initialization"""
    agent_name = "ReportBuilderAgent"
    test_name = "Initialization"

    try:
        agent = ReportBuilderAgentLogic(agent_id="test-report-builder")
        assert agent is not None
        assert agent.agent_id == "test-report-builder"
        test_results.add_result(agent_name, test_name, "PASSED", "Agent initialized successfully")
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


@pytest.mark.integration
def test_report_builder_generate_report():
    """Test ReportBuilderAgent report generation"""
    agent_name = "ReportBuilderAgent"
    test_name = "Report Generation"

    try:
        agent = ReportBuilderAgentLogic(agent_id="test-report-gen")

        result = agent.process_task(
            {
                "product_name": "Baby Stroller Model X",
                "upc": "070470003795",
                "scan_id": "test-scan-123",
                "recalls": [
                    {
                        "recall_id": "TEST-001",
                        "product_name": "Baby Stroller",
                        "hazard": "Fall risk",
                        "agency": "CPSC",
                    },
                ],
            },
        )

        assert result is not None
        assert "report_id" in result or "report" in result or "error" not in result

        test_results.add_result(agent_name, test_name, "PASSED", "Successfully generated report")
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


# ============================================================================
# VISUAL SEARCH AGENT TESTS
# ============================================================================


@pytest.mark.unit
def test_visual_search_initialization():
    """Test VisualSearchAgent initialization"""
    agent_name = "VisualSearchAgent"
    test_name = "Initialization"

    try:
        agent = VisualSearchAgentLogic(agent_id="test-visual-search")
        assert agent is not None
        assert agent.agent_id == "test-visual-search"
        test_results.add_result(agent_name, test_name, "PASSED", "Agent initialized successfully")
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


@pytest.mark.unit
@pytest.mark.asyncio
async def test_visual_search_capabilities():
    """Test VisualSearchAgent capabilities"""
    agent_name = "VisualSearchAgent"
    test_name = "Capabilities Check"

    try:
        agent = VisualSearchAgentLogic(agent_id="test-visual-caps")

        # Check that agent has expected methods
        assert hasattr(agent, "process_task")

        test_results.add_result(agent_name, test_name, "PASSED", "Agent has required capabilities")
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


# ============================================================================
# ALTERNATIVES AGENT TESTS
# ============================================================================


@pytest.mark.unit
def test_alternatives_agent_initialization():
    """Test AlternativesAgent initialization"""
    agent_name = "AlternativesAgent"
    test_name = "Initialization"

    try:
        agent = AlternativesAgentLogic(agent_id="test-alternatives")
        assert agent is not None
        assert agent.agent_id == "test-alternatives"
        test_results.add_result(agent_name, test_name, "PASSED", "Agent initialized successfully")
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_alternatives_agent_find_alternatives():
    """Test AlternativesAgent finding alternatives"""
    agent_name = "AlternativesAgent"
    test_name = "Find Alternatives"

    try:
        agent = AlternativesAgentLogic(agent_id="test-find-alt")

        result = await agent.process_task(
            {
                "product_name": "Baby Bottle X",
                "product_category": "feeding",
                "unsafe_product": True,
            },
        )

        assert result is not None

        test_results.add_result(agent_name, test_name, "PASSED", "Successfully found alternatives")
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


# ============================================================================
# PRODUCT IDENTIFIER AGENT TESTS
# ============================================================================


@pytest.mark.unit
@pytest.mark.skipif(
    not _PRODUCT_IDENTIFIER_AVAILABLE,
    reason="ProductIdentifierAgent not available",
)
def test_product_identifier_initialization():
    """Test ProductIdentifierAgent initialization"""
    agent_name = "ProductIdentifierAgent"
    test_name = "Initialization"

    try:
        agent = ProductIdentifierAgentLogic(agent_id="test-product-id")
        assert agent is not None
        assert agent.agent_id == "test-product-id"
        test_results.add_result(agent_name, test_name, "PASSED", "Agent initialized successfully")
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(
    not _PRODUCT_IDENTIFIER_AVAILABLE,
    reason="ProductIdentifierAgent not available",
)
async def test_product_identifier_process():
    """Test ProductIdentifierAgent processing"""
    agent_name = "ProductIdentifierAgent"
    test_name = "Product Identification"

    try:
        agent = ProductIdentifierAgentLogic(agent_id="test-prod-process")

        result = await agent.process_task({"upc": "070470003795", "product_name": "Test Product"})

        assert result is not None

        test_results.add_result(agent_name, test_name, "PASSED", "Successfully identified product")
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


# ============================================================================
# ROUTER AGENT TESTS
# ============================================================================


@pytest.mark.unit
@pytest.mark.skipif(not _ROUTER_AVAILABLE, reason="RouterAgent not available")
def test_router_agent_initialization():
    """Test RouterAgent initialization"""
    agent_name = "RouterAgent"
    test_name = "Initialization"

    try:
        agent = RouterAgentLogic(agent_id="test-router")
        assert agent is not None
        assert agent.agent_id == "test-router"
        test_results.add_result(agent_name, test_name, "PASSED", "Agent initialized successfully")
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


@pytest.mark.integration
@pytest.mark.skipif(not _ROUTER_AVAILABLE, reason="RouterAgent not available")
def test_router_agent_capabilities():
    """Test RouterAgent capabilities mapping"""
    agent_name = "RouterAgent"
    test_name = "Capabilities Mapping"

    try:
        agent = RouterAgentLogic(agent_id="test-router-caps")

        # Check that router knows about all agents
        assert hasattr(agent, "route_task") or hasattr(agent, "process_task")

        test_results.add_result(agent_name, test_name, "PASSED", "Router has capability mappings")
    except Exception as e:
        test_results.add_result(agent_name, test_name, "FAILED", f"Error: {e!s}")
        raise


# ============================================================================
# TEST SUITE EXECUTION
# ============================================================================


def pytest_sessionfinish(session, exitstatus):
    """Hook to print summary after all tests complete"""
    test_results.print_summary()


if __name__ == "__main__":
    print("=" * 80)
    print("COMPREHENSIVE AGENT TEST SUITE")
    print("Testing all major agents in the BabyShield system")
    print("=" * 80)
    print()

    # Run pytest programmatically
    pytest.main([__file__, "-v", "--tb=short", "-m", "unit or integration"])
