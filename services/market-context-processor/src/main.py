"""Market Context Processor main application.

FastAPI application providing market analysis endpoints for:
- Regime detection (bull/bear/neutral)
- Anomaly detection (price/sentiment/volume)
- Correlation analysis between assets
- Granger causality testing (sentiment -> price)
"""

import asyncio
import base64
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sentilyze_core import (
    BigQueryClient,
    PubSubClient,
    PubSubMessage,
    configure_logging,
    get_logger,
)
from sentilyze_core.exceptions import RateLimitError

from .config import (
    AnomalySeverity,
    CorrelationStrength,
    MarketRegime,
    TrendDirection,
    VolatilityRegime,
    get_market_context_settings,
)
from .analyzer import AnomalyDetector, RegimeDetector
from .correlation import CorrelationAnalyzer
from .publisher import MarketContextPublisher

logger = get_logger(__name__)
settings = get_market_context_settings()

SERVICE_NAME = "market-context-processor"
SERVICE_VERSION = "3.0.0"

# Global instances
regime_detector: RegimeDetector | None = None
anomaly_detector: AnomalyDetector | None = None
correlation_analyzer: CorrelationAnalyzer | None = None
publisher: MarketContextPublisher | None = None
pubsub_client: PubSubClient | None = None
bigquery_client: BigQueryClient | None = None


def _parse_pubsub_push(envelope: dict[str, Any]) -> PubSubMessage:
    """Parse Pub/Sub push delivery JSON into PubSubMessage."""
    if "message" not in envelope:
        raise ValueError("Missing 'message' in Pub/Sub push envelope")

    msg = envelope["message"] or {}
    data_b64 = msg.get("data") or ""
    try:
        raw_bytes = base64.b64decode(data_b64)
    except Exception as e:
        raise ValueError(f"Invalid base64 data: {e}") from e

    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid JSON message data: {e}") from e

    return PubSubMessage(
        data=payload,
        message_id=msg.get("messageId"),
        publish_time=msg.get("publishTime"),
        attributes=msg.get("attributes") or {},
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    global regime_detector, anomaly_detector, correlation_analyzer, publisher, pubsub_client, bigquery_client

    configure_logging(
        log_level=settings.log_level,
        service_name=SERVICE_NAME,
        environment=settings.environment,
    )
    logger.info("Starting market context processor service")

    # Initialize clients
    pubsub_client = PubSubClient()
    bigquery_client = BigQueryClient()
    publisher = MarketContextPublisher(pubsub_client)
    await publisher.initialize()

    # Initialize analyzers
    if settings.enable_regime_detection:
        regime_detector = RegimeDetector()
    if settings.enable_anomaly_detection:
        anomaly_detector = AnomalyDetector()
    if settings.enable_correlation_analysis:
        correlation_analyzer = CorrelationAnalyzer()

    logger.info(
        "Service initialized",
        regime_enabled=settings.enable_regime_detection,
        anomaly_enabled=settings.enable_anomaly_detection,
        correlation_enabled=settings.enable_correlation_analysis,
    )

    yield

    # Shutdown
    logger.info("Shutting down market context processor service")

    if publisher:
        await publisher.close()
    if pubsub_client:
        pubsub_client.close()
    if bigquery_client:
        bigquery_client.close()


app = FastAPI(
    title="Sentilyze Market Context Processor",
    description="Market analysis service for regime detection, anomaly detection, and correlation analysis",
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


# Pydantic Models for Request/Response
from pydantic import BaseModel, Field


class RegimeAnalysisRequest(BaseModel):
    prices: list[float] = Field(..., description="List of closing prices (oldest first)", min_length=50)
    volumes: list[float] | None = Field(None, description="Optional volume data")
    symbol: str = Field(default="UNKNOWN", description="Trading symbol")
    market_type: str = Field(default="generic", description="Market type (crypto/gold/generic)")


class RegimeAnalysisResponse(BaseModel):
    symbol: str
    market_type: str
    regime: str
    trend_direction: str
    volatility_regime: str
    confidence: float
    rsi_14: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_20: float | None = None
    price: float | None = None
    support_level: float | None = None
    resistance_level: float | None = None
    trend_strength: float | None = None
    volume_trend: str | None = None
    timestamp: str


class AnomalyAnalysisRequest(BaseModel):
    prices: list[float] = Field(..., description="List of prices (oldest first)", min_length=20)
    sentiments: list[float] | None = Field(None, description="Optional sentiment scores")
    volumes: list[float] | None = Field(None, description="Optional volume data")
    timestamps: list[str] | None = Field(None, description="Optional timestamps")
    symbol: str = Field(default="UNKNOWN", description="Trading symbol")
    market_type: str = Field(default="generic", description="Market type (crypto/gold/generic)")
    support_level: float | None = Field(None, description="Support level for breakout detection")
    resistance_level: float | None = Field(None, description="Resistance level for breakout detection")


class AnomalyDetectionResponse(BaseModel):
    anomaly_type: str
    severity: str
    symbol: str
    market_type: str
    timestamp: str
    description: str
    price_at_detection: float
    price_change_percent: float
    sentiment_score: float | None = None
    expected_sentiment: float | None = None
    volume_ratio: float | None = None
    z_score: float | None = None
    recommendation: str | None = None


class AnomalyAnalysisResponse(BaseModel):
    anomalies: list[AnomalyDetectionResponse]
    total_anomalies: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int


class CorrelationAnalysisRequest(BaseModel):
    primary_prices: list[float] = Field(..., description="Primary asset prices", min_length=30)
    secondary_prices: list[float] = Field(..., description="Secondary asset prices", min_length=30)
    primary_symbol: str = Field(default="PRIMARY", description="Primary symbol")
    secondary_symbol: str = Field(default="SECONDARY", description="Secondary symbol")
    period_days: int = Field(default=30, ge=7, le=365, description="Analysis period in days")
    calculate_lag: bool = Field(default=True, description="Calculate lead/lag relationship")
    market_type: str = Field(default="generic", description="Market type (crypto/gold/generic)")


class CorrelationAnalysisResponse(BaseModel):
    primary_symbol: str
    secondary_symbol: str
    market_type: str
    correlation: float
    correlation_strength: str
    period_days: int
    sample_size: int
    interpretation: str
    lag_analysis: dict | None = None
    rolling_correlations: list[dict] | None = None
    timestamp: str


class GrangerAnalysisRequest(BaseModel):
    prices: list[float] = Field(..., description="Price series", min_length=30)
    sentiments: list[float] = Field(..., description="Sentiment score series", min_length=30)
    symbol: str = Field(default="UNKNOWN", description="Trading symbol")
    market_type: str = Field(default="generic", description="Market type (crypto/gold/generic)")
    max_lag_hours: int = Field(default=24, ge=1, le=72, description="Maximum lag to test in hours")


class GrangerAnalysisResponse(BaseModel):
    cause_variable: str
    effect_variable: str
    market_type: str
    lag_hours: int
    f_statistic: float
    p_value: float
    is_causal: bool
    interpretation: str
    timestamp: str


# API Endpoints

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
        "regime_detector": regime_detector is not None,
        "anomaly_detector": anomaly_detector is not None,
        "correlation_analyzer": correlation_analyzer is not None,
        "publisher": publisher is not None,
    }

    all_ready = all(checks.values())

    if not all_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not ready", "checks": checks},
        )

    return {"status": "ready", "checks": checks}


@app.post("/analyze/regime", response_model=RegimeAnalysisResponse, tags=["analysis"])
async def analyze_regime(request: RegimeAnalysisRequest):
    """Detect market regime from price data."""
    if not regime_detector:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Regime detector not initialized",
        )

    try:
        result = await regime_detector.detect_regime(
            prices=request.prices,
            volumes=request.volumes,
            symbol=request.symbol,
            market_type=request.market_type,
        )

        return RegimeAnalysisResponse(
            symbol=result.symbol,
            market_type=result.market_type,
            regime=result.regime.value,
            trend_direction=result.trend_direction.value,
            volatility_regime=result.volatility_regime.value,
            confidence=result.confidence,
            rsi_14=result.rsi_14,
            sma_50=result.sma_50,
            sma_200=result.sma_200,
            ema_20=result.ema_20,
            price=result.price,
            support_level=result.support_level,
            resistance_level=result.resistance_level,
            trend_strength=result.trend_strength,
            volume_trend=result.volume_trend,
            timestamp=result.timestamp.isoformat(),
        )
    except Exception as e:
        logger.error("Regime detection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Regime detection failed: {str(e)}",
        )


@app.post("/analyze/anomalies", response_model=AnomalyAnalysisResponse, tags=["analysis"])
async def analyze_anomalies(request: AnomalyAnalysisRequest):
    """Detect anomalies in market data."""
    if not anomaly_detector:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anomaly detector not initialized",
        )

    try:
        # Parse timestamps if provided
        parsed_timestamps = None
        if request.timestamps:
            parsed_timestamps = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts in request.timestamps]

        anomalies = await anomaly_detector.detect_anomalies(
            prices=request.prices,
            sentiments=request.sentiments,
            volumes=request.volumes,
            timestamps=parsed_timestamps,
            symbol=request.symbol,
            support_level=request.support_level,
            resistance_level=request.resistance_level,
            market_type=request.market_type,
        )

        # Count by severity
        critical_count = sum(1 for a in anomalies if a.severity == AnomalySeverity.CRITICAL)
        high_count = sum(1 for a in anomalies if a.severity == AnomalySeverity.HIGH)
        medium_count = sum(1 for a in anomalies if a.severity == AnomalySeverity.MEDIUM)
        low_count = sum(1 for a in anomalies if a.severity == AnomalySeverity.LOW)

        # Convert to response model
        anomaly_responses = [
            AnomalyDetectionResponse(
                anomaly_type=a.anomaly_type.value,
                severity=a.severity.value,
                symbol=a.symbol,
                market_type=a.market_type,
                timestamp=a.timestamp.isoformat(),
                description=a.description,
                price_at_detection=a.price_at_detection,
                price_change_percent=a.price_change_percent,
                sentiment_score=a.sentiment_score,
                expected_sentiment=a.expected_sentiment,
                volume_ratio=a.volume_ratio,
                z_score=a.z_score,
                recommendation=a.recommendation,
            )
            for a in anomalies
        ]

        return AnomalyAnalysisResponse(
            anomalies=anomaly_responses,
            total_anomalies=len(anomalies),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
        )
    except Exception as e:
        logger.error("Anomaly detection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly detection failed: {str(e)}",
        )


@app.post("/analyze/correlation", response_model=CorrelationAnalysisResponse, tags=["analysis"])
async def analyze_correlation(request: CorrelationAnalysisRequest):
    """Calculate correlation between two assets."""
    if not correlation_analyzer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Correlation analyzer not initialized",
        )

    if len(request.primary_prices) != len(request.secondary_prices):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price series must have the same length",
        )

    try:
        result = await correlation_analyzer.calculate_correlation(
            primary_prices=request.primary_prices,
            secondary_prices=request.secondary_prices,
            primary_symbol=request.primary_symbol,
            secondary_symbol=request.secondary_symbol,
            period_days=request.period_days,
            calculate_lag=request.calculate_lag,
            market_type=request.market_type,
        )

        return CorrelationAnalysisResponse(
            primary_symbol=result.primary_symbol,
            secondary_symbol=result.secondary_symbol,
            market_type=result.market_type,
            correlation=result.correlation,
            correlation_strength=result.correlation_strength.value,
            period_days=result.period_days,
            sample_size=result.sample_size,
            interpretation=result.interpretation,
            lag_analysis=result.lag_analysis,
            rolling_correlations=result.rolling_correlations,
            timestamp=result.timestamp.isoformat(),
        )
    except Exception as e:
        logger.error("Correlation calculation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Correlation calculation failed: {str(e)}",
        )


@app.post("/analyze/granger", response_model=GrangerAnalysisResponse, tags=["analysis"])
async def analyze_granger_causality(request: GrangerAnalysisRequest):
    """Test Granger causality between sentiment and price."""
    if not correlation_analyzer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Correlation analyzer not initialized",
        )

    if len(request.prices) != len(request.sentiments):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price and sentiment series must have the same length",
        )

    try:
        result = await correlation_analyzer.analyze_sentiment_price_causality(
            prices=request.prices,
            sentiments=request.sentiments,
            symbol=request.symbol,
            max_lag_hours=request.max_lag_hours,
            market_type=request.market_type,
        )

        return GrangerAnalysisResponse(
            cause_variable=result.cause_variable,
            effect_variable=result.effect_variable,
            market_type=result.market_type,
            lag_hours=result.lag_hours,
            f_statistic=result.f_statistic,
            p_value=result.p_value,
            is_causal=result.is_causal,
            interpretation=result.interpretation,
            timestamp=result.timestamp.isoformat(),
        )
    except Exception as e:
        logger.error("Granger causality test failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Granger causality test failed: {str(e)}",
        )


async def _process_processed_sentiment(message: PubSubMessage) -> None:
    """Process a processed sentiment message from Pub/Sub.
    
    Extracts market context from sentiment data and publishes to market-context topic.
    """
    from uuid import uuid4
    from .models import MarketContextEvent
    
    logger.info(
        "Processing processed sentiment message",
        message_id=message.message_id,
    )
    
    try:
        data = message.data
        if not isinstance(data, dict):
            logger.error("Invalid message data type", type=type(data).__name__)
            return
            
        # Extract sentiment info
        sentiment_score = data.get("sentiment", {}).get("score", 0.0)
        sentiment_label = data.get("sentiment", {}).get("label", "neutral")
        symbols = data.get("symbols", [])
        source = data.get("source", "unknown")
        event_id = data.get("event_id")
        
        if not symbols:
            logger.warning("No symbols in sentiment message, skipping")
            return
            
        symbol = symbols[0]
        market_type = data.get("market_type", "generic")
        
        # Create market context event
        context_event = MarketContextEvent(
            context_id=uuid4(),
            event_id=event_id,
            symbol=symbol,
            market_type=market_type,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            source=source,
            timestamp=datetime.utcnow(),
        )
        
        # Publish to market-context topic
        if publisher:
            await publisher.publish_market_context(context_event)
            logger.info(
                "Published market context",
                symbol=symbol,
                sentiment_score=sentiment_score,
                context_id=str(context_event.context_id),
            )
        
        # Save to BigQuery
        if bigquery_client:
            await bigquery_client.insert_market_context(context_event.model_dump(mode="json"))
            
    except Exception as e:
        logger.error("Failed to process sentiment message", error=str(e))
        raise


@app.post("/pubsub-push/processed-sentiment", tags=["pubsub"])
async def pubsub_push_processed_sentiment(request: Request) -> dict[str, str]:
    """Pub/Sub push endpoint for processed-sentiment subscription."""
    try:
        envelope = await request.json()
        message = _parse_pubsub_push(envelope)
        await _process_processed_sentiment(message)
        return {"status": "ok"}
    except RateLimitError as e:
        logger.warning("Backpressure/rate limit", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "rate_limited", "retry_after": e.retry_after},
            headers={"Retry-After": str(e.retry_after)},
        )
    except Exception as e:
        logger.error("Pub/Sub push processing failed", error=str(e))
        raise HTTPException(status_code=500, detail="processing failed")


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
