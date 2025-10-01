import os, uuid
from fastapi.testclient import TestClient
from api.main_babyshield import app

os.environ.setdefault("DATABASE_URL", "sqlite:///./babyshield_test.db")
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("CREATE_TABLES_ON_IMPORT", "true")

client = TestClient(app)

def auth():
    email = f"test+{uuid.uuid4().hex[:6]}@ex.com"; pwd = "P@ssw0rd!"
    r = client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "confirm_password": pwd})
    print("register_status", r.status_code)
    r = client.post("/api/v1/auth/token", data={"username": email, "password": pwd, "grant_type": "password"})
    print("token_status", r.status_code)
    tok = r.json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    me = client.get("/api/v1/auth/me", headers=h)
    print("me_status", me.status_code)
    uid = (me.json() or {}).get("id") or (me.json().get("data", {}) if me.ok else {}).get("id")
    return h, uid

def run():
    h, uid = auth()
    # Generate
    r = client.post("/api/v1/baby/reports/generate", headers=h, json={"report_type":"safety_summary","user_id":uid})
    print("safety_summary generate_status", r.status_code)
    print("safety_summary generate_body", r.text)
    if r.status_code != 200:
        return
    data = r.json()
    rid = data.get("report_id") or data.get("data", {}).get("report_id")
    url = data.get("download_url") or f"/api/v1/baby/reports/download/{rid}"

    # HEAD
    rh = client.head(url, headers=h)
    print("safety_summary HEAD_status", rh.status_code)
    for k in ["Content-Type","Content-Disposition","Cache-Control","Content-Length"]:
        if k in rh.headers: print("safety_summary", k+":", rh.headers[k])

    # GET
    rg = client.get(url, headers=h)
    print("safety_summary GET_status", rg.status_code)
    for k in ["Content-Type","Content-Disposition","Cache-Control","Content-Length"]:
        if k in rg.headers: print("safety_summary", k+":", rg.headers[k])

if __name__ == "__main__":
    run()
