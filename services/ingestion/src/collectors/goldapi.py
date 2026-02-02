"""GoldAPI.io collector for real-time gold and precious metals prices.

GoldAPI.io Features:
- Real-time spot prices for gold, silver, platinum, palladium
- Multiple currencies (USD, EUR, GBP, etc.)
- No rate limits on free tier for real-time data
- JSON format

API Endpoint: https://www.goldapi.io/api/{symbol}/{currency}
"""

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

GOLDAPI_BASE_URL = "https://www.goldapi.io/api"

# Gold and precious metals symbols supported by GoldAPI.io
GOLD_SYMBOLS = {
    "XAU": "Gold",
    "XAG": "Silver",
    "XPT": "Platinum",
    "XPD": "Palladium",
}

# Default polling interval (seconds)
DEFAULT_INTERVAL = 60


class GoldAPICollector(BaseEventCollector):
    """GoldAPI.io collector for precious metals spot prices."""

    def __init__(
        self,
        publisher: "EventPublisher",
        api_key: Optional[str] = None,
        symbols: Optional[list[str]] = None,
        currencies: Optional[list[str]] = None,
        interval: int = DEFAULT_INTERVAL,
    ) -> None:
        super().__init__(publisher)
        self.api_key = api_key
        self.symbols = symbols or ["XAU"]
        self.currencies = currencies or ["USD", "EUR"]
        self.interval = interval
        self.client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize HTTP client with API key headers."""
        if not self.api_key:
            raise ExternalServiceError(
                "GoldAPI.io API key is required",
                service="goldapi",
            )

        self.client = httpx.AsyncClient(
            base_url=GOLDAPI_BASE_URL,
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers={
                "x-access-token": self.api_key,
                "Content-Type": "application/json",
            },
        )
        self._initialized = True
        logger.info(
            "GoldAPI collector initialized",
            symbols=self.symbols,
            currencies=self.currencies,
        )

    @circuit_breaker(failure_threshold=5, recovery_timeout=60)
    async def collect(self, symbol: Optional[str] = None) -> list[RawEvent]:
        """Collect spot price data from GoldAPI.io.

        Args:
            symbol: Specific symbol to collect (e.g., "XAU")

        Returns:
            List of RawEvent objects containing price data
        """
        if not self._initialized or not self.client:
            raise ExternalServiceError(
                "GoldAPI collector not initialized",
                service="goldapi",
            )

        symbols_to_collect = [symbol] if symbol else self.symbols
        events: list[RawEvent] = []

        for sym in symbols_to_collect:
            for currency in self.currencies:
                try:
                    event = await self._fetch_price(sym, currency)
                    if event:
                        events.append(event)
                        logger.debug(
                            "Collected price data",
                            symbol=sym,
                            currency=currency,
                        )
                except Exception as e:
                    logger.error(
                        "Failed to fetch price",
                        symbol=sym,
                        currency=currency,
                        error=str(e),
                    )

        return events

    async def _fetch_price(self, symbol: str, currency: str) -> Optional[RawEvent]:
        """Fetch spot price for a specific symbol and currency."""
        if not self.client:
            return None

        endpoint = f"/{symbol}/{currency}"

        try:
            response = await self.client.get(endpoint)
            response.raise_for_status()
            data = response.json()

            if "price" not in data:
                raise ExternalServiceError(
                    f"Invalid response from GoldAPI: {data}",
                    service="goldapi",
                )

            pair_symbol = f"{symbol}{currency}"

            price_data = {
                "symbol": symbol,
                "currency": currency,
                "pair": pair_symbol,
                "price": float(data.get("price", 0)),
                "open_price": float(data.get("open_price", 0)) if data.get("open_price") else None,
                "high_price": float(data.get("high_price", 0)) if data.get("high_price") else None,
                "low_price": float(data.get("low_price", 0)) if data.get("low_price") else None,
                "change": float(data.get("ch", 0)),
                "change_percent": float(data.get("chp", 0)),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_response": data,
            }

            event = RawEvent(
                source=DataSource.CUSTOM,
                source_id=f"goldapi_{pair_symbol}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                content=f"{GOLD_SYMBOLS.get(symbol, symbol)} price: {price_data['price']} {currency}",
                metadata={
                    "api_source": "goldapi.io",
                    "metal": symbol,
                    "currency": currency,
                    "quote_type": "spot",
                    "price_data": price_data,
                },
                collected_at=datetime.now(timezone.utc),
                symbols=[pair_symbol, symbol],
            )

            return event

        except httpx.HTTPStatusError as e:
            logger.error(
                "GoldAPI HTTP error",
                status_code=e.response.status_code,
                symbol=symbol,
                currency=currency,
            )
            raise ExternalServiceError(
                f"HTTP {e.response.status_code}",
                service="goldapi",
            ) from e

        except Exception as e:
            logger.error(
                "GoldAPI request failed",
                error=str(e),
                symbol=symbol,
                currency=currency,
            )
            raise ExternalServiceError(
                f"Request failed: {e}",
                service="goldapi",
            ) from e

    async def close(self) -> None:
        """Close the collector and cleanup resources."""
        if self.client:
            await self.client.aclose()
            self.client = None

        self._initialized = False
        logger.info("GoldAPI collector closed")
