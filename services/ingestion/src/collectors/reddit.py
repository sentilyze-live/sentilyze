"""Reddit data collector using PRAW."""

import asyncio
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import praw
from praw.models import Submission

from sentilyze_core import DataSource, RawEvent, get_logger
from sentilyze_core.exceptions import ExternalServiceError

from .base import BaseCollector

if TYPE_CHECKING:
    from ..publisher import EventPublisher

logger = get_logger(__name__)

# Default crypto-related subreddits
DEFAULT_SUBREDDITS = [
    "Bitcoin",
    "ethereum",
    "CryptoCurrency",
    "CryptoMarkets",
    "BitcoinMarkets",
    "altcoin",
    "defi",
    "NFTs",
]

# Crypto symbols to track
CRYPTO_SYMBOLS = [
    "BTC", "ETH", "BNB", "SOL", "ADA", "XRP", "DOT", "DOGE",
    "AVAX", "MATIC", "LINK", "UNI", "LTC", "ATOM", "ETC",
]


class RedditCollector(BaseCollector):
    """Reddit data collector."""

    DEFAULT_SUBREDDITS = DEFAULT_SUBREDDITS
    CRYPTO_SYMBOLS = CRYPTO_SYMBOLS

    def __init__(self, publisher: "EventPublisher") -> None:
        super().__init__(publisher)
        self.reddit: praw.Reddit | None = None
        self._settings = None

    async def initialize(self) -> None:
        """Initialize Reddit client."""
        from sentilyze_core import get_settings
        
        settings = get_settings()
        self._settings = settings
        
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            raise ExternalServiceError(
                "Reddit credentials not configured",
                service="reddit",
            )

        try:
            loop = asyncio.get_event_loop()
            self.reddit = await loop.run_in_executor(
                None,
                lambda: praw.Reddit(
                    client_id=settings.reddit_client_id,
                    client_secret=settings.reddit_client_secret,
                    user_agent=settings.reddit_user_agent,
                ),
            )

            await loop.run_in_executor(None, lambda: self.reddit.user.me())
            self._initialized = True
            logger.info("Reddit client initialized")
        except Exception as e:
            raise ExternalServiceError(
                f"Failed to initialize Reddit client: {e}",
                service="reddit",
            ) from e

    async def collect(self, subreddit: str | None = None, limit: int = 100) -> int:
        """Collect posts from Reddit.

        Args:
            subreddit: Specific subreddit to collect from
            limit: Maximum number of posts to collect

        Returns:
            Number of posts collected
        """
        if not self._initialized or not self.reddit:
            raise ExternalServiceError(
                "Reddit collector not initialized",
                service="reddit",
            )

        subreddits = [subreddit] if subreddit else self.DEFAULT_SUBREDDITS
        collected_count = 0

        for sub_name in subreddits:
            try:
                count = await self._collect_from_subreddit(sub_name, limit)
                collected_count += count
                logger.info(
                    "Collected from subreddit",
                    subreddit=sub_name,
                    count=count,
                )
            except Exception as e:
                logger.error(
                    "Failed to collect from subreddit",
                    subreddit=sub_name,
                    error=str(e),
                )
                continue

        return collected_count

    async def _collect_from_subreddit(
        self,
        subreddit_name: str,
        limit: int,
    ) -> int:
        """Collect posts from a specific subreddit."""
        if not self.reddit:
            return 0

        loop = asyncio.get_event_loop()
        count = 0

        try:
            subreddit = await loop.run_in_executor(
                None,
                lambda: self.reddit.subreddit(subreddit_name),
            )

            posts = await loop.run_in_executor(
                None,
                lambda: list(subreddit.hot(limit=limit)),
            )

            for post in posts:
                try:
                    event = self._post_to_event(post, subreddit_name)
                    await self.publisher.publish_raw_event(event)
                    count += 1
                except Exception as e:
                    logger.error(
                        "Failed to process post",
                        post_id=post.id,
                        error=str(e),
                    )
                    continue

        except Exception as e:
            logger.error(
                "Failed to fetch subreddit",
                subreddit=subreddit_name,
                error=str(e),
            )

        return count

    def _post_to_event(self, post: Submission, subreddit: str) -> RawEvent:
        """Convert Reddit post to RawEvent."""
        text = f"{post.title} {post.selftext or ''}"
        symbols = self._extract_symbols(text)
        created_at = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)

        return RawEvent(
            source=DataSource.REDDIT,
            source_id=f"reddit_{post.id}",
            content=text,
            metadata={
                "subreddit": subreddit,
                "post_id": post.id,
                "score": post.score,
                "upvote_ratio": post.upvote_ratio,
                "num_comments": post.num_comments,
                "awards": post.total_awards_received,
            },
            collected_at=datetime.now(timezone.utc),
            author=post.author.name if post.author else None,
            url=f"https://reddit.com{post.permalink}",
            title=post.title,
            published_at=created_at,
            symbols=symbols,
        )

    def _extract_symbols(self, text: str) -> list[str]:
        """Extract crypto symbols from text."""
        found_symbols = []
        text_upper = text.upper()

        for symbol in self.CRYPTO_SYMBOLS:
            pattern = rf'\b{re.escape(symbol)}\b'
            if re.search(pattern, text_upper):
                found_symbols.append(symbol)

        return found_symbols

    async def close(self) -> None:
        """Close Reddit client."""
        if self.reddit:
            self.reddit = None
            self._initialized = False
            logger.info("Reddit client closed")
