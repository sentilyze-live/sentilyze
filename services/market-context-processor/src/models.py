"""Data models for market context processor."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MarketContextEvent(BaseModel):
    """Market context event generated from processed sentiment."""
    
    context_id: UUID = Field(..., description="Unique context event ID")
    event_id: Any = Field(..., description="Source event ID")
    symbol: str = Field(..., description="Trading symbol")
    market_type: str = Field(default="generic", description="Market type (crypto/gold/generic)")
    sentiment_score: float = Field(..., description="Sentiment score (-1 to 1)")
    sentiment_label: str = Field(default="neutral", description="Sentiment label")
    source: str = Field(default="unknown", description="Data source")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }
