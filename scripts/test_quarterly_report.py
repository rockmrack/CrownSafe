import os
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite:///./babyshield_test.db"
os.environ["TEST_MODE"] = "true"
os.environ["CREATE_TABLES_ON_IMPORT"] = "true"

from fastapi.testclient import TestClient
from api.main_babyshield import app


def main():
    c = TestClient(app)
    email = f"test+{uuid4().hex[:6]}@ex.com"
    password = "P@ssw0rd!"

    r = c.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "confirm_password": password},
    )
    print("register_status", r.status_code)

    r = c.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password, "grant_type": "password"},
    )
    print("token_status", r.status_code)
    access = r.json().get("access_token")
    headers = {"Authorization": f"Bearer {access}"}

    me = c.get("/api/v1/auth/me", headers=headers)
    user_id = me.json().get("id") if me.status_code == 200 else 1
    print("me_status", me.status_code, "user_id", user_id)

    payload = {
        "user_id": user_id,
        "report_type": "nursery_quarterly",
        "format": "pdf",
        "products": ["Yoto Mini Player", "Graco Car Seat", "Generic Silicone Teethers"],
    }
    gen = c.post("/api/v1/baby/reports/generate", json=payload, headers=headers)
    print("generate_status", gen.status_code)
    print("generate_body", gen.text)


if __name__ == "__main__":
    main()
