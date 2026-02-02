"""Pub/Sub client wrapper with async support."""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Optional

from google.cloud import pubsub_v1
from google.api_core import retry as google_retry
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import Settings, get_settings
from .exceptions import PubSubError
from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class PubSubMessage:
    """Pub/Sub message wrapper."""

    data: dict[str, Any]
    message_id: Optional[str] = None
    publish_time: Optional[str] = None
    attributes: dict[str, str] | None = None
    market_type: Optional[str] = None

    def to_json(self) -> str:
        """Convert message data to JSON string."""
        return json.dumps(self.data)

    @classmethod
    def from_pubsub_message(cls, message: Any) -> "PubSubMessage":
        """Create from Google Pub/Sub message."""
        try:
            data = json.loads(message.data.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise PubSubError(f"Invalid JSON in message: {e}")

        # Extract market type from attributes if present
        attributes = dict(message.attributes) if message.attributes else {}
        market_type = attributes.get("market_type")

        return cls(
            data=data,
            message_id=message.message_id,
            publish_time=str(message.publish_time) if message.publish_time else None,
            attributes=attributes,
            market_type=market_type,
        )


class PubSubClient:
    """Async Pub/Sub client with connection pooling and market support."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.project_id = self.settings.pubsub_project_id
        self._publisher: Optional[pubsub_v1.PublisherClient] = None
        self._subscriber: Optional[pubsub_v1.SubscriberClient] = None

    @property
    def publisher(self) -> pubsub_v1.PublisherClient:
        """Get or create publisher client."""
        if self._publisher is None:
            self._publisher = pubsub_v1.PublisherClient()
        return self._publisher

    @property
    def subscriber(self) -> pubsub_v1.SubscriberClient:
        """Get or create subscriber client."""
        if self._subscriber is None:
            self._subscriber = pubsub_v1.SubscriberClient()
        return self._subscriber

    def _get_topic_path(self, topic_id: str) -> str:
        """Get full topic path."""
        return self.publisher.topic_path(self.project_id, topic_id)

    def _get_subscription_path(self, subscription_id: str) -> str:
        """Get full subscription path."""
        return self.subscriber.subscription_path(self.project_id, subscription_id)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def publish(
        self,
        topic_id: str,
        data: dict[str, Any],
        attributes: Optional[dict[str, str]] = None,
        market_type: Optional[str] = None,
    ) -> str:
        """Publish message to topic.

        Args:
            topic_id: Topic name
            data: Message payload
            attributes: Message attributes
            market_type: Optional market type tag (crypto, gold, etc.)

        Returns:
            Published message ID

        Raises:
            PubSubError: If publish fails
        """
        topic_path = self._get_topic_path(topic_id)
        message_data = json.dumps(data).encode("utf-8")

        # Add market type to attributes
        final_attributes = attributes or {}
        if market_type:
            final_attributes["market_type"] = market_type

        try:
            future = self.publisher.publish(
                topic_path,
                message_data,
                **final_attributes,
            )
            message_id = await asyncio.to_thread(future.result, 30)
            logger.debug(
                "Published message",
                topic=topic_id,
                message_id=message_id,
                market_type=market_type,
            )
            return message_id
        except Exception as e:
            logger.error("Failed to publish message", topic=topic_id, error=str(e))
            raise PubSubError(f"Failed to publish to {topic_id}: {e}")

    async def subscribe(
        self,
        subscription_id: str,
        callback: Callable[[PubSubMessage], Coroutine[Any, Any, None]],
        max_messages: int = 100,
        market_filter: Optional[str] = None,
    ) -> Any:
        """Subscribe to messages.

        Args:
            subscription_id: Subscription name
            callback: Async callback function
            max_messages: Maximum concurrent messages
            market_filter: Optional filter for market type (crypto, gold, etc.)

        Returns:
            Streaming pull future
        """
        subscription_path = self._get_subscription_path(subscription_id)

        def wrapper(message: Any) -> None:
            """Wrap async callback."""
            import asyncio

            try:
                pubsub_message = PubSubMessage.from_pubsub_message(message)
                
                # Apply market filter if specified
                if market_filter and pubsub_message.market_type != market_filter:
                    message.ack()
                    return
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(callback(pubsub_message))
                message.ack()
                logger.debug(
                    "Message acknowledged",
                    subscription=subscription_id,
                    message_id=pubsub_message.message_id,
                )
            except Exception as e:
                logger.error(
                    "Message processing failed",
                    subscription=subscription_id,
                    error=str(e),
                )
                message.nack()

        flow_control = pubsub_v1.types.FlowControl(max_messages=max_messages)

        try:
            streaming_pull_future = self.subscriber.subscribe(
                subscription_path,
                callback=wrapper,
                flow_control=flow_control,
                await_callbacks_on_shutdown=True,
            )
            logger.info(
                "Started subscription",
                subscription=subscription_id,
                market_filter=market_filter,
            )
            return streaming_pull_future
        except Exception as e:
            raise PubSubError(f"Failed to subscribe to {subscription_id}: {e}")

    async def create_topic(self, topic_id: str) -> str:
        """Create a new topic.

        Args:
            topic_id: Topic name

        Returns:
            Topic path
        """
        topic_path = self._get_topic_path(topic_id)

        try:
            topic = self.publisher.create_topic(request={"name": topic_path})
            logger.info("Created topic", topic=topic_id)
            return topic.name
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.debug("Topic already exists", topic=topic_id)
                return topic_path
            raise PubSubError(f"Failed to create topic {topic_id}: {e}")

    async def create_subscription(
        self,
        topic_id: str,
        subscription_id: str,
        dead_letter_topic: Optional[str] = None,
        max_delivery_attempts: int = 5,
    ) -> str:
        """Create a new subscription.

        Args:
            topic_id: Topic name
            subscription_id: Subscription name
            dead_letter_topic: Optional dead letter topic
            max_delivery_attempts: Max delivery attempts before DLQ

        Returns:
            Subscription path
        """
        topic_path = self._get_topic_path(topic_id)
        subscription_path = self._get_subscription_path(subscription_id)

        subscription_config = {
            "name": subscription_path,
            "topic": topic_path,
            "ack_deadline_seconds": 60,
        }

        if dead_letter_topic:
            dlq_path = self._get_topic_path(dead_letter_topic)
            subscription_config["dead_letter_policy"] = {
                "dead_letter_topic": dlq_path,
                "max_delivery_attempts": max_delivery_attempts,
            }

        try:
            subscription = self.subscriber.create_subscription(
                request=subscription_config
            )
            logger.info(
                "Created subscription",
                subscription=subscription_id,
                topic=topic_id,
            )
            return subscription.name
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.debug("Subscription already exists", subscription=subscription_id)
                return subscription_path
            raise PubSubError(f"Failed to create subscription {subscription_id}: {e}")

    def close(self) -> None:
        """Close client connections."""
        if self._publisher:
            self._publisher.transport.close()
            self._publisher = None
        if self._subscriber:
            self._subscriber.close()
            self._subscriber = None
        logger.debug("PubSub client closed")

    async def __aenter__(self) -> "PubSubClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        self.close()
