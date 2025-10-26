"""
Premium Features API Endpoints
Provides endpoints for pregnancy safety and allergy checking features
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# LEGACY BABY CODE: FamilyMember removed for Crown Safe
from core_infra.database import get_db, User  # , FamilyMember
from core_infra.auth import get_current_active_user
from core_infra.rate_limiter import limiter
from api.schemas.common import ok, fail
from agents.premium.pregnancy_product_safety_agent.agent_logic import (
    PregnancyProductSafetyAgentLogic,
)
from agents.premium.allergy_sensitivity_agent.agent_logic import (
    AllergySensitivityAgentLogic,
)

logger = logging.getLogger(__name__)

# Create router with prefix
router = APIRouter(prefix="/api/v1/premium", tags=["Premium Features"])

# ==================== Request/Response Models ====================


class PregnancyCheckRequest(BaseModel):
    """Request model for pregnancy safety check"""

    barcode: Optional[str] = Field(None, description="Product barcode/UPC")
    product_name: Optional[str] = Field(None, description="Product name if barcode not available")
    trimester: int = Field(1, ge=1, le=3, description="Pregnancy trimester (1-3)")
    user_id: Optional[int] = Field(None, description="User ID (deprecated; derived from token if present)")


class PregnancyCheckResponse(BaseModel):
    """Response model for pregnancy safety check"""

    status: str
    product_name: str
    is_safe: bool
    risk_level: Optional[str] = None
    alerts: List[Dict[str, Any]]
    recommendations: List[str]
    checked_at: datetime


class AllergyCheckRequest(BaseModel):
    """Request model for allergy check"""

    barcode: Optional[str] = Field(None, description="Product barcode/UPC")
    product_name: Optional[str] = Field(None, description="Product name if barcode not available")
    user_id: Optional[int] = Field(None, description="User ID (deprecated; derived from token if present)")
    check_all_members: bool = Field(True, description="Check for all family members")


class AllergyCheckResponse(BaseModel):
    """Response model for allergy check"""

    status: str
    product_name: str
    is_safe: bool
    alerts: List[Dict[str, Any]]
    safe_for_members: List[str]
    unsafe_for_members: List[Dict[str, Any]]
    checked_at: datetime


class FamilyMemberRequest(BaseModel):
    """Request model for adding/updating family member"""

    name: str = Field(..., min_length=1, max_length=100, description="Family member name")
    relationship: Optional[str] = Field(None, description="Relationship to user")
    allergies: List[str] = Field(default=[], description="List of allergies")
    dietary_restrictions: Optional[List[str]] = Field(default=[], description="Dietary restrictions")
    age: Optional[int] = Field(None, ge=0, le=150, description="Age of family member")


class FamilyMemberResponse(BaseModel):
    """Response model for family member"""

    id: int
    name: str
    relationship: Optional[str]
    allergies: List[str]
    dietary_restrictions: List[str]
    age: Optional[int]
    created_at: datetime


class CombinedSafetyCheckRequest(BaseModel):
    """Request for combined safety check including pregnancy and allergies"""

    barcode: Optional[str] = Field(None, description="Product barcode/UPC")
    product_name: Optional[str] = Field(None, description="Product name")
    user_id: int = Field(..., description="User ID")
    check_pregnancy: bool = Field(False, description="Include pregnancy safety check")
    trimester: Optional[int] = Field(None, ge=1, le=3, description="If pregnant, which trimester")
    check_allergies: bool = Field(True, description="Include allergy check")


# Initialize agent logic instances
pregnancy_agent = PregnancyProductSafetyAgentLogic(agent_id="api_pregnancy_agent")
allergy_agent = AllergySensitivityAgentLogic(agent_id="api_allergy_agent")

# ==================== Pregnancy Safety Endpoints ====================


@router.post("/pregnancy/check")
@limiter.limit("10 per minute")
async def check_pregnancy_safety(
    payload: PregnancyCheckRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Check if a product is safe for pregnant women.

    This endpoint:
    1. Identifies the product from barcode or name
    2. Checks ingredients against pregnancy safety database
    3. Returns trimester-specific safety recommendations
    """
    try:
        # Resolve user from JWT
        user_id = current_user.id
        if payload.user_id and payload.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "error": {"message": "Mismatched user_id vs token"},
                },
            )
        logger.info(f"Pregnancy safety check for user {user_id}, trimester {payload.trimester}")

        # Validate user exists (defensive)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail={"success": False, "error": {"message": "User not found"}},
            )

        # Use barcode as product identifier (UPC)
        product_upc = payload.barcode or "unknown"

        # Perform pregnancy safety check
        result = pregnancy_agent.check_product_safety(product_upc, payload.trimester)

        # Build recommendations based on alerts
        recommendations = []
        if result.get("alerts"):
            for alert in result["alerts"]:
                if alert.get("risk_level") == "High":
                    recommendations.append(
                        f"AVOID: {alert['ingredient']} - {alert.get('reason', 'High risk during pregnancy')}"
                    )
                elif alert.get("risk_level") == "Moderate":
                    recommendations.append(
                        f"CAUTION: {alert['ingredient']} - {alert.get('reason', 'Use with caution')}"
                    )
            recommendations.append("Consult your healthcare provider before using this product.")
        else:
            recommendations.append("No known pregnancy risks identified in our database.")
            recommendations.append("Always consult your healthcare provider for personalized advice.")

        # Determine overall risk level
        risk_level = "Low"
        if result.get("alerts"):
            risk_levels = [a.get("risk_level", "Low") for a in result["alerts"]]
            if "High" in risk_levels:
                risk_level = "High"
            elif "Moderate" in risk_levels:
                risk_level = "Moderate"

        payload = {
            "product_name": result.get("product_name", payload.product_name or "Unknown Product"),
            "is_safe": result.get("is_safe", True),
            "risk_level": risk_level,
            "alerts": result.get("alerts", []),
            "recommendations": recommendations,
            "checked_at": datetime.now(),
        }
        return ok(payload)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pregnancy safety check failed: {e}", exc_info=True)
        fail(f"Safety check failed: {str(e)}", code="INTERNAL_ERROR", status=500)


# ==================== Allergy Check Endpoints ====================


@router.post("/allergy/check")
@limiter.limit("10 per minute")
async def check_product_allergies(
    payload: AllergyCheckRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Check if a product contains allergens for any family member.

    This endpoint:
    1. Retrieves family member allergy profiles
    2. Checks product ingredients against known allergens
    3. Returns personalized alerts for each family member
    """
    try:
        # Resolve user from JWT
        user_id = current_user.id
        if payload.user_id and payload.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "error": {"message": "Mismatched user_id vs token"},
                },
            )
        logger.info(f"Allergy check for user {user_id} family")

        # Validate user exists (defensive)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail={"success": False, "error": {"message": "User not found"}},
            )

        # Use barcode as product identifier
        product_upc = payload.barcode or "unknown"

        # Perform allergy check for family
        result = allergy_agent.check_product_for_family(user_id, product_upc)

        # Process results to separate safe and unsafe members
        safe_members = []
        unsafe_members = []

        if result.get("alerts"):
            # Get all family members
            if user.family_members:
                all_members = [member.name for member in user.family_members]

                # Identify unsafe members
                unsafe_member_names = set()
                for alert in result["alerts"]:
                    member_name = alert.get("member_name")
                    if member_name:
                        unsafe_member_names.add(member_name)
                        unsafe_members.append(
                            {
                                "member_name": member_name,
                                "allergens_found": alert.get("found_allergens", []),
                                "risk_level": alert.get("risk_level", "high"),
                            }
                        )

                # Remaining members are safe
                safe_members = [m for m in all_members if m not in unsafe_member_names]
            else:
                safe_members = ["No family members registered"]
        else:
            # Product is safe for everyone
            if user.family_members:
                safe_members = [member.name for member in user.family_members]
            else:
                safe_members = ["No family members registered"]

        payload: Dict[str, Any] = {
            "product_name": result.get("product_name", payload.product_name or "Unknown Product"),
            "is_safe": result.get("is_safe", True),
            "alerts": result.get("alerts", []),
            "safe_for_members": safe_members,
            "unsafe_for_members": unsafe_members,
            "checked_at": datetime.now(),
        }
        if not user.family_members:
            payload["notice"] = "No family members registered"
        return ok(payload)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Allergy check failed: {e}", exc_info=True)
        fail(f"Allergy check failed: {str(e)}", code="INTERNAL_ERROR", status=500)


# ==================== Family Member Management Endpoints ====================


@router.get("/family/members", response_model=List[FamilyMemberResponse])
async def get_family_members(user_id: int = Query(..., description="User ID"), db: Session = Depends(get_db)):
    """
    Get all family members and their allergy profiles.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not user.family_members:
            return []

        members = []

        for member in user.family_members:
            # Return simplified response since not all fields are in DB
            members.append(
                FamilyMemberResponse(
                    id=member.id,
                    name=member.name,
                    relationship=None,  # Not stored in DB yet
                    allergies=[],  # Would need proper allergy model integration
                    dietary_restrictions=[],  # Not stored in DB yet
                    age=None,  # Not stored in DB yet
                    created_at=datetime.now(),
                )
            )

        return members

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get family members: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve family members: {str(e)}")


@router.post("/family/members", response_model=FamilyMemberResponse)
async def add_family_member(
    user_id: int = Query(..., description="User ID"),
    member: FamilyMemberRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Add a new family member with their allergy profile.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create new family member linked to the user
        new_member = FamilyMember(user_id=user_id, name=member.name)

        # Note: Additional fields like relationship, age, allergies would need
        # to be added to the database model. For now, just save the name.

        db.add(new_member)
        db.commit()
        db.refresh(new_member)

        # Return the requested fields even if not stored in DB
        return FamilyMemberResponse(
            id=new_member.id,
            name=new_member.name,
            relationship=member.relationship,
            allergies=member.allergies or [],
            dietary_restrictions=member.dietary_restrictions or [],
            age=member.age,
            created_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add family member: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add family member: {str(e)}")


@router.put("/family/members/{member_id}", response_model=FamilyMemberResponse)
async def update_family_member(
    member_id: int,
    user_id: int = Query(..., description="User ID"),
    member: FamilyMemberRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Update a family member's allergy profile.
    """
    try:
        # Verify user owns this family member
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get the family member
        family_member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
        if not family_member:
            raise HTTPException(status_code=404, detail="Family member not found")

        # Verify ownership
        if family_member.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this family member")

        # Update only the fields that exist in the database model
        family_member.name = member.name
        # Note: Other fields like allergies, relationship, age, dietary_restrictions
        # would need to be added to the database model

        db.commit()
        db.refresh(family_member)

        # Return the requested fields even if not all are stored in DB
        return FamilyMemberResponse(
            id=family_member.id,
            name=family_member.name,
            relationship=member.relationship,
            allergies=member.allergies or [],
            dietary_restrictions=member.dietary_restrictions or [],
            age=member.age,
            created_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update family member: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update family member: {str(e)}")


@router.delete("/family/members/{member_id}")
async def delete_family_member(
    member_id: int,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """
    Remove a family member from the user's family.
    """
    try:
        # Verify user owns this family member
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get the family member
        family_member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
        if not family_member:
            raise HTTPException(status_code=404, detail="Family member not found")

        # Verify ownership
        if family_member.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this family member")

        # Delete family member
        db.delete(family_member)
        db.commit()

        return {
            "status": "success",
            "message": f"Family member {family_member.name} removed",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete family member: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete family member: {str(e)}")


# ==================== Dev Override Endpoints for Testing ====================


@router.post("/pregnancy/check-dev")
async def check_pregnancy_safety_dev(payload: PregnancyCheckRequest, db: Session = Depends(get_db)):
    """
    Dev override version of pregnancy safety check - no authentication required
    """
    try:
        # Check dev override for premium features
        from api.services.dev_override import dev_entitled

        REQUIRED_FEATURE = "premium.pregnancy"

        if not dev_entitled(payload.user_id or 0, REQUIRED_FEATURE):
            raise HTTPException(
                status_code=402,
                detail="Subscription required for pregnancy safety check",
            )

        logger.info(f"Pregnancy safety check for user {payload.user_id}")

        # Initialize pregnancy agent
        pregnancy_agent = PregnancyProductSafetyAgentLogic(agent_id="pregnancy_check_dev")

        # Perform pregnancy safety check
        result = pregnancy_agent.check_product_safety(
            payload.barcode or payload.product_name or "unknown", payload.trimester
        )

        return PregnancyCheckResponse(
            status="COMPLETED",
            product_name=payload.product_name or "Unknown Product",
            is_safe=result.get("is_safe", True),
            risk_level=result.get("risk_level", "Low"),
            alerts=result.get("alerts", []),
            recommendations=result.get("recommendations", []),
            checked_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pregnancy safety check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pregnancy safety check failed: {str(e)}")


@router.post("/allergy/check-dev")
async def check_allergy_safety_dev(payload: AllergyCheckRequest, db: Session = Depends(get_db)):
    """
    Dev override version of allergy safety check - no authentication required
    """
    try:
        # Check dev override for premium features
        from api.services.dev_override import dev_entitled

        REQUIRED_FEATURE = "premium.allergy"

        if not dev_entitled(payload.user_id or 0, REQUIRED_FEATURE):
            raise HTTPException(status_code=402, detail="Subscription required for allergy safety check")

        logger.info(f"Allergy safety check for user {payload.user_id}")

        # Initialize allergy agent
        allergy_agent = AllergySensitivityAgentLogic(agent_id="allergy_check_dev")

        # Perform allergy safety check
        result = allergy_agent.check_product_for_family(
            payload.user_id or 0, payload.barcode or payload.product_name or "unknown"
        )

        return AllergyCheckResponse(
            status="COMPLETED",
            product_name=payload.product_name or "Unknown Product",
            is_safe=result.get("is_safe", True),
            risk_level=result.get("risk_level", "Low"),
            alerts=result.get("alerts", []),
            recommendations=result.get("recommendations", []),
            safe_for_members=result.get("safe_for_members", []),
            unsafe_for_members=result.get("unsafe_for_members", []),
            checked_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Allergy safety check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Allergy safety check failed: {str(e)}")


# ==================== Combined Safety Check Endpoint ====================


@router.post("/safety/comprehensive")
async def comprehensive_safety_check(request: CombinedSafetyCheckRequest, db: Session = Depends(get_db)):
    """
    Perform a comprehensive safety check including recalls, pregnancy, and allergies.

    This endpoint combines multiple safety checks into one response.
    """
    try:
        logger.info(f"Comprehensive safety check for user {request.user_id}")

        # Check dev override for premium features
        from api.services.dev_override import dev_entitled

        REQUIRED_FEATURE = "safety.comprehensive"

        if not dev_entitled(request.user_id, REQUIRED_FEATURE):
            # Check subscription for non-dev users
            user = db.query(User).filter(User.id == request.user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            if not getattr(user, "is_subscribed", False):
                raise HTTPException(
                    status_code=402,
                    detail="Subscription required for comprehensive safety check",
                )
        else:
            logger.info(f"DEV OVERRIDE: Bypassing subscription check for user {request.user_id}")
            # Skip subscription validation and proceed

        response = {
            "product_identifier": request.barcode or request.product_name,
            "checks_performed": [],
            "overall_safety": "SAFE",
            "risk_factors": [],
            "recommendations": [],
            "timestamp": datetime.now().isoformat(),
        }

        # Pregnancy check
        if request.check_pregnancy and request.trimester:
            pregnancy_result = pregnancy_agent.check_product_safety(request.barcode or "unknown", request.trimester)

            response["checks_performed"].append("pregnancy")

            if not pregnancy_result.get("is_safe"):
                response["overall_safety"] = "CAUTION"
                response["risk_factors"].append({"type": "pregnancy", "alerts": pregnancy_result.get("alerts", [])})

                for alert in pregnancy_result.get("alerts", []):
                    if alert.get("risk_level") == "High":
                        response["overall_safety"] = "UNSAFE"
                        response["recommendations"].append(
                            f"PREGNANCY WARNING: Avoid {alert['ingredient']} - {alert.get('reason', 'High risk')}"
                        )

        # Allergy check
        if request.check_allergies:
            allergy_result = allergy_agent.check_product_for_family(request.user_id, request.barcode or "unknown")

            response["checks_performed"].append("allergies")

            if not allergy_result.get("is_safe"):
                if response["overall_safety"] == "SAFE":
                    response["overall_safety"] = "CAUTION"

                response["risk_factors"].append({"type": "allergies", "alerts": allergy_result.get("alerts", [])})

                for alert in allergy_result.get("alerts", []):
                    response["recommendations"].append(
                        f"ALLERGY WARNING for {alert['member_name']}: Contains {', '.join(alert.get('found_allergens', []))}"
                    )

        # Add general recommendation
        if response["overall_safety"] == "SAFE":
            response["recommendations"].append("No safety concerns identified based on available data.")
        else:
            response["recommendations"].append("Please review all warnings carefully before use.")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Comprehensive safety check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Safety check failed: {str(e)}")
