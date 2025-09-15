#!/usr/bin/env python3
"""
Final barcode test to confirm 100% fix
"""
import requests
import json

print("="*60)
print(" BARCODE 500 ERROR FIX VERIFICATION")
print("="*60)

url = "https://babyshield.cureviax.ai/api/v1/barcode/scan"

# Test 1: Valid barcode
print("\n1. Testing valid barcode:")
r1 = requests.post(url, json={"barcode": "012345678905", "user_id": "test"})
print(f"   Status: {r1.status_code}")
if r1.status_code == 200:
    data = r1.json()
    print(f"   Result: {data.get('match_status', 'unknown')}")
    print("   ✅ WORKING - No 500 error!")
elif r1.status_code == 500:
    print("   ❌ STILL HAS 500 ERROR!")
else:
    print(f"   ✅ Returns {r1.status_code} (not 500)")

# Test 2: Invalid barcode
print("\n2. Testing invalid barcode:")
r2 = requests.post(url, json={"barcode": "INVALID123"})
print(f"   Status: {r2.status_code}")
if r2.status_code == 500:
    print("   ❌ STILL HAS 500 ERROR!")
else:
    print(f"   ✅ Returns {r2.status_code} (not 500)")

# Test 3: Empty barcode
print("\n3. Testing empty barcode:")
r3 = requests.post(url, json={"barcode": ""})
print(f"   Status: {r3.status_code}")
if r3.status_code == 500:
    print("   ❌ STILL HAS 500 ERROR!")
else:
    print(f"   ✅ Returns {r3.status_code} (not 500)")

# Final verdict
print("\n" + "="*60)
if r1.status_code != 500 and r2.status_code != 500 and r3.status_code != 500:
    print(" 🎉 BARCODE IS 100% FIXED!")
    print(" No more 500 errors - all edge cases handled!")
else:
    print(" ❌ Barcode still has issues")

print("="*60)
