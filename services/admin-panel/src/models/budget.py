"""Budget management and cost tracking models."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..db.base import Base, TimestampMixin, UUIDMixin


class BudgetConfig(Base, UUIDMixin, TimestampMixin):
    """Budget configuration and tier management."""

    __tablename__ = "budget_configs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, default=uuid.uuid4
    )
    tier_name: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    monthly_budget_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    effective_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "tier_name IN ('minimal', 'basic', 'standard', 'premium', 'custom')",
            name="check_valid_tier_name",
        ),
        CheckConstraint(
            "monthly_budget_usd >= 0",
            name="check_positive_budget",
        ),
        UniqueConstraint(
            "tenant_id",
            "is_active",
            name="unique_active_config_per_tenant",
            postgresql_where="is_active = true",
        ),
    )

    def __repr__(self) -> str:
        return f"<BudgetConfig(tier={self.tier_name}, budget=${self.monthly_budget_usd}, active={self.is_active})>"


class CostTracking(Base, UUIDMixin):
    """Daily cost tracking per service."""

    __tablename__ = "cost_tracking"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    service_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    service_category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    cost_type: Mapped[str] = mapped_column(String(30), nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    usage_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0)
    actual_cost_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "service_category IN ('api', 'compute', 'storage', 'ml', 'network', 'other')",
            name="check_valid_service_category",
        ),
        CheckConstraint(
            "cost_type IN ('api_call', 'compute_time', 'storage_bytes', 'ml_request', 'egress', 'query_bytes', 'message_count')",
            name="check_valid_cost_type",
        ),
        CheckConstraint("usage_count >= 0", name="check_positive_usage_count"),
        CheckConstraint("usage_amount >= 0", name="check_positive_usage_amount"),
        CheckConstraint("estimated_cost_usd >= 0", name="check_positive_estimated_cost"),
        UniqueConstraint(
            "tenant_id",
            "date",
            "service_name",
            "cost_type",
            name="unique_cost_per_day_service_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<CostTracking(service={self.service_name}, date={self.date}, cost=${self.estimated_cost_usd})>"


class BudgetAlert(Base, UUIDMixin):
    """Budget alerts and warnings."""

    __tablename__ = "budget_alerts"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    threshold_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    current_spend_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    budget_limit_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    acknowledged_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('budget_warning', 'budget_exceeded', 'service_expensive', 'quota_reached', 'anomaly_detected')",
            name="check_valid_alert_type",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="check_valid_severity",
        ),
    )

    def __repr__(self) -> str:
        return f"<BudgetAlert(type={self.alert_type}, severity={self.severity}, acknowledged={self.is_acknowledged})>"


class ServiceQuota(Base, UUIDMixin):
    """Service usage quotas and limits."""

    __tablename__ = "service_quotas"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    service_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    quota_type: Mapped[str] = mapped_column(String(30), nullable=False)
    quota_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    current_usage: Mapped[int] = mapped_column(Integer, default=0)
    reset_period: Mapped[str] = mapped_column(String(20), nullable=False)
    last_reset: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    next_reset: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "quota_type IN ('daily_requests', 'monthly_requests', 'concurrent_connections', 'storage_gb', 'compute_hours')",
            name="check_valid_quota_type",
        ),
        CheckConstraint("quota_limit > 0", name="check_positive_quota_limit"),
        CheckConstraint("current_usage >= 0", name="check_positive_current_usage"),
        CheckConstraint(
            "reset_period IN ('hourly', 'daily', 'monthly', 'never')",
            name="check_valid_reset_period",
        ),
        UniqueConstraint(
            "tenant_id",
            "service_name",
            "quota_type",
            name="unique_quota_per_service_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<ServiceQuota(service={self.service_name}, type={self.quota_type}, usage={self.current_usage}/{self.quota_limit})>"

    @property
    def usage_percent(self) -> float:
        """Calculate quota usage percentage."""
        if self.quota_limit == 0:
            return 0.0
        return round((self.current_usage / self.quota_limit) * 100, 2)

    @property
    def is_exceeded(self) -> bool:
        """Check if quota is exceeded."""
        return self.current_usage >= self.quota_limit

    @property
    def is_near_limit(self, threshold: float = 80.0) -> bool:
        """Check if quota usage is near limit (default 80%)."""
        return self.usage_percent >= threshold


class CostReportDaily(Base, UUIDMixin):
    """Pre-aggregated daily cost reports."""

    __tablename__ = "cost_reports_daily"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    api_costs_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    compute_costs_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    storage_costs_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    ml_costs_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    network_costs_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    top_services: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    recommendations: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("total_cost_usd >= 0", name="check_positive_total_cost"),
        CheckConstraint("api_costs_usd >= 0", name="check_positive_api_costs"),
        CheckConstraint("compute_costs_usd >= 0", name="check_positive_compute_costs"),
        CheckConstraint("storage_costs_usd >= 0", name="check_positive_storage_costs"),
        CheckConstraint("ml_costs_usd >= 0", name="check_positive_ml_costs"),
        CheckConstraint("network_costs_usd >= 0", name="check_positive_network_costs"),
        UniqueConstraint(
            "tenant_id",
            "report_date",
            name="unique_report_per_tenant_date",
        ),
    )

    def __repr__(self) -> str:
        return f"<CostReportDaily(date={self.report_date}, total=${self.total_cost_usd})>"
