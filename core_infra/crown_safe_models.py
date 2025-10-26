"""
Crown Safe Database Models
Hair product safety database for Black hair care (3C-4C)

Version: 1.0.0
Last Updated: October 24, 2025
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()
# ============================================================================
# USER & PROFILE MODELS
# ============================================================================


class HairProfileModel(Base):
    """User's hair profile for personalized product recommendations"""

    __tablename__ = "hair_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # Hair characteristics
    hair_type = Column(String(10), nullable=False)  # 3C, 4A, 4B, 4C, Mixed
    porosity = Column(String(10), nullable=False)  # Low, Medium, High

    # Current state (JSON array)
    hair_state = Column(JSON, default=[])  # ["Natural", "Relaxed", etc.]

    # Goals (JSON array)
    hair_goals = Column(JSON, default=[])  # ["Growth", "Moisture", "Edges", etc.]

    # Sensitivities (JSON array)
    sensitivities = Column(JSON, default=[])  # ["protein-sensitive", "coconut-sensitive"]

    # Additional preferences
    preferred_brands = Column(JSON, default=[])  # List of brand names
    avoided_ingredients = Column(JSON, default=[])  # User-defined ingredient blacklist

    # Climate context (affects humectant effectiveness)
    climate = Column(String(20), default="humid")  # humid, dry, mixed

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="hair_profile")
    scans = relationship("ProductScanModel", back_populates="hair_profile")


# ============================================================================
# PRODUCT MODELS
# ============================================================================


class HairProductModel(Base):
    """Hair product catalog (15,000+ products planned)"""

    __tablename__ = "hair_products"

    id = Column(Integer, primary_key=True, index=True)

    # Product identification
    product_id = Column(String(50), unique=True, nullable=False, index=True)
    barcode = Column(String(20), index=True)  # UPC/EAN

    # Basic info
    name = Column(String(255), nullable=False, index=True)
    brand = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # Shampoo, Conditioner, etc.
    product_type = Column(String(50), nullable=False)  # Leave-In, Deep Conditioner, etc.

    # Description
    description = Column(Text)
    size = Column(String(50))  # "8 oz", "250ml", etc.

    # Ingredients (ordered list)
    ingredients = Column(JSON, nullable=False)  # ["Water", "Shea Butter", ...]

    # Product metadata
    ph_level = Column(Float)  # Ideal: 4.5-5.5
    is_curly_girl_approved = Column(Boolean, default=False)
    is_sulfate_free = Column(Boolean, default=False)
    is_silicone_free = Column(Boolean, default=False)
    is_protein_free = Column(Boolean, default=False)
    is_paraben_free = Column(Boolean, default=False)

    # Pricing & availability
    price = Column(Float)  # In USD
    currency = Column(String(3), default="USD")
    available_at = Column(JSON, default=[])  # ["Amazon", "Target", "Sally Beauty"]
    affiliate_links = Column(JSON, default={})  # {"amazon": "https://...", "target": "..."}

    # Crown Score (pre-calculated for popular products)
    # Personalized scores calculated on-demand based on user profile
    avg_crown_score = Column(Integer)  # Average score across all hair types

    # Images
    image_url = Column(String(500))
    thumbnail_url = Column(String(500))

    # Community data
    review_count = Column(Integer, default=0)
    avg_rating = Column(Float, default=0.0)  # 1.0-5.0 stars

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    scans = relationship("ProductScanModel", back_populates="product")
    reviews = relationship("ProductReviewModel", back_populates="product")


# ============================================================================
# INGREDIENT MODELS
# ============================================================================


class IngredientModel(Base):
    """Individual ingredient database (200+ ingredients in MVP)"""

    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)

    # Ingredient identification
    ingredient_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False, unique=True, index=True)
    common_names = Column(JSON, default=[])  # Alternative names

    # Classification
    category = Column(String(50), nullable=False, index=True)  # Alcohol, Sulfate, Butter, etc.
    subcategory = Column(String(50))  # Drying Alcohol, Fatty Alcohol, etc.

    # Safety data
    base_score = Column(Integer, nullable=False)  # -50 to +20
    safety_level = Column(String(20), nullable=False)  # Safe, Caution, Avoid, Dangerous

    # Effects (JSON array)
    effects = Column(JSON, default=[])  # ["Moisturizing", "Drying", "Protein", etc.]

    # Hair type compatibility (JSON object)
    # {"Low": -5, "Medium": 0, "High": 10}
    porosity_adjustments = Column(JSON, default={})

    # {"4A": 5, "4B": 10, "4C": 10}
    curl_pattern_adjustments = Column(JSON, default={})

    # Scientific data
    inci_name = Column(String(200))  # International Nomenclature Cosmetic Ingredient
    cas_number = Column(String(20))  # Chemical Abstracts Service number
    function = Column(String(100))  # Surfactant, Emollient, Humectant, etc.

    # Regulatory info
    fda_status = Column(String(50))  # Approved, Restricted, Banned
    eu_status = Column(String(50))

    # Detailed description
    description = Column(Text)
    why_good = Column(Text)  # If beneficial
    why_bad = Column(Text)  # If harmful

    # Research references
    research_links = Column(JSON, default=[])  # Scientific papers, studies

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


# ============================================================================
# SCAN & ANALYSIS MODELS
# ============================================================================


class ProductScanModel(Base):
    """User's product scan history with Crown Score analysis"""

    __tablename__ = "product_scans"

    id = Column(Integer, primary_key=True, index=True)

    # Scan identification
    scan_id = Column(String(50), unique=True, nullable=False, index=True)

    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    hair_profile_id = Column(Integer, ForeignKey("hair_profiles.id"))
    product_id = Column(Integer, ForeignKey("hair_products.id"), index=True)

    # Scan input
    barcode = Column(String(20), index=True)
    scan_method = Column(String(20), default="barcode")  # barcode, image, manual

    # Product info (if not in database)
    product_name = Column(String(255))
    brand = Column(String(100))
    scanned_ingredients = Column(JSON)  # User-provided ingredient list

    # Crown Score analysis results
    crown_score = Column(Integer, nullable=False)  # 0-100
    verdict = Column(String(50), nullable=False)  # CROWN APPROVED, GOOD CHOICE, etc.

    # Breakdown (for transparency)
    score_breakdown = Column(JSON, nullable=False)  # Full ScoreBreakdown object
    red_flags = Column(JSON, default=[])  # Harmful ingredients found
    good_ingredients = Column(JSON, default=[])  # Beneficial ingredients found
    warnings = Column(JSON, default=[])  # Interaction warnings

    # Recommended alternatives (if score is low)
    alternatives = Column(JSON, default=[])  # [product_id_1, product_id_2, ...]

    # User actions
    is_favorite = Column(Boolean, default=False)
    is_in_routine = Column(Boolean, default=False)  # Part of current hair routine

    # Metadata
    scanned_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    hair_profile = relationship("HairProfileModel", back_populates="scans")
    product = relationship("HairProductModel", back_populates="scans")


# ============================================================================
# COMMUNITY FEATURES
# ============================================================================


class ProductReviewModel(Base):
    """Community product reviews"""

    __tablename__ = "product_reviews"

    id = Column(Integer, primary_key=True, index=True)

    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("hair_products.id"), nullable=False, index=True)

    # Review data
    rating = Column(Float, nullable=False)  # 1.0-5.0 stars
    review_text = Column(Text)

    # Hair profile context (what worked for them)
    hair_type = Column(String(10))  # Their hair type when reviewing
    porosity = Column(String(10))

    # Results
    would_recommend = Column(Boolean, default=True)
    achieved_goals = Column(JSON, default=[])  # Which goals the product helped with

    # Images (optional)
    before_image_url = Column(String(500))
    after_image_url = Column(String(500))

    # Community engagement
    helpful_count = Column(Integer, default=0)
    verified_purchase = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    product = relationship("HairProductModel", back_populates="reviews")


# ============================================================================
# BRAND PARTNERSHIP MODELS (Revenue Stream #3)
# ============================================================================


class BrandCertificationModel(Base):
    """Crown Safe Certified brands (revenue model)"""

    __tablename__ = "brand_certifications"

    id = Column(Integer, primary_key=True, index=True)

    # Brand info
    brand_name = Column(String(100), unique=True, nullable=False, index=True)
    brand_logo_url = Column(String(500))
    brand_website = Column(String(500))

    # Certification status
    is_certified = Column(Boolean, default=False)
    certification_level = Column(String(20))  # Gold, Silver, Bronze

    # Certification details
    certified_products = Column(JSON, default=[])  # List of product_ids
    certification_date = Column(DateTime)
    expiry_date = Column(DateTime)

    # Business
    certification_fee_paid = Column(Float, default=10000.00)  # $10K initial
    annual_renewal_fee = Column(Float, default=2000.00)  # $2K/year

    # Benefits
    featured_in_app = Column(Boolean, default=True)
    badge_enabled = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


# ============================================================================
# SALON B2B MODELS (Revenue Stream #4)
# ============================================================================


class SalonAccountModel(Base):
    """Professional salon accounts ($49/month)"""

    __tablename__ = "salon_accounts"

    id = Column(Integer, primary_key=True, index=True)

    # Salon info
    salon_name = Column(String(200), nullable=False)
    owner_name = Column(String(200))
    email = Column(String(200), unique=True, nullable=False)
    phone = Column(String(20))

    # Location
    address = Column(String(500))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(10))
    country = Column(String(50), default="USA")

    # Subscription
    subscription_tier = Column(String(20), default="professional")  # Professional, Enterprise
    monthly_fee = Column(Float, default=49.00)
    is_active_subscription = Column(Boolean, default=True)

    # Features enabled
    client_profiles_count = Column(Integer, default=0)  # How many clients they manage
    inventory_tracking_enabled = Column(Boolean, default=True)
    custom_formulation_notes = Column(Boolean, default=True)

    # Business metrics
    total_scans = Column(Integer, default=0)
    total_clients = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    subscription_starts_at = Column(DateTime)
    subscription_ends_at = Column(DateTime)


# ============================================================================
# ANALYTICS & INSIGHTS MODELS (Revenue Stream #5)
# ============================================================================


class MarketInsightModel(Base):
    """Aggregated market data for brands ($50K+ per report)"""

    __tablename__ = "market_insights"

    id = Column(Integer, primary_key=True, index=True)

    # Insight data
    # trending_ingredients, consumer_preferences, competitive_analysis, etc.
    insight_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    summary = Column(Text)

    # Data (aggregated, no PII)
    data = Column(JSON, nullable=False)  # Charts, trends, statistics

    # Timeframe
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Access control (which brands purchased this report)
    purchased_by = Column(JSON, default=[])  # List of brand names
    price = Column(Float, default=50000.00)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def create_all_tables(engine):
    """Create all Crown Safe database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ All Crown Safe tables created successfully!")


def drop_all_tables(engine):
    """Drop all Crown Safe tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)
    print("⚠️ All Crown Safe tables dropped!")
