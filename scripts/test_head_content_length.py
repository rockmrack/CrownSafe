from fastapi.testclient import TestClient
from api.main_babyshield import app
import uuid

c = TestClient(app)


def auth():
    # fresh email each run to avoid "Email already registered"
    email = f"test+{uuid.uuid4().hex[:6]}@ex.com"
    pw = "Passw0rd!"
    r = c.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pw, "confirm_password": pw},
    )
    if r.status_code not in (200, 201):
        text_lower = (r.text or "").lower()
        if r.status_code == 400 and "already registered" in text_lower:
            pass  # proceed to login for idempotency
        else:
            raise RuntimeError(f"register failed: {r.status_code} {r.text}")
    r = c.post("/api/v1/auth/token", data={"username": email, "password": pw})
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token") or r.json().get("token")
    headers = {"Authorization": f"Bearer {tok}"}
    me = c.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    uid = me.json().get("id") or me.json().get("user_id") or me.json().get("user", {}).get("id")
    return headers, uid


def gen_and_check(headers, uid, report_type):
    payload = {"user_id": uid, "report_type": report_type, "format": "pdf"}
    r = c.post("/api/v1/baby/reports/generate", headers=headers, json=payload)
    print(report_type, "generate_status", r.status_code)
    print(report_type, "generate_body", r.text)
    assert r.status_code == 200, r.text
    url = r.json()["download_url"]

    rh = c.head(url, headers=headers)
    rg = c.get(url, headers=headers)
    head_len = int(rh.headers.get("Content-Length", "0"))
    get_len = int(rg.headers.get("Content-Length", "0"))
    print(report_type, "HEAD_status", rh.status_code, "HEAD_Content-Length", head_len)
    print(report_type, "GET_status", rg.status_code, "GET_Content-Length", get_len)
    assert rh.status_code == 200 == rg.status_code
    assert head_len == get_len, f"{report_type}: mismatch HEAD {head_len} vs GET {get_len}"


if __name__ == "__main__":
    headers, uid = auth()
    gen_and_check(headers, uid, "product_safety")
    gen_and_check(headers, uid, "safety_summary")
    print("OK: HEAD Content-Length matches GET for both types.")

from fastapi.testclient import TestClient
from api.main_babyshield import app

c = TestClient(app)

def auth():
    r = c.post("/api/v1/auth/register", json={
        "email":"test+headlen@ex.com",
        "password":"Passw0rd!",
        "confirm_password":"Passw0rd!"
    })
    assert r.status_code == 200, r.text
    r = c.post("/api/v1/auth/token", data={"username":"test+headlen@ex.com","password":"Passw0rd!"})
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token") or r.json().get("token")
    headers = {"Authorization": f"Bearer {tok}"}
    me = c.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    user = me.json()
    uid = user.get("id") or user.get("user_id") or user.get("user", {}).get("id")
    assert uid, f"Could not determine user id from {user}"
    return headers, uid

def gen_and_check(headers, uid, report_type):
    payload = {"user_id": uid, "report_type": report_type, "format": "pdf"}
    r = c.post("/api/v1/baby/reports/generate", headers=headers, json=payload)
    print(report_type, "generate_status", r.status_code)
    print(report_type, "generate_body", r.text)
    assert r.status_code == 200, r.text
    d = r.json()
    url = d["download_url"]

    rh = c.head(url, headers=headers)
    rg = c.get(url, headers=headers)

    head_len = int(rh.headers.get("Content-Length", "0") or 0)
    get_len  = len(rg.content)

    print(report_type, "HEAD_status", rh.status_code, "HEAD_Content-Length", head_len)
    print(report_type, "GET_status", rg.status_code, "GET_Content-Length", get_len)

    assert rh.status_code == 200 and rg.status_code == 200
    assert head_len == get_len, f"{report_type}: mismatch HEAD {head_len} vs GET {get_len}"

headers, uid = auth()
gen_and_check(headers, uid, "product_safety")
gen_and_check(headers, uid, "safety_summary")
print("OK: HEAD sizes match GET for both report types.")
