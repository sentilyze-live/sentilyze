"""Feature flags API endpoints."""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_db
from ...models import FeatureFlag, FeatureFlagAuditLog, User
from ...core.auth import get_current_active_user, require_admin

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])


# Pydantic schemas
class FeatureFlagBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    enabled: bool = False
    cost_impact_daily_usd: Optional[float] = Field(None, ge=0)
    category: Optional[str] = Field(None, max_length=50)


class FeatureFlagCreate(FeatureFlagBase):
    pass


class FeatureFlagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    cost_impact_daily_usd: Optional[float] = Field(None, ge=0)
    category: Optional[str] = Field(None, max_length=50)


class FeatureFlagResponse(FeatureFlagBase):
    id: int
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[int]

    class Config:
        from_attributes = True


class FeatureFlagCheckResponse(BaseModel):
    key: str
    enabled: bool


class FeatureFlagsCheckRequest(BaseModel):
    keys: List[str]


# Helper function to log flag changes
async def log_flag_change(
    db: AsyncSession,
    flag_key: str,
    action: str,
    old_value: Optional[str],
    new_value: Optional[str],
    user_id: Optional[int],
    request: Optional[Request] = None
):
    """Log a feature flag change to audit log."""
    log_entry = FeatureFlagAuditLog(
        flag_key=flag_key,
        action=action,
        old_value=old_value,
        new_value=new_value,
        changed_by=user_id,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.add(log_entry)
    await db.commit()


@router.get("", response_model=List[FeatureFlagResponse])
async def list_feature_flags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all feature flags."""
    result = await db.execute(select(FeatureFlag).order_by(FeatureFlag.key))
    flags = result.scalars().all()
    return flags


@router.get("/check/{key}", response_model=FeatureFlagCheckResponse)
async def check_feature_flag(
    key: str,
    db: AsyncSession = Depends(get_db),
):
    """Check if a feature flag is enabled (public endpoint)."""
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
    flag = result.scalar_one_or_none()
    
    if not flag:
        return FeatureFlagCheckResponse(key=key, enabled=False)
    
    return FeatureFlagCheckResponse(key=key, enabled=flag.enabled)


@router.post("/check", response_model=dict)
async def check_feature_flags(
    request: FeatureFlagsCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """Check multiple feature flags at once (public endpoint)."""
    result = await db.execute(
        select(FeatureFlag).where(FeatureFlag.key.in_(request.keys))
    )
    flags = result.scalars().all()
    
    flags_map = {flag.key: flag.enabled for flag in flags}
    
    # Add missing keys as disabled
    for key in request.keys:
        if key not in flags_map:
            flags_map[key] = False
    
    return flags_map


@router.post("", response_model=FeatureFlagResponse, status_code=status.HTTP_201_CREATED)
async def create_feature_flag(
    flag_data: FeatureFlagCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new feature flag (admin only)."""
    # Check if flag already exists
    result = await db.execute(
        select(FeatureFlag).where(FeatureFlag.key == flag_data.key)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Feature flag with key '{flag_data.key}' already exists"
        )
    
    flag = FeatureFlag(
        **flag_data.model_dump(),
        updated_by=current_user.id
    )
    db.add(flag)
    await db.commit()
    await db.refresh(flag)
    
    # Log the creation
    await log_flag_change(
        db, flag.key, "CREATE", None, str(flag_data.model_dump()), current_user.id, request
    )
    
    return flag


@router.put("/{key}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    key: str,
    flag_data: FeatureFlagUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update a feature flag (admin only)."""
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
    flag = result.scalar_one_or_none()
    
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag with key '{key}' not found"
        )
    
    # Store old values for audit log
    old_values = {
        "name": flag.name,
        "description": flag.description,
        "enabled": flag.enabled,
        "cost_impact_daily_usd": float(flag.cost_impact_daily_usd) if flag.cost_impact_daily_usd else None,
        "category": flag.category,
    }
    
    # Update fields
    update_data = flag_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(flag, field, value)
    
    flag.updated_by = current_user.id
    
    await db.commit()
    await db.refresh(flag)
    
    # Log the update
    await log_flag_change(
        db, flag.key, "UPDATE", str(old_values), str(update_data), current_user.id, request
    )
    
    return flag


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature_flag(
    key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a feature flag (admin only)."""
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
    flag = result.scalar_one_or_none()
    
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag with key '{key}' not found"
        )
    
    # Log the deletion
    await log_flag_change(
        db, flag.key, "DELETE", str({
            "name": flag.name,
            "enabled": flag.enabled,
            "category": flag.category,
        }), None, current_user.id, request
    )
    
    await db.delete(flag)
    await db.commit()
    
    return None


@router.get("/costs/summary")
async def get_cost_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get cost summary for all enabled feature flags."""
    result = await db.execute(select(FeatureFlag))
    flags = result.scalars().all()
    
    enabled_flags = [f for f in flags if f.enabled]
    total_daily_cost = sum(f.daily_cost for f in enabled_flags)
    
    return {
        "total_daily_cost_usd": round(total_daily_cost, 2),
        "total_monthly_estimate_usd": round(total_daily_cost * 30, 2),
        "enabled_flags_count": len(enabled_flags),
        "total_flags_count": len(flags),
        "flags_by_category": {
            category: {
                "count": len([f for f in enabled_flags if f.category == category]),
                "daily_cost": round(sum(f.daily_cost for f in enabled_flags if f.category == category), 2)
            }
            for category in set(f.category for f in flags if f.category)
        }
    }
