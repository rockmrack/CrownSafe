#!/usr/bin/env python3
"""
Lint JSON/YAML files and validate links in documentation
"""

import os
import sys
import json
import re
import time
import yaml
import requests

ROOT = os.path.dirname(os.path.dirname(__file__))

# Files to JSON-parse
JSON_FILES = [
    "docs/store/apple/metadata.json",
    "docs/store/google/listing.json",
    "docs/app_review/privacy_labels_apple.json",
    "docs/app_review/google_data_safety.json",
]

# MD files whose links we validate (GET 200)
MD_FILES = [
    "docs/store/apple/review_notes.md",
    "docs/store/google/review_notes.md",
    "docs/store/common/descriptions/long_description_en.txt",
    "docs/store/common/descriptions/short_tagline.txt",
]

BASE = os.getenv("BABYSHIELD_BASE_URL", "https://babyshield.cureviax.ai")
REQUIRED_200 = [f"{BASE}/legal/privacy", f"{BASE}/legal/terms", f"{BASE}/legal/data-deletion"]


def ok(cond, msg):
    """Print status and exit if condition is false"""
    print(("✅ " if cond else "❌ ") + msg)
    if not cond:
        sys.exit(1)


def load_json(path):
    """Load and parse JSON file"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path):
    """Load and parse YAML file"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def find_links(text):
    """Find all HTTP(S) links in text"""
    # crude but effective: http(s) links
    return re.findall(r"https?://[^\s)>\]]+", text)


def http_ok(url, expect=200, timeout=15):
    """Check if URL returns expected status code"""
    try:
        r = requests.get(url, timeout=timeout, allow_redirects=True)
        return r.status_code == expect
    except Exception:
        return False


def main():
    """Main validation function"""
    print("🔍 Starting docs and links validation...")
    print("=" * 60)

    # JSON lint
    print("\n📋 Validating JSON files...")
    for rel in JSON_FILES:
        p = os.path.join(ROOT, rel)
        ok(os.path.exists(p), f"{rel} exists")
        try:
            _ = load_json(p)
            ok(True, f"{rel} valid JSON")
        except Exception as e:
            ok(False, f"{rel} invalid JSON: {e}")

    # YAML sanity if present
    print("\n📋 Validating YAML files...")
    for rel in ("docs/api/openapi_v1.yaml", "docs/api/openapi_v1.yml"):
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            try:
                _ = load_yaml(p)
                ok(True, f"{rel} parses as YAML")
            except Exception as e:
                ok(False, f"{rel} invalid YAML: {e}")

    # MD link checks
    print("\n🔗 Checking links in documentation...")
    for rel in MD_FILES:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            print(f"⚠️  {rel} not found, skipping")
            continue

        with open(p, "r", encoding="utf-8") as f:
            txt = f.read()

        links = find_links(txt)
        if links:
            print(f"   Checking {len(links)} links in {rel}...")
            bad = []
            for u in links:
                if not http_ok(u):
                    bad.append(u)
                    print(f"     ❌ Dead link: {u}")
            ok(len(bad) == 0, f"{rel} all external links reachable")
        else:
            print(f"   No links found in {rel}")

    # Legal pages must be live
    print("\n🔒 Checking required legal pages...")
    for url in REQUIRED_200:
        ok(http_ok(url), f"Legal page live: {url}")

    print("\n" + "=" * 60)
    print("🎉 Docs & links look good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
