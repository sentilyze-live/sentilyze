"""Unified Sentiment Processor main application.

This service processes both crypto and gold market content using Vertex AI Gemini
for sentiment analysis with market-specific prompts and COT framework support for gold.

Cloud Run scale-to-zero compatible:
- Uses Pub/Sub push subscriptions (HTTP endpoint)
- No streaming-pull subscriber loops
"""

import asyncio
import base64
import json
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from pydantic import ValidationError
except Exception:
    ValidationError = Exception

from sentilyze_core import (
    AlertEvent,
    BigQueryClient,
    PubSubClient,
    PubSubMessage,
    RawEvent,
    configure_logging,
    get_logger,
    get_settings,
)
from sentilyze_core.exceptions import RateLimitError

from .analyzer import UnifiedSentimentAnalyzer
from .transformers import DataTransformer, SilverLayerTransformer
from .publisher import ResultsPublisher
from .config import MarketType

logger = get_logger(__name__)
settings = get_settings()

PROCESSED_EVENTS_TOPIC = "processed-events"
ALERTS_TOPIC = "alerts"

analyzer: UnifiedSentimentAnalyzer | None = None
transformer: DataTransformer | None = None
publisher: ResultsPublisher | None = None
pubsub_client: PubSubClient | None = None
bigquery_client: BigQueryClient | None = None


async def process_message(message: PubSubMessage) -> None:
    """Process a Pub/Sub message with market-specific routing."""
    if not analyzer or not transformer or not publisher:
        raise RuntimeError("Service not initialized")

    lock_acquired = False
    try:
        try:
            if not isinstance(message.data, dict):
                raise ValueError(f"message.data must be a dict, got {type(message.data).__name__}")
            raw_event = RawEvent(**message.data)
        except (ValidationError, ValueError, TypeError) as e:
            logger.error(
                "Invalid raw event payload (acking and skipping)",
                error=str(e),
                message_id=message.message_id,
            )
            return

        logger.debug("Processing event", event_id=str(raw_event.event_id))

        prediction_id = uuid4()

        done_key = f"processed:{raw_event.event_id}"
        lock_key = f"lock:{raw_event.event_id}"
        if await analyzer.cache.exists(done_key, namespace="dedup"):
            logger.info("Duplicate delivery ignored (already processed)", event_id=str(raw_event.event_id))
            return
        acquired = await analyzer.cache.add(
            lock_key,
            {"message_id": message.message_id},
            namespace="dedup",
            ttl=10 * 60,
        )
        lock_acquired = acquired
        if not acquired:
            raise RateLimitError("Duplicate delivery in-flight", retry_after=5)

        if bigquery_client:
            await bigquery_client.insert_raw_event(raw_event.model_dump(mode="json"))

        if not raw_event.content or not raw_event.content.strip():
            logger.info(
                "Skipping sentiment analysis (no text content)",
                event_id=str(raw_event.event_id),
                source=raw_event.source.value,
            )
            await analyzer.cache.set(done_key, "1", namespace="dedup", ttl=7 * 24 * 3600)
            return

        market_type = _determine_market_type(raw_event)
        processed_event = await analyzer.analyze(raw_event, market_type=market_type, prediction_id=prediction_id)

        processed_event = transformer.transform(
            raw_event,
            processed_event.sentiment,
            prediction_id=prediction_id,
            market_type=market_type,
        )

        if bigquery_client:
            row = SilverLayerTransformer.to_bigquery_row(processed_event)
            await bigquery_client.insert_processed_event(row)

        await publisher.publish_processed_event(processed_event, message_id=message.message_id)

        if settings.enable_alerts:
            await _maybe_publish_alert(processed_event, message_id=message.message_id)

        logger.info(
            "Event processed successfully",
            event_id=str(raw_event.event_id),
            market_type=market_type.value,
            sentiment=processed_event.sentiment.label.value,
            score=processed_event.sentiment.score,
        )
        await analyzer.cache.set(done_key, "1", namespace="dedup", ttl=7 * 24 * 3600)

    except RateLimitError:
        raise
    except Exception as e:
        logger.error(
            "Failed to process message",
            error=str(e),
            message_id=message.message_id,
        )
        raise
    finally:
        if analyzer and lock_acquired and "raw_event" in locals():
            await analyzer.cache.delete(f"lock:{raw_event.event_id}", namespace="dedup")


def _determine_market_type(event: RawEvent) -> MarketType:
    """Determine market type based on event content and symbols."""
    content_lower = (event.content or "").lower()
    symbols = [s.lower() for s in (event.symbols or [])]

    gold_keywords = ["gold", "xau", "xauusd", "precious metal", "bullion", "gld", "iau"]
    for keyword in gold_keywords:
        if keyword in content_lower:
            return MarketType.GOLD

    crypto_keywords = [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency",
        "blockchain", "altcoin", "defi", "nft", "web3"
    ]
    for keyword in crypto_keywords:
        if keyword in content_lower:
            return MarketType.CRYPTO

    if any(s in ["xau", "xauusd", "gold"] for s in symbols):
        return MarketType.GOLD
    if any(s in ["btc", "eth", "crypto"] for s in symbols):
        return MarketType.CRYPTO

    # sentilyze_core.MarketType has no GENERIC; use CRYPTO as a safe fallback.
    return MarketType.CRYPTO


async def _maybe_publish_alert(processed_event, *, message_id: str | None) -> None:
    """Best-effort threshold-based alert publishing."""
    if not publisher or not analyzer:
        return

    s = processed_event.sentiment
    if s.confidence < settings.alert_min_confidence:
        return

    symbols = processed_event.symbols or []
    primary_symbol = symbols[0] if symbols else None
    if not primary_symbol:
        return

    alert_type: str | None = None
    severity: str = "low"
    if s.score <= settings.alert_negative_score_threshold:
        alert_type = "sentiment_negative"
        severity = "high" if s.score <= -0.6 else "medium"
    elif s.score >= settings.alert_positive_score_threshold:
        alert_type = "sentiment_positive"
        severity = "medium" if s.score >= 0.8 else "low"

    if not alert_type:
        return

    cooldown_key = f"cooldown:{alert_type}:{primary_symbol}"
    ok = await analyzer.cache.add(
        cooldown_key,
        "1",
        namespace="alerts",
        ttl=settings.alert_cooldown_seconds,
    )
    if not ok:
        return

    channels = [c.strip() for c in (settings.alert_default_channels or "").split(",") if c.strip()]
    recipients: list[str] = []
    if "telegram" in channels and settings.alert_telegram_chat_ids:
        recipients = [c.strip() for c in settings.alert_telegram_chat_ids.split(",") if c.strip()]

    if not channels or ("telegram" in channels and not recipients):
        logger.warning(
            "Alert skipped (no routing configured)",
            event_id=str(processed_event.event_id),
            alert_type=alert_type,
        )
        return

    from uuid import NAMESPACE_URL, uuid5

    alert_id = uuid5(NAMESPACE_URL, f"{processed_event.event_id}:{alert_type}")
    alert = AlertEvent(
        alert_id=alert_id,
        alert_type=alert_type,
        severity=severity,
        title=f"{primary_symbol}: {alert_type.replace('_', ' ').title()}",
        message=(
            f"score={s.score:.3f} label={s.label.value} confidence={s.confidence:.2f} "
            f"source={processed_event.source.value}"
        ),
        data={
            "event_id": str(processed_event.event_id),
            "message_id": message_id,
            "symbol": primary_symbol,
            "symbols": processed_event.symbols,
            "score": s.score,
            "label": s.label.value,
            "confidence": s.confidence,
            "processed_at": processed_event.processed_at.isoformat(),
        },
        channels=channels,
        recipients=recipients,
        tenant_id=processed_event.tenant_id,
    )

    await publisher.publish_alert(alert)


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
    global analyzer, transformer, publisher, pubsub_client, bigquery_client

    configure_logging(
        log_level=settings.log_level,
        service_name="sentiment-processor",
        environment=settings.environment,
    )
    logger.info("Starting unified sentiment processor service")

    pubsub_client = PubSubClient()
    bigquery_client = BigQueryClient()
    publisher = ResultsPublisher(pubsub_client)

    analyzer = UnifiedSentimentAnalyzer()
    await analyzer.initialize()

    transformer = DataTransformer()

    logger.info(
        "Service initialized",
        crypto_enabled=settings.enable_crypto_analysis,
        gold_enabled=settings.enable_gold_analysis,
        cot_enabled=settings.enable_cot_framework,
    )

    yield

    logger.info("Shutting down sentiment processor service")

    if analyzer:
        await analyzer.close()
    if publisher:
        await publisher.close()
    if pubsub_client:
        pubsub_client.close()
    if bigquery_client:
        bigquery_client.close()


app = FastAPI(
    title="Sentilyze Unified Sentiment Processor",
    description="AI-powered sentiment analysis for crypto and gold markets",
    version="3.0.0",
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


@app.post("/pubsub-push/raw-events", tags=["pubsub"])
async def pubsub_push_raw_events(request: Request) -> dict[str, str]:
    """Pub/Sub push endpoint for raw-events subscription."""
    envelope: dict[str, Any] | None = None
    try:
        try:
            envelope = await request.json()
        except json.JSONDecodeError as e:
            logger.error("Invalid Pub/Sub push envelope JSON (acking and skipping)", error=str(e))
            return {"status": "skipped"}

        try:
            message = _parse_pubsub_push(envelope)
        except ValueError as e:
            msg_id = None
            try:
                msg_id = (envelope.get("message") or {}).get("messageId")
            except Exception:
                msg_id = None
            logger.error(
                "Pub/Sub message parse failed (acking and skipping)",
                error=str(e),
                message_id=msg_id,
            )
            return {"status": "skipped"}

        await process_message(message)
        return {"status": "ok"}
    except RateLimitError as e:
        logger.info("Backpressure/rate limit", error=str(e), retry_after=e.retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "rate_limited", "retry_after": e.retry_after},
            headers={"Retry-After": str(e.retry_after)},
        )
    except Exception as e:
        logger.error("Pub/Sub push processing failed", error=str(e))
        raise HTTPException(status_code=500, detail="processing failed")


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "sentiment-processor",
        "version": "3.0.0",
    }


@app.get("/ready", tags=["health"])
async def readiness_check() -> dict:
    """Readiness check endpoint."""
    checks = {
        "analyzer": analyzer is not None and analyzer._initialized,
        "pubsub": pubsub_client is not None,
        "bigquery": bigquery_client is not None,
        "publisher": publisher is not None,
    }

    all_ready = all(checks.values())

    if not all_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not ready", "checks": checks},
        )

    return {"status": "ready", "checks": checks}


@app.post("/analyze", tags=["analysis"])
async def analyze_text(text: str, market_type: str = "auto") -> dict:
    """Analyze sentiment of provided text."""
    if not analyzer or not analyzer._initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analyzer not initialized",
        )

    try:
        from datetime import datetime
        from sentilyze_core import DataSource
        from .config import MarketType

        raw_event = RawEvent(
            event_id=uuid4(),
            source=DataSource.CUSTOM,
            source_id="manual",
            content=text,
            collected_at=datetime.utcnow(),
        )

        mt = MarketType(market_type) if market_type != "auto" else MarketType.CRYPTO
        prediction_id = uuid4()
        result = await analyzer.analyze(raw_event, market_type=mt, prediction_id=prediction_id)

        return {
            "predictionId": str(result.prediction_id),
            "marketType": mt.value,
            "sentiment": result.sentiment.model_dump(),
            "entities": result.entities,
            "symbols": result.symbols,
            "keywords": result.keywords,
        }
    except Exception as e:
        logger.error("Analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )


@app.get("/status", tags=["status"])
async def get_status() -> dict:
    """Get service status."""
    return {
        "service": "sentiment-processor",
        "analyzer_ready": analyzer is not None and analyzer._initialized,
        "model": settings.gemini_model,
        "enable_crypto": settings.enable_crypto_analysis,
        "enable_gold": settings.enable_gold_analysis,
        "enable_cot": settings.enable_cot_framework,
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
