#!/usr/bin/env python3
"""
CI Database Initialization Script
Creates necessary tables for CI smoke tests
"""

import sqlite3
import os
from datetime import datetime

def init_ci_database():
    """Initialize database with required tables for CI smoke tests"""
    
    # Use the same database path as production
    db_path = os.environ.get('DATABASE_URL', 'sqlite:///./babyshield.db')
    if db_path.startswith('sqlite:///'):
        db_path = db_path.replace('sqlite:///', '')
    
    print(f"Initializing database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Create recalls_enhanced table (primary table used by search)
    c.execute("""
    CREATE TABLE IF NOT EXISTS recalls_enhanced (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recall_id TEXT,
        product_name TEXT,
        brand TEXT,
        manufacturer TEXT,
        model_number TEXT,
        upc TEXT,
        ean_code TEXT,
        gtin TEXT,
        article_number TEXT,
        lot_number TEXT,
        batch_number TEXT,
        serial_number TEXT,
        part_number TEXT,
        expiry_date TEXT,
        best_before_date TEXT,
        production_date TEXT,
        ndc_number TEXT,
        din_number TEXT,
        vehicle_make TEXT,
        vehicle_model TEXT,
        model_year TEXT,
        vin_range TEXT,
        registry_codes TEXT,
        country TEXT,
        regions_affected TEXT,
        recall_date TEXT,
        source_agency TEXT,
        hazard TEXT,
        hazard_category TEXT,
        recall_reason TEXT,
        remedy TEXT,
        recall_class TEXT,
        description TEXT,
        manufacturer_contact TEXT,
        url TEXT,
        search_keywords TEXT,
        agency_specific_data TEXT
    )
    """)
    
    # Create legacy recalls table (fallback)
    c.execute("""
    CREATE TABLE IF NOT EXISTS recalls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recall_id TEXT,
        product_name TEXT,
        brand TEXT,
        manufacturer TEXT,
        model_number TEXT,
        upc TEXT,
        country TEXT,
        recall_date TEXT,
        hazard_description TEXT,
        manufacturer_contact TEXT,
        source_agency TEXT,
        description TEXT,
        hazard TEXT,
        remedy TEXT,
        url TEXT
    )
    """)
    
    # Create users table (for authentication)
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create agencies table
    c.execute("""
    CREATE TABLE IF NOT EXISTS agencies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        country TEXT,
        website TEXT,
        api_endpoint TEXT,
        is_active BOOLEAN DEFAULT 1
    )
    """)
    
    # Insert test data for smoke tests
    # Check if recalls_enhanced has data
    count = c.execute("SELECT COUNT(*) FROM recalls_enhanced").fetchone()[0]
    if count == 0:
        c.execute("""
        INSERT INTO recalls_enhanced 
        (recall_id, product_name, brand, manufacturer, hazard, recall_date, source_agency, url, country, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "TEST-001", 
            "Baby Pacifier", 
            "SafeBaby", 
            "SafeBaby Corp", 
            "Choking hazard", 
            datetime.now().isoformat(), 
            "CPSC", 
            "https://example.com/recall/test", 
            "USA", 
            "Test recall for CI smoke tests"
        ))
        print("✅ Inserted test recall data")
    else:
        print("✅ recalls_enhanced table already has data")
    
    # Check if agencies has data
    count = c.execute("SELECT COUNT(*) FROM agencies").fetchone()[0]
    if count == 0:
        agencies = [
            ("FDA", "USA", "https://fda.gov", "https://api.fda.gov", 1),
            ("CPSC", "USA", "https://cpsc.gov", "https://api.cpsc.gov", 1),
            ("EU Safety Gate", "EU", "https://ec.europa.eu", "https://api.ec.europa.eu", 1),
        ]
        c.executemany("""
        INSERT INTO agencies (name, country, website, api_endpoint, is_active)
        VALUES (?, ?, ?, ?, ?)
        """, agencies)
        print("✅ Inserted test agency data")
    else:
        print("✅ agencies table already has data")
    
    conn.commit()
    conn.close()
    print("✅ Database initialization complete")

if __name__ == "__main__":
    init_ci_database()
