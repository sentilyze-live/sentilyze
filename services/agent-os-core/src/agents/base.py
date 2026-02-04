"""Base agent class for all Agent OS agents."""

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import structlog

from src.api import HiggsfieldClient, KimiClient, VertexAIClient
from src.config import settings
from src.data_bridge import BigQueryDataClient, FirestoreDataClient, PubSubDataClient
from src.memory import StructuredMemory, TaskState, DailyActivity
from src.utils import TelegramNotifier
from src.utils.telegram_manager import get_telegram_manager

logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    """Base class for all agents in the Agent OS system."""
    
    # Class-level tracking to prevent notification spam across all agents
    _last_error_notifications: Dict[str, datetime] = {}
    _error_counts: Dict[str, int] = {}
    _notification_cooldown = timedelta(minutes=15)  # 15 minutes between notifications
    _max_notifications_per_hour = 4  # Max 4 notifications per hour per agent

    def __init__(
        self,
        agent_type: str,
        name: str,
        description: str,
    ):
        """Initialize base agent.

        Args:
            agent_type: Unique agent type identifier
            name: Human-readable agent name
            description: Agent description
        """
        self.agent_type = agent_type
        self.name = name
        self.description = description
        self.agent_id = str(uuid.uuid4())

        # Initialize Kimi client with agent-specific model configuration
        self.kimi = self._initialize_kimi_client()
        self.telegram = TelegramNotifier()
        self.telegram_manager = get_telegram_manager()  # New unified manager
        self.bigquery = BigQueryDataClient()
        self.firestore = FirestoreDataClient()
        self.pubsub = PubSubDataClient()

        # Initialize structured memory (WORKING.md style)
        self.memory = StructuredMemory(agent_name=agent_type)

        # Telegram context (set when agent is triggered via Telegram)
        self.telegram_context: Optional[Dict[str, Any]] = None

        # Higgsfield client (only for Ece agent typically)
        self.higgsfield: Optional[HiggsfieldClient] = None

        # Capabilities and metadata
        self.capabilities: List[str] = []
        self.system_prompt: str = ""
        self.version: str = "1.0.0"

        logger.info(
            "agent.initialized",
            agent_type=self.agent_type,
            name=self.name,
            agent_id=self.agent_id,
            model=self.kimi.model,
        )

    def _initialize_kimi_client(self) -> KimiClient:
        """Initialize Kimi client with agent-specific model configuration.
        
        Each agent type uses an optimized model for its specific use case:
        - SCOUT & ORACLE: kimi-k2-thinking (deep reasoning)
        - SETH & ZARA: kimi-k2-0905-preview (coding/JSON, cost-effective)
        - ELON: kimi-k2-0905-preview (speed vs cost balance)
        - MARIA: Uses Vertex AI as fallback when MOONSHOT_API_KEY is not set
        
        Returns:
            Configured KimiClient instance
        """
        agent_type = self.agent_type.lower()
        
        # Map agent types to their specific model settings
        model_config_map = {
            "scout": {
                "model": settings.MOONSHOT_MODEL_SCOUT,
                "max_tokens": settings.MOONSHOT_MAX_TOKENS_SCOUT,
                "temperature": settings.MOONSHOT_TEMPERATURE_SCOUT,
            },
            "oracle": {
                "model": settings.MOONSHOT_MODEL_ORACLE,
                "max_tokens": settings.MOONSHOT_MAX_TOKENS_ORACLE,
                "temperature": settings.MOONSHOT_TEMPERATURE_ORACLE,
            },
            "seth": {
                "model": settings.MOONSHOT_MODEL_SETH,
                "max_tokens": settings.MOONSHOT_MAX_TOKENS_SETH,
                "temperature": settings.MOONSHOT_TEMPERATURE_SETH,
            },
            "zara": {
                "model": settings.MOONSHOT_MODEL_ZARA,
                "max_tokens": settings.MOONSHOT_MAX_TOKENS_ZARA,
                "temperature": settings.MOONSHOT_TEMPERATURE_ZARA,
            },
            "elon": {
                "model": settings.MOONSHOT_MODEL_ELON,
                "max_tokens": settings.MOONSHOT_MAX_TOKENS_ELON,
                "temperature": settings.MOONSHOT_TEMPERATURE_ELON,
            },
            "maria": {
                "model": settings.MOONSHOT_MODEL,
                "max_tokens": settings.MOONSHOT_MAX_TOKENS,
                "temperature": settings.MOONSHOT_TEMPERATURE,
            },
            "coder": {
                "model": settings.MOONSHOT_MODEL_CODER,
                "max_tokens": settings.MOONSHOT_MAX_TOKENS_CODER,
                "temperature": settings.MOONSHOT_TEMPERATURE_CODER,
            },
            "sentinel": {
                "model": settings.MOONSHOT_MODEL_SENTINEL,
                "max_tokens": settings.MOONSHOT_MAX_TOKENS_SENTINEL,
                "temperature": settings.MOONSHOT_TEMPERATURE_SENTINEL,
            },
            "atlas": {
                "model": settings.MOONSHOT_MODEL_ATLAS,
                "max_tokens": settings.MOONSHOT_MAX_TOKENS_ATLAS,
                "temperature": settings.MOONSHOT_TEMPERATURE_ATLAS,
            },
        }
        
        # Get config for this agent or use defaults
        config = model_config_map.get(agent_type, {})
        
        # Check if we should use Vertex AI (for MARIA when MOONSHOT_API_KEY is missing)
        use_vertex_ai = settings.ENABLE_VERTEX_AI_FOR_AGENTS and not settings.MOONSHOT_API_KEY
        
        if use_vertex_ai and agent_type == "maria":
            logger.info(
                "kimi_client.using_vertex_ai_fallback",
                agent_type=agent_type,
                reason="MOONSHOT_API_KEY not set",
            )
            # Return a KimiClient that uses Vertex AI internally
            return KimiClient(
                model=config.get("model"),
                max_tokens=config.get("max_tokens"),
                temperature=config.get("temperature"),
            )
        
        logger.info(
            "kimi_client.initializing_for_agent",
            agent_type=agent_type,
            model=config.get("model", settings.MOONSHOT_MODEL),
            max_tokens=config.get("max_tokens", settings.MOONSHOT_MAX_TOKENS),
            temperature=config.get("temperature", settings.MOONSHOT_TEMPERATURE),
        )
        
        return KimiClient(
            model=config.get("model"),
            max_tokens=config.get("max_tokens"),
            temperature=config.get("temperature"),
        )

    async def run(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute agent's main workflow.

        Args:
            context: Optional context data

        Returns:
            Execution results
        """
        start_time = datetime.utcnow()
        run_id = str(uuid.uuid4())

        # Check if this is a Telegram-triggered run
        if context and context.get("telegram_enabled"):
            self.telegram_context = context
            logger.info(
                "agent.run_started_telegram",
                agent_type=self.agent_type,
                run_id=run_id,
                user=context.get("telegram_username"),
            )
        else:
            self.telegram_context = None
            logger.info(
                "agent.run_started",
                agent_type=self.agent_type,
                run_id=run_id,
            )

        try:
            # Pre-run setup
            await self._before_run(context)

            # Check if this is a conversational follow-up
            if self.is_conversation_mode():
                response_text = await self.respond_conversationally(context)
                await self.reply_to_telegram(response_text)
                result = {"response": response_text, "mode": "conversation"}
            else:
                # Execute main logic
                result = await self._execute(context)

                # If Telegram-triggered, send a conversational summary
                if self.is_telegram_triggered() and context:
                    formatted = await self._format_telegram_response(result, context)
                    if formatted:
                        await self.reply_to_telegram(formatted)

            # Post-run cleanup
            await self._after_run(result)

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Save state
            await self._save_state(run_id, result, duration)

            # Notify success (skip for conversation mode - already sent via Telegram)
            if not self.is_conversation_mode():
                await self.telegram.notify_agent_run(
                    agent_name=self.name,
                    status="success",
                    duration_seconds=duration,
                    output_summary=self._summarize_result(result),
                )

            logger.info(
                "agent.run_completed",
                agent_type=self.agent_type,
                run_id=run_id,
                duration=duration,
                mode="conversation" if self.is_conversation_mode() else "execute",
            )

            return {
                "success": True,
                "agent_type": self.agent_type,
                "run_id": run_id,
                "duration_seconds": duration,
                "result": result,
            }

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.error(
                "agent.run_failed",
                agent_type=self.agent_type,
                run_id=run_id,
                error=str(e),
                duration=duration,
            )

            # Notify error only if cooldown has passed
            if self._should_send_error_notification():
                error_count = self._error_counts.get(self.agent_type, 0)
                await self.telegram.send_error_alert(
                    agent_name=self.name,
                    error=str(e),
                    context={
                        "run_id": run_id, 
                        "duration": duration,
                        "recent_error_count": error_count,
                    },
                )
                self._last_error_notifications[self.agent_type] = datetime.utcnow()

            return {
                "success": False,
                "agent_type": self.agent_type,
                "run_id": run_id,
                "duration_seconds": duration,
                "error": str(e),
            }

    def _should_send_error_notification(self) -> bool:
        """Check if we should send an error notification based on cooldown.
        
        Returns:
            True if notification should be sent, False otherwise
        """
        now = datetime.utcnow()
        agent_type = self.agent_type
        
        # Get last notification time
        last_notification = self._last_error_notifications.get(agent_type)
        
        if last_notification is None:
            # Never sent before, send now
            self._error_counts[agent_type] = 1
            return True
        
        # Check if cooldown has passed
        time_since_last = now - last_notification
        if time_since_last >= self._notification_cooldown:
            # Cooldown passed, reset counter
            self._error_counts[agent_type] = 1
            return True
        
        # Still in cooldown, increment counter
        self._error_counts[agent_type] = self._error_counts.get(agent_type, 0) + 1
        
        # Only log that we're skipping notification (not sending Telegram)
        if self._error_counts[agent_type] <= 3:  # Log first few suppressions
            logger.warning(
                "agent.error_notification_suppressed",
                agent_type=agent_type,
                error_count=self._error_counts[agent_type],
                cooldown_remaining_seconds=(self._notification_cooldown - time_since_last).total_seconds(),
            )
        
        return False

    @abstractmethod
    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute agent-specific logic.

        Args:
            context: Optional context data

        Returns:
            Execution results
        """
        pass

    async def _before_run(self, context: Optional[Dict[str, Any]]) -> None:
        """Hook called before run.

        Args:
            context: Optional context data
        """
        pass

    async def _after_run(self, result: Dict[str, Any]) -> None:
        """Hook called after run.

        Args:
            result: Execution results
        """
        pass

    async def _save_state(
        self,
        run_id: str,
        result: Dict[str, Any],
        duration: float,
    ) -> None:
        """Save agent state to Firestore.

        Args:
            run_id: Run identifier
            result: Execution results
            duration: Execution duration
        """
        state = {
            "last_run_id": run_id,
            "last_run_at": datetime.utcnow(),
            "last_run_duration": duration,
            "last_run_success": result.get("success", False),
            "run_count": await self._increment_run_count(),
            "version": self.version,
        }

        await self.firestore.save_agent_state(self.agent_type, state)

    async def _increment_run_count(self) -> int:
        """Increment and return run count.

        Returns:
            New run count
        """
        current_state = await self.firestore.get_agent_state(self.agent_type)
        current_count = current_state.get("run_count", 0) if current_state else 0
        return current_count + 1

    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """Summarize result for notifications.

        Args:
            result: Execution results

        Returns:
            Summary string
        """
        return f"Completed with {len(result)} items"

    async def get_sentiment_data(
        self,
        asset: Optional[str] = None,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get sentiment data from BigQuery.

        Args:
            asset: Asset symbol
            hours: Hours of data

        Returns:
            Sentiment data
        """
        return await self.bigquery.get_sentiment_data(asset=asset, hours=hours)

    async def get_prediction_data(
        self,
        asset: Optional[str] = None,
        hours: int = 168,
    ) -> List[Dict[str, Any]]:
        """Get prediction data from BigQuery.

        Args:
            asset: Asset symbol
            hours: Hours of data

        Returns:
            Prediction data
        """
        return await self.bigquery.get_prediction_data(asset=asset, hours=hours)

    async def get_market_data(
        self,
        asset: Optional[str] = None,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get market data from BigQuery.

        Args:
            asset: Asset symbol
            hours: Hours of data

        Returns:
            Market data
        """
        return await self.bigquery.get_market_data(asset=asset, hours=hours)

    async def get_user_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get user analytics from BigQuery.

        Args:
            days: Days of data

        Returns:
            Analytics data
        """
        return await self.bigquery.get_user_analytics(days=days)

    async def cache_get(self, key: str) -> Optional[Any]:
        """Get cached value.

        Args:
            key: Cache key

        Returns:
            Cached value
        """
        return await self.firestore.cache_get(f"{self.agent_type}:{key}")

    async def cache_set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
    ) -> None:
        """Set cached value.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL
        """
        await self.firestore.cache_set(
            f"{self.agent_type}:{key}",
            value,
            ttl_seconds,
        )

    # Structured Memory Methods (WORKING.md style)
    async def get_working_memory(self) -> TaskState:
        """Get current working memory (WORKING.md equivalent).
        
        Returns:
            Current task state
        """
        return await self.memory.get_working_memory()
    
    async def update_working_memory(
        self,
        title: str,
        description: str = "",
        status: str = "in_progress",
        progress_percent: int = 0,
        next_steps: Optional[List[str]] = None,
        blockers: Optional[List[str]] = None,
        notes: str = "",
    ) -> None:
        """Update working memory with current task state.
        
        Args:
            title: Task title
            description: Task description
            status: Task status (idle, in_progress, blocked, review, done)
            progress_percent: Progress percentage (0-100)
            next_steps: List of next steps
            blockers: List of blockers
            notes: Additional notes
        """
        task_state = TaskState(
            title=title,
            description=description,
            status=status,
            progress_percent=progress_percent,
            next_steps=next_steps or [],
            blockers=blockers or [],
            notes=notes,
            started_at=datetime.utcnow().isoformat() if status == "in_progress" else None,
            last_updated=datetime.utcnow().isoformat(),
        )
        await self.memory.update_working_memory(task_state)
        logger.debug("agent.working_memory_updated", agent=self.agent_type, task=title)
    
    async def log_activity(
        self,
        action: str,
        details: str,
        result: Optional[str] = None,
    ) -> None:
        """Log daily activity.
        
        Args:
            action: What was done
            details: Description
            result: Optional result
        """
        await self.memory.add_daily_activity(action, details, result)
        logger.debug("agent.activity_logged", agent=self.agent_type, action=action)
    
    async def remember(
        self,
        category: str,
        key: str,
        value: str,
        importance: str = "medium",
    ) -> None:
        """Add long-term memory.
        
        Args:
            category: Memory category (e.g., "lessons", "decisions")
            key: Unique key
            value: Memory content
            importance: low, medium, high, critical
        """
        await self.memory.add_long_term_memory(category, key, value, importance)
        logger.info("agent.memory_added", agent=self.agent_type, category=category, key=key)
    
    async def get_memory_context(self) -> Dict[str, Any]:
        """Get full memory context for this agent.

        Returns:
            Dictionary with working, daily, and long-term memory
        """
        return await self.memory.get_full_context()

    # ═══════════════════════════════════════════════════════════════════
    # Telegram Integration Methods
    # ═══════════════════════════════════════════════════════════════════

    async def reply_to_telegram(self, message: str) -> bool:
        """Reply to Telegram user who triggered this agent.

        Only works if agent was triggered via Telegram.
        Automatically sends to the correct chat.

        Args:
            message: Message to send

        Returns:
            True if sent successfully, False otherwise

        Example:
            ```python
            if self.telegram_context:
                await self.reply_to_telegram("✅ Analysis complete! Found 5 opportunities.")
            ```
        """
        if not self.telegram_context:
            logger.debug("agent.reply_skipped", reason="not_telegram_triggered")
            return False

        chat_id = self.telegram_context.get("telegram_chat_id")
        if not chat_id:
            logger.warning("agent.reply_failed", reason="no_chat_id")
            return False

        try:
            # Add agent signature
            formatted_message = f"🤖 <b>{self.name}</b>\n\n{message}"

            # Send via telegram manager
            result = await self.telegram_manager.send_message(
                text=formatted_message,
                chat_id=chat_id,
            )

            success = result.get("ok", False)
            if success:
                logger.info("agent.telegram_reply_sent", agent=self.agent_type)

                # Store agent response in conversation history
                conversation_id = self.telegram_context.get("conversation_id")
                if conversation_id:
                    try:
                        from src.managers.conversation_manager import get_conversation_manager
                        conv_mgr = get_conversation_manager()
                        await conv_mgr.add_message(
                            conversation_id=conversation_id,
                            chat_id=chat_id,
                            agent_type=self.agent_type,
                            role="agent",
                            content=message,
                        )
                    except Exception as conv_err:
                        logger.warning("agent.conversation_store_failed", error=str(conv_err))
            else:
                logger.error("agent.telegram_reply_failed", error=result.get("error"))

            return success

        except Exception as e:
            logger.error("agent.telegram_reply_error", error=str(e))
            return False

    def is_conversation_mode(self) -> bool:
        """Check if this run is a conversation follow-up with history.

        Returns:
            True if running in conversation mode, False otherwise
        """
        if not self.telegram_context:
            return False
        return bool(self.telegram_context.get("conversation_history"))

    async def respond_conversationally(self, context: Dict[str, Any]) -> str:
        """Generate a conversational response using conversation history.

        Builds a multi-turn messages array from the ConversationManager
        history and sends to KimiClient.chat().

        Args:
            context: Context with conversation_history and task

        Returns:
            Conversational response text
        """
        history = context.get("conversation_history", [])
        user_message = context.get("task", "")

        # Build messages array for LLM (last 10 messages to control costs)
        messages = []
        for msg in history[-10:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            content = msg.get("content", "")
            if content:
                messages.append({"role": role, "content": content})

        # Ensure current message is included
        if not messages or messages[-1].get("content") != user_message:
            messages.append({"role": "user", "content": user_message})

        # Get conversational system prompt
        system_prompt = self._get_conversational_system_prompt()

        # Generate response via multi-turn chat
        response = await self.kimi.chat(
            messages=messages,
            system_prompt=system_prompt,
        )

        return response

    def _get_conversational_system_prompt(self) -> str:
        """Get conversation-friendly system prompt.

        Override in subclasses for agent-specific conversational personality.

        Returns:
            Conversational system prompt
        """
        return f"""You are {self.name}, part of the Sentilyze AI team.
You are having a natural conversation via Telegram.

RULES:
- Respond naturally and conversationally in the user's language
- Reference previous messages when relevant
- Keep responses concise (Telegram format, max ~500 chars)
- Be helpful and proactive
- If you need clarification, ask
- Use your domain expertise: {self.description}

You can use HTML formatting: <b>bold</b>, <i>italic</i>, <code>code</code>"""

    async def _format_telegram_response(
        self,
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Format execution result as a conversational Telegram message.

        Uses the LLM to generate a natural-sounding summary of the
        structured result for Telegram.

        Override in subclasses for agent-specific formatting.

        Args:
            result: Execution results dict
            context: Optional context with task info

        Returns:
            Formatted message string or None
        """
        task = context.get("task", "") if context else ""

        # Truncate result for prompt
        result_str = json.dumps(result, indent=2, default=str)[:2000]

        prompt = f"""Summarize this agent result into a natural, conversational Telegram message.
The user asked: "{task}"

Result data:
{result_str}

Write a concise, helpful response in the user's language. Use HTML formatting (<b>, <i>, <code>). Max 500 chars."""

        try:
            return await self.kimi.generate(
                prompt=prompt,
                system_prompt=self._get_conversational_system_prompt(),
                max_tokens=500,
            )
        except Exception:
            return self._summarize_result(result)

    def is_telegram_triggered(self) -> bool:
        """Check if this agent run was triggered via Telegram.

        Returns:
            True if triggered via Telegram, False otherwise
        """
        return bool(self.telegram_context and self.telegram_context.get("telegram_enabled"))

    def get_telegram_user(self) -> Optional[str]:
        """Get Telegram username who triggered this run.

        Returns:
            Username or None
        """
        if not self.telegram_context:
            return None
        return self.telegram_context.get("telegram_username")

    def get_telegram_task(self) -> Optional[str]:
        """Get task description from Telegram message.

        Returns:
            Task description or None
        """
        if not self.telegram_context:
            return None
        return self.telegram_context.get("task")

    # ═══════════════════════════════════════════════════════════════════

    def get_info(self) -> Dict[str, Any]:
        """Get agent information.

        Returns:
            Agent info
        """
        return {
            "agent_type": self.agent_type,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": self.capabilities,
            "agent_id": self.agent_id,
        }

