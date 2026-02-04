"""Firestore client for caching and real-time data."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from google.cloud import firestore

from src.config import settings

logger = structlog.get_logger(__name__)


class FirestoreDataClient:
    """Client for Firestore operations."""

    def __init__(self, project_id: Optional[str] = None):
        """Initialize Firestore client.

        Args:
            project_id: GCP project ID
        """
        self.project_id = project_id or settings.FIRESTORE_PROJECT_ID

        if settings.FIRESTORE_EMULATOR_HOST:
            # Use emulator for local development
            import os

            os.environ["FIRESTORE_EMULATOR_HOST"] = settings.FIRESTORE_EMULATOR_HOST
            self.client = firestore.Client(project=self.project_id)
            logger.info("firestore_client.emulator_mode", host=settings.FIRESTORE_EMULATOR_HOST)
        else:
            self.client = firestore.Client(project=self.project_id)
            logger.info("firestore_client.initialized", project=self.project_id)

        # Collection references
        self.conversations_collection = self.client.collection("agent_os_conversations")
        self.messages_collection = self.client.collection("agent_os_messages")
        self.trends_collection = self.client.collection("agent_os_trends")
        self.content_collection = self.client.collection("agent_os_content")
        self.experiments_collection = self.client.collection("agent_os_experiments")
        self.community_collection = self.client.collection("agent_os_community")
        self.cache_collection = self.client.collection("agent_os_cache")
        self.agent_state_collection = self.client.collection("agent_os_state")
        self.predictions_collection = self.client.collection("agent_os_predictions")

    async def cache_set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
    ) -> None:
        """Set cache value with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
        """
        try:
            expires_at = datetime.utcnow().timestamp() + ttl_seconds

            self.cache_collection.document(key).set({
                "value": value,
                "expires_at": expires_at,
                "created_at": datetime.utcnow(),
            })

            logger.debug("firestore.cache_set", key=key, ttl=ttl_seconds)

        except Exception as e:
            logger.error("firestore.cache_set_error", key=key, error=str(e))

    async def cache_get(self, key: str) -> Optional[Any]:
        """Get cached value.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        try:
            doc = self.cache_collection.document(key).get()

            if not doc.exists:
                return None

            data = doc.to_dict()
            expires_at = data.get("expires_at", 0)

            if datetime.utcnow().timestamp() > expires_at:
                # Expired
                self.cache_collection.document(key).delete()
                return None

            logger.debug("firestore.cache_hit", key=key)
            return data.get("value")

        except Exception as e:
            logger.error("firestore.cache_get_error", key=key, error=str(e))
            return None

    async def save_trend(
        self,
        trend_id: str,
        trend_data: Dict[str, Any],
    ) -> None:
        """Save trend data.

        Args:
            trend_id: Unique trend ID
            trend_data: Trend data
        """
        try:
            trend_data["updated_at"] = datetime.utcnow()
            trend_data["status"] = trend_data.get("status", "active")

            self.trends_collection.document(trend_id).set(trend_data, merge=True)

            logger.info("firestore.trend_saved", trend_id=trend_id)

        except Exception as e:
            logger.error("firestore.trend_save_error", trend_id=trend_id, error=str(e))

    async def get_trends(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get trends from Firestore.

        Args:
            status: Filter by status
            limit: Maximum results

        Returns:
            List of trends
        """
        try:
            query = self.trends_collection.order_by("updated_at", direction=firestore.Query.DESCENDING)

            if status:
                query = query.where("status", "==", status)

            docs = query.limit(limit).stream()

            trends = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                trends.append(data)

            logger.debug("firestore.trends_loaded", count=len(trends))
            return trends

        except Exception as e:
            logger.error("firestore.trends_load_error", error=str(e))
            return []

    async def save_content(
        self,
        content_id: str,
        content_data: Dict[str, Any],
    ) -> None:
        """Save content data.

        Args:
            content_id: Unique content ID
            content_data: Content data
        """
        try:
            content_data["updated_at"] = datetime.utcnow()

            self.content_collection.document(content_id).set(content_data, merge=True)

            logger.info("firestore.content_saved", content_id=content_id)

        except Exception as e:
            logger.error("firestore.content_save_error", content_id=content_id, error=str(e))

    async def get_content(
        self,
        content_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get content from Firestore.

        Args:
            content_type: Filter by type (blog, reel, post)
            status: Filter by status
            limit: Maximum results

        Returns:
            List of content
        """
        try:
            query = self.content_collection.order_by("updated_at", direction=firestore.Query.DESCENDING)

            if content_type:
                query = query.where("content_type", "==", content_type)

            if status:
                query = query.where("status", "==", status)

            docs = query.limit(limit).stream()

            content = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                content.append(data)

            return content

        except Exception as e:
            logger.error("firestore.content_load_error", error=str(e))
            return []

    async def save_experiment(
        self,
        experiment_id: str,
        experiment_data: Dict[str, Any],
    ) -> None:
        """Save experiment data.

        Args:
            experiment_id: Unique experiment ID
            experiment_data: Experiment data
        """
        try:
            experiment_data["updated_at"] = datetime.utcnow()

            self.experiments_collection.document(experiment_id).set(
                experiment_data, merge=True
            )

            logger.info("firestore.experiment_saved", experiment_id=experiment_id)

        except Exception as e:
            logger.error(
                "firestore.experiment_save_error",
                experiment_id=experiment_id,
                error=str(e),
            )

    async def get_experiments(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get experiments from Firestore.

        Args:
            status: Filter by status (proposed, running, completed)
            limit: Maximum results

        Returns:
            List of experiments
        """
        try:
            query = self.experiments_collection.order_by(
                "updated_at", direction=firestore.Query.DESCENDING
            )

            if status:
                query = query.where("status", "==", status)

            docs = query.limit(limit).stream()

            experiments = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                experiments.append(data)

            return experiments

        except Exception as e:
            logger.error("firestore.experiments_load_error", error=str(e))
            return []

    async def save_agent_state(
        self,
        agent_name: str,
        state: Dict[str, Any],
    ) -> None:
        """Save agent state.

        Args:
            agent_name: Name of the agent
            state: Agent state
        """
        try:
            state["updated_at"] = datetime.utcnow()
            state["agent_name"] = agent_name

            self.agent_state_collection.document(agent_name).set(state, merge=True)

            logger.debug("firestore.agent_state_saved", agent=agent_name)

        except Exception as e:
            logger.error("firestore.agent_state_error", agent=agent_name, error=str(e))

    async def get_agent_state(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get agent state.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent state or None
        """
        try:
            doc = self.agent_state_collection.document(agent_name).get()

            if not doc.exists:
                return None

            data = doc.to_dict()
            data["id"] = doc.id
            return data

        except Exception as e:
            logger.error("firestore.agent_state_load_error", agent=agent_name, error=str(e))
            return None

    async def save_community_engagement(
        self,
        engagement_id: str,
        engagement_data: Dict[str, Any],
    ) -> None:
        """Save community engagement data.

        Args:
            engagement_id: Unique engagement ID
            engagement_data: Engagement data
        """
        try:
            engagement_data["updated_at"] = datetime.utcnow()

            self.community_collection.document(engagement_id).set(
                engagement_data, merge=True
            )

            logger.info("firestore.engagement_saved", engagement_id=engagement_id)

        except Exception as e:
            logger.error(
                "firestore.engagement_save_error",
                engagement_id=engagement_id,
                error=str(e),
            )

    async def get_vip_followers(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get VIP followers (most engaged).

        Args:
            limit: Maximum results

        Returns:
            List of VIP followers
        """
        try:
            query = (
                self.community_collection.where("tier", "in", ["advocate", "ambassador"])
                .order_by("engagement_score", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            docs = query.stream()

            followers = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                followers.append(data)

            return followers

        except Exception as e:
            logger.error("firestore.vip_followers_error", error=str(e))
            return []

    async def save_prediction(
        self,
        prediction_id: str,
        prediction_data: Dict[str, Any],
    ) -> None:
        """Save prediction/validation data.

        Args:
            prediction_id: Unique prediction ID
            prediction_data: Prediction data including statistics
        """
        try:
            prediction_data["updated_at"] = datetime.utcnow()
            prediction_data["status"] = prediction_data.get("status", "active")

            self.predictions_collection.document(prediction_id).set(
                prediction_data, merge=True
            )

            logger.info("firestore.prediction_saved", prediction_id=prediction_id)

        except Exception as e:
            logger.error(
                "firestore.prediction_save_error",
                prediction_id=prediction_id,
                error=str(e),
            )

    async def get_predictions(
        self,
        status: Optional[str] = None,
        validated: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get predictions from Firestore.

        Args:
            status: Filter by status
            validated: Filter by validation status
            limit: Maximum results

        Returns:
            List of predictions
        """
        try:
            query = self.predictions_collection.order_by(
                "updated_at", direction=firestore.Query.DESCENDING
            )

            if status:
                query = query.where("status", "==", status)

            if validated is not None:
                query = query.where("validated", "==", validated)

            docs = query.limit(limit).stream()

            predictions = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                predictions.append(data)

            logger.debug("firestore.predictions_loaded", count=len(predictions))
            return predictions

        except Exception as e:
            logger.error("firestore.predictions_load_error", error=str(e))
            return []

    async def get_community_engagements(
        self,
        platform: Optional[str] = None,
        hours: Optional[int] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Get community engagements.

        Args:
            platform: Filter by platform
            hours: Filter by recent hours
            limit: Maximum results

        Returns:
            List of engagements
        """
        try:
            query = self.community_collection.order_by(
                "timestamp", direction=firestore.Query.DESCENDING
            )

            if platform:
                query = query.where("platform", "==", platform)

            if hours:
                from datetime import datetime, timedelta
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                query = query.where("timestamp", ">=", cutoff.isoformat())

            docs = query.limit(limit).stream()

            engagements = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                engagements.append(data)

            logger.debug("firestore.engagements_loaded", count=len(engagements))
            return engagements

        except Exception as e:
            logger.error("firestore.engagements_load_error", error=str(e))
            return []

    async def save_vip_follower(
        self,
        vip_id: str,
        vip_data: Dict[str, Any],
    ) -> None:
        """Save VIP follower data.

        Args:
            vip_id: Unique VIP identifier
            vip_data: VIP data including tier and scores
        """
        try:
            vip_data["updated_at"] = datetime.utcnow()

            # Save to community collection with VIP prefix
            self.community_collection.document(f"vip-{vip_id}").set(
                vip_data, merge=True
            )

            logger.info("firestore.vip_saved", vip_id=vip_id)

        except Exception as e:
            logger.error("firestore.vip_save_error", vip_id=vip_id, error=str(e))

    async def get_leads(
        self,
        hours: Optional[int] = None,
        tier: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get qualified leads.

        Args:
            hours: Filter by recent hours
            tier: Filter by lead tier (Hot/Warm/Cold)
            limit: Maximum results

        Returns:
            List of leads
        """
        try:
            query = self.community_collection.where("lead_qualified", "==", True)

            if tier:
                query = query.where("lead_tier", "==", tier)

            if hours:
                from datetime import datetime, timedelta
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                query = query.where("timestamp", ">=", cutoff.isoformat())

            query = query.order_by("timestamp", direction=firestore.Query.DESCENDING)
            docs = query.limit(limit).stream()

            leads = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                leads.append(data)

            logger.debug("firestore.leads_loaded", count=len(leads))
            return leads

        except Exception as e:
            logger.error("firestore.leads_load_error", error=str(e))
            return []

    # Generic document operations for structured memory
    async def get_document(
        self,
        collection: str,
        document_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a document from any collection.

        Args:
            collection: Collection name
            document_id: Document ID

        Returns:
            Document data or None
        """
        try:
            doc_ref = self.client.collection(collection).document(document_id)
            doc = doc_ref.get()

            if not doc.exists:
                return None

            data = doc.to_dict()
            data["id"] = doc.id
            return data

        except Exception as e:
            logger.error("firestore.get_document_error", collection=collection, document_id=document_id, error=str(e))
            return None

    async def set_document(
        self,
        collection: str,
        document_id: str,
        data: Dict[str, Any],
        merge: bool = True,
    ) -> None:
        """Set a document in any collection.

        Args:
            collection: Collection name
            document_id: Document ID
            data: Document data
            merge: Whether to merge with existing data
        """
        try:
            doc_ref = self.client.collection(collection).document(document_id)
            
            if merge:
                doc_ref.set(data, merge=True)
            else:
                doc_ref.set(data)

            logger.debug("firestore.document_set", collection=collection, document_id=document_id)

        except Exception as e:
            logger.error("firestore.set_document_error", collection=collection, document_id=document_id, error=str(e))

    async def delete_document(
        self,
        collection: str,
        document_id: str,
    ) -> None:
        """Delete a document from any collection.

        Args:
            collection: Collection name
            document_id: Document ID
        """
        try:
            doc_ref = self.client.collection(collection).document(document_id)
            doc_ref.delete()

            logger.info("firestore.document_deleted", collection=collection, document_id=document_id)

        except Exception as e:
            logger.error("firestore.delete_document_error", collection=collection, document_id=document_id, error=str(e))

    # ═══════════════════════════════════════════════════════════════════
    # Conversation Management Methods
    # ═══════════════════════════════════════════════════════════════════

    async def save_conversation(
        self,
        conversation_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Save or update conversation data.

        Args:
            conversation_id: Unique conversation ID
            data: Conversation data
        """
        try:
            data["updated_at"] = datetime.utcnow()
            self.conversations_collection.document(conversation_id).set(data, merge=True)
            logger.debug("firestore.conversation_saved", conversation_id=conversation_id)
        except Exception as e:
            logger.error("firestore.conversation_save_error", conversation_id=conversation_id, error=str(e))

    async def get_conversation(
        self,
        conversation_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation data or None
        """
        try:
            doc = self.conversations_collection.document(conversation_id).get()
            if doc.exists:
                data = doc.to_dict()
                data["conversation_id"] = doc.id
                return data
            return None
        except Exception as e:
            logger.error("firestore.conversation_get_error", conversation_id=conversation_id, error=str(e))
            return None

    async def get_active_conversation(
        self,
        chat_id: str,
        agent_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Find active conversation for a chat+agent pair.

        Args:
            chat_id: Telegram chat ID
            agent_type: Agent type

        Returns:
            Active conversation data or None
        """
        try:
            query = (
                self.conversations_collection
                .where("chat_id", "==", chat_id)
                .where("agent_type", "==", agent_type)
                .where("status", "==", "active")
                .order_by("last_message_at", direction=firestore.Query.DESCENDING)
                .limit(1)
            )
            docs = list(query.stream())
            if docs:
                data = docs[0].to_dict()
                data["conversation_id"] = docs[0].id
                # Check expiry
                expires_at = data.get("expires_at")
                if isinstance(expires_at, datetime):
                    if expires_at > datetime.utcnow():
                        return data
                elif isinstance(expires_at, str):
                    if datetime.fromisoformat(expires_at) > datetime.utcnow():
                        return data
            return None
        except Exception as e:
            logger.error(
                "firestore.active_conversation_error",
                chat_id=chat_id,
                agent_type=agent_type,
                error=str(e),
            )
            return None

    async def get_any_active_conversation(
        self,
        chat_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Find any active conversation for a chat, regardless of agent type.

        Finds the most recently active conversation for this chat.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Active conversation data or None
        """
        try:
            query = (
                self.conversations_collection
                .where("chat_id", "==", chat_id)
                .where("status", "==", "active")
                .order_by("last_message_at", direction=firestore.Query.DESCENDING)
                .limit(1)
            )
            docs = list(query.stream())
            if docs:
                data = docs[0].to_dict()
                data["conversation_id"] = docs[0].id
                # Check expiry
                expires_at = data.get("expires_at")
                if isinstance(expires_at, datetime):
                    if expires_at > datetime.utcnow():
                        return data
                elif isinstance(expires_at, str):
                    if datetime.fromisoformat(expires_at) > datetime.utcnow():
                        return data
            return None
        except Exception as e:
            logger.error("firestore.any_active_conversation_error", chat_id=chat_id, error=str(e))
            return None

    async def save_message(
        self,
        message_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Save conversation message.

        Args:
            message_id: Unique message ID
            data: Message data
        """
        try:
            data["created_at"] = datetime.utcnow()
            self.messages_collection.document(message_id).set(data)
            logger.debug("firestore.message_saved", message_id=message_id)
        except Exception as e:
            logger.error("firestore.message_save_error", message_id=message_id, error=str(e))

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation, ordered chronologically.

        Args:
            conversation_id: Conversation ID
            limit: Maximum messages to return

        Returns:
            List of messages
        """
        try:
            query = (
                self.messages_collection
                .where("conversation_id", "==", conversation_id)
                .order_by("created_at")
                .limit(limit)
            )
            messages = []
            for doc in query.stream():
                data = doc.to_dict()
                data["id"] = doc.id
                messages.append(data)
            logger.debug("firestore.messages_loaded", conversation_id=conversation_id, count=len(messages))
            return messages
        except Exception as e:
            logger.error("firestore.messages_load_error", conversation_id=conversation_id, error=str(e))
            return []

    async def update_conversation_status(
        self,
        conversation_id: str,
        status: str,
    ) -> None:
        """Update conversation status.

        Args:
            conversation_id: Conversation ID
            status: New status (active, timeout, completed, user_ended)
        """
        try:
            self.conversations_collection.document(conversation_id).update({
                "status": status,
                "updated_at": datetime.utcnow(),
            })
            logger.info("firestore.conversation_status_updated", conversation_id=conversation_id, status=status)
        except Exception as e:
            logger.error("firestore.conversation_status_error", conversation_id=conversation_id, error=str(e))

    async def mark_message_read(
        self,
        message_id: str,
    ) -> None:
        """Mark message as read.

        Args:
            message_id: Message ID
        """
        try:
            self.messages_collection.document(message_id).update({
                "status": "read",
                "read_at": datetime.utcnow(),
            })
            logger.debug("firestore.message_marked_read", message_id=message_id)
        except Exception as e:
            logger.error("firestore.message_read_error", message_id=message_id, error=str(e))

    async def cleanup_expired_conversations(self) -> int:
        """Cleanup expired active conversations.

        Returns:
            Number of cleaned conversations
        """
        try:
            now = datetime.utcnow()
            query = self.conversations_collection.where("status", "==", "active")
            count = 0
            for doc in query.stream():
                data = doc.to_dict()
                expires_at = data.get("expires_at")
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                if isinstance(expires_at, datetime) and expires_at < now:
                    doc.reference.update({"status": "timeout", "updated_at": now})
                    count += 1
            logger.info("firestore.conversations_cleaned", count=count)
            return count
        except Exception as e:
            logger.error("firestore.conversation_cleanup_error", error=str(e))
            return 0
