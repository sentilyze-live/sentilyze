"""Pub/Sub client for real-time event streaming."""

import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import structlog
from google.cloud import pubsub_v1
from google.api_core import retry as google_retry

from src.config import settings

logger = structlog.get_logger(__name__)


class PubSubDataClient:
    """Client for Pub/Sub operations."""

    # Topic names
    TOPIC_TRENDS = "agent-os-trends"
    TOPIC_CONTENT = "agent-os-content"
    TOPIC_EXPERIMENTS = "agent-os-experiments"
    TOPIC_COMMUNITY = "agent-os-community"
    TOPIC_VISUALS = "agent-os-visuals"

    def __init__(self, project_id: Optional[str] = None):
        """Initialize Pub/Sub client.

        Args:
            project_id: GCP project ID
        """
        self.project_id = project_id or settings.PUBSUB_PROJECT_ID

        if settings.PUBSUB_EMULATOR_HOST:
            # Use emulator for local development
            import os
            os.environ["PUBSUB_EMULATOR_HOST"] = settings.PUBSUB_EMULATOR_HOST

        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()

        logger.info("pubsub_client.initialized", project=self.project_id)

    def _get_topic_path(self, topic_name: str) -> str:
        """Get full topic path."""
        return self.publisher.topic_path(self.project_id, topic_name)

    def _get_subscription_path(self, subscription_name: str) -> str:
        """Get full subscription path."""
        return self.subscriber.subscription_path(self.project_id, subscription_name)

    async def publish_trend(
        self,
        trend_data: Dict[str, Any],
        agent_name: str = "SCOUT",
    ) -> str:
        """Publish trend event.

        Args:
            trend_data: Trend data
            agent_name: Name of the agent

        Returns:
            Message ID
        """
        message = {
            "type": "trend_detected",
            "agent": agent_name,
            "data": trend_data,
            "timestamp": json.dumps(json.loads(json.dumps({}), default=str)),
        }

        return await self._publish(self.TOPIC_TRENDS, message)

    async def publish_content(
        self,
        content_data: Dict[str, Any],
        agent_name: str,
        status: str = "created",
    ) -> str:
        """Publish content event.

        Args:
            content_data: Content data
            agent_name: Name of the agent
            status: Content status

        Returns:
            Message ID
        """
        message = {
            "type": "content_update",
            "agent": agent_name,
            "status": status,
            "data": content_data,
        }

        return await self._publish(self.TOPIC_CONTENT, message)

    async def publish_experiment(
        self,
        experiment_data: Dict[str, Any],
        agent_name: str = "ELON",
    ) -> str:
        """Publish experiment event.

        Args:
            experiment_data: Experiment data
            agent_name: Name of the agent

        Returns:
            Message ID
        """
        message = {
            "type": "experiment_proposed",
            "agent": agent_name,
            "data": experiment_data,
        }

        return await self._publish(self.TOPIC_EXPERIMENTS, message)

    async def publish_community(
        self,
        engagement_data: Dict[str, Any],
        agent_name: str = "ZARA",
    ) -> str:
        """Publish community engagement event.

        Args:
            engagement_data: Engagement data
            agent_name: Name of the agent

        Returns:
            Message ID
        """
        message = {
            "type": "community_engagement",
            "agent": agent_name,
            "data": engagement_data,
        }

        return await self._publish(self.TOPIC_COMMUNITY, message)

    async def publish_visual(
        self,
        visual_data: Dict[str, Any],
        agent_name: str = "ECE",
    ) -> str:
        """Publish visual content event.

        Args:
            visual_data: Visual data
            agent_name: Name of the agent

        Returns:
            Message ID
        """
        message = {
            "type": "visual_created",
            "agent": agent_name,
            "data": visual_data,
        }

        return await self._publish(self.TOPIC_VISUALS, message)

    async def _publish(
        self,
        topic_name: str,
        message: Dict[str, Any],
    ) -> str:
        """Publish message to topic.

        Args:
            topic_name: Topic name
            message: Message data

        Returns:
            Message ID
        """
        try:
            topic_path = self._get_topic_path(topic_name)

            # Encode message
            data = json.dumps(message).encode("utf-8")

            # Publish with retry
            future = self.publisher.publish(topic_path, data)
            message_id = future.result()

            logger.debug(
                "pubsub.message_published",
                topic=topic_name,
                message_id=message_id,
            )

            return message_id

        except Exception as e:
            logger.error(
                "pubsub.publish_error",
                topic=topic_name,
                error=str(e),
            )
            raise

    def subscribe_to_trends(
        self,
        callback: Callable[[Dict[str, Any]], None],
        subscription_name: Optional[str] = None,
    ) -> str:
        """Subscribe to trend events.

        Args:
            callback: Callback function for messages
            subscription_name: Subscription name (auto-generated if None)

        Returns:
            Subscription path
        """
        if subscription_name is None:
            subscription_name = f"agent-os-trends-sub-{settings.ENVIRONMENT}"

        return self._subscribe(self.TOPIC_TRENDS, subscription_name, callback)

    def subscribe_to_content(
        self,
        callback: Callable[[Dict[str, Any]], None],
        subscription_name: Optional[str] = None,
    ) -> str:
        """Subscribe to content events.

        Args:
            callback: Callback function
            subscription_name: Subscription name

        Returns:
            Subscription path
        """
        if subscription_name is None:
            subscription_name = f"agent-os-content-sub-{settings.ENVIRONMENT}"

        return self._subscribe(self.TOPIC_CONTENT, subscription_name, callback)

    def _subscribe(
        self,
        topic_name: str,
        subscription_name: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> str:
        """Subscribe to topic.

        Args:
            topic_name: Topic name
            subscription_name: Subscription name
            callback: Callback function

        Returns:
            Subscription path
        """
        try:
            topic_path = self._get_topic_path(topic_name)
            subscription_path = self._get_subscription_path(subscription_name)

            # Create subscription if it doesn't exist
            try:
                self.subscriber.create_subscription(
                    request={
                        "name": subscription_path,
                        "topic": topic_path,
                    }
                )
                logger.info(
                    "pubsub.subscription_created",
                    subscription=subscription_name,
                    topic=topic_name,
                )
            except Exception:
                # Subscription already exists
                pass

            # Define callback wrapper
            def callback_wrapper(message):
                try:
                    data = json.loads(message.data.decode("utf-8"))
                    callback(data)
                    message.ack()
                except Exception as e:
                    logger.error("pubsub.callback_error", error=str(e))
                    message.nack()

            # Start streaming pull
            streaming_pull_future = self.subscriber.subscribe(
                subscription_path,
                callback=callback_wrapper,
            )

            logger.info(
                "pubsub.subscribed",
                subscription=subscription_name,
                topic=topic_name,
            )

            return subscription_path

        except Exception as e:
            logger.error(
                "pubsub.subscribe_error",
                topic=topic_name,
                error=str(e),
            )
            raise

    async def create_topics(self) -> List[str]:
        """Create all required topics.

        Returns:
            List of created topic names
        """
        topics = [
            self.TOPIC_TRENDS,
            self.TOPIC_CONTENT,
            self.TOPIC_EXPERIMENTS,
            self.TOPIC_COMMUNITY,
            self.TOPIC_VISUALS,
        ]

        created = []
        for topic_name in topics:
            try:
                topic_path = self._get_topic_path(topic_name)
                self.publisher.create_topic(request={"name": topic_path})
                created.append(topic_name)
                logger.info("pubsub.topic_created", topic=topic_name)
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.debug("pubsub.topic_exists", topic=topic_name)
                else:
                    logger.error("pubsub.topic_create_error", topic=topic_name, error=str(e))

        return created

    # New topics for agent coordination
    TOPIC_AGENT_DIRECTIVES = "agent-os-directives"
    TOPIC_AGENT_REQUESTS = "agent-os-requests"
    TOPIC_PREDICTIONS = "agent-os-predictions"
    TOPIC_STRATEGY = "agent-os-strategy"
    TOPIC_COMMUNITY_INSIGHTS = "agent-os-community-insights"

    async def publish_agent_directive(
        self,
        target_agent: str,
        directive: Dict[str, Any],
        source_agent: str,
    ) -> str:
        """Publish agent directive for inter-agent coordination.

        Args:
            target_agent: Target agent name
            directive: Directive data
            source_agent: Source agent name

        Returns:
            Message ID
        """
        message = {
            "type": "agent_directive",
            "source": source_agent,
            "target": target_agent,
            "directive": directive,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return await self._publish(self.TOPIC_AGENT_DIRECTIVES, message)

    async def publish_agent_request(
        self,
        target_agent: str,
        requests: Dict[str, Any],
        source_agent: str,
    ) -> str:
        """Publish agent request for support.

        Args:
            target_agent: Target agent name
            requests: Request data
            source_agent: Source agent name

        Returns:
            Message ID
        """
        message = {
            "type": "agent_request",
            "source": source_agent,
            "target": target_agent,
            "requests": requests,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return await self._publish(self.TOPIC_AGENT_REQUESTS, message)

    async def publish_prediction(
        self,
        prediction: Dict[str, Any],
        agent_name: str = "ORACLE",
    ) -> str:
        """Publish prediction/validation event.

        Args:
            prediction: Prediction data with statistics
            agent_name: Name of the agent (default ORACLE)

        Returns:
            Message ID
        """
        message = {
            "type": "prediction_validated",
            "agent": agent_name,
            "prediction": prediction,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return await self._publish(self.TOPIC_PREDICTIONS, message)

    async def publish_strategy_update(
        self,
        recommendations: Dict[str, Any],
        agent_name: str = "SETH",
    ) -> str:
        """Publish content strategy update.

        Args:
            recommendations: Strategy recommendations
            agent_name: Name of the agent (default SETH)

        Returns:
            Message ID
        """
        message = {
            "type": "strategy_update",
            "agent": agent_name,
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return await self._publish(self.TOPIC_STRATEGY, message)

    async def publish_community_insights(
        self,
        insights: Dict[str, Any],
        agent_name: str = "ZARA",
    ) -> str:
        """Publish community insights.

        Args:
            insights: Community insights data
            agent_name: Name of the agent (default ZARA)

        Returns:
            Message ID
        """
        message = {
            "type": "community_insights",
            "agent": agent_name,
            "insights": insights,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return await self._publish(self.TOPIC_COMMUNITY_INSIGHTS, message)
