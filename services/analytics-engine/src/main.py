"""Analytics Engine main application."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sentilyze_core import BigQueryClient, configure_logging, get_logger

from .aggregator import AnalyticsAggregator, MaterializationWindow
from .config import get_analytics_settings

logger = get_logger(__name__)
settings = get_analytics_settings()

SERVICE_NAME = "analytics-engine"
SERVICE_VERSION = "3.0.0"

# Global instances
aggregator: AnalyticsAggregator | None = None
bigquery_client: BigQueryClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    global aggregator, bigquery_client

    configure_logging(
        log_level=settings.log_level,
        service_name=SERVICE_NAME,
        environment=settings.environment,
    )
    logger.info("Starting analytics engine")

    # Initialize clients
    bigquery_client = BigQueryClient()
    aggregator = AnalyticsAggregator(bigquery_client)

    logger.info(
        "Service initialized",
        materialization_enabled=settings.enable_materialization,
        correlation_enabled=settings.enable_correlation_analysis,
    )

    yield

    # Shutdown
    logger.info("Shutting down analytics engine")

    if bigquery_client:
        bigquery_client.close()


app = FastAPI(
    title="Sentilyze Analytics Engine",
    description="Statistical analysis, aggregation, and insights generation service",
    version=SERVICE_VERSION,
    lifespan=lifespan,
)

# CORS Configuration - Read from environment or use production defaults
import os
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://sentilyze.live,https://www.sentilyze.live,https://admin.sentilyze.live").split(",")
if os.getenv("ENVIRONMENT") == "development":
    CORS_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
    }


@app.get("/ready", tags=["health"])
async def readiness_check() -> dict:
    """Readiness check endpoint."""
    checks = {
        "aggregator": aggregator is not None,
        "bigquery": bigquery_client is not None,
    }

    all_ready = all(checks.values())

    if not all_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not ready", "checks": checks},
        )

    return {"status": "ready", "checks": checks}


@app.post("/jobs/materialize-analytics", tags=["jobs"])
async def materialize_analytics(
    hours: int = Query(default=24, ge=1, le=168, description="Window size (hours)"),
    also_last_1h: bool = Query(default=True, description="Also materialize the last 1 hour window"),
) -> dict:
    """Materialize aggregated metrics into analytics dataset."""
    if not aggregator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Aggregator not initialized",
        )

    try:
        now = datetime.now(timezone.utc)
        windows: list[MaterializationWindow] = []

        if also_last_1h:
            windows.append(MaterializationWindow(window_start=now - timedelta(hours=1), window_end=now))

        windows.append(MaterializationWindow(window_start=now - timedelta(hours=hours), window_end=now))

        results = []
        total_rows_written = 0

        for w in windows:
            metrics = await aggregator.compute_metrics(w)
            rows_written = await aggregator.write_metrics(aggregator.bigquery, w, metrics, created_at=now)
            total_rows_written += rows_written
            results.append(
                {
                    "windowHours": round((w.window_end - w.window_start).total_seconds() / 3600.0, 4),
                    "metrics": metrics,
                    "rowsWritten": rows_written,
                }
            )

        return {
            "status": "ok",
            "windows": results,
            "totalRowsWritten": total_rows_written,
        }

    except Exception as e:
        logger.error("Analytics materialization failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Materialization failed: {str(e)}",
        )


@app.get("/sentiment/trend/{symbol}", tags=["sentiment"])
async def get_sentiment_trend(
    symbol: str,
    days: int = Query(default=7, ge=1, le=90, description="Number of days"),
):
    """Get sentiment trend for a symbol."""
    if not aggregator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Aggregator not initialized",
        )

    try:
        trend = await aggregator.get_sentiment_trend(symbol.upper(), days)
        return {
            "symbol": symbol.upper(),
            "days": days,
            "trend": trend,
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error("Sentiment trend failed", symbol=symbol, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sentiment trend: {str(e)}",
        )


@app.get("/sentiment/compare", tags=["sentiment"])
async def compare_sentiment(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    days: int = Query(default=7, ge=1, le=30, description="Number of days"),
):
    """Compare sentiment across multiple symbols."""
    if not aggregator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Aggregator not initialized",
        )

    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        comparison = await aggregator.get_market_comparison(symbol_list, days)
        return comparison
    except Exception as e:
        logger.error("Sentiment comparison failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare sentiment: {str(e)}",
        )


@app.get("/correlation/{symbol}", tags=["correlation"])
async def get_correlation(
    symbol: str,
    lag: int = Query(default=6, ge=0, le=48, description="Lag in hours"),
    days: int = Query(default=30, ge=7, le=365, description="Days of data"),
):
    """Get sentiment-price correlation (placeholder implementation)."""
    return {
        "symbol": symbol.upper(),
        "lag_hours": lag,
        "correlation": 0.65,
        "p_value": 0.001,
        "significant": True,
        "note": "Full correlation analysis requires price data integration",
    }


@app.get("/status", tags=["status"])
async def get_status() -> dict:
    """Get service status."""
    return {
        "service": SERVICE_NAME,
        "materialization_enabled": settings.enable_materialization,
        "correlation_enabled": settings.enable_correlation_analysis,
        "granger_enabled": settings.enable_granger_causality,
        "aggregator_ready": aggregator is not None,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
    )
