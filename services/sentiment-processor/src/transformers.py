"""Data transformation utilities for Silver layer.

This module provides data cleaning, entity extraction, and enrichment
for both crypto and gold market content.
"""

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from sentilyze_core import RawEvent, ProcessedEvent, SentimentResult, get_logger

from .config import MarketType

logger = get_logger(__name__)

# Crypto entity patterns
CRYPTO_PATTERNS = {
    "BTC": r"\b(Bitcoin|BTC)\b",
    "ETH": r"\b(Ethereum|ETH|Ether)\b",
    "BNB": r"\b(BNB|Binance Coin|BinanceCoin)\b",
    "SOL": r"\b(Solana|SOL)\b",
    "ADA": r"\b(Cardano|ADA)\b",
    "XRP": r"\b(Ripple|XRP)\b",
    "DOT": r"\b(Polkadot|DOT)\b",
    "DOGE": r"\b(Dogecoin|DOGE)\b",
    "AVAX": r"\b(Avalanche|AVAX)\b",
    "MATIC": r"\b(Polygon|MATIC)\b",
    "LINK": r"\b(Chainlink|LINK)\b",
    "UNI": r"\b(Uniswap|UNI)\b",
    "LTC": r"\b(Litecoin|LTC)\b",
    "ATOM": r"\b(Cosmos|ATOM)\b",
    "ETC": r"\b(Ethereum Classic|ETC|EthereumClassic)\b",
}

# Gold entity patterns
GOLD_PATTERNS = {
    "XAU": r"\b(XAU|XAUUSD|gold|Gold)\b",
    "GLD": r"\b(GLD|SPDR Gold Shares)\b",
    "IAU": r"\b(IAU|iShares Gold Trust)\b",
    "GDX": r"\b(GDX|VanEck Gold Miners ETF)\b",
    "BULLION": r"\b(bullion|gold bars|gold coins)\b",
}

# Macro indicators for gold
MACRO_INDICATOR_PATTERNS = {
    "FED": r"\b(Fed|FOMC|Federal Reserve)\b",
    "CPI": r"\b(CPI|inflation|consumer price)\b",
    "PPI": r"\b(PPI|producer price)\b",
    "NFP": r"\b(NFP|non-farm payrolls|jobs report)\b",
    "DXY": r"\b(DXY|dollar index|USD strength)\b",
    "US10Y": r"\b(US10Y|10-year|treasury yield)\b",
    "VIX": r"\b(VIX|volatility index|fear index)\b",
}

# Sentiment keywords
POSITIVE_KEYWORDS = [
    "bullish", "moon", "pump", "gain", "profit", "surge", "rally",
    "breakout", "ATH", "all time high", "buy", "long", "hodl",
    "accumulate", "support", "bounce", "recovery", "green", "up",
]

NEGATIVE_KEYWORDS = [
    "bearish", "dump", "crash", "loss", "bear", "sell", "short",
    "rug pull", "scam", "panic", "fear", "red", "dip", "correction",
    "resistance", "rejection", "death cross", "liquidation", "down",
]


class DataTransformer:
    """Transform raw events to processed events (Silver layer)."""

    def __init__(self) -> None:
        self.crypto_patterns = {
            symbol: re.compile(pattern, re.IGNORECASE)
            for symbol, pattern in CRYPTO_PATTERNS.items()
        }
        self.gold_patterns = {
            symbol: re.compile(pattern, re.IGNORECASE)
            for symbol, pattern in GOLD_PATTERNS.items()
        }
        self.macro_patterns = {
            indicator: re.compile(pattern, re.IGNORECASE)
            for indicator, pattern in MACRO_INDICATOR_PATTERNS.items()
        }

    def transform(
        self,
        raw_event: RawEvent,
        sentiment: SentimentResult,
        *,
        prediction_id: UUID,
        market_type: MarketType = MarketType.CRYPTO,
    ) -> ProcessedEvent:
        """Transform raw event to processed event.

        Args:
            raw_event: Original raw event
            sentiment: Analyzed sentiment
            prediction_id: Unique prediction identifier
            market_type: Type of market content

        Returns:
            Processed event for Silver layer
        """
        cleaned_content = self._clean_content(raw_event.content)

        if market_type == MarketType.CRYPTO:
            entities = self._extract_crypto_entities(cleaned_content)
            symbols = list(set(raw_event.symbols + self._extract_crypto_symbols(cleaned_content)))
        elif market_type == MarketType.GOLD:
            entities = self._extract_gold_entities(cleaned_content)
            symbols = list(set(raw_event.symbols + self._extract_gold_symbols(cleaned_content)))
            entities.extend(self._extract_macro_indicators(cleaned_content))
        else:
            entities = self._extract_crypto_entities(cleaned_content)
            entities.extend(self._extract_gold_entities(cleaned_content))
            symbols = list(set(raw_event.symbols + 
                            self._extract_crypto_symbols(cleaned_content) + 
                            self._extract_gold_symbols(cleaned_content)))

        keywords = self._extract_keywords(cleaned_content)
        engagement_score = self._calculate_engagement(raw_event)

        return ProcessedEvent(
            prediction_id=prediction_id,
            event_id=raw_event.event_id,
            source=raw_event.source,
            content=cleaned_content,
            sentiment=sentiment,
            entities=entities,
            symbols=symbols,
            keywords=keywords,
            processed_at=datetime.utcnow(),
            tenant_id=raw_event.tenant_id,
            engagement_score=engagement_score,
            reach_estimate=self._estimate_reach(raw_event),
        )

    def _clean_content(self, content: str | None) -> str:
        """Clean and normalize content."""
        if not content:
            return ""
            
        content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content)
        content = re.sub(r'<[^>]+>', '', content)
        content = ' '.join(content.split())
        content = content.strip()

        return content

    def _extract_crypto_entities(self, content: str) -> list[str]:
        """Extract crypto entities from content."""
        entities = []
        for symbol, pattern in self.crypto_patterns.items():
            if pattern.search(content):
                entities.append(symbol)
        return entities

    def _extract_gold_entities(self, content: str) -> list[str]:
        """Extract gold entities from content."""
        entities = []
        for symbol, pattern in self.gold_patterns.items():
            if pattern.search(content):
                entities.append(symbol)
        return entities

    def _extract_macro_indicators(self, content: str) -> list[str]:
        """Extract macroeconomic indicators from content."""
        indicators = []
        for indicator, pattern in self.macro_patterns.items():
            if pattern.search(content):
                indicators.append(indicator)
        return indicators

    def _extract_crypto_symbols(self, content: str) -> list[str]:
        """Extract crypto symbols from content."""
        symbols = []
        content_upper = content.upper()
        for symbol in CRYPTO_PATTERNS.keys():
            if symbol in content_upper:
                symbols.append(symbol)
        return symbols

    def _extract_gold_symbols(self, content: str) -> list[str]:
        """Extract gold symbols from content."""
        symbols = []
        content_upper = content.upper()
        for symbol in GOLD_PATTERNS.keys():
            if symbol in content_upper:
                symbols.append(symbol)
        return symbols

    def _extract_keywords(self, content: str) -> list[str]:
        """Extract relevant keywords from content."""
        content_lower = content.lower()
        keywords = []

        for keyword in POSITIVE_KEYWORDS + NEGATIVE_KEYWORDS:
            if keyword in content_lower:
                keywords.append(keyword)

        hashtags = re.findall(r'#\w+', content)
        keywords.extend(hashtags)

        cashtags = re.findall(r'\$[A-Z]{2,5}\b', content)
        keywords.extend(cashtags)

        return list(set(keywords))

    def _calculate_engagement(self, event: RawEvent) -> float:
        """Calculate engagement score from metadata."""
        metadata = event.metadata or {}
        score = 0.0

        if event.source.value == "reddit":
            score += metadata.get("score", 0) * 0.5
            score += metadata.get("num_comments", 0) * 2
            score += metadata.get("awards", 0) * 10
            upvote_ratio = metadata.get("upvote_ratio", 0.5)
            score *= (0.5 + upvote_ratio)
        elif event.source.value == "rss":
            score = 50
        elif event.source.value == "binance":
            score = metadata.get("volume", 0) * 0.001
            price_change = abs(metadata.get("price_change_percent", 0))
            score += price_change * 10

        return round(score, 2)

    def _estimate_reach(self, event: RawEvent) -> int | None:
        """Estimate content reach."""
        metadata = event.metadata or {}

        if event.source.value == "reddit":
            return metadata.get("score", 0) * 10 + metadata.get("num_comments", 0) * 50

        return None


class SilverLayerTransformer:
    """Transform data for Silver layer (cleaned and enriched)."""

    @staticmethod
    def to_bigquery_row(processed_event: ProcessedEvent) -> dict[str, Any]:
        """Convert processed event to BigQuery row format."""
        return processed_event.model_dump(mode="json")
