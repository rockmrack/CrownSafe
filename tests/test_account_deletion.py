import time
from httpx import AsyncClient
import pytest

@pytest.mark.anyio
async def test_delete_requires_auth(app_client: AsyncClient):
    r = await app_client.delete("/api/v1/account")
    assert r.status_code in (401, 403)

@pytest.mark.anyio
async def test_delete_happy_path(auth_client_factory, user_factory):
    user = await user_factory()
    client = await auth_client_factory(user, fresh=True)  # token with auth_time<5min
    r = await client.delete("/api/v1/account")
    assert r.status_code == 204

    # token reuse must fail (blocklisted)
    r2 = await client.get("/api/v1/me")
    assert r2.status_code in (401, 403)

@pytest.mark.anyio
async def test_delete_requires_recent_auth(auth_client_factory, user_factory, monkeypatch):
    user = await user_factory()
    client = await auth_client_factory(user, fresh=False)  # token older than 5min
    r = await client.delete("/api/v1/account")
    assert r.status_code == 401
    assert "Re-authentication required" in r.text

@pytest.mark.anyio
async def test_legacy_endpoint_returns_410(app_client: AsyncClient):
    r = await app_client.post("/api/v1/user/data/delete")
    assert r.status_code == 410

@pytest.mark.anyio
async def test_rate_limit_3_per_day(auth_client_factory, user_factory):
    user = await user_factory()
    client = await auth_client_factory(user, fresh=True)

    # 1st attempt (we won't actually delete user; assume test DB rollback/fixture isolation)
    for i in range(3):
        r = await client.delete("/api/v1/account")
        # allow 204 or 401 depending on fixture isolation; focus on rate limit at 4th call
        assert r.status_code in (204, 401, 403)

    r4 = await client.delete("/api/v1/account")
    assert r4.status_code == 429
