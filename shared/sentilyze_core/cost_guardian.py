"""Cost Guardian - Vertex AI usage tracking and budget enforcement.

This module provides cost monitoring and enforcement for Vertex AI API calls,
ensuring daily limits are not exceeded and providing fallback mechanisms
when budgets are exhausted.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from enum import Enum

from .config import get_settings
from .logging import get_logger
from .firestore_cache import FirestoreCacheClient

logger = get_logger(__name__)
settings = get_settings()


class EnforcementAction(Enum):
    """Cost enforcement actions."""
    NONE = "none"
    CACHE_ONLY = "cache_only"
    REDUCE_FREQUENCY = "reduce_frequency"
    DISABLE_NON_ESSENTIAL = "disable_non_essential"
    EMERGENCY_MODE = "emergency_mode"


@dataclass
class CostBudget:
    """Budget configuration for cost control."""
    daily_vertex_ai_limit: int = 500
    daily_bigquery_limit_usd: float = 1.0
    daily_cloud_run_limit_usd: float = 5.0
    alert_threshold_percent: float = 80.0
    critical_threshold_percent: float = 95.0
    
    # Cost per 1k tokens (Gemini Flash)
    vertex_ai_cost_per_1k: float = 0.000175


@dataclass
class UsageMetrics:
    """Current usage metrics."""
    vertex_ai_calls: int = 0
    vertex_ai_cost_usd: float = 0.0
    bigquery_cost_usd: float = 0.0
    cloud_run_cost_usd: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def total_cost_usd(self) -> float:
        """Calculate total cost."""
        return self.vertex_ai_cost_usd + self.bigquery_cost_usd + self.cloud_run_cost_usd


class CostGuardian:
    """Monitor and enforce cost budgets for Vertex AI and other services.
    
    This class provides:
    - Real-time usage tracking
    - Budget threshold alerts
    - Automatic enforcement actions
    - Fallback to cache/rule-based analysis
    
    Example:
        >>> guardian = CostGuardian()
        >>> await guardian.initialize()
        >>> 
        >>> # Check if call should be allowed
        >>> if await guardian.should_allow_vertex_ai_call(priority="high"):
        >>>     result = await call_gemini_api()
        >>>     await guardian.track_vertex_ai_call(tokens_used=1000)
        >>> else:
        >>>     result = await guardian.get_fallback_result()
    """
    
    def __init__(
        self,
        budget: Optional[CostBudget] = None,
        cache_client: Optional[FirestoreCacheClient] = None,
    ):
        """Initialize Cost Guardian.
        
        Args:
            budget: Budget configuration (uses defaults if not provided)
            cache_client: Cache client for persistence
        """
        self.budget = budget or CostBudget()
        self.cache = cache_client or FirestoreCacheClient()
        self._metrics = UsageMetrics()
        self._enforcement_level = EnforcementAction.NONE
        self._alert_callbacks: List[Callable[[str], None]] = []
        self._enforcement_callbacks: List[Callable[[EnforcementAction], None]] = []
        self._initialized = False
        
        # Cache keys
        self._daily_usage_key = "cost_guardian:daily_usage"
        self._enforcement_key = "cost_guardian:enforcement"
        
    async def initialize(self) -> None:
        """Initialize the cost guardian and load current usage."""
        if self._initialized:
            return
            
        try:
            # Load current day's usage from cache
            await self._load_daily_usage()
            
            # Check current enforcement level
            await self._update_enforcement_level()
            
            self._initialized = True
            logger.info(
                "CostGuardian initialized",
                daily_limit=self.budget.daily_vertex_ai_limit,
                current_usage=self._metrics.vertex_ai_calls,
                enforcement_level=self._enforcement_level.value,
            )
        except Exception as e:
            logger.error("Failed to initialize CostGuardian", error=str(e))
            raise
    
    async def _load_daily_usage(self) -> None:
        """Load current day's usage from cache (lazy loaded)."""
        # Check if already loaded and still valid for today
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self._metrics and self._metrics.last_updated:
            last_update_day = self._metrics.last_updated.strftime("%Y-%m-%d")
            if last_update_day == today and self._metrics.vertex_ai_calls > 0:
                # Already loaded today's data, skip cache read
                logger.debug("Daily usage already loaded, skipping cache read")
                return

        cache_key = f"{self._daily_usage_key}:{today}"

        try:
            cached = await self.cache.get(cache_key, namespace="cost_guardian")
            if cached:
                self._metrics = UsageMetrics(
                    vertex_ai_calls=cached.get("vertex_ai_calls", 0),
                    vertex_ai_cost_usd=cached.get("vertex_ai_cost_usd", 0.0),
                    bigquery_cost_usd=cached.get("bigquery_cost_usd", 0.0),
                    cloud_run_cost_usd=cached.get("cloud_run_cost_usd", 0.0),
                    last_updated=datetime.fromisoformat(cached.get("last_updated", datetime.utcnow().isoformat())),
                )
                logger.debug("Loaded daily usage from cache")
            else:
                self._metrics = UsageMetrics()
                logger.debug("No cached usage found, starting fresh")
        except Exception as e:
            logger.warning("Failed to load daily usage from cache", error=str(e))
            self._metrics = UsageMetrics()
    
    async def _save_daily_usage(self) -> None:
        """Save current day's usage to cache."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        cache_key = f"{self._daily_usage_key}:{today}"
        
        self._metrics.last_updated = datetime.utcnow()
        
        data = {
            "vertex_ai_calls": self._metrics.vertex_ai_calls,
            "vertex_ai_cost_usd": self._metrics.vertex_ai_cost_usd,
            "bigquery_cost_usd": self._metrics.bigquery_cost_usd,
            "cloud_run_cost_usd": self._metrics.cloud_run_cost_usd,
            "last_updated": self._metrics.last_updated.isoformat(),
        }
        
        try:
            await self.cache.set(
                cache_key,
                data,
                ttl=86400,  # 24 hours
                namespace="cost_guardian",
            )
        except Exception as e:
            logger.error("Failed to save daily usage to cache", error=str(e))
    
    async def track_vertex_ai_call(
        self,
        tokens_used: int = 1000,
        model: str = "gemini-flash",
    ) -> None:
        """Track a Vertex AI API call.
        
        Args:
            tokens_used: Number of tokens used in the call
            model: Model name used
        """
        self._metrics.vertex_ai_calls += 1
        
        # Calculate cost (simplified - actual cost depends on input/output split)
        cost = (tokens_used / 1000) * self.budget.vertex_ai_cost_per_1k
        self._metrics.vertex_ai_cost_usd += cost
        
        # Save to cache
        await self._save_daily_usage()
        
        # Check thresholds
        await self._check_thresholds()
        
        logger.debug(
            "Vertex AI call tracked",
            calls_today=self._metrics.vertex_ai_calls,
            cost_usd=round(cost, 6),
            total_cost_usd=round(self._metrics.vertex_ai_cost_usd, 6),
        )
    
    async def should_allow_vertex_ai_call(
        self,
        priority: str = "normal",
    ) -> bool:
        """Check if a new Vertex AI call should be allowed.
        
        Args:
            priority: Call priority ("high", "normal", "low")
            
        Returns:
            True if call should be allowed, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        # High priority always allowed
        if priority == "high":
            return True
        
        # Check against limit with buffer based on priority
        current = self._metrics.vertex_ai_calls
        limit = self.budget.daily_vertex_ai_limit
        
        buffers = {
            "high": 0.0,      # No buffer for high (already handled above)
            "normal": 0.05,   # 5% buffer for normal
            "low": 0.15,      # 15% buffer for low priority
        }
        
        buffer = buffers.get(priority, 0.05)
        allowed = current < (limit * (1 - buffer))
        
        if not allowed:
            logger.warning(
                "Vertex AI call blocked by CostGuardian",
                current=current,
                limit=limit,
                priority=priority,
                enforcement_level=self._enforcement_level.value,
            )
        
        return allowed
    
    async def get_current_usage(self) -> UsageMetrics:
        """Get current usage metrics."""
        if not self._initialized:
            await self.initialize()
        return self._metrics
    
    async def get_usage_percent(self) -> float:
        """Get current usage as percentage of daily limit."""
        if not self._initialized:
            await self.initialize()
        return (self._metrics.vertex_ai_calls / self.budget.daily_vertex_ai_limit) * 100
    
    async def _check_thresholds(self) -> None:
        """Check usage thresholds and trigger alerts/actions."""
        usage_percent = await self.get_usage_percent()
        
        # Alert threshold
        if usage_percent >= self.budget.alert_threshold_percent:
            await self._send_alert(
                f"Vertex AI usage at {usage_percent:.1f}% of daily limit "
                f"({self._metrics.vertex_ai_calls}/{self.budget.daily_vertex_ai_limit} calls)"
            )
        
        # Critical threshold - enforce limits
        if usage_percent >= self.budget.critical_threshold_percent:
            await self._enforce_limit()
        
        # Update enforcement level
        await self._update_enforcement_level()
    
    async def _update_enforcement_level(self) -> None:
        """Update enforcement level based on current usage."""
        usage_percent = await self.get_usage_percent()
        
        new_level = EnforcementAction.NONE
        
        if usage_percent >= 100:
            new_level = EnforcementAction.EMERGENCY_MODE
        elif usage_percent >= 95:
            new_level = EnforcementAction.DISABLE_NON_ESSENTIAL
        elif usage_percent >= 90:
            new_level = EnforcementAction.REDUCE_FREQUENCY
        elif usage_percent >= 80:
            new_level = EnforcementAction.CACHE_ONLY
        
        if new_level != self._enforcement_level:
            self._enforcement_level = new_level
            
            # Save to cache
            try:
                await self.cache.set(
                    self._enforcement_key,
                    {
                        "level": new_level.value,
                        "updated_at": datetime.utcnow().isoformat(),
                        "usage_percent": usage_percent,
                    },
                    ttl=86400,
                    namespace="cost_guardian",
                )
            except Exception as e:
                logger.error("Failed to save enforcement level", error=str(e))
            
            # Trigger callbacks
            for callback in self._enforcement_callbacks:
                try:
                    callback(new_level)
                except Exception as e:
                    logger.error("Enforcement callback failed", error=str(e))
            
            logger.info(
                "Enforcement level updated",
                level=new_level.value,
                usage_percent=usage_percent,
            )
    
    async def _send_alert(self, message: str) -> None:
        """Send cost alert notification."""
        logger.warning(f"COST ALERT: {message}")
        
        # Trigger callbacks
        for callback in self._alert_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error("Alert callback failed", error=str(e))
    
    async def _enforce_limit(self) -> None:
        """Enforce cost limit by taking actions."""
        logger.error(
            "Cost limit enforcement triggered",
            usage=self._metrics.vertex_ai_calls,
            limit=self.budget.daily_vertex_ai_limit,
        )
        
        # Actions are handled by enforcement level change
        # Services should check get_enforcement_level() and act accordingly
    
    def get_enforcement_level(self) -> EnforcementAction:
        """Get current enforcement level."""
        return self._enforcement_level
    
    def register_alert_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback for cost alerts.
        
        Args:
            callback: Function to call with alert message
        """
        self._alert_callbacks.append(callback)
    
    def register_enforcement_callback(
        self,
        callback: Callable[[EnforcementAction], None],
    ) -> None:
        """Register a callback for enforcement level changes.
        
        Args:
            callback: Function to call with new enforcement level
        """
        self._enforcement_callbacks.append(callback)
    
    async def get_fallback_result(
        self,
        content_type: str = "sentiment",
    ) -> Dict:
        """Get fallback result when API calls are blocked.
        
        Args:
            content_type: Type of content being analyzed
            
        Returns:
            Fallback result dictionary
        """
        if content_type == "sentiment":
            return {
                "score": 0.0,
                "label": "neutral",
                "confidence": 0.0,
                "explanation": "Analysis temporarily unavailable due to cost limits. Using neutral fallback.",
                "model_used": "cost_guardian_fallback",
                "fallback_level": self._enforcement_level.value,
            }
        
        return {
            "error": "Service temporarily unavailable",
            "fallback_level": self._enforcement_level.value,
            "reason": "Cost budget exceeded",
        }
    
    async def reset_daily_usage(self) -> None:
        """Reset daily usage counters (for testing or manual reset)."""
        self._metrics = UsageMetrics()
        self._enforcement_level = EnforcementAction.NONE
        await self._save_daily_usage()
        logger.info("Daily usage reset")
    
    async def get_cost_summary(self) -> Dict:
        """Get cost summary for reporting.
        
        Returns:
            Dictionary with cost breakdown
        """
        return {
            "vertex_ai": {
                "calls": self._metrics.vertex_ai_calls,
                "cost_usd": round(self._metrics.vertex_ai_cost_usd, 4),
                "limit": self.budget.daily_vertex_ai_limit,
                "usage_percent": round(await self.get_usage_percent(), 2),
            },
            "bigquery": {
                "cost_usd": round(self._metrics.bigquery_cost_usd, 4),
                "limit": self.budget.daily_bigquery_limit_usd,
            },
            "cloud_run": {
                "cost_usd": round(self._metrics.cloud_run_cost_usd, 4),
                "limit": self.budget.daily_cloud_run_limit_usd,
            },
            "total": {
                "cost_usd": round(self._metrics.total_cost_usd, 4),
            },
            "enforcement": {
                "level": self._enforcement_level.value,
                "alert_threshold": self.budget.alert_threshold_percent,
                "critical_threshold": self.budget.critical_threshold_percent,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }


# Global instance for shared use
_guardian: Optional[CostGuardian] = None


async def get_cost_guardian() -> CostGuardian:
    """Get or create global CostGuardian instance."""
    global _guardian
    if _guardian is None:
        _guardian = CostGuardian()
        await _guardian.initialize()
    return _guardian


def reset_cost_guardian() -> None:
    """Reset global CostGuardian instance (for testing)."""
    global _guardian
    _guardian = None