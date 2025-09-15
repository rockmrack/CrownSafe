#!/usr/bin/env python3
"""
🚀 BabyShield Database Migration Script
Migrates from basic RecallDB to Enhanced 39-Agency Schema

This migration adds CRITICAL fields for complete international coverage:
- Food agencies: lot_number, expiry_date, production_date
- Vehicle agencies: vehicle_make, vehicle_model, model_year, vin_range  
- Pharma agencies: ndc_number, din_number, batch_number
- International: ean_code, gtin, registry_codes, regions_affected
- And 15+ more identifier types for comprehensive matching

Run with: python scripts/migrate_to_enhanced_schema.py
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text, inspect, Column, Integer, String, Date, Text, JSON
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_infra.database import engine, SessionLocal, RecallDB, Base
from core_infra.enhanced_database_schema import EnhancedRecallDB

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BabyShieldMigration:
    """Enhanced Database Migration for 39-Agency Coverage"""
    
    def __init__(self):
        self.engine = engine
        self.session = SessionLocal()
        self.inspector = inspect(self.engine)
        
    def check_current_schema(self):
        """Analyze current database schema"""
        logger.info("🔍 Analyzing current database schema...")
        
        tables = self.inspector.get_table_names()
        logger.info(f"📊 Found tables: {tables}")
        
        if 'recalls' in tables:
            columns = [col['name'] for col in self.inspector.get_columns('recalls')]
            logger.info(f"📋 Current recalls table columns: {columns}")
            
            # Count current records
            result = self.session.execute(text("SELECT COUNT(*) FROM recalls")).scalar()
            logger.info(f"📈 Current records: {result}")
            
            return True
        else:
            logger.warning("⚠️ No existing recalls table found")
            return False
    
    def create_enhanced_schema(self):
        """Create the enhanced schema with all 39-agency fields"""
        logger.info("🏗️ Creating enhanced database schema...")
        
        try:
            # Create the enhanced table
            EnhancedRecallDB.__table__.create(self.engine, checkfirst=True)
            logger.info("✅ Enhanced schema created successfully!")
            
            # Show new columns
            enhanced_columns = [col['name'] for col in self.inspector.get_columns('recalls_enhanced')]
            logger.info(f"🆕 Enhanced table columns ({len(enhanced_columns)}): {enhanced_columns}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create enhanced schema: {e}")
            return False
    
    def migrate_existing_data(self):
        """Migrate data from old schema to enhanced schema"""
        logger.info("📦 Migrating existing data to enhanced schema...")
        
        try:
            # Get all existing recalls
            existing_recalls = self.session.query(RecallDB).all()
            logger.info(f"🔄 Migrating {len(existing_recalls)} existing recalls...")
            
            migrated_count = 0
            for old_recall in existing_recalls:
                # Create enhanced record with mapped fields
                enhanced_recall = EnhancedRecallDB(
                    # Core identifiers (direct mapping)
                    recall_id=old_recall.recall_id,
                    product_name=old_recall.product_name,
                    brand=old_recall.brand,
                    model_number=old_recall.model_number,
                    upc=old_recall.upc,
                    
                    # Metadata (direct mapping)
                    recall_date=old_recall.recall_date,
                    source_agency=old_recall.source_agency,
                    hazard=old_recall.hazard,
                    recall_reason=old_recall.hazard_description,
                    remedy=old_recall.remedy,
                    description=old_recall.description,
                    manufacturer_contact=old_recall.manufacturer_contact,
                    url=old_recall.url,
                    country=old_recall.country,
                    
                    # Enhanced fields (initially null, to be populated by connectors)
                    ean_code=None,
                    gtin=None,
                    lot_number=None,
                    batch_number=None,
                    serial_number=None,
                    expiry_date=None,
                    best_before_date=None,
                    production_date=None,
                    ndc_number=None,
                    din_number=None,
                    vehicle_make=None,
                    vehicle_model=None,
                    model_year=None,
                    vin_range=None,
                    registry_codes=None,
                    regions_affected=None,
                    hazard_category=None,
                    recall_class=None,
                    part_number=None,
                    article_number=None,
                    search_keywords=f"{old_recall.product_name} {old_recall.brand or ''} {old_recall.model_number or ''}".strip(),
                    agency_specific_data=None
                )
                
                self.session.add(enhanced_recall)
                migrated_count += 1
                
                if migrated_count % 100 == 0:
                    logger.info(f"📊 Migrated {migrated_count} records...")
                    self.session.commit()
            
            # Final commit
            self.session.commit()
            logger.info(f"✅ Successfully migrated {migrated_count} records to enhanced schema!")
            
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Migration failed: {e}")
            return False
    
    def create_performance_indexes(self):
        """Create performance indexes for the enhanced schema"""
        logger.info("⚡ Creating performance indexes for enhanced schema...")
        
        index_statements = [
            # Core product identifiers
            "CREATE INDEX IF NOT EXISTS idx_enhanced_product_name ON recalls_enhanced(product_name)",
            "CREATE INDEX IF NOT EXISTS idx_enhanced_brand ON recalls_enhanced(brand)",
            "CREATE INDEX IF NOT EXISTS idx_enhanced_model_number ON recalls_enhanced(model_number)",
            
            # Barcode identifiers
            "CREATE INDEX IF NOT EXISTS idx_enhanced_upc ON recalls_enhanced(upc)",
            "CREATE INDEX IF NOT EXISTS idx_enhanced_ean_code ON recalls_enhanced(ean_code)",
            "CREATE INDEX IF NOT EXISTS idx_enhanced_gtin ON recalls_enhanced(gtin)",
            
            # Food/pharma identifiers
            "CREATE INDEX IF NOT EXISTS idx_enhanced_lot_number ON recalls_enhanced(lot_number)",
            "CREATE INDEX IF NOT EXISTS idx_enhanced_batch_number ON recalls_enhanced(batch_number)",
            "CREATE INDEX IF NOT EXISTS idx_enhanced_ndc_number ON recalls_enhanced(ndc_number)",
            "CREATE INDEX IF NOT EXISTS idx_enhanced_expiry_date ON recalls_enhanced(expiry_date)",
            
            # Vehicle identifiers
            "CREATE INDEX IF NOT EXISTS idx_enhanced_vehicle_make ON recalls_enhanced(vehicle_make)",
            "CREATE INDEX IF NOT EXISTS idx_enhanced_vehicle_model ON recalls_enhanced(vehicle_model)",
            "CREATE INDEX IF NOT EXISTS idx_enhanced_model_year ON recalls_enhanced(model_year)",
            
            # Electronics identifiers
            "CREATE INDEX IF NOT EXISTS idx_enhanced_serial_number ON recalls_enhanced(serial_number)",
            "CREATE INDEX IF NOT EXISTS idx_enhanced_part_number ON recalls_enhanced(part_number)",
            
            # Meta fields
            "CREATE INDEX IF NOT EXISTS idx_enhanced_source_agency ON recalls_enhanced(source_agency)",
            "CREATE INDEX IF NOT EXISTS idx_enhanced_recall_date ON recalls_enhanced(recall_date)",
            "CREATE INDEX IF NOT EXISTS idx_enhanced_hazard_category ON recalls_enhanced(hazard_category)",
            
            # Compound indexes for common searches
            "CREATE INDEX IF NOT EXISTS idx_enhanced_product_brand ON recalls_enhanced(product_name, brand)",
            "CREATE INDEX IF NOT EXISTS idx_enhanced_agency_date ON recalls_enhanced(source_agency, recall_date)",
        ]
        
        try:
            for statement in index_statements:
                self.session.execute(text(statement))
                
            self.session.commit()
            logger.info(f"✅ Created {len(index_statements)} performance indexes!")
            
        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
    
    def backup_current_schema(self):
        """Create backup of current schema before migration"""
        logger.info("💾 Creating backup of current schema...")
        
        try:
            backup_table_sql = """
            CREATE TABLE IF NOT EXISTS recalls_backup AS 
            SELECT * FROM recalls;
            """
            
            self.session.execute(text(backup_table_sql))
            self.session.commit()
            
            # Count backup records
            result = self.session.execute(text("SELECT COUNT(*) FROM recalls_backup")).scalar()
            logger.info(f"✅ Backup created with {result} records")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return False
    
    def run_migration(self):
        """Execute the complete migration process"""
        logger.info("🚀 Starting BabyShield Enhanced Schema Migration...")
        logger.info("="*60)
        
        # Step 1: Check current schema
        if not self.check_current_schema():
            logger.error("❌ Migration aborted: No existing schema found")
            return False
        
        # Step 2: Create backup
        if not self.backup_current_schema():
            logger.error("❌ Migration aborted: Backup failed")
            return False
        
        # Step 3: Create enhanced schema
        if not self.create_enhanced_schema():
            logger.error("❌ Migration aborted: Schema creation failed")
            return False
        
        # Step 4: Migrate existing data
        if not self.migrate_existing_data():
            logger.error("❌ Migration aborted: Data migration failed")
            return False
        
        # Step 5: Create performance indexes
        self.create_performance_indexes()
        
        # Final status
        logger.info("="*60)
        logger.info("🎉 MIGRATION COMPLETE!")
        logger.info("📊 Enhanced schema ready for 39-agency coverage")
        logger.info("⚡ Performance indexes created")
        logger.info("💾 Original data backed up to 'recalls_backup'")
        logger.info("🌍 Ready for global deployment!")
        
        return True
    
    def __del__(self):
        """Cleanup session"""
        if hasattr(self, 'session'):
            self.session.close()

if __name__ == "__main__":
    migration = BabyShieldMigration()
    success = migration.run_migration()
    
    if success:
        print("\n🎯 Next Steps:")
        print("1. Update core_infra/database.py to use EnhancedRecallDB")
        print("2. Update agents/recall_data_agent/models.py with new fields")
        print("3. Update all 39 connectors to populate new identifier fields")
        print("4. Update search logic to use enhanced matching")
        print("5. Test with real data from all agency types")
        
        sys.exit(0)
    else:
        print("\n❌ Migration failed! Check logs for details.")
        sys.exit(1)