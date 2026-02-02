"""Cost tracking API endpoints."""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import get_current_user
from ...db.repositories.budget_repository import BudgetRepository
from ...db.session import get_db
from ...models.user import User

router = APIRouter(prefix="/costs", tags=["costs"])


class CostSummary(BaseModel):
    """Current month cost summary."""

    total: Decimal
    by_category: dict[str, Decimal]
    top_services: list[dict]


class DailyCost(BaseModel):
    """Daily cost breakdown."""

    date: date
    total: Decimal
    by_service: dict[str, Decimal]


@router.get("/current", response_model=CostSummary)
async def get_current_costs(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get current month cost summary."""
    repo = BudgetRepository(db)

    total = await repo.get_current_month_total(current_user.tenant_id)
    by_category = await repo.get_current_month_by_category(current_user.tenant_id)
    top_services = await repo.get_top_services_by_cost(current_user.tenant_id)

    return CostSummary(total=total, by_category=by_category, top_services=top_services)


@router.get("/daily")
async def get_daily_costs(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get daily cost breakdown."""
    repo = BudgetRepository(db)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    costs = await repo.get_costs_by_date_range(current_user.tenant_id, start_date, end_date)

    return {"start_date": start_date, "end_date": end_date, "costs": costs}
