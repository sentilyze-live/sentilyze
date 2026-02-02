"""Crypto-specific sentiment analyzer using Vertex AI Gemini.

This module provides the CryptoSentimentAnalyzer class that extends
BaseSentimentAnalyzer with crypto market-specific prompts and entity extraction.
"""

from typing import Any
from uuid import UUID

from sentilyze_core import (
    ProcessedEvent,
    RawEvent,
    SentimentResult,
    get_logger,
)

from .analyzer_base import BaseSentimentAnalyzer

logger = get_logger(__name__)

# Default crypto prompt template
DEFAULT_CRYPTO_PROMPT_TEMPLATE = """Analyze the sentiment of the following text related to cryptocurrency markets.

Text: {text}

Provide a sentiment analysis with the following JSON structure:
{{
    "score": <float between -1 and 1, where -1 is very negative, 0 is neutral, 1 is very positive>,
    "label": <one of: "very_positive", "positive", "neutral", "negative", "very_negative">,
    "confidence": <float between 0 and 1>,
    "explanation": <brief explanation of the sentiment>,
    "entities": [<list of crypto entities mentioned: BTC, ETH, etc.>],
    "key_factors": [<list of key factors: "technology", "adoption", "regulation", "market_sentiment", "price_action">]
}}

Consider:
- Market sentiment indicators (bullish/bearish)
- Price predictions or expectations
- Technology developments and adoption
- Regulatory news and compliance
- General crypto market sentiment

Respond ONLY with the JSON object, no other text."""

# Crypto entity patterns
CRYPTO_ENTITIES = {
    "BTC", "ETH", "XRP", "SOL", "ADA", "DOT", "AVAX", "MATIC", "LINK", "UNI",
    "AAVE", "COMP", "MKR", "SNX", "YFI", "CRV", "SUSHI", "1INCH", "BAL", "LRC",
    "bitcoin", "ethereum", "ripple", "solana", "cardano", "polkadot", "avalanche",
    "polygon", "chainlink", "uniswap", "aave", "compound", "maker", "synthetix",
    "yearn", "curve", "sushi", "1inch", "balancer", "loopring",
}

CRYPTO_KEYWORDS = [
    "crypto", "cryptocurrency", "bitcoin", "ethereum", "btc", "eth",
    "blockchain", "defi", "nft", "altcoin", "token", "wallet",
    "mining", "staking", "yield", "liquidity", "dex", "cex",
    "bullish", "bearish", "pump", "dump", "hodl", "fomo", "fud",
]


class CryptoSentimentAnalyzer(BaseSentimentAnalyzer):
    """Crypto market-specific sentiment analyzer using Vertex AI Gemini.
    
    Extends BaseSentimentAnalyzer with crypto-specific:
    - Prompt templates
    - Entity extraction (BTC, ETH, etc.)
    - Content relevance filtering
    """

    def __init__(self, prompt_template: str | None = None) -> None:
        super().__init__(prompt_template)
        self._market_type = "crypto"

    @property
    def _prompt_file_name(self) -> str:
        return "crypto_v1.txt"

    @property
    def _cache_namespace(self) -> str:
        return "crypto_sentiment"

    def _get_default_prompt_template(self) -> str:
        return DEFAULT_CRYPTO_PROMPT_TEMPLATE

    def _is_content_relevant(self, content: str | None) -> bool:
        """Check if content is crypto-related."""
        if not content:
            return True  # Process all content by default for crypto (generic fallback)
        
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in CRYPTO_KEYWORDS)

    def _extract_entities(self, text: str) -> list[str]:
        """Extract crypto entities from text."""
        if not text:
            return []
        
        text_upper = text.upper()
        found_entities = []
        
        for entity in CRYPTO_ENTITIES:
            if entity.upper() in text_upper:
                found_entities.append(entity)
        
        return found_entities

    async def _post_process_result(
        self, 
        event: RawEvent, 
        sentiment: SentimentResult
    ) -> ProcessedEvent:
        """Create processed event with crypto-specific entity extraction."""
        entities = self._extract_entities(event.content or "")
        
        return ProcessedEvent(
            prediction_id=event.event_id,
            event_id=event.event_id,
            source=event.source,
            content=event.content,
            sentiment=sentiment,
            entities=entities,
            symbols=event.symbols,
            keywords=entities,
            processed_at=__import__('datetime').datetime.utcnow(),
            tenant_id=event.tenant_id,
        )
