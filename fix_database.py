#!/usr/bin/env python3
"""
Quick database fix - adds missing columns to production database
"""

import os
from sqlalchemy import create_engine, text
import sys

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: Set DATABASE_URL environment variable first!")
    print("Example: set DATABASE_URL=postgresql://user:pass@host/dbname")
    sys.exit(1)

print(f"Connecting to database...")
print(f"URL: {DATABASE_URL[:30]}...")

try:
    # Connect to database
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Add missing columns
        print("\nAdding missing columns...")
        
        # Add severity column
        try:
            conn.execute(text("ALTER TABLE recalls_enhanced ADD COLUMN severity VARCHAR(50)"))
            print("✅ Added 'severity' column")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✓ 'severity' column already exists")
            else:
                print(f"⚠️ Error adding severity: {e}")
        
        # Add risk_category column
        try:
            conn.execute(text("ALTER TABLE recalls_enhanced ADD COLUMN risk_category VARCHAR(100)"))
            print("✅ Added 'risk_category' column")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✓ 'risk_category' column already exists")
            else:
                print(f"⚠️ Error adding risk_category: {e}")
        
        # Set default values
        print("\nSetting default values...")
        conn.execute(text("UPDATE recalls_enhanced SET severity = 'medium' WHERE severity IS NULL"))
        conn.execute(text("UPDATE recalls_enhanced SET risk_category = 'general' WHERE risk_category IS NULL"))
        conn.commit()
        print("✅ Default values set")
        
        # Verify columns exist
        result = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'recalls_enhanced' 
              AND column_name IN ('severity', 'risk_category')
        """))
        
        print("\n✅ Database schema fixed! Columns present:")
        for row in result:
            print(f"  - {row[0]}: {row[1]}")
        
        print("\n🎉 SUCCESS! Your search API should work now!")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTry running the SQL manually:")
    print("1. Connect to your database")
    print("2. Run the commands in fix_database_schema.sql")
    sys.exit(1)
