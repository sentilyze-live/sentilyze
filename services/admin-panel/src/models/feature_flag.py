"""Feature flag database model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base, TimestampMixin


class FeatureFlag(Base, TimestampMixin):
    """Feature flag model for cost control."""

    __tablename__ = "feature_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    cost_impact_daily_usd: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    # Who last updated this flag
    updated_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("admin_users.id"), nullable=True
    )
    
    # Relationships
    updater: Mapped[Optional["User"]] = relationship("User", foreign_keys=[updated_by])

    def __repr__(self) -> str:
        return f"<FeatureFlag(key={self.key}, enabled={self.enabled})>"

    @property
    def daily_cost(self) -> float:
        """Get daily cost if enabled, otherwise 0."""
        return float(self.cost_impact_daily_usd or 0) if self.enabled else 0.0

    @property
    def monthly_estimate(self) -> float:
        """Get monthly cost estimate."""
        return self.daily_cost * 30


class FeatureFlagAuditLog(Base, TimestampMixin):
    """Audit log for feature flag changes."""

    __tablename__ = "feature_flag_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flag_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # CREATE, UPDATE, DELETE
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("admin_users.id"), nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<FeatureFlagAuditLog(flag_key={self.flag_key}, action={self.action})>"
