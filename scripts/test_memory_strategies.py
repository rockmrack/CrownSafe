# C:\Users\rossd\Downloads\RossNetAgents\scripts\test_memory_strategies.py
# Version: 1.0 - Systematic Strategy Testing for Memory-Augmented Planner
# Tests how the planner adapts strategies based on existing knowledge

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Any

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.test_commander_flow import run_commander_flow  # noqa: E402

# Test scenarios designed to trigger different strategies
TEST_SCENARIOS = [
    {
        "name": "SGLT2_Fourth_Drug",
        "query": "Investigate the efficacy and safety of Ertugliflozin for treating Heart Failure, including at least 10 recent clinical trials and 10 published articles",  # noqa: E501
        "expected_strategy": "update",  # Should recognize 3 SGLT2s already in memory
        "rationale": "Fourth SGLT2 inhibitor after Cana/Dapa/Empa - should trigger update strategy",
    },
    {
        "name": "Different_Drug_Class_Same_Condition",
        "query": "Investigate the efficacy and safety of Lisinopril for treating Heart Failure, including comprehensive safety profile",  # noqa: E501
        "expected_strategy": "focused",  # Has heart failure data but new drug class
        "rationale": "ACE inhibitor for heart failure - new drug class but known condition",
    },
    {
        "name": "Known_Drug_New_Condition",
        "query": "Investigate the efficacy and safety of Empagliflozin for treating Diabetic Nephropathy",
        "expected_strategy": "focused",  # Has Empagliflozin data but new indication
        "rationale": "Known SGLT2 inhibitor but new condition - should focus on new indication",
    },
    {
        "name": "Completely_New_Drug",
        "query": "Investigate the efficacy and safety of Tirzepatide for treating Type 2 Diabetes with cardiovascular outcomes",  # noqa: E501
        "expected_strategy": "comprehensive",  # Completely new drug
        "rationale": "New GLP-1/GIP dual agonist - no existing data",
    },
    {
        "name": "Update_Recent_Only",
        "query": "Find the latest 2025 studies on Canagliflozin for Heart Failure focusing on real-world evidence",
        "expected_strategy": "update",  # Explicitly asking for updates
        "rationale": "Explicit request for latest updates on well-studied drug",
    },
]


class MemoryStrategyTester:
    """Tests memory-augmented planner strategies systematically."""

    def __init__(self) -> None:
        self.results = []
        self.logs_dir = os.path.join(project_root, "logs")
        self.test_results_dir = os.path.join(project_root, "test_results")
        os.makedirs(self.test_results_dir, exist_ok=True)

    async def run_test_scenario(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Run a single test scenario."""
        print(f"\n{'=' * 60}")
        print(f"TEST: {scenario['name']}")
        print(f"Query: {scenario['query'][:100]}...")
        print(f"Expected Strategy: {scenario['expected_strategy']}")
        print(f"{'=' * 60}")

        start_time = time.time()
        result = {
            "scenario": scenario,
            "start_time": datetime.now().isoformat(),
            "success": False,
            "actual_strategy": None,
            "strategy_match": False,
            "execution_time": None,
            "error": None,
            "workflow_id": None,
        }

        try:
            # Run the workflow
            print("\nStarting workflow...")
            _ = await run_commander_flow(scenario["query"])  # workflow_result

            # Allow time for completion
            await asyncio.sleep(10)

            # Analyze planner logs
            strategy_found = self._extract_strategy_from_logs()
            result["actual_strategy"] = strategy_found
            result["strategy_match"] = strategy_found == scenario["expected_strategy"]
            result["success"] = True
            result["workflow_id"] = self._extract_workflow_id()

            print("\n✓ Test completed")
            print(f"  Expected: {scenario['expected_strategy']}")
            print(f"  Actual: {strategy_found}")
            print(f"  Match: {'✓' if result['strategy_match'] else '✗'}")

        except Exception as e:
            result["error"] = str(e)
            print(f"\n✗ Test failed: {e}")

        result["execution_time"] = time.time() - start_time
        result["end_time"] = datetime.now().isoformat()

        self.results.append(result)
        return result

    def _extract_strategy_from_logs(self) -> str | None:
        """Extract strategy from latest planner log."""
        try:
            # Find latest planner log
            planner_logs = [
                f for f in os.listdir(self.logs_dir) if f.startswith("planner_agent_") and f.endswith(".log")
            ]
            if not planner_logs:
                return None

            latest_log = max(
                planner_logs,
                key=lambda f: os.path.getmtime(os.path.join(self.logs_dir, f)),
            )
            log_path = os.path.join(self.logs_dir, latest_log)

            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()

                # Look for strategy in various formats
                import re

                # Memory insights pattern
                match = re.search(r"Memory insights gathered: (\w+) strategy recommended", content)
                if match:
                    return match.group(1)

                # Plan creation pattern
                match = re.search(r"plan created successfully with (\w+) strategy", content)
                if match:
                    return match.group(1)

                # Fallback plan pattern
                match = re.search(r"Fallback plan created with (\w+) strategy", content)
                if match:
                    return match.group(1)

                # Check in JSON plan
                match = re.search(r'"research_strategy":\s*"(\w+)"', content)
                if match:
                    return match.group(1)

        except Exception as e:
            print(f"Error extracting strategy: {e}")

        return None

    def _extract_workflow_id(self) -> str | None:
        """Extract workflow ID from commander logs."""
        try:
            commander_logs = [
                f for f in os.listdir(self.logs_dir) if f.startswith("commander_agent_") and f.endswith(".log")
            ]
            if not commander_logs:
                return None

            latest_log = max(
                commander_logs,
                key=lambda f: os.path.getmtime(os.path.join(self.logs_dir, f)),
            )
            log_path = os.path.join(self.logs_dir, latest_log)

            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()

                import re

                match = re.search(r"Starting new workflow: ([a-f0-9-]+)", content)
                if match:
                    return match.group(1)

        except Exception as e:
            print(f"Error extracting workflow ID: {e}")

        return None

    async def run_all_tests(self, scenarios: list[dict[str, Any]] | None = None) -> None:
        """Run all test scenarios."""
        if scenarios is None:
            scenarios = TEST_SCENARIOS

        print("\n" + "=" * 60)
        print("MEMORY-AUGMENTED PLANNER STRATEGY TESTING")
        print(f"Running {len(scenarios)} test scenarios")
        print("=" * 60)

        for scenario in scenarios:
            await self.run_test_scenario(scenario)

            # Wait between tests to avoid overwhelming the system
            if scenario != scenarios[-1]:
                print("\nWaiting 30 seconds before next test...")
                await asyncio.sleep(30)

        # Generate summary report
        self.generate_summary_report()

    def generate_summary_report(self) -> None:
        """Generate summary report of all tests."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY REPORT")
        print("=" * 60)

        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r["success"])
        strategy_matches = sum(1 for r in self.results if r["strategy_match"])

        print(f"\nTotal Tests: {total_tests}")
        print(f"Successful: {successful_tests} ({successful_tests / total_tests * 100:.1f}%)")
        print(f"Strategy Matches: {strategy_matches} ({strategy_matches / total_tests * 100:.1f}%)")

        print("\nDetailed Results:")
        print("-" * 60)

        for result in self.results:
            scenario = result["scenario"]
            print(f"\nTest: {scenario['name']}")
            print(f"  Expected: {scenario['expected_strategy']}")
            print(f"  Actual: {result['actual_strategy'] or 'ERROR'}")
            print(f"  Match: {'✓' if result['strategy_match'] else '✗'}")
            print(f"  Time: {result['execution_time']:.1f}s")
            if result.get("error"):
                print(f"  Error: {result['error']}")

        # Save detailed results
        report_file = os.path.join(
            self.test_results_dir,
            f"strategy_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )

        with open(report_file, "w") as f:
            json.dump(
                {
                    "summary": {
                        "total_tests": total_tests,
                        "successful": successful_tests,
                        "strategy_matches": strategy_matches,
                        "accuracy": strategy_matches / total_tests * 100 if total_tests > 0 else 0,
                    },
                    "results": self.results,
                    "test_completed": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

        print(f"\n✓ Detailed report saved to: {report_file}")

        # Recommendations
        print("\n" + "=" * 60)
        print("RECOMMENDATIONS")
        print("=" * 60)

        if strategy_matches < total_tests * 0.8:
            print("⚠ Strategy selection accuracy below 80% - consider refining:")
            print("  1. Review entity extraction patterns")
            print("  2. Adjust memory insight thresholds")
            print("  3. Refine GPT-4 prompt instructions")
        else:
            print("✓ Excellent strategy selection accuracy!")

        # Check for specific patterns
        update_tests = [r for r in self.results if r["scenario"]["expected_strategy"] == "update"]
        update_correct = sum(1 for r in update_tests if r["strategy_match"])
        if update_tests and update_correct < len(update_tests):
            print("\n⚠ Update strategy detection needs improvement")
            print("  Consider: Lowering threshold for existing evidence")


async def main() -> None:
    """Main test function."""
    tester = MemoryStrategyTester()

    # You can run all tests or specific ones
    print("Select test mode:")
    print("1. Run all tests")
    print("2. Run single test (Ertugliflozin)")
    print("3. Run custom test")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == "1":
        await tester.run_all_tests()
    elif choice == "2":
        # Just test Ertugliflozin
        await tester.run_all_tests([TEST_SCENARIOS[0]])
    elif choice == "3":
        custom_query = input("Enter custom query: ").strip()
        custom_scenario = {
            "name": "Custom_Test",
            "query": custom_query,
            "expected_strategy": input("Expected strategy (comprehensive/focused/update): ").strip(),
            "rationale": "Custom test scenario",
        }
        await tester.run_all_tests([custom_scenario])
    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
