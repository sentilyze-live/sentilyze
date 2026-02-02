"""RSS feed collector."""

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from xml.etree.ElementTree import ParseError

import aiohttp
import feedparser

from sentilyze_core import DataSource, RawEvent, get_logger
from sentilyze_core.exceptions import ExternalServiceError

from .base import BaseCollector

if TYPE_CHECKING:
    from ..publisher import EventPublisher

logger = get_logger(__name__)

# Default crypto news feeds
DEFAULT_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptonews.com/news/feed",
    "https://decrypt.co/feed",
    "https://bitcoinmagazine.com/feed",
]

# Crypto symbols to track
CRYPTO_SYMBOLS = [
    "BTC", "ETH", "BNB", "SOL", "ADA", "XRP", "DOT", "DOGE",
    "AVAX", "MATIC", "LINK", "UNI", "LTC", "ATOM", "ETC",
    "BITCOIN", "ETHEREUM", "BINANCE", "SOLANA", "CARDANO",
    "RIPPLE", "POLKADOT", "DOGECOIN", "AVALANCHE", "POLYGON",
]


class RSSCollector(BaseCollector):
    """RSS feed collector."""

    DEFAULT_FEEDS = DEFAULT_FEEDS
    CRYPTO_SYMBOLS = CRYPTO_SYMBOLS

    def __init__(self, publisher: "EventPublisher") -> None:
        super().__init__(publisher)
        self.session: aiohttp.ClientSession | None = None

    async def initialize(self) -> None:
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "User-Agent": "Sentilyze/4.0 Unified Ingestion Service",
            },
        )
        self._initialized = True
        logger.info("RSS collector initialized")

    async def collect(self, feed_url: str | None = None) -> int:
        """Collect entries from RSS feeds.

        Args:
            feed_url: Specific feed URL to collect from

        Returns:
            Number of entries collected
        """
        if not self._initialized or not self.session:
            raise ExternalServiceError(
                "RSS collector not initialized",
                service="rss",
            )

        feeds = [feed_url] if feed_url else self.DEFAULT_FEEDS
        collected_count = 0

        for url in feeds:
            try:
                count = await self._collect_from_feed(url)
                collected_count += count
                logger.info(
                    "Collected from RSS feed",
                    feed=url,
                    count=count,
                )
            except Exception as e:
                logger.error(
                    "Failed to collect from RSS feed",
                    feed=url,
                    error=str(e),
                )
                continue

        return collected_count

    async def _collect_from_feed(self, feed_url: str) -> int:
        """Collect entries from a specific RSS feed."""
        if not self.session:
            return 0

        try:
            async with self.session.get(feed_url) as response:
                if response.status != 200:
                    raise ExternalServiceError(
                        f"HTTP {response.status}",
                        service="rss",
                    )
                content = await response.text()
        except Exception as e:
            raise ExternalServiceError(
                f"Failed to fetch feed: {e}",
                service="rss",
            ) from e

        try:
            feed = feedparser.parse(content)
        except ParseError as e:
            raise ExternalServiceError(
                f"Failed to parse feed: {e}",
                service="rss",
            ) from e

        if feed.bozo:
            logger.warning(
                "Feed parsing warning",
                feed=feed_url,
                error=feed.bozo_exception,
            )

        count = 0
        for entry in feed.entries:
            try:
                event = self._entry_to_event(entry, feed_url)
                await self.publisher.publish_raw_event(event)
                count += 1
            except Exception as e:
                logger.error(
                    "Failed to process entry",
                    entry_id=getattr(entry, 'id', 'unknown'),
                    error=str(e),
                )
                continue

        return count

    def _entry_to_event(self, entry: Any, feed_url: str) -> RawEvent:
        """Convert RSS entry to RawEvent."""
        title = getattr(entry, 'title', '')
        summary = getattr(entry, 'summary', '')
        content_text = getattr(entry, 'content', [{}])[0].get('value', '') if hasattr(entry, 'content') else ''
        text = f"{title} {summary} {content_text}".strip()

        symbols = self._extract_symbols(text)

        published_at = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            published_at = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

        entry_id = getattr(entry, 'id', '') or getattr(entry, 'link', '') or str(hash(text))

        return RawEvent(
            source=DataSource.RSS,
            source_id=f"rss_{entry_id}",
            content=text,
            metadata={
                "feed_url": feed_url,
                "feed_title": getattr(entry, 'source', {}).get('title', '') if hasattr(entry, 'source') else '',
                "tags": getattr(entry, 'tags', []),
            },
            collected_at=datetime.now(timezone.utc),
            author=getattr(entry, 'author', None),
            url=getattr(entry, 'link', None),
            title=title or None,
            published_at=published_at,
            symbols=symbols,
        )

    def _extract_symbols(self, text: str) -> list[str]:
        """Extract crypto symbols from text."""
        found_symbols = []
        text_upper = text.upper()

        for symbol in self.CRYPTO_SYMBOLS:
            pattern = rf'\b{re.escape(symbol)}\b'
            if re.search(pattern, text_upper):
                ticker = symbol[:3] if len(symbol) > 3 and symbol not in self.CRYPTO_SYMBOLS[:15] else symbol
                if ticker not in found_symbols:
                    found_symbols.append(ticker)

        return found_symbols

    async def close(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            self._initialized = False
            logger.info("RSS collector closed")
