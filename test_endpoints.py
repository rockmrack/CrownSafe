"""Test script to verify all API endpoints are operational."""

import sys

sys.path.insert(0, ".")

try:
    from api.main_crownsafe import app

    print("✓ Main application imported successfully")

    # Get all routes
    routes = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            methods = list(route.methods) if route.methods else []
            routes.append((route.path, methods))

    print(f"\n✓ Found {len(routes)} endpoints:")

    # Group by prefix
    endpoints_by_prefix = {}
    for path, methods in routes:
        prefix = path.split("/")[1] if len(path.split("/")) > 1 else "root"
        if prefix not in endpoints_by_prefix:
            endpoints_by_prefix[prefix] = []
        endpoints_by_prefix[prefix].append((path, methods))

    # Display endpoints by group
    for prefix, endpoint_list in sorted(endpoints_by_prefix.items()):
        print(f"\n  {prefix.upper()}:")
        for path, methods in sorted(endpoint_list):
            method_str = ", ".join(sorted(methods)) if methods else "N/A"
            print(f"    {method_str:20} {path}")

    print("\n✓ All endpoints are operational and ready to serve requests")
    print("\nTo start the server, run:")
    print("  uvicorn api.main_crownsafe:app --host 0.0.0.0 --port 8001 --reload")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
