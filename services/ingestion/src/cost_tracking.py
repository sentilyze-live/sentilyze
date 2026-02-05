"""Cost tracking for ingestion API calls with connection pool management."""

import os
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


# Module-level singleton engine to prevent connection pool exhaustion
_engine: Optional[AsyncEngine] = None
_session_maker: Optional[sessionmaker] = None


def _get_engine() -> AsyncEngine:
    """Get or create the global database engine."""
    global _engine, _session_maker
    if _engine is None:
        db_url = os.getenv(
            "ADMIN_DB_URL",
            "postgresql+asyncpg://sentilyze:sentilyze123@postgres:5432/sentilyze_predictions",
        )
        _engine = create_async_engine(db_url, echo=False, pool_size=5, max_overflow=10)
        _session_maker = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine


def _get_session_maker() -> sessionmaker:
    """Get the global session maker."""
    _get_engine()  # Ensure engine is initialized
    return _session_maker


class IngestionCostTracker:
    """Track external API calls (GoldAPI, Finnhub, etc) with shared connection pool."""

    COSTS = {
        "goldapi": Decimal("0.00"),  # FREE
        "finnhub": Decimal("0.00"),  # FREE
        "coinmarketcap": Decimal("0.033"),  # $0.033 per 1K calls
    }

    def __init__(self):
        self.tenant_id = uuid.UUID(os.getenv("TENANT_ID", str(uuid.uuid4())))
        # Use shared engine and session maker
        self.session_maker = _get_session_maker()

    async def track_api_call(self, service_name: str, count: int = 1):
        """Track external API call."""
        cost_per_1k = self.COSTS.get(service_name, Decimal("0"))
        cost = (cost_per_1k / 1000) * count

        async with self.session_maker() as session:
            await session.execute(
                text(
                    """
                INSERT INTO cost_tracking
                (tenant_id, date, service_name, service_category, cost_type,
                 usage_count, estimated_cost_usd)
                VALUES (:tenant_id, :date, :service_name, 'api', 'api_call', :count, :cost)
                ON CONFLICT (tenant_id, date, service_name, cost_type)
                DO UPDATE SET
                    usage_count = cost_tracking.usage_count + :count,
                    estimated_cost_usd = cost_tracking.estimated_cost_usd + :cost
                """
                ),
                {
                    "tenant_id": self.tenant_id,
                    "date": date.today(),
                    "service_name": service_name,
                    "count": count,
                    "cost": cost,
                },
            )
            await session.commit()


# Global instance
_tracker = None


def get_tracker() -> IngestionCostTracker:
    """Get global tracker."""
    global _tracker
    if _tracker is None:
        _tracker = IngestionCostTracker()
    return _tracker
