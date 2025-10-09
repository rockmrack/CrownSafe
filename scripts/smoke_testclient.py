import os
import sys
import pathlib
import json
from uuid import uuid4

# Ensure local test env
os.environ.setdefault("DATABASE_URL", "sqlite:///./babyshield_test.db")
os.environ.setdefault("TEST_MODE", "true")

# Ensure repo root is importable
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient
from api.main_babyshield import app


def main() -> int:
    client = TestClient(app)

    results = {}

    def record(name: str, resp):
        results[name] = resp.status_code
        print(f"{name}: {resp.status_code}")
        return resp

    # Health
    record("healthz", client.get("/healthz"))
    record("readyz", client.get("/readyz"))

    # Auth: register → token → me
    email = f"test+{uuid4().hex[:8]}@example.com"
    password = "P@ssw0rd!"
    r_reg = record(
        "register",
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "confirm_password": password},
        ),
    )

    user_id = None
    if r_reg.status_code == 200:
        try:
            user_id = r_reg.json().get("id")
        except Exception:
            pass

    r_tok = record(
        "token",
        client.post(
            "/api/v1/auth/token",
            data={"username": email, "password": password, "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ),
    )

    access_token = None
    if r_tok.status_code == 200:
        try:
            access_token = r_tok.json().get("access_token")
        except Exception:
            pass

    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
    record("me", client.get("/api/v1/auth/me", headers=headers))

    # Premium endpoints
    if user_id is None:
        print("No user_id from register; skipping premium checks")
    else:
        record(
            "pregnancy_check",
            client.post(
                "/api/v1/premium/pregnancy/check",
                json={"barcode": "012345678905", "trimester": 1, "user_id": user_id},
                headers=headers,
            ),
        )
        record(
            "allergy_check",
            client.post(
                "/api/v1/premium/allergy/check",
                json={"barcode": "012345678905", "user_id": user_id},
                headers=headers,
            ),
        )

    print("SUMMARY:", json.dumps(results, indent=2))
    # Exit non-zero if any critical failed
    failures = [k for k, v in results.items() if v >= 400]
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
