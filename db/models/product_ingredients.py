"""
Product Ingredients Database Model
Stores product ingredient data locally for immediate offline access
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Index, Integer, String, Text

from core_infra.database import Base


class ProductIngredient(Base):
    """Local database of product ingredients for immediate safety checks"""

    __tablename__ = "product_ingredients"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Product identification
    upc = Column(String(50), unique=True, nullable=False, index=True)
    product_name = Column(String(255), nullable=False, index=True)
    brand = Column(String(100), nullable=True, index=True)
    category = Column(String(100), nullable=True, index=True)

    # Ingredient data
    ingredients = Column(JSON, nullable=False)  # List of ingredient strings
    allergens = Column(JSON, nullable=True)  # List of known allergens
    nutritional_info = Column(JSON, nullable=True)  # Nutritional data

    # Safety flags
    pregnancy_safe = Column(Boolean, default=True, index=True)
    baby_safe = Column(Boolean, default=True, index=True)
    toddler_safe = Column(Boolean, default=True, index=True)

    # Metadata
    data_source = Column(String(100), nullable=True)  # Where data came from
    confidence_score = Column(Integer, default=100)  # Data quality score (0-100)
    last_updated = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes for performance
    __table_args__ = (
        Index("idx_product_safety", "pregnancy_safe", "baby_safe", "toddler_safe"),
        Index("idx_product_category_brand", "category", "brand"),
    )


class IngredientSafety(Base):
    """Database of ingredient safety information"""

    __tablename__ = "ingredient_safety"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Ingredient info
    ingredient_name = Column(String(200), unique=True, nullable=False, index=True)
    alternative_names = Column(JSON, nullable=True)  # List of alternative names

    # Safety information
    pregnancy_risk_level = Column(String(20), nullable=True, index=True)  # None, Low, Moderate, High
    pregnancy_risk_reason = Column(Text, nullable=True)
    pregnancy_source = Column(String(200), nullable=True)

    baby_risk_level = Column(String(20), nullable=True, index=True)
    baby_risk_reason = Column(Text, nullable=True)
    baby_source = Column(String(200), nullable=True)

    # Allergy information
    common_allergen = Column(Boolean, default=False, index=True)
    allergen_type = Column(String(50), nullable=True)  # dairy, nuts, gluten, etc.

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, index=True)
    data_source = Column(String(100), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_safety_levels", "pregnancy_risk_level", "baby_risk_level"),
        Index("idx_allergen_info", "common_allergen", "allergen_type"),
    )


class ProductNutrition(Base):
    """Nutritional information for products"""

    __tablename__ = "product_nutrition"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Link to product
    upc = Column(String(50), nullable=False, index=True)

    # Nutritional data (per 100g/100ml)
    calories = Column(Integer, nullable=True)
    protein_g = Column(Integer, nullable=True)
    carbs_g = Column(Integer, nullable=True)
    fat_g = Column(Integer, nullable=True)
    sugar_g = Column(Integer, nullable=True)
    sodium_mg = Column(Integer, nullable=True)
    fiber_g = Column(Integer, nullable=True)

    # Vitamins and minerals (as JSON for flexibility)
    vitamins = Column(JSON, nullable=True)
    minerals = Column(JSON, nullable=True)

    # Age appropriateness
    min_age_months = Column(Integer, nullable=True, index=True)
    max_age_months = Column(Integer, nullable=True, index=True)

    # Metadata
    serving_size = Column(String(50), nullable=True)
    data_source = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
