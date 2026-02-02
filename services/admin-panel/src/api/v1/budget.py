"""Budget management API endpoints."""

import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import get_current_user
from ...db.repositories.budget_repository import BudgetRepository
from ...db.session import get_db
from ...models.user import User

router = APIRouter(prefix="/budget", tags=["budget"])


# ============================================
# Pydantic Schemas
# ============================================


class BudgetConfigResponse(BaseModel):
    """Budget configuration response."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    tier_name: str
    monthly_budget_usd: Decimal
    config_json: dict
    is_active: bool
    effective_from: str
    effective_until: Optional[str] = None

    class Config:
        from_attributes = True


class BudgetConfigUpdate(BaseModel):
    """Budget configuration update."""

    monthly_budget_usd: Optional[Decimal] = Field(None, gt=0)
    config_json: Optional[dict] = None


class TierSwitchRequest(BaseModel):
    """Tier switch request."""

    tier_name: str = Field(..., pattern="^(minimal|basic|standard|premium|custom)$")


# ============================================
# Endpoints
# ============================================


@router.get("/config", response_model=BudgetConfigResponse)
async def get_budget_config(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get current budget configuration."""
    repo = BudgetRepository(db)
    config = await repo.get_active_config(current_user.tenant_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active budget configuration found"
        )

    return config


@router.put("/config", response_model=BudgetConfigResponse)
async def update_budget_config(
    update: BudgetConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current budget configuration."""
    repo = BudgetRepository(db)
    config = await repo.get_active_config(current_user.tenant_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active budget configuration found"
        )

    updated = await repo.update_config(
        config.id, monthly_budget=update.monthly_budget_usd, config_json=update.config_json
    )

    return updated


@router.get("/tiers", response_model=list[BudgetConfigResponse])
async def get_budget_tiers(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get all available budget tiers."""
    repo = BudgetRepository(db)
    tiers = await repo.get_all_tiers()
    return tiers


@router.post("/tier", response_model=BudgetConfigResponse)
async def switch_tier(
    request: TierSwitchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Switch to a different budget tier."""
    repo = BudgetRepository(db)

    try:
        new_config = await repo.switch_tier(current_user.tenant_id, request.tier_name)
        return new_config
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
