"""FRED (Federal Reserve Economic Data) API collector.

FRED provides:
- Economic indicators (interest rates, inflation, employment)
- Treasury yields
- Dollar index (DXY)
- GDP and economic growth data
- Custom data series for financial analysis

API Documentation: https://fred.stlouisfed.org/docs/api/fred/
"""

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

import httpx

from sentilyze_core import DataSource, RawEvent, get_logger
from sentilyze_core.circuit_breaker import circuit_breaker
from sentilyze_core.exceptions import ExternalServiceError

from .base import BaseEventCollector

if TYPE_CHECKING:
    from ..publisher import EventPublisher

logger = get_logger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred"

# Default series to track for gold/crypto market analysis
DEFAULT_SERIES = {
    # Interest Rates
    "DFF": "Federal Funds Effective Rate",
    "DTB3": "3-Month Treasury Bill",
    "DGS10": "10-Year Treasury Constant Maturity Rate",
    "DGS2": "2-Year Treasury Constant Maturity Rate",
    "T10Y2Y": "10-Year Treasury Constant Maturity Minus 2-Year",
    
    # Dollar Index & Forex
    "DTWEXBGS": "Trade Weighted U.S. Dollar Index",
    
    # Inflation
    "CPIAUCSL": "Consumer Price Index for All Urban Consumers",
    "PCEPI": "Personal Consumption Expenditures Price Index",
    "CORESTICKM159SFRBATL": "Sticky Price Consumer Price Index",
    
    # Employment
    "UNRATE": "Unemployment Rate",
    "PAYEMS": "Total Nonfarm Payrolls",
    
    # Economic Activity
    "GDP": "Gross Domestic Product",
    "INDPRO": "Industrial Production Index",
    "RSXFS": "Advance Retail Sales",
    
    # Gold-related
    "GOLDAMGBD228NLBM": "Gold Fixing Price 10:30 A.M. (London Time)",
    "GOLDPMGBD228NLBM": "Gold Fixing Price 3:00 P.M. (London Time)",
}

# Rate limiting: 120 requests per minute
REQUESTS_PER_MINUTE = 120
MIN_INTERVAL_SECONDS = 60.0 / REQUESTS_PER_MINUTE


class FredCollector(BaseEventCollector):
    """FRED API collector for economic data."""

    def __init__(
        self,
        publisher: "EventPublisher",
        api_key: Optional[str] = None,
        series: Optional[dict[str, str]] = None,
    ) -> None:
        super().__init__(publisher)
        self.api_key = api_key
        self.series = series or DEFAULT_SERIES
        self._session: Optional[httpx.AsyncClient] = None
        self._last_request_time: Optional[datetime] = None
        self._settings = None

    async def initialize(self) -> None:
        """Initialize FRED client."""
        from sentilyze_core import get_settings

        self._settings = get_settings()
        
        # Get API key from settings if not provided
        if not self.api_key:
            self.api_key = getattr(self._settings, 'fred_api_key', None)
            
        if not self.api_key:
            logger.warning("FRED API key not configured")
            raise ExternalServiceError(
                "FRED API key required",
                service="fred",
            )

        # Initialize HTTP client
        self._session = httpx.AsyncClient(
            base_url=FRED_BASE_URL,
            headers={
                "Accept": "application/json",
            },
            timeout=30.0,
        )

        self._initialized = True
        logger.info(
            "FRED collector initialized",
            series_count=len(self.series),
        )

    async def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        if self._last_request_time:
            elapsed = (datetime.now(timezone.utc) - self._last_request_time).total_seconds()
            if elapsed < MIN_INTERVAL_SECONDS:
                await asyncio.sleep(MIN_INTERVAL_SECONDS - elapsed)
        self._last_request_time = datetime.now(timezone.utc)

    @circuit_breaker(failure_threshold=5, recovery_timeout=60)
    async def _fetch_series_data(self, series_id: str) -> dict[str, Any]:
        """Fetch latest data for a series."""
        await self._rate_limit()

        try:
            params = {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1,  # Get latest value only
            }
            
            response = await self._session.get("/series/observations", params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data or "observations" not in data:
                logger.warning("No data returned from FRED", series_id=series_id)
                return {}
            
            observations = data.get("observations", [])
            if not observations:
                return {}
            
            latest = observations[0]
            return {
                "series_id": series_id,
                "date": latest.get("date"),
                "value": latest.get("value"),
            }
        except httpx.HTTPStatusError as e:
            logger.error(
                "FRED API HTTP error",
                status_code=e.response.status_code,
                series_id=series_id,
            )
            raise ExternalServiceError(
                f"FRED API error: {e.response.status_code}",
                service="fred",
            )
        except httpx.RequestError as e:
            logger.error(
                "FRED API request failed",
                error=str(e),
                series_id=series_id,
            )
            raise ExternalServiceError(
                f"FRED request failed: {e}",
                service="fred",
            )

    @circuit_breaker(failure_threshold=5, recovery_timeout=60)
    async def _fetch_series_info(self, series_id: str) -> dict[str, Any]:
        """Fetch series metadata."""
        await self._rate_limit()

        try:
            params = {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
            }
            
            response = await self._session.get("/series", params=params)
            response.raise_for_status()
            data = response.json()
            
            if data and "seriess" in data and len(data["seriess"]) > 0:
                return data["seriess"][0]
            return {}
        except Exception as e:
            logger.warning("Failed to fetch series info", series_id=series_id, error=str(e))
            return {}

    def _transform_to_event(self, series_id: str, series_name: str, data: dict[str, Any], info: dict[str, Any]) -> RawEvent:
        """Transform FRED data to RawEvent."""
        # Parse value
        value_str = data.get("value", ".")
        try:
            value = float(value_str) if value_str != "." else None
        except (ValueError, TypeError):
            value = None
        
        # Parse date
        date_str = data.get("date", "")
        try:
            timestamp = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            timestamp = datetime.now(timezone.utc)
        
        # Determine category
        category = "economic_indicator"
        if "Treasury" in series_name or "Rate" in series_name:
            category = "interest_rate"
        elif "Dollar" in series_name:
            category = "currency_index"
        elif "Gold" in series_name:
            category = "gold_price"
        elif "CPI" in series_id or "PCE" in series_id:
            category = "inflation"
        elif "GDP" in series_id:
            category = "gdp"
        elif "UNRATE" in series_id or "PAYEMS" in series_id:
            category = "employment"
        
        return RawEvent(
            source=DataSource.FRED,
            event_type="economic_data",
            symbol=series_id,
            timestamp=timestamp,
            payload={
                "series_id": series_id,
                "series_name": series_name,
                "category": category,
                "value": value,
                "value_text": value_str,
                "date": date_str,
                "units": info.get("units"),
                "frequency": info.get("frequency"),
                "last_updated": info.get("last_updated"),
            },
            metadata={
                "collector": "fred",
                "source": "Federal Reserve Economic Data",
                "notes": info.get("notes"),
            }
        )

    async def collect(self, **kwargs: Any) -> int:
        """Collect economic data from FRED.
        
        Args:
            **kwargs: Optional 'series' to override default series
            
        Returns:
            Number of events collected
        """
        if not self._initialized:
            raise RuntimeError("Collector not initialized")

        series = kwargs.get("series", self.series)
        events: list[RawEvent] = []

        logger.info("Starting FRED collection", series_count=len(series))

        for series_id, series_name in series.items():
            try:
                # Fetch data and info in parallel
                data_task = self._fetch_series_data(series_id)
                info_task = self._fetch_series_info(series_id)
                data, info = await asyncio.gather(data_task, info_task)
                
                if data and data.get("value"):
                    event = self._transform_to_event(series_id, series_name, data, info)
                    events.append(event)
                    logger.debug(
                        "Collected FRED data",
                        series_id=series_id,
                        value=data.get("value"),
                    )
            except Exception as e:
                logger.error("Failed to collect series data", series_id=series_id, error=str(e))
                continue

        # Publish events
        if events:
            try:
                message_ids = await self.publish_events(events)
                logger.info(
                    "Published FRED events",
                    count=len(message_ids),
                    series=[e.symbol for e in events],
                )
                return len(events)
            except Exception as e:
                logger.error("Failed to publish events", error=str(e))
                return 0

        return 0

    async def close(self) -> None:
        """Close the collector and cleanup resources."""
        if self._session:
            await self._session.aclose()
            self._session = None
        self._initialized = False
        logger.info("FRED collector closed")
