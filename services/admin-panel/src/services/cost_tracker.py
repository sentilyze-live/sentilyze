"""Cost tracking service for API usage."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.repositories.budget_repository import BudgetRepository


class CostTracker:
    """Track API costs and usage."""

    # Cost per 1000 requests (USD)
    PRICING = {
        "vertex-ai-gemini-flash": Decimal("0.075"),  # $0.075 per 1K requests
        "goldapi": Decimal("0.00"),  # FREE
        "finnhub": Decimal("0.00"),  # FREE
        "bigquery-query": Decimal("5.00"),  # $5 per TB
        "pubsub-message": Decimal("0.00"),  # FREE tier
    }

    def __init__(self, db: AsyncSession):
        self.repo = BudgetRepository(db)

    async def track_api_call(
        self,
        tenant_id: uuid.UUID,
        service_name: str,
        service_category: str,
        cost_type: str,
        count: int = 1,
    ):
        """Track single API call."""
        cost_per_1k = self.PRICING.get(f"{service_name}-{cost_type}", Decimal("0"))
        estimated_cost = (cost_per_1k / 1000) * count

        await self.repo.track_cost(
            tenant_id=tenant_id,
            date_=date.today(),
            service_name=service_name,
            service_category=service_category,
            cost_type=cost_type,
            usage_count=count,
            estimated_cost_usd=estimated_cost,
        )

    async def track_gemini_call(self, tenant_id: uuid.UUID, model: str = "flash"):
        """Track Vertex AI Gemini call."""
        await self.track_api_call(
            tenant_id=tenant_id,
            service_name="vertex-ai-gemini",
            service_category="ml",
            cost_type=f"gemini-{model}",
            count=1,
        )

    async def track_bigquery_bytes(self, tenant_id: uuid.UUID, bytes_processed: int):
        """Track BigQuery bytes processed."""
        tb_processed = Decimal(bytes_processed) / Decimal(1_000_000_000_000)
        cost = tb_processed * Decimal("5.00")

        await self.repo.track_cost(
            tenant_id=tenant_id,
            date_=date.today(),
            service_name="bigquery",
            service_category="storage",
            cost_type="query_bytes",
            usage_amount=Decimal(bytes_processed),
            estimated_cost_usd=cost,
        )

    async def check_quota(self, tenant_id: uuid.UUID, service_name: str, quota_type: str) -> bool:
        """Check if quota limit reached."""
        quota = await self.repo.get_quota(tenant_id, service_name, quota_type)
        if not quota:
            return True  # No quota = allowed

        return quota.current_usage < quota.quota_limit
