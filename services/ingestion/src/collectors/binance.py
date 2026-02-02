"""Binance WebSocket and API collector."""

import asyncio
import json
import random
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import aiohttp
import websockets

from sentilyze_core import DataSource, RawEvent, get_logger
from sentilyze_core.exceptions import ExternalServiceError

from .base import BaseStreamCollector

if TYPE_CHECKING:
    from ..publisher import EventPublisher

logger = get_logger(__name__)

# Binance WebSocket endpoints
BINANCE_WS_BASE = "wss://stream.binance.com:9443/ws"
BINANCE_API_BASE = "https://api.binance.com"

# Default symbols to monitor
DEFAULT_SYMBOLS = ["btcusdt", "ethusdt", "bnbusdt", "solusdt", "adausdt", "xrpusdt"]

# Exponential backoff configuration
MAX_RETRIES = 5
BASE_DELAY_SECONDS = 1
MAX_DELAY_SECONDS = 60


class BinanceCollector(BaseStreamCollector):
    """Binance market data collector."""

    DEFAULT_SYMBOLS = DEFAULT_SYMBOLS

    def __init__(self, publisher: "EventPublisher") -> None:
        super().__init__(publisher)
        self.session: aiohttp.ClientSession | None = None
        self.ws_connection: websockets.WebSocketClientProtocol | None = None
        self._settings = None
        # Track failures for exponential backoff
        self._failed_tickers: dict[str, int] = {}  # symbol -> retry count
        self._last_retry_time: dict[str, datetime] = {}  # symbol -> last retry time

    async def initialize(self) -> None:
        """Initialize Binance client."""
        from sentilyze_core import get_settings
        
        settings = get_settings()
        self._settings = settings
        
        headers = {}
        if settings.binance_api_key:
            headers["X-MBX-APIKEY"] = settings.binance_api_key

        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=headers,
        )
        self._initialized = True
        logger.info("Binance collector initialized")

    async def collect(self, symbol: str | None = None) -> int:
        """Collect data from Binance.

        Args:
            symbol: Specific symbol to collect (e.g., 'BTCUSDT')

        Returns:
            Number of data points collected
        """
        if not self._initialized or not self.session:
            raise ExternalServiceError(
                "Binance collector not initialized",
                service="binance",
            )

        collected_count = 0

        try:
            count = await self._collect_ticker_data(symbol)
            collected_count += count
        except Exception as e:
            logger.error("Failed to collect ticker data", error=str(e))

        if not self._streaming:
            self._stream_task = asyncio.create_task(self._run_websocket())

        return collected_count

    def _calculate_backoff_delay(self, retry_count: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        # Exponential backoff: 2^retry * base_delay, capped at max_delay
        delay = min(BASE_DELAY_SECONDS * (2 ** retry_count), MAX_DELAY_SECONDS)
        # Add jitter (randomness) to prevent thundering herd
        jitter = random.uniform(0, delay * 0.1)
        return delay + jitter

    def _should_retry_ticker(self, symbol: str) -> bool:
        """Check if ticker should be retried based on backoff policy."""
        if symbol not in self._failed_tickers:
            return True
        
        retry_count = self._failed_tickers[symbol]
        if retry_count >= MAX_RETRIES:
            logger.warning(
                "Max retries exceeded for ticker, skipping",
                symbol=symbol,
                retries=retry_count,
            )
            return False
        
        last_retry = self._last_retry_time.get(symbol)
        if last_retry:
            elapsed = (datetime.now(timezone.utc) - last_retry).total_seconds()
            required_delay = self._calculate_backoff_delay(retry_count)
            if elapsed < required_delay:
                return False
        
        return True

    def _record_ticker_failure(self, symbol: str) -> None:
        """Record a ticker processing failure."""
        self._failed_tickers[symbol] = self._failed_tickers.get(symbol, 0) + 1
        self._last_retry_time[symbol] = datetime.now(timezone.utc)

    def _record_ticker_success(self, symbol: str) -> None:
        """Record a ticker processing success (reset failure count)."""
        if symbol in self._failed_tickers:
            del self._failed_tickers[symbol]
        if symbol in self._last_retry_time:
            del self._last_retry_time[symbol]

    async def _collect_ticker_data(self, symbol: str | None = None) -> int:
        """Collect 24hr ticker data from REST API."""
        if not self.session:
            return 0

        url = f"{BINANCE_API_BASE}/api/v3/ticker/24hr"
        params = {}
        if symbol:
            params["symbol"] = symbol.upper()

        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise ExternalServiceError(
                        f"HTTP {response.status}",
                        service="binance",
                    )

                data = await response.json()
                tickers = [data] if isinstance(data, dict) else data

                success_count = 0
                failed_symbols = []

                for ticker in tickers:
                    symbol_name = ticker.get('symbol', 'unknown')
                    
                    # Check if we should skip due to backoff
                    if not self._should_retry_ticker(symbol_name):
                        continue
                    
                    try:
                        event = self._ticker_to_event(ticker)
                        await self.publisher.publish_raw_event(event)
                        self._record_ticker_success(symbol_name)
                        success_count += 1
                    except Exception as e:
                        logger.error(
                            "Failed to process ticker",
                            symbol=symbol_name,
                            error=str(e),
                        )
                        self._record_ticker_failure(symbol_name)
                        failed_symbols.append((symbol_name, str(e)))

                # Raise if all tickers failed
                if failed_symbols and success_count == 0:
                    raise ExternalServiceError(
                        f"All {len(failed_symbols)} tickers failed to process",
                        service="binance",
                        details={"failed_symbols": [s for s, _ in failed_symbols[:5]]},
                    )
                
                if failed_symbols:
                    logger.warning(
                        "Some tickers failed to process",
                        failed_count=len(failed_symbols),
                        success_count=success_count,
                    )

                return success_count
        except ExternalServiceError:
            raise
        except Exception as e:
            raise ExternalServiceError(
                f"Failed to fetch ticker data: {e}",
                service="binance",
            ) from e

    async def start_stream(self) -> None:
        """Start WebSocket streaming."""
        if self._streaming:
            return
        self._stream_task = asyncio.create_task(self._run_websocket())

    async def stop_stream(self) -> None:
        """Stop WebSocket streaming."""
        self._streaming = False
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None

    async def _run_websocket(self) -> None:
        """Run WebSocket connection for real-time data."""
        self._streaming = True
        symbols = self.DEFAULT_SYMBOLS

        streams = [f"{s}@ticker" for s in symbols]
        ws_url = f"{BINANCE_WS_BASE}/{'/'.join(streams)}"

        while self._streaming:
            try:
                logger.info("Connecting to Binance WebSocket", url=ws_url)
                async with websockets.connect(ws_url) as ws:
                    self.ws_connection = ws
                    logger.info("Binance WebSocket connected")

                    while self._streaming:
                        try:
                            message = await asyncio.wait_for(
                                ws.recv(),
                                timeout=30,
                            )
                            await self._handle_ws_message(message)
                        except asyncio.TimeoutError:
                            await ws.ping()
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("Binance WebSocket closed")
                            break

            except Exception as e:
                logger.error("WebSocket error", error=str(e))
                await asyncio.sleep(5)

        self.ws_connection = None
        logger.info("Binance WebSocket stopped")

    async def _handle_ws_message(self, message: str) -> None:
        """Handle WebSocket message."""
        try:
            data = json.loads(message)
            event_type = data.get('e')

            if event_type == '24hrTicker':
                event = self._ws_ticker_to_event(data)
                await self.publisher.publish_raw_event(event)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse WebSocket message", error=str(e))
        except Exception as e:
            logger.error("Failed to handle WebSocket message", error=str(e))

    def _ticker_to_event(self, ticker: dict[str, Any]) -> RawEvent:
        """Convert REST API ticker to RawEvent."""
        symbol = ticker.get('symbol', '')
        base_symbol = symbol.replace('USDT', '').replace('BUSD', '')

        price_change = float(ticker.get('priceChange', 0))
        price_change_percent = float(ticker.get('priceChangePercent', 0))
        last_price = float(ticker.get('lastPrice', 0))
        volume = float(ticker.get('volume', 0))

        content = (
            f"{base_symbol} is trading at ${last_price:.2f}. "
            f"24h change: {price_change:+.2f} ({price_change_percent:+.2f}%). "
            f"Volume: {volume:.2f}"
        )

        return RawEvent(
            source=DataSource.BINANCE,
            source_id=f"binance_ticker_{symbol}_{int(datetime.now(timezone.utc).timestamp())}",
            content=content,
            metadata={
                "symbol": symbol,
                "price_change": price_change,
                "price_change_percent": price_change_percent,
                "last_price": last_price,
                "volume": volume,
                "high_price": float(ticker.get('highPrice', 0)),
                "low_price": float(ticker.get('lowPrice', 0)),
                "quote_volume": float(ticker.get('quoteVolume', 0)),
            },
            collected_at=datetime.now(timezone.utc),
            symbols=[base_symbol],
        )

    def _ws_ticker_to_event(self, data: dict[str, Any]) -> RawEvent:
        """Convert WebSocket ticker to RawEvent."""
        symbol = data.get('s', '')
        base_symbol = symbol.replace('USDT', '').replace('BUSD', '')

        price_change = float(data.get('p', 0))
        price_change_percent = float(data.get('P', 0))
        last_price = float(data.get('c', 0))
        volume = float(data.get('v', 0))

        content = (
            f"{base_symbol} is trading at ${last_price:.2f}. "
            f"24h change: {price_change:+.2f} ({price_change_percent:+.2f}%). "
            f"Volume: {volume:.2f}"
        )

        return RawEvent(
            source=DataSource.BINANCE,
            source_id=f"binance_ws_{symbol}_{data.get('E', '')}",
            content=content,
            metadata={
                "symbol": symbol,
                "price_change": price_change,
                "price_change_percent": price_change_percent,
                "last_price": last_price,
                "volume": volume,
                "high_price": float(data.get('h', 0)),
                "low_price": float(data.get('l', 0)),
                "event_time": data.get('E'),
            },
            collected_at=datetime.now(timezone.utc),
            symbols=[base_symbol],
        )

    async def close(self) -> None:
        """Close Binance client."""
        await self.stop_stream()

        if self.ws_connection:
            await self.ws_connection.close()

        if self.session:
            await self.session.close()
            self.session = None

        self._initialized = False
        logger.info("Binance collector closed")
