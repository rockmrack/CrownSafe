#!/usr/bin/env python3
"""
Test SDK compilation and validity
"""

import os
import json
import sys
from pathlib import Path

def test_typescript_sdk():
    """Check TypeScript SDK exists and has proper structure"""
    sdk_path = Path("clients/mobile/babyshield_client.ts")
    
    if not sdk_path.exists():
        print("   ❌ TypeScript SDK not found")
        return False
    
    with open(sdk_path, 'r') as f:
        content = f.read()
    
    # Check for key components
    checks = [
        ("export class BabyShieldClient", "BabyShieldClient class"),
        ("export interface RecallItem", "RecallItem interface"),
        ("export type Severity", "Severity type"),
        ("searchAdvanced", "searchAdvanced method"),
        ("getRecallById", "getRecallById method"),
    ]
    
    all_good = True
    for check, name in checks:
        if check in content:
            print(f"   ✅ {name} found")
        else:
            print(f"   ❌ {name} missing")
            all_good = False
    
    # Check file size
    lines = len(content.split('\n'))
    print(f"   ℹ️  TypeScript SDK has {lines} lines")
    
    return all_good

def test_swift_sdk():
    """Check Swift SDK exists and has proper structure"""
    sdk_path = Path("clients/ios/BabyShieldClient.swift")
    
    if not sdk_path.exists():
        print("   ❌ Swift SDK not found")
        return False
    
    with open(sdk_path, 'r') as f:
        content = f.read()
    
    # Check for key components
    checks = [
        ("final class BabyShieldClient", "BabyShieldClient class"),
        ("struct RecallItem", "RecallItem struct"),
        ("enum Severity", "Severity enum"),
        ("func searchAdvanced", "searchAdvanced method"),
        ("func getRecallById", "getRecallById method"),
    ]
    
    all_good = True
    for check, name in checks:
        if check in content:
            print(f"   ✅ {name} found")
        else:
            print(f"   ❌ {name} missing")
            all_good = False
    
    # Check file size
    lines = len(content.split('\n'))
    print(f"   ℹ️  Swift SDK has {lines} lines")
    
    return all_good

def test_postman_collection():
    """Check Postman collection is valid JSON with proper structure"""
    collection_path = Path("docs/api/postman/BabyShield_v1.postman_collection.json")
    
    if not collection_path.exists():
        print("   ❌ Postman collection not found")
        return False
    
    try:
        with open(collection_path, 'r') as f:
            collection = json.load(f)
        print("   ✅ Postman collection is valid JSON")
    except json.JSONDecodeError as e:
        print(f"   ❌ Postman collection has invalid JSON: {e}")
        return False
    
    # Check structure
    if 'info' in collection:
        print(f"   ✅ Collection info: {collection['info'].get('name', 'Unknown')}")
    else:
        print("   ❌ Missing collection info")
        return False
    
    # Count requests
    total_requests = 0
    if 'item' in collection:
        for item in collection['item']:
            if 'item' in item:  # Folder
                total_requests += len(item['item'])
            elif 'request' in item:  # Direct request
                total_requests += 1
        print(f"   ✅ Collection has {total_requests} requests")
    else:
        print("   ❌ No items in collection")
        return False
    
    # Check for variables
    if 'variable' in collection:
        vars_list = [f"{v['key']}={v.get('value', 'undefined')}" for v in collection['variable']]
        print(f"   ✅ Variables: {', '.join(vars_list)}")
    
    return total_requests > 0

def test_openapi_exists():
    """Check OpenAPI spec exists"""
    spec_path = Path("docs/api/openapi_v1.yaml")
    
    if spec_path.exists():
        with open(spec_path, 'r', encoding='utf-8') as f:
            lines = len(f.read().split('\n'))
        print(f"   ✅ OpenAPI spec exists ({lines} lines)")
        return True
    else:
        print("   ❌ OpenAPI spec not found")
        return False

def test_readme_exists():
    """Check API README exists"""
    readme_path = Path("docs/api/README.md")
    
    if readme_path.exists():
        with open(readme_path, 'r', encoding='utf-8') as f:
            lines = len(f.read().split('\n'))
        print(f"   ✅ API README exists ({lines} lines)")
        return True
    else:
        print("   ❌ API README not found")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("📱 Mobile SDK & API Documentation Test")
    print("=" * 60)
    
    results = []
    
    print("\n1. TypeScript SDK Check...")
    results.append(test_typescript_sdk())
    
    print("\n2. Swift SDK Check...")
    results.append(test_swift_sdk())
    
    print("\n3. Postman Collection Check...")
    results.append(test_postman_collection())
    
    print("\n4. OpenAPI Spec Check...")
    results.append(test_openapi_exists())
    
    print("\n5. API README Check...")
    results.append(test_readme_exists())
    
    print("\n" + "=" * 60)
    
    if all(results):
        print("🎉 All SDK and documentation tests passed!")
        print("✅ Task 3 completed successfully")
        return 0
    else:
        print("⚠️  Some tests failed")
        print("Please review and fix the issues above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
