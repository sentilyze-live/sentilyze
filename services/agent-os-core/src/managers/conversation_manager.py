"""Conversation Manager for 10-minute agent conversations.

Manages active conversation sessions with:
- 10-minute timeout with automatic extension on user activity
- Message persistence and read receipts
- Separate threads per agent
- Conversation status tracking
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from src.data_bridge import FirestoreDataClient

logger = structlog.get_logger(__name__)


class ConversationManager:
    """Manages agent conversations with 10-minute timeout."""

    SESSION_TIMEOUT_MINUTES = 10
    SESSION_TIMEOUT_SECONDS = SESSION_TIMEOUT_MINUTES * 60

    _instance: Optional["ConversationManager"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.firestore = FirestoreDataClient()
        self._initialized = True

        logger.info(
            "conversation_manager.initialized",
            timeout_minutes=self.SESSION_TIMEOUT_MINUTES,
        )

    def _generate_conversation_id(self, chat_id: str, agent_type: str) -> str:
        """Generate unique conversation ID.

        Args:
            chat_id: Telegram chat ID
            agent_type: Agent type

        Returns:
            Unique conversation ID
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"conv_{agent_type}_{chat_id}_{timestamp}"

    def _generate_message_id(self) -> str:
        """Generate unique message ID.

        Returns:
            Unique message ID
        """
        return f"msg_{uuid.uuid4().hex[:16]}"

    def _get_expires_at(self) -> datetime:
        """Get expiration timestamp for new session.

        Returns:
            Expiration datetime
        """
        return datetime.utcnow() + timedelta(minutes=self.SESSION_TIMEOUT_MINUTES)

    async def start_conversation(
        self,
        chat_id: str,
        agent_type: str,
        initial_task: str,
        username: str = "User",
    ) -> Dict[str, Any]:
        """Start a new conversation with an agent.

        Args:
            chat_id: Telegram chat ID
            agent_type: Agent type (scout, oracle, etc.)
            initial_task: Initial task description
            username: Telegram username

        Returns:
            Conversation data including conversation_id
        """
        conversation_id = self._generate_conversation_id(chat_id, agent_type)
        expires_at = self._get_expires_at()

        conversation_data = {
            "chat_id": chat_id,
            "agent_type": agent_type,
            "username": username,
            "status": "active",
            "started_at": datetime.utcnow(),
            "expires_at": expires_at,
            "last_message_at": datetime.utcnow(),
            "message_count": 0,
            "initial_task": initial_task,
        }

        await self.firestore.save_conversation(conversation_id, conversation_data)

        # Add initial user message
        await self.add_message(
            conversation_id=conversation_id,
            chat_id=chat_id,
            agent_type=agent_type,
            role="user",
            content=initial_task,
        )

        logger.info(
            "conversation.started",
            conversation_id=conversation_id,
            agent_type=agent_type,
            chat_id=chat_id,
            expires_at=expires_at.isoformat(),
        )

        return {
            "conversation_id": conversation_id,
            "expires_at": expires_at.isoformat(),
            "status": "active",
        }

    async def add_message(
        self,
        conversation_id: str,
        chat_id: str,
        agent_type: str,
        role: str,
        content: str,
    ) -> str:
        """Add a message to conversation.

        Args:
            conversation_id: Conversation ID
            chat_id: Telegram chat ID
            agent_type: Agent type
            role: Message role (user/agent)
            content: Message content

        Returns:
            Message ID
        """
        message_id = self._generate_message_id()

        message_data = {
            "conversation_id": conversation_id,
            "chat_id": chat_id,
            "agent_type": agent_type,
            "role": role,
            "content": content,
            "status": "pending",
        }

        await self.firestore.save_message(message_id, message_data)

        # Update conversation message count
        conversation = await self.firestore.get_conversation(conversation_id)
        if conversation:
            await self.firestore.save_conversation(
                conversation_id,
                {"message_count": conversation.get("message_count", 0) + 1},
            )

        logger.debug(
            "conversation.message_added",
            conversation_id=conversation_id,
            message_id=message_id,
            role=role,
        )

        return message_id

    async def mark_message_read(self, message_id: str) -> None:
        """Mark message as read.

        Args:
            message_id: Message ID
        """
        await self.firestore.mark_message_read(message_id)

        logger.debug("conversation.message_marked_read", message_id=message_id)

    async def extend_session(
        self,
        conversation_id: str,
        chat_id: str,
        agent_type: str,
    ) -> bool:
        """Extend conversation session (called when user sends message).

        Args:
            conversation_id: Conversation ID
            chat_id: Telegram chat ID
            agent_type: Agent type

        Returns:
            True if extended, False if not found/expired
        """
        conversation = await self.firestore.get_conversation(conversation_id)

        if not conversation:
            logger.warning(
                "conversation.extend_failed_not_found",
                conversation_id=conversation_id,
            )
            return False

        if conversation.get("status") != "active":
            logger.warning(
                "conversation.extend_failed_not_active",
                conversation_id=conversation_id,
                status=conversation.get("status"),
            )
            return False

        # Check if already expired
        expires_at = conversation.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)

        if expires_at < datetime.utcnow():
            logger.info(
                "conversation.already_expired",
                conversation_id=conversation_id,
            )
            await self.firestore.update_conversation_status(
                conversation_id, "timeout"
            )
            return False

        # Extend session
        new_expires_at = self._get_expires_at()

        await self.firestore.save_conversation(
            conversation_id,
            {
                "status": "active",
                "expires_at": new_expires_at,
                "last_message_at": datetime.utcnow(),
            },
        )

        logger.info(
            "conversation.session_extended",
            conversation_id=conversation_id,
            new_expires_at=new_expires_at.isoformat(),
        )

        return True

    async def get_or_create_conversation(
        self,
        chat_id: str,
        agent_type: str,
        new_task: str,
        username: str = "User",
    ) -> Dict[str, Any]:
        """Get active conversation or create new one.

        Args:
            chat_id: Telegram chat ID
            agent_type: Agent type
            new_task: Task if creating new conversation
            username: Telegram username

        Returns:
            Conversation data
        """
        # Try to find existing active conversation
        existing = await self.firestore.get_active_conversation(
            chat_id=chat_id,
            agent_type=agent_type,
        )

        if existing:
            logger.info(
                "conversation.found_existing",
                conversation_id=existing.get("conversation_id"),
                agent_type=agent_type,
            )
            return existing

        # Create new conversation
        logger.info(
            "conversation.creating_new",
            chat_id=chat_id,
            agent_type=agent_type,
        )

        return await self.start_conversation(
            chat_id=chat_id,
            agent_type=agent_type,
            initial_task=new_task,
            username=username,
        )

    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum messages to return

        Returns:
            List of messages
        """
        return await self.firestore.get_messages(conversation_id, limit)

    async def end_conversation(
        self,
        conversation_id: str,
        reason: str = "completed",
    ) -> None:
        """End a conversation.

        Args:
            conversation_id: Conversation ID
            reason: End reason (completed, timeout, user_ended)
        """
        await self.firestore.update_conversation_status(conversation_id, reason)

        logger.info(
            "conversation.ended",
            conversation_id=conversation_id,
            reason=reason,
        )

    async def is_conversation_active(self, conversation_id: str) -> bool:
        """Check if conversation is still active.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if active and not expired
        """
        conversation = await self.firestore.get_conversation(conversation_id)

        if not conversation:
            return False

        if conversation.get("status") != "active":
            return False

        expires_at = conversation.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)

        return expires_at > datetime.utcnow()

    async def cleanup_expired(self) -> int:
        """Clean up expired conversations.

        Returns:
            Number of cleaned conversations
        """
        return await self.firestore.cleanup_expired_conversations()

    def build_conversation_context(
        self,
        conversation_id: str,
        new_message: str,
    ) -> Dict[str, Any]:
        """Build context for agent with conversation history.

        Args:
            conversation_id: Conversation ID
            new_message: New user message

        Returns:
            Context dict for agent
        """
        return {
            "conversation_id": conversation_id,
            "user_message": new_message,
            "has_history": True,
        }


conversation_manager = ConversationManager()


def get_conversation_manager() -> ConversationManager:
    """Get or create ConversationManager singleton.

    Returns:
        ConversationManager instance
    """
    return conversation_manager
