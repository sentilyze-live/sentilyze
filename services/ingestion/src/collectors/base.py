"""Base collector class with common interface."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

from sentilyze_core import get_logger
from sentilyze_core.exceptions import PubSubError

if TYPE_CHECKING:
    from ..publisher import EventPublisher

logger = get_logger(__name__)


class BaseCollector(ABC):
    """Base class for all data collectors.
    
    Provides common interface for initialization, collection,
    and cleanup across all collector types.
    """

    def __init__(self, publisher: "EventPublisher") -> None:
        self.publisher = publisher
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if collector is initialized."""
        return self._initialized

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the collector.
        
        Must be called before any collection operations.
        """
        pass

    @abstractmethod
    async def collect(self, **kwargs: Any) -> int:
        """Collect data from the source.
        
        Args:
            **kwargs: Source-specific collection parameters
            
        Returns:
            Number of items collected
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the collector and cleanup resources."""
        pass

    async def health_check(self) -> dict:
        """Check collector health status.
        
        Returns:
            Dictionary with health status information
        """
        return {
            "initialized": self._initialized,
            "status": "healthy" if self._initialized else "not_initialized",
        }


class BaseEventCollector(BaseCollector):
    """Base collector for event-based sources (APIs, scrapers).
    
    Extends BaseCollector with event publishing capabilities.
    """

    async def publish_events(self, events: list[Any]) -> list[str]:
        """Publish collected events to Pub/Sub.
        
        Args:
            events: List of events to publish
            
        Returns:
            List of published message IDs
            
        Raises:
            PubSubError: If any events fail to publish (after processing all events)
        """
        if not events:
            return []

        message_ids: list[str] = []
        failed_events: list[tuple[Any, Exception]] = []
        
        for event in events:
            try:
                message_id = await self.publisher.publish_raw_event(event)
                if message_id:
                    message_ids.append(message_id)
                else:
                    # Track events that return None but don't raise
                    failed_events.append((event, Exception("Publisher returned None")))
            except Exception as e:
                logger.error(
                    "Failed to publish event",
                    error=str(e),
                    collector=self.__class__.__name__,
                )
                failed_events.append((event, e))

        # Raise if any events failed after processing all events
        if failed_events:
            raise PubSubError(
                f"Failed to publish {len(failed_events)} of {len(events)} events",
                details={
                    "collector": self.__class__.__name__,
                    "total_events": len(events),
                    "failed_count": len(failed_events),
                    "successful_count": len(message_ids),
                    "errors": [str(e) for _, e in failed_events[:5]],  # First 5 errors
                }
            )

        return message_ids


class BaseStreamCollector(BaseCollector):
    """Base collector for streaming sources (WebSockets).
    
    Extends BaseCollector with streaming capabilities.
    """

    def __init__(self, publisher: "EventPublisher") -> None:
        super().__init__(publisher)
        self._streaming = False
        self._stream_task: Optional[Any] = None

    @property
    def is_streaming(self) -> bool:
        """Check if collector is currently streaming."""
        return self._streaming

    @abstractmethod
    async def start_stream(self) -> None:
        """Start the streaming connection."""
        pass

    @abstractmethod
    async def stop_stream(self) -> None:
        """Stop the streaming connection."""
        pass
