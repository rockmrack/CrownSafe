#!/usr/bin/env python3
"""Comprehensive Test Suite Runner for BabyShield Backend
Runs all possible tests with detailed reporting and coverage analysis.
"""

import json
import os
import subprocess
import sys
from datetime import datetime


class ComprehensiveTestRunner:
    def __init__(self) -> None:
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "coverage_percentage": 0,
            "test_categories": {},
        }

    def run_command(self, cmd, category):
        """Run a test command and capture results."""
        print(f"\n{'=' * 80}")
        print(f"Running: {category}")
        print(f"Command: {' '.join(cmd)}")
        print(f"{'=' * 80}\n")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout per category
            )

            self.results["test_categories"][category] = {
                "status": "passed" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "stdout": result.stdout[-5000:],  # Last 5000 chars
                "stderr": result.stderr[-5000:] if result.stderr else "",
            }

            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print(f"⚠️  TIMEOUT: {category} took longer than 10 minutes")
            self.results["test_categories"][category] = {
                "status": "timeout",
                "returncode": -1,
            }
            return False
        except Exception as e:
            print(f"❌ ERROR running {category}: {e}")
            self.results["test_categories"][category] = {
                "status": "error",
                "error": str(e),
            }
            return False

    def run_all_tests(self) -> None:
        """Run comprehensive test suite."""
        test_suites = [
            # 1. Unit Tests (All test files)
            {
                "category": "1. Unit Tests - All Files",
                "command": [
                    "pytest",
                    "tests/",
                    "-v",
                    "--tb=short",
                    "-x",
                    "--maxfail=50",
                ],
            },
            # 2. Unit Tests with Coverage
            {
                "category": "2. Unit Tests with Coverage",
                "command": [
                    "pytest",
                    "tests/",
                    "--cov=.",
                    "--cov-report=term-missing",
                    "--cov-report=html",
                    "--cov-report=json",
                ],
            },
            # 3. Integration Tests
            {
                "category": "3. Integration Tests",
                "command": ["pytest", "tests/deep/", "-v", "--tb=short"],
            },
            # 4. API Endpoint Tests
            {
                "category": "4. API Endpoint Tests",
                "command": ["pytest", "tests/api/", "-v", "--tb=short"],
            },
            # 5. Security Tests
            {
                "category": "5. Security Tests",
                "command": ["pytest", "tests/security/", "-v", "--tb=short"],
            },
            # 6. Database Tests
            {
                "category": "6. Database Tests",
                "command": ["pytest", "tests/", "-k", "database", "-v", "--tb=short"],
            },
            # 7. Authentication Tests
            {
                "category": "7. Authentication Tests",
                "command": ["pytest", "tests/", "-k", "auth", "-v", "--tb=short"],
            },
            # 8. Chat/Conversation Tests
            {
                "category": "8. Chat/Conversation Tests",
                "command": [
                    "pytest",
                    "tests/",
                    "-k",
                    "chat or conversation",
                    "-v",
                    "--tb=short",
                ],
            },
            # 9. Agent Tests
            {
                "category": "9. Agent Tests",
                "command": ["pytest", "tests/agents/", "-v", "--tb=short"],
            },
            # 10. Performance Tests
            {
                "category": "10. Performance Tests",
                "command": [
                    "pytest",
                    "tests/deep/test_performance_deep.py",
                    "-v",
                    "--tb=short",
                ],
            },
            # 11. Smoke Tests
            {
                "category": "11. Smoke Tests (Local)",
                "command": ["pytest", "tests/_local_smoke_test.py", "-v", "--tb=short"],
            },
            # 12. Import Tests
            {
                "category": "12. Import Tests",
                "command": ["pytest", "tests/", "-k", "import", "-v", "--tb=short"],
            },
            # 13. Validation Tests
            {
                "category": "13. Validation Tests",
                "command": ["pytest", "tests/", "-k", "validat", "-v", "--tb=short"],
            },
            # 14. Encryption Tests
            {
                "category": "14. Encryption Tests",
                "command": ["pytest", "tests/test_encryption.py", "-v", "--tb=short"],
            },
            # 15. Error Handler Tests
            {
                "category": "15. Error Handler Tests",
                "command": [
                    "pytest",
                    "tests/test_error_handlers.py",
                    "-v",
                    "--tb=short",
                ],
            },
            # 16. Barcode Scanner Tests
            {
                "category": "16. Barcode Scanner Tests",
                "command": [
                    "pytest",
                    "tests/unit/",
                    "-k",
                    "barcode",
                    "-v",
                    "--tb=short",
                ],
            },
            # 17. Parallel Test Execution (Fast)
            {
                "category": "17. Parallel Tests (4 workers)",
                "command": ["pytest", "tests/unit/", "-n", "4", "-v"],
            },
            # 18. Strict Mode (Warnings as Errors)
            {
                "category": "18. Strict Mode Tests",
                "command": [
                    "pytest",
                    "tests/unit/",
                    "-v",
                    "--strict-markers",
                    "-W",
                    "error",
                ],
            },
            # 19. Doctest (Code Examples)
            {
                "category": "19. Doctest Validation",
                "command": ["pytest", "--doctest-modules", "api/", "core_infra/", "-v"],
            },
            # 20. Type Checking with mypy
            {
                "category": "20. Type Checking (mypy)",
                "command": [
                    "mypy",
                    "api/",
                    "core_infra/",
                    "--ignore-missing-imports",
                    "--no-error-summary",
                ],
            },
        ]

        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST SUITE EXECUTION")
        print("BabyShield Backend - Deep Testing")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")

        passed = 0
        failed = 0

        for suite in test_suites:
            success = self.run_command(suite["command"], suite["category"])
            if success:
                passed += 1
                print(f"✅ {suite['category']}: PASSED")
            else:
                failed += 1
                print(f"❌ {suite['category']}: FAILED")

        # Generate final report
        self.generate_report(passed, failed, len(test_suites))

    def generate_report(self, passed, failed, total) -> None:
        """Generate comprehensive test report."""
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST REPORT")
        print("=" * 80 + "\n")

        print(f"Total Test Suites: {total}")
        print(f"Passed: {passed} ({passed / total * 100:.1f}%)")
        print(f"Failed: {failed} ({failed / total * 100:.1f}%)")
        print(f"\nTimestamp: {self.results['timestamp']}")

        # Read coverage data if available
        try:
            if os.path.exists("coverage.json"):
                with open("coverage.json", "r") as f:
                    cov_data = json.load(f)
                    total_cov = cov_data.get("totals", {}).get("percent_covered", 0)
                    print(f"\n📊 Code Coverage: {total_cov:.2f}%")
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass  # Coverage file not found or invalid

        print("\n" + "=" * 80)
        print("CATEGORY BREAKDOWN")
        print("=" * 80 + "\n")

        for category, data in self.results["test_categories"].items():
            status_icon = "✅" if data["status"] == "passed" else "❌"
            print(f"{status_icon} {category}: {data['status'].upper()}")

        # Save detailed report
        report_path = "test_report_comprehensive.json"
        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\n📄 Detailed report saved to: {report_path}")

        # Exit with appropriate code
        if failed == 0:
            print("\n🎉 ALL TEST SUITES PASSED!")
            sys.exit(0)
        else:
            print(f"\n⚠️  {failed} test suite(s) failed. Review logs above.")
            sys.exit(1)


if __name__ == "__main__":
    runner = ComprehensiveTestRunner()
    runner.run_all_tests()
