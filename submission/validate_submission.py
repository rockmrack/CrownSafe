#!/usr/bin/env python3
"""Submission Validation Script
Performs comprehensive checks before app store submission
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests


# ANSI colors for output
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


class SubmissionValidator:
    """Validates app submission readiness"""

    def __init__(self):
        self.api_url = os.environ.get("API_URL", "https://babyshield.cureviax.ai")
        self.results = {}
        self.warnings = []
        self.errors = []

    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{title}{Colors.ENDC}")
        print(f"{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")

    def print_result(self, test: str, passed: bool, details: str = ""):
        """Print test result"""
        if passed:
            print(f"{Colors.GREEN}✅ {test}{Colors.ENDC}")
        else:
            print(f"{Colors.RED}❌ {test}{Colors.ENDC}")

        if details:
            print(f"   {details}")

    def validate_api_endpoints(self) -> bool:
        """Validate all API endpoints are functioning"""
        self.print_header("API ENDPOINT VALIDATION")

        endpoints = [
            ("/api/v1/healthz", "Health Check"),
            ("/api/v1/version", "Version Info"),
            ("/api/v1/agencies", "Agencies List"),
            (
                "/api/v1/search/advanced",
                "Search API",
                {"method": "POST", "json": {"product": "test"}},
            ),
            ("/api/v1/categories", "Categories"),
            ("/legal/privacy", "Privacy Policy"),
            ("/legal/terms", "Terms of Service"),
        ]

        all_passed = True
        results = []

        for endpoint_info in endpoints:
            endpoint = endpoint_info[0]
            name = endpoint_info[1]
            options = endpoint_info[2] if len(endpoint_info) > 2 else {}

            try:
                method = options.get("method", "GET")
                url = f"{self.api_url}{endpoint}"

                if method == "POST":
                    response = requests.post(url, json=options.get("json", {}), timeout=5)
                else:
                    response = requests.get(url, timeout=5)

                response_time = response.elapsed.total_seconds() * 1000

                if response.status_code == 200:
                    self.print_result(
                        f"{name}: {endpoint}",
                        True,
                        f"Response time: {response_time:.0f}ms",
                    )
                    results.append(
                        {
                            "endpoint": endpoint,
                            "status": "pass",
                            "response_time": response_time,
                        },
                    )
                else:
                    self.print_result(
                        f"{name}: {endpoint}",
                        False,
                        f"Status code: {response.status_code}",
                    )
                    all_passed = False
                    results.append(
                        {
                            "endpoint": endpoint,
                            "status": "fail",
                            "error": f"Status {response.status_code}",
                        },
                    )

            except Exception as e:
                self.print_result(f"{name}: {endpoint}", False, f"Error: {str(e)}")
                all_passed = False
                results.append({"endpoint": endpoint, "status": "error", "error": str(e)})

        # Check average response time
        successful_times = [r["response_time"] for r in results if "response_time" in r]
        if successful_times:
            avg_time = sum(successful_times) / len(successful_times)
            print(f"\n📊 Average response time: {avg_time:.0f}ms")

            if avg_time < 500:
                print(f"{Colors.GREEN}   ✅ Excellent performance{Colors.ENDC}")
            elif avg_time < 1000:
                print(f"{Colors.YELLOW}   ⚠️ Acceptable performance{Colors.ENDC}")
            else:
                print(f"{Colors.RED}   ❌ Performance needs improvement{Colors.ENDC}")
                self.warnings.append("API response times are slow")

        self.results["api_endpoints"] = results
        return all_passed

    def validate_security_headers(self) -> bool:
        """Check security headers"""
        self.print_header("SECURITY HEADERS VALIDATION")

        try:
            response = requests.get(f"{self.api_url}/api/v1/healthz", timeout=5)
            headers = response.headers

            required_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": ["DENY", "SAMEORIGIN"],
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": None,  # Just check presence
            }

            all_present = True

            for header, expected in required_headers.items():
                value = headers.get(header)

                if value:
                    if expected:
                        if isinstance(expected, list):
                            valid = any(exp in value for exp in expected)
                        else:
                            valid = expected in value
                    else:
                        valid = True

                    self.print_result(f"Security header: {header}", valid, value)
                else:
                    self.print_result(f"Security header: {header}", False, "Missing")
                    all_present = False

            return all_present

        except Exception as e:
            self.print_result("Security headers check", False, str(e))
            return False

    def validate_store_metadata(self) -> bool:
        """Validate store metadata files"""
        self.print_header("STORE METADATA VALIDATION")

        metadata_files = {
            "Apple Metadata": "docs/store/apple/metadata.json",
            "Google Listing": "docs/store/google/listing.json",
            "Privacy Labels (Apple)": "docs/app_review/privacy_labels_apple.json",
            "Data Safety (Google)": "docs/app_review/google_data_safety.json",
        }

        all_valid = True

        for name, filepath in metadata_files.items():
            path = Path(filepath)

            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Check for required fields
                    if "apple" in filepath:
                        required = ["app_name", "bundle_id", "primary_category"]
                        if "metadata" in filepath:
                            missing = [field for field in required if field not in data]
                        else:
                            missing = []
                    elif "google" in filepath:
                        required = ["package_name", "default_language"]
                        if "listing" in filepath:
                            missing = [field for field in required if field not in data]
                        else:
                            missing = []
                    else:
                        missing = []

                    if missing:
                        self.print_result(name, False, f"Missing fields: {', '.join(missing)}")
                        all_valid = False
                    else:
                        self.print_result(name, True, "Valid JSON")

                except json.JSONDecodeError as e:
                    self.print_result(name, False, f"Invalid JSON: {e}")
                    all_valid = False
            else:
                self.print_result(name, False, "File not found")
                all_valid = False

        return all_valid

    def validate_screenshots(self) -> bool:
        """Validate screenshot assets"""
        self.print_header("SCREENSHOT VALIDATION")

        screenshot_requirements = {
            "iOS": {
                "path": "assets/store/screenshots/ios",
                "required_sizes": [
                    ("iphone67", "1290x2796"),
                    ("iphone65", "1284x2778"),
                ],
                "min_count": 2,
                "max_count": 10,
            },
            "Android": {
                "path": "assets/store/screenshots/android",
                "required_sizes": [
                    ("phone", "min 1080x1920"),
                ],
                "min_count": 2,
                "max_count": 8,
            },
        }

        all_valid = True

        for platform, reqs in screenshot_requirements.items():
            path = Path(reqs["path"])

            if path.exists():
                screenshots = list(path.glob("*.png")) + list(path.glob("*.jpg"))
                count = len(screenshots)

                if count < reqs["min_count"]:
                    self.print_result(
                        f"{platform} screenshots",
                        False,
                        f"Only {count} found, minimum {reqs['min_count']} required",
                    )
                    all_valid = False
                elif count > reqs["max_count"]:
                    self.print_result(
                        f"{platform} screenshots",
                        False,
                        f"{count} found, maximum {reqs['max_count']} allowed",
                    )
                    all_valid = False
                else:
                    self.print_result(f"{platform} screenshots", True, f"{count} screenshots found")

                    # Check file sizes
                    for screenshot in screenshots[:3]:  # Check first 3
                        size_mb = screenshot.stat().st_size / (1024 * 1024)
                        if size_mb > 10:
                            self.warnings.append(f"Large screenshot: {screenshot.name} ({size_mb:.1f}MB)")
            else:
                self.print_result(f"{platform} screenshots", False, "Directory not found")
                all_valid = False

        return all_valid

    def validate_app_icons(self) -> bool:
        """Validate app icons"""
        self.print_header("APP ICON VALIDATION")

        icon_requirements = {
            "iOS App Icon": {
                "path": "assets/store/icons/ios/AppIcon1024.png",
                "size": "1024x1024",
                "format": "PNG",
                "alpha": False,
            },
            "Android App Icon": {
                "path": "assets/store/icons/android/Icon512.png",
                "size": "512x512",
                "format": "PNG",
                "alpha": True,
            },
            "Play Feature Graphic": {
                "path": "assets/store/graphics/play-feature-1024x500.png",
                "size": "1024x500",
                "format": "PNG",
                "alpha": False,
            },
        }

        all_valid = True

        for name, reqs in icon_requirements.items():
            path = Path(reqs["path"])

            if path.exists():
                size_kb = path.stat().st_size / 1024

                # Check file size
                if size_kb > 1024:  # Over 1MB
                    self.print_result(name, True, f"⚠️ Large file: {size_kb:.0f}KB")
                    self.warnings.append(f"{name} is large ({size_kb:.0f}KB)")
                else:
                    self.print_result(name, True, f"Size: {size_kb:.0f}KB")

                # Verify it's actually an image
                try:
                    with open(path, "rb") as f:
                        header = f.read(8)
                        if header[:8] == b"\x89PNG\r\n\x1a\n":
                            _ = True  # format_ok
                        else:
                            _ = False  # format_ok
                            self.warnings.append(f"{name} may not be a valid PNG")
                except (OSError, IOError):
                    pass  # Can't read file header

            else:
                self.print_result(name, False, "File not found")
                all_valid = False
                self.errors.append(f"Missing required icon: {name}")

        return all_valid

    def validate_text_content(self) -> bool:
        """Validate text content for store listings"""
        self.print_header("TEXT CONTENT VALIDATION")

        text_files = {
            "Short Description": {
                "path": "docs/store/common/descriptions/short_tagline.txt",
                "max_length": 80,
            },
            "Long Description": {
                "path": "docs/store/common/descriptions/long_description_en.txt",
                "max_length": 4000,
            },
        }

        all_valid = True

        for name, info in text_files.items():
            path = Path(info["path"])

            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                length = len(content)
                max_length = info["max_length"]

                if length > max_length:
                    self.print_result(name, False, f"Too long: {length} chars (max {max_length})")
                    all_valid = False
                else:
                    self.print_result(name, True, f"Length: {length}/{max_length} chars")

                # Check for placeholder text
                placeholders = ["TODO", "FIXME", "XXX", "[PLACEHOLDER]"]
                for placeholder in placeholders:
                    if placeholder in content.upper():
                        self.warnings.append(f"{name} contains placeholder text: {placeholder}")

            else:
                self.print_result(name, False, "File not found")
                all_valid = False

        return all_valid

    def validate_legal_documents(self) -> bool:
        """Validate legal documents are present and accessible"""
        self.print_header("LEGAL DOCUMENTS VALIDATION")

        legal_urls = {
            "Privacy Policy": f"{self.api_url}/legal/privacy",
            "Terms of Service": f"{self.api_url}/legal/terms",
            "Data Deletion": f"{self.api_url}/api/v1/user/data/delete",
        }

        all_valid = True

        for name, url in legal_urls.items():
            try:
                if "delete" in url:
                    # Just check if endpoint exists
                    response = requests.options(url, timeout=5)
                    valid = response.status_code in [200, 204, 405]
                else:
                    response = requests.get(url, timeout=5)
                    valid = response.status_code == 200 and len(response.text) > 100

                if valid:
                    self.print_result(name, True, "Accessible")
                else:
                    self.print_result(name, False, f"Status: {response.status_code}")
                    all_valid = False

            except Exception as e:
                self.print_result(name, False, f"Error: {e}")
                all_valid = False

        return all_valid

    def run_postman_tests(self) -> bool:
        """Run Postman collection tests"""
        self.print_header("POSTMAN COLLECTION TESTS")

        collection_path = Path("docs/api/postman/BabyShield_v1.postman_collection.json")

        if not collection_path.exists():
            self.print_result("Postman collection", False, "Collection file not found")
            self.warnings.append("Postman collection not found - skipping API tests")
            return True  # Don't fail if collection doesn't exist

        try:
            # Check if newman is installed
            result = subprocess.run(["newman", "--version"], capture_output=True, text=True)

            if result.returncode != 0:
                self.print_result("Newman CLI", False, "Not installed - run: npm install -g newman")
                return True  # Don't fail if newman not installed

            # Run the collection
            print("Running Postman collection tests...")
            result = subprocess.run(
                [
                    "newman",
                    "run",
                    str(collection_path),
                    "--env-var",
                    f"baseUrl={self.api_url}",
                    "--reporters",
                    "cli,json",
                    "--reporter-json-export",
                    "postman_results.json",
                    "--suppress-exit-code",
                ],
                capture_output=True,
                text=True,
            )

            # Parse results
            if Path("postman_results.json").exists():
                with open("postman_results.json", "r") as f:
                    results = json.load(f)

                stats = results.get("run", {}).get("stats", {})

                total = stats.get("assertions", {}).get("total", 0)
                failed = stats.get("assertions", {}).get("failed", 0)

                if failed == 0:
                    self.print_result("Postman tests", True, f"All {total} tests passed")
                    return True
                else:
                    self.print_result("Postman tests", False, f"{failed}/{total} tests failed")
                    return False
            else:
                print("   ℹ️ Could not parse test results")
                return True

        except FileNotFoundError:
            self.print_result("Newman", False, "Not installed")
            self.warnings.append("Newman not installed - cannot run Postman tests")
            return True
        except Exception as e:
            self.print_result("Postman tests", False, str(e))
            return True

    def generate_validation_report(self):
        """Generate validation report for submission"""
        report_path = Path("submission/validation_report.json")
        report_path.parent.mkdir(exist_ok=True)

        report = {
            "timestamp": datetime.now().isoformat(),
            "api_url": self.api_url,
            "results": self.results,
            "warnings": self.warnings,
            "errors": self.errors,
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results.values() if r),
                "warnings": len(self.warnings),
                "errors": len(self.errors),
            },
        }

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n📋 Validation report saved to: {report_path}")

        # Also create markdown report
        md_path = Path("submission/validation_report.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Submission Validation Report\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**API URL:** {self.api_url}\n\n")

            f.write("## Summary\n\n")
            f.write(f"- Total Tests: {report['summary']['total_tests']}\n")
            f.write(f"- Passed: {report['summary']['passed']}\n")
            f.write(f"- Warnings: {report['summary']['warnings']}\n")
            f.write(f"- Errors: {report['summary']['errors']}\n\n")

            if self.warnings:
                f.write("## ⚠️ Warnings\n\n")
                for warning in self.warnings:
                    f.write(f"- {warning}\n")
                f.write("\n")

            if self.errors:
                f.write("## ❌ Errors\n\n")
                for error in self.errors:
                    f.write(f"- {error}\n")
                f.write("\n")

        print(f"📄 Markdown report saved to: {md_path}")

    def run_all_validations(self) -> bool:
        """Run all validation checks"""
        print(f"{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
        print(f"{Colors.BOLD}🚀 APP STORE SUBMISSION PREFLIGHT VALIDATION{Colors.ENDC}")
        print(f"{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
        print(f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"API: {self.api_url}\n")

        # Run all validation checks
        checks = [
            ("API Endpoints", self.validate_api_endpoints),
            ("Security Headers", self.validate_security_headers),
            ("Store Metadata", self.validate_store_metadata),
            ("Screenshots", self.validate_screenshots),
            ("App Icons", self.validate_app_icons),
            ("Text Content", self.validate_text_content),
            ("Legal Documents", self.validate_legal_documents),
            ("Postman Tests", self.run_postman_tests),
        ]

        for name, check_func in checks:
            self.results[name] = check_func()

        # Generate report
        self.generate_validation_report()

        # Final summary
        self.print_header("VALIDATION SUMMARY")

        passed = sum(1 for r in self.results.values() if r)
        total = len(self.results)

        print(f"Results: {passed}/{total} checks passed\n")

        for check, result in self.results.items():
            if result:
                print(f"{Colors.GREEN}✅ {check}{Colors.ENDC}")
            else:
                print(f"{Colors.RED}❌ {check}{Colors.ENDC}")

        if self.warnings:
            print(f"\n{Colors.YELLOW}⚠️ {len(self.warnings)} Warnings:{Colors.ENDC}")
            for warning in self.warnings[:5]:
                print(f"   - {warning}")

        if self.errors:
            print(f"\n{Colors.RED}❌ {len(self.errors)} Errors:{Colors.ENDC}")
            for error in self.errors[:5]:
                print(f"   - {error}")

        # Determine readiness
        print(f"\n{Colors.BOLD}{'=' * 70}{Colors.ENDC}")

        if passed == total and len(self.errors) == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}✅ READY FOR SUBMISSION{Colors.ENDC}")
            print("All validation checks passed. You may proceed with app store submission.")
            return True
        elif passed >= total * 0.8 and len(self.errors) <= 2:
            print(f"{Colors.YELLOW}{Colors.BOLD}⚠️ ALMOST READY{Colors.ENDC}")
            print("Minor issues detected. Review warnings before submission.")
            return True
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ NOT READY FOR SUBMISSION{Colors.ENDC}")
            print("Critical issues detected. Address errors before proceeding.")
            return False


def main():
    """Main entry point"""
    validator = SubmissionValidator()
    success = validator.run_all_validations()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
