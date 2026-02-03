"""Telegram routes - Simplified and unified.

Clean webhook endpoint using the new TelegramManager.
"""

from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import structlog

from src.agents import get_agent
from src.utils.telegram_manager import get_telegram_manager

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = structlog.get_logger(__name__)


@router.post("/webhook")
async def telegram_webhook(request: Request) -> Dict[str, Any]:
    """Handle incoming Telegram webhook updates.

    This is the main entry point for Telegram messages.
    Users can:
    - Mention specific agents: @SCOUT, @ORACLE, @SETH, @ZARA, @ELON, @MARIA
    - Broadcast to all: @all or @herkes

    The webhook:
    1. Receives the message
    2. Detects agent mentions
    3. Activates the relevant agents
    4. Sends confirmation to user

    Returns:
        Always returns 200 OK to Telegram (to avoid retries)
    """
    try:
        # Parse update
        update = await request.json()

        # Get manager
        telegram = get_telegram_manager()

        # Process update
        result = await telegram.handle_webhook_update(update)

        # Check if we need to activate agents
        if result.get("action") == "activate_agents":
            agents = result["agents"]
            task = result["task"]
            telegram_context = result["telegram_context"]

            # Activate each agent
            activated = []
            failed = []

            for agent_name in agents:
                try:
                    # Get agent instance
                    agent = get_agent(agent_name)

                    # Create context for agent
                    context = {
                        "task": task,
                        **telegram_context.to_dict(),
                    }

                    # Run agent asynchronously (don't wait)
                    import asyncio
                    asyncio.create_task(agent.run(context))

                    activated.append(agent_name.upper())
                    logger.info("telegram.agent_activated", agent=agent_name)

                except ValueError:
                    failed.append(f"{agent_name.upper()} (not found)")
                    logger.error("telegram.agent_not_found", agent=agent_name)
                except Exception as e:
                    failed.append(f"{agent_name.upper()} (error: {str(e)[:30]})")
                    logger.error("telegram.agent_activation_error", agent=agent_name, error=str(e))

            # Send confirmation to user
            if len(agents) > 1:
                # Broadcast
                await telegram.notify_broadcast_result(
                    activated_agents=activated,
                    failed_agents=failed,
                    task=task,
                    user_name=telegram_context.username,
                    chat_id=telegram_context.chat_id,
                )
            else:
                # Single agent
                if activated:
                    await telegram.notify_agent_activated(
                        agent_name=activated[0],
                        task=task,
                        user_name=telegram_context.username,
                        chat_id=telegram_context.chat_id,
                    )

        # Always return 200 OK to Telegram
        return {"ok": True, "result": result}

    except Exception as e:
        logger.error("telegram.webhook_error", error=str(e))
        # Still return 200 to avoid Telegram retries
        return JSONResponse(
            status_code=200,
            content={"ok": False, "error": str(e)},
        )


@router.get("/webhook")
async def verify_webhook() -> Dict[str, str]:
    """Verify webhook is active.

    Returns:
        Status message
    """
    return {
        "status": "active",
        "message": "Telegram webhook endpoint is ready",
        "version": "2.0",
    }


@router.get("/webhook/info")
async def get_webhook_info() -> Dict[str, Any]:
    """Get current webhook information from Telegram.

    Returns:
        Webhook info
    """
    telegram = get_telegram_manager()
    return await telegram.get_webhook_info()


@router.post("/webhook/set")
async def set_webhook(webhook_url: str) -> Dict[str, Any]:
    """Set Telegram webhook URL.

    Args:
        webhook_url: Full HTTPS URL for webhook

    Returns:
        Set result
    """
    telegram = get_telegram_manager()
    return await telegram.set_webhook(webhook_url)


@router.post("/send")
async def send_message(
    text: str,
    chat_id: str = None,
) -> Dict[str, Any]:
    """Send a message to Telegram.

    Useful for testing or manual notifications.

    Args:
        text: Message text
        chat_id: Optional chat ID (defaults to configured chat)

    Returns:
        Send result
    """
    telegram = get_telegram_manager()
    return await telegram.send_message(text, chat_id=chat_id)


@router.post("/test")
async def test_telegram() -> Dict[str, Any]:
    """Test Telegram connection.

    Sends a test message to verify bot is working.

    Returns:
        Test result
    """
    telegram = get_telegram_manager()

    test_message = """🧪 <b>Telegram Test</b>

✅ Bot connection successful!
✅ Webhook endpoint active
✅ Ready to receive agent mentions

Try mentioning an agent:
• @SCOUT - Market intelligence
• @ORACLE - Statistical validation
• @SETH - SEO content
• @ZARA - Community engagement
• @ELON - Growth experiments
• @MARIA - DevOps guardian

Or use @all to activate all agents!"""

    result = await telegram.send_message(test_message)

    return {
        "ok": result.get("ok", False),
        "message": "Test message sent" if result.get("ok") else "Failed to send",
        "telegram_response": result,
    }
