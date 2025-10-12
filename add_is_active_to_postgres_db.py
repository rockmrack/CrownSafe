"""
Add is_active column to users table in POSTGRES database
This script connects to the CORRECT database that production uses.
"""

import psycopg2
import sys

# Production database connection - POSTGRES database (not babyshield_db!)
DB_CONFIG = {
    "host": "babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com",
    "port": 5432,
    "database": "postgres",  # THIS IS THE KEY - app uses postgres, not babyshield_db!
    "user": "babyshield_user",
    "password": "MandarunLabadiena25!",
}


def main():
    print("🔗 Connecting to POSTGRES database...")
    print(f"   Host: {DB_CONFIG['host']}")
    print(f"   Database: {DB_CONFIG['database']}")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected successfully!\n")

        with conn.cursor() as cur:
            # Check current database
            cur.execute("SELECT current_database(), current_schema();")
            db_name, schema = cur.fetchone()
            print(f"📍 Current database: {db_name}")
            print(f"📍 Current schema: {schema}\n")

            # Check if is_active column exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND table_schema = 'public'
                AND column_name = 'is_active';
            """)
            exists = cur.fetchone()

            if exists:
                print("✅ is_active column already exists in users table!")
            else:
                print("➕ Adding is_active column to users table...")
                cur.execute("""
                    ALTER TABLE users 
                    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;
                """)
                conn.commit()
                print("✅ Column added successfully!\n")

            # Verify all columns
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND table_schema = 'public'
                ORDER BY ordinal_position;
            """)
            columns = cur.fetchall()

            print("📋 Current columns in users table:")
            for col in columns:
                indicator = "✅" if col[0] == "is_active" else "  "
                print(f"{indicator} {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")

            # Count records
            cur.execute("SELECT COUNT(*) FROM users;")
            count = cur.fetchone()[0]
            print(f"\n📊 Total users in table: {count}")

            print("\n🎉 Done! The is_active column is now available in production.")

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        if "conn" in locals():
            conn.close()
            print("🔌 Connection closed.")


if __name__ == "__main__":
    main()
