#!/usr/bin/env python3
"""
Create a test scan record for chat agent testing
"""

import os
import sys
from datetime import datetime
from uuid import uuid4

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from core_infra.database import get_db_session
from db.models.scan_history import ScanHistory

def create_test_scan():
    """Create a test scan record for chat testing"""
    
    print("🔧 Creating test scan record...")
    
    with get_db_session() as db:
        # Check if test scan already exists
        existing = db.query(ScanHistory).filter(ScanHistory.scan_id == "test_scan_123").first()
        if existing:
            print("✅ Test scan 'test_scan_123' already exists!")
            print_scan_info(existing)
            return
        
        # Create new test scan
        test_scan = ScanHistory(
            scan_id="test_scan_123",
            user_id=None,  # Anonymous test
            product_name="Test Baby Formula",
            brand="SafeBaby",
            barcode="012345678901",
            upc_gtin="012345678901",
            model_number="SB-FORM-001",
            category="baby_formula",
            scan_type="barcode",
            scan_timestamp=datetime.now(),
            confidence_score=0.95,
            barcode_format="UPC-A",
            
            # Safety results
            verdict="Safe - No Recalls Found",
            risk_level="low", 
            recalls_found=0,
            recall_ids=[],
            agencies_checked="39 agencies (FDA, CPSC, USDA, etc.)",
            
            # Safety alerts
            allergen_alerts=["Contains milk", "May contain soy"],
            pregnancy_warnings=[],
            age_warnings=["Suitable for infants 0-12 months"],
            
            # Metadata
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(test_scan)
        db.commit()
        db.refresh(test_scan)
        
        print("✅ Test scan created successfully!")
        print_scan_info(test_scan)

def print_scan_info(scan):
    """Print scan information"""
    print(f"   📋 Scan ID: {scan.scan_id}")
    print(f"   🏷️  Product: {scan.product_name}")
    print(f"   🏪 Brand: {scan.brand}")
    print(f"   📊 Barcode: {scan.barcode}")
    print(f"   🔒 Safety: {scan.verdict}")
    print(f"   ⚠️  Alerts: {len(scan.allergen_alerts or [])} allergen(s)")

def list_existing_scans():
    """List some existing scans for reference"""
    print("\n🔍 Existing scans in database:")
    
    with get_db_session() as db:
        scans = db.query(ScanHistory).limit(5).all()
        if not scans:
            print("   No scans found in database")
            return
            
        for scan in scans:
            print(f"   📋 {scan.scan_id} - {scan.product_name or 'Unknown'}")

if __name__ == "__main__":
    try:
        create_test_scan()
        list_existing_scans()
        
        print("\n🧪 Now you can test the chat agent with:")
        print('   $Body = @{ scan_id="test_scan_123"; user_query="Is this safe for my baby?" } | ConvertTo-Json')
        print('   Invoke-RestMethod "$BASE/api/v1/chat/conversation" -Method Post -Headers @{"Content-Type"="application/json"} -Body $Body')
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
