"""
API Documentation Enhancement Tool
Automatically generates comprehensive API documentation

Features:
- OpenAPI/Swagger schema enhancement
- Endpoint categorization
- Request/response examples
- Error code documentation
- Rate limiting information
"""

from typing import Any


class APIDocumentationEnhancer:
    """
    Enhances FastAPI automatic documentation
    Adds comprehensive examples and descriptions
    """

    @staticmethod
    def get_monitoring_endpoints_docs() -> list[dict[str, Any]]:
        """
        Get documentation for monitoring endpoints

        Returns:
            List of endpoint documentation objects
        """
        return [
            {
                "path": "/api/v1/monitoring/system-health-dashboard",
                "method": "GET",
                "summary": "Comprehensive System Health Dashboard",
                "description": """
                Aggregates health metrics from all subsystems and provides
                an overall system health score (0-100).
                
                Returns HTTP 503 if system is in critical/warning state.
                Returns HTTP 200 if system is healthy or degraded.
                """,
                "response_example": {
                    "status": "healthy",
                    "timestamp": "2025-10-31T12:00:00.000Z",
                    "uptime_seconds": 3600,
                    "overall_health_score": 95.5,
                    "subsystems": {
                        "security": {
                            "status": "pass",
                            "risk_level": "LOW",
                            "total_checks": 15,
                            "failures": 0,
                            "warnings": 0,
                        },
                        "azure_storage": {
                            "status": "healthy",
                            "connectivity": "ok",
                            "performance": "ok",
                            "metrics": {
                                "upload_count": 1250,
                                "download_count": 3400,
                                "error_count": 2,
                                "uptime_percent": 99.95,
                            },
                        },
                        "cache": {
                            "cache_enabled": True,
                            "hit_rate_percent": 87.5,
                            "total_requests": 5000,
                            "cache_hits": 4375,
                            "cache_misses": 625,
                        },
                        "connection_pool": {
                            "available_connections": 8,
                            "in_use_connections": 2,
                            "reuse_rate_percent": 92.3,
                            "pool_exhaustion_count": 3,
                        },
                        "database": {"status": "healthy", "connectivity": "ok"},
                    },
                },
                "health_score_penalties": {
                    "security_critical": -50,
                    "security_high": -30,
                    "security_medium": -15,
                    "security_low": -5,
                    "azure_storage_unhealthy": -20,
                    "database_failure": -25,
                    "cache_hit_rate_below_50": -10,
                    "cache_hit_rate_below_70": -5,
                    "pool_exhaustion_above_100": -15,
                    "pool_exhaustion_above_50": -10,
                    "pool_exhaustion_above_10": -5,
                },
            },
            {
                "path": "/api/v1/monitoring/security-audit",
                "method": "GET",
                "summary": "Security Configuration Audit",
                "description": """
                Performs comprehensive security configuration validation
                across 5 categories with risk scoring.
                
                Returns HTTP 200 if all checks pass.
                Returns HTTP 500 if security issues detected.
                """,
                "response_example": {
                    "overall_status": "pass",
                    "risk_level": "LOW",
                    "risk_score": 1.2,
                    "total_checks": 15,
                    "total_failures": 0,
                    "total_warnings": 1,
                    "results": {
                        "environment_variables": {
                            "status": "pass",
                            "failures": 0,
                            "warnings": 0,
                            "checks": [
                                "SECRET_KEY length >= 32",
                                "JWT_SECRET_KEY length >= 32",
                                "DATABASE_URL configured",
                            ],
                        },
                        "cors_configuration": {
                            "status": "pass",
                            "failures": 0,
                            "warnings": 1,
                            "checks": ["CORS not set to wildcard"],
                        },
                        "ssl_tls_configuration": {
                            "status": "pass",
                            "failures": 0,
                            "warnings": 0,
                            "checks": ["Database SSL enabled", "Redis SSL enabled"],
                        },
                        "rate_limiting": {
                            "status": "pass",
                            "failures": 0,
                            "warnings": 0,
                            "checks": ["Rate limiting configured"],
                        },
                        "logging_configuration": {
                            "status": "pass",
                            "failures": 0,
                            "warnings": 0,
                            "checks": ["Log level appropriate for environment"],
                        },
                    },
                    "timestamp": "2025-10-31T12:00:00.000Z",
                },
            },
            {
                "path": "/api/v1/monitoring/azure-storage",
                "method": "GET",
                "summary": "Azure Storage Health Check",
                "description": """
                Checks Azure Blob Storage connectivity and performance.
                
                Returns HTTP 200 if storage is healthy.
                Returns HTTP 503 if storage has issues.
                """,
                "response_example": {
                    "status": "healthy",
                    "connectivity": {
                        "status": "ok",
                        "response_time_ms": 45,
                        "last_check": "2025-10-31T12:00:00.000Z",
                    },
                    "performance": {
                        "status": "ok",
                        "avg_operation_time_ms": 120,
                        "threshold_ms": 5000,
                    },
                    "capacity": {
                        "status": "unknown",
                        "message": "Requires Azure Monitor API integration",
                    },
                    "timestamp": "2025-10-31T12:00:00.000Z",
                },
            },
            {
                "path": "/api/v1/monitoring/azure-cache-stats",
                "method": "GET",
                "summary": "Azure Storage Cache Performance",
                "description": """
                Returns performance statistics for Redis-based SAS URL caching.
                
                Shows cache hit rate, total requests, and efficiency metrics.
                """,
                "response_example": {
                    "cache_stats": {
                        "cache_enabled": True,
                        "cache_hits": 4375,
                        "cache_misses": 625,
                        "total_requests": 5000,
                        "hit_rate_percent": 87.5,
                        "cache_invalidations": 23,
                        "redis_connected": True,
                    },
                    "timestamp": "2025-10-31T12:00:00.000Z",
                },
            },
        ]

    @staticmethod
    def get_api_best_practices() -> dict[str, Any]:
        """
        Get API best practices documentation

        Returns:
            Dictionary with best practices
        """
        return {
            "rate_limiting": {
                "description": "API endpoints are rate-limited to prevent abuse",
                "default_limit": "100 requests per minute per IP",
                "headers": {
                    "X-RateLimit-Limit": "Maximum requests allowed",
                    "X-RateLimit-Remaining": "Requests remaining in window",
                    "X-RateLimit-Reset": "Unix timestamp when limit resets",
                },
            },
            "authentication": {
                "description": "JWT-based authentication for protected endpoints",
                "header": "Authorization: Bearer <token>",
                "token_expiry": "7 days",
            },
            "error_handling": {
                "description": "Standardized error responses",
                "format": {
                    "error": "Error message",
                    "detail": "Detailed error information",
                    "timestamp": "ISO 8601 timestamp",
                },
                "common_status_codes": {
                    "200": "Success",
                    "400": "Bad Request - Invalid input",
                    "401": "Unauthorized - Authentication required",
                    "403": "Forbidden - Insufficient permissions",
                    "404": "Not Found - Resource doesn't exist",
                    "429": "Too Many Requests - Rate limit exceeded",
                    "500": "Internal Server Error",
                    "503": "Service Unavailable - System unhealthy",
                },
            },
            "pagination": {
                "description": "List endpoints support pagination",
                "parameters": {
                    "skip": "Number of records to skip (default: 0)",
                    "limit": "Maximum records to return (default: 100, max: 1000)",
                },
            },
            "caching": {
                "description": "Responses may be cached",
                "headers": {
                    "Cache-Control": "Caching directives",
                    "ETag": "Response version identifier",
                },
            },
        }


# Generate documentation
def generate_api_documentation():
    """Generate comprehensive API documentation"""
    enhancer = APIDocumentationEnhancer()

    print("Crown Safe API Documentation")
    print("=" * 80)
    print()

    # Monitoring endpoints
    print("MONITORING ENDPOINTS")
    print("-" * 80)
    for endpoint_doc in enhancer.get_monitoring_endpoints_docs():
        print(f"\n{endpoint_doc['method']} {endpoint_doc['path']}")
        print(f"Summary: {endpoint_doc['summary']}")
        print(f"Description: {endpoint_doc['description'].strip()}")

    print("\n\n")
    print("API BEST PRACTICES")
    print("-" * 80)
    best_practices = enhancer.get_api_best_practices()
    for category, details in best_practices.items():
        print(f"\n{category.upper().replace('_', ' ')}")
        print(f"  {details['description']}")


if __name__ == "__main__":
    generate_api_documentation()
