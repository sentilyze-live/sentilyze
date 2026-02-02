"""Prediction Engine main application."""

import asyncio
import base64
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from sentilyze_core import (
    BigQueryClient,
    PubSubClient,
    PubSubMessage,
    configure_logging,
    get_logger,
)

from .config import (
    ConfidenceLevel,
    PredictionDirection,
    PredictionType,
    get_prediction_settings,
)
from .models import PredictionResult, TechnicalIndicators
from .predictor import PredictionEngine
from .publisher import PredictionPublisher

logger = get_logger(__name__)
settings = get_prediction_settings()

SERVICE_NAME = "prediction-engine"
SERVICE_VERSION = "3.0.0"

# Global instances
prediction_engine: PredictionEngine | None = None
publisher: PredictionPublisher | None = None
pubsub_client: PubSubClient | None = None
bigquery_client: BigQueryClient | None = None


# Pydantic Models
class GeneratePredictionRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    market_type: str = Field(default="generic", description="Market type (crypto/gold/generic)")
    current_price: float = Field(..., description="Current price")
    prices: list[float] = Field(..., description="Price history (oldest first)", min_length=50)
    sentiment_score: float = Field(default=0.0, description="Current sentiment score (-1 to 1)")
    prediction_type: str = Field(default="1h", description="Prediction timeframe")


class GeneratePredictionResponse(BaseModel):
    prediction_id: str
    symbol: str
    market_type: str
    prediction_type: str
    current_price: float
    predicted_price: float
    predicted_direction: str
    confidence_score: int
    confidence_level: str
    technical_indicators: dict
    sentiment_score: float
    reasoning: str
    created_at: str


class BatchPredictionRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    market_type: str = Field(default="generic", description="Market type")
    current_price: float = Field(..., description="Current price")
    prices: list[float] = Field(..., description="Price history", min_length=50)
    sentiment_score: float = Field(default=0.0, description="Sentiment score")


class BatchPredictionResponse(BaseModel):
    symbol: str
    market_type: str
    predictions: list[dict]
    current_price: float


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    global prediction_engine, publisher, pubsub_client, bigquery_client

    configure_logging(
        log_level=settings.log_level,
        service_name=SERVICE_NAME,
        environment=settings.environment,
    )
    logger.info("Starting prediction engine service")

    # Initialize clients
    pubsub_client = PubSubClient()
    bigquery_client = BigQueryClient()
    publisher = PredictionPublisher(pubsub_client)
    await publisher.initialize()

    # Initialize engine
    prediction_engine = PredictionEngine()

    logger.info(
        "Service initialized",
        ml_enabled=settings.enable_ml_predictions,
        technical_enabled=settings.enable_technical_analysis,
    )

    yield

    # Shutdown
    logger.info("Shutting down prediction engine service")

    if publisher:
        await publisher.close()
    if pubsub_client:
        pubsub_client.close()
    if bigquery_client:
        bigquery_client.close()


app = FastAPI(
    title="Sentilyze Prediction Engine",
    description="Price prediction service with technical analysis and ML for crypto and gold markets",
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
        "prediction_engine": prediction_engine is not None,
        "publisher": publisher is not None,
        "pubsub": pubsub_client is not None,
    }

    all_ready = all(checks.values())

    if not all_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not ready", "checks": checks},
        )

    return {"status": "ready", "checks": checks}


@app.post("/predict", response_model=GeneratePredictionResponse, tags=["predictions"])
async def generate_prediction(request: GeneratePredictionRequest):
    """Generate price prediction for a single timeframe."""
    if not prediction_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction engine not initialized",
        )

    try:
        prediction_id = str(uuid.uuid4())
        
        result = prediction_engine.generate_prediction(
            symbol=request.symbol,
            current_price=request.current_price,
            prices=request.prices,
            sentiment_score=request.sentiment_score,
            prediction_type=request.prediction_type,
            market_type=request.market_type,
        )
        
        # Create prediction result
        prediction = PredictionResult(
            prediction_id=prediction_id,
            prediction_type=result["prediction_type"],
            market_type=result["market_type"],
            symbol=result["symbol"],
            current_price=result["current_price"],
            predicted_price=result["predicted_price"],
            predicted_direction=PredictionDirection(result["predicted_direction"]),
            confidence_score=result["confidence_score"],
            confidence_level=ConfidenceLevel(result["confidence_level"]),
            technical_indicators=TechnicalIndicators(**result["technical_indicators"]),
            sentiment_score=result["sentiment_score"],
            reasoning=result["reasoning"],
        )
        
        # Publish to Pub/Sub
        await publisher.publish_prediction(prediction)
        
        return GeneratePredictionResponse(
            prediction_id=prediction_id,
            symbol=result["symbol"],
            market_type=result["market_type"],
            prediction_type=result["prediction_type"],
            current_price=result["current_price"],
            predicted_price=result["predicted_price"],
            predicted_direction=result["predicted_direction"],
            confidence_score=result["confidence_score"],
            confidence_level=result["confidence_level"],
            technical_indicators=result["technical_indicators"],
            sentiment_score=result["sentiment_score"],
            reasoning=result["reasoning"],
            created_at=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error("Prediction generation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction generation failed: {str(e)}",
        )


@app.post("/predict/batch", response_model=BatchPredictionResponse, tags=["predictions"])
async def generate_batch_predictions(request: BatchPredictionRequest):
    """Generate predictions for all timeframes."""
    if not prediction_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction engine not initialized",
        )

    try:
        prediction_types = ["30m", "1h", "3h", "6h"]
        predictions = []
        
        for pred_type in prediction_types:
            prediction_id = str(uuid.uuid4())
            
            result = prediction_engine.generate_prediction(
                symbol=request.symbol,
                current_price=request.current_price,
                prices=request.prices,
                sentiment_score=request.sentiment_score,
                prediction_type=pred_type,
                market_type=request.market_type,
            )
            
            result["prediction_id"] = prediction_id
            result["created_at"] = datetime.utcnow().isoformat()
            predictions.append(result)
            
            # Publish each prediction
            prediction = PredictionResult(
                prediction_id=prediction_id,
                prediction_type=result["prediction_type"],
                market_type=result["market_type"],
                symbol=result["symbol"],
                current_price=result["current_price"],
                predicted_price=result["predicted_price"],
                predicted_direction=PredictionDirection(result["predicted_direction"]),
                confidence_score=result["confidence_score"],
                confidence_level=ConfidenceLevel(result["confidence_level"]),
                technical_indicators=TechnicalIndicators(**result["technical_indicators"]),
                sentiment_score=result["sentiment_score"],
                reasoning=result["reasoning"],
            )
            await publisher.publish_prediction(prediction)
        
        return BatchPredictionResponse(
            symbol=request.symbol,
            market_type=request.market_type,
            predictions=predictions,
            current_price=request.current_price,
        )
    except Exception as e:
        logger.error("Batch prediction generation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction generation failed: {str(e)}",
        )


@app.get("/status", tags=["status"])
async def get_status() -> dict:
    """Get service status."""
    return {
        "service": SERVICE_NAME,
        "ml_enabled": settings.enable_ml_predictions,
        "technical_enabled": settings.enable_technical_analysis,
        "crypto_enabled": settings.enable_crypto_predictions,
        "gold_enabled": settings.enable_gold_predictions,
        "engine_ready": prediction_engine is not None,
    }


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


async def _process_market_context(message: PubSubMessage) -> None:
    """Process a market context message from Pub/Sub.
    
    Generates price predictions based on market context data.
    """
    from sentilyze_core.exceptions import RateLimitError
    
    logger.info(
        "Processing market context message",
        message_id=message.message_id,
    )
    
    try:
        data = message.data
        if not isinstance(data, dict):
            logger.error("Invalid message data type", type=type(data).__name__)
            return
            
        # Extract market context info
        symbol = data.get("symbol", "")
        sentiment_score = data.get("sentiment_score", 0.0)
        market_type = data.get("market_type", "generic")
        
        if not symbol:
            logger.warning("No symbol in market context message, skipping")
            return
        
        # TODO: Get actual price data from data source
        # For now, create a placeholder prediction based on sentiment
        if prediction_engine and publisher:
            # Simple prediction based on sentiment
            predicted_direction = "UP" if sentiment_score > 0.1 else ("DOWN" if sentiment_score < -0.1 else "FLAT")
            confidence = min(abs(sentiment_score) * 100, 95)
            
            prediction_result = {
                "prediction_id": str(uuid.uuid4()),
                "symbol": symbol,
                "market_type": market_type,
                "predicted_direction": predicted_direction,
                "confidence": int(confidence),
                "sentiment_score": sentiment_score,
                "prediction_timestamp": datetime.utcnow().isoformat(),
            }
            
            # Publish prediction
            await publisher.publish_prediction(prediction_result)
            logger.info(
                "Published prediction from market context",
                symbol=symbol,
                direction=predicted_direction,
                confidence=confidence,
            )
            
            # Save to BigQuery
            if bigquery_client:
                await bigquery_client.insert_prediction(prediction_result)
            
    except RateLimitError:
        raise
    except Exception as e:
        logger.error("Failed to process market context message", error=str(e))
        raise


@app.post("/pubsub-push/market-context", tags=["pubsub"])
async def pubsub_push_market_context(request: Request) -> dict[str, str]:
    """Pub/Sub push endpoint for market-context subscription."""
    from sentilyze_core.exceptions import RateLimitError
    
    try:
        envelope = await request.json()
        message = _parse_pubsub_push(envelope)
        await _process_market_context(message)
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
