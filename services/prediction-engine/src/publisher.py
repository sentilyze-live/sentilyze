"""Publisher for prediction events."""

from typing import Any

from sentilyze_core import PubSubClient, get_logger

from .config import get_prediction_settings
from .models import PredictionOutcome, PredictionResult

logger = get_logger(__name__)
settings = get_prediction_settings()


class PredictionPublisher:
    """Publishes prediction events to Pub/Sub."""
    
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
            
    async def publish_prediction(self, prediction: PredictionResult | dict[str, Any]) -> None:
        """Publish new prediction.
        
        Accepts either PredictionResult model or dict.
        """
        if not self.pubsub_client:
            logger.warning("PubSub client not initialized, skipping publish")
            return
        
        if isinstance(prediction, PredictionResult):
            prediction_id = prediction.prediction_id
            symbol = prediction.symbol
            prediction_type = prediction.prediction_type
            market_type = prediction.market_type
            direction = prediction.predicted_direction.value
            confidence = str(prediction.confidence_score)
            data = prediction.to_dict()
        else:
            prediction_id = prediction.get("prediction_id", "unknown")
            symbol = prediction.get("symbol", "unknown")
            prediction_type = prediction.get("prediction_type", "generic")
            market_type = prediction.get("market_type", "generic")
            direction = prediction.get("predicted_direction", "FLAT")
            confidence = str(prediction.get("confidence", 50))
            data = prediction
            
        await self.pubsub_client.publish(
            settings.pubsub_predictions_topic,
            data,
            attributes={
                "prediction_type": prediction_type,
                "symbol": symbol,
                "market_type": market_type,
                "direction": direction,
                "confidence": confidence,
            },
        )
        
        logger.info(
            "Published prediction",
            prediction_id=prediction_id,
            symbol=symbol,
            direction=direction,
        )
        
    async def publish_outcome(self, outcome: PredictionOutcome) -> None:
        """Publish prediction outcome."""
        if not self.pubsub_client:
            logger.warning("PubSub client not initialized, skipping publish")
            return
            
        await self.pubsub_client.publish(
            settings.pubsub_predictions_outcomes_topic,
            outcome.to_dict(),
            attributes={
                "prediction_id": outcome.prediction_id,
                "success_level": outcome.success_level,
                "direction_correct": str(outcome.direction_correct),
            },
        )
        
        logger.info(
            "Published prediction outcome",
            prediction_id=outcome.prediction_id,
            success_level=outcome.success_level,
            direction_correct=outcome.direction_correct,
        )
