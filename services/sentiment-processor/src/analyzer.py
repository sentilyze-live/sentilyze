"""Unified sentiment analyzer with market-specific routing.

This module provides the main entry point for sentiment analysis,
routing to market-specific analyzers based on content type.
"""

import asyncio
from typing import Any
from uuid import UUID

from sentilyze_core import (
    CacheClient,
    ProcessedEvent,
    RawEvent,
    SentimentLabel,
    SentimentResult,
    get_logger,
    get_settings,
)
from sentilyze_core.exceptions import ExternalServiceError, RateLimitError

from .config import MarketType, is_market_enabled
from .analyzer_crypto import CryptoSentimentAnalyzer
from .analyzer_gold import GoldSentimentAnalyzer
from .cache import SentimentCache

logger = get_logger(__name__)
settings = get_settings()


class UnifiedSentimentAnalyzer:
    """Unified sentiment analyzer with market-specific routing.
    
    This analyzer routes content to the appropriate market-specific
    analyzer (crypto or gold) based on content analysis and feature flags.
    """

    def __init__(self) -> None:
        self._initialized = False
        self.cache = SentimentCache()
        self._crypto_analyzer: CryptoSentimentAnalyzer | None = None
        self._gold_analyzer: GoldSentimentAnalyzer | None = None
        self._generic_analyzer: CryptoSentimentAnalyzer | None = None

    async def initialize(self) -> None:
        """Initialize all market-specific analyzers."""
        try:
            # Initialize crypto analyzer (also serves as generic fallback)
            if settings.enable_crypto_analysis:
                self._crypto_analyzer = CryptoSentimentAnalyzer()
                await self._crypto_analyzer.initialize()
                logger.info("Crypto sentiment analyzer initialized")

            # Initialize gold analyzer
            if settings.enable_gold_analysis:
                self._gold_analyzer = GoldSentimentAnalyzer()
                await self._gold_analyzer.initialize()
                logger.info("Gold sentiment analyzer initialized")

            # Use crypto analyzer as generic fallback if enabled
            if settings.enable_crypto_analysis:
                self._generic_analyzer = self._crypto_analyzer
            elif settings.enable_gold_analysis:
                self._generic_analyzer = self._gold_analyzer

            self._initialized = True
            logger.info("Unified sentiment analyzer initialized")
        except Exception as e:
            raise ExternalServiceError(
                f"Failed to initialize sentiment analyzer: {e}",
                service="sentiment_analyzer",
            )

    async def analyze(
        self,
        event: RawEvent,
        market_type: MarketType = MarketType.CRYPTO,
        prediction_id: UUID | None = None,
    ) -> ProcessedEvent:
        """Analyze sentiment with market-specific routing.
        
        Args:
            event: Raw event to analyze
            market_type: Target market type for specialized analysis
            prediction_id: Unique prediction identifier
            
        Returns:
            Processed event with sentiment results
        """
        if not self._initialized:
            raise RuntimeError("Analyzer not initialized")

        # Check cache first
        cache_key = self.cache.get_cache_key(event.content, market_type)
        cached_result = await self.cache.get_cached_result(cache_key)

        if cached_result:
            logger.debug("Using cached sentiment result", 
                        event_id=str(event.event_id),
                        market_type=market_type.value)
            sentiment = SentimentResult(**cached_result)
            return self._create_processed_event(event, sentiment, prediction_id)

        # Route to appropriate analyzer
        analyzer = self._get_analyzer_for_market(market_type)
        
        if analyzer is None:
            logger.warning(
                f"No analyzer available for {market_type.value}, using generic fallback"
            )
            analyzer = self._generic_analyzer

        if analyzer is None:
            raise ExternalServiceError(
                f"No analyzer available for market type: {market_type.value}",
                service="sentiment_analyzer",
            )

        # Perform analysis
        try:
            processed = await analyzer.analyze(event, prediction_id=prediction_id)
            
            # Cache the result
            await self.cache.cache_result(cache_key, processed.sentiment)
            
            return processed
        except Exception as e:
            logger.error(
                f"Market-specific analysis failed for {market_type.value}",
                error=str(e),
                event_id=str(event.event_id),
            )
            raise

    def _get_analyzer_for_market(
        self,
        market_type: MarketType,
    ) -> CryptoSentimentAnalyzer | GoldSentimentAnalyzer | None:
        """Get the appropriate analyzer for the market type."""
        if market_type == MarketType.CRYPTO and settings.enable_crypto_analysis:
            return self._crypto_analyzer
        elif market_type == MarketType.GOLD and settings.enable_gold_analysis:
            return self._gold_analyzer
        # Fallback for any other market types (FOREX, STOCKS, etc.)
        return self._generic_analyzer

    def _create_processed_event(
        self,
        event: RawEvent,
        sentiment: SentimentResult,
        prediction_id: UUID | None = None,
    ) -> ProcessedEvent:
        """Create a processed event from cached sentiment."""
        return ProcessedEvent(
            prediction_id=prediction_id or event.event_id,
            event_id=event.event_id,
            source=event.source,
            content=event.content,
            sentiment=sentiment,
            entities=[],
            symbols=event.symbols,
            keywords=[],
            processed_at=__import__('datetime').datetime.utcnow(),
            tenant_id=event.tenant_id,
        )

    async def close(self) -> None:
        """Close all analyzer resources."""
        if self._crypto_analyzer:
            await self._crypto_analyzer.close()
        if self._gold_analyzer:
            await self._gold_analyzer.close()
        await self.cache.close()
        self._initialized = False
        logger.info("Unified sentiment analyzer closed")
