import sys
import os
import time
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

# Add project root to Python path for imports
# Use absolute path consistently to avoid confusion
project_root = Path(__file__).parent.parent.resolve()

# Validate project root structure (enabled by default, can be disabled with SKIP_PROJECT_VALIDATION)
if os.environ.get('SKIP_PROJECT_VALIDATION', 'false').lower() != 'true':
    # Validate that we have a proper project root with expected structure
    expected_dirs = ['api', 'core_infra', 'tests']
    missing_dirs = [d for d in expected_dirs if not (project_root / d).is_dir()]
    if missing_dirs:
        # Provide detailed debugging info
        try:
            all_dirs = [p.name for p in project_root.iterdir() if p.is_dir()]
        except Exception as e:
            all_dirs = f"[Error listing directories: {e}]"
        
        raise RuntimeError(
            f"Invalid project root: {project_root}\n"
            f"Missing expected directories: {missing_dirs}\n"
            f"Current directory structure: {all_dirs}\n"
            f"Working directory: {os.getcwd()}\n"
            f"To skip this check, set SKIP_PROJECT_VALIDATION=true"
        )

# Convert to string and add to sys.path
project_root_str = str(project_root)

# CRITICAL: Remove tests/ directory from sys.path to prevent shadowing
# pytest automatically adds tests/ which causes tests/core_infra to shadow real core_infra
# Remove ALL occurrences to prevent any shadowing
tests_dir = str(project_root / 'tests')
while tests_dir in sys.path:
    sys.path.remove(tests_dir)

# Ensure project root is at the BEGINNING of sys.path
# Remove all occurrences first, then add at position 0
while project_root_str in sys.path:
    sys.path.remove(project_root_str)
sys.path.insert(0, project_root_str)

# Debug: Print sys.path in CI to verify
if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS'):
    print(f"DEBUG: sys.path after conftest setup:")
    for i, p in enumerate(sys.path[:5]):
        print(f"  [{i}] {p}")

from api.main_babyshield import app  # FastAPI app

# Basic ASGI test client
@pytest.fixture
async def app_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

# Creates a user via the API and returns credentials
@pytest.fixture
def user_factory():
    async def _create():
        email = f"ci+{int(time.time()*1000)}@example.com"
        password = "StrongPass!2025"
        payload = {
            "email": email,
            "password": password,
            "confirm_password": password,
            "full_name": "CI"
        }
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/v1/auth/register", json=payload)
            assert r.status_code in (200, 201)
        return {"email": email, "password": password}
    return _create

# Logs in and returns an AsyncClient with Authorization header set
@pytest.fixture
def auth_client_factory():
    async def _login(user, fresh: bool = True):
        transport = ASGITransport(app=app)
        client = AsyncClient(transport=transport, base_url="http://test")
        form = {"username": user["email"], "password": user["password"], "grant_type": "password"}
        r = await client.post("/api/v1/auth/token", data=form)
        assert r.status_code == 200
        token = r.json().get("access_token") or r.json().get("token")
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client
    return _login

