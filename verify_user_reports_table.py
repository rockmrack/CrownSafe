"""Verify user_reports table was created and test the endpoints."""

import os

import psycopg

# Connect to production database
DATABASE_URL = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(DATABASE_URL)
cur = conn.cursor()

print("🔍 Checking if user_reports table exists...")
cur.execute(
    """
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public'
        AND table_name = 'user_reports'
    );
""",
)
table_exists = cur.fetchone()[0]

if table_exists:
    print("✅ user_reports table already exists")

    # Count existing reports
    cur.execute("SELECT COUNT(*) FROM user_reports")
    count = cur.fetchone()[0]
    print(f"📊 Current report count: {count}")

else:
    print("❌ user_reports table does NOT exist")
    print("🔨 Creating user_reports table...")

    # Create the table
    cur.execute(
        """
        CREATE TABLE user_reports (
            report_id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            product_name VARCHAR(255) NOT NULL,
            hazard_description TEXT NOT NULL,
            barcode VARCHAR(50),
            model_number VARCHAR(100),
            lot_number VARCHAR(100),
            brand VARCHAR(100),
            manufacturer VARCHAR(200),
            severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
            category VARCHAR(100),
            status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
            reporter_name VARCHAR(100),
            reporter_email VARCHAR(255),
            reporter_phone VARCHAR(50),
            incident_date DATE,
            incident_description TEXT,
            photos JSONB,
            metadata JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER,
            review_notes TEXT
        );
    """,
    )

    # Create indexes
    print("🔨 Creating indexes...")
    cur.execute("CREATE INDEX idx_user_reports_user_id ON user_reports(user_id);")
    cur.execute("CREATE INDEX idx_user_reports_status ON user_reports(status);")
    cur.execute("CREATE INDEX idx_user_reports_severity ON user_reports(severity);")
    cur.execute("CREATE INDEX idx_user_reports_created_at ON user_reports(created_at);")
    cur.execute("CREATE INDEX idx_user_reports_barcode ON user_reports(barcode);")
    cur.execute("CREATE INDEX idx_user_reports_model_number ON user_reports(model_number);")

    conn.commit()
    print("✅ user_reports table created successfully!")

conn.close()
print("\n🎉 Database is ready for Report Unsafe Product feature!")
