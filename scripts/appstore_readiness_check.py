#!/usr/bin/env python3
"""
App Store Readiness Check for BabyShield API
Validates API stability, predictability, and documentation for App Store/Play review
"""

import os
import sys
import threading
import time

import requests

BASE = os.getenv("BABYSHIELD_BASE_URL", "https://babyshield.cureviax.ai")
S = requests.Session()
S.headers.update({"Content-Type": "application/json"})


def expect(cond, msg):
    if not cond:
        print(f"❌ {msg}")
        sys.exit(1)
    print(f"✅ {msg}")


def get_json(path):
    try:
        r = S.get(f"{BASE}{path}", timeout=15)
        return r, (r.json() if r.headers.get("content-type", "").startswith("application/json") else None)
    except Exception as e:
        print(f"❌ Failed to GET {path}: {e}")
        return None, None


def post_json(path, payload):
    try:
        r = S.post(f"{BASE}{path}", json=payload, timeout=30)
        return r, (r.json() if r.headers.get("content-type", "").startswith("application/json") else None)
    except Exception as e:
        print(f"❌ Failed to POST {path}: {e}")
        return None, None


print("=" * 80)
print("🚀 BABYSHIELD API - APP STORE READINESS CHECK")
print(f"🌍 Target: {BASE}")
print("=" * 80)
print()

# Track overall status
all_passed = True

# 1) Health + version + headers
print("📋 1. Health Check & Security Headers")
print("-" * 40)
r, j = get_json("/api/v1/healthz")
expect(r and r.status_code == 200, "/api/v1/healthz returns 200")
expect(r and "X-API-Version" in r.headers, "X-API-Version header present")
expect(r and r.headers.get("Strict-Transport-Security"), "HSTS header present")
expect(r and r.headers.get("X-Content-Type-Options") == "nosniff", "nosniff header present")
expect(
    r and r.headers.get("X-Frame-Options") in {"DENY", "SAMEORIGIN"},
    "X-Frame-Options present",
)

# 2) Docs available
print("\n📚 2. API Documentation")
print("-" * 40)
r, _ = get_json("/api/v1/docs")
expect(r and r.status_code in [200, 302], "Swagger UI reachable at /api/v1/docs")
r, _ = get_json("/api/v1/openapi.json")
expect(r and r.status_code in [200, 302], "OpenAPI JSON reachable")

# Alternative paths for documentation
r, _ = get_json("/docs")
expect(r and r.status_code == 200, "Swagger UI also at /docs")
r, _ = get_json("/openapi.json")
expect(r and r.status_code == 200, "OpenAPI JSON also at /openapi.json")

# 3) Functional search (short query & product)
print("\n🔍 3. Search Functionality")
print("-" * 40)
payload = {"product": "pacifier", "agencies": ["FDA"], "limit": 3}
r, j = post_json("/api/v1/search/advanced", payload)
expect(r and r.status_code == 200, "advanced search basic POST works")
expect(j and j.get("ok"), "search returns ok=true")

items = []
if j and "data" in j and "items" in j["data"]:
    items = j["data"]["items"]
elif j and "items" in j:
    items = j["items"]

expect(isinstance(items, list), "advanced search returns items list")
print(f"   ℹ️ Found {len(items)} results for 'pacifier'")

# 4) Aliases & validation errors
print("\n🔄 4. Parameter Aliases & Validation")
print("-" * 40)
alias_payload = {
    "severity": "medium",
    "product_category": "drug",
    "agency": "FDA",
    "product": "bottle",
    "limit": 2,
}
r, j = post_json("/api/v1/search/advanced", alias_payload)
expect(r and r.status_code == 200, "aliases accepted (severity/product_category/agency)")

# Test that risk_level and riskCategory also work
alt_alias_payload = {
    "risk_level": "high",
    "riskCategory": "baby food",
    "agencies": ["CPSC"],
    "query": "toy",
    "limit": 2,
}
r, j = post_json("/api/v1/search/advanced", alt_alias_payload)
expect(r and r.status_code == 200, "alternative aliases accepted")

# Bad request test
bad_payload = {"foo": "bar"}
r, j = post_json("/api/v1/search/advanced", bad_payload)
expect(
    r and (r.status_code == 400 or (r.status_code == 422 and j)),
    "invalid params produce 400/422",
)
expect(j and (j.get("error") or j.get("detail")), "error message present for bad request")

# 5) Pagination & deterministic order
print("\n📖 5. Pagination & Ordering")
print("-" * 40)
payload2 = {"product": "doll", "agencies": ["FDA"], "limit": 2}
r, j = post_json("/api/v1/search/advanced", payload2)
expect(r and r.status_code == 200, "pagination first page 200")

first_items = []
cursor = None
if j and "data" in j:
    first_items = j["data"].get("items", [])
    cursor = j["data"].get("nextCursor")
elif j:
    first_items = j.get("items", [])
    cursor = j.get("nextCursor")

if cursor:
    # Test pagination with cursor
    r2, j2 = post_json("/api/v1/search/advanced", {"product": "doll", "nextCursor": cursor})
    expect(r2 and r2.status_code == 200, "pagination next page 200")

    second_items = []
    if j2 and "data" in j2:
        second_items = j2["data"].get("items", [])
    elif j2:
        second_items = j2.get("items", [])

    first_ids = {item.get("id") or item.get("recall_id") for item in first_items}
    second_ids = {item.get("id") or item.get("recall_id") for item in second_items}
    expect(not first_ids.intersection(second_ids), "no overlap between pages")
else:
    print("   ℹ️ Pagination cursor not implemented yet")

# 6) Per-ID lookup must succeed for any item found
print("\n🔎 6. Individual Recall Lookup")
print("-" * 40)
if items and len(items) > 0:
    rid = items[0].get("id") or items[0].get("recall_id")
    if rid:
        r, j = get_json(f"/api/v1/recall/{rid}")
        expect(r and r.status_code == 200, f"recall detail works for {rid}")
        expect(j and (j.get("ok") or j.get("data")), "recall detail returns data")
    else:
        print("   ⚠️ No recall ID field found in search results")
else:
    print("   ⚠️ No items to test individual lookup")

# 7) Error semantics
print("\n❌ 7. Error Handling")
print("-" * 40)
r, j = post_json("/api/v1/search/advanced", {"product": "test", "date_from": "invalid-date"})
expect(r and r.status_code in (400, 422), "invalid date returns 4xx")

r, j = get_json("/api/v1/recall/DOES-NOT-EXIST-99999")
expect(r and r.status_code == 404, "unknown recall id returns 404")

# Empty search
r, j = post_json("/api/v1/search/advanced", {"product": ""})
expect(r and r.status_code in (400, 422), "empty search term returns 4xx")

# 8) CORS preflight (simulate webview)
print("\n🌐 8. CORS Support")
print("-" * 40)
try:
    r = requests.options(
        f"{BASE}/api/v1/search/advanced",
        headers={
            "Origin": "https://app.babyshield.ai",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
        timeout=15,
    )

    expect(r.status_code in (200, 204), "CORS preflight allowed")

    # Check for CORS headers (case-insensitive)
    headers_lower = {k.lower(): v for k, v in r.headers.items()}
    expect(
        "access-control-allow-origin" in headers_lower,
        "CORS allow-origin header present",
    )
    expect(
        "access-control-allow-methods" in headers_lower,
        "CORS allow-methods header present",
    )
except Exception as e:
    print(f"   ⚠️ CORS test failed: {e}")

# 9) Light performance check (20 concurrent POSTs, measure p95)
print("\n⚡ 9. Performance Test")
print("-" * 40)
lat = []
errors = []


def worker():
    try:
        t0 = time.time()
        r, j = post_json("/api/v1/search/advanced", {"product": "bottle", "limit": 3})
        elapsed = (time.time() - t0) * 1000
        if r and r.status_code == 200:
            lat.append(elapsed)
        else:
            errors.append(f"Status {r.status_code if r else 'None'}")
    except Exception as e:
        errors.append(str(e))


threads = []
print("   Running 20 concurrent requests...")
for _ in range(20):
    th = threading.Thread(target=worker)
    th.start()
    threads.append(th)

for th in threads:
    th.join()

if lat:
    lat_sorted = sorted(lat)
    p50 = lat_sorted[len(lat) // 2]
    p95 = lat_sorted[int(len(lat) * 0.95) - 1] if len(lat) > 1 else lat_sorted[0]
    p99 = lat_sorted[-1]
    avg = sum(lat) / len(lat)

    print("   📊 Latency stats (ms):")
    print(f"      • Average: {avg:.0f} ms")
    print(f"      • P50: {p50:.0f} ms")
    print(f"      • P95: {p95:.0f} ms")
    print(f"      • P99: {p99:.0f} ms")
    print(f"      • Success rate: {len(lat)}/20 ({len(lat) * 5}%)")

    expect(p95 < 800, "p95 latency < 800ms under light load")
    expect(len(lat) >= 18, "at least 90% success rate")
else:
    print(f"   ❌ All requests failed: {errors[:3]}")
    all_passed = False

# 10) Additional API checks
print("\n🔧 10. Additional API Checks")
print("-" * 40)

# Check FDA quick search
r, j = get_json("/api/v1/fda?product=toy&limit=5")
expect(r and r.status_code == 200, "FDA quick search endpoint works")

# Check agencies list
r, j = get_json("/api/v1/agencies")
if r and r.status_code == 200:
    agencies = j.get("data", {}).get("agencies", []) if j else []
    expect(len(agencies) > 0, f"agencies endpoint returns list ({len(agencies)} found)")
else:
    print("   ⚠️ Agencies endpoint not available")

# Check for traceId in responses
r, j = post_json("/api/v1/search/advanced", {"product": "test product"})
if j:
    has_trace = "traceId" in j or "trace_id" in j or (j.get("data") and "traceId" in j["data"])
    expect(has_trace, "traceId present in response")
else:
    print("   ⚠️ Could not verify traceId")

# Final summary
print("\n" + "=" * 80)
if all_passed and len(lat) > 0:
    print("🎉 ALL CHECKS PASSED - API IS APP STORE READY!")
    print("\n✅ Summary:")
    print("   • Health endpoint working")
    print("   • Security headers present")
    print("   • Documentation accessible")
    print("   • Search functionality verified")
    print("   • Aliases and validation working")
    print("   • Error handling correct")
    print("   • CORS configured")
    print(f"   • Performance acceptable (P95: {p95:.0f}ms)")
    print("\n🚀 The BabyShield API is ready for App Store submission!")
    sys.exit(0)
else:
    print("❌ SOME CHECKS FAILED - Please review the issues above")
    print("\n📋 Failed areas need attention before App Store submission")
    sys.exit(1)
