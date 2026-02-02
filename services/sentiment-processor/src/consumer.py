"""Pub/Sub consumer for streaming processing.

This module provides message consumption capabilities for the
sentiment processor using Google Cloud Pub/Sub.
"""

import asyncio
from typing import Callable, Any

from sentilyze_core import PubSubClient, PubSubMessage, get_logger, get_settings
from sentilyze_core.exceptions import ExternalServiceError, PubSubError

logger = get_logger(__name__)
settings = get_settings()

# Default max retries before sending to DLQ
DEFAULT_MAX_RETRIES = 3


class DeadLetterQueueHandler:
    """Handles messages that fail processing and should be retried or archived."""

    def __init__(
        self,
        pubsub_client: PubSubClient,
        dlq_topic: str = "dlq-events",
        max_retries: int = 3,
    ) -> None:
        self.client = pubsub_client
        self.dlq_topic = dlq_topic
        self.max_retries = max_retries

    async def send_to_dlq(
        self,
        message: PubSubMessage,
        error: Exception,
        retry_count: int = 0,
    ) -> None:
        """Send a failed message to the dead letter queue.

        Args:
            message: The original message that failed
            error: The exception that caused the failure
            retry_count: Number of retry attempts made
        """
        try:
            dlq_payload = {
                "original_message": message.data,
                "error": str(error),
                "error_type": type(error).__name__,
                "retry_count": retry_count,
                "message_id": message.message_id,
                "attributes": message.attributes,
            }
            
            await self.client.publish(
                self.dlq_topic,
                dlq_payload,
                attributes={
                    "dlq_source": "sentiment_processor",
                    "original_message_id": message.message_id,
                    "retry_count": str(retry_count),
                },
            )
            
            logger.info(
                f"Message sent to DLQ",
                message_id=message.message_id,
                error_type=type(error).__name__,
            )
        except Exception as e:
            logger.error(
                f"Failed to send message to DLQ: {e}",
                message_id=message.message_id,
            )


class PubSubConsumer:
    """Pub/Sub message consumer for streaming processing.
    
    This consumer supports both push subscription (HTTP) and pull subscription
    modes, with automatic acknowledgment handling and error recovery.
    Implements retry logic with DLQ for messages that exceed max retries.
    """

    def __init__(
        self,
        pubsub_client: PubSubClient,
        subscription_id: str,
        message_handler: Callable[[PubSubMessage], Any],
        dlq_handler: DeadLetterQueueHandler | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """Initialize the Pub/Sub consumer.

        Args:
            pubsub_client: Configured PubSubClient instance
            subscription_id: Full subscription path or ID
            message_handler: Async function to process messages
            dlq_handler: Optional DLQ handler for failed messages
            max_retries: Maximum retry attempts before sending to DLQ
        """
        self.client = pubsub_client
        self.subscription_id = subscription_id
        self.message_handler = message_handler
        self.dlq_handler = dlq_handler
        self.max_retries = max_retries
        self._running = False
        self._shutdown_event: asyncio.Event | None = None
        self._retry_counts: dict[str, int] = {}  # message_id -> retry count

    async def start_pull_consumer(self) -> None:
        """Start a pull-based consumer loop.
        
        Note: Pull mode is NOT recommended for Cloud Run. Use push mode instead.
        """
        self._running = True
        self._shutdown_event = asyncio.Event()
        
        logger.info(f"Starting pull consumer for {self.subscription_id}")
        
        while self._running:
            try:
                messages = await self._pull_messages()
                if messages:
                    await self._process_batch(messages)
                else:
                    await asyncio.sleep(1.0)
            except Exception as e:
                logger.error(f"Consumer error: {e}")
                await asyncio.sleep(5.0)
        
        logger.info("Pull consumer stopped")

    async def _pull_messages(self) -> list[PubSubMessage]:
        """Pull messages from the subscription."""
        try:
            return await self.client.pull(self.subscription_id, max_messages=100)
        except Exception as e:
            logger.error(f"Failed to pull messages: {e}")
            return []

    async def _process_batch(self, messages: list[PubSubMessage]) -> None:
        """Process a batch of messages with retry tracking and DLQ support."""
        ack_ids = []
        nack_ids = []  # Messages to not acknowledge (for retry)
        
        for message in messages:
            msg_id = message.message_id
            retry_count = self._retry_counts.get(msg_id, 0)
            
            try:
                await self.message_handler(message)
                if hasattr(message, 'ack_id'):
                    ack_ids.append(message.ack_id)
                # Clear retry count on success
                if msg_id in self._retry_counts:
                    del self._retry_counts[msg_id]
                    
            except Exception as e:
                retry_count += 1
                self._retry_counts[msg_id] = retry_count
                
                if retry_count >= self.max_retries:
                    # Max retries exceeded - send to DLQ
                    logger.error(
                        f"Max retries ({self.max_retries}) exceeded for message",
                        message_id=msg_id,
                        error=str(e),
                    )
                    
                    if self.dlq_handler:
                        try:
                            await self.dlq_handler.send_to_dlq(message, e, retry_count)
                        except Exception as dlq_error:
                            logger.error(
                                f"Failed to send message to DLQ: {dlq_error}",
                                message_id=msg_id,
                            )
                    
                    # Acknowledge to prevent infinite retry
                    if hasattr(message, 'ack_id'):
                        ack_ids.append(message.ack_id)
                    
                    # Clean up retry count
                    del self._retry_counts[msg_id]
                else:
                    # Don't acknowledge - let it retry
                    logger.warning(
                        f"Message processing failed, will retry",
                        message_id=msg_id,
                        retry_count=retry_count,
                        max_retries=self.max_retries,
                        error=str(e),
                    )
                    if hasattr(message, 'ack_id'):
                        nack_ids.append(message.ack_id)
        
        # Acknowledge successfully processed messages
        if ack_ids:
            try:
                await self.client.acknowledge(self.subscription_id, ack_ids)
            except Exception as e:
                logger.error(f"Failed to acknowledge messages: {e}")
        
        # Modify ack deadline for messages to retry (NACK)
        if nack_ids:
            try:
                # Setting ack deadline to 0 makes the message immediately available for redelivery
                await self.client.modify_ack_deadline(self.subscription_id, nack_ids, 0)
            except Exception as e:
                logger.error(f"Failed to modify ack deadline for retry: {e}")

    async def stop(self) -> None:
        """Stop the consumer gracefully."""
        logger.info("Stopping Pub/Sub consumer...")
        self._running = False
        if self._shutdown_event:
            self._shutdown_event.set()

    async def close(self) -> None:
        """Close consumer resources."""
        await self.stop()


class MessageRouter:
    """Routes messages to appropriate handlers based on content type."""

    def __init__(self) -> None:
        self.handlers: dict[str, Callable[[PubSubMessage], Any]] = {}

    def register_handler(
        self,
        content_type: str,
        handler: Callable[[PubSubMessage], Any],
    ) -> None:
        """Register a handler for a specific content type."""
        self.handlers[content_type] = handler
        logger.info(f"Registered handler for content type: {content_type}")

    async def route(self, message: PubSubMessage) -> None:
        """Route a message to the appropriate handler."""
        content_type = message.attributes.get("content_type", "default")
        handler = self.handlers.get(content_type)
        
        if handler:
            await handler(message)
        else:
            default_handler = self.handlers.get("default")
            if default_handler:
                await default_handler(message)
            else:
                logger.warning(f"No handler for content type: {content_type}")
