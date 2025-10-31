"""Check UK recalls schema and data in Azure PostgreSQL."""

import os
from urllib.parse import unquote

import psycopg2
from dotenv import load_dotenv

# Load Azure environment variables
load_dotenv(".env.azure")

# Get connection details
pg_host = os.getenv("AZURE_PG_HOST")
pg_user = os.getenv("AZURE_PG_USER")
pg_database = os.getenv("AZURE_PG_DATABASE")
pg_password_encoded = os.getenv("AZURE_PG_PASSWORD_ENCODED")
pg_password = unquote(pg_password_encoded) if pg_password_encoded else None

print("=" * 80)
print("AZURE POSTGRESQL - UK RECALLS ANALYSIS")
print("=" * 80)

conn_string = f"host={pg_host} dbname={pg_database} user={pg_user} password={pg_password} sslmode=require"

try:
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()

    print("✅ Connected successfully!\n")

    # Get column names
    print("=" * 80)
    print("RECALLS TABLE SCHEMA")
    print("=" * 80)

    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'recalls' 
        ORDER BY ordinal_position;
    """)

    columns = cursor.fetchall()
    print("\nAvailable columns:")
    for col_name, col_type in columns:
        print(f"  - {col_name} ({col_type})")

    # Check for UK data
    print("\n" + "=" * 80)
    print("UK RECALLS SEARCH")
    print("=" * 80)

    # Try different approaches to find UK data
    queries = [
        ("By country field", "SELECT COUNT(*) FROM recalls WHERE country = 'UK' OR country ILIKE '%United Kingdom%';"),
        (
            "By source_agency",
            "SELECT source_agency, COUNT(*) FROM recalls WHERE source_agency ILIKE '%UK%' GROUP BY source_agency ORDER BY COUNT(*) DESC LIMIT 10;",  # noqa: E501
        ),
        ("Total recalls", "SELECT COUNT(*) FROM recalls;"),
    ]

    for description, query in queries:
        try:
            print(f"\n{description}:")
            cursor.execute(query)
            results = cursor.fetchall()

            if "COUNT" in description or "Total" in description:
                count = results[0][0] if results else 0
                print(f"  Count: {count:,}")
            else:
                for row in results:
                    print(f"  - {row[0]}: {row[1]:,}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Get sample UK recalls
    print("\n" + "=" * 80)
    print("SAMPLE UK RECALLS (First 5)")
    print("=" * 80)

    cursor.execute("""
        SELECT id, source_agency, country, recall_date 
        FROM recalls 
        WHERE source_agency ILIKE '%UK%' OR country ILIKE '%UK%'
        LIMIT 5;
    """)

    samples = cursor.fetchall()
    for sample in samples:
        print(f"  ID: {sample[0]}, Agency: {sample[1]}, Country: {sample[2]}, Date: {sample[3]}")

    cursor.close()
    conn.close()

    print("\n✅ Analysis complete!")

except Exception as e:
    print(f"❌ Error: {e}")
