"""Check UK recalls in Azure PostgreSQL and analyze agency distribution."""

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

# URL decode the password
pg_password = unquote(pg_password_encoded) if pg_password_encoded else None

print("=" * 80)
print("CONNECTING TO AZURE POSTGRESQL")
print("=" * 80)
print(f"Host: {pg_host}")
print(f"Database: {pg_database}")
print(f"User: {pg_user}")
print()

# Construct connection string
conn_string = f"host={pg_host} dbname={pg_database} user={pg_user} password={pg_password} sslmode=require"

try:
    # Connect to Azure PostgreSQL
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()

    print("✅ Connected to Azure PostgreSQL successfully!")
    print()

    # Query to analyze UK recalls by agency
    query = """
    SELECT
        CASE
            WHEN source_url ILIKE '%gov.uk/product-safety%'
                OR source_agency ILIKE '%OPSS%' THEN 'UK_OPSS'
            WHEN source_url ILIKE '%food.gov.uk%'
                OR source_agency ILIKE '%FSA%' THEN 'UK_FSA'
            WHEN source_url ILIKE '%tradingstandards.uk%'
                THEN 'UK_TRADING_STANDARDS'
            WHEN source_url ILIKE '%check-vehicle-recalls.service.gov.uk%'
                OR source_url ILIKE '%vehicle-recalls%' THEN 'UK_DVSA'
            WHEN source_url ILIKE '%drug-device-alerts%'
                OR source_agency ILIKE '%MHRA%' THEN 'UK_MHRA'
            ELSE 'UNKNOWN'
        END AS agency,
        COUNT(*) AS items
    FROM recalls
    WHERE (
        country = 'UK'
        OR source_url ILIKE '%gov.uk%'
        OR source_url ILIKE '%food.gov.uk%'
        OR source_url ILIKE '%tradingstandards.uk%'
        OR source_url ILIKE '%check-vehicle-recalls.service.gov.uk%'
    )
    GROUP BY 1
    ORDER BY items DESC;
    """

    print("=" * 80)
    print("UK RECALLS BY AGENCY")
    print("=" * 80)

    cursor.execute(query)
    results = cursor.fetchall()

    if results:
        total_uk_recalls = sum(row[1] for row in results)
        print(f"\n📊 Total UK Recalls: {total_uk_recalls:,}")
        print("\nBreakdown by Agency:")
        print("-" * 60)

        for agency, count in results:
            percentage = (count / total_uk_recalls) * 100 if total_uk_recalls > 0 else 0
            status = "✅" if agency != "UNKNOWN" else "❓"
            print(f"{status} {agency:25} {count:>8,} ({percentage:>5.1f}%)")

        print("\n" + "=" * 80)

        # Additional analysis - get sample URLs
        print("\nSAMPLE SOURCE URLs BY AGENCY:")
        print("=" * 80)

        sample_query = """
        WITH classified AS (
            SELECT DISTINCT
                source_url,
                CASE
                    WHEN source_url ILIKE '%gov.uk/product-safety%'
                        OR source_agency ILIKE '%OPSS%' THEN 'UK_OPSS'
                    WHEN source_url ILIKE '%food.gov.uk%'
                        OR source_agency ILIKE '%FSA%' THEN 'UK_FSA'
                    WHEN source_url ILIKE '%tradingstandards.uk%'
                        THEN 'UK_TRADING_STANDARDS'
                    WHEN source_url ILIKE '%check-vehicle-recalls.service.gov.uk%'
                        OR source_url ILIKE '%vehicle-recalls%'
                        THEN 'UK_DVSA'
                    WHEN source_url ILIKE '%drug-device-alerts%'
                        OR source_agency ILIKE '%MHRA%' THEN 'UK_MHRA'
                    ELSE 'UNKNOWN'
                END AS agency
            FROM recalls
            WHERE (
                country = 'UK'
                OR source_url ILIKE '%gov.uk%'
                OR source_url ILIKE '%food.gov.uk%'
            )
        )
        SELECT source_url
        FROM classified
        WHERE agency = %s
        LIMIT 3;
        """

        for agency, _ in results[:5]:  # Top 5 agencies
            cursor.execute(sample_query, (agency,))
            samples = cursor.fetchall()

            print(f"\n{agency}:")
            for sample in samples:
                print(f"  - {sample[0]}")
    else:
        print("❌ No UK recalls found in database")

    # Check total recalls in database
    print("\n" + "=" * 80)
    print("DATABASE STATISTICS")
    print("=" * 80)

    cursor.execute("SELECT COUNT(*) FROM recalls;")
    total_row = cursor.fetchone()
    total = total_row[0] if total_row else 0
    print(f"Total recalls in database: {total:,}")

    cursor.execute("SELECT COUNT(DISTINCT source_agency) FROM recalls WHERE source_agency IS NOT NULL;")
    agencies_row = cursor.fetchone()
    agencies = agencies_row[0] if agencies_row else 0
    print(f"Unique source agencies: {agencies}")

    cursor.close()
    conn.close()

    print("\n✅ Analysis complete!")

except psycopg2.Error as e:
    print(f"❌ Database error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
