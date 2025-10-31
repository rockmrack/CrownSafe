"""Crown Safe - Hair Profile Management Endpoints
Handles user hair profiles for personalized Crown Score calculations.

Endpoints:
- POST /api/v1/profiles - Create new hair profile
- GET /api/v1/profiles/{user_id} - Get user's hair profile
- PUT /api/v1/profiles/{user_id} - Update hair profile
- DELETE /api/v1/profiles/{user_id} - Delete hair profile (optional)
"""

import logging
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth_endpoints import get_current_user
from core_infra.crown_safe_models import HairProfileModel
from core_infra.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/profiles", tags=["hair-profiles"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class HairProfileCreate(BaseModel):
    """Request model for creating a hair profile."""

    hair_type: str = Field(..., description="Hair type: 3C, 4A, 4B, 4C, Mixed")
    porosity: str = Field(..., description="Porosity: Low, Medium, High")
    hair_state: list[str] = Field(
        default=[],
        description="Current state: Natural, Relaxed, Transitioning, Heat-damaged, Color-treated",
    )
    hair_goals: list[str] = Field(
        default=[],
        description="Goals: Growth, Moisture retention, Edge recovery, Definition, Thickness",
    )
    sensitivities: list[str] = Field(
        default=[],
        description="Sensitivities: protein-sensitive, coconut-sensitive, fragrance-sensitive",
    )
    preferred_brands: list[str] = Field(default=[], description="Preferred brand names")
    avoided_ingredients: list[str] = Field(default=[], description="Ingredients to avoid")
    climate: str = Field(default="humid", description="Climate: humid, dry, mixed (affects humectants)")

    class Config:
        json_schema_extra = {
            "example": {
                "hair_type": "4C",
                "porosity": "High",
                "hair_state": ["Natural"],
                "hair_goals": ["Moisture retention", "Edge recovery"],
                "sensitivities": ["protein-sensitive"],
                "preferred_brands": ["Shea Moisture", "Mielle"],
                "avoided_ingredients": ["Mineral Oil", "Petrolatum"],
                "climate": "dry",
            },
        }


class HairProfileUpdate(BaseModel):
    """Request model for updating a hair profile (all fields optional)."""

    hair_type: str | None = None
    porosity: str | None = None
    hair_state: list[str] | None = None
    hair_goals: list[str] | None = None
    sensitivities: list[str] | None = None
    preferred_brands: list[str] | None = None
    avoided_ingredients: list[str] | None = None
    climate: str | None = None


class HairProfileResponse(BaseModel):
    """Response model for hair profile."""

    id: int
    user_id: int
    hair_type: str
    porosity: str
    hair_state: list[str]
    hair_goals: list[str]
    sensitivities: list[str]
    preferred_brands: list[str]
    avoided_ingredients: list[str]
    climate: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApiResponse(BaseModel):
    """Standard API response wrapper."""

    success: bool
    message: str
    data: dict | None = None


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_hair_profile(
    profile_data: HairProfileCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new hair profile for the current user.

    **Note**: Each user can only have one hair profile. Use PUT to update existing profile.
    """
    try:
        # Check if profile already exists
        existing_profile = db.query(HairProfileModel).filter(HairProfileModel.user_id == current_user.id).first()

        if existing_profile:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Hair profile already exists. Use PUT /profiles/{user_id} to update.",
            )

        # Create new profile
        new_profile = HairProfileModel(
            user_id=current_user.id,
            hair_type=profile_data.hair_type,
            porosity=profile_data.porosity,
            hair_state=profile_data.hair_state,
            hair_goals=profile_data.hair_goals,
            sensitivities=profile_data.sensitivities,
            preferred_brands=profile_data.preferred_brands,
            avoided_ingredients=profile_data.avoided_ingredients,
            climate=profile_data.climate,
        )

        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)

        logger.info(f"✅ Created hair profile for user {current_user.id}")

        return ApiResponse(
            success=True,
            message="Hair profile created successfully",
            data={
                "profile_id": new_profile.id,
                "user_id": new_profile.user_id,
                "hair_type": new_profile.hair_type,
                "porosity": new_profile.porosity,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Error creating hair profile: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create hair profile",
        )


@router.get("/{user_id}", response_model=HairProfileResponse)
async def get_hair_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get hair profile for a specific user.

    Users can only access their own profile unless they have admin privileges.
    """
    # Security: Users can only access their own profile
    if current_user.id != user_id and not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own hair profile",
        )

    profile = db.query(HairProfileModel).filter(HairProfileModel.user_id == user_id).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hair profile not found. Create one with POST /profiles",
        )

    return profile


@router.put("/{user_id}", response_model=ApiResponse)
async def update_hair_profile(
    user_id: int,
    profile_data: HairProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update an existing hair profile.

    Only updates fields that are provided. Omitted fields remain unchanged.
    """
    # Security: Users can only update their own profile
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own hair profile",
        )

    profile = db.query(HairProfileModel).filter(HairProfileModel.user_id == user_id).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hair profile not found. Create one with POST /profiles",
        )

    try:
        # Update only provided fields
        update_data = profile_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(profile, field, value)

        profile.updated_at = datetime.now(UTC)

        db.commit()
        db.refresh(profile)

        logger.info(f"✅ Updated hair profile for user {user_id} - fields: {list(update_data.keys())}")

        return ApiResponse(
            success=True,
            message="Hair profile updated successfully",
            data={
                "profile_id": profile.id,
                "updated_fields": list(update_data.keys()),
            },
        )

    except Exception as e:
        logger.exception(f"❌ Error updating hair profile: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update hair profile",
        )


@router.delete("/{user_id}", response_model=ApiResponse)
async def delete_hair_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a hair profile (optional feature).

    This is typically used for account deletion or data privacy requests.
    """
    # Security: Users can only delete their own profile
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own hair profile",
        )

    profile = db.query(HairProfileModel).filter(HairProfileModel.user_id == user_id).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hair profile not found",
        )

    try:
        db.delete(profile)
        db.commit()

        logger.info(f"✅ Deleted hair profile for user {user_id}")

        return ApiResponse(success=True, message="Hair profile deleted successfully", data=None)

    except Exception as e:
        logger.exception(f"❌ Error deleting hair profile: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete hair profile",
        )
