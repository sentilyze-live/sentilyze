"""Budget management service."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.repositories.budget_repository import BudgetRepository
from ..models.budget import BudgetConfig


class BudgetService:
    """Budget tier management and cost optimization."""

    def __init__(self, db: AsyncSession):
        self.repo = BudgetRepository(db)

    async def get_budget_status(self, tenant_id: uuid.UUID) -> dict:
        """Get comprehensive budget status."""
        config = await self.repo.get_active_config(tenant_id)
        if not config:
            return {"error": "No active budget config"}

        current_spend = await self.repo.get_current_month_total(tenant_id)
        budget_limit = config.monthly_budget_usd

        percent_used = round((current_spend / budget_limit * 100), 2) if budget_limit > 0 else 0

        return {
            "tier": config.tier_name,
            "monthly_budget": float(budget_limit),
            "current_spend": float(current_spend),
            "remaining": float(budget_limit - current_spend),
            "percent_used": percent_used,
            "config": config.config_json,
        }

    async def check_budget_alerts(self, tenant_id: uuid.UUID) -> Optional[dict]:
        """Check if budget thresholds exceeded."""
        status = await self.get_budget_status(tenant_id)
        if "error" in status:
            return None

        percent = status["percent_used"]
        config = await self.repo.get_active_config(tenant_id)

        # Alert thresholds
        if percent >= 100:
            await self.repo.create_alert(
                tenant_id=tenant_id,
                alert_type="budget_exceeded",
                severity="critical",
                message=f"Budget exceeded: {percent}% used",
                current_spend=Decimal(str(status["current_spend"])),
                budget_limit=Decimal(str(status["monthly_budget"])),
                threshold_percent=Decimal("100"),
            )
            return {"level": "critical", "percent": percent}

        elif percent >= 90:
            await self.repo.create_alert(
                tenant_id=tenant_id,
                alert_type="budget_warning",
                severity="high",
                message=f"Budget warning: {percent}% used",
                current_spend=Decimal(str(status["current_spend"])),
                budget_limit=Decimal(str(status["monthly_budget"])),
                threshold_percent=Decimal("90"),
            )
            return {"level": "high", "percent": percent}

        elif percent >= 75:
            return {"level": "medium", "percent": percent}

        return None

    async def get_cost_optimization_tips(self, tenant_id: uuid.UUID) -> list[dict]:
        """Get cost optimization recommendations."""
        top_services = await self.repo.get_top_services_by_cost(tenant_id, limit=5)
        tips = []

        for service in top_services:
            if service["service_name"] == "vertex-ai-gemini":
                tips.append(
                    {
                        "service": "vertex-ai-gemini",
                        "tip": "Enable sentiment_lite_mode or reduce gemini_daily_limit",
                        "potential_savings": "50-80%",
                    }
                )
            elif service["service_name"] == "bigquery":
                tips.append(
                    {
                        "service": "bigquery",
                        "tip": "Optimize queries, use partitioning, reduce data retention",
                        "potential_savings": "30-50%",
                    }
                )

        return tips
