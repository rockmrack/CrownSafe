# C:\Users\rossd\Downloads\RossNetAgents\scripts\check_memory_content.py
# Version: 2.1 (FIXED - Cross-Workflow Evidence Validation)
# Complete validation suite with corrected cross-workflow testing

import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import MemoryManager
try:
    from core_infra.memory_manager import MemoryManager
except ImportError as e:
    print(f"[FAIL] CRITICAL ERROR: Could not import MemoryManager: {e}")
    print("       Make sure core_infra/memory_manager.py exists with MVP-1.4 code")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("memory_validator")


class MemoryValidationSuite:
    """Comprehensive validation suite for MemoryManager MVP-1.4"""

    def __init__(self):
        self.memory: Optional[MemoryManager] = None
        self.test_results = {
            "basic_functionality": False,
            "enhanced_retrieval": False,
            "memory_augmented_methods": False,
            "analytics": False,
            "performance": {},
        }

    def print_header(self, title: str, level: int = 1):
        """Print formatted section headers"""
        if level == 1:
            print(f"\n{'=' * 80}")
            print(f"[TEST] {title}")
            print(f"{'=' * 80}")
        else:
            print(f"\n{'-' * 60}")
            print(f"[STEP] {title}")
            print(f"{'-' * 60}")

    def print_success(self, message: str):
        """Print success message"""
        print(f"[PASS] {message}")

    def print_error(self, message: str):
        """Print error message"""
        print(f"[FAIL] {message}")

    def print_info(self, message: str):
        """Print info message"""
        print(f"[INFO] {message}")

    async def initialize_memory(self) -> bool:
        """Initialize and validate MemoryManager connection"""
        self.print_header("Memory Manager Initialization", 2)

        # Load environment
        dotenv_path = os.path.join(project_root, ".env")
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
            self.print_success(f"Loaded .env from {dotenv_path}")
        else:
            self.print_error(f"No .env file found at {dotenv_path}")
            return False

        # Initialize MemoryManager
        try:
            self.memory = MemoryManager()
            if not self.memory.collection:
                self.print_error("MemoryManager failed to initialize collection")
                return False

            count = self.memory.collection.count()
            self.print_success(f"Connected to ChromaDB collection '{self.memory.collection_name}'")
            self.print_success(f"Database path: {self.memory.db_path}")
            self.print_success(f"Document count: {count}")

            if count == 0:
                self.print_error("Collection is empty - no data to test with")
                return False

            return True

        except Exception as e:
            self.print_error(f"Failed to initialize MemoryManager: {e}")
            logger.exception("Initialization error details:")
            return False

    async def test_basic_functionality(self) -> bool:
        """Test core MemoryManager functionality - FIXED VERSION"""
        self.print_header("Basic Functionality Tests", 2)

        try:
            # Test 1: Basic retrieval (backward compatibility)
            self.print_info("Testing basic document retrieval...")
            basic_results = await self.memory.retrieve_similar_documents(query_text="SGLT2 inhibitors", n_results=3)

            if not basic_results:
                self.print_error("Basic retrieval returned no results")
                return False

            self.print_success(f"Basic retrieval: {len(basic_results)} documents found")

            # Test 2: FIXED - Check cross-workflow evidence using analytics
            self.print_info("Checking for cross-workflow evidence using analytics...")
            analytics = await self.memory.get_document_usage_analytics()

            if not analytics or "error" in analytics:
                self.print_error("Could not get analytics to check cross-workflow evidence")
                return False

            cross_workflow_count = len(analytics.get("cross_workflow_evidence", []))
            high_quality_count = analytics.get("quality_metrics", {}).get("high_quality_documents", 0)

            if cross_workflow_count > 0:
                self.print_success(f"Cross-workflow evidence confirmed: {cross_workflow_count} documents")
                self.print_info(f"High-quality documents (ref_count >= 2): {high_quality_count}")

                # Show examples of cross-workflow documents
                cross_workflow_docs = analytics.get("cross_workflow_evidence", [])[:3]
                for i, doc in enumerate(cross_workflow_docs):
                    workflows = doc.get("workflows", [])
                    drugs = doc.get("drugs", [])
                    self.print_info(f"  Example {i + 1}: {doc.get('id')} - Workflows: {len(workflows)}, Drugs: {drugs}")

                _ = True  # cross_workflow_found
            else:
                self.print_error("No cross-workflow documents found (analytics check)")
                return False

            # Test 3: Verify specific high-quality retrieval
            self.print_info("Testing high-quality document retrieval...")
            high_quality_results = await self.memory.retrieve_similar_documents(
                query_text="heart failure treatment",
                n_results=5,
                quality_threshold=2,  # Only documents with reference_count >= 2
            )

            if high_quality_results:
                self.print_success(f"High-quality retrieval: {len(high_quality_results)} documents")
                for result in high_quality_results:
                    ref_count = result.get("metadata", {}).get("reference_count", 1)
                    self.print_info(f"  Document {result['id']}: reference_count = {ref_count}")
            else:
                self.print_error("No high-quality documents found with quality_threshold=2")
                return False

            self.test_results["basic_functionality"] = True
            return True

        except Exception as e:
            self.print_error(f"Basic functionality test failed: {e}")
            logger.exception("Basic test error details:")
            return False

    async def test_enhanced_retrieval(self) -> bool:
        """Test enhanced retrieval features"""
        self.print_header("Enhanced Retrieval Features", 2)

        try:
            # Test 1: Context history parsing
            self.print_info("Testing context history parsing...")
            start_time = time.time()

            context_results = await self.memory.retrieve_similar_documents(
                query_text="heart failure treatment",
                n_results=3,
                include_context_history=True,
                quality_threshold=1,
            )

            retrieval_time = time.time() - start_time
            self.test_results["performance"]["context_retrieval_time"] = retrieval_time

            if not context_results:
                self.print_error("Context history retrieval failed")
                return False

            # Check if context history is properly parsed
            context_found = False
            for result in context_results:
                if "context_history" in result:
                    context = result["context_history"]
                    self.print_success(f"Context history found for {result['id']}")
                    self.print_info(f"  Workflows: {len(context.get('referenced_workflows', []))}")
                    self.print_info(f"  Goals: {len(context.get('user_goals', []))}")
                    self.print_info(f"  Drugs: {context.get('drug_contexts', [])}")
                    self.print_info(f"  Reference count: {context.get('reference_count', 1)}")
                    context_found = True
                    break

            if not context_found:
                self.print_error("No context history found in results")
                return False

            # Test 2: Quality filtering validation
            self.print_info("Testing quality filtering...")
            high_quality_results = await self.memory.retrieve_similar_documents(
                query_text="SGLT2 inhibitors",
                n_results=5,
                quality_threshold=2,  # Only high-quality evidence
            )

            all_high_quality = all(
                result.get("metadata", {}).get("reference_count", 1) >= 2 for result in high_quality_results
            )

            if all_high_quality and high_quality_results:
                self.print_success(f"Quality filtering works: {len(high_quality_results)} high-quality documents")
            else:
                self.print_error("Quality filtering not working correctly")
                return False

            # Test 3: Recency weighting
            self.print_info("Testing recency weighting...")
            recency_results = await self.memory.retrieve_similar_documents(
                query_text="diabetes treatment", n_results=3, recency_weight=0.3
            )

            if recency_results and "adjusted_distance" in recency_results[0]:
                self.print_success("Recency weighting applied")
            else:
                self.print_error("Recency weighting not working")
                return False

            self.test_results["enhanced_retrieval"] = True
            return True

        except Exception as e:
            self.print_error(f"Enhanced retrieval test failed: {e}")
            logger.exception("Enhanced retrieval error details:")
            return False

    async def test_memory_augmented_methods(self) -> bool:
        """Test new memory-augmented methods for PlannerAgent"""
        self.print_header("Memory-Augmented Methods", 2)

        try:
            # Test 1: Find similar workflows
            self.print_info("Testing find_similar_workflows...")
            start_time = time.time()

            similar_workflows = await self.memory.find_similar_workflows(
                user_goal="Investigate SGLT2 inhibitor safety for heart failure patients",
                n_results=2,
            )

            workflow_time = time.time() - start_time
            self.test_results["performance"]["workflow_search_time"] = workflow_time

            if similar_workflows:
                self.print_success(f"Found {len(similar_workflows)} similar workflows")
                for i, wf in enumerate(similar_workflows):
                    goal = wf.get("metadata", {}).get("user_goal", "N/A")
                    self.print_info(f"  {i + 1}. {goal[:80]}...")
            else:
                self.print_error("No similar workflows found")
                return False

            # Test 2: Get evidence for entities
            self.print_info("Testing get_evidence_for_entities...")
            start_time = time.time()

            evidence = await self.memory.get_evidence_for_entities(
                drug_name="Canagliflozin",
                disease_name="Heart Failure",
                min_quality=1,
                n_results=5,
            )

            entity_time = time.time() - start_time
            self.test_results["performance"]["entity_search_time"] = entity_time

            if evidence:
                pubmed_count = len(evidence.get("pubmed", []))
                trials_count = len(evidence.get("trials", []))
                safety_count = len(evidence.get("safety", []))

                self.print_success(
                    f"Evidence found - PubMed: {pubmed_count}, Trials: {trials_count}, Safety: {safety_count}"
                )

                if pubmed_count == 0 and trials_count == 0:
                    self.print_error("No evidence found for known entities")
                    return False
            else:
                self.print_error("get_evidence_for_entities returned no data")
                return False

            # Test 3: Research recommendations
            self.print_info("Testing get_research_recommendations...")
            recommendations = await self.memory.get_research_recommendations(
                user_goal="Study cardiovascular effects of new diabetes medications",
                drug_name="Dapagliflozin",
                disease_name="Heart Failure",
            )

            if recommendations:
                strategy = recommendations.get("research_strategy", "unknown")
                gaps = recommendations.get("knowledge_gaps", [])
                priorities = recommendations.get("priority_areas", [])

                self.print_success("Research recommendations generated")
                self.print_info(f"  Strategy: {strategy}")
                self.print_info(f"  Knowledge gaps: {gaps}")
                self.print_info(f"  Priority areas: {priorities}")

                if strategy == "unknown":
                    self.print_error("Research strategy not properly determined")
                    return False
            else:
                self.print_error("No research recommendations generated")
                return False

            self.test_results["memory_augmented_methods"] = True
            return True

        except Exception as e:
            self.print_error(f"Memory-augmented methods test failed: {e}")
            logger.exception("Memory-augmented methods error details:")
            return False

    async def test_analytics(self) -> bool:
        """Test enhanced analytics functionality"""
        self.print_header("Enhanced Analytics", 2)

        try:
            self.print_info("Testing get_document_usage_analytics...")
            start_time = time.time()

            analytics = await self.memory.get_document_usage_analytics()

            analytics_time = time.time() - start_time
            self.test_results["performance"]["analytics_time"] = analytics_time

            if not analytics or "error" in analytics:
                self.print_error(f"Analytics failed: {analytics.get('error', 'Unknown error')}")
                return False

            # Validate analytics structure
            required_fields = [
                "total_documents",
                "most_referenced",
                "workflow_coverage",
                "content_type_distribution",
                "quality_metrics",
                "drug_class_patterns",
            ]

            missing_fields = [field for field in required_fields if field not in analytics]
            if missing_fields:
                self.print_error(f"Missing analytics fields: {missing_fields}")
                return False

            # Display key analytics
            self.print_success("Analytics generated successfully")
            self.print_info(f"  Total documents: {analytics['total_documents']}")
            self.print_info(
                f"  High-quality documents: {analytics['quality_metrics'].get('high_quality_documents', 0)}"
            )
            self.print_info(f"  Drug patterns found: {len(analytics['drug_class_patterns'])}")
            self.print_info(f"  Cross-workflow evidence: {len(analytics.get('cross_workflow_evidence', []))}")

            # Show top drug patterns
            if analytics["drug_class_patterns"]:
                self.print_info("  Top drug patterns:")
                for drug, data in list(analytics["drug_class_patterns"].items())[:3]:
                    self.print_info(f"    {drug}: {data['document_count']} docs, {data['workflow_count']} workflows")

            self.test_results["analytics"] = True
            return True

        except Exception as e:
            self.print_error(f"Analytics test failed: {e}")
            logger.exception("Analytics error details:")
            return False

    def print_performance_summary(self):
        """Print performance metrics summary"""
        self.print_header("Performance Summary", 2)

        perf = self.test_results["performance"]
        if not perf:
            self.print_info("No performance metrics collected")
            return

        for metric, value in perf.items():
            self.print_info(f"{metric.replace('_', ' ').title()}: {value:.3f}s")

        # Overall assessment
        total_time = sum(perf.values())
        if total_time < 5.0:
            self.print_success(f"Excellent performance: {total_time:.2f}s total")
        elif total_time < 10.0:
            self.print_success(f"Good performance: {total_time:.2f}s total")
        else:
            self.print_error(f"Slow performance: {total_time:.2f}s total")

    def print_final_summary(self):
        """Print final test summary"""
        self.print_header("Final Validation Summary")

        total_tests = len([k for k in self.test_results.keys() if k != "performance"])
        passed_tests = sum(1 for k, v in self.test_results.items() if k != "performance" and v)

        print(f"[RESULTS] Test Results: {passed_tests}/{total_tests} passed")

        for test_name, passed in self.test_results.items():
            if test_name == "performance":
                continue

            status = "[PASS]" if passed else "[FAIL]"
            test_display = test_name.replace("_", " ").title()
            print(f"  {test_display}: {status}")

        if passed_tests == total_tests:
            print("\n[SUCCESS] ALL TESTS PASSED! MemoryManager MVP-1.4 is working correctly!")
            print("[PASS] Enhanced features are functional")
            print("[PASS] Cross-workflow learning validated")
            print("[PASS] Memory-augmented methods ready for PlannerAgent integration")
        else:
            print(f"\n[WARNING] {total_tests - passed_tests} test(s) failed. Please review errors above.")
            print("[FAIL] MemoryManager MVP-1.4 needs fixes before proceeding")

    async def run_full_validation(self):
        """Run complete validation suite"""
        print("[START] Starting MemoryManager MVP-1.4 Validation Suite - FIXED VERSION")
        print(f"[TIME] Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Initialize
        if not await self.initialize_memory():
            self.print_error("Initialization failed - cannot continue")
            return

        # Run test suite
        await self.test_basic_functionality()
        await self.test_enhanced_retrieval()
        await self.test_memory_augmented_methods()
        await self.test_analytics()

        # Print summaries
        self.print_performance_summary()
        self.print_final_summary()

        print(f"\n[TIME] Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


async def main():
    """Main entry point"""
    validator = MemoryValidationSuite()
    await validator.run_full_validation()


if __name__ == "__main__":
    asyncio.run(main())
