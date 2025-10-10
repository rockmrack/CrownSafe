import os
import uuid
import sqlite3
from fastapi.testclient import TestClient
from api.main_babyshield import app

os.environ.setdefault("DATABASE_URL", "sqlite:///./babyshield_test.db")
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("CREATE_TABLES_ON_IMPORT", "true")

c = TestClient(app)

# auth
email = f"test+{uuid.uuid4().hex[:6]}@ex.com"
pwd = "P@ssw0rd!"
r = c.post(
    "/api/v1/auth/register",
    json={"email": email, "password": pwd, "confirm_password": pwd},
)
print("register_status", r.status_code)
tok = c.post(
    "/api/v1/auth/token",
    data={"username": email, "password": pwd, "grant_type": "password"},
).json()["access_token"]
h = {"Authorization": f"Bearer {tok}"}
me = c.get("/api/v1/auth/me", headers=h).json()
uid = me.get("id") or me.get("data", {}).get("id")
print("me_user_id", uid)

# generate report
gen = c.post(
    "/api/v1/baby/reports/generate",
    headers=h,
    json={"report_type": "product_safety", "user_id": uid},
)
print("generate_status", gen.status_code)
print("generate_body", gen.text)
rid = gen.json().get("report_id") or gen.json().get("data", {}).get("report_id")

# check report_records
conn = sqlite3.connect("babyshield_test.db")
cur = conn.cursor()
cur.execute(
    "SELECT report_id,user_id,report_type,storage_path,created_at FROM report_records WHERE report_id = ?",
    (rid,),
)
row = cur.fetchone()
print("report_records_row", row)
conn.close()
