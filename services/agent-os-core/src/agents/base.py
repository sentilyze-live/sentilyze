"""Base agent class for all Agent OS agents."""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from src.api import HiggsfieldClient, KimiClient
from src.config import settings
from src.data_bridge import BigQueryDataClient, FirestoreDataClient, PubSubDataClient
from src.memory import StructuredMemory, TaskState, DailyActivity
from src.utils import TelegramNotifier

logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    """Base class for all agents in the Agent OS system."""

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
        self.bigquery = BigQueryDataClient()
        self.firestore = FirestoreDataClient()
        self.pubsub = PubSubDataClient()
        
        # Initialize structured memory (WORKING.md style)
        self.memory = StructuredMemory(agent_name=agent_type)

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
        }
        
        # Get config for this agent or use defaults
        config = model_config_map.get(agent_type, {})
        
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

        logger.info(
            "agent.run_started",
            agent_type=self.agent_type,
            run_id=run_id,
        )

        try:
            # Pre-run setup
            await self._before_run(context)

            # Execute main logic
            result = await self._execute(context)

            # Post-run cleanup
            await self._after_run(result)

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Save state
            await self._save_state(run_id, result, duration)

            # Notify success
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

            # Notify error
            await self.telegram.send_error_alert(
                agent_name=self.name,
                error=str(e),
                context={"run_id": run_id, "duration": duration},
            )

            return {
                "success": False,
                "agent_type": self.agent_type,
                "run_id": run_id,
                "duration_seconds": duration,
                "error": str(e),
            }

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

