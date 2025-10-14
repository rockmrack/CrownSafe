from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    try:
        conn.execute(
            text("ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR UNIQUE;")
        )
        print("stripe_customer_id column added successfully.")
    except Exception as e:
        print("Could not add column (maybe it already exists):", e)
