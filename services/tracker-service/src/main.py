"""Tracker Service main application."""

import asyncio
import base64
import json
from contextlib import asynccontextmanager
from datetime import datetime
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
from sentilyze_core.exceptions import RateLimitError

from .config import get_tracker_settings
from .models import PredictionOutcome, PredictionRecord
from .tracker import PredictionTracker

logger = get_logger(__name__)
settings = get_tracker_settings()

SERVICE_NAME = "tracker-service"
SERVICE_VERSION = "3.0.0"

# Global instances
tracker: PredictionTracker | None = None
pubsub_client: PubSubClient | None = None
bigquery_client: BigQueryClient | None = None


# Pydantic Models
class ProcessOutcomeRequest(BaseModel):
    prediction_id: str = Field(..., description="Prediction ID")
    symbol: str = Field(..., description="Trading symbol")
    market_type: str = Field(default="generic", description="Market type")
    predicted_price: float = Field(..., description="Predicted price")
    predicted_direction: str = Field(..., description="Predicted direction (UP/DOWN/FLAT)")
    current_price: float = Field(..., description="Price at prediction time")
    actual_price: float = Field(..., description="Actual current price")
    confidence_score: int = Field(default=50, description="Prediction confidence")


class ProcessOutcomeResponse(BaseModel):
    outcome_id: str
    prediction_id: str
    actual_direction: str
    price_diff: float
    percent_diff: float
    direction_correct: bool
    success_level: str
    ai_analysis_generated: bool


class AccuracyStatsRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=365, description="Number of days to analyze")
    symbol: str | None = Field(default=None, description="Filter by symbol")
    market_type: str | None = Field(default=None, description="Filter by market type")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    global tracker, pubsub_client, bigquery_client

    configure_logging(
        log_level=settings.log_level,
        service_name=SERVICE_NAME,
        environment=settings.environment,
    )
    logger.info("Starting tracker service")

    # Initialize clients
    pubsub_client = PubSubClient()
    bigquery_client = BigQueryClient()

    # Initialize tracker
    tracker = PredictionTracker()

    logger.info(
        "Service initialized",
        ai_analysis_enabled=settings.enable_ai_analysis,
        tracking_enabled=settings.enable_auto_tracking,
    )

    yield

    # Shutdown
    logger.info("Shutting down tracker service")

    if pubsub_client:
        pubsub_client.close()
    if bigquery_client:
        bigquery_client.close()


app = FastAPI(
    title="Sentilyze Tracker Service",
    description="Prediction tracking and outcome evaluation service",
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
        "tracker": tracker is not None,
        "pubsub": pubsub_client is not None,
        "bigquery": bigquery_client is not None,
    }

    all_ready = all(checks.values())

    if not all_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not ready", "checks": checks},
        )

    return {"status": "ready", "checks": checks}


@app.post("/outcomes/process", response_model=ProcessOutcomeResponse, tags=["outcomes"])
async def process_outcome(request: ProcessOutcomeRequest):
    """Process a prediction outcome."""
    if not tracker:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tracker not initialized",
        )

    try:
        # Create prediction record
        prediction = PredictionRecord(
            prediction_id=request.prediction_id,
            user_id="api",  # Would come from auth context
            symbol=request.symbol,
            market_type=request.market_type,
            prediction_type="1h",  # Default, could be passed in request
            current_price=request.current_price,
            predicted_price=request.predicted_price,
            predicted_direction=request.predicted_direction,
            confidence_score=request.confidence_score,
            confidence_level="MEDIUM" if request.confidence_score >= 50 else "LOW",
            technical_signals={},
            sentiment_score=0.0,
            reasoning="API submitted",
        )

        # Calculate outcome
        outcome = tracker.calculate_outcome(prediction, request.actual_price)

        # Check if AI analysis needed
        ai_analysis = None
        if tracker.should_generate_ai_analysis(prediction, outcome):
            # AI analysis would be generated here with Vertex AI
            outcome.ai_analysis_generated = False  # Placeholder

        return ProcessOutcomeResponse(
            outcome_id=outcome.outcome_id,
            prediction_id=outcome.prediction_id,
            actual_direction=outcome.actual_direction,
            price_diff=outcome.price_diff,
            percent_diff=outcome.percent_diff,
            direction_correct=outcome.direction_correct,
            success_level=outcome.success_level,
            ai_analysis_generated=outcome.ai_analysis_generated,
        )
    except Exception as e:
        logger.error("Outcome processing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Outcome processing failed: {str(e)}",
        )


@app.get("/stats/accuracy", tags=["stats"])
async def get_accuracy_stats(
    days: int = 7,
    symbol: str | None = None,
    market_type: str | None = None,
):
    """Get prediction accuracy statistics."""
    if not bigquery_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BigQuery client not initialized",
        )

    try:
        # Placeholder - would query BigQuery for stats
        return {
            "days": days,
            "symbol": symbol,
            "market_type": market_type,
            "total_predictions": 0,
            "correct_directions": 0,
            "accuracy_percentage": 0.0,
            "by_period": [],
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error("Stats retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stats retrieval failed: {str(e)}",
        )


@app.get("/status", tags=["status"])
async def get_status() -> dict:
    """Get service status."""
    return {
        "service": SERVICE_NAME,
        "ai_analysis_enabled": settings.enable_ai_analysis,
        "tracking_enabled": settings.enable_auto_tracking,
        "tracker_ready": tracker is not None,
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


async def _process_prediction(message: PubSubMessage) -> None:
    """Process a prediction message from Pub/Sub.
    
    Stores prediction for later outcome tracking.
    """
    logger.info(
        "Processing prediction message",
        message_id=message.message_id,
    )
    
    try:
        data = message.data
        if not isinstance(data, dict):
            logger.error("Invalid message data type", type=type(data).__name__)
            return
        
        prediction_id = data.get("prediction_id")
        symbol = data.get("symbol")
        
        if not prediction_id or not symbol:
            logger.warning("Missing prediction_id or symbol, skipping")
            return
        
        # Store prediction in database for tracking
        if bigquery_client:
            await bigquery_client.insert_prediction(data)
            logger.info(
                "Stored prediction for tracking",
                prediction_id=prediction_id,
                symbol=symbol,
            )
        
        # TODO: Schedule outcome tracking after prediction window
        # This would typically be done via Cloud Scheduler or delayed Pub/Sub message
        
    except Exception as e:
        logger.error("Failed to process prediction message", error=str(e))
        raise


@app.post("/pubsub-push/predictions", tags=["pubsub"])
async def pubsub_push_predictions(request: Request) -> dict[str, str]:
    """Pub/Sub push endpoint for predictions subscription."""
    try:
        envelope = await request.json()
        message = _parse_pubsub_push(envelope)
        await _process_prediction(message)
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
