"""
Check production database schema
"""

import psycopg2
import sys

# Production database connection
conn_string = "postgresql://babyshield_user:MandarunLabadiena25!@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/postgres"

try:
    print("Connecting to production database...")
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor()

    # 1. Check which tables exist
    print("\n=== CHECKING TABLES ===")
    cur.execute(
        """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema='public' 
        AND table_name IN ('recalls', 'recalls_enhanced')
        ORDER BY table_name
    """
    )
    tables = cur.fetchall()
    print(f"Found tables: {[t[0] for t in tables]}")

    # 2. Check recalls_enhanced columns
    if any(t[0] == "recalls_enhanced" for t in tables):
        print("\n=== RECALLS_ENHANCED COLUMNS ===")
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'recalls_enhanced'
            AND column_name IN ('source_agency', 'severity', 'risk_category', 'product_name', 'description')
            ORDER BY column_name
        """
        )
        columns = cur.fetchall()
        for col in columns:
            print(f"  {col[0]}: {col[1]} (nullable: {col[2]})")

    # 3. Check pg_trgm extension
    print("\n=== CHECKING EXTENSIONS ===")
    cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_trgm'")
    extensions = cur.fetchall()
    if extensions:
        print(f"  pg_trgm extension: INSTALLED (version {extensions[0][1]})")
    else:
        print("  pg_trgm extension: NOT INSTALLED ❌")

    # 4. Check agency values
    if any(t[0] == "recalls_enhanced" for t in tables):
        print("\n=== SAMPLE AGENCY VALUES ===")
        cur.execute(
            """
            SELECT DISTINCT source_agency 
            FROM recalls_enhanced 
            WHERE source_agency IS NOT NULL 
            LIMIT 10
        """
        )
        agencies = cur.fetchall()
        for agency in agencies:
            print(f"  - {agency[0]}")

    # 5. Test the failing query
    print("\n=== TESTING FAILING QUERY ===")
    try:
        cur.execute(
            """
            SELECT COUNT(*) 
            FROM recalls_enhanced 
            WHERE source_agency = ANY(ARRAY['FDA'])
            AND lower(product_name) LIKE %s
        """,
            ("%triacting night time cold%",),
        )
        count = cur.fetchone()[0]
        print(f"  Query executed successfully! Found {count} results.")
    except Exception as e:
        print(f"  Query FAILED: {e}")

    cur.close()
    conn.close()
    print("\n✅ Database check complete!")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    sys.exit(1)
