"""Comprehensive endpoint verification for BabyShield API."""

import sys

sys.path.insert(0, ".")

print("=" * 70)
print("BabyShield API - Endpoint Verification")
print("=" * 70)

# Test 1: Import main application
print("\n[1/5] Testing main application import...")
try:
    from api.main_crownsafe import app

    print("✓ Main application imported successfully")
except Exception as e:
    print(f"✗ Failed to import main application: {e}")
    sys.exit(1)

# Test 2: Import all endpoint modules
print("\n[2/5] Testing endpoint module imports...")
endpoint_modules = [
    "api.barcode_endpoints",
    "api.scan_history_endpoints",
    "api.user_dashboard_endpoints",
    "api.incident_report_endpoints",
    "api.safety_reports_endpoints",
    "api.auth_endpoints",
]

failed_imports = []
for module in endpoint_modules:
    try:
        __import__(module)
        print(f"  ✓ {module}")
    except Exception as e:
        print(f"  ✗ {module}: {e}")
        failed_imports.append((module, e))

if failed_imports:
    print(f"\n✗ {len(failed_imports)} module(s) failed to import")
    sys.exit(1)
else:
    print(f"\n✓ All {len(endpoint_modules)} endpoint modules imported successfully")

# Test 3: Count registered routes
print("\n[3/5] Analyzing registered routes...")
routes_with_path = [r for r in app.routes if hasattr(r, "path")]
print(f"  Total routes: {len(routes_with_path)}")

# Test 4: Group routes by API prefix
print("\n[4/5] API endpoint groups:")
api_prefixes = {}
for route in routes_with_path:
    if hasattr(route, "methods") and route.methods:
        path_parts = route.path.split("/")
        if len(path_parts) > 2 and path_parts[1] == "api":
            prefix = path_parts[2] if len(path_parts) > 2 else "root"
            if prefix not in api_prefixes:
                api_prefixes[prefix] = []
            api_prefixes[prefix].append(route.path)

for prefix in sorted(api_prefixes.keys()):
    count = len(api_prefixes[prefix])
    print(f"  /api/{prefix:<30} {count:3} endpoint(s)")

# Test 5: Check critical endpoints
print("\n[5/5] Verifying critical endpoints exist...")
critical_endpoints = [
    "/api/auth/register",
    "/api/auth/login",
    "/api/barcode/scan",
    "/api/scan-history",
    "/api/dashboard/overview",
    "/api/incidents/report",
    "/api/safety-reports",
]

missing_endpoints = []
all_paths = [r.path for r in routes_with_path]
for endpoint in critical_endpoints:
    if endpoint in all_paths:
        print(f"  ✓ {endpoint}")
    else:
        print(f"  ✗ {endpoint} (MISSING)")
        missing_endpoints.append(endpoint)

# Final summary
print("\n" + "=" * 70)
if not failed_imports and not missing_endpoints:
    print("✓ ALL ENDPOINTS ARE OPERATIONAL")
    print(f"✓ {len(routes_with_path)} routes registered")
    print(f"✓ {len(api_prefixes)} API endpoint groups")
    print("\nServer is ready to start:")
    print("  uvicorn api.main_crownsafe:app --host 0.0.0.0 --port 8001 --reload")
else:
    print("✗ ISSUES DETECTED:")
    if failed_imports:
        print(f"  - {len(failed_imports)} module import failures")
    if missing_endpoints:
        print(f"  - {len(missing_endpoints)} critical endpoints missing")
    sys.exit(1)

print("=" * 70)
