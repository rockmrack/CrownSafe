#!/usr/bin/env python3
"""
Validate OpenAPI specification file locally
"""

import sys
import json
import yaml
from openapi_spec_validator import validate_spec
import os

PATHS = [
    "docs/api/openapi_v1.yaml",
    "docs/api/openapi_v1.yml",
    "docs/api/openapi_v1.json",
]


def main():
    """Validate OpenAPI spec if it exists"""
    path = next((p for p in PATHS if os.path.exists(p)), None)
    if not path:
        print("ℹ️ OpenAPI file not found locally; skipping.")
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            if path.endswith((".yaml", ".yml")):
                spec = yaml.safe_load(f)
            else:
                spec = json.load(f)

        # Validate the spec
        validate_spec(spec)
        print(f"✅ OpenAPI spec valid: {path}")
        return 0
    except Exception as e:
        print(f"❌ OpenAPI spec invalid: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
