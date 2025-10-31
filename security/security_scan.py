#!/usr/bin/env python3
"""
Security Scanner for BabyShield
Performs comprehensive security analysis of the codebase
"""

import ast
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple


class SecurityScanner:
    """Comprehensive security scanner"""

    def __init__(self):
        self.base_path = Path.cwd()
        self.findings = {
            "secrets": [],
            "vulnerabilities": [],
            "data_handling": [],
            "dependencies": [],
            "configuration": [],
            "recommendations": [],
        }

        # Secret patterns to detect
        self.secret_patterns = {
            "AWS Access Key": r"AKIA[0-9A-Z]{16}",
            "AWS Secret Key": r"[0-9a-zA-Z/+=]{40}",
            "API Key": r'[aA][pP][iI]_?[kK][eE][yY]\s*[:=]\s*["\'][0-9a-zA-Z]{32,}["\']',
            "Private Key": r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----",
            "JWT Secret": r'[jJ][wW][tT]_?[sS][eE][cC][rR][eE][tT]\s*[:=]\s*["\'][^"\']+["\']',
            "Database URL": r'(postgres|postgresql|mysql|mongodb)://[^"\'\s]+',
            "Password": r'[pP][aA][sS][sS][wW][oO][rR][dD]\s*[:=]\s*["\'][^"\']+["\']',
            "Token": r'[tT][oO][kK][eE][nN]\s*[:=]\s*["\'][0-9a-zA-Z]{20,}["\']',
            "Stripe Key": r"sk_live_[0-9a-zA-Z]{24,}",
            "GitHub Token": r"ghp_[0-9a-zA-Z]{36}",
            "Slack Token": r"xox[baprs]-[0-9]{10,}-[0-9a-zA-Z]{24,}",
        }

        # Files to skip
        self.skip_patterns = {
            ".git",
            "__pycache__",
            "node_modules",
            ".env.example",
            "test_",
            "mock_",
            ".pyc",
            ".md",
            ".txt",
            ".json",
        }

        # Sensitive data patterns
        self.sensitive_data = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "phone": r"(\+\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}",
            "ssn": r"\d{3}-\d{2}-\d{4}",
            "credit_card": r"\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}",
            "ip_address": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
        }

    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "=" * 70)
        print(f" {title}")
        print("=" * 70)

    def scan_for_secrets(self) -> List[Dict]:
        """Scan codebase for exposed secrets"""

        self.print_header("🔍 SECRET SCANNING")

        secrets_found = []
        files_scanned = 0

        for root, dirs, files in os.walk(self.base_path):
            # Skip certain directories
            dirs[:] = [d for d in dirs if not any(skip in d for skip in self.skip_patterns)]

            for file in files:
                # Skip certain files
                if any(skip in file for skip in self.skip_patterns):
                    continue

                file_path = Path(root) / file
                files_scanned += 1

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                        for secret_type, pattern in self.secret_patterns.items():
                            matches = re.finditer(pattern, content)
                            for match in matches:
                                # Check if it's an environment variable reference
                                if "os.environ" in content[max(0, match.start() - 20) : match.end() + 20]:
                                    continue

                                secrets_found.append(
                                    {
                                        "type": secret_type,
                                        "file": str(file_path.relative_to(self.base_path)),
                                        "line": content[: match.start()].count("\n") + 1,
                                        "preview": match.group()[:50] + "..."
                                        if len(match.group()) > 50
                                        else match.group(),
                                    }
                                )

                except Exception:
                    pass

        print(f"Files scanned: {files_scanned}")
        print(f"Secrets found: {len(secrets_found)}")

        if secrets_found:
            print("\n⚠️ POTENTIAL SECRETS DETECTED:")
            for secret in secrets_found[:10]:  # Show first 10
                print(f"  - {secret['type']} in {secret['file']}:{secret['line']}")
        else:
            print("✅ No hardcoded secrets detected")

        self.findings["secrets"] = secrets_found
        return secrets_found

    def scan_dependencies(self) -> List[Dict]:
        """Scan Python dependencies for vulnerabilities"""

        self.print_header("📦 DEPENDENCY SCANNING")

        vulnerabilities = []

        # Check if requirements.txt exists
        req_file = self.base_path / "requirements.txt"
        if not req_file.exists():
            print("❌ requirements.txt not found")
            return vulnerabilities

        # Parse requirements
        with open(req_file, "r") as f:
            requirements = f.readlines()

        print(f"Dependencies found: {len(requirements)}")

        # Check for outdated packages (simplified check)
        outdated_packages = [
            "flask<2.0",  # Should use FastAPI or Flask 2.0+
            "django<3.2",  # Should use Django 3.2+
            "requests<2.25",  # Should use newer version
            "cryptography<3.4",  # Security updates
            "pyyaml<5.4",  # Security fixes
            "jinja2<2.11.3",  # Template injection fixes
            "werkzeug<2.0",  # Security updates
            "sqlalchemy<1.4",  # Security improvements
        ]

        for req in requirements:
            req = req.strip()
            if not req or req.startswith("#"):
                continue

            # Check for vulnerable versions
            for vulnerable in outdated_packages:
                if vulnerable.split("<")[0] in req.lower():
                    vulnerabilities.append(
                        {
                            "package": req,
                            "issue": f"Potentially outdated: {vulnerable}",
                            "severity": "medium",
                        }
                    )

        # Check for packages with known vulnerabilities
        high_risk_packages = {
            "pycrypto": "Use cryptography instead",
            "md5": "Use hashlib with SHA256",
            "pickle": "Can execute arbitrary code",
            "eval": "Security risk - avoid if possible",
            "exec": "Security risk - avoid if possible",
        }

        for req in requirements:
            package_name = req.split("==")[0].split(">=")[0].split("<=")[0].strip()
            if package_name in high_risk_packages:
                vulnerabilities.append(
                    {
                        "package": package_name,
                        "issue": high_risk_packages[package_name],
                        "severity": "high",
                    }
                )

        if vulnerabilities:
            print("\n⚠️ DEPENDENCY ISSUES:")
            for vuln in vulnerabilities:
                print(f"  - {vuln['package']}: {vuln['issue']} [{vuln['severity']}]")
        else:
            print("✅ No known vulnerable dependencies")

        self.findings["dependencies"] = vulnerabilities
        return vulnerabilities

    def verify_data_handling(self) -> Dict:
        """Verify data handling practices"""

        self.print_header("🔐 DATA HANDLING VERIFICATION")

        data_checks = {
            "email_storage": False,
            "password_hashing": False,
            "pii_encryption": False,
            "user_id_only": False,
            "provider_sub": False,
            "data_retention": False,
            "secure_deletion": False,
        }

        # Check database models
        db_file = self.base_path / "core_infra" / "database.py"
        if db_file.exists():
            with open(db_file, "r") as f:
                content = f.read()

                # Check for email storage
                if "email" in content.lower():
                    # Check if it's actually stored
                    if "Column(String" in content and "email" in content:
                        data_checks["email_storage"] = True
                        print("⚠️ Email field found in database schema")
                    else:
                        print("ℹ️ Email referenced but may not be stored")
                else:
                    print("✅ No email storage detected")

                # Check for password hashing
                if "hashed_password" in content or "password_hash" in content:
                    data_checks["password_hashing"] = True
                    print("✅ Password hashing implemented")

                # Check for user_id and provider_sub
                if "provider_id" in content or "provider_sub" in content:
                    data_checks["provider_sub"] = True
                    print("✅ Provider sub storage found")

                if "user_id" in content or "id = Column(Integer" in content:
                    data_checks["user_id_only"] = True
                    print("✅ Internal user_id implementation found")

        # Check for PII handling
        api_files = list((self.base_path / "api").glob("*.py"))
        for api_file in api_files:
            with open(api_file, "r") as f:
                content = f.read()

                # Check for encryption
                if "encrypt" in content.lower() or "crypto" in content.lower():
                    data_checks["pii_encryption"] = True

                # Check for data retention
                if "retention" in content.lower() or "expire" in content.lower():
                    data_checks["data_retention"] = True

                # Check for secure deletion
                if "delete" in content.lower() and ("secure" in content.lower() or "permanent" in content.lower()):
                    data_checks["secure_deletion"] = True

        # Summary
        compliant_items = sum(1 for v in data_checks.values() if v)
        print(f"\n📊 Data Handling Compliance: {compliant_items}/{len(data_checks)}")

        for check, passed in data_checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check.replace('_', ' ').title()}")

        self.findings["data_handling"] = data_checks
        return data_checks

    def check_security_configurations(self) -> Dict:
        """Check security configurations"""

        self.print_header("⚙️ SECURITY CONFIGURATION")

        configs = {
            "rate_limiting": False,
            "cors_configured": False,
            "security_headers": False,
            "https_enforced": False,
            "authentication": False,
            "authorization": False,
            "input_validation": False,
            "error_handling": False,
            "logging": False,
            "monitoring": False,
        }

        # Check main API file
        main_api = self.base_path / "api" / "main_crownsafe.py"
        if main_api.exists():
            with open(main_api, "r") as f:
                content = f.read()

                # Check configurations
                if "RateLimiter" in content or "slowapi" in content:
                    configs["rate_limiting"] = True
                    print("✅ Rate limiting configured")

                if "CORS" in content or "CORSMiddleware" in content:
                    configs["cors_configured"] = True
                    print("✅ CORS configured")

                if "SecurityMiddleware" in content or "security_headers" in content:
                    configs["security_headers"] = True
                    print("✅ Security headers configured")

                if "HTTPSRedirect" in content or "force_https" in content:
                    configs["https_enforced"] = True
                    print("✅ HTTPS enforcement configured")

                if "OAuth" in content or "JWT" in content or "authenticate" in content:
                    configs["authentication"] = True
                    print("✅ Authentication implemented")

                if "authorize" in content or "permissions" in content or "roles" in content:
                    configs["authorization"] = True
                    print("✅ Authorization implemented")

                if "validate" in content or "BaseModel" in content or "pydantic" in content:
                    configs["input_validation"] = True
                    print("✅ Input validation implemented")

                if "try:" in content and "except" in content:
                    configs["error_handling"] = True
                    print("✅ Error handling implemented")

                if "logging" in content or "logger" in content:
                    configs["logging"] = True
                    print("✅ Logging configured")

                if "metrics" in content or "monitoring" in content:
                    configs["monitoring"] = True
                    print("✅ Monitoring configured")

        # Calculate security score
        security_score = sum(1 for v in configs.values() if v) / len(configs) * 100
        print(f"\n🛡️ Security Score: {security_score:.0f}%")

        if security_score < 70:
            print("⚠️ Security configuration needs improvement")
        elif security_score < 90:
            print("ℹ️ Good security configuration, minor improvements possible")
        else:
            print("✅ Excellent security configuration")

        self.findings["configuration"] = configs
        return configs

    def check_read_only_db_roles(self) -> bool:
        """Check for read-only database roles"""

        self.print_header("👤 DATABASE ROLE VERIFICATION")

        # Check for read-only role SQL
        sql_file = self.base_path / "sql" / "create_readonly_user.sql"
        if sql_file.exists():
            print("✅ Read-only database role script found")

            with open(sql_file, "r") as f:
                content = f.read()

                required_elements = [
                    "CREATE ROLE" in content or "CREATE USER" in content,
                    "GRANT SELECT" in content,
                    "REVOKE" in content or "DENY" in content,
                    "babyshield_readonly" in content.lower() or "readonly" in content.lower(),
                ]

                if all(required_elements):
                    print("✅ Read-only role properly configured")
                    print("  - User creation: ✓")
                    print("  - SELECT permission: ✓")
                    print("  - Write protection: ✓")
                    return True
                else:
                    print("⚠️ Read-only role configuration incomplete")
                    return False
        else:
            print("❌ Read-only database role not configured")
            print("  Create sql/create_readonly_user.sql")
            return False

    def check_secret_rotation(self) -> Dict:
        """Check secret rotation procedures"""

        self.print_header("🔄 SECRET ROTATION VERIFICATION")

        rotation_checks = {
            "documentation": False,
            "api_keys": False,
            "database_passwords": False,
            "jwt_secrets": False,
            "encryption_keys": False,
            "automation": False,
        }

        # Check for secret rotation documentation
        rotation_file = self.base_path / "security" / "SECRET_ROTATION_GUIDE.md"
        if rotation_file.exists():
            rotation_checks["documentation"] = True
            print("✅ Secret rotation guide found")

            with open(rotation_file, "r") as f:
                content = f.read()

                if "API" in content and ("key" in content.lower() or "token" in content.lower()):
                    rotation_checks["api_keys"] = True

                if "database" in content.lower() or "password" in content.lower():
                    rotation_checks["database_passwords"] = True

                if "JWT" in content or "token" in content.lower():
                    rotation_checks["jwt_secrets"] = True

                if "encrypt" in content.lower() or "KMS" in content:
                    rotation_checks["encryption_keys"] = True

                if "automat" in content.lower() or "script" in content.lower():
                    rotation_checks["automation"] = True
        else:
            print("❌ Secret rotation guide not found")

        # Print results
        for check, passed in rotation_checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check.replace('_', ' ').title()}")

        return rotation_checks

    def generate_recommendations(self) -> List[str]:
        """Generate security recommendations"""

        recommendations = []

        # Based on findings, generate recommendations
        if self.findings["secrets"]:
            recommendations.append("Remove hardcoded secrets and use environment variables")

        if self.findings["dependencies"]:
            recommendations.append("Update vulnerable dependencies")

        data_handling = self.findings.get("data_handling", {})
        if data_handling.get("email_storage"):
            recommendations.append("Consider removing direct email storage")

        if not data_handling.get("pii_encryption"):
            recommendations.append("Implement PII encryption at rest")

        configs = self.findings.get("configuration", {})
        if not configs.get("rate_limiting"):
            recommendations.append("Implement rate limiting on all endpoints")

        if not configs.get("security_headers"):
            recommendations.append("Add security headers (CSP, HSTS, etc.)")

        if not configs.get("monitoring"):
            recommendations.append("Implement security monitoring and alerting")

        self.findings["recommendations"] = recommendations
        return recommendations

    def generate_report(self) -> Dict:
        """Generate security scan report"""

        self.print_header("📋 SECURITY SCAN SUMMARY")

        report = {
            "timestamp": datetime.now().isoformat(),
            "findings": self.findings,
            "statistics": {
                "secrets_found": len(self.findings["secrets"]),
                "vulnerabilities": len(self.findings["dependencies"]),
                "security_score": 0,
            },
            "compliance": {
                "no_email_storage": not self.findings.get("data_handling", {}).get("email_storage", True),
                "user_id_only": self.findings.get("data_handling", {}).get("user_id_only", False),
                "provider_sub": self.findings.get("data_handling", {}).get("provider_sub", False),
            },
        }

        # Calculate security score
        configs = self.findings.get("configuration", {})
        if configs:
            report["statistics"]["security_score"] = sum(1 for v in configs.values() if v) / len(configs) * 100

        # Print summary
        print(f"\n🔍 Secrets Found: {report['statistics']['secrets_found']}")
        print(f"📦 Vulnerable Dependencies: {report['statistics']['vulnerabilities']}")
        print(f"🛡️ Security Score: {report['statistics']['security_score']:.0f}%")
        print(f"✅ No Email Storage: {report['compliance']['no_email_storage']}")
        print(f"✅ User ID Only: {report['compliance']['user_id_only']}")
        print(f"✅ Provider Sub: {report['compliance']['provider_sub']}")

        if self.findings["recommendations"]:
            print("\n📌 Recommendations:")
            for i, rec in enumerate(self.findings["recommendations"], 1):
                print(f"  {i}. {rec}")

        # Save report
        report_path = self.base_path / "security" / "security_scan_report.json"
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print("\n📄 Report saved to: security/security_scan_report.json")

        return report

    def run_full_scan(self) -> Dict:
        """Run complete security scan"""

        print("=" * 70)
        print(" 🔒 BABYSHIELD SECURITY SCAN")
        print(f" Time: {datetime.now().isoformat()}")
        print("=" * 70)

        # Run all scans
        self.scan_for_secrets()
        self.scan_dependencies()
        self.verify_data_handling()
        self.check_security_configurations()
        self.check_read_only_db_roles()
        self.check_secret_rotation()
        self.generate_recommendations()

        # Generate report
        report = self.generate_report()

        return report


def main():
    """Run security scan"""
    scanner = SecurityScanner()
    report = scanner.run_full_scan()

    # Determine exit code
    if report["statistics"]["secrets_found"] > 0:
        print("\n⚠️ Security issues detected - review report")
        return 1
    elif report["statistics"]["security_score"] < 70:
        print("\n⚠️ Security configuration needs improvement")
        return 1
    else:
        print("\n✅ Security scan completed successfully")
        return 0


if __name__ == "__main__":
    exit(main())
