"""
Comprehensive test suite for EnhancedMemoryManager V2.0
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Now import from core_infra
from core_infra.enhanced_memory_manager import EnhancedMemoryManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_enhanced_memory():
    """Test all enhanced memory features"""

    print("Testing EnhancedMemoryManager V2.0...")

    try:
        # Initialize enhanced memory
        memory = EnhancedMemoryManager()

        # Test data
        test_workflow = {
            "goal": "Investigate Empagliflozin for Heart Failure treatment",
            "research_data": {
                "pubmed": {
                    "content": "Empagliflozin shows significant efficacy in heart failure patients. Clinical trials demonstrate reduced hospitalization."
                },
                "clinical_trials": {
                    "content": "Multiple randomized controlled trials confirm Empagliflozin safety and efficacy."
                },
                "drug_safety": {
                    "content": "Empagliflozin has a well-established safety profile with rare adverse events."
                },
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Test enhanced storage
        print("\n1. Testing enhanced workflow storage...")
        results = await memory.store_workflow_outputs_enhanced(test_workflow)

        print(f"SUCCESS: Standard storage: {results['standard_storage']['status']}")
        print(
            f"SUCCESS: Temporal analysis: {len(results['temporal_analysis'].get('patterns_detected', []))} patterns"
        )
        print(
            f"SUCCESS: Contradiction detection: {len(results['contradiction_detection'].get('contradictions_found', []))} contradictions"
        )
        print(
            f"SUCCESS: Gap analysis: {len(results['gap_analysis'].get('gaps_identified', []))} gaps"
        )
        print(
            f"SUCCESS: Cross-workflow insights: {len(results['cross_workflow_insights'].get('insights_generated', []))} insights"
        )

        # Test enhanced analytics
        print("\n2. Testing enhanced analytics...")
        analytics = memory.get_enhanced_analytics()

        print(f"SUCCESS: Total documents: {analytics['base_analytics']['total_documents']}")
        print(f"SUCCESS: Temporal patterns: {analytics['temporal_patterns']['total_patterns']}")
        print(f"SUCCESS: Contradictions: {analytics['contradictions']['total_contradictions']}")
        print(f"SUCCESS: Research gaps: {analytics['research_gaps']['total_gaps']}")
        print(
            f"SUCCESS: Cross-workflow insights: {analytics['cross_workflow_insights']['total_insights']}"
        )

        # Test enhanced recommendations
        print("\n3. Testing enhanced recommendations...")
        entities = {"drugs": ["Empagliflozin"], "indications": ["Heart Failure"]}
        recommendations = await memory.get_enhanced_research_recommendations(entities)

        print(
            f"SUCCESS: Priority research: {len(recommendations['priority_research'])} recommendations"
        )
        print(f"SUCCESS: Gap addressing: {len(recommendations['gap_addressing'])} suggestions")
        print(f"SUCCESS: Temporal insights: {len(recommendations['temporal_insights'])} insights")

        print("\nAll enhanced memory tests passed!")
        return True

    except Exception as e:
        print(f"\nEnhanced memory test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_basic_functionality():
    """Test basic memory functionality"""

    print("\n4. Testing basic functionality...")

    try:
        memory = EnhancedMemoryManager()

        # Test basic analytics
        analytics = memory.get_document_usage_analytics()
        print(f"SUCCESS: Basic analytics - Total documents: {analytics['total_documents']}")

        # Test similarity search
        if analytics["total_documents"] > 0:
            results = memory.find_similar_documents("SGLT2 inhibitor heart failure")
            print(f"SUCCESS: Similarity search returned {len(results)} results")
        else:
            print("INFO: No documents available for similarity search")

        return True

    except Exception as e:
        print(f"Basic functionality test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_memory_integration():
    """Test integration with existing memory data"""

    print("\n5. Testing memory integration...")

    try:
        memory = EnhancedMemoryManager()

        # Check if we can access existing data
        analytics = memory.get_document_usage_analytics()

        if analytics["total_documents"] > 0:
            print(f"SUCCESS: Found {analytics['total_documents']} existing documents")
            print(f"SUCCESS: High-quality documents: {analytics.get('high_quality_documents', 0)}")

            # Test cross-workflow evidence
            cross_evidence = analytics.get("cross_workflow_evidence", 0)
            print(f"SUCCESS: Cross-workflow evidence: {cross_evidence}")

        else:
            print("INFO: No existing documents found - starting with clean slate")

        return True

    except Exception as e:
        print(f"Memory integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def run_all_tests():
    """Run complete test suite"""

    print("Running EnhancedMemoryManager V2.0 Test Suite")
    print("=" * 50)

    tests = [test_enhanced_memory, test_basic_functionality, test_memory_integration]

    results = []

    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"Test {test.__name__} failed with exception: {e}")
            results.append(False)

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    passed = sum(results)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("All tests passed! EnhancedMemoryManager V2.0 is ready for use.")
        return True
    else:
        print("Some tests failed. Please check the output above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())

    if success:
        print("\nEnhancedMemoryManager V2.0 testing completed successfully!")
    else:
        print("\nTesting completed with some failures. Please review and fix issues.")
