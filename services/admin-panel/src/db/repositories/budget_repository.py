"""Budget management repository."""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.budget import (
    BudgetAlert,
    BudgetConfig,
    CostReportDaily,
    CostTracking,
    ServiceQuota,
)


class BudgetRepository:
    """Repository for budget configuration operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================
    # Budget Config Operations
    # ============================================

    async def get_active_config(self, tenant_id: uuid.UUID) -> Optional[BudgetConfig]:
        """Get active budget configuration for tenant."""
        query = select(BudgetConfig).where(
            and_(BudgetConfig.tenant_id == tenant_id, BudgetConfig.is_active == True)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_config_by_id(self, config_id: uuid.UUID) -> Optional[BudgetConfig]:
        """Get budget configuration by ID."""
        query = select(BudgetConfig).where(BudgetConfig.id == config_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_tiers(self) -> list[BudgetConfig]:
        """Get all budget tier templates."""
        query = select(BudgetConfig).order_by(BudgetConfig.monthly_budget_usd)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_config(
        self, tenant_id: uuid.UUID, tier_name: str, monthly_budget: Decimal, config_json: dict
    ) -> BudgetConfig:
        """Create new budget configuration."""
        # Deactivate previous active config
        await self._deactivate_previous_configs(tenant_id)

        config = BudgetConfig(
            tenant_id=tenant_id,
            tier_name=tier_name,
            monthly_budget_usd=monthly_budget,
            config_json=config_json,
            is_active=True,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def switch_tier(self, tenant_id: uuid.UUID, tier_name: str) -> BudgetConfig:
        """Switch to a different budget tier."""
        # Get tier template
        query = select(BudgetConfig).where(
            and_(
                BudgetConfig.tier_name == tier_name,
                BudgetConfig.tenant_id == tenant_id,  # Or get from templates
            )
        )
        result = await self.db.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            raise ValueError(f"Budget tier '{tier_name}' not found")

        # Create new config from template
        return await self.create_config(
            tenant_id=tenant_id,
            tier_name=template.tier_name,
            monthly_budget=template.monthly_budget_usd,
            config_json=template.config_json,
        )

    async def update_config(
        self,
        config_id: uuid.UUID,
        monthly_budget: Optional[Decimal] = None,
        config_json: Optional[dict] = None,
    ) -> Optional[BudgetConfig]:
        """Update existing budget configuration."""
        config = await self.get_config_by_id(config_id)
        if not config:
            return None

        if monthly_budget is not None:
            config.monthly_budget_usd = monthly_budget
        if config_json is not None:
            config.config_json = config_json

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def _deactivate_previous_configs(self, tenant_id: uuid.UUID):
        """Deactivate all previous active configs for tenant."""
        query = (
            select(BudgetConfig)
            .where(and_(BudgetConfig.tenant_id == tenant_id, BudgetConfig.is_active == True))
        )
        result = await self.db.execute(query)
        configs = result.scalars().all()

        for config in configs:
            config.is_active = False
            config.effective_until = datetime.utcnow()

        await self.db.commit()

    # ============================================
    # Cost Tracking Operations
    # ============================================

    async def track_cost(
        self,
        tenant_id: uuid.UUID,
        date_: date,
        service_name: str,
        service_category: str,
        cost_type: str,
        usage_count: int = 0,
        usage_amount: Decimal = Decimal("0"),
        estimated_cost_usd: Decimal = Decimal("0"),
        metadata: Optional[dict] = None,
    ) -> CostTracking:
        """Track cost for a service (upsert operation)."""
        # Check if record exists
        query = select(CostTracking).where(
            and_(
                CostTracking.tenant_id == tenant_id,
                CostTracking.date == date_,
                CostTracking.service_name == service_name,
                CostTracking.cost_type == cost_type,
            )
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing record
            existing.usage_count += usage_count
            existing.usage_amount += usage_amount
            existing.estimated_cost_usd += estimated_cost_usd
            if metadata:
                existing.metadata = {**(existing.metadata or {}), **metadata}
            cost_record = existing
        else:
            # Create new record
            cost_record = CostTracking(
                tenant_id=tenant_id,
                date=date_,
                service_name=service_name,
                service_category=service_category,
                cost_type=cost_type,
                usage_count=usage_count,
                usage_amount=usage_amount,
                estimated_cost_usd=estimated_cost_usd,
                metadata=metadata,
            )
            self.db.add(cost_record)

        await self.db.commit()
        await self.db.refresh(cost_record)
        return cost_record

    async def get_costs_by_date_range(
        self,
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date,
        service_name: Optional[str] = None,
        service_category: Optional[str] = None,
    ) -> list[CostTracking]:
        """Get cost tracking records for date range."""
        query = select(CostTracking).where(
            and_(
                CostTracking.tenant_id == tenant_id,
                CostTracking.date >= start_date,
                CostTracking.date <= end_date,
            )
        )

        if service_name:
            query = query.where(CostTracking.service_name == service_name)
        if service_category:
            query = query.where(CostTracking.service_category == service_category)

        query = query.order_by(desc(CostTracking.date))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_current_month_total(self, tenant_id: uuid.UUID) -> Decimal:
        """Get total estimated cost for current month."""
        today = date.today()
        month_start = date(today.year, today.month, 1)

        query = select(func.sum(CostTracking.estimated_cost_usd)).where(
            and_(
                CostTracking.tenant_id == tenant_id,
                CostTracking.date >= month_start,
                CostTracking.date <= today,
            )
        )
        result = await self.db.execute(query)
        total = result.scalar_one_or_none()
        return total or Decimal("0")

    async def get_current_month_by_category(
        self, tenant_id: uuid.UUID
    ) -> dict[str, Decimal]:
        """Get current month costs grouped by category."""
        today = date.today()
        month_start = date(today.year, today.month, 1)

        query = (
            select(
                CostTracking.service_category,
                func.sum(CostTracking.estimated_cost_usd).label("total_cost"),
            )
            .where(
                and_(
                    CostTracking.tenant_id == tenant_id,
                    CostTracking.date >= month_start,
                    CostTracking.date <= today,
                )
            )
            .group_by(CostTracking.service_category)
        )

        result = await self.db.execute(query)
        return {row.service_category: row.total_cost for row in result}

    async def get_top_services_by_cost(
        self, tenant_id: uuid.UUID, limit: int = 5
    ) -> list[dict]:
        """Get top services by cost for current month."""
        today = date.today()
        month_start = date(today.year, today.month, 1)

        query = (
            select(
                CostTracking.service_name,
                CostTracking.service_category,
                func.sum(CostTracking.estimated_cost_usd).label("total_cost"),
                func.sum(CostTracking.usage_count).label("total_usage"),
            )
            .where(
                and_(
                    CostTracking.tenant_id == tenant_id,
                    CostTracking.date >= month_start,
                    CostTracking.date <= today,
                )
            )
            .group_by(CostTracking.service_name, CostTracking.service_category)
            .order_by(desc("total_cost"))
            .limit(limit)
        )

        result = await self.db.execute(query)
        return [
            {
                "service_name": row.service_name,
                "service_category": row.service_category,
                "total_cost": float(row.total_cost),
                "total_usage": row.total_usage,
            }
            for row in result
        ]

    # ============================================
    # Budget Alert Operations
    # ============================================

    async def create_alert(
        self,
        tenant_id: uuid.UUID,
        alert_type: str,
        severity: str,
        message: str,
        current_spend: Optional[Decimal] = None,
        budget_limit: Optional[Decimal] = None,
        threshold_percent: Optional[Decimal] = None,
        details: Optional[dict] = None,
    ) -> BudgetAlert:
        """Create budget alert."""
        alert = BudgetAlert(
            tenant_id=tenant_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            current_spend_usd=current_spend,
            budget_limit_usd=budget_limit,
            threshold_percent=threshold_percent,
            details=details,
        )
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def get_unacknowledged_alerts(self, tenant_id: uuid.UUID) -> list[BudgetAlert]:
        """Get unacknowledged alerts for tenant."""
        query = (
            select(BudgetAlert)
            .where(
                and_(
                    BudgetAlert.tenant_id == tenant_id,
                    BudgetAlert.is_acknowledged == False,
                )
            )
            .order_by(desc(BudgetAlert.created_at))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def acknowledge_alert(
        self, alert_id: uuid.UUID, acknowledged_by: uuid.UUID
    ) -> Optional[BudgetAlert]:
        """Acknowledge an alert."""
        query = select(BudgetAlert).where(BudgetAlert.id == alert_id)
        result = await self.db.execute(query)
        alert = result.scalar_one_or_none()

        if alert:
            alert.is_acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(alert)

        return alert

    # ============================================
    # Service Quota Operations
    # ============================================

    async def get_quota(
        self, tenant_id: uuid.UUID, service_name: str, quota_type: str
    ) -> Optional[ServiceQuota]:
        """Get service quota."""
        query = select(ServiceQuota).where(
            and_(
                ServiceQuota.tenant_id == tenant_id,
                ServiceQuota.service_name == service_name,
                ServiceQuota.quota_type == quota_type,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def increment_quota_usage(
        self, tenant_id: uuid.UUID, service_name: str, quota_type: str, increment: int = 1
    ) -> Optional[ServiceQuota]:
        """Increment quota usage."""
        quota = await self.get_quota(tenant_id, service_name, quota_type)
        if not quota:
            return None

        quota.current_usage += increment
        await self.db.commit()
        await self.db.refresh(quota)
        return quota

    async def reset_quota(
        self, tenant_id: uuid.UUID, service_name: str, quota_type: str
    ) -> Optional[ServiceQuota]:
        """Reset quota usage."""
        quota = await self.get_quota(tenant_id, service_name, quota_type)
        if not quota:
            return None

        quota.current_usage = 0
        quota.last_reset = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(quota)
        return quota

    async def get_all_quotas(self, tenant_id: uuid.UUID) -> list[ServiceQuota]:
        """Get all quotas for tenant."""
        query = (
            select(ServiceQuota)
            .where(and_(ServiceQuota.tenant_id == tenant_id, ServiceQuota.is_active == True))
            .order_by(ServiceQuota.service_name)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ============================================
    # Daily Report Operations
    # ============================================

    async def create_daily_report(
        self, tenant_id: uuid.UUID, report_date: date, report_data: dict
    ) -> CostReportDaily:
        """Create or update daily cost report."""
        # Check if report exists
        query = select(CostReportDaily).where(
            and_(
                CostReportDaily.tenant_id == tenant_id,
                CostReportDaily.report_date == report_date,
            )
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            for key, value in report_data.items():
                setattr(existing, key, value)
            report = existing
        else:
            # Create new
            report = CostReportDaily(
                tenant_id=tenant_id, report_date=report_date, **report_data
            )
            self.db.add(report)

        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_daily_report(
        self, tenant_id: uuid.UUID, report_date: date
    ) -> Optional[CostReportDaily]:
        """Get daily cost report."""
        query = select(CostReportDaily).where(
            and_(
                CostReportDaily.tenant_id == tenant_id,
                CostReportDaily.report_date == report_date,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_reports_by_range(
        self, tenant_id: uuid.UUID, start_date: date, end_date: date
    ) -> list[CostReportDaily]:
        """Get daily reports for date range."""
        query = (
            select(CostReportDaily)
            .where(
                and_(
                    CostReportDaily.tenant_id == tenant_id,
                    CostReportDaily.report_date >= start_date,
                    CostReportDaily.report_date <= end_date,
                )
            )
            .order_by(desc(CostReportDaily.report_date))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
