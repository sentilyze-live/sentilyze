"""Results publisher for processed events and alerts.

This module handles publishing processed sentiment results to
Pub/Sub topics for downstream consumption.
"""

from typing import Any
from uuid import UUID

from sentilyze_core import PubSubClient, ProcessedEvent, AlertEvent, get_logger, get_settings
from sentilyze_core.exceptions import PubSubError

from .config import MarketType

logger = get_logger(__name__)
settings = get_settings()

# Topic names
PROCESSED_EVENTS_TOPIC = "processed-events"
ALERTS_TOPIC = "alerts"
GOLD_ANALYSIS_TOPIC = "gold-analysis"
CRYPTO_ANALYSIS_TOPIC = "crypto-analysis"


class ResultsPublisher:
    """Publisher for sentiment analysis results.
    
    This class handles publishing processed events and alerts to
the appropriate Pub/Sub topics based on market type and content.
    """

    def __init__(self, pubsub_client: PubSubClient | None = None) -> None:
        """Initialize the results publisher.

        Args:
            pubsub_client: Configured PubSubClient instance
        """
        self.client = pubsub_client
        self._initialized = pubsub_client is not None

    async def publish_processed_event(
        self,
        processed_event: ProcessedEvent,
        message_id: str | None = None,
    ) -> str | None:
        """Publish a processed event to the appropriate topic.

        Args:
            processed_event: The processed event to publish
            message_id: Original message ID for tracing

        Returns:
            Published message ID or None if publishing failed
        """
        if not self.client:
            logger.warning("No Pub/Sub client configured, skipping publish")
            return None

        # Determine topic before try block for error reporting
        topic = self._get_topic_for_event(processed_event)
        
        try:
            attributes = {
                "source": processed_event.source.value,
                "sentiment_label": processed_event.sentiment.label.value,
                "event_id": str(processed_event.event_id),
                "correlation_id": str(processed_event.event_id),
                "prediction_id": str(processed_event.prediction_id),
            }

            message_id_result = await self.client.publish(
                topic,
                processed_event.model_dump(mode="json"),
                attributes=attributes,
            )

            logger.debug(
                "Published processed event",
                event_id=str(processed_event.event_id),
                topic=topic,
                message_id=message_id_result,
            )

            return message_id_result
        except Exception as e:
            logger.error(
                "Failed to publish processed event",
                error=str(e),
                event_id=str(processed_event.event_id),
            )
            raise PubSubError(
                f"Failed to publish processed event: {e}",
                details={"event_id": str(processed_event.event_id), "topic": topic}
            ) from e

    async def publish_alert(self, alert: AlertEvent) -> str | None:
        """Publish an alert to the alerts topic.

        Args:
            alert: The alert event to publish

        Returns:
            Published message ID or None if publishing failed
        """
        if not self.client:
            logger.warning("No Pub/Sub client configured, skipping alert publish")
            return None

        try:
            message_id = await self.client.publish(
                ALERTS_TOPIC,
                alert.model_dump(mode="json"),
                attributes={
                    "type": alert.alert_type,
                    "severity": alert.severity,
                    "event_id": str(alert.alert_id),
                    "correlation_id": str(alert.data.get("event_id", "")),
                },
            )

            logger.info(
                "Published alert",
                alert_id=str(alert.alert_id),
                alert_type=alert.alert_type,
                severity=alert.severity,
            )

            return message_id
        except Exception as e:
            logger.error(
                "Failed to publish alert",
                error=str(e),
                alert_id=str(alert.alert_id),
            )
            raise PubSubError(
                f"Failed to publish alert: {e}",
                details={"alert_id": str(alert.alert_id), "topic": ALERTS_TOPIC}
            ) from e

    async def publish_market_analysis(
        self,
        market_type: MarketType,
        analysis_data: dict[str, Any],
        event_id: UUID,
    ) -> str | None:
        """Publish market-specific analysis to dedicated topic.

        Args:
            market_type: Type of market (crypto or gold)
            analysis_data: Analysis results dictionary
            event_id: Associated event ID

        Returns:
            Published message ID or None if publishing failed
        """
        if not self.client:
            return None

        topic = (
            CRYPTO_ANALYSIS_TOPIC
            if market_type == MarketType.CRYPTO
            else GOLD_ANALYSIS_TOPIC
        )

        try:
            message_id = await self.client.publish(
                topic,
                analysis_data,
                attributes={
                    "market_type": market_type.value,
                    "event_id": str(event_id),
                },
            )

            logger.debug(
                "Published market analysis",
                market_type=market_type.value,
                event_id=str(event_id),
            )

            return message_id
        except Exception as e:
            logger.error(
                "Failed to publish market analysis",
                error=str(e),
                market_type=market_type.value,
            )
            raise PubSubError(
                f"Failed to publish market analysis: {e}",
                details={"market_type": market_type.value, "topic": topic, "event_id": str(event_id)}
            ) from e

    def _get_topic_for_event(self, processed_event: ProcessedEvent) -> str:
        """Determine the appropriate topic for a processed event.

        This can be extended to route to different topics based on
        sentiment score, source, or other criteria.
        """
        # Check metadata for market type hints
        metadata = processed_event.metadata or {}
        if metadata.get("macro_forces"):
            return GOLD_ANALYSIS_TOPIC
        
        # Default to main processed events topic
        return PROCESSED_EVENTS_TOPIC

    async def close(self) -> None:
        """Close publisher resources."""
        if self.client:
            self.client.close()
        self._initialized = False
        logger.info("Results publisher closed")


class BatchPublisher:
    """Batch publisher for high-throughput scenarios.

    Accumulates messages and publishes them in batches to reduce API calls.
    """

    def __init__(
        self,
        pubsub_client: PubSubClient,
        batch_size: int = 100,
        flush_interval_seconds: float = 5.0,
    ) -> None:
        self.client = pubsub_client
        self.batch_size = batch_size
        self.flush_interval = flush_interval_seconds
        self._buffer: list[tuple[str, dict, dict]] = []
        self._flush_task: Any = None

    async def start(self) -> None:
        """Start the periodic flush task."""
        import asyncio
        self._flush_task = asyncio.create_task(self._periodic_flush())

    async def _periodic_flush(self) -> None:
        """Periodically flush the buffer."""
        import asyncio
        while True:
            await asyncio.sleep(self.flush_interval)
            if self._buffer:
                await self._flush()

    async def publish(
        self,
        topic: str,
        data: dict,
        attributes: dict | None = None,
    ) -> None:
        """Add a message to the batch buffer."""
        self._buffer.append((topic, data, attributes or {}))
        
        if len(self._buffer) >= self.batch_size:
            await self._flush()

    async def _flush(self) -> None:
        """Flush all buffered messages."""
        if not self._buffer:
            return

        batch = self._buffer[:]
        self._buffer = []

        try:
            # Group by topic
            by_topic: dict[str, list[tuple[dict, dict]]] = {}
            for topic, data, attrs in batch:
                if topic not in by_topic:
                    by_topic[topic] = []
                by_topic[topic].append((data, attrs))

            # Publish each topic's messages
            for topic, messages in by_topic.items():
                for data, attrs in messages:
                    await self.client.publish(topic, data, attributes=attrs)

            logger.debug(f"Flushed {len(batch)} messages to Pub/Sub")
        except Exception as e:
            logger.error(f"Failed to flush batch: {e}")

    async def close(self) -> None:
        """Close the batch publisher and flush remaining messages."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except Exception:
                pass
        
        await self._flush()
        self.client.close()
