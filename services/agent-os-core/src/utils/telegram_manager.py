"""Unified Telegram Manager for Agent OS.

Clean, simple, and secure Telegram integration.
All Telegram operations go through this single manager.

Architecture:
- Single entry point for all Telegram operations
- Agent-agnostic design (works with any agent)
- Built-in security (rate limiting, sanitization)
- Simple API for agents to send messages
"""

import hashlib
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class TelegramContext:
    """Context for Telegram-triggered agent runs.

    When an agent is triggered via Telegram, this context is passed
    to the agent's run() method.
    """
    chat_id: str
    user_id: str
    username: str
    message_text: str
    message_id: int
    trigger_type: str  # "mention", "command", "broadcast"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for agent context."""
        return {
            "telegram_chat_id": self.chat_id,
            "telegram_user_id": self.user_id,
            "telegram_username": self.username,
            "telegram_message": self.message_text,
            "telegram_message_id": self.message_id,
            "telegram_trigger_type": self.trigger_type,
            "telegram_enabled": True,
        }


class TelegramManager:
    """Unified Telegram Manager for Agent OS.

    Singleton pattern ensures single point of control for all
    Telegram operations across the application.

    Features:
    - Webhook message handling
    - Agent message sending
    - Rate limiting (per user)
    - Message sanitization
    - Security logging
    """

    _instance: Optional["TelegramManager"] = None
    _initialized: bool = False

    # Agent mention patterns (@SCOUT, @ORACLE, etc.)
    AGENT_PATTERNS = {
        "scout": r"@SCOUT\b",
        "oracle": r"@ORACLE\b",
        "seth": r"@SETH\b",
        "zara": r"@ZARA\b",
        "elon": r"@ELON\b",
        "maria": r"@MARIA\b",
        "coder": r"@CODER\b",
        "sentinel": r"@SENTINEL\b",
        "atlas": r"@ATLAS\b",
    }

    # Broadcast patterns (@all, @herkes)
    BROADCAST_PATTERNS = [r"@all\b", r"@herkes\b"]

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Telegram Manager (once)."""
        if self._initialized:
            return

        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.default_chat_id = settings.TELEGRAM_CHAT_ID
        self.enabled = bool(self.bot_token and self.default_chat_id)

        if not self.enabled:
            logger.warning("telegram_manager.disabled", reason="missing_credentials")
            self._initialized = True
            return

        # HTTP client for Telegram API
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

        # Security: Rate limiting
        self._rate_limit_store: Dict[str, List[datetime]] = {}
        self._blocked_users: Set[str] = set()
        self._max_commands_per_minute = settings.TELEGRAM_RATE_LIMIT_PER_MINUTE
        self._max_commands_per_hour = settings.TELEGRAM_RATE_LIMIT_PER_HOUR

        # Compile regex patterns
        self._agent_regex = {
            agent: re.compile(pattern, re.IGNORECASE)
            for agent, pattern in self.AGENT_PATTERNS.items()
        }
        self._broadcast_regex = re.compile(
            "|".join(self.BROADCAST_PATTERNS),
            re.IGNORECASE
        )

        self._initialized = True
        logger.info("telegram_manager.initialized", enabled=self.enabled)

    async def close(self):
        """Close HTTP client."""
        if hasattr(self, 'client'):
            await self.client.aclose()
            logger.info("telegram_manager.closed")

    # ═══════════════════════════════════════════════════════════════════
    # PUBLIC API: Message Handling (Webhook)
    # ═══════════════════════════════════════════════════════════════════

    async def handle_webhook_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook update from Telegram.

        Main entry point for processing Telegram messages.

        Args:
            update: Telegram update object

        Returns:
            Processing result
        """
        if not self.enabled:
            return {"ok": False, "error": "Telegram not enabled"}

        try:
            # Extract message
            message = update.get("message", {})
            if not message:
                return {"ok": True, "skipped": "no_message"}

            # Extract details
            text = message.get("text", "")
            chat_id = str(message.get("chat", {}).get("id", ""))
            message_id = message.get("message_id", 0)
            user = message.get("from", {})
            user_id = str(user.get("id", ""))
            username = user.get("username", "Unknown")
            first_name = user.get("first_name", "User")

            logger.info(
                "telegram.message_received",
                user=username,
                chat_id=chat_id,
                text=text[:100],
            )

            # Security: Check rate limits
            if not self._check_rate_limit(user_id):
                await self._send_message(
                    chat_id,
                    "⚠️ Rate limit exceeded. Please wait before sending more commands."
                )
                return {"ok": False, "error": "rate_limit_exceeded"}

            # Detect agent mentions or broadcast
            detected = self._detect_agent_or_broadcast(text)

            if not detected:
                # No agent mentioned, ignore
                return {"ok": True, "skipped": "no_agent_mentioned"}

            agent_names = detected["agents"]
            trigger_type = detected["type"]  # "mention" or "broadcast"

            # Extract task (remove agent mentions from text)
            task = self._extract_task(text, agent_names)

            # Create Telegram context
            telegram_context = TelegramContext(
                chat_id=chat_id,
                user_id=user_id,
                username=username or first_name,
                message_text=text,
                message_id=message_id,
                trigger_type=trigger_type,
            )

            # Return agent activation request
            # (The caller - webhook endpoint - will trigger agents)
            return {
                "ok": True,
                "action": "activate_agents",
                "agents": agent_names,
                "task": task,
                "telegram_context": telegram_context,
            }

        except Exception as e:
            logger.error("telegram.webhook_error", error=str(e))
            return {"ok": False, "error": str(e)}

    # ═══════════════════════════════════════════════════════════════════
    # PUBLIC API: Agent Communication
    # ═══════════════════════════════════════════════════════════════════

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
    ) -> Dict[str, Any]:
        """Send message to Telegram.

        Main method for agents to send messages.

        Args:
            text: Message text
            chat_id: Target chat ID (defaults to configured chat)
            parse_mode: Parse mode (HTML or Markdown)

        Returns:
            API response
        """
        if not self.enabled:
            logger.debug("telegram.send_skipped", reason="disabled")
            return {"ok": False, "error": "disabled"}

        target_chat_id = chat_id or self.default_chat_id

        # Sanitize message
        sanitized_text = self._sanitize_message(text)

        return await self._send_message(target_chat_id, sanitized_text, parse_mode)

    async def notify_agent_activated(
        self,
        agent_name: str,
        task: str,
        user_name: str,
        chat_id: str,
    ) -> Dict[str, Any]:
        """Notify user that agent was activated.

        Args:
            agent_name: Name of activated agent
            task: Task description
            user_name: User who triggered
            chat_id: Chat to send to

        Returns:
            Send result
        """
        message = f"""✅ <b>{agent_name.upper()} Activated!</b>

👤 Triggered by: {user_name}
📝 Task: {task}

<i>Agent is processing your request...</i>"""

        return await self.send_message(message, chat_id=chat_id)

    async def notify_broadcast_result(
        self,
        activated_agents: List[str],
        failed_agents: List[str],
        task: str,
        user_name: str,
        chat_id: str,
    ) -> Dict[str, Any]:
        """Notify broadcast result.

        Args:
            activated_agents: Successfully activated agents
            failed_agents: Failed agents
            task: Task description
            user_name: User who triggered
            chat_id: Chat to send to

        Returns:
            Send result
        """
        message_parts = [
            "🔔 <b>Broadcast to All Agents!</b>",
            "",
            f"👤 Triggered by: {user_name}",
            f"📝 Task: {task}",
            "",
            "<b>Activated:</b>",
        ]

        for agent in activated_agents:
            message_parts.append(f"✅ {agent}")

        if failed_agents:
            message_parts.extend(["", "<b>Failed:</b>"])
            for agent in failed_agents:
                message_parts.append(f"❌ {agent}")

        message = "\n".join(message_parts)
        return await self.send_message(message, chat_id=chat_id)

    # ═══════════════════════════════════════════════════════════════════
    # WEBHOOK MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════

    async def set_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """Set Telegram webhook URL.

        Args:
            webhook_url: Full HTTPS URL for webhook

        Returns:
            API response
        """
        if not self.enabled:
            return {"ok": False, "error": "disabled"}

        try:
            response = await self.client.post(
                f"{self.base_url}/setWebhook",
                json={"url": webhook_url},
            )
            data = response.json()

            if data.get("ok"):
                logger.info("telegram.webhook_set", url=webhook_url)
            else:
                logger.error("telegram.webhook_error", error=data.get("description"))

            return data

        except Exception as e:
            logger.error("telegram.set_webhook_error", error=str(e))
            return {"ok": False, "error": str(e)}

    async def get_webhook_info(self) -> Dict[str, Any]:
        """Get webhook info.

        Returns:
            Webhook info from Telegram API
        """
        if not self.enabled:
            return {"ok": False, "error": "disabled"}

        try:
            response = await self.client.get(f"{self.base_url}/getWebhookInfo")
            return response.json()
        except Exception as e:
            logger.error("telegram.webhook_info_error", error=str(e))
            return {"ok": False, "error": str(e)}

    # ═══════════════════════════════════════════════════════════════════
    # PRIVATE METHODS: Security & Helpers
    # ═══════════════════════════════════════════════════════════════════

    def _check_rate_limit(self, user_id: str) -> bool:
        """Check rate limit for user.

        Args:
            user_id: User identifier

        Returns:
            True if within limits, False if exceeded
        """
        now = datetime.utcnow()

        # Check if blocked
        if user_id in self._blocked_users:
            logger.warning("telegram.blocked_user", user_id_hash=self._hash_id(user_id))
            return False

        # Get user's command history
        user_commands = self._rate_limit_store.get(user_id, [])

        # Clean old entries (>1 hour)
        user_commands = [t for t in user_commands if now - t < timedelta(hours=1)]
        self._rate_limit_store[user_id] = user_commands

        # Check per-minute limit
        recent = [t for t in user_commands if now - t < timedelta(minutes=1)]
        if len(recent) >= self._max_commands_per_minute:
            logger.warning("telegram.rate_limit_minute", user_id_hash=self._hash_id(user_id))
            return False

        # Check per-hour limit
        if len(user_commands) >= self._max_commands_per_hour:
            logger.warning("telegram.rate_limit_hour", user_id_hash=self._hash_id(user_id))
            self._blocked_users.add(user_id)
            return False

        # Record this command
        user_commands.append(now)
        return True

    def _sanitize_message(self, text: str, max_length: int = 4000) -> str:
        """Sanitize message text.

        Args:
            text: Raw text
            max_length: Maximum length

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Limit length (Telegram max is 4096)
        if len(text) > max_length:
            text = text[:max_length - 3] + "..."

        # Remove potential script injection
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)

        # Remove excessive newlines
        text = re.sub(r"\n{4,}", "\n\n\n", text)

        return text.strip()

    def _detect_agent_or_broadcast(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect agent mentions or broadcast in text.

        Args:
            text: Message text

        Returns:
            Detection result or None
        """
        if not text:
            return None

        # Check for broadcast
        if self._broadcast_regex.search(text):
            return {
                "type": "broadcast",
                "agents": list(self.AGENT_PATTERNS.keys()),  # All agents
            }

        # Check for individual agents
        detected_agents = []
        for agent_name, regex in self._agent_regex.items():
            if regex.search(text):
                detected_agents.append(agent_name)

        if detected_agents:
            return {
                "type": "mention",
                "agents": detected_agents,
            }

        return None

    def _extract_task(self, text: str, agent_names: List[str]) -> str:
        """Extract task from message text.

        Removes agent mentions and broadcast keywords.

        Args:
            text: Original message
            agent_names: Detected agent names

        Returns:
            Clean task text
        """
        # Remove broadcast patterns
        task = self._broadcast_regex.sub("", text)

        # Remove agent mentions
        for agent_name in agent_names:
            if agent_name in self._agent_regex:
                regex = self._agent_regex[agent_name]
                task = regex.sub("", task)

        # Clean whitespace
        task = " ".join(task.split())

        return task if task else "No specific task provided"

    def _hash_id(self, user_id: str) -> str:
        """Hash user ID for logging (privacy).

        Args:
            user_id: User ID

        Returns:
            Hashed ID
        """
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]

    async def _send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
    ) -> Dict[str, Any]:
        """Internal method to send message to Telegram API.

        Args:
            chat_id: Chat ID
            text: Message text
            parse_mode: Parse mode

        Returns:
            API response
        """
        try:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }

            response = await self.client.post(
                f"{self.base_url}/sendMessage",
                json=payload,
            )

            response.raise_for_status()
            data = response.json()

            if data.get("ok"):
                logger.info("telegram.message_sent", chat_id_hash=self._hash_id(chat_id))
            else:
                logger.error("telegram.send_failed", error=data.get("description"))

            return data

        except Exception as e:
            logger.error("telegram.send_error", error=str(e))
            return {"ok": False, "error": str(e)}


# Global singleton instance
_telegram_manager: Optional[TelegramManager] = None


def get_telegram_manager() -> TelegramManager:
    """Get or create TelegramManager singleton.

    Returns:
        TelegramManager instance
    """
    global _telegram_manager
    if _telegram_manager is None:
        _telegram_manager = TelegramManager()
    return _telegram_manager
