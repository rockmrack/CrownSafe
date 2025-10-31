"""Enterprise Security Validator
Validates security configuration and best practices across the application.
"""

import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class SecurityConfigValidator:
    """Validates security configuration against enterprise best practices."""

    def __init__(self) -> None:
        self.findings: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.passed_checks: list[str] = []

    def validate_environment_variables(self) -> dict[str, Any]:
        """Validate critical environment variables are properly configured.

        Returns:
            Dict with validation results

        """
        results = {
            "status": "pass",
            "checks": [],
            "recommendations": [],
        }

        # Critical security variables
        critical_vars = {
            "SECRET_KEY": {
                "min_length": 32,
                "required": True,
                "description": "Application secret key for signing",
            },
            "JWT_SECRET_KEY": {
                "min_length": 32,
                "required": True,
                "description": "JWT token signing key",
            },
            "DATABASE_URL": {
                "min_length": 20,
                "required": True,
                "description": "Database connection string",
                "should_not_contain": ["localhost", "postgres:postgres"],
            },
        }

        # Azure-specific variables
        azure_vars = {
            "AZURE_STORAGE_CONNECTION_STRING": {
                "min_length": 50,
                "required": False,
                "description": "Azure Blob Storage connection",
            },
            "AZURE_STORAGE_ACCOUNT_KEY": {
                "min_length": 32,
                "required": False,
                "description": "Azure storage account key",
            },
        }

        all_vars = {**critical_vars, **azure_vars}

        for var_name, config in all_vars.items():
            value = os.getenv(var_name)

            check = {
                "variable": var_name,
                "description": config["description"],
                "status": "pass",
                "issues": [],
            }

            if config["required"] and not value:
                check["status"] = "fail"
                check["issues"].append(f"Required variable {var_name} is not set")
                results["status"] = "fail"

            elif value:
                # Check minimum length
                if len(value) < config["min_length"]:
                    check["status"] = "warn"
                    check["issues"].append(f"Value is too short ({len(value)} < {config['min_length']} chars)")

                # Check for insecure defaults
                insecure_patterns = [
                    "change",
                    "replace",
                    "dev",
                    "test",
                    "example",
                    "placeholder",
                ]
                if any(pattern in value.lower() for pattern in insecure_patterns):
                    check["status"] = "warn"
                    check["issues"].append("Value appears to be a default/placeholder")

                # Check blacklisted values
                if "should_not_contain" in config:
                    for blacklisted in config["should_not_contain"]:
                        if blacklisted in value.lower():
                            check["status"] = "fail"
                            check["issues"].append(f"Value contains insecure pattern: {blacklisted}")
                            results["status"] = "fail"

            results["checks"].append(check)

        # Recommendations
        if results["status"] != "pass":
            results["recommendations"].extend(
                [
                    "Use Azure Key Vault for production secrets",
                    "Rotate secrets every 90 days",
                    "Never commit secrets to git",
                    "Use managed identity where possible",
                ],
            )

        return results

    def validate_cors_configuration(self) -> dict[str, Any]:
        """Validate CORS configuration for security.

        Returns:
            Dict with CORS validation results

        """
        results = {"status": "pass", "checks": [], "recommendations": []}

        cors_origins = os.getenv("CORS_ORIGINS", "*")

        check = {
            "setting": "CORS_ORIGINS",
            "value": cors_origins,
            "status": "pass",
            "issues": [],
        }

        # Check if CORS is too permissive
        if cors_origins == "*":
            check["status"] = "warn"
            check["issues"].append("CORS allows all origins - should be restricted in production")
            results["recommendations"].append("Set CORS_ORIGINS to specific domains (e.g., https://app.crownsafe.com)")

        # Check for localhost in production
        if "localhost" in cors_origins.lower() and os.getenv("ENVIRONMENT") == "production":
            check["status"] = "fail"
            check["issues"].append("CORS includes localhost in production environment")
            results["status"] = "fail"

        results["checks"].append(check)

        return results

    def validate_ssl_tls_configuration(self) -> dict[str, Any]:
        """Validate SSL/TLS configuration.

        Returns:
            Dict with SSL/TLS validation results

        """
        results = {"status": "pass", "checks": [], "recommendations": []}

        # Check if database uses SSL
        database_url = os.getenv("DATABASE_URL", "")

        db_check = {
            "setting": "Database SSL",
            "status": "pass",
            "issues": [],
        }

        if database_url:
            if "sslmode=require" not in database_url and "ssl=true" not in database_url:
                db_check["status"] = "warn"
                db_check["issues"].append("Database connection may not enforce SSL")
                results["recommendations"].append("Add sslmode=require to DATABASE_URL")

        results["checks"].append(db_check)

        # Check Redis SSL
        redis_url = os.getenv("REDIS_URL", "")

        redis_check = {
            "setting": "Redis SSL",
            "status": "pass",
            "issues": [],
        }

        if redis_url and "redis://" in redis_url:
            if "ssl=true" not in redis_url:
                redis_check["status"] = "warn"
                redis_check["issues"].append("Redis connection may not use SSL")
                results["recommendations"].append("Use rediss:// scheme or add ?ssl=true parameter")

        results["checks"].append(redis_check)

        return results

    def validate_rate_limiting(self) -> dict[str, Any]:
        """Validate rate limiting configuration.

        Returns:
            Dict with rate limiting validation results

        """
        results = {"status": "pass", "checks": [], "recommendations": []}

        rate_limit = os.getenv("RATE_LIMIT_PER_MINUTE", "")

        check = {
            "setting": "RATE_LIMIT_PER_MINUTE",
            "status": "pass",
            "issues": [],
        }

        if not rate_limit:
            check["status"] = "warn"
            check["issues"].append("Rate limiting not configured")
            results["recommendations"].append("Set RATE_LIMIT_PER_MINUTE=100 (or appropriate value)")
        else:
            try:
                limit = int(rate_limit)
                if limit > 1000:
                    check["status"] = "warn"
                    check["issues"].append(f"Rate limit is very high ({limit}/min) - may not prevent abuse")
                    results["recommendations"].append("Consider lowering rate limit for better DDoS protection")
            except ValueError:
                check["status"] = "fail"
                check["issues"].append("Invalid rate limit value")
                results["status"] = "fail"

        results["checks"].append(check)

        return results

    def validate_logging_configuration(self) -> dict[str, Any]:
        """Validate logging configuration for security events.

        Returns:
            Dict with logging validation results

        """
        results = {"status": "pass", "checks": [], "recommendations": []}

        log_level = os.getenv("LOG_LEVEL", "INFO")

        check = {
            "setting": "LOG_LEVEL",
            "value": log_level,
            "status": "pass",
            "issues": [],
        }

        if log_level.upper() == "DEBUG" and os.getenv("ENVIRONMENT") == "production":
            check["status"] = "fail"
            check["issues"].append("DEBUG logging enabled in production - may expose sensitive data")
            results["status"] = "fail"
            results["recommendations"].append("Set LOG_LEVEL=INFO or WARNING in production")

        results["checks"].append(check)

        # Check if audit logging is enabled
        audit_check = {
            "setting": "AUDIT_LOGGING_ENABLED",
            "value": os.getenv("AUDIT_LOGGING_ENABLED", "false"),
            "status": "pass",
            "issues": [],
        }

        if os.getenv("AUDIT_LOGGING_ENABLED", "false").lower() != "true":
            audit_check["status"] = "warn"
            audit_check["issues"].append("Audit logging not enabled")
            results["recommendations"].append("Enable audit logging for security compliance")

        results["checks"].append(audit_check)

        return results

    def comprehensive_security_audit(self) -> dict[str, Any]:
        """Run comprehensive security audit.

        Returns:
            Dict with complete audit results

        """
        audit_results = {
            "timestamp": datetime.now(UTC).isoformat(),
            "overall_status": "pass",
            "categories": {},
            "summary": {
                "total_checks": 0,
                "passed": 0,
                "warnings": 0,
                "failures": 0,
            },
            "recommendations": [],
        }

        # Run all validation checks
        validations = {
            "environment_variables": self.validate_environment_variables(),
            "cors_configuration": self.validate_cors_configuration(),
            "ssl_tls": self.validate_ssl_tls_configuration(),
            "rate_limiting": self.validate_rate_limiting(),
            "logging": self.validate_logging_configuration(),
        }

        # Aggregate results
        for category, results in validations.items():
            audit_results["categories"][category] = results

            for check in results.get("checks", []):
                audit_results["summary"]["total_checks"] += 1

                if check["status"] == "pass":
                    audit_results["summary"]["passed"] += 1
                elif check["status"] == "warn":
                    audit_results["summary"]["warnings"] += 1
                elif check["status"] == "fail":
                    audit_results["summary"]["failures"] += 1
                    audit_results["overall_status"] = "fail"

            # Collect recommendations
            audit_results["recommendations"].extend(results.get("recommendations", []))

        # Determine overall status
        if audit_results["summary"]["failures"] > 0:
            audit_results["overall_status"] = "fail"
        elif audit_results["summary"]["warnings"] > 0:
            audit_results["overall_status"] = "warn"

        # Add risk score
        total_checks = audit_results["summary"]["total_checks"]
        if total_checks > 0:
            risk_score = (
                (audit_results["summary"]["failures"] * 10 + audit_results["summary"]["warnings"] * 5)
                / total_checks
                * 10
            )
            audit_results["risk_score"] = round(risk_score, 2)
            audit_results["risk_level"] = self._get_risk_level(risk_score)

        return audit_results

    def _get_risk_level(self, score: float) -> str:
        """Get risk level based on score."""
        if score < 2:
            return "LOW"
        if score < 5:
            return "MEDIUM"
        if score < 8:
            return "HIGH"
        return "CRITICAL"


# Global validator instance
security_validator = SecurityConfigValidator()
