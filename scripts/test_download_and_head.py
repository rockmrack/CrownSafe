import os
import uuid
from fastapi.testclient import TestClient
from api.main_babyshield import app

# Env (local SQLite)
os.environ.setdefault("DATABASE_URL", "sqlite:///./babyshield_test.db")
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("CREATE_TABLES_ON_IMPORT", "true")

client = TestClient(app)


def auth_and_get_user_id():
    email = f"test+{uuid.uuid4().hex[:6]}@ex.com"
    pwd = "P@ssw0rd!"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd, "confirm_password": pwd},
    )
    print("register_status", r.status_code)
    r = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": pwd, "grant_type": "password"},
    )
    print("token_status", r.status_code)
    tok = r.json().get("access_token")
    h = {"Authorization": f"Bearer {tok}"}
    me = client.get("/api/v1/auth/me", headers=h)
    print("me_status", me.status_code)
    uid = (me.json() or {}).get("id") or (
        me.json().get("data", {}) if me.ok else {}
    ).get("id")
    return h, uid


def extract_report(resp_json):
    # Handles both {"status":"success",...} and {"success":true,"data":{...}}
    rid = resp_json.get("report_id")
    dl = resp_json.get("download_url")
    if not rid and "data" in resp_json:
        rid = resp_json["data"].get("report_id")
        dl = resp_json["data"].get("download_url")
    if not dl and rid:
        dl = f"/api/v1/baby/reports/download/{rid}"
    return rid, dl


def generate(h, uid, rtype):
    payloads = ({"type": rtype, "user_id": uid}, {"report_type": rtype, "user_id": uid})
    last = None
    for p in payloads:
        last = client.post("/api/v1/baby/reports/generate", headers=h, json=p)
        if last.status_code == 200:
            break
    print(f"{rtype} generate_status", last.status_code)
    print(f"{rtype} generate_body", last.text)
    if last.status_code != 200:
        return None, None
    return extract_report(last.json())


def head_and_get(h, url, label):
    # HEAD
    rh = client.head(url, headers=h)
    print(f"{label} HEAD_status", rh.status_code)
    for k in [
        "Content-Type",
        "Content-Disposition",
        "Cache-Control",
        "Content-Length",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
    ]:
        if k in rh.headers:
            print(f"{label} {k}: {rh.headers[k]}")
    # GET
    rg = client.get(url, headers=h)
    print(f"{label} GET_status", rg.status_code)
    for k in ["Content-Type", "Content-Disposition", "Cache-Control", "Content-Length"]:
        if k in rg.headers:
            print(f"{label} {k}: {rg.headers[k]}")


def run():
    h, uid = auth_and_get_user_id()

    for rtype in ["product_safety", "nursery_quarterly"]:
        rid, url = generate(h, uid, rtype)
        if rid and url:
            head_and_get(h, url, rtype)


if __name__ == "__main__":
    run()
