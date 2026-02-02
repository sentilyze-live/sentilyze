"""Intelligent agent triggering system for cost optimization."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog

from src.config import settings
from src.data_bridge.bigquery_client import BigQueryDataClient

logger = structlog.get_logger(__name__)


class SmartTrigger:
    """Intelligent triggering system to skip unnecessary agent runs."""

    def __init__(self):
        """Initialize smart trigger system."""
        self.bigquery = BigQueryDataClient()
        self._last_check: Dict[str, datetime] = {}
        self._last_volatility: Dict[str, float] = {}
        
    async def should_run_scout(self) -> Tuple[bool, str]:
        """Determine if SCOUT should run based on market conditions."""
        if not settings.ENABLE_SMART_TRIGGERS:
            return True, "Smart triggers disabled"
        
        # Check time-based reductions
        if self._is_night_mode():
            last_run = self._last_check.get("scout")
            if last_run and (datetime.utcnow() - last_run) < timedelta(hours=12):
                return False, "Night mode: Reduced frequency"
        
        # Check weekend mode
        if settings.WEEKEND_REDUCED_MODE and self._is_weekend():
            last_run = self._last_check.get("scout")
            if last_run and (datetime.utcnow() - last_run) < timedelta(hours=12):
                return False, "Weekend mode: Reduced activity"
        
        try:
            volatility = await self._calculate_market_volatility()
            
            if volatility < settings.SCOUT_MIN_VOLATILITY_THRESHOLD:
                return False, f"Market too calm (volatility: {volatility:.2%})"
            
            if await self._has_significant_data_changes():
                self._last_check["scout"] = datetime.utcnow()
                self._last_volatility["scout"] = volatility
                return True, f"Significant market activity detected"
            else:
                return False, "No significant data changes"
                
        except Exception as e:
            logger.error("smart_trigger.scout_error", error=str(e))
            return True, "Error in trigger, allowing run"

    async def should_run_oracle(self, opportunities: List[Dict]) -> Tuple[bool, str]:
        """Determine if ORACLE should run based on SCOUT results."""
        if not settings.ENABLE_SMART_TRIGGERS:
            return True, "Smart triggers disabled"
        
        high_value = [o for o in opportunities if o.get("opportunity_score", 0) >= settings.ORACLE_TRIGGER_MIN_SCORE]
        
        if not high_value:
            return False, f"No high-value opportunities to validate"
        
        self._last_check["oracle"] = datetime.utcnow()
        return True, f"Validating {len(high_value)} opportunities"

    async def should_run_zara(self, opportunities: List[Dict]) -> Tuple[bool, str]:
        """Determine if ZARA should run."""
        if not settings.ENABLE_SMART_TRIGGERS:
            return True, "Smart triggers disabled"
        
        worthy = [o for o in opportunities if o.get("opportunity_score", 0) >= settings.ZARA_MIN_OPPORTUNITY_SCORE]
        
        if not worthy:
            return False, "No community-worthy opportunities"
        
        self._last_check["zara"] = datetime.utcnow()
        return True, f"Engagement needed for {len(worthy)} opportunities"

    async def should_run_elon(self) -> Tuple[bool, str]:
        """Determine if ELON should run."""
        if not settings.ENABLE_SMART_TRIGGERS:
            return True, "Smart triggers disabled"
        
        if settings.ELON_SKIP_WEEKENDS and self._is_weekend():
            return False, "Weekend: Skipping experiments"
        
        self._last_check["elon"] = datetime.utcnow()
        return True, "Growth experiment check"

    async def should_run_seth(self, opportunities: List[Dict]) -> Tuple[bool, str]:
        """Determine if SETH should run."""
        if not settings.ENABLE_SMART_TRIGGERS:
            return True, "Smart triggers disabled"
        
        content_opps = [o for o in opportunities if o.get("opportunity_score", 0) >= settings.SETH_MIN_OPPORTUNITY_SCORE]
        
        if not content_opps:
            return False, "No content-worthy opportunities"
        
        self._last_check["seth"] = datetime.utcnow()
        return True, f"Content needed for {len(content_opps)} opportunities"

    async def _calculate_market_volatility(self) -> float:
        """Calculate current market volatility."""
        assets = ["BTC", "ETH", "XAU", "SOL"]
        volatilities = []
        
        try:
            for asset in assets:
                data = await self.bigquery.get_market_data(asset=asset, hours=24)
                if len(data) >= 2:
                    prices = [d.get("price", 0) for d in data if d.get("price")]
                    if len(prices) >= 2 and prices[-1] > 0:
                        change = abs(prices[0] - prices[-1]) / prices[-1]
                        volatilities.append(change)
            
            if volatilities:
                return sum(volatilities) / len(volatilities)
            
        except Exception as e:
            logger.error("smart_trigger.volatility_error", error=str(e))
        
        return 0.5

    async def _has_significant_data_changes(self) -> bool:
        """Check if there's been significant new data."""
        try:
            last_run = self._last_check.get("scout")
            if not last_run:
                return True
            
            sentiment_data = await self.bigquery.get_sentiment_data(hours=settings.MIN_NEW_DATA_AGE_MINUTES // 60)
            
            if sentiment_data:
                newest = max(s.get("timestamp") for s in sentiment_data)
                if isinstance(newest, str):
                    newest = datetime.fromisoformat(newest.replace("Z", "+00:00"))
                return newest > last_run
            
        except Exception as e:
            logger.error("smart_trigger.data_changes_error", error=str(e))
        
        return True

    def _is_night_mode(self) -> bool:
        """Check if currently in night mode hours."""
        if not settings.NIGHT_MODE_REDUCTION:
            return False
        hour = datetime.utcnow().hour
        return settings.NIGHT_MODE_HOURS[0] <= hour < settings.NIGHT_MODE_HOURS[1]

    def _is_weekend(self) -> bool:
        """Check if today is weekend."""
        return datetime.utcnow().weekday() >= 5


smart_trigger = SmartTrigger()
