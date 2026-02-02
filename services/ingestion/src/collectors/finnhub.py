"""Finnhub news collector for gold and financial markets.

Finnhub provides:
- Company & market news
- Social media sentiment (Reddit/Twitter)
- 60 requests/minute on free tier (86,400/month)
- Real-time news feed

API Documentation: https://finnhub.io/docs/api
"""

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

import httpx

from sentilyze_core import DataSource, RawEvent, get_logger
from sentilyze_core.circuit_breaker import circuit_breaker
from sentilyze_core.exceptions import ExternalServiceError

from .base import BaseEventCollector

if TYPE_CHECKING:
    from ..publisher import EventPublisher

logger = get_logger(__name__)

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

# Default symbols to track for gold-related news
DEFAULT_SYMBOLS = ["GLD", "IAU", "GC=F", "XAU", "GC"]

# Keywords to filter gold-related news
GOLD_KEYWORDS = [
    "gold", "xau", "xauusd", "precious metals", "bullion",
    "federal reserve", "fed", "interest rate", "inflation", "cpi",
    "dollar index", "dxy", "treasury", "yield", "us10y",
    "geopolitical", "safe haven", "recession",
]

# Rate limiting: 60 requests per minute
REQUESTS_PER_MINUTE = 60
MIN_INTERVAL_SECONDS = 60.0 / REQUESTS_PER_MINUTE


class FinnhubNewsCollector(BaseEventCollector):
    """Finnhub news collector for gold market news and sentiment."""

    def __init__(
        self,
        publisher: "EventPublisher",
        api_key: Optional[str] = None,
        symbols: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None,
        interval_seconds: int = 300,
    ) -> None:
        super().__init__(publisher)
        self.api_key = api_key
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.keywords = [kw.lower() for kw in (keywords or GOLD_KEYWORDS)]
        self.interval_seconds = max(interval_seconds, 60)
        self.client: Optional[httpx.AsyncClient] = None
        self._last_request_time: Optional[datetime] = None

    async def initialize(self) -> None:
        """Initialize HTTP client."""
        if not self.api_key:
            raise ExternalServiceError(
                "Finnhub API key is required",
                service="finnhub",
            )

        self.client = httpx.AsyncClient(
            base_url=FINNHUB_BASE_URL,
            timeout=httpx.Timeout(15.0, connect=5.0),
            headers={
                "X-Finnhub-Token": self.api_key,
                "Content-Type": "application/json",
            },
        )
        self._initialized = True
        logger.info(
            "Finnhub news collector initialized",
            symbols=self.symbols,
            keywords_count=len(self.keywords),
        )

    async def _rate_limit(self) -> None:
        """Ensure we don't exceed rate limits."""
        if self._last_request_time:
            elapsed = (datetime.now(timezone.utc) - self._last_request_time).total_seconds()
            if elapsed < MIN_INTERVAL_SECONDS:
                sleep_time = MIN_INTERVAL_SECONDS - elapsed
                await asyncio.sleep(sleep_time)
        self._last_request_time = datetime.now(timezone.utc)

    @circuit_breaker(failure_threshold=5, recovery_timeout=60)
    async def collect(self, symbol: Optional[str] = None) -> list[RawEvent]:
        """Collect news from Finnhub.

        Args:
            symbol: Specific symbol to collect news for

        Returns:
            List of RawEvent objects containing news data
        """
        if not self._initialized or not self.client:
            raise ExternalServiceError(
                "Finnhub collector not initialized",
                service="finnhub",
            )

        symbols_to_collect = [symbol] if symbol else self.symbols
        events: list[RawEvent] = []
        seen_ids: set[str] = set()

        for sym in symbols_to_collect:
            try:
                await self._rate_limit()
                news_items = await self._fetch_news(sym)

                for item in news_items:
                    item_id = item.get("id", "")
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    if self._is_gold_related(item):
                        event = self._news_to_event(item, sym)
                        if event:
                            events.append(event)

                logger.info(
                    "Collected Finnhub news",
                    symbol=sym,
                    total_items=len(news_items),
                    gold_related=len([e for e in events if e.metadata.get("symbol_queried") == sym]),
                )

            except Exception as e:
                logger.error(
                    "Failed to fetch news",
                    symbol=sym,
                    error=str(e),
                )

        return events

    async def _fetch_news(self, symbol: str) -> list[dict]:
        """Fetch news for a specific symbol from Finnhub."""
        if not self.client:
            return []

        end_time = int(datetime.now(timezone.utc).timestamp())
        start_time = end_time - (24 * 60 * 60)

        params = {
            "symbol": symbol,
            "from": datetime.fromtimestamp(start_time, timezone.utc).strftime("%Y-%m-%d"),
            "to": datetime.fromtimestamp(end_time, timezone.utc).strftime("%Y-%m-%d"),
        }

        try:
            response = await self.client.get("/company-news", params=params)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                return data
            else:
                logger.warning("Unexpected response format from Finnhub", response=data)
                return []

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Finnhub rate limit hit (429), waiting...")
                await asyncio.sleep(5)
            raise ExternalServiceError(
                f"HTTP {e.response.status_code}",
                service="finnhub",
            ) from e

        except Exception as e:
            logger.error(
                "Finnhub request failed",
                error=str(e),
                symbol=symbol,
            )
            raise ExternalServiceError(
                f"Request failed: {e}",
                service="finnhub",
            ) from e

    def _is_gold_related(self, news_item: dict) -> bool:
        """Check if a news item is gold-related based on keywords."""
        headline = (news_item.get("headline", "") or "").lower()
        summary = (news_item.get("summary", "") or "").lower()
        source = (news_item.get("source", "") or "").lower()

        text = f"{headline} {summary} {source}"

        for keyword in self.keywords:
            if keyword in text:
                return True

        return False

    def _news_to_event(self, news_item: dict, symbol: str) -> Optional[RawEvent]:
        """Convert a Finnhub news item to RawEvent."""
        try:
            headline = news_item.get("headline", "")
            summary = news_item.get("summary", "")
            content = f"{headline}. {summary}".strip()

            if not content:
                return None

            timestamp_ms = news_item.get("datetime", 0)
            published_at = datetime.fromtimestamp(timestamp_ms, timezone.utc) if timestamp_ms else None

            source = news_item.get("source", "Finnhub")
            url = news_item.get("url", "")
            news_id = str(news_item.get("id", ""))
            source_id = f"finnhub_{news_id}" if news_id else f"finnhub_{hash(content)}"

            related_symbols = [symbol]
            if "GLD" in content.upper() or "gld" in headline.lower():
                related_symbols.extend(["GLD", "XAU"])
            if "IAU" in content.upper():
                related_symbols.append("IAU")
            if any(kw in content.lower() for kw in ["gold", "xau"]):
                related_symbols.append("XAUUSD")

            seen = set()
            unique_symbols = [s for s in related_symbols if not (s in seen or seen.add(s))]

            return RawEvent(
                source=DataSource.FINNHUB,
                source_id=source_id,
                content=content,
                metadata={
                    "api_source": "finnhub",
                    "symbol_queried": symbol,
                    "news_source": source,
                    "headline": headline,
                    "summary": summary,
                    "url": url,
                    "news_id": news_id,
                    "is_gold_related": True,
                },
                collected_at=datetime.now(timezone.utc),
                title=headline or None,
                url=url or None,
                published_at=published_at,
                symbols=unique_symbols,
            )

        except Exception as e:
            logger.error(
                "Failed to convert news to event",
                error=str(e),
                news_id=news_item.get("id"),
            )
            return None

    async def close(self) -> None:
        """Close the collector and cleanup resources."""
        if self.client:
            await self.client.aclose()
            self.client = None

        self._initialized = False
        logger.info("Finnhub news collector closed")
