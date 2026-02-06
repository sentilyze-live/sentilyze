"""Prediction Engine main application."""

import asyncio
import base64
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Optional

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
from .ensemble import EnsemblePredictor
from .training import TrainingPipeline
from .feedback import FeedbackLoop

logger = get_logger(__name__)
settings = get_prediction_settings()

SERVICE_NAME = "prediction-engine"
SERVICE_VERSION = "3.1.0"

# Global instances
prediction_engine: PredictionEngine | None = None
ensemble_predictor: EnsemblePredictor | None = None
publisher: PredictionPublisher | None = None
pubsub_client: PubSubClient | None = None
bigquery_client: BigQueryClient | None = None
training_pipeline: TrainingPipeline | None = None
feedback_loop: FeedbackLoop | None = None


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
    global prediction_engine, ensemble_predictor, publisher, pubsub_client, bigquery_client, training_pipeline, feedback_loop

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

    # Initialize training pipeline and feedback loop
    training_pipeline = TrainingPipeline(models_dir="models")
    feedback_loop = FeedbackLoop()

    # Try to load pre-trained models from GCS
    await _load_models_from_gcs()

    # Initialize ensemble predictor if enabled
    if settings.enable_ensemble_predictions:
        try:
            ensemble_predictor = EnsemblePredictor(
                enable_lstm=settings.enable_lstm_model,
                enable_arima=settings.enable_arima_model,
                enable_xgboost=settings.enable_xgboost_model,
                enable_random_forest=True,
            )
            logger.info("Ensemble predictor initialized",
                       lstm=settings.enable_lstm_model,
                       arima=settings.enable_arima_model,
                       xgboost=settings.enable_xgboost_model)
        except Exception as e:
            logger.error("Failed to initialize ensemble predictor", error=str(e))
            ensemble_predictor = None

    logger.info(
        "Service initialized",
        ml_enabled=settings.enable_ml_predictions,
        technical_enabled=settings.enable_technical_analysis,
        ensemble_enabled=ensemble_predictor is not None,
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

        # Record in feedback loop for outcome tracking
        if feedback_loop:
            try:
                indicators = result["technical_indicators"]
                await feedback_loop.record_prediction(
                    prediction_id=prediction_id,
                    symbol=result["symbol"],
                    market_type=result["market_type"],
                    prediction_type=result["prediction_type"],
                    predicted_direction=result["predicted_direction"],
                    predicted_price=result["predicted_price"],
                    current_price=result["current_price"],
                    confidence_score=result["confidence_score"],
                    technical_signal=prediction_engine.technical_analyzer.calculate_technical_signal(
                        TechnicalIndicators(**indicators)
                    ),
                    sentiment_score=result["sentiment_score"],
                    ml_prediction=0.0,
                    indicator_signals={
                        "rsi": indicators.get("rsi", 50) / 100 - 0.5,
                        "macd": 0.3 if (indicators.get("macd_histogram") or 0) > 0 else -0.3,
                        "ema_cross": 0.4 if (indicators.get("ema_short") or 0) > (indicators.get("ema_medium") or 0) else -0.4,
                    },
                )
            except Exception as fb_err:
                logger.debug("Feedback recording failed (non-fatal)", error=str(fb_err))

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
        # Optimized timeframes based on sentiment-to-price lag analysis
        prediction_types = ["1h", "2h", "3h"]
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


class EnsemblePredictionRequest(BaseModel):
    """Request for ensemble prediction with historical data."""
    symbol: str = Field(..., description="Trading symbol")
    current_price: float = Field(..., description="Current price")
    indicators: dict = Field(..., description="Technical indicators")
    sentiment_score: float = Field(default=0.0, description="Sentiment score")
    economic_data: Optional[dict] = Field(default=None, description="Economic indicators")
    price_history: Optional[list[float]] = Field(default=None, description="Price history for ARIMA")
    feature_history: Optional[list[list[float]]] = Field(default=None, description="Feature history for LSTM")


class EnsemblePredictionResponse(BaseModel):
    """Response from ensemble prediction."""
    symbol: str
    ensemble_price: float
    confidence: str
    num_models: int
    models: dict
    timestamp: str


@app.post("/predict/ensemble", response_model=EnsemblePredictionResponse, tags=["predictions"])
async def generate_ensemble_prediction(request: EnsemblePredictionRequest):
    """Generate ensemble prediction using LSTM, ARIMA, XGBoost, and Random Forest."""
    if not ensemble_predictor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ensemble predictor not initialized. Enable with ENABLE_ENSEMBLE_PREDICTIONS=True",
        )

    try:
        # Convert dict to TechnicalIndicators
        from .predictor import TechnicalAnalyzer
        indicators_obj = TechnicalAnalyzer.TechnicalIndicators(
            rsi=request.indicators.get('rsi'),
            macd=request.indicators.get('macd'),
            macd_signal=request.indicators.get('macd_signal'),
            macd_histogram=request.indicators.get('macd_histogram'),
            bb_upper=request.indicators.get('bb_upper'),
            bb_middle=request.indicators.get('bb_middle'),
            bb_lower=request.indicators.get('bb_lower'),
            ema_short=request.indicators.get('ema_short', 0.0),
            ema_medium=request.indicators.get('ema_medium', 0.0),
            ema_long=request.indicators.get('ema_long', 0.0),
        )

        result = await ensemble_predictor.predict(
            indicators=indicators_obj,
            sentiment_score=request.sentiment_score,
            current_price=request.current_price,
            economic_data=request.economic_data or {},
            price_history=request.price_history,
            feature_history=request.feature_history,
        )

        return EnsemblePredictionResponse(
            symbol=request.symbol,
            ensemble_price=result['ensemble_price'],
            confidence=result['confidence'],
            num_models=result['num_models'],
            models=result['models'],
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error("Ensemble prediction failed", error=str(e), symbol=request.symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ensemble prediction failed: {str(e)}",
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
        "ensemble_enabled": ensemble_predictor is not None,
        "models": {
            "lstm": settings.enable_lstm_model if ensemble_predictor else False,
            "arima": settings.enable_arima_model if ensemble_predictor else False,
            "xgboost": settings.enable_xgboost_model if ensemble_predictor else False,
            "random_forest": True if ensemble_predictor else False,
        },
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


# --- Feedback Loop Endpoints ---

class RecordOutcomeRequest(BaseModel):
    """Request to record a prediction outcome."""
    prediction_id: str = Field(..., description="Original prediction ID")
    actual_price: float = Field(..., description="Actual price at expiry")


@app.post("/feedback/outcome", tags=["feedback"])
async def record_prediction_outcome(request: RecordOutcomeRequest):
    """Record actual outcome for a prediction."""
    if not feedback_loop:
        raise HTTPException(status_code=503, detail="Feedback loop not initialized")

    result = await feedback_loop.record_outcome(
        prediction_id=request.prediction_id,
        actual_price=request.actual_price,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Prediction not found")

    return {"status": "recorded", "outcome": result}


@app.post("/feedback/resolve-expired", tags=["feedback"])
async def resolve_expired_predictions(req: Request):
    """Resolve expired predictions by fetching actual prices."""
    api_key = req.headers.get("X-Admin-API-Key") or req.headers.get("x-admin-api-key")
    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key or api_key != admin_key:
        raise HTTPException(status_code=403, detail="Admin API key required")

    if not feedback_loop:
        raise HTTPException(status_code=503, detail="Feedback loop not initialized")

    resolved = await feedback_loop.check_and_resolve_expired()
    return {"status": "ok", "resolved_count": resolved}


@app.get("/feedback/accuracy", tags=["feedback"])
async def get_accuracy_report():
    """Get prediction accuracy report and indicator performance."""
    if not feedback_loop:
        return {"status": "not_initialized"}

    return feedback_loop.get_accuracy_report()


@app.get("/feedback/weights", tags=["feedback"])
async def get_optimized_weights():
    """Get current optimized prediction weights."""
    if not feedback_loop:
        return settings.prediction_weights

    return feedback_loop.get_current_weights()


@app.get("/feedback/daily-report", tags=["feedback"])
async def get_daily_report(date: Optional[str] = None):
    """Generate daily prediction report with success/failure analysis.

    Shows what went right, what went wrong, and why.
    Includes actionable lessons for improvement.

    Args:
        date: Date in YYYY-MM-DD format (defaults to today)
    """
    if not feedback_loop:
        return {"status": "not_initialized"}

    report_date = None
    if date:
        try:
            report_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD",
            )

    return await feedback_loop.generate_daily_report(report_date)


@app.post("/feedback/apply-lessons", tags=["feedback"])
async def apply_daily_lessons(req: Request):
    """Apply lessons from daily report to improve future predictions.

    Automatically adjusts component and indicator weights based on
    performance analysis. Only applies high-severity lessons.
    """
    api_key = req.headers.get("X-Admin-API-Key") or req.headers.get("x-admin-api-key")
    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key or api_key != admin_key:
        raise HTTPException(status_code=403, detail="Admin API key required")

    if not feedback_loop:
        raise HTTPException(status_code=503, detail="Feedback loop not initialized")

    # First generate today's report
    report = await feedback_loop.generate_daily_report()
    lessons = report.get("lessons_learned", [])

    if not lessons:
        return {"status": "no_lessons", "message": "No lessons to apply today"}

    # Apply the lessons
    result = await feedback_loop.apply_lessons(lessons)

    return {
        "status": "applied",
        "report_date": report["date"],
        "accuracy": report["summary"]["accuracy_pct"],
        **result,
    }


@app.post("/feedback/end-of-day", tags=["feedback"])
async def end_of_day_cycle(req: Request):
    """Run the complete end-of-day cycle.

    1. Resolve all expired predictions
    2. Generate daily report
    3. Apply high-severity lessons
    4. Trigger weight re-optimization if needed

    This endpoint should be called by Cloud Scheduler at 23:55 UTC daily.
    """
    api_key = req.headers.get("X-Admin-API-Key") or req.headers.get("x-admin-api-key")
    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key or api_key != admin_key:
        raise HTTPException(status_code=403, detail="Admin API key required")

    if not feedback_loop:
        raise HTTPException(status_code=503, detail="Feedback loop not initialized")

    results = {}

    # Step 1: Resolve expired predictions
    resolved = await feedback_loop.check_and_resolve_expired()
    results["resolved_predictions"] = resolved

    # Step 2: Generate daily report
    report = await feedback_loop.generate_daily_report()
    results["report"] = {
        "date": report.get("date"),
        "accuracy": report.get("summary", {}).get("accuracy_pct", "N/A"),
        "total": report.get("summary", {}).get("total_predictions", 0),
        "lessons_count": len(report.get("lessons_learned", [])),
        "top_failures": report.get("top_failure_reasons", [])[:5],
    }

    # Step 3: Apply lessons
    lessons = report.get("lessons_learned", [])
    if lessons:
        applied = await feedback_loop.apply_lessons(lessons)
        results["lessons_applied"] = applied

    # Step 4: Re-optimize weights if enough data
    try:
        # Get recent prices for regime detection
        if bigquery_client:
            prices = await _get_recent_prices()
            if prices and len(prices) >= 20:
                optimized = await feedback_loop.maybe_optimize_weights(
                    prices=prices, symbol="XAU"
                )
                if optimized:
                    results["weight_optimization"] = {
                        "status": "optimized",
                        "new_weights": optimized.component_weights,
                        "regime": optimized.market_regime,
                        "confidence": f"{optimized.optimization_confidence:.0%}",
                    }
                else:
                    results["weight_optimization"] = {"status": "not_needed"}
    except Exception as e:
        results["weight_optimization"] = {"status": "error", "error": str(e)}

    logger.info("End-of-day cycle completed", results=results)
    return results


async def _get_recent_prices() -> list[float]:
    """Fetch recent gold prices from BigQuery for weight optimization."""
    if not bigquery_client:
        return []

    try:
        from google.cloud import bigquery as bq

        client = bq.Client(project=settings.google_cloud_project)
        query = """
        SELECT CAST(JSON_EXTRACT_SCALAR(payload, '$.price') AS FLOAT64) as price
        FROM `{project}.{dataset}.raw_events`
        WHERE symbol LIKE '%XAU%'
          AND JSON_EXTRACT_SCALAR(payload, '$.price') IS NOT NULL
          AND timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        ORDER BY timestamp DESC
        LIMIT 200
        """.format(
            project=settings.google_cloud_project,
            dataset=settings.bigquery_dataset,
        )

        rows = client.query(query).result()
        prices = [float(row.price) for row in rows if row.price]
        prices.reverse()  # oldest first
        return prices

    except Exception as e:
        logger.warning("Could not fetch recent prices", error=str(e))
        return []


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


async def _load_models_from_gcs() -> None:
    """Try to download pre-trained models from GCS on startup."""
    try:
        from google.cloud import storage

        bucket_name = f"{settings.google_cloud_project}-models"
        client = storage.Client(project=settings.google_cloud_project)

        try:
            bucket = client.get_bucket(bucket_name)
        except Exception:
            logger.info("Models bucket not found, skipping GCS model load")
            return

        prefix = "prediction-engine/XAU/latest/"
        blobs = list(bucket.list_blobs(prefix=prefix))

        if not blobs:
            logger.info("No pre-trained models found in GCS")
            return

        os.makedirs("models", exist_ok=True)

        for blob in blobs:
            filename = blob.name.split("/")[-1]
            if not filename:
                continue
            local_path = os.path.join("models", filename)
            blob.download_to_filename(local_path)
            logger.info("Downloaded model from GCS", file=filename)

        logger.info("Pre-trained models loaded from GCS", count=len(blobs))

    except Exception as e:
        logger.warning("Could not load models from GCS (non-fatal)", error=str(e))


class TrainRequest(BaseModel):
    """Request to trigger model training."""
    symbol: str = Field(default="XAU", description="Asset symbol to train on")
    days: int = Field(default=180, description="Days of historical data", ge=30, le=365)
    save_to_gcs: bool = Field(default=True, description="Upload models to GCS")


@app.post("/train", tags=["training"])
async def trigger_training(request: TrainRequest, req: Request):
    """Trigger model training pipeline.

    Protected by admin API key. Trains all ML models on historical data.
    """
    # Require admin API key
    api_key = req.headers.get("X-Admin-API-Key") or req.headers.get("x-admin-api-key")
    admin_key = os.getenv("ADMIN_API_KEY", "")
    if not admin_key or api_key != admin_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin API key required",
        )

    if not training_pipeline:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Training pipeline not initialized",
        )

    try:
        results = await training_pipeline.run_full_training(
            symbol=request.symbol,
            days=request.days,
            save_to_gcs=request.save_to_gcs,
        )
        return results
    except Exception as e:
        logger.error("Training failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Training failed: {str(e)}",
        )


@app.get("/training/status", tags=["training"])
async def get_training_status():
    """Get last training results."""
    if not training_pipeline:
        return {"status": "not_initialized"}

    return training_pipeline.training_results or {"status": "no_training_run"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
    )
