"""yfinance collector for market data (VIX, S&P 500, Gold Futures, Oil, etc.).

yfinance Features:
- No rate limits
- Real-time and historical data
- Intraday and daily timeframes
- Comprehensive market coverage (stocks, indices, futures, forex)
- Free and reliable

Collected Data:
- ^VIX: CBOE Volatility Index (fear gauge)
- ^GSPC: S&P 500 Index (market sentiment)
- GC=F: Gold Futures (COMEX)
- DX-Y.NYB: USD Index (alternative to FRED)
- CL=F: WTI Crude Oil Futures
- SI=F: Silver Futures
"""

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

import yfinance as yf

from sentilyze_core import DataSource, RawEvent, get_logger
from sentilyze_core.circuit_breaker import circuit_breaker
from sentilyze_core.exceptions import ExternalServiceError

from .base import BaseEventCollector

if TYPE_CHECKING:
    from ..publisher import EventPublisher

logger = get_logger(__name__)

# Default symbols to track
DEFAULT_SYMBOLS = {
    "^VIX": {
        "name": "CBOE Volatility Index",
        "category": "volatility",
        "description": "Market fear gauge - high VIX correlates with gold rallies",
    },
    "^GSPC": {
        "name": "S&P 500 Index",
        "category": "equity_index",
        "description": "Risk-on/risk-off indicator - inverse correlation with gold",
    },
    "GC=F": {
        "name": "Gold Futures",
        "category": "commodity",
        "description": "COMEX gold futures (primary gold pricing reference)",
    },
    "DX-Y.NYB": {
        "name": "US Dollar Index",
        "category": "currency_index",
        "description": "Measures USD strength - inverse correlation with gold",
    },
    "CL=F": {
        "name": "WTI Crude Oil Futures",
        "category": "commodity",
        "description": "Energy prices - inflation indicator affecting gold",
    },
    "SI=F": {
        "name": "Silver Futures",
        "category": "commodity",
        "description": "Precious metal correlated with gold (gold/silver ratio)",
    },
    "^TNX": {
        "name": "10-Year Treasury Yield",
        "category": "interest_rate",
        "description": "Bond yields - inverse correlation with gold",
    },
}

# Default interval for data collection (1 hour)
DEFAULT_INTERVAL = 3600  # seconds


class YFinanceCollector(BaseEventCollector):
    """yfinance collector for market data."""

    def __init__(
        self,
        publisher: "EventPublisher",
        symbols: Optional[dict[str, dict[str, str]]] = None,
        interval: int = DEFAULT_INTERVAL,
        period: str = "1d",
        data_interval: str = "1h",
    ) -> None:
        """Initialize yfinance collector.

        Args:
            publisher: Event publisher instance
            symbols: Dictionary of symbols to track with metadata
            interval: Collection interval in seconds (default: 3600 = 1 hour)
            period: Data period to fetch (default: "1d" = 1 day)
            data_interval: Data granularity (default: "1h" = 1 hour candles)
        """
        super().__init__(publisher)
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.interval = interval
        self.period = period
        self.data_interval = data_interval
        self._settings = None

    async def initialize(self) -> None:
        """Initialize yfinance collector."""
        from sentilyze_core import get_settings

        self._settings = get_settings()
        self._initialized = True
        logger.info(
            "yfinance collector initialized",
            symbols=list(self.symbols.keys()),
            interval=self.interval,
        )

    @circuit_breaker(failure_threshold=5, recovery_timeout=60)
    async def _fetch_symbol_data(self, symbol: str) -> Optional[dict[str, Any]]:
        """Fetch data for a single symbol.

        Args:
            symbol: Yahoo Finance symbol (e.g., "^VIX", "GC=F")

        Returns:
            Dictionary containing symbol data or None if fetch fails
        """
        try:
            # Run yfinance download in executor to avoid blocking
            loop = asyncio.get_event_loop()
            ticker_data = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    symbol,
                    period=self.period,
                    interval=self.data_interval,
                    progress=False,
                    show_errors=False,
                ),
            )

            if ticker_data.empty:
                logger.warning("No data returned from yfinance", symbol=symbol)
                return None

            # Get latest data point
            latest = ticker_data.iloc[-1]
            timestamp = ticker_data.index[-1]

            # Get ticker info for additional metadata
            ticker = yf.Ticker(symbol)
            info = await loop.run_in_executor(None, lambda: ticker.info)

            # Extract relevant fields
            data = {
                "symbol": symbol,
                "timestamp": timestamp.to_pydatetime().replace(tzinfo=timezone.utc),
                "open": float(latest["Open"]) if not latest["Open"] is None else None,
                "high": float(latest["High"]) if not latest["High"] is None else None,
                "low": float(latest["Low"]) if not latest["Low"] is None else None,
                "close": float(latest["Close"]) if not latest["Close"] is None else None,
                "volume": int(latest["Volume"]) if not latest["Volume"] is None else None,
                "change": None,
                "change_percent": None,
            }

            # Calculate change if we have enough data
            if len(ticker_data) >= 2:
                prev_close = float(ticker_data.iloc[-2]["Close"])
                current_close = data["close"]
                if prev_close and current_close:
                    data["change"] = current_close - prev_close
                    data["change_percent"] = (data["change"] / prev_close) * 100

            # Add metadata from ticker info
            data["metadata"] = {
                "long_name": info.get("longName"),
                "short_name": info.get("shortName"),
                "currency": info.get("currency"),
                "exchange": info.get("exchange"),
                "market_cap": info.get("marketCap"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
            }

            return data

        except Exception as e:
            logger.error(
                "Failed to fetch symbol data",
                symbol=symbol,
                error=str(e),
            )
            return None

    def _transform_to_event(
        self, symbol: str, data: dict[str, Any], symbol_meta: dict[str, str]
    ) -> RawEvent:
        """Transform yfinance data to RawEvent.

        Args:
            symbol: Yahoo Finance symbol
            data: Symbol data dictionary
            symbol_meta: Symbol metadata (name, category, description)

        Returns:
            RawEvent object
        """
        timestamp = data["timestamp"]
        close_price = data["close"]
        change_percent = data.get("change_percent", 0)

        # Create content string
        content = f"{symbol_meta['name']}: {close_price:.2f}"
        if change_percent is not None:
            direction = "up" if change_percent > 0 else "down"
            content += f" ({direction} {abs(change_percent):.2f}%)"

        # Determine event type based on category
        event_type_map = {
            "volatility": "volatility_index",
            "equity_index": "equity_index",
            "commodity": "commodity_price",
            "currency_index": "currency_index",
            "interest_rate": "interest_rate",
        }
        event_type = event_type_map.get(symbol_meta["category"], "market_data")

        # Create payload
        payload = {
            "symbol": symbol,
            "name": symbol_meta["name"],
            "category": symbol_meta["category"],
            "description": symbol_meta["description"],
            "price": close_price,
            "open": data["open"],
            "high": data["high"],
            "low": data["low"],
            "volume": data["volume"],
            "change": data["change"],
            "change_percent": data["change_percent"],
            "data_source": "yfinance",
            "market_metadata": data.get("metadata", {}),
        }

        # Determine symbols list for categorization
        symbols = [symbol]
        if "gold" in symbol_meta["name"].lower() or symbol in ["GC=F"]:
            symbols.append("XAU")
        elif "silver" in symbol_meta["name"].lower() or symbol in ["SI=F"]:
            symbols.append("XAG")
        elif "oil" in symbol_meta["name"].lower() or symbol in ["CL=F"]:
            symbols.append("OIL")

        return RawEvent(
            source=DataSource.CUSTOM,
            event_type=event_type,
            symbol=symbol,
            timestamp=timestamp,
            payload=payload,
            metadata={
                "collector": "yfinance",
                "source": "Yahoo Finance",
                "interval": self.data_interval,
                "period": self.period,
            },
        )

    async def collect(self, symbol: Optional[str] = None, **kwargs: Any) -> int:
        """Collect market data from yfinance.

        Args:
            symbol: Specific symbol to collect (optional, collects all if None)
            **kwargs: Additional collection parameters

        Returns:
            Number of events collected
        """
        if not self._initialized:
            raise RuntimeError("Collector not initialized")

        symbols_to_collect = {symbol: self.symbols[symbol]} if symbol and symbol in self.symbols else self.symbols
        events: list[RawEvent] = []

        logger.info("Starting yfinance collection", symbols=list(symbols_to_collect.keys()))

        # Collect data for all symbols in parallel
        tasks = []
        for sym in symbols_to_collect.keys():
            tasks.append(self._fetch_symbol_data(sym))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Transform results to events
        for sym, result in zip(symbols_to_collect.keys(), results):
            if isinstance(result, Exception):
                logger.error("Failed to collect symbol", symbol=sym, error=str(result))
                continue

            if result is None:
                continue

            try:
                event = self._transform_to_event(sym, result, symbols_to_collect[sym])
                events.append(event)
                logger.debug(
                    "Collected market data",
                    symbol=sym,
                    price=result["close"],
                    change_percent=result.get("change_percent"),
                )
            except Exception as e:
                logger.error("Failed to transform event", symbol=sym, error=str(e))
                continue

        # Publish events
        if events:
            try:
                message_ids = await self.publish_events(events)
                logger.info(
                    "Published yfinance events",
                    count=len(message_ids),
                    symbols=[e.symbol for e in events],
                )
                return len(events)
            except Exception as e:
                logger.error("Failed to publish events", error=str(e))
                return 0

        return 0

    async def close(self) -> None:
        """Close the collector and cleanup resources."""
        self._initialized = False
        logger.info("yfinance collector closed")
