"""Unified sentiment analysis API routes with real BigQuery data."""

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import get_optional_user, get_current_user
from ..config import get_settings
from ..logging import get_logger
from ..bigquery_helper import get_bq_helper

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter(prefix="/sentiment", tags=["sentiment"])


@router.get("/symbol/{symbol}")
async def get_sentiment_by_symbol(
    symbol: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    source: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get sentiment data for a specific symbol.
    
    Works for both crypto and gold symbols.
    
    Args:
        symbol: Symbol (e.g., BTC, ETH, XAUUSD)
        start: Start time (defaults to 24h ago)
        end: End time (defaults to now)
        source: Filter by data source
        limit: Number of results to return
        offset: Pagination offset
        user: Current user (optional)
        
    Returns:
        Paginated sentiment data
    """
    if not end:
        end = datetime.utcnow()
    if not start:
        start = end - timedelta(days=1)
    
    symbol = symbol.upper()
    
    try:
        bq = get_bq_helper()
        result = await bq.get_sentiment_by_symbol(
            symbol=symbol,
            start=start,
            end=end,
            source=source,
            limit=limit,
            offset=offset,
        )
        
        result["timestamp"] = datetime.utcnow().isoformat()
        return result
        
    except Exception as e:
        logger.error("Failed to fetch sentiment data", error=str(e), symbol=symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch sentiment data",
        )


@router.get("/symbol/{symbol}/aggregate")
async def get_sentiment_aggregation(
    symbol: str,
    interval: str = Query(default="HOUR", pattern="^(HOUR|DAY|WEEK)$"),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get aggregated sentiment data for a symbol.
    
    Args:
        symbol: Symbol to analyze
        interval: Aggregation interval (HOUR, DAY, WEEK)
        start: Start time
        end: End time
        user: Current user (optional)
        
    Returns:
        Aggregated sentiment data
    """
    if not end:
        end = datetime.utcnow()
    if not start:
        start = end - timedelta(days=7)
    
    symbol = symbol.upper()
    
    try:
        bq = get_bq_helper()
        result = await bq.get_sentiment_aggregation(
            symbol=symbol,
            start=start,
            end=end,
            interval=interval,
        )
        
        result["timestamp"] = datetime.utcnow().isoformat()
        return result
        
    except Exception as e:
        logger.error("Failed to fetch aggregation", error=str(e), symbol=symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch aggregation data",
        )


@router.get("/symbol/{symbol}/latest")
async def get_latest_sentiment(
    symbol: str,
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get latest sentiment for a symbol.
    
    Args:
        symbol: Symbol to query
        user: Current user (optional)
        
    Returns:
        Latest sentiment data
    """
    symbol = symbol.upper()
    
    try:
        bq = get_bq_helper()
        end = datetime.utcnow()
        start = end - timedelta(hours=1)
        
        result = await bq.get_sentiment_by_symbol(
            symbol=symbol,
            start=start,
            end=end,
            limit=1,
        )
        
        if result["items"]:
            latest = result["items"][0]
            return {
                "symbol": symbol,
                "sentiment": latest["sentiment"]["label"],
                "score": latest["sentiment"]["score"],
                "confidence": latest["sentiment"]["confidence"],
                "timestamp": latest["timestamp"],
                "source": latest["source"],
            }
        else:
            # No data found
            return {
                "symbol": symbol,
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "none",
                "message": "No sentiment data available for this symbol",
            }
        
    except Exception as e:
        logger.error("Failed to fetch latest sentiment", error=str(e), symbol=symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch latest sentiment",
        )


@router.get("/trending")
async def get_trending_symbols(
    limit: int = Query(default=10, ge=1, le=50),
    hours: int = Query(default=24, ge=1, le=168, description="Time window in hours"),
    asset_type: str = Query(default="all", pattern="^(all|crypto|gold)$"),
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get trending symbols based on sentiment volume.
    
    Queries for symbols with the most mentions in the last N hours.
    
    Args:
        limit: Number of symbols to return
        hours: Time window to analyze (default: 24h)
        asset_type: Filter by asset type (all, crypto, gold)
        user: Current user (optional)
        
    Returns:
        List of trending symbols
    """
    try:
        bq = get_bq_helper()
        result = await bq.get_trending_symbols(
            hours=hours,
            limit=limit,
            asset_type=asset_type,
        )
        
        result["timestamp"] = datetime.utcnow().isoformat()
        return result
        
    except Exception as e:
        logger.error("Failed to fetch trending symbols", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch trending symbols",
        )


@router.get("/market-sentiment")
async def get_overall_market_sentiment(
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get overall market sentiment across all tracked assets.
    
    Args:
        user: Current user (optional)
        
    Returns:
        Overall market sentiment
    """
    try:
        bq = get_bq_helper()
        result = await bq.get_market_sentiment_overview()
        
        result["timestamp"] = datetime.utcnow().isoformat()
        return result
        
    except Exception as e:
        logger.error("Failed to fetch market sentiment", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch market sentiment",
        )
