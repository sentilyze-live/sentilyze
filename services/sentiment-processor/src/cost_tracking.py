"""Cost tracking helper for sentiment processor."""

import asyncio
import os
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Import from admin-panel models (requires shared models or package)
# For now, use direct SQL


class SentimentCostTracker:
    """Track Gemini API usage costs."""

    def __init__(self):
        self.tenant_id = uuid.UUID(os.getenv("TENANT_ID", str(uuid.uuid4())))
        self.db_url = os.getenv(
            "ADMIN_DB_URL",
            "postgresql+asyncpg://sentilyze:sentilyze123@postgres:5432/sentilyze_predictions",
        )
        self.engine = None
        self.session = None

    async def initialize(self):
        """Initialize DB connection."""
        self.engine = create_async_engine(self.db_url, echo=False)
        async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.session = async_session

    async def track_gemini_call(self, model: str = "flash"):
        """Track a single Gemini API call."""
        if not self.session:
            return  # Skip if not initialized

        cost_per_1k = Decimal("0.075") if model == "flash" else Decimal("0.25")
        cost = cost_per_1k / 1000

        async with self.session() as session:
            await session.execute(
                """
                INSERT INTO cost_tracking
                (tenant_id, date, service_name, service_category, cost_type,
                 usage_count, estimated_cost_usd)
                VALUES (:tenant_id, :date, 'vertex-ai-gemini', 'ml', 'api_call', 1, :cost)
                ON CONFLICT (tenant_id, date, service_name, cost_type)
                DO UPDATE SET
                    usage_count = cost_tracking.usage_count + 1,
                    estimated_cost_usd = cost_tracking.estimated_cost_usd + :cost
                """,
                {
                    "tenant_id": self.tenant_id,
                    "date": date.today(),
                    "cost": cost,
                },
            )
            await session.commit()


# Global tracker instance
_tracker = None


async def get_tracker() -> SentimentCostTracker:
    """Get or create global tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = SentimentCostTracker()
        await _tracker.initialize()
    return _tracker
