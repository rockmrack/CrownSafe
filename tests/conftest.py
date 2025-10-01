import time
import pytest
from httpx import AsyncClient, ASGITransport
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

