"""Database base models and utilities."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class TimestampMixin:
    """Mixin for timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin for UUID primary key."""

    @declared_attr
    def id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def update_updated_at(mapper: Any, connection: Any, target: Any) -> None:
    """Update updated_at timestamp on model update."""
    target.updated_at = datetime.utcnow()
