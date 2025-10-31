# core_infra/enhanced_database_schema.py
# Enhanced RecallDB Schema for Complete 39-Agency Coverage
# Addresses ALL GPT recommendations for comprehensive product identification

from sqlalchemy import Column, Date, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON

# Import Base from main database module to ensure all models share the same metadata
from core_infra.database import Base


class EnhancedRecallDB(Base):
    """🌍 COMPREHENSIVE 39-AGENCY RECALL SCHEMA
    Supports ALL identifier types used by international recall agencies
    """

    __tablename__ = "recalls_enhanced"

    # ================================
    # 🔑 PRIMARY IDENTIFIERS (Core)
    # ================================
    id = Column(Integer, primary_key=True, index=True)
    recall_id = Column(String, unique=True, index=True, nullable=False)

    # ================================
    # 📦 PRODUCT IDENTIFIERS (Universal)
    # ================================
    product_name = Column(String, index=True, nullable=False)  # ✅ Existing
    brand = Column(String, index=True, nullable=True)  # ✅ Existing
    manufacturer = Column(String, nullable=True)  # Enhanced from manufacturer_contact
    model_number = Column(String, index=True, nullable=True)  # ✅ Existing

    # ================================
    # 🏷️ RETAIL IDENTIFIERS (Global Barcodes)
    # ================================
    upc = Column(String, index=True, nullable=True)  # ✅ Existing (US/Canada)
    ean_code = Column(String, index=True, nullable=True)  # 🆕 European Article Number
    gtin = Column(String, index=True, nullable=True)  # 🆕 Global Trade Item Number
    article_number = Column(String, index=True, nullable=True)  # 🆕 Style/Article codes

    # ================================
    # 🔢 BATCH/LOT IDENTIFIERS (Food/Pharma Critical)
    # ================================
    lot_number = Column(String, index=True, nullable=True)  # 🆕 CRITICAL for food agencies
    batch_number = Column(String, index=True, nullable=True)  # 🆕 CRITICAL for pharma
    serial_number = Column(String, index=True, nullable=True)  # 🆕 Electronics/devices
    part_number = Column(String, index=True, nullable=True)  # 🆕 Vehicle parts/components

    # ================================
    # 📅 DATE IDENTIFIERS (Expiry/Production Critical)
    # ================================
    expiry_date = Column(Date, index=True, nullable=True)  # 🆕 CRITICAL for food/drugs
    best_before_date = Column(Date, index=True, nullable=True)  # 🆕 Food products
    production_date = Column(Date, index=True, nullable=True)  # 🆕 Manufacturing date

    # ================================
    # 💊 PHARMACEUTICAL IDENTIFIERS (FDA/Health Agencies)
    # ================================
    ndc_number = Column(String, index=True, nullable=True)  # 🆕 US National Drug Code
    din_number = Column(String, index=True, nullable=True)  # 🆕 Canada Drug Identification

    # ================================
    # 🚗 VEHICLE IDENTIFIERS (NHTSA/Transport Agencies)
    # ================================
    vehicle_make = Column(String, index=True, nullable=True)  # 🆕 Car manufacturer
    vehicle_model = Column(String, index=True, nullable=True)  # 🆕 Car model
    model_year = Column(String, index=True, nullable=True)  # 🆕 Manufacturing year
    vin_range = Column(String, nullable=True)  # 🆕 VIN number ranges

    # ================================
    # 🌎 REGIONAL REGISTRY CODES (Latin America/International)
    # ================================
    registry_codes = Column(JSON, nullable=True)  # 🆕 Registry numbers as JSON
    # Examples: {"rnpa": "12345", "rne": "67890", "anvisa": "ABC123"}

    # ================================
    # 📍 GEOGRAPHIC/DISTRIBUTION (Enhanced)
    # ================================
    country = Column(String, nullable=True)  # ✅ Existing
    regions_affected = Column(JSON, nullable=True)  # 🆕 Distribution regions as JSON
    # Examples: ["US-CA", "US-NY", "EU", "North America"]

    # ================================
    # ⚠️ RECALL METADATA (Enhanced)
    # ================================
    recall_date = Column(Date, index=True, nullable=False)  # ✅ Existing
    source_agency = Column(String, index=True, nullable=True)  # ✅ Existing
    hazard = Column(Text, nullable=True)  # ✅ Existing
    hazard_category = Column(String, index=True, nullable=True)  # 🆕 Structured hazard type
    # Examples: "choking", "fire", "chemical", "microbial", "allergen"

    severity = Column(String(50), nullable=True)  # 🆕 Severity level (low, medium, high, critical)
    risk_category = Column(String(100), nullable=True)  # 🆕 Risk category (general, food, vehicle, etc.)

    recall_reason = Column(Text, nullable=True)  # Enhanced from hazard_description
    remedy = Column(Text, nullable=True)  # ✅ Existing
    recall_class = Column(String, nullable=True)  # 🆕 Class I/II/III for FDA

    # ================================
    # 📄 DESCRIPTIVE FIELDS (Enhanced)
    # ================================
    description = Column(Text, nullable=True)  # ✅ Existing
    manufacturer_contact = Column(String, nullable=True)  # ✅ Existing
    url = Column(String, nullable=True)  # ✅ Existing

    # ================================
    # 🔍 SEARCH OPTIMIZATION (Performance)
    # ================================
    search_keywords = Column(Text, nullable=True)  # 🆕 Pre-computed search terms
    agency_specific_data = Column(JSON, nullable=True)  # 🆕 Raw agency data for fallback

    def to_dict(self) -> dict:
        """Convert to dictionary with proper handling of dates and JSON fields"""
        from datetime import date

        result = {}
        for c in self.__table__.columns:
            v = getattr(self, c.name)
            if isinstance(v, date):
                result[c.name] = v.isoformat() if v else None
            else:
                result[c.name] = v
        return result

    def __repr__(self) -> str:
        return f"<EnhancedRecallDB(id={self.id}, recall_id={self.recall_id!r}, product_name={self.product_name!r})>"


# ================================
# 📊 FIELD MAPPING FOR 39 AGENCIES
# ================================
AGENCY_FIELD_MAPPING = {
    # US Agencies
    "CPSC": ["product_name", "brand", "model_number", "upc", "serial_number"],
    "FDA": ["product_name", "brand", "lot_number", "ndc_number", "expiry_date"],
    "NHTSA": ["vehicle_make", "vehicle_model", "model_year", "vin_range"],
    "USDA_FSIS": ["product_name", "brand", "lot_number", "production_date"],
    # Canadian Agencies
    "Health_Canada": ["product_name", "brand", "model_number", "upc", "din_number"],
    "CFIA": ["product_name", "brand", "lot_number", "expiry_date"],
    "Transport_Canada": ["vehicle_make", "vehicle_model", "model_year"],
    # European Agencies
    "EU_RAPEX": ["product_name", "brand", "model_number", "ean_code", "gtin"],
    "UK_OPSS": ["product_name", "brand", "model_number", "ean_code"],
    "UK_FSA": ["product_name", "brand", "lot_number", "best_before_date"],
    # Latin American Agencies
    "ANMAT": ["product_name", "brand", "registry_codes", "lot_number"],
    "ANVISA": ["product_name", "brand", "registry_codes", "batch_number"],
    "SENACON": ["product_name", "brand", "model_number"],
    # And 26 more agencies...
}

# ================================
# 🎯 BENEFITS OF ENHANCED SCHEMA
# ================================
"""
✅ COMPLETE COVERAGE: All 39 agencies can store their specific identifiers
✅ FOOD SAFETY: Lot numbers, expiry dates for USDA FSIS, CFIA, ANVISA, etc.
✅ VEHICLE SAFETY: Make/model/year for NHTSA, Transport Canada car seats  
✅ PHARMACEUTICAL: NDC, DIN codes for FDA, Health Canada drugs
✅ INTERNATIONAL: Registry codes for Latin American agencies
✅ EUROPEAN: EAN/GTIN codes for EU agencies
✅ PERFORMANCE: Indexed fields for fast matching across all identifier types
✅ FLEXIBILITY: JSON fields for agency-specific data and regional distribution
"""
