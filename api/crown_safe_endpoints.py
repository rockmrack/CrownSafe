#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/crown_safe_endpoints.py
# Crown Safe - Hair Product Safety Analysis Endpoints

"""
Crown Safe API Endpoints

This module provides hair product safety analysis using the Crown Score algorithm.
Replaces baby product recall checking with personalized hair ingredient analysis
for Black hair types (3C-4C).
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agents.ingredient_analysis_agent import IngredientAnalysisAgent
from core_infra.crown_safe_models import ProductScanModel
from core_infra.database import User, get_db_session, get_user_hair_profile

logger = logging.getLogger(__name__)


# ============================================
# Request/Response Models
# ============================================


class ProductAnalysisRequest(BaseModel):
    """Request model for hair product analysis"""

    user_id: int = Field(..., description="User ID for personalized analysis", example=1)
    product_name: str = Field(
        ..., description="Name of the hair product", example="Shea Moisture Curl Enhancing Smoothie"
    )
    ingredients: List[str] = Field(
        ...,
        description="List of ingredients in the product",
        example=["Water", "Butyrospermum Parkii (Shea Butter)", "Cocos Nucifera (Coconut Oil)", "Fragrance"],
    )
    brand: Optional[str] = Field(None, description="Brand name", example="Shea Moisture")
    category: Optional[str] = Field(None, description="Product category", example="styling_cream")
    upc_barcode: Optional[str] = Field(None, description="UPC barcode for product lookup", example="764302215004")


class ProductAnalysisResponse(BaseModel):
    """Response model for hair product analysis"""

    status: str = Field(..., description="Analysis status", example="COMPLETED")
    crown_score: int = Field(..., description="Crown Score (0-100)", example=85)
    verdict: str = Field(..., description="Safety verdict", example="SAFE")
    product_name: str = Field(..., description="Analyzed product name")
    breakdown: dict = Field(..., description="Detailed score breakdown")
    recommendations: str = Field(..., description="Personalized recommendations")
    alternatives: List[dict] = Field(default_factory=list, description="Alternative product suggestions")
    error: Optional[str] = Field(None, description="Error message if analysis failed")


class HairProfileRequest(BaseModel):
    """Request model for creating/updating hair profile"""

    user_id: int = Field(..., description="User ID", example=1)
    hair_type: str = Field(..., description="Hair curl pattern", example="4C")
    porosity: str = Field(..., description="Hair porosity level", example="High")
    hair_state: Optional[dict] = Field(
        None, description="Current hair state", example={"dryness": True, "breakage": False, "shedding": False}
    )
    hair_goals: Optional[dict] = Field(
        None,
        description="Hair care goals",
        example={"moisture_retention": True, "length_retention": True, "curl_definition": True},
    )
    sensitivities: Optional[dict] = Field(
        None, description="Known ingredient sensitivities", example={"fragrance": True, "sulfates": True}
    )


class HairProfileResponse(BaseModel):
    """Response model for hair profile"""

    status: str = Field(..., description="Operation status", example="COMPLETED")
    profile: dict = Field(..., description="Hair profile data")
    error: Optional[str] = Field(None, description="Error message if operation failed")


class ScanHistoryResponse(BaseModel):
    """Response model for scan history"""

    status: str = Field(..., description="Operation status", example="COMPLETED")
    scans: List[dict] = Field(..., description="List of previous product scans")
    total_scans: int = Field(..., description="Total number of scans")
    error: Optional[str] = Field(None, description="Error message if operation failed")


# ============================================
# Crown Safe Endpoints
# ============================================


async def analyze_product_endpoint(req: ProductAnalysisRequest, db: Session) -> ProductAnalysisResponse:
    """
    Analyze a hair product and return personalized Crown Score.

    This endpoint:
    1. Retrieves user's hair profile
    2. Analyzes product ingredients using Crown Score engine
    3. Provides personalized safety assessment
    4. Suggests safer alternatives if needed
    5. Saves scan history to database

    Args:
        req: Product analysis request
        db: Database session

    Returns:
        ProductAnalysisResponse with Crown Score and recommendations

    Raises:
        HTTPException: If user not found, no hair profile, or analysis fails
    """
    start_time = datetime.now()
    logger.info(
        f"Crown Safe product analysis for user_id={req.user_id}, "
        f"product={req.product_name}, ingredients_count={len(req.ingredients)}"
    )

    try:
        # 1. Validate user exists
        user = db.query(User).filter(User.id == req.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Optional: Check subscription status
        if not getattr(user, "is_subscribed", True):
            raise HTTPException(status_code=403, detail="Subscription required for Crown Safe analysis")

        # 2. Get user's hair profile
        hair_profile = get_user_hair_profile(req.user_id)
        if not hair_profile:
            raise HTTPException(
                status_code=400, detail="Please create a hair profile first. Use POST /api/v1/profile/hair"
            )

        # 3. Analyze product with Ingredient Analysis Agent
        agent = IngredientAnalysisAgent()
        result = await agent.analyze_product(
            product_name=req.product_name, ingredients=req.ingredients, hair_profile=hair_profile
        )

        # 4. Save scan to database
        scan = ProductScanModel(
            user_id=req.user_id,
            product_name=req.product_name,
            ingredients_scanned=req.ingredients,
            crown_score=result["crown_score"],
            verdict=result["verdict"],
            score_breakdown=result["breakdown"],
            recommendations=result["recommendations"],
            alternatives=result.get("alternatives", []),
            scan_date=datetime.now(),
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)

        # 5. Return response
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(
            f"Crown Safe analysis completed in {elapsed_ms:.2f}ms: "
            f"score={result['crown_score']}, verdict={result['verdict']}"
        )

        return ProductAnalysisResponse(
            status="COMPLETED",
            crown_score=result["crown_score"],
            verdict=result["verdict"],
            product_name=req.product_name,
            breakdown=result["breakdown"],
            recommendations=result["recommendations"],
            alternatives=result.get("alternatives", []),
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Crown Safe analysis failed: {e}", exc_info=True)
        return ProductAnalysisResponse(
            status="FAILED",
            crown_score=0,
            verdict="ERROR",
            product_name=req.product_name,
            breakdown={},
            recommendations="Analysis failed. Please try again.",
            alternatives=[],
            error=str(e),
        )


async def create_hair_profile_endpoint(req: HairProfileRequest, db: Session) -> HairProfileResponse:
    """
    Create or update a user's hair profile.

    Hair profiles enable personalized Crown Score calculations based on:
    - Hair type (3C, 4A, 4B, 4C, Mixed)
    - Porosity (Low, Medium, High)
    - Current hair state (dryness, breakage, etc.)
    - Hair care goals (moisture, growth, definition, etc.)
    - Known ingredient sensitivities

    Args:
        req: Hair profile request
        db: Database session

    Returns:
        HairProfileResponse with created/updated profile

    Raises:
        HTTPException: If user not found or profile creation fails
    """
    logger.info(f"Creating hair profile for user_id={req.user_id}, type={req.hair_type}")

    try:
        # 1. Validate user exists
        user = db.query(User).filter(User.id == req.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 2. Create or update hair profile
        from core_infra.database import create_hair_profile

        profile = create_hair_profile(
            user_id=req.user_id,
            hair_type=req.hair_type,
            porosity=req.porosity,
            hair_state=req.hair_state or {},
            hair_goals=req.hair_goals or {},
            sensitivities=req.sensitivities or {},
        )

        # 3. Return response
        return HairProfileResponse(
            status="COMPLETED",
            profile={
                "id": profile.id,
                "user_id": profile.user_id,
                "hair_type": profile.hair_type,
                "porosity": profile.porosity,
                "hair_state": profile.hair_state,
                "hair_goals": profile.hair_goals,
                "sensitivities": profile.sensitivities,
                "created_at": profile.created_at.isoformat(),
                "updated_at": profile.updated_at.isoformat(),
            },
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hair profile creation failed: {e}", exc_info=True)
        return HairProfileResponse(status="FAILED", profile={}, error=str(e))


async def get_hair_profile_endpoint(user_id: int, db: Session) -> HairProfileResponse:
    """
    Get a user's hair profile.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        HairProfileResponse with user's profile

    Raises:
        HTTPException: If user or profile not found
    """
    logger.info(f"Retrieving hair profile for user_id={user_id}")

    try:
        # 1. Validate user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 2. Get hair profile
        profile = get_user_hair_profile(user_id)
        if not profile:
            raise HTTPException(
                status_code=404, detail="Hair profile not found. Create one with POST /api/v1/profile/hair"
            )

        # 3. Return response
        return HairProfileResponse(
            status="COMPLETED",
            profile={
                "id": profile.id,
                "user_id": profile.user_id,
                "hair_type": profile.hair_type,
                "porosity": profile.porosity,
                "hair_state": profile.hair_state,
                "hair_goals": profile.hair_goals,
                "sensitivities": profile.sensitivities,
                "created_at": profile.created_at.isoformat(),
                "updated_at": profile.updated_at.isoformat(),
            },
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hair profile retrieval failed: {e}", exc_info=True)
        return HairProfileResponse(status="FAILED", profile={}, error=str(e))


async def get_scan_history_endpoint(user_id: int, limit: int = 50, db: Session = None) -> ScanHistoryResponse:
    """
    Get user's product scan history.

    Args:
        user_id: User ID
        limit: Maximum number of scans to return (default 50)
        db: Database session

    Returns:
        ScanHistoryResponse with scan history

    Raises:
        HTTPException: If user not found
    """
    logger.info(f"Retrieving scan history for user_id={user_id}, limit={limit}")

    try:
        # 1. Validate user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 2. Get scan history
        scans = (
            db.query(ProductScanModel)
            .filter(ProductScanModel.user_id == user_id)
            .order_by(ProductScanModel.scan_date.desc())
            .limit(limit)
            .all()
        )

        # 3. Format response
        scan_list = []
        for scan in scans:
            scan_list.append(
                {
                    "id": scan.id,
                    "product_name": scan.product_name,
                    "crown_score": scan.crown_score,
                    "verdict": scan.verdict,
                    "scan_date": scan.scan_date.isoformat(),
                    "ingredients_count": len(scan.ingredients_scanned) if scan.ingredients_scanned else 0,
                    "alternatives_count": len(scan.alternatives) if scan.alternatives else 0,
                }
            )

        return ScanHistoryResponse(status="COMPLETED", scans=scan_list, total_scans=len(scan_list), error=None)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scan history retrieval failed: {e}", exc_info=True)
        return ScanHistoryResponse(status="FAILED", scans=[], total_scans=0, error=str(e))
