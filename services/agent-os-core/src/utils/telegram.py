"""Telegram notification and approval system."""

import json
from typing import Any, Dict, List, Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings

logger = structlog.get_logger(__name__)


class TelegramNotifier:
    """Telegram bot for notifications and manual approvals."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        """Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token (defaults to settings)
            chat_id: Telegram chat ID (defaults to settings)
        """
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self.enabled = settings.ENABLE_TELEGRAM_NOTIFICATIONS

        if not self.bot_token or not self.chat_id:
            logger.warning("telegram.notifier_disabled", reason="missing_credentials")
            self.enabled = False

        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def send_message(
        self,
        message: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send message to Telegram.

        Args:
            message: Message text
            parse_mode: Parse mode (HTML, Markdown, etc.)
            reply_markup: Optional inline keyboard

        Returns:
            API response
        """
        if not self.enabled:
            logger.debug("telegram.message_skipped", reason="disabled")
            return {"ok": False, "description": "Telegram notifications disabled"}

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
        }

        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)

        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.debug("telegram.send_message", message_length=len(message))

            response = await client.post(
                f"{self.base_url}/sendMessage",
                json=payload,
            )

            response.raise_for_status()
            data = response.json()

            if data.get("ok"):
                logger.info("telegram.message_sent", message_id=data["result"]["message_id"])
            else:
                logger.error("telegram.message_failed", error=data.get("description"))

            return data

    async def send_for_approval(
        self,
        content_type: str,
        content: str,
        agent_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send content for manual approval.

        Args:
            content_type: Type of content (blog, reel, post, experiment)
            content: Content to approve
            agent_name: Name of the agent
            metadata: Additional metadata

        Returns:
            API response
        """
        # Truncate content if too long
        display_content = content[:800] + "..." if len(content) > 800 else content

        message = f"""🔔 <b>New Content for Approval</b>

<b>Agent:</b> {agent_name}
<b>Type:</b> {content_type.upper()}

<b>Content:</b>
{display_content}

<i>Please approve or reject this content.</i>"""

        # Create approval buttons
        content_id = metadata.get("content_id", "unknown") if metadata else "unknown"

        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Approve",
                        "callback_data": f"approve:{content_type}:{content_id}",
                    },
                    {
                        "text": "❌ Reject",
                        "callback_data": f"reject:{content_type}:{content_id}",
                    },
                ],
                [
                    {
                        "text": "📝 Edit",
                        "callback_data": f"edit:{content_type}:{content_id}",
                    },
                ],
            ],
        }

        return await self.send_message(message, reply_markup=reply_markup)

    async def notify_published(
        self,
        content_type: str,
        url: Optional[str] = None,
        agent_name: str = "",
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Notify when content is published.

        Args:
            content_type: Type of content
            url: Published URL
            agent_name: Name of the agent
            metrics: Performance metrics

        Returns:
            API response
        """
        message = f"""✅ <b>Content Published</b>

<b>Agent:</b> {agent_name}
<b>Type:</b> {content_type.upper()}
"""

        if url:
            message += f"\n<b>URL:</b> {url}"

        if metrics:
            message += "\n\n<b>Metrics:</b>"
            for key, value in metrics.items():
                message += f"\n• {key}: {value}"

        return await self.send_message(message)

    async def notify_agent_run(
        self,
        agent_name: str,
        status: str,
        duration_seconds: float,
        output_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Notify when agent run completes.

        Args:
            agent_name: Name of the agent
            status: Run status (success, error)
            duration_seconds: Run duration
            output_summary: Summary of output

        Returns:
            API response
        """
        status_emoji = "✅" if status == "success" else "❌"

        message = f"""{status_emoji} <b>Agent Run: {agent_name}</b>

<b>Status:</b> {status.upper()}
<b>Duration:</b> {duration_seconds:.2f}s
"""

        if output_summary:
            message += f"\n<b>Output:</b>\n{output_summary[:500]}"

        return await self.send_message(message)

    async def notify_trend_detected(
        self,
        trend_data: Dict[str, Any],
        agent_name: str = "SCOUT",
    ) -> Dict[str, Any]:
        """Notify when a new trend is detected.

        Args:
            trend_data: Trend analysis data
            agent_name: Name of the agent

        Returns:
            API response
        """
        viral_score = trend_data.get("viral_score", 0)
        migration = trend_data.get("migration_probability", "Unknown")
        hook = trend_data.get("suggested_hook", "")

        # Emoji based on viral score
        if viral_score >= 8:
            emoji = "🔥"
        elif viral_score >= 6:
            emoji = "⚡"
        else:
            emoji = "📊"

        message = f"""{emoji} <b>New Trend Detected</b>

<b>Agent:</b> {agent_name}
<b>Viral Score:</b> {viral_score}/10
<b>Migration:</b> {migration}

<b>Hook:</b>
<i>{hook}</i>

<b>Keywords:</b> {', '.join(trend_data.get('keywords', []))}
"""

        return await self.send_message(message)

    async def notify_experiment_proposed(
        self,
        experiment: Dict[str, Any],
        agent_name: str = "ELON",
    ) -> Dict[str, Any]:
        """Notify when a growth experiment is proposed.

        Args:
            experiment: Experiment data
            agent_name: Name of the agent

        Returns:
            API response
        """
        ice = experiment.get("ice_scores", {})
        total = ice.get("total", 0)

        message = f"""🧪 <b>Growth Experiment Proposed</b>

<b>Agent:</b> {agent_name}
<b>Name:</b> {experiment.get('experiment_name', 'Unnamed')}

<b>Hypothesis:</b>
<i>{experiment.get('hypothesis', '')}</i>

<b>ICE Score:</b> {total}/30
• Impact: {ice.get('impact', 0)}/10
• Confidence: {ice.get('confidence', 0)}/10
• Ease: {ice.get('ease', 0)}/10

<b>Target:</b> {experiment.get('target_metric', 'Unknown')}
<b>Expected Lift:</b> {experiment.get('expected_lift', 'Unknown')}
"""

        return await self.send_message(message)

    async def send_daily_summary(
        self,
        agent_activities: List[Dict[str, Any]],
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send daily summary of agent activities.

        Args:
            agent_activities: List of agent activity summaries
            metrics: Daily metrics

        Returns:
            API response
        """
        message = """📊 <b>Daily Agent OS Summary</b>

<b>Agent Activities:</b>
"""

        for activity in agent_activities:
            agent = activity.get("agent", "Unknown")
            status = activity.get("status", "unknown")
            count = activity.get("items_generated", 0)

            emoji = "✅" if status == "success" else "❌"
            message += f"\n{emoji} <b>{agent}:</b> {count} items generated"

        message += "\n\n<b>Daily Metrics:</b>"
        for key, value in metrics.items():
            message += f"\n• {key}: {value}"

        return await self.send_message(message)

    async def send_error_alert(
        self,
        agent_name: str,
        error: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send error alert.

        Args:
            agent_name: Name of the agent that failed
            error: Error message
            context: Additional context

        Returns:
            API response
        """
        message = f"""🚨 <b>Agent Error Alert</b>

<b>Agent:</b> {agent_name}
<b>Error:</b>
<code>{error[:500]}</code>
"""

        if context:
            message += "\n\n<b>Context:</b>"
            for key, value in context.items():
                message += f"\n• {key}: {value}"

        return await self.send_message(message)
