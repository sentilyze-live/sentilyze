"""Notification notifiers for different channels."""

import aiohttp

from sentilyze_core import AlertEvent, get_logger
from sentilyze_core.exceptions import ExternalServiceError, RateLimitError

from .config import get_alert_settings

logger = get_logger(__name__)
settings = get_alert_settings()

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


class TelegramNotifier:
    """Telegram bot for sending alerts."""

    def __init__(self, bot_token: str | None = None) -> None:
        self.bot_token = bot_token or settings.telegram_bot_token
        self._session: aiohttp.ClientSession | None = None
        self.enabled: bool = False

    async def initialize(self) -> None:
        """Initialize HTTP session."""
        self._session = aiohttp.ClientSession()

        if not self.bot_token:
            self.enabled = False
            logger.warning("Telegram bot token not configured; Telegram delivery disabled")
            return

        try:
            me = await self._api_call("getMe")
            self.enabled = True
            logger.info("Telegram bot initialized", bot_name=me.get("username"))
        except Exception as e:
            self.enabled = False
            logger.error("Failed to initialize Telegram bot; disabling Telegram delivery", error=str(e))

    async def send_alert(self, alert: AlertEvent, chat_id: str) -> bool:
        """Send alert to Telegram chat."""
        if not self._session:
            raise RuntimeError("Notifier not initialized")

        if not self.bot_token or not self.enabled:
            logger.warning(
                "Telegram delivery disabled; skipping send",
                alert_id=str(alert.alert_id),
                chat_id=chat_id,
            )
            return False

        message = self._format_message(alert)

        await self._api_call(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
            },
        )
        logger.info("Alert sent to Telegram", alert_id=str(alert.alert_id), chat_id=chat_id)
        return True

    def _format_message(self, alert: AlertEvent) -> str:
        """Format alert as Telegram message."""
        emoji_map = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🚨",
            "critical": "🔴",
        }
        emoji = emoji_map.get(alert.severity, "📢")

        message = f"{emoji} *{alert.title}*\n\n"
        message += f"{alert.message}\n\n"
        message += f"Severity: `{alert.severity.upper()}`\n"
        message += f"Type: `{alert.alert_type}`\n"
        message += f"Time: `{alert.triggered_at.isoformat()}`\n"

        if alert.data:
            message += "\n*Details:*\n"
            for key, value in alert.data.items():
                message += f"• {key}: `{value}`\n"

        return message

    async def _api_call(self, method: str, params: dict | None = None) -> dict:
        """Make Telegram API call."""
        if not self._session:
            raise RuntimeError("Session not initialized")

        url = f"{TELEGRAM_API_BASE}{self.bot_token}/{method}"

        async with self._session.post(url, json=params) as response:
            if response.status == 429:
                retry_after = 5
                try:
                    retry_after = int(response.headers.get("Retry-After") or "5")
                except Exception:
                    retry_after = 5
                text = await response.text()
                raise RateLimitError(
                    f"Telegram rate limited (429): {text}",
                    retry_after=retry_after,
                )
            if response.status != 200:
                text = await response.text()
                raise ExternalServiceError(
                    f"Telegram API error: {response.status} - {text}",
                    service="telegram",
                )

            data = await response.json()

            if not data.get("ok"):
                raise ExternalServiceError(
                    f"Telegram API error: {data.get('description')}",
                    service="telegram",
                )

            return data.get("result", {})

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None


class WebhookNotifier:
    """Webhook notifier for alerts."""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self.enabled: bool = False

    async def initialize(self) -> None:
        """Initialize HTTP session."""
        self._session = aiohttp.ClientSession()
        
        if not settings.webhook_url:
            self.enabled = False
            logger.warning("Webhook URL not configured; webhook delivery disabled")
            return
        
        self.enabled = True
        logger.info("Webhook notifier initialized")

    async def send_alert(self, alert: AlertEvent, webhook_url: str | None = None) -> bool:
        """Send alert to webhook."""
        if not self._session:
            raise RuntimeError("Notifier not initialized")

        if not self.enabled:
            logger.warning("Webhook delivery disabled; skipping send")
            return False

        url = webhook_url or settings.webhook_url
        if not url:
            logger.error("No webhook URL provided")
            return False

        headers = {"Content-Type": "application/json"}
        if settings.webhook_secret:
            headers["X-Webhook-Secret"] = settings.webhook_secret

        payload = {
            "alert_id": str(alert.alert_id),
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "data": alert.data,
            "triggered_at": alert.triggered_at.isoformat(),
            "channels": alert.channels,
            "recipients": alert.recipients,
        }

        try:
            async with self._session.post(
                url, json=payload, headers=headers, timeout=settings.webhook_timeout
            ) as response:
                if response.status >= 400:
                    text = await response.text()
                    raise ExternalServiceError(
                        f"Webhook error: {response.status} - {text}",
                        service="webhook",
                    )
                
                logger.info("Alert sent to webhook", alert_id=str(alert.alert_id), url=url)
                return True
        except Exception as e:
            logger.error("Webhook delivery failed", error=str(e), alert_id=str(alert.alert_id))
            raise

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None


class NotifierManager:
    """Manages all notification channels."""

    def __init__(self):
        self.telegram = TelegramNotifier()
        self.webhook = WebhookNotifier()

    async def initialize(self) -> None:
        """Initialize all notifiers."""
        if settings.enable_telegram:
            await self.telegram.initialize()
        if settings.enable_webhook:
            await self.webhook.initialize()

    async def close(self) -> None:
        """Close all notifiers."""
        await self.telegram.close()
        await self.webhook.close()

    async def send_to_channel(
        self,
        alert: AlertEvent,
        channel: str,
        recipient: str | None = None,
    ) -> bool:
        """Send alert to specific channel."""
        if channel == "telegram":
            if not recipient:
                logger.error("Telegram channel requires recipient (chat_id)")
                return False
            return await self.telegram.send_alert(alert, recipient)
        elif channel == "webhook":
            return await self.webhook.send_alert(alert, recipient)
        else:
            logger.warning(f"Unknown notification channel: {channel}")
            return False
