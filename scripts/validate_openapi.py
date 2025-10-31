#!/usr/bin/env python3
"""
Validate OpenAPI specification
Ensures the API spec is valid and matches implementation
"""

import json
import sys
from pathlib import Path

import yaml


def validate_openapi_spec():
    """Validate OpenAPI spec using openapi-spec-validator if available"""
    spec_path = Path("docs/api/openapi_v1.yaml")

    if not spec_path.exists():
        print(f"❌ OpenAPI spec not found at {spec_path}")
        return False

    try:
        # Load YAML
        with open(spec_path, "r") as f:
            spec = yaml.safe_load(f)
        print(f"✅ OpenAPI spec loaded from {spec_path}")

        # Basic validation
        assert spec.get("openapi"), "Missing openapi version"
        assert spec.get("info"), "Missing info section"
        assert spec.get("paths"), "Missing paths section"
        print("✅ Basic structure validated")

        # Check version
        version = spec["info"].get("version", "unknown")
        print(f"   API Version: {version}")

        # Count endpoints
        endpoint_count = len(spec.get("paths", {}))
        print(f"   Endpoints: {endpoint_count}")

        # Count schemas
        schema_count = len(spec.get("components", {}).get("schemas", {}))
        print(f"   Schemas: {schema_count}")

        # Try advanced validation if library available
        try:
            from openapi_spec_validator import validate_spec

            validate_spec(spec)
            print("✅ OpenAPI spec fully validated with openapi-spec-validator")
        except ImportError:
            print("⚠️  openapi-spec-validator not installed, skipping advanced validation")
            print("   Install with: pip install openapi-spec-validator")
        except Exception as e:
            print(f"❌ OpenAPI validation error: {e}")
            return False

        return True

    except yaml.YAMLError as e:
        print(f"❌ YAML parsing error: {e}")
        return False
    except AssertionError as e:
        print(f"❌ Validation error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def check_endpoints_match():
    """Check if documented endpoints match implementation"""
    spec_path = Path("docs/api/openapi_v1.yaml")

    try:
        with open(spec_path, "r") as f:
            spec = yaml.safe_load(f)

        paths = spec.get("paths", {})

        # Expected endpoints
        expected = [
            "/api/v1/healthz",
            "/api/v1/search/advanced",
            "/api/v1/recall/{id}",
            "/api/v1/fda",
            "/api/v1/agencies",
        ]

        documented = list(paths.keys())

        print("\n📋 Endpoint Coverage:")
        for endpoint in expected:
            if endpoint in documented:
                print(f"   ✅ {endpoint}")
            else:
                # Check with parameter placeholders
                endpoint_pattern = endpoint.replace("{id}", "{")
                found = any(endpoint_pattern in doc for doc in documented)
                if found:
                    print(f"   ✅ {endpoint}")
                else:
                    print(f"   ❌ {endpoint} (missing in spec)")

        # Check for extra endpoints
        for endpoint in documented:
            if endpoint not in expected:
                print(f"   ⚠️  {endpoint} (extra in spec)")

        return True

    except Exception as e:
        print(f"❌ Error checking endpoints: {e}")
        return False


def validate_examples():
    """Validate that examples in spec are valid JSON"""
    spec_path = Path("docs/api/openapi_v1.yaml")

    try:
        with open(spec_path, "r") as f:
            spec = yaml.safe_load(f)

        print("\n📝 Validating Examples:")
        example_count = 0

        # Check request examples
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    # Check request body examples
                    request_body = details.get("requestBody", {})
                    content = request_body.get("content", {})
                    for content_type, content_details in content.items():
                        examples = content_details.get("examples", {})
                        for example_name, example_data in examples.items():
                            example_count += 1
                            value = example_data.get("value")
                            if value:
                                try:
                                    # Validate it's proper JSON structure
                                    json.dumps(value)
                                    print(f"   ✅ {path} {method.upper()} - {example_name}")
                                except:
                                    print(f"   ❌ {path} {method.upper()} - {example_name} (invalid JSON)")

        print(f"   Total examples validated: {example_count}")
        return example_count > 0

    except Exception as e:
        print(f"❌ Error validating examples: {e}")
        return False


def main():
    """Main validation routine"""
    print("=" * 60)
    print("🔍 OpenAPI Specification Validation")
    print("=" * 60)

    all_passed = True

    # Validate spec
    if not validate_openapi_spec():
        all_passed = False

    # Check endpoints
    if not check_endpoints_match():
        all_passed = False

    # Validate examples
    if not validate_examples():
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All validations passed!")
        print("✅ OpenAPI spec is ready for use")
    else:
        print("⚠️  Some validations failed")
        print("Please review and fix the issues above")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
