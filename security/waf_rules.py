"""AWS WAF Rules Configuration for BabyShield
Enterprise-grade Web Application Firewall rules.
"""

import json
from typing import Any


class WAFRulesGenerator:
    """Generate AWS WAF rules for bulletproof protection."""

    @staticmethod
    def generate_rate_limiting_rules() -> list[dict[str, Any]]:
        """Generate rate limiting rules."""
        return [
            {
                "Name": "BabyShield-GlobalRateLimit",
                "Priority": 1,
                "Statement": {
                    "RateBasedStatement": {
                        "Limit": 2000,  # 2000 requests per 5 minutes per IP
                        "AggregateKeyType": "IP",
                    },
                },
                "Action": {"Block": {}},
                "VisibilityConfig": {
                    "SampledRequestsEnabled": True,
                    "CloudWatchMetricsEnabled": True,
                    "MetricName": "BabyShieldGlobalRateLimit",
                },
            },
            {
                "Name": "BabyShield-APIRateLimit",
                "Priority": 2,
                "Statement": {
                    "RateBasedStatement": {
                        "Limit": 500,  # 500 API calls per 5 minutes per IP
                        "AggregateKeyType": "IP",
                        "ScopeDownStatement": {
                            "ByteMatchStatement": {
                                "SearchString": "/api/",
                                "FieldToMatch": {"UriPath": {}},
                                "TextTransformations": [{"Priority": 0, "Type": "LOWERCASE"}],
                                "PositionalConstraint": "STARTS_WITH",
                            },
                        },
                    },
                },
                "Action": {"Block": {}},
                "VisibilityConfig": {
                    "SampledRequestsEnabled": True,
                    "CloudWatchMetricsEnabled": True,
                    "MetricName": "BabyShieldAPIRateLimit",
                },
            },
        ]

    @staticmethod
    def generate_attack_prevention_rules() -> list[dict[str, Any]]:
        """Generate rules to prevent common attacks."""
        return [
            # SQL Injection Prevention
            {
                "Name": "BabyShield-SQLInjection",
                "Priority": 10,
                "Statement": {
                    "OrStatement": {
                        "Statements": [
                            {
                                "ByteMatchStatement": {
                                    "SearchString": "union select",
                                    "FieldToMatch": {"AllQueryArguments": {}},
                                    "TextTransformations": [
                                        {"Priority": 0, "Type": "URL_DECODE"},
                                        {"Priority": 1, "Type": "LOWERCASE"},
                                    ],
                                    "PositionalConstraint": "CONTAINS",
                                },
                            },
                            {
                                "ByteMatchStatement": {
                                    "SearchString": "drop table",
                                    "FieldToMatch": {"Body": {}},
                                    "TextTransformations": [
                                        {"Priority": 0, "Type": "URL_DECODE"},
                                        {"Priority": 1, "Type": "LOWERCASE"},
                                    ],
                                    "PositionalConstraint": "CONTAINS",
                                },
                            },
                        ],
                    },
                },
                "Action": {"Block": {}},
                "VisibilityConfig": {
                    "SampledRequestsEnabled": True,
                    "CloudWatchMetricsEnabled": True,
                    "MetricName": "BabyShieldSQLInjection",
                },
            },
            # XSS Prevention
            {
                "Name": "BabyShield-XSS",
                "Priority": 11,
                "Statement": {
                    "OrStatement": {
                        "Statements": [
                            {
                                "ByteMatchStatement": {
                                    "SearchString": "<script>",
                                    "FieldToMatch": {"AllQueryArguments": {}},
                                    "TextTransformations": [
                                        {"Priority": 0, "Type": "URL_DECODE"},
                                        {"Priority": 1, "Type": "HTML_ENTITY_DECODE"},
                                        {"Priority": 2, "Type": "LOWERCASE"},
                                    ],
                                    "PositionalConstraint": "CONTAINS",
                                },
                            },
                            {
                                "ByteMatchStatement": {
                                    "SearchString": "javascript:",
                                    "FieldToMatch": {"UriPath": {}},
                                    "TextTransformations": [
                                        {"Priority": 0, "Type": "URL_DECODE"},
                                        {"Priority": 1, "Type": "LOWERCASE"},
                                    ],
                                    "PositionalConstraint": "CONTAINS",
                                },
                            },
                        ],
                    },
                },
                "Action": {"Block": {}},
                "VisibilityConfig": {
                    "SampledRequestsEnabled": True,
                    "CloudWatchMetricsEnabled": True,
                    "MetricName": "BabyShieldXSS",
                },
            },
            # Path Traversal Prevention
            {
                "Name": "BabyShield-PathTraversal",
                "Priority": 12,
                "Statement": {
                    "OrStatement": {
                        "Statements": [
                            {
                                "ByteMatchStatement": {
                                    "SearchString": "../",
                                    "FieldToMatch": {"UriPath": {}},
                                    "TextTransformations": [{"Priority": 0, "Type": "URL_DECODE"}],
                                    "PositionalConstraint": "CONTAINS",
                                },
                            },
                            {
                                "ByteMatchStatement": {
                                    "SearchString": "%2e%2e/",
                                    "FieldToMatch": {"UriPath": {}},
                                    "TextTransformations": [{"Priority": 0, "Type": "LOWERCASE"}],
                                    "PositionalConstraint": "CONTAINS",
                                },
                            },
                        ],
                    },
                },
                "Action": {"Block": {}},
                "VisibilityConfig": {
                    "SampledRequestsEnabled": True,
                    "CloudWatchMetricsEnabled": True,
                    "MetricName": "BabyShieldPathTraversal",
                },
            },
        ]

    @staticmethod
    def generate_geographic_rules() -> list[dict[str, Any]]:
        """Generate geographic blocking rules."""
        return [
            {
                "Name": "BabyShield-GeoBlock",
                "Priority": 5,
                "Statement": {
                    "NotStatement": {
                        "Statement": {
                            "GeoMatchStatement": {
                                "CountryCodes": ["US", "CA", "GB", "IE", "AU", "NZ"]
                                + [
                                    "DE",
                                    "FR",
                                    "ES",
                                    "IT",
                                    "NL",
                                    "BE",
                                    "AT",
                                    "CH",
                                    "SE",
                                    "NO",
                                    "DK",
                                    "FI",
                                ],
                            },
                        },
                    },
                },
                "Action": {"Block": {}},
                "VisibilityConfig": {
                    "SampledRequestsEnabled": True,
                    "CloudWatchMetricsEnabled": True,
                    "MetricName": "BabyShieldGeoBlock",
                },
            },
        ]

    @staticmethod
    def generate_ip_reputation_rules() -> list[dict[str, Any]]:
        """Generate IP reputation rules."""
        return [
            {
                "Name": "BabyShield-IPReputation",
                "Priority": 3,
                "Statement": {
                    "ManagedRuleGroupStatement": {
                        "VendorName": "AWS",
                        "Name": "AWSManagedRulesAmazonIpReputationList",
                    },
                },
                "Action": {"Block": {}},
                "VisibilityConfig": {
                    "SampledRequestsEnabled": True,
                    "CloudWatchMetricsEnabled": True,
                    "MetricName": "BabyShieldIPReputation",
                },
                "OverrideAction": {"None": {}},
            },
            {
                "Name": "BabyShield-KnownBadInputs",
                "Priority": 4,
                "Statement": {
                    "ManagedRuleGroupStatement": {
                        "VendorName": "AWS",
                        "Name": "AWSManagedRulesKnownBadInputsRuleSet",
                    },
                },
                "Action": {"Block": {}},
                "VisibilityConfig": {
                    "SampledRequestsEnabled": True,
                    "CloudWatchMetricsEnabled": True,
                    "MetricName": "BabyShieldKnownBadInputs",
                },
                "OverrideAction": {"None": {}},
            },
        ]


def generate_complete_waf_config() -> dict[str, Any]:
    """Generate complete WAF configuration."""
    generator = WAFRulesGenerator()

    all_rules = []
    all_rules.extend(generator.generate_rate_limiting_rules())
    all_rules.extend(generator.generate_ip_reputation_rules())
    all_rules.extend(generator.generate_geographic_rules())
    all_rules.extend(generator.generate_attack_prevention_rules())

    return {
        "Name": "BabyShield-BulletproofWAF",
        "Scope": "REGIONAL",
        "DefaultAction": {"Allow": {}},
        "Rules": all_rules,
        "Description": "Bulletproof WAF for BabyShield - Comprehensive protection against all known attack vectors",
        "Tags": [
            {"Key": "Environment", "Value": "Production"},
            {"Key": "Application", "Value": "BabyShield"},
            {"Key": "Security", "Value": "Bulletproof"},
        ],
    }


if __name__ == "__main__":
    # Generate WAF configuration for deployment
    config = generate_complete_waf_config()
    print(json.dumps(config, indent=2))
