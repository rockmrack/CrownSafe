import os, json, uuid
from fastapi.testclient import TestClient
from api.main_babyshield import app

# Ensure local test DB/env
os.environ.setdefault("DATABASE_URL", "sqlite:///./babyshield_test.db")
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("CREATE_TABLES_ON_IMPORT", "true")

client = TestClient(app)

def auth_headers():
    email = f"test+{uuid.uuid4().hex[:6]}@ex.com"
    pwd = "P@ssw0rd!"
    r = client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "confirm_password": pwd})
    print("register_status", r.status_code)
    r = client.post("/api/v1/auth/token", data={"username": email, "password": pwd, "grant_type": "password"})
    print("token_status", r.status_code)
    tok = r.json().get("access_token")
    return {"Authorization": f"Bearer {tok}"}

def generate_report(h, rtype):
    # Try both possible payload keys
    payloads = ({"type": rtype}, {"report_type": rtype})
    last = None
    for p in payloads:
        last = client.post("/api/v1/baby/reports/generate", headers=h, json=p)
        if last.status_code == 200:
            break
    print(f"{rtype} generate_status", last.status_code)
    print(f"{rtype} generate_body", last.text)
    if last.status_code != 200:
        return None, None
    data = last.json()
    rid = data.get("report_id")
    dl = data.get("download_url") or f"/api/v1/baby/reports/download/{rid}"
    return rid, dl

def head_check(h, url, label):
    r = client.head(url, headers=h)
    print(f"{label} HEAD_status", r.status_code)
    # Print key headers
    for k in ["Content-Type","Content-Disposition","Cache-Control","Content-Length","X-Content-Type-Options","X-Frame-Options","Referrer-Policy"]:
        if k in r.headers:
            print(f"{label} {k}: {r.headers[k]}")
    return r.status_code

def run_both():
    h = auth_headers()

    # Level 1: product_safety
    rid1, url1 = generate_report(h, "product_safety")
    if rid1 and url1:
        head_check(h, url1, "product_safety")

    # Level 2: nursery_quarterly
    rid2, url2 = generate_report(h, "nursery_quarterly")
    if rid2 and url2:
        head_check(h, url2, "nursery_quarterly")

if __name__ == "__main__":
    run_both()
