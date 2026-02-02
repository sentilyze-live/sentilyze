"""Pub/Sub message publisher for raw events."""

from typing import TYPE_CHECKING, Any

from sentilyze_core import PubSubClient, RawEvent, get_logger, get_settings
from sentilyze_core.logging import get_logger

if TYPE_CHECKING:
    from ..config import IngestionSettings

logger = get_logger(__name__)
settings: "IngestionSettings" = get_settings()

# Pub/Sub topic names
DEFAULT_RAW_EVENTS_TOPIC = "raw-events"
DEFAULT_BRONZE_TOPIC = "bronze-events"


class EventPublisher:
    """Publisher for raw events to Pub/Sub."""

    def __init__(self) -> None:
        self.client = PubSubClient()
        self._initialized = False
        self.raw_events_topic = getattr(settings, "pubsub_raw_events_topic", DEFAULT_RAW_EVENTS_TOPIC)
        self.bronze_topic = getattr(settings, "pubsub_bronze_topic", DEFAULT_BRONZE_TOPIC)

    async def initialize(self) -> None:
        """Initialize the publisher."""
        # Topic provisioning is handled by Terraform (IaC). Avoid requiring
        # pubsub.admin permissions at runtime.
        self._initialized = True
        logger.info(
            "Event publisher initialized",
            raw_events_topic=self.raw_events_topic,
            bronze_topic=self.bronze_topic,
        )

    async def publish_raw_event(self, event: RawEvent) -> str:
        """Publish a raw event to Pub/Sub.

        Args:
            event: RawEvent to publish

        Returns:
            Published message ID
        """
        if not self._initialized:
            raise RuntimeError("Publisher not initialized")

        # Convert event to dict for serialization
        event_data = event.model_dump(mode="json")

        # Add attributes for filtering
        attributes: dict[str, str] = {
            "source": str(event.source),
            "event_id": str(event.event_id),
        }

        if hasattr(event, "tenant_id") and event.tenant_id:
            attributes["tenant_id"] = event.tenant_id

        if event.symbols:
            attributes["symbols"] = ",".join(event.symbols)

        message_id = await self.client.publish(
            self.raw_events_topic,
            event_data,
            attributes,
        )

        logger.debug(
            "Published raw event",
            message_id=message_id,
            source=str(event.source),
            event_id=str(event.event_id),
        )

        return message_id

    async def publish_bronze_event(self, event: RawEvent) -> str:
        """Publish a bronze event to Pub/Sub.

        Args:
            event: RawEvent to publish to bronze topic

        Returns:
            Published message ID
        """
        if not self._initialized:
            raise RuntimeError("Publisher not initialized")

        event_data = event.model_dump(mode="json")

        attributes: dict[str, str] = {
            "source": str(event.source),
            "event_id": str(event.event_id),
            "data_type": getattr(event, "data_type", "raw"),
        }

        if event.symbols:
            attributes["symbols"] = ",".join(event.symbols)

        message_id = await self.client.publish(
            self.bronze_topic,
            event_data,
            attributes,
        )

        logger.debug(
            "Published bronze event",
            message_id=message_id,
            source=str(event.source),
        )

        return message_id

    async def publish_events(self, events: list[RawEvent]) -> list[str]:
        """Publish multiple events to Pub/Sub.

        Args:
            events: List of RawEvent objects

        Returns:
            List of published message IDs
        """
        if not events:
            return []

        message_ids: list[str] = []
        for event in events:
            try:
                message_id = await self.publish_raw_event(event)
                if message_id:
                    message_ids.append(message_id)
            except Exception as e:
                logger.error(
                    "Failed to publish event",
                    error=str(e),
                    event_id=str(event.event_id),
                )

        logger.info(
            "Published events batch",
            count=len(message_ids),
            total=len(events),
        )
        return message_ids

    async def close(self) -> None:
        """Close the publisher."""
        self.client.close()
        self._initialized = False
        logger.info("Event publisher closed")
