"""Example: How to create a Telegram-enabled agent.

This example shows how to create an agent that:
1. Responds to Telegram mentions
2. Uses context-aware replies
3. Handles both Telegram and non-Telegram triggers
"""

from typing import Any, Dict, Optional
from src.agents.base import BaseAgent


class ExampleTelegramAgent(BaseAgent):
    """Example agent that demonstrates Telegram integration.

    Usage in Telegram:
        @EXAMPLE analyze market trends
        @EXAMPLE what's the latest news?
    """

    def __init__(self):
        super().__init__(
            agent_type="example",
            name="Example Agent",
            description="Demonstrates Telegram integration features",
        )

        self.capabilities = [
            "telegram_replies",
            "context_awareness",
            "user_interaction",
        ]

    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute agent logic.

        This method is called when the agent runs.
        It can be triggered via:
        - Telegram mention (@EXAMPLE task)
        - API call (/agents/example/run)
        - Scheduled run

        Args:
            context: Run context (contains Telegram info if triggered via Telegram)

        Returns:
            Execution result
        """

        # ═══════════════════════════════════════════════════════════════════
        # Step 1: Check if triggered via Telegram
        # ═══════════════════════════════════════════════════════════════════

        if self.is_telegram_triggered():
            # Get Telegram context
            user = self.get_telegram_user()
            task = self.get_telegram_task()

            # Send initial reply
            await self.reply_to_telegram(
                f"👋 Merhaba {user}!\n\n"
                f"'{task}' görevini işlemeye başlıyorum..."
            )

        # ═══════════════════════════════════════════════════════════════════
        # Step 2: Do your actual work
        # ═══════════════════════════════════════════════════════════════════

        # Simulate some work
        result = await self._do_analysis(context)

        # ═══════════════════════════════════════════════════════════════════
        # Step 3: Reply to Telegram (if triggered via Telegram)
        # ═══════════════════════════════════════════════════════════════════

        if self.is_telegram_triggered():
            # Format result for Telegram
            telegram_message = self._format_telegram_result(result)

            # Send reply
            await self.reply_to_telegram(telegram_message)

        # ═══════════════════════════════════════════════════════════════════
        # Step 4: Return result (standard agent behavior)
        # ═══════════════════════════════════════════════════════════════════

        return {
            "success": True,
            "items_analyzed": result["count"],
            "telegram_triggered": self.is_telegram_triggered(),
            "result": result,
        }

    async def _do_analysis(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform the actual analysis work.

        This is where your agent's core logic goes.

        Args:
            context: Execution context

        Returns:
            Analysis result
        """

        # Example: Get task from Telegram or use default
        task = self.get_telegram_task() if self.is_telegram_triggered() else "default analysis"

        # Simulate analysis
        items = [
            {"name": "Item 1", "score": 8.5},
            {"name": "Item 2", "score": 7.2},
            {"name": "Item 3", "score": 9.1},
        ]

        return {
            "task": task,
            "count": len(items),
            "items": items,
            "top_item": items[0],
        }

    def _format_telegram_result(self, result: Dict[str, Any]) -> str:
        """Format result for Telegram message.

        Args:
            result: Analysis result

        Returns:
            Formatted Telegram message (HTML)
        """

        message = f"""✅ <b>Analiz Tamamlandı!</b>

📊 <b>Özet:</b>
• Toplam Item: {result['count']}
• En İyi: {result['top_item']['name']} ({result['top_item']['score']}/10)

<b>Detaylar:</b>
"""

        for item in result["items"]:
            message += f"• {item['name']}: {item['score']}/10\n"

        message += "\n<i>Analiz başarıyla tamamlandı!</i>"

        return message


# ═══════════════════════════════════════════════════════════════════════
# Example 2: Minimal Telegram Agent
# ═══════════════════════════════════════════════════════════════════════


class MinimalTelegramAgent(BaseAgent):
    """Minimal example - just the essentials."""

    def __init__(self):
        super().__init__(
            agent_type="minimal",
            name="Minimal Agent",
            description="Minimal Telegram integration example",
        )

    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        # Do work
        result = {"message": "Work completed"}

        # Reply if Telegram triggered
        if self.is_telegram_triggered():
            await self.reply_to_telegram("✅ Done!")

        return result


# ═══════════════════════════════════════════════════════════════════════
# Example 3: Advanced - Progressive Updates
# ═══════════════════════════════════════════════════════════════════════


class AdvancedTelegramAgent(BaseAgent):
    """Advanced example with progressive updates."""

    def __init__(self):
        super().__init__(
            agent_type="advanced",
            name="Advanced Agent",
            description="Shows progressive Telegram updates",
        )

    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Send multiple updates during processing."""

        # Start notification
        if self.is_telegram_triggered():
            await self.reply_to_telegram("🚀 Starting analysis...")

        # Step 1
        step1_result = await self._step_1()
        if self.is_telegram_triggered():
            await self.reply_to_telegram(
                f"✅ Step 1/3 complete\n\nFound {step1_result['count']} items"
            )

        # Step 2
        step2_result = await self._step_2(step1_result)
        if self.is_telegram_triggered():
            await self.reply_to_telegram(
                f"✅ Step 2/3 complete\n\nProcessed {step2_result['processed']} items"
            )

        # Step 3
        final_result = await self._step_3(step2_result)
        if self.is_telegram_triggered():
            await self.reply_to_telegram(
                f"🎉 <b>Analysis Complete!</b>\n\n"
                f"Final Score: {final_result['score']}/10\n"
                f"Recommendations: {len(final_result['recommendations'])}"
            )

        return final_result

    async def _step_1(self):
        return {"count": 10}

    async def _step_2(self, data):
        return {"processed": data["count"]}

    async def _step_3(self, data):
        return {
            "score": 8.5,
            "recommendations": ["Action 1", "Action 2"],
            "processed_count": data["processed"],
        }


# ═══════════════════════════════════════════════════════════════════════
# Example 4: Conditional Reply
# ═══════════════════════════════════════════════════════════════════════


class ConditionalReplyAgent(BaseAgent):
    """Only reply to Telegram if there are significant findings."""

    def __init__(self):
        super().__init__(
            agent_type="conditional",
            name="Conditional Reply Agent",
            description="Only replies if findings are significant",
        )

    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        # Perform analysis
        opportunities = await self._find_opportunities()

        # Only reply if significant findings AND triggered via Telegram
        if self.is_telegram_triggered() and len(opportunities) > 0:
            # Format message
            message = "🔍 <b>Opportunities Found!</b>\n\n"

            for opp in opportunities[:5]:  # Top 5
                message += f"• {opp['name']}: {opp['score']}/10\n"

            if len(opportunities) > 5:
                message += f"\n... and {len(opportunities) - 5} more"

            await self.reply_to_telegram(message)

        elif self.is_telegram_triggered():
            # No findings
            await self.reply_to_telegram(
                "ℹ️ No significant opportunities found at the moment."
            )

        return {"opportunities": opportunities}

    async def _find_opportunities(self):
        # Simulate finding opportunities
        return [
            {"name": "Opportunity 1", "score": 8.5},
            {"name": "Opportunity 2", "score": 7.8},
        ]


# ═══════════════════════════════════════════════════════════════════════
# Usage Examples
# ═══════════════════════════════════════════════════════════════════════

"""
USAGE IN TELEGRAM:

1. Single agent mention:
   @EXAMPLE analyze market trends
   @MINIMAL test
   @ADVANCED full analysis

2. Broadcast to all agents:
   @all what's happening today?
   @herkes bugün ne var?

3. With specific tasks:
   @EXAMPLE check gold prices
   @ADVANCED deep dive into crypto


API USAGE:

# Trigger via API
import httpx

async def trigger_agent():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/agents/example/run",
            json={
                "context": {
                    # Optional: Simulate Telegram trigger
                    "telegram_enabled": True,
                    "telegram_chat_id": "123456789",
                    "telegram_user_id": "987654321",
                    "telegram_username": "johndoe",
                    "telegram_message": "test",
                    "telegram_message_id": 1,
                    "telegram_trigger_type": "mention",
                    "task": "analyze trends",
                }
            }
        )
        print(response.json())


TESTING:

# Test via curl
curl -X POST http://localhost:8080/agents/example/run

# Test Telegram webhook
curl -X POST http://localhost:8080/telegram/test

# Check agent info
curl http://localhost:8080/agents/example
"""


# ═══════════════════════════════════════════════════════════════════════
# Key Takeaways
# ═══════════════════════════════════════════════════════════════════════

"""
✅ DO:
- Use `is_telegram_triggered()` to check if Telegram triggered
- Use `reply_to_telegram()` for replies
- Use `get_telegram_user()` and `get_telegram_task()` for context
- Reply conditionally (only when needed)
- Format messages with HTML for better readability

❌ DON'T:
- Don't call `reply_to_telegram()` without checking `is_telegram_triggered()`
- Don't spam multiple replies (rate limiting will block)
- Don't expose sensitive data in Telegram messages
- Don't rely on Telegram for critical system operations

🎯 BEST PRACTICES:
1. Always check `is_telegram_triggered()` before replying
2. Keep messages concise and formatted
3. Use progressive updates for long operations
4. Reply with meaningful information (not just "done")
5. Handle errors gracefully
"""
