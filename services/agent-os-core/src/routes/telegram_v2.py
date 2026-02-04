"""Telegram routes - Unified webhook with conversation support.

Clean webhook endpoint using the TelegramManager.
Supports multi-turn conversations: follow-up messages are routed
to the agent in the active conversation without needing @mention.
"""

import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import structlog

from src.agents import get_agent
from src.managers.conversation_manager import get_conversation_manager
from src.utils.telegram_manager import get_telegram_manager

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = structlog.get_logger(__name__)


@router.post("/webhook")
async def telegram_webhook(request: Request) -> Dict[str, Any]:
    """Handle incoming Telegram webhook updates.

    This is the main entry point for Telegram messages.

    Flow:
    1. If agent is @mentioned → start new conversation, activate agent
    2. If no mention but active conversation exists → route as follow-up
    3. If no mention and no active conversation → ignore

    Returns:
        Always returns 200 OK to Telegram (to avoid retries)
    """
    try:
        update = await request.json()

        # Extract message basics
        message = update.get("message", {})
        if not message:
            return {"ok": True, "skipped": "no_message"}

        text = message.get("text", "")
        if not text:
            return {"ok": True, "skipped": "no_text"}

        chat_id = str(message.get("chat", {}).get("id", ""))
        user = message.get("from", {})
        user_id = str(user.get("id", ""))
        username = user.get("username") or user.get("first_name", "User")
        message_id = message.get("message_id", 0)

        telegram = get_telegram_manager()
        conversation_mgr = get_conversation_manager()

        # Step 0: Check for autonomous action commands (/approve, /reject)
        if text.startswith("/approve ") or text.startswith("/reject "):
            return await _handle_action_command(text, chat_id)

        # Step 1: Let TelegramManager detect agent mentions
        result = await telegram.handle_webhook_update(update)

        if result.get("action") == "activate_agents":
            # ─── Agent mentioned → Start new conversation ───
            agents = result["agents"]
            task = result["task"]
            telegram_context = result["telegram_context"]

            activated = []
            failed = []

            for agent_name in agents:
                try:
                    agent = get_agent(agent_name)

                    # Start a new conversation
                    conv = await conversation_mgr.start_conversation(
                        chat_id=chat_id,
                        agent_type=agent_name,
                        initial_task=task,
                        username=username,
                    )

                    # Create context for agent
                    context = {
                        "task": task,
                        "conversation_id": conv["conversation_id"],
                        **telegram_context.to_dict(),
                    }

                    # Run agent asynchronously
                    asyncio.create_task(agent.run(context))
                    activated.append(agent_name.upper())
                    logger.info("telegram.agent_activated", agent=agent_name, conversation_id=conv["conversation_id"])

                except ValueError:
                    failed.append(f"{agent_name.upper()} (not found)")
                    logger.error("telegram.agent_not_found", agent=agent_name)
                except Exception as e:
                    failed.append(f"{agent_name.upper()} (error: {str(e)[:30]})")
                    logger.error("telegram.agent_activation_error", agent=agent_name, error=str(e))

            # Send confirmation
            if len(agents) > 1:
                await telegram.notify_broadcast_result(
                    activated_agents=activated,
                    failed_agents=failed,
                    task=task,
                    user_name=telegram_context.username,
                    chat_id=telegram_context.chat_id,
                )
            elif activated:
                await telegram.notify_agent_activated(
                    agent_name=activated[0],
                    task=task,
                    user_name=telegram_context.username,
                    chat_id=telegram_context.chat_id,
                )

        else:
            # ─── No agent mentioned → Check for active conversation ───
            active_conv = await conversation_mgr.firestore.get_any_active_conversation(chat_id)

            if active_conv:
                agent_type = active_conv["agent_type"]
                conversation_id = active_conv["conversation_id"]

                logger.info(
                    "telegram.conversation_followup",
                    agent_type=agent_type,
                    conversation_id=conversation_id,
                )

                # Extend session
                await conversation_mgr.extend_session(
                    conversation_id, chat_id, agent_type
                )

                # Add user message to history
                await conversation_mgr.add_message(
                    conversation_id=conversation_id,
                    chat_id=chat_id,
                    agent_type=agent_type,
                    role="user",
                    content=text,
                )

                # Get conversation history
                history = await conversation_mgr.get_conversation_messages(conversation_id)

                # Run agent with conversation context
                try:
                    agent = get_agent(agent_type)
                    context = {
                        "task": text,
                        "conversation_id": conversation_id,
                        "conversation_history": history,
                        "telegram_chat_id": chat_id,
                        "telegram_user_id": user_id,
                        "telegram_username": username,
                        "telegram_message": text,
                        "telegram_message_id": message_id,
                        "telegram_trigger_type": "followup",
                        "telegram_enabled": True,
                    }

                    asyncio.create_task(agent.run(context))

                except Exception as e:
                    logger.error("telegram.followup_error", agent_type=agent_type, error=str(e))
                    await telegram.send_message(
                        f"⚠️ {agent_type.upper()} follow-up failed: {str(e)[:50]}",
                        chat_id=chat_id,
                    )
            else:
                # No active conversation, no agent mentioned - ignore silently
                logger.debug("telegram.no_active_conversation", chat_id=chat_id)

        # Always return 200 OK to Telegram
        return {"ok": True}

    except Exception as e:
        logger.error("telegram.webhook_error", error=str(e))
        return JSONResponse(
            status_code=200,
            content={"ok": False, "error": str(e)},
        )


@router.get("/webhook")
async def verify_webhook() -> Dict[str, str]:
    """Verify webhook is active."""
    return {
        "status": "active",
        "message": "Telegram webhook endpoint is ready",
        "version": "3.0",
        "features": ["multi-turn conversations", "agent mentions", "broadcast"],
    }


@router.get("/webhook/info")
async def get_webhook_info() -> Dict[str, Any]:
    """Get current webhook information from Telegram."""
    telegram = get_telegram_manager()
    return await telegram.get_webhook_info()


@router.post("/webhook/set")
async def set_webhook(webhook_url: str) -> Dict[str, Any]:
    """Set Telegram webhook URL."""
    telegram = get_telegram_manager()
    return await telegram.set_webhook(webhook_url)


@router.post("/send")
async def send_message(
    text: str,
    chat_id: str = None,
) -> Dict[str, Any]:
    """Send a message to Telegram."""
    telegram = get_telegram_manager()
    return await telegram.send_message(text, chat_id=chat_id)


@router.post("/test")
async def test_telegram() -> Dict[str, Any]:
    """Test Telegram connection."""
    telegram = get_telegram_manager()

    test_message = """🧪 <b>Telegram Test</b>

✅ Bot connection successful!
✅ Webhook endpoint active
✅ Multi-turn conversations enabled
✅ Autonomous brainstorming active

<b>Agentlar:</b>
• @SCOUT - Market intelligence
• @ORACLE - Statistical validation
• @SETH - SEO content
• @ZARA - Community engagement
• @ELON - Growth experiments
• @MARIA - DevOps guardian
• @CODER - Senior developer
• @SENTINEL - Anomaly detection
• @ATLAS - Data quality
• @all - Tum agentlar

<b>Komutlar:</b>
• /approve [id] - Otonom aksiyonu onayla
• /reject [id] [sebep] - Otonom aksiyonu reddet

Sohbet icin @ ile agent sec, sonra @ olmadan devam et."""

    result = await telegram.send_message(test_message)

    return {
        "ok": result.get("ok", False),
        "message": "Test message sent" if result.get("ok") else "Failed to send",
        "telegram_response": result,
    }


async def _handle_action_command(text: str, chat_id: str) -> Dict[str, Any]:
    """Handle /approve and /reject commands for autonomous actions.

    Args:
        text: Command text (/approve action_id or /reject action_id reason)
        chat_id: Telegram chat ID

    Returns:
        Response dict
    """
    telegram = get_telegram_manager()

    try:
        from src.managers.autonomous_actions import get_action_manager
        action_mgr = get_action_manager()

        parts = text.split(maxsplit=2)
        command = parts[0]  # /approve or /reject
        action_id = parts[1] if len(parts) > 1 else ""

        if not action_id:
            await telegram.send_message(
                "⚠️ Kullanim: <code>/approve action_id</code> veya <code>/reject action_id sebep</code>",
                chat_id=chat_id,
            )
            return {"ok": True, "handled": "missing_action_id"}

        if command == "/approve":
            result = await action_mgr.approve_action(action_id)
            if "error" in result:
                await telegram.send_message(f"❌ Hata: {result['error']}", chat_id=chat_id)
            # Success notification is handled inside approve_action
        elif command == "/reject":
            reason = parts[2] if len(parts) > 2 else ""
            result = await action_mgr.reject_action(action_id, reason=reason)
            if "error" in result:
                await telegram.send_message(f"❌ Hata: {result['error']}", chat_id=chat_id)

        return {"ok": True, "handled": command}

    except Exception as e:
        logger.error("telegram.action_command_error", error=str(e))
        await telegram.send_message(
            f"❌ Komut hatasi: {str(e)[:100]}",
            chat_id=chat_id,
        )
        return {"ok": True, "error": str(e)}
