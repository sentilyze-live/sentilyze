"""Publisher for market context events."""

from typing import Any

from sentilyze_core import PubSubClient, get_logger, get_settings

from .config import get_market_context_settings

logger = get_logger(__name__)
settings = get_market_context_settings()


class MarketContextPublisher:
    """Publishes market context events to Pub/Sub."""
    
    def __init__(self, pubsub_client: PubSubClient | None = None):
        self.pubsub_client = pubsub_client
        self._owns_client = pubsub_client is None
        
    async def initialize(self) -> None:
        """Initialize the publisher."""
        if self._owns_client:
            self.pubsub_client = PubSubClient()
            
    async def close(self) -> None:
        """Close the publisher."""
        if self._owns_client and self.pubsub_client:
            self.pubsub_client.close()
            
    async def publish_regime_change(
        self,
        symbol: str,
        old_regime: str,
        new_regime: str,
        confidence: float,
        market_type: str = "generic",
    ) -> None:
        """Publish regime change event."""
        if not self.pubsub_client:
            logger.warning("PubSub client not initialized, skipping publish")
            return
            
        event = {
            "event_type": "regime_change",
            "symbol": symbol,
            "old_regime": old_regime,
            "new_regime": new_regime,
            "confidence": confidence,
            "market_type": market_type,
            "timestamp": "auto",
        }
        
        await self.pubsub_client.publish(
            settings.pubsub_market_context_topic,
            event,
            attributes={
                "event_type": "regime_change",
                "symbol": symbol,
                "market_type": market_type,
            },
        )
        
        logger.info(
            "Published regime change",
            symbol=symbol,
            old_regime=old_regime,
            new_regime=new_regime,
        )
        
    async def publish_anomaly(
        self,
        anomaly: dict[str, Any],
    ) -> None:
        """Publish anomaly detection event."""
        if not self.pubsub_client:
            logger.warning("PubSub client not initialized, skipping publish")
            return
            
        await self.pubsub_client.publish(
            settings.pubsub_anomalies_topic,
            anomaly,
            attributes={
                "event_type": "anomaly",
                "severity": anomaly.get("severity", "low"),
                "symbol": anomaly.get("symbol", "unknown"),
            },
        )
        
        logger.info(
            "Published anomaly",
            symbol=anomaly.get("symbol"),
            anomaly_type=anomaly.get("anomaly_type"),
        )
        
    async def publish_market_context(self, context_event) -> None:
        """Publish market context event to Pub/Sub.
        
        Args:
            context_event: MarketContextEvent instance
        """
        if not self.pubsub_client:
            logger.warning("PubSub client not initialized, skipping publish")
            return
        
        event_data = context_event.model_dump(mode="json")
        
        await self.pubsub_client.publish(
            settings.pubsub_market_context_topic,
            event_data,
            attributes={
                "event_type": "market_context",
                "symbol": context_event.symbol,
                "market_type": context_event.market_type,
            },
        )
        
        logger.info(
            "Published market context",
            symbol=context_event.symbol,
            sentiment_score=context_event.sentiment_score,
        )
