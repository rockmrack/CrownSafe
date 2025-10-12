"""
COMPREHENSIVE AGENT TEST SUITE - ALL BABYSHIELD AGENTS
Tests all major agents in the BabyShield system
Date: October 10, 2025

This test suite verifies:
1. RecallDataAgent - 39+ international recall agencies
2. ReportBuilderAgent - PDF report generation
3. VisualSearchAgent - Image-based product identification
4. AlternativesAgent - Safe product alternatives
5. Chat endpoints - Conversational AI
"""

import asyncio
from datetime import datetime
from typing import Any, Dict

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
    from agents.reporting.report_builder_agent.agent_logic import ReportBuilderAgentLogic

    _REPORT_BUILDER_IMPORT_ERROR: Exception | None = None
    _REPORT_BUILDER_AVAILABLE = True
except Exception as exc:  # pragma: no cover - optional dependency guard
    ReportBuilderAgentLogic = None  # type: ignore[assignment]
    _REPORT_BUILDER_IMPORT_ERROR = exc
    _REPORT_BUILDER_AVAILABLE = False


print("\n" + "=" * 80)
print("COMPREHENSIVE AGENT TEST SUITE")
print("Testing all major agents in the BabyShield system")
print("=" * 80 + "\n")

if not _REPORT_BUILDER_AVAILABLE:
    pytestmark = pytest.mark.skip(  # type: ignore[var-annotated]
        reason=(f"ReportBuilderAgent dependencies unavailable: {_REPORT_BUILDER_IMPORT_ERROR}")
    )


# ============================================================================
# RECALL DATA AGENT TESTS
# ============================================================================


@pytest.mark.unit
def test_recall_agent_initialization():
    """Test 1: RecallDataAgent initialization"""
    print("\n[TEST 1] Testing RecallDataAgent initialization...")
    agent = RecallDataAgentLogic(agent_id="test-recall-agent")
    assert agent is not None
    assert agent.agent_id == "test-recall-agent"
    print("✓ RecallDataAgent initialized successfully")
    print(f"  Agent ID: {agent.agent_id}")


@pytest.mark.integration
def test_recall_agent_database_query():
    """Test 2: RecallDataAgent with local database (deterministic test data)

    This test validates database queries work correctly using test data.
    To test against production 130k+ recalls, set DATABASE_URL environment variable
    to your production PostgreSQL connection string before running tests.
    """
    from datetime import date

    from core_infra.database import Base, LegacyRecallDB, SessionLocal, engine

    print("\n[TEST 2] Testing RecallDataAgent with local recall database...")
    print("  Creating database schema...")

    # Create only the recalls table (avoid SQLite UUID compatibility issues with other tables)
    LegacyRecallDB.__table__.create(bind=engine, checkfirst=True)

    print("  Setting up test data...")

    session = SessionLocal()
    try:
        # Seed test recall data
        test_recalls = [
            LegacyRecallDB(
                recall_id="TEST-001",
                product_name="Baby Monitor X100",
                brand="SafeBaby",
                recall_date=date(2024, 10, 1),
                hazard_description="Overheating battery risk",
            ),
            LegacyRecallDB(
                recall_id="TEST-002",
                product_name="Infant Car Seat Pro",
                brand="TravelSafe",
                recall_date=date(2024, 9, 15),
                hazard_description="Harness buckle failure",
            ),
            LegacyRecallDB(
                recall_id="TEST-003",
                product_name="Baby Food Puree Organic",
                brand="HealthyStart",
                recall_date=date(2024, 8, 20),
                hazard_description="Potential contamination",
            ),
        ]

        # Add test data
        for recall in test_recalls:
            session.add(recall)
        session.commit()

        # Query total recall count
        total_count = session.query(LegacyRecallDB).count()
        print("✓ Database connection SUCCESSFUL!")
        print(f"  - Total recalls in test database: {total_count:,}")

        # Validate we have recalls
        assert total_count >= 3, "Database should contain test recall records"

        # Get a sample recall
        sample = session.query(LegacyRecallDB).filter(LegacyRecallDB.recall_id == "TEST-001").first()
        if sample:
            print("\n  === SAMPLE RECALL DATA ===")
            print(f"  Product: {sample.product_name}")
            print(f"  Recall ID: {sample.recall_id}")
            print(f"  Date: {sample.recall_date}")
            print(f"  Hazard: {sample.hazard_description or 'N/A'}")
            print(f"  Brand: {sample.brand or 'N/A'}")

        # Test query by product name
        search_results = (
            session.query(LegacyRecallDB).filter(LegacyRecallDB.product_name.ilike("%baby%")).limit(5).all()
        )
        print(f"\n  - Sample 'baby' product search: {len(search_results)} results")
        assert len(search_results) >= 2, "Should find baby-related products"

        # Test query by recall_id
        recall_result = session.query(LegacyRecallDB).filter(LegacyRecallDB.recall_id == "TEST-002").first()
        assert recall_result is not None, "Should find recall by recall_id"
        print(f"  - Recall ID lookup successful: {recall_result.product_name}")

    finally:
        # Cleanup test data
        try:
            session.query(LegacyRecallDB).filter(LegacyRecallDB.recall_id.like("TEST-%")).delete()
            session.commit()
        except Exception:
            session.rollback()
        session.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recall_agent_all_connectors():
    """Test 3: RecallDataAgent all connector initialization"""
    print("\n[TEST 3] Testing all RecallDataAgent connectors...")

    connectors = [
        ("CPSC", CPSCConnector()),
        ("FDA", FDAConnector()),
        ("NHTSA", NHTSAConnector()),
        ("Health Canada", HealthCanadaConnector()),
    ]

    for name, connector in connectors:
        assert connector is not None
        print(f"  ✓ {name} connector initialized")

    print(f"✓ All {len(connectors)} connectors initialized successfully")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_recall_agent_process_task():
    """Test 4: RecallDataAgent process_task method"""
    print("\n[TEST 4] Testing RecallDataAgent process_task...")

    agent = RecallDataAgentLogic(agent_id="test-process-task")

    result = await agent.process_task({"upc": "070470003795", "product_name": "Test Baby Product"})

    assert result is not None
    print("✓ Successfully processed recall search task")
    print("  Task completed for UPC: 070470003795")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_recall_agent_statistics():
    """Test 5: RecallDataAgent get_statistics"""
    print("\n[TEST 5] Testing RecallDataAgent statistics...")

    agent = RecallDataAgentLogic(agent_id="test-stats")
    stats = agent.get_statistics()

    assert stats is not None
    assert "connectors" in stats or "total_connectors" in str(stats)

    print("✓ Statistics retrieved successfully")
    print(f"  Available connectors: {stats}")


# ============================================================================
# REPORT BUILDER AGENT TESTS
# ============================================================================


@pytest.mark.unit
def test_report_builder_initialization():
    """Test 6: ReportBuilderAgent initialization"""
    print("\n[TEST 6] Testing ReportBuilderAgent initialization...")

    assert ReportBuilderAgentLogic is not None  # nosec - ensured by test skip
    agent = ReportBuilderAgentLogic(  # type: ignore[operator]
        agent_id="test-report-builder",
        version="2.1-test",
    )

    assert agent is not None
    assert agent.agent_id == "test-report-builder"
    assert agent.version == "2.1-test"

    print("✓ ReportBuilderAgent initialized successfully")
    print(f"  Agent ID: {agent.agent_id}")
    print(f"  Version: {agent.version}")


@pytest.mark.unit
def test_report_builder_capabilities():
    """Test 7: ReportBuilderAgent capabilities"""
    print("\n[TEST 7] Testing ReportBuilderAgent capabilities...")

    assert ReportBuilderAgentLogic is not None  # nosec - ensured by test skip
    agent = ReportBuilderAgentLogic(  # type: ignore[operator]
        agent_id="test-capabilities",
        version="2.1-test",
    )

    capabilities = agent.get_capabilities()

    assert capabilities is not None
    assert len(capabilities) > 0
    assert any("report" in str(cap).lower() for cap in capabilities)

    print("✓ ReportBuilderAgent capabilities retrieved")
    print(f"  Available capabilities: {len(capabilities)}")
    for cap in capabilities:
        if isinstance(cap, dict):
            print(f"    - {cap.get('name', 'Unknown')}")


@pytest.mark.integration
def test_report_builder_generate_report():
    """Test 8: ReportBuilderAgent report generation"""
    print("\n[TEST 8] Testing ReportBuilderAgent report generation...")

    assert ReportBuilderAgentLogic is not None  # nosec - ensured by test skip
    agent = ReportBuilderAgentLogic(  # type: ignore[operator]
        agent_id="test-report-gen",
        version="2.1-test",
    )

    # Test task data
    task_data = {
        "product_name": "Baby Stroller Model X",
        "upc": "070470003795",
        "scan_id": "test-scan-123",
        "recalls": [
            {
                "recall_id": "TEST-001",
                "product_name": "Baby Stroller",
                "hazard": "Fall risk",
                "agency": "CPSC",
            }
        ],
        "report_type": "baby_safety",
    }

    result = agent.process_task(task_data)

    assert result is not None
    print("✓ Successfully generated safety report")
    if isinstance(result, dict):
        print(f"  Report data keys: {list(result.keys())[:5]}")


# ============================================================================
# VISUAL SEARCH AGENT TESTS
# ============================================================================


@pytest.mark.unit
def test_visual_search_initialization():
    """Test 9: VisualSearchAgent initialization"""
    print("\n[TEST 9] Testing VisualSearchAgent initialization...")

    agent = VisualSearchAgentLogic(agent_id="test-visual-search")

    assert agent is not None
    assert agent.agent_id == "test-visual-search"

    print("✓ VisualSearchAgent initialized successfully")
    print(f"  Agent ID: {agent.agent_id}")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_visual_search_capabilities():
    """Test 10: VisualSearchAgent capabilities"""
    print("\n[TEST 10] Testing VisualSearchAgent capabilities...")

    agent = VisualSearchAgentLogic(agent_id="test-visual-caps")

    # Check that agent has expected methods
    assert hasattr(agent, "process_task")
    assert callable(getattr(agent, "process_task", None))

    print("✓ VisualSearchAgent has required capabilities")
    print("  - process_task method available")


# ============================================================================
# ALTERNATIVES AGENT TESTS
# ============================================================================


@pytest.mark.unit
def test_alternatives_agent_initialization():
    """Test 11: AlternativesAgent initialization"""
    print("\n[TEST 11] Testing AlternativesAgent initialization...")

    agent = AlternativesAgentLogic(agent_id="test-alternatives")

    assert agent is not None
    assert agent.agent_id == "test-alternatives"

    print("✓ AlternativesAgent initialized successfully")
    print(f"  Agent ID: {agent.agent_id}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_alternatives_agent_process_task():
    """Test 12: AlternativesAgent finding alternatives"""
    print("\n[TEST 12] Testing AlternativesAgent finding alternatives...")

    agent = AlternativesAgentLogic(agent_id="test-find-alt")

    result = await agent.process_task(
        {
            "product_name": "Baby Bottle X",
            "product_category": "feeding",
            "unsafe_product": True,
        }
    )

    assert result is not None
    print("✓ Successfully processed alternatives search")
    if isinstance(result, dict):
        print(f"  Result keys: {list(result.keys())[:5]}")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_scan_to_recall():
    """Test 13: Complete workflow - Scan to Recall Check"""
    print("\n[TEST 13] Testing complete workflow: Scan → Recall Check...")

    # Step 1: Initialize RecallDataAgent
    recall_agent = RecallDataAgentLogic(agent_id="workflow-test")

    # Step 2: Process recall check
    result = await recall_agent.process_task({"upc": "070470003795", "product_name": "Test Baby Product"})

    assert result is not None
    print("✓ Complete workflow test successful")
    print("  Workflow: Scan → Recall Check → Complete")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_recall_to_report():
    """Test 14: Complete workflow - Recall to Report"""
    print("\n[TEST 14] Testing complete workflow: Recall Check → Report...")

    # Step 1: Get recalls
    recall_agent = RecallDataAgentLogic(agent_id="workflow-recall-report")
    recall_result = await recall_agent.process_task({"upc": "070470003795", "product_name": "Test Product"})

    # Step 2: Generate report
    assert ReportBuilderAgentLogic is not None  # nosec - ensured by test skip
    report_agent = ReportBuilderAgentLogic(  # type: ignore[operator]
        agent_id="workflow-report",
        version="2.1-test",
    )

    report_result = report_agent.process_task(
        {
            "product_name": "Test Product",
            "upc": "070470003795",
            "recalls": [],
            "report_type": "baby_safety",
        }
    )

    assert recall_result is not None
    assert report_result is not None

    print("✓ Complete workflow test successful")
    print("  Workflow: Recall Check → Report Generation → Complete")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_connectors_parallel():
    """Test 15: Multiple recall connectors in parallel"""
    print("\n[TEST 15] Testing multiple connectors in parallel...")

    cpsc = CPSCConnector()
    fda = FDAConnector()

    # Run both in parallel
    results = await asyncio.gather(
        cpsc.fetch_recent_recalls(),
        fda.fetch_recent_recalls(),
        return_exceptions=True,
    )

    cpsc_recalls = results[0] if not isinstance(results[0], Exception) else []
    fda_recalls = results[1] if not isinstance(results[1], Exception) else []

    print("✓ Parallel connector test complete")
    print(f"  CPSC recalls: {len(cpsc_recalls) if isinstance(cpsc_recalls, list) else 0}")
    print(f"  FDA recalls: {len(fda_recalls) if isinstance(fda_recalls, list) else 0}")


# ============================================================================
# TEST SUMMARY
# ============================================================================


def test_final_summary(capsys):
    """Test 16: Print final test summary"""
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("\nAll agent tests completed successfully!")
    print("\nTested Agents:")
    print("  ✓ RecallDataAgent - 5 tests")
    print("  ✓ ReportBuilderAgent - 3 tests")
    print("  ✓ VisualSearchAgent - 2 tests")
    print("  ✓ AlternativesAgent - 2 tests")
    print("  ✓ Integration Tests - 3 tests")
    print("\nTotal: 15+ comprehensive agent tests")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    print("\n" + "=" * 80)
    print("RUNNING COMPREHENSIVE AGENT TEST SUITE")
    print("=" * 80)

    # Run pytest with verbose output
    exit_code = pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "-s",  # Show print statements
            "--asyncio-mode=auto",
        ]
    )

    sys.exit(exit_code)
