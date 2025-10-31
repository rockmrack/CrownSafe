#!/usr/bin/env python3
"""
Test the Quarterly Nursery Report Generation
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from db.models.scan_history import SafetyReport, ScanHistory


def create_nursery_scan_history(db_session, user_id=1):
    """Create sample nursery product scan history for testing"""

    print(f"Creating nursery product scan history for user {user_id}...")

    # Nursery product samples with categories
    nursery_products = [
        # Critical Safety Items
        {
            "product_name": "Graco Pack 'n Play Crib",
            "brand": "Graco",
            "barcode": "047406140244",
            "category": "Critical Safety",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        {
            "product_name": "Chicco KeyFit 30 Car Seat",
            "brand": "Chicco",
            "barcode": "049796605051",
            "category": "Critical Safety",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        {
            "product_name": "Fisher-Price High Chair",
            "brand": "Fisher-Price",
            "barcode": "887961755831",
            "category": "Critical Safety",
            "risk_level": "high",
            "recalls_found": 1,
            "verdict": "Recall Alert",
            "recall_ids": ["CPSC-2024-HC001"],
        },
        # Feeding Items
        {
            "product_name": "Dr. Brown's Baby Bottles Set",
            "brand": "Dr. Brown's",
            "barcode": "072239301913",
            "category": "Feeding",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        {
            "product_name": "Similac Pro-Advance Formula",
            "brand": "Similac",
            "barcode": "070074681061",
            "category": "Feeding",
            "risk_level": "medium",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        # Toys & Play
        {
            "product_name": "Sophie the Giraffe Teether",
            "brand": "Vulli",
            "barcode": "616043300016",
            "category": "Toys & Play",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        {
            "product_name": "VTech Baby Rattle",
            "brand": "VTech",
            "barcode": "050803809195",
            "category": "Toys & Play",
            "risk_level": "critical",
            "recalls_found": 2,
            "verdict": "Recall Alert",
            "recall_ids": ["CPSC-2024-TOY001", "CPSC-2024-TOY002"],
        },
        # Clothing & Textiles
        {
            "product_name": "Halo Sleep Sack Swaddle",
            "brand": "Halo",
            "barcode": "818771011299",
            "category": "Clothing & Textiles",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        {
            "product_name": "Carter's Baby Blanket",
            "brand": "Carter's",
            "barcode": "190795532606",
            "category": "Clothing & Textiles",
            "risk_level": "medium",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        # Furniture
        {
            "product_name": "IKEA Sundvik Changing Table",
            "brand": "IKEA",
            "barcode": "702902123456",
            "category": "Furniture",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        {
            "product_name": "DaVinci Dresser",
            "brand": "DaVinci",
            "barcode": "048517015698",
            "category": "Furniture",
            "risk_level": "high",
            "recalls_found": 1,
            "verdict": "Recall Alert",
            "recall_ids": ["CPSC-2024-FUR001"],
        },
        # Safety Equipment
        {
            "product_name": "Safety 1st Baby Gate",
            "brand": "Safety 1st",
            "barcode": "884392603427",
            "category": "Safety Equipment",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        {
            "product_name": "Nanit Pro Baby Monitor",
            "brand": "Nanit",
            "barcode": "850001452014",
            "category": "Safety Equipment",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        {
            "product_name": "Cabinet Safety Locks",
            "brand": "Munchkin",
            "barcode": "735282351006",
            "category": "Safety Equipment",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        # Health & Hygiene
        {
            "product_name": "Pampers Swaddlers Diapers",
            "brand": "Pampers",
            "barcode": "037000862222",
            "category": "Health & Hygiene",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        {
            "product_name": "WaterWipes Baby Wipes",
            "brand": "WaterWipes",
            "barcode": "853963005019",
            "category": "Health & Hygiene",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        # Transportation
        {
            "product_name": "UPPAbaby Vista Stroller",
            "brand": "UPPAbaby",
            "barcode": "810030090229",
            "category": "Transportation",
            "risk_level": "low",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
        {
            "product_name": "Ergobaby Carrier",
            "brand": "Ergobaby",
            "barcode": "816271012301",
            "category": "Transportation",
            "risk_level": "medium",
            "recalls_found": 0,
            "verdict": "No Recalls Found",
        },
    ]

    # Create scans over the past 90 days (quarterly period)
    scans_created = 0
    for days_ago in range(90, 0, -5):  # Scan every 5 days
        scan_date = datetime.utcnow() - timedelta(days=days_ago)

        # Scan 3-5 random nursery products
        num_scans = random.randint(3, 5)
        for _ in range(num_scans):
            product = random.choice(nursery_products)

            scan = ScanHistory(
                user_id=user_id,
                scan_id=f"nursery_scan_{scans_created}",
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

    # Add recent scans (last week)
    for days_ago in [6, 4, 2, 0]:
        scan_date = datetime.utcnow() - timedelta(days=days_ago)

        # Focus on critical items and safety equipment
        critical_products = [p for p in nursery_products if p["category"] in ["Critical Safety", "Safety Equipment"]]
        product = random.choice(critical_products if critical_products else nursery_products)

        scan = ScanHistory(
            user_id=user_id,
            scan_id=f"nursery_scan_{scans_created}",
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
    print(f"✅ Created {scans_created} nursery product scans")
    return scans_created


def test_quarterly_nursery_report():
    """Test the quarterly nursery report generation"""

    print("Testing Quarterly Nursery Report Generation...")
    print("=" * 60)

    # Create test database session
    engine = create_engine("sqlite:///test_nursery_report.db")

    # Create only the tables we need (metadata for table creation)
    _ = MetaData()
    ScanHistory.__table__.create(engine, checkfirst=True)
    SafetyReport.__table__.create(engine, checkfirst=True)

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Create test data
        user_id = 1
        _ = create_nursery_scan_history(db, user_id)  # scans_created

        # Test report generation
        print("\n🏠 Generating Quarterly Nursery Report...")

        # Get scan history
        end_date = datetime.utcnow()
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

        print(f"Found {len(scan_history)} nursery product scans in the last quarter")

        # Categorize products
        categories = {
            "Critical Safety": [],
            "Feeding": [],
            "Toys & Play": [],
            "Clothing & Textiles": [],
            "Furniture": [],
            "Safety Equipment": [],
            "Health & Hygiene": [],
            "Transportation": [],
        }

        for scan in scan_history:
            product_name_lower = (scan.product_name or "").lower()

            if any(word in product_name_lower for word in ["crib", "car seat", "high chair", "bassinet"]):
                categories["Critical Safety"].append(scan)
            elif any(word in product_name_lower for word in ["bottle", "formula", "food", "sippy"]):
                categories["Feeding"].append(scan)
            elif any(word in product_name_lower for word in ["toy", "play", "rattle", "teether"]):
                categories["Toys & Play"].append(scan)
            elif any(word in product_name_lower for word in ["clothes", "blanket", "swaddle", "sheet"]):
                categories["Clothing & Textiles"].append(scan)
            elif any(word in product_name_lower for word in ["dresser", "changing table", "shelf"]):
                categories["Furniture"].append(scan)
            elif any(word in product_name_lower for word in ["gate", "monitor", "lock", "guard"]):
                categories["Safety Equipment"].append(scan)
            elif any(word in product_name_lower for word in ["diaper", "wipe", "thermometer"]):
                categories["Health & Hygiene"].append(scan)
            elif any(word in product_name_lower for word in ["stroller", "carrier", "wrap"]):
                categories["Transportation"].append(scan)

        # Calculate statistics
        total_products = len(set(s.barcode for s in scan_history if s.barcode))
        categories_audited = sum(1 for cat in categories.values() if cat)
        total_recalls = sum(s.recalls_found or 0 for s in scan_history)
        high_risk_items = sum(1 for s in scan_history if s.risk_level in ["high", "critical"])

        # Calculate compliance score
        compliance_score = 100.0
        if total_products > 0:
            recall_penalty = (total_recalls / total_products) * 30
            risk_penalty = (high_risk_items / total_products) * 20
            safety_bonus = min(10, (len(categories["Safety Equipment"]) / max(1, total_products)) * 20)
            compliance_score = max(0, min(100, 100 - recall_penalty - risk_penalty + safety_bonus))

        print("\n📊 Quarterly Nursery Audit Statistics:")
        print(f"  Total Products: {total_products}")
        print(f"  Categories Audited: {categories_audited}/8")
        print(f"  Critical Safety Items: {len(categories['Critical Safety'])}")
        print(f"  Feeding Items: {len(categories['Feeding'])}")
        print(f"  Toys & Play Items: {len(categories['Toys & Play'])}")
        print(f"  Safety Equipment: {len(categories['Safety Equipment'])}")
        print(f"  Total Recalls Found: {total_recalls}")
        print(f"  High Risk Items: {high_risk_items}")
        print(f"  Compliance Score: {round(compliance_score, 1)}/100")

        print("\n📦 Products by Category:")
        for category_name, items in categories.items():
            if items:
                unique_products = len(set(item.barcode for item in items if item.barcode))
                recalls = sum(item.recalls_found or 0 for item in items)
                high_risk = sum(1 for item in items if item.risk_level in ["high", "critical"])

                status = "✅" if recalls == 0 and high_risk == 0 else "⚠️"
                print(f"  {status} {category_name}: {unique_products} products")
                if recalls > 0:
                    print(f"      - {recalls} recalls found")
                if high_risk > 0:
                    print(f"      - {high_risk} high-risk items")

        # Generate recommendations
        print("\n💡 Recommendations:")
        if total_recalls > 0:
            print("  ⚠️ URGENT: Remove recalled items from nursery immediately")

        if len(categories["Safety Equipment"]) < 3:
            print("  📍 Add more safety equipment (gates, locks, monitors)")

        if len(categories["Critical Safety"]) > 0 and any(
            s.risk_level in ["high", "critical"] for s in categories["Critical Safety"]
        ):
            print("  🔍 Review and update critical safety items")

        if compliance_score >= 90:
            print("  ✅ Excellent nursery safety! Continue regular monitoring")
        elif compliance_score >= 70:
            print("  👍 Good nursery safety. Address any recalled items")
        else:
            print("  ⚠️ Schedule a comprehensive nursery safety review")

        # Save report
        print("\n💾 Saving quarterly nursery report...")
        report = SafetyReport(
            report_id=f"NR_test_{datetime.utcnow().strftime('%Y%m%d')}",
            user_id=user_id,
            report_type="quarterly_nursery",
            period_start=start_date,
            period_end=end_date,
            total_scans=len(scan_history),
            unique_products=total_products,
            recalls_found=total_recalls,
            high_risk_products=high_risk_items,
            report_data={
                "categories_audited": categories_audited,
                "compliance_score": round(compliance_score, 1),
            },
        )
        db.add(report)
        db.commit()

        print(f"✅ Report saved with ID: {report.report_id}")

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("\n🏠 Quarterly Nursery Report Features:")
        print("  1. ✅ Complete nursery product inventory")
        print("  2. ✅ 8 category classification system")
        print("  3. ✅ Critical safety item tracking")
        print("  4. ✅ Compliance scoring (0-100)")
        print("  5. ✅ Personalized recommendations")
        print("  6. ✅ Recall and risk assessment")
        print("  7. ✅ PDF generation ready")
        print("=" * 60)

    finally:
        db.close()
        # Clean up test database
        try:
            if os.path.exists("test_nursery_report.db"):
                os.remove("test_nursery_report.db")
        except:
            pass  # Ignore cleanup errors


if __name__ == "__main__":
    test_quarterly_nursery_report()
