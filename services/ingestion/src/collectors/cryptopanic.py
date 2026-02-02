"""CryptoPanic API collector for crypto news and sentiment.

CryptoPanic provides:
- Real-time crypto news aggregation
- Social signals (Reddit, Twitter)
- Portfolio tracking
- Developer-friendly JSON API

API Documentation: https://cryptopanic.com/developers/api/
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

CRYPTOPANIC_BASE_URL = "https://cryptopanic.com/api/v1"

# Default currencies to track
DEFAULT_CURRENCIES = ["BTC", "ETH", "BNB", "SOL", "ADA", "XRP", "DOT", "DOGE"]

# Rate limiting: API dependent on plan
REQUESTS_PER_MINUTE = 60
MIN_INTERVAL_SECONDS = 60.0 / REQUESTS_PER_MINUTE

# Filter types for news
FILTER_TYPES = ["rising", "hot", "bullish", "bearish", "important", "saved", "lol"]


class CryptoPanicCollector(BaseEventCollector):
    """CryptoPanic API collector for crypto news and social signals."""

    def __init__(
        self,
        publisher: "EventPublisher",
        api_key: Optional[str] = None,
        currencies: Optional[list[str]] = None,
        filter_type: Optional[str] = None,
    ) -> None:
        super().__init__(publisher)
        self.api_key = api_key
        self.currencies = currencies or DEFAULT_CURRENCIES
        self.filter_type = filter_type  # rising, hot, bullish, bearish, etc.
        self._session: Optional[httpx.AsyncClient] = None
        self._last_request_time: Optional[datetime] = None
        self._settings = None

    async def initialize(self) -> None:
        """Initialize CryptoPanic client."""
        from sentilyze_core import get_settings

        self._settings = get_settings()
        
        # Get API key from settings if not provided
        if not self.api_key:
            self.api_key = getattr(self._settings, 'cryptopanic_api_key', None)
            
        if not self.api_key:
            logger.warning("CryptoPanic API key not configured")
            raise ExternalServiceError(
                "CryptoPanic API key required",
                service="cryptopanic",
            )

        # Initialize HTTP client
        self._session = httpx.AsyncClient(
            base_url=CRYPTOPANIC_BASE_URL,
            headers={
                "Accept": "application/json",
            },
            timeout=30.0,
        )

        self._initialized = True
        logger.info(
            "CryptoPanic collector initialized",
            currencies=self.currencies,
            filter_type=self.filter_type,
        )

    async def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        if self._last_request_time:
            elapsed = (datetime.now(timezone.utc) - self._last_request_time).total_seconds()
            if elapsed < MIN_INTERVAL_SECONDS:
                await asyncio.sleep(MIN_INTERVAL_SECONDS - elapsed)
        self._last_request_time = datetime.now(timezone.utc)

    @circuit_breaker(failure_threshold=5, recovery_timeout=60)
    async def _make_request(self, endpoint: str, params: Optional[dict] = None) -> dict[str, Any]:
        """Make rate-limited API request."""
        await self._rate_limit()

        try:
            response = await self._session.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "CryptoPanic API HTTP error",
                status_code=e.response.status_code,
                endpoint=endpoint,
            )
            raise ExternalServiceError(
                f"CryptoPanic API error: {e.response.status_code}",
                service="cryptopanic",
            )
        except httpx.RequestError as e:
            logger.error(
                "CryptoPanic API request failed",
                error=str(e),
                endpoint=endpoint,
            )
            raise ExternalServiceError(
                f"CryptoPanic request failed: {e}",
                service="cryptopanic",
            )

    async def _fetch_news(self, currency: Optional[str] = None) -> list[dict[str, Any]]:
        """Fetch news from CryptoPanic."""
        try:
            params = {
                "auth_token": self.api_key,
                "public": "true",
            }
            
            if currency:
                params["currencies"] = currency
            
            if self.filter_type and self.filter_type in FILTER_TYPES:
                params["filter"] = self.filter_type

            data = await self._make_request("/posts/", params=params)
            
            if not data or "results" not in data:
                logger.warning("No data returned from CryptoPanic", currency=currency)
                return []
                
            return data["results"]
        except Exception as e:
            logger.error("Failed to fetch news", currency=currency, error=str(e))
            return []

    def _transform_to_event(self, post: dict[str, Any]) -> RawEvent:
        """Transform CryptoPanic post to RawEvent."""
        # Extract currencies from the post
        currencies = [c["code"] for c in post.get("currencies", [])]
        primary_currency = currencies[0] if currencies else "UNKNOWN"
        
        # Extract sentiment from votes
        votes = post.get("votes", {})
        bullish_votes = votes.get("positive", 0)
        bearish_votes = votes.get("negative", 0)
        total_votes = bullish_votes + bearish_votes
        
        sentiment_score = 0.0
        if total_votes > 0:
            sentiment_score = (bullish_votes - bearish_votes) / total_votes
        
        # Parse published_at timestamp
        published_at = post.get("published_at", "")
        try:
            timestamp = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            timestamp = datetime.now(timezone.utc)
        
        return RawEvent(
            source=DataSource.CRYPTOPANIC,
            event_type="news",
            symbol=primary_currency,
            timestamp=timestamp,
            payload={
                "title": post.get("title", ""),
                "url": post.get("url", ""),
                "source_domain": post.get("domain", ""),
                "sentiment_score": sentiment_score,
                "bullish_votes": bullish_votes,
                "bearish_votes": bearish_votes,
                "total_votes": total_votes,
                "currencies": currencies,
            },
            metadata={
                "collector": "cryptopanic",
                "post_id": post.get("id"),
                "slug": post.get("slug"),
            }
        )

    async def collect(self, **kwargs: Any) -> int:
        """Collect news from CryptoPanic.
        
        Args:
            **kwargs: Optional 'currencies' to override default currencies
            
        Returns:
            Number of events collected
        """
        if not self._initialized:
            raise RuntimeError("Collector not initialized")

        currencies = kwargs.get("currencies", self.currencies)
        events: list[RawEvent] = []

        logger.info("Starting CryptoPanic collection", currencies=currencies)

        # Fetch news for all currencies or general news
        if currencies:
            for currency in currencies:
                try:
                    posts = await self._fetch_news(currency)
                    for post in posts:
                        event = self._transform_to_event(post)
                        events.append(event)
                    logger.debug("Collected CryptoPanic news", currency=currency, count=len(posts))
                except Exception as e:
                    logger.error("Failed to collect news", currency=currency, error=str(e))
                    continue
        else:
            # Fetch general news
            try:
                posts = await self._fetch_news()
                for post in posts:
                    event = self._transform_to_event(post)
                    events.append(event)
                logger.debug("Collected CryptoPanic general news", count=len(posts))
            except Exception as e:
                logger.error("Failed to collect general news", error=str(e))

        # Publish events
        if events:
            try:
                message_ids = await self.publish_events(events)
                logger.info(
                    "Published CryptoPanic events",
                    count=len(message_ids),
                    currencies=list(set(e.symbol for e in events)),
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
        logger.info("CryptoPanic collector closed")
