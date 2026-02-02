"""Alert Service main application."""

import asyncio
import base64
import json
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sentilyze_core import (
    AlertEvent,
    BigQueryClient,
    CacheClient,
    PubSubClient,
    PubSubMessage,
    configure_logging,
    get_logger,
)
from sentilyze_core.exceptions import RateLimitError

from .config import AlertSeverity, get_alert_settings
from .notifier import NotifierManager

logger = get_logger(__name__)
settings = get_alert_settings()

SERVICE_NAME = "alert-service"
SERVICE_VERSION = "3.0.0"
ALERTS_TOPIC = "alerts"

# Global instances
pubsub_client: PubSubClient | None = None
bigquery_client: BigQueryClient | None = None
notifier_manager: NotifierManager | None = None
cache: CacheClient | None = None


async def process_alert(message: PubSubMessage) -> None:
    """Process an alert message."""
    if not notifier_manager or not bigquery_client or not cache:
        raise RuntimeError("Service not initialized")

    try:
        alert = AlertEvent(**message.data)
        logger.info(
            "Processing alert",
            alert_id=str(alert.alert_id),
            correlation_id=(alert.data.get("event_id") if isinstance(alert.data, dict) else None),
        )

        # Save to BigQuery
        await bigquery_client.insert_alert(alert.model_dump(mode="json"))

        # Resolve routing
        channels = alert.channels or []
        if not channels:
            channels = [c.strip() for c in settings.alert_default_channels.split(",") if c.strip()]

        recipients = alert.recipients or []
        if "telegram" in channels and not recipients and settings.telegram_chat_ids:
            recipients = [c.strip() for c in settings.telegram_chat_ids.split(",") if c.strip()]

        if not channels:
            raise RuntimeError("No alert channels configured")

        # Send notifications with idempotency
        any_failed = False
        for channel in channels:
            if channel == "telegram":
                if not recipients:
                    raise RuntimeError("Telegram channel configured but no recipients")
                for recipient in recipients:
                    sent_key = f"sent:{alert.alert_id}:{channel}:{recipient}"
                    if await cache.exists(sent_key, namespace="alert-delivery"):
                        continue
                    try:
                        ok = await notifier_manager.send_to_channel(alert, channel, recipient)
                        if ok:
                            await cache.set(sent_key, "1", namespace="alert-delivery", ttl=7 * 24 * 3600)
                        else:
                            logger.warning(
                                "Telegram send skipped/disabled",
                                channel=channel,
                                recipient=recipient,
                                alert_id=str(alert.alert_id),
                            )
                    except RateLimitError:
                        raise
                    except Exception as e:
                        logger.error(
                            "Notification send failed",
                            channel=channel,
                            recipient=recipient,
                            error=str(e),
                            alert_id=str(alert.alert_id),
                        )
                        any_failed = True
            elif channel == "webhook":
                try:
                    await notifier_manager.send_to_channel(alert, channel)
                except Exception as e:
                    logger.error("Webhook send failed", error=str(e), alert_id=str(alert.alert_id))
                    any_failed = True
            else:
                logger.warning("Unknown alert channel", channel=channel, alert_id=str(alert.alert_id))

        if any_failed:
            raise RuntimeError("One or more notifications failed")

        logger.info("Alert processed successfully", alert_id=str(alert.alert_id), channels=channels)

    except Exception as e:
        logger.error("Failed to process alert", error=str(e))
        raise


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
    global pubsub_client, bigquery_client, notifier_manager, cache

    configure_logging(
        log_level=settings.log_level,
        service_name=SERVICE_NAME,
        environment=settings.environment,
    )
    logger.info("Starting alert service")

    # Initialize clients
    pubsub_client = PubSubClient()
    bigquery_client = BigQueryClient()
    cache = CacheClient()

    # Initialize notifiers
    notifier_manager = NotifierManager()
    await notifier_manager.initialize()

    yield

    # Shutdown
    logger.info("Shutting down alert service")

    if notifier_manager:
        await notifier_manager.close()
    if pubsub_client:
        pubsub_client.close()
    if bigquery_client:
        bigquery_client.close()


app = FastAPI(
    title="Sentilyze Alert Service",
    description="Notification and alerting service for crypto and gold markets",
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
        "telegram": notifier_manager.telegram.enabled if notifier_manager else False,
        "webhook": notifier_manager.webhook.enabled if notifier_manager else False,
        "pubsub": pubsub_client is not None,
    }

    all_ready = any([
        checks["telegram"],
        checks["webhook"],
    ])

    if not all_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not ready", "checks": checks},
        )

    return {"status": "ready", "checks": checks}


@app.post("/pubsub-push/alerts", tags=["pubsub"])
async def pubsub_push_alerts(request: Request) -> dict[str, str]:
    """Pub/Sub push endpoint for alerts subscription."""
    try:
        envelope = await request.json()
        message = _parse_pubsub_push(envelope)
        await process_alert(message)
        return {"status": "ok"}
    except RateLimitError as e:
        logger.warning("Backpressure/rate limit", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "rate_limited", "retry_after": e.retry_after},
        )
    except Exception as e:
        logger.error("Pub/Sub push processing failed", error=str(e))
        raise HTTPException(status_code=500, detail="processing failed")


@app.post("/alerts", status_code=status.HTTP_201_CREATED, tags=["alerts"])
async def create_alert(alert: AlertEvent) -> dict:
    """Create and send an alert."""
    if not pubsub_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    try:
        await pubsub_client.publish(
            ALERTS_TOPIC,
            alert.model_dump(mode="json"),
            attributes={
                "severity": alert.severity,
                "type": alert.alert_type,
            },
        )

        return {
            "status": "created",
            "alert_id": str(alert.alert_id),
        }

    except Exception as e:
        logger.error("Failed to create alert", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create alert: {str(e)}",
        )


@app.post("/test/telegram", tags=["test"])
async def test_telegram_alert(chat_id: str, message: str = "Test alert from Sentilyze") -> dict:
    """Send a test alert to Telegram."""
    if not notifier_manager or not notifier_manager.telegram.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram not initialized",
        )

    try:
        test_alert = AlertEvent(
            alert_type="test",
            severity="low",
            title="Test Alert",
            message=message,
            channels=["telegram"],
            recipients=[chat_id],
        )

        success = await notifier_manager.telegram.send_alert(test_alert, chat_id)

        return {
            "success": success,
            "chat_id": chat_id,
            "message": message,
        }

    except Exception as e:
        logger.error("Test alert failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test failed: {str(e)}",
        )


@app.get("/status", tags=["status"])
async def get_status() -> dict:
    """Get service status."""
    return {
        "service": SERVICE_NAME,
        "telegram_enabled": settings.enable_telegram,
        "webhook_enabled": settings.enable_webhook,
        "telegram_ready": notifier_manager.telegram.enabled if notifier_manager else False,
        "webhook_ready": notifier_manager.webhook.enabled if notifier_manager else False,
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
