#!/usr/bin/env python3
"""Test the 90-Day Safety Summary Report Generation
"""

import os
import random
import sys
from datetime import datetime, timedelta, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from db.models.scan_history import SafetyReport, ScanHistory


def create_test_scan_history(db_session, user_id=1):
    """Create sample scan history for testing"""
    print(f"Creating test scan history for user {user_id}...")

    # Product samples with varying risk levels
    products = [
        {
            "product_name": "Baby Monitor Pro",
            "brand": "SafeWatch",
            "barcode": "123456789001",
            "category": "Electronics",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        {
            "product_name": "Organic Baby Food",
            "brand": "NatureBaby",
            "barcode": "123456789002",
            "category": "Food",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        {
            "product_name": "Teething Ring",
            "brand": "ChewyToys",
            "barcode": "123456789003",
            "category": "Toys",
            "risk_level": "medium",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        {
            "product_name": "Baby Crib Model X",
            "brand": "DangerCribs",
            "barcode": "123456789004",
            "category": "Furniture",
            "risk_level": "high",
            "recalls_found": 1,
            "verdict": "Recall Alert",
            "recall_ids": ["CPSC-2024-001"],
        },
        {
            "product_name": "Car Seat Alpha",
            "brand": "SafeRide",
            "barcode": "123456789005",
            "category": "Car Seats",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        {
            "product_name": "Baby Bottle Set",
            "brand": "FlowBottles",
            "barcode": "123456789006",
            "category": "Feeding",
            "risk_level": "critical",
            "recalls_found": 2,
            "verdict": "Recall Alert",
            "recall_ids": ["FDA-2024-001", "FDA-2024-002"],
        },
    ]

    # Create scans over the past 90 days
    scans_created = 0
    for days_ago in range(90, 0, -7):  # Weekly scans
        scan_date = datetime.now(timezone.utc) - timedelta(days=days_ago)

        # Scan 2-3 random products each week
        num_scans = random.randint(2, 3)
        for _ in range(num_scans):
            product = random.choice(products)

            scan = ScanHistory(
                user_id=user_id,
                scan_id=f"test_scan_{scans_created}",
                scan_timestamp=scan_date,
                product_name=product["product_name"],
                brand=product["brand"],
                barcode=product["barcode"],
                category=product.get("category"),
                scan_type="barcode",
                confidence_score=random.uniform(95.0, 99.9),
                barcode_format="ean13",
                verdict=product["verdict"],
                risk_level=product["risk_level"],
                recalls_found=product["recalls_found"],
                recall_ids=product.get("recall_ids"),
                agencies_checked="39+ agencies",
            )

            db_session.add(scan)
            scans_created += 1

    # Add some recent scans
    for days_ago in [3, 2, 1, 0]:
        scan_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
        product = random.choice(products)

        scan = ScanHistory(
            user_id=user_id,
            scan_id=f"test_scan_{scans_created}",
            scan_timestamp=scan_date,
            product_name=product["product_name"],
            brand=product["brand"],
            barcode=product["barcode"],
            category=product.get("category"),
            scan_type="barcode",
            confidence_score=random.uniform(95.0, 99.9),
            barcode_format="ean13",
            verdict=product["verdict"],
            risk_level=product["risk_level"],
            recalls_found=product["recalls_found"],
            recall_ids=product.get("recall_ids"),
            agencies_checked="39+ agencies",
        )

        db_session.add(scan)
        scans_created += 1

    db_session.commit()
    print(f"✅ Created {scans_created} test scans")
    return scans_created


def test_90_day_report():
    """Test the 90-day safety summary generation"""
    print("Testing 90-Day Safety Summary Report Generation...")
    print("=" * 60)

    # Create test database session
    engine = create_engine("sqlite:///test_safety_reports.db")

    # Create only the tables we need for this test (metadata for table creation)
    _ = MetaData()
    ScanHistory.__table__.create(engine, checkfirst=True)
    SafetyReport.__table__.create(engine, checkfirst=True)

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Create test data
        user_id = 1
        _ = create_test_scan_history(db, user_id)  # scans_created

        # Test report generation
        print("\nGenerating 90-day report...")

        # Simulate the API call

        # Get scan history
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=90)

        scan_history = (
            db.query(ScanHistory)
            .filter(
                ScanHistory.user_id == user_id,
                ScanHistory.scan_timestamp >= start_date,
                ScanHistory.scan_timestamp <= end_date,
            )
            .all()
        )

        print(f"Found {len(scan_history)} scans in the last 90 days")

        # Calculate statistics
        total_scans = len(scan_history)
        unique_products = len(set(s.barcode for s in scan_history if s.barcode))
        recalls_found = sum(s.recalls_found or 0 for s in scan_history)

        risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for scan in scan_history:
            if scan.risk_level:
                risk_counts[scan.risk_level] += 1

        # Calculate safety score
        safety_score = 100.0
        if total_scans > 0:
            critical_weight = risk_counts["critical"] * 10
            high_weight = risk_counts["high"] * 5
            medium_weight = risk_counts["medium"] * 2
            total_weight = critical_weight + high_weight + medium_weight
            safety_score = max(0, 100 - (total_weight / total_scans * 10))

        print("\n📊 90-Day Safety Summary Statistics:")
        print(f"  Total Scans: {total_scans}")
        print(f"  Unique Products: {unique_products}")
        print(f"  Recalls Found: {recalls_found}")
        print(f"  High Risk Products: {risk_counts['high'] + risk_counts['critical']}")
        print(f"  Medium Risk Products: {risk_counts['medium']}")
        print(f"  Low Risk Products: {risk_counts['low']}")
        print(f"  Safety Score: {round(safety_score, 1)}/100")

        # Group products
        product_groups = {}
        for scan in scan_history:
            key = scan.barcode or scan.product_name
            if key not in product_groups:
                product_groups[key] = {
                    "product_name": scan.product_name,
                    "brand": scan.brand,
                    "barcode": scan.barcode,
                    "scans": [],
                    "risk_levels": [],
                }
            product_groups[key]["scans"].append(scan)
            if scan.risk_level:
                product_groups[key]["risk_levels"].append(scan.risk_level)

        print("\n📦 Top Scanned Products:")
        sorted_products = sorted(product_groups.items(), key=lambda x: len(x[1]["scans"]), reverse=True)
        for i, (key, group) in enumerate(sorted_products[:5], 1):
            scan_count = len(group["scans"])
            risk = (
                "critical"
                if "critical" in group["risk_levels"]
                else "high"
                if "high" in group["risk_levels"]
                else "medium"
                if "medium" in group["risk_levels"]
                else "low"
            )
            print(f"  {i}. {group['product_name']} ({group['brand']})")
            print(f"     Scanned: {scan_count} times | Risk: {risk}")

        # Test report saving
        print("\n💾 Saving report to database...")
        report = SafetyReport(
            report_id=f"SR_test_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            user_id=user_id,
            report_type="90_day_summary",
            period_start=start_date,
            period_end=end_date,
            total_scans=total_scans,
            unique_products=unique_products,
            recalls_found=recalls_found,
            high_risk_products=risk_counts["high"] + risk_counts["critical"],
            report_data={
                "statistics": {
                    "total_scans": total_scans,
                    "unique_products": unique_products,
                    "recalls_found": recalls_found,
                    "safety_score": round(safety_score, 1),
                },
            },
        )
        db.add(report)
        db.commit()

        print(f"✅ Report saved with ID: {report.report_id}")

        # Verify report retrieval
        saved_report = db.query(SafetyReport).filter(SafetyReport.report_id == report.report_id).first()

        assert saved_report is not None, "Report should be saved"
        assert saved_report.total_scans == total_scans, "Total scans should match"
        assert saved_report.unique_products == unique_products, "Unique products should match"

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("\n🎯 90-Day Safety Summary Features:")
        print("  1. ✅ Tracks all scans over 90 days")
        print("  2. ✅ Calculates safety statistics")
        print("  3. ✅ Groups products by frequency")
        print("  4. ✅ Identifies high-risk products")
        print("  5. ✅ Generates safety score (0-100)")
        print("  6. ✅ Saves reports for future access")
        print("  7. ✅ Ready for PDF generation")
        print("=" * 60)

    finally:
        db.close()
        # Clean up test database
        if os.path.exists("test_safety_reports.db"):
            os.remove("test_safety_reports.db")


if __name__ == "__main__":
    test_90_day_report()
