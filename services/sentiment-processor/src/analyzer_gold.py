"""Gold-specific sentiment analyzer using Vertex AI Gemini with COT framework.

This module provides the GoldSentimentAnalyzer class that extends
BaseSentimentAnalyzer with gold market-specific prompts, COT framework
integration, and macro force extraction.
"""

from typing import Any
from uuid import UUID

from sentilyze_core import (
    ProcessedEvent,
    RawEvent,
    SentimentLabel,
    SentimentResult,
    get_logger,
    get_settings,
)
from sentilyze_core.exceptions import ExternalServiceError

from .analyzer_base import BaseSentimentAnalyzer
from .config import (
    MacroIndicatorType,
    CotPositionType,
)

logger = get_logger(__name__)
settings = get_settings()

# Default gold prompt template with COT context placeholder
DEFAULT_GOLD_PROMPT_TEMPLATE = """You are a gold market sentiment analyst. Analyze the following text for sentiment related to gold (XAU) prices and the precious metals market.

TEXT TO ANALYZE:
{text}

Provide a comprehensive sentiment analysis with the following JSON structure:
{{
    "score": <float between -1 and 1, where -1 is very bearish for gold, 0 is neutral, 1 is very bullish>,
    "label": <one of: "very_positive", "positive", "neutral", "negative", "very_negative">,
    "confidence": <float between 0 and 1>,
    "explanation": <brief 2-3 sentence explanation of the sentiment and key drivers>,
    "entities": [<list of key entities mentioned: FED, ECB, central banks, inflation, rates, etc.>],
    "key_drivers": [<list of 2-4 key factors driving the sentiment>],
    "price_implication": <"bullish", "bearish", or "neutral" for gold prices>,
    "time_horizon": <"short_term", "medium_term", or "long_term">
}}

ANALYSIS GUIDELINES:

1. **SCORING CRITERIA** (bullish = positive for gold price):
   - Score > 0.6: Very bullish (e.g., Fed rate cuts expected, high inflation, major geopolitical crisis)
   - Score 0.2 to 0.6: Bullish (e.g., moderate inflation concerns, some safe haven demand)
   - Score -0.2 to 0.2: Neutral (e.g., mixed signals, consolidation, no clear direction)
   - Score -0.6 to -0.2: Bearish (e.g., strong dollar, rate hikes, risk-on sentiment)
   - Score < -0.6: Very bearish (e.g., aggressive Fed tightening, strong economic data, strong USD)

2. **KEY ENTITIES TO IDENTIFY**:
   - Central banks: FED, ECB, BOE, BOJ, PBOC
   - Economic indicators: CPI, PPI, NFP, GDP, inflation, recession
   - Market factors: DXY (dollar index), yields, US10Y, treasury, real rates
   - Geopolitical: war, conflict, sanctions, elections, trade disputes
   - Gold-specific: XAU, XAUUSD, GLD, IAU, bullion, precious metals

3. **KEY DRIVERS**:
   - "inflation" - Inflation concerns or data
   - "fed_policy" - Federal Reserve decisions, forward guidance
   - "dollar_strength" - US Dollar strength/weakness (DXY)
   - "rates" - Interest rate changes or expectations
   - "safe_haven_demand" - Flight to safety, risk-off sentiment
   - "geopolitical_risk" - Wars, conflicts, political instability
   - "economic_uncertainty" - Recession fears, economic data concerns
   - "central_bank_buying" - Central bank gold purchases
   - "technical_levels" - Support/resistance, chart patterns
   - "etf_flows" - Gold ETF inflows/outflows

4. **CONFIDENCE FACTORS**:
   - High confidence (0.8-1.0): Clear, direct statements from authoritative sources
   - Medium confidence (0.5-0.8): Analyst opinions with supporting data
   - Low confidence (0.0-0.5): Vague statements, conflicting information

Respond ONLY with the valid JSON object, no markdown formatting or additional text."""

# Macro patterns for fallback extraction
MACRO_PATTERNS = {
    MacroIndicatorType.FED_RATE: ["fed", "federal reserve", "interest rate", "rate hike", "rate cut", "fomc"],
    MacroIndicatorType.CPI: ["cpi", "inflation", "consumer price", "inflation data"],
    MacroIndicatorType.PPI: ["ppi", "producer price"],
    MacroIndicatorType.NFP: ["nfp", "non-farm payrolls", "jobs report", "employment"],
    MacroIndicatorType.GDP: ["gdp", "gross domestic product", "economic growth"],
    MacroIndicatorType.DXY: ["dxy", "dollar index", "usd strength", "dollar strength"],
    MacroIndicatorType.US10Y: ["us10y", "10-year", "treasury yield", "bond yield", "real rates"],
    MacroIndicatorType.VIX: ["vix", "volatility", "fear index"],
    MacroIndicatorType.GEOPOLITICAL: ["war", "conflict", "sanctions", "geopolitical", "election", "brexit", "tension"],
}

# Gold keywords for content filtering (English + Turkish)
GOLD_KEYWORDS = [
    # English
    "gold", "xau", "xauusd", "precious metal", "bullion",
    "gld", "iau", "gdx", "gold price", "gold market",
    "gold etf", "gold futures", "spot gold",
    # Turkish
    "altın", "gram altın", "çeyrek altın", "ons", "xautry",
    "külçe", "kuyumcu", "altın fiyatı",
]

# Driver to indicator mapping
DRIVER_TO_INDICATOR = {
    "inflation": MacroIndicatorType.CPI,
    "fed_policy": MacroIndicatorType.FED_RATE,
    "dollar_strength": MacroIndicatorType.DXY,
    "rates": MacroIndicatorType.US10Y,
    "safe_haven_demand": MacroIndicatorType.GEOPOLITICAL,
    "geopolitical_risk": MacroIndicatorType.GEOPOLITICAL,
    "economic_uncertainty": MacroIndicatorType.GDP,
    "central_bank_buying": MacroIndicatorType.FED_RATE,
}


class CotDataPoint:
    """COT (Commitment of Traders) data point."""
    
    def __init__(
        self,
        position_type: CotPositionType,
        long_positions: int,
        short_positions: int,
        net_position: int,
        change_from_prev: int = 0,
        percent_of_open_interest: float = 0.0,
    ) -> None:
        self.position_type = position_type
        self.long_positions = long_positions
        self.short_positions = short_positions
        self.net_position = net_position
        self.change_from_prev = change_from_prev
        self.percent_of_open_interest = percent_of_open_interest


class CotReport:
    """COT report for gold futures."""
    
    def __init__(
        self,
        report_date: str,
        positions: dict[CotPositionType, CotDataPoint],
        total_open_interest: int,
        price_at_report: float | None = None,
    ) -> None:
        self.report_date = report_date
        self.positions = positions
        self.total_open_interest = total_open_interest
        self.price_at_report = price_at_report
    
    def get_net_position(self, position_type: CotPositionType) -> int:
        """Get net position for a specific trader type."""
        if position_type in self.positions:
            return self.positions[position_type].net_position
        return 0
    
    def get_sentiment_signal(self) -> str:
        """Generate sentiment signal from COT data."""
        mm_net = self.get_net_position(CotPositionType.MONEY_MANAGER)
        
        if mm_net > 100000:
            return "very_bullish"
        elif mm_net > 50000:
            return "bullish"
        elif mm_net < -100000:
            return "very_bearish"
        elif mm_net < -50000:
            return "bearish"
        return "neutral"


class MacroForce:
    """Macroeconomic force affecting gold prices."""
    
    def __init__(
        self,
        indicator: MacroIndicatorType,
        value: float,
        impact: str,
        direction: str,
        description: str,
    ) -> None:
        self.indicator = indicator
        self.value = value
        self.impact = impact
        self.direction = direction
        self.description = description


class GoldSentimentAnalysis:
    """Extended sentiment analysis for gold markets."""
    
    def __init__(
        self,
        sentiment: SentimentResult,
        macro_forces: list[MacroForce],
        entities: list[str],
        key_drivers: list[str],
        price_implication: str,
        confidence_factors: list[str],
        cot_signal: str | None = None,
        time_horizon: str = "short_term",
    ) -> None:
        self.sentiment = sentiment
        self.macro_forces = macro_forces
        self.entities = entities
        self.key_drivers = key_drivers
        self.price_implication = price_implication
        self.confidence_factors = confidence_factors
        self.cot_signal = cot_signal
        self.time_horizon = time_horizon
    
    def model_dump(self, mode: str = "json") -> dict:
        """Dump to dictionary format."""
        return {
            "sentiment": self.sentiment.model_dump(mode=mode) if hasattr(self.sentiment, 'model_dump') else vars(self.sentiment),
            "macro_forces": [
                {
                    "indicator": f.indicator.value,
                    "value": f.value,
                    "impact": f.impact,
                    "direction": f.direction,
                    "description": f.description,
                }
                for f in self.macro_forces
            ],
            "entities": self.entities,
            "key_drivers": self.key_drivers,
            "price_implication": self.price_implication,
            "confidence_factors": self.confidence_factors,
            "cot_signal": self.cot_signal,
            "time_horizon": self.time_horizon,
        }


class GoldSentimentAnalyzer(BaseSentimentAnalyzer):
    """Gold market-specific sentiment analyzer with COT framework support.
    
    Extends BaseSentimentAnalyzer with gold-specific:
    - COT (Commitment of Traders) framework integration
    - Macro force extraction
    - Extended sentiment analysis with price implications
    - Gold-specific entity extraction (FED, inflation, etc.)
    """

    def __init__(self, prompt_template: str | None = None) -> None:
        super().__init__(prompt_template)
        self._market_type = "gold"
        self._cot_report: CotReport | None = None
        self._language: str = "en"  # Default to English

    @property
    def _prompt_file_name(self) -> str:
        # Return Turkish prompt if Turkish content detected
        if self._language == "tr":
            return "turkish_gold_v1.txt"
        return "gold_v1.txt"

    @property
    def _cache_namespace(self) -> str:
        return "gold_sentiment"

    def _get_default_prompt_template(self) -> str:
        return DEFAULT_GOLD_PROMPT_TEMPLATE

    def set_cot_report(self, cot_report: CotReport | None) -> None:
        """Set COT report data for enhanced analysis."""
        self._cot_report = cot_report
        logger.info(f"COT report set for date: {cot_report.report_date if cot_report else 'None'}")

    def _detect_language(self, text: str) -> str:
        """Detect if text is Turkish or English.

        Args:
            text: Text to analyze

        Returns:
            "tr" for Turkish, "en" for English
        """
        try:
            from sentilyze_core.keywords_turkish import is_turkish_gold_content

            if is_turkish_gold_content(text):
                return "tr"
            return "en"
        except ImportError:
            logger.warning("Turkish keywords module not found, defaulting to English")
            return "en"

    def _is_content_relevant(self, content: str | None) -> bool:
        """Check if content is gold-related."""
        if not content:
            return False

        content_lower = content.lower()
        return any(keyword in content_lower for keyword in GOLD_KEYWORDS)

    def _build_prompt(self, text: str) -> str:
        """Build prompt with optional COT context and language detection."""
        prompt_text = text[:3000]

        # Detect language and reload prompt if needed
        detected_language = self._detect_language(prompt_text)
        if detected_language != self._language:
            self._language = detected_language
            # Reload prompt template for detected language
            self._load_prompt_template()
            logger.info(f"Detected language: {detected_language}, loaded appropriate prompt")

        # Add COT context if available and enabled (only for English)
        if self._cot_report and settings.enable_cot_framework and self._language == "en":
            cot_context = self._build_cot_context()
            if cot_context:
                prompt_text = f"{cot_context}\n\n{prompt_text}"

        return self._prompt_template.format(text=prompt_text)

    def _build_cot_context(self) -> str:
        """Build COT context string for prompt enhancement."""
        if not self._cot_report:
            return ""
        
        mm = self._cot_report.positions.get(CotPositionType.MONEY_MANAGER)
        if not mm:
            return ""
        
        return f"""COT (Commitment of Traders) Context for Gold Futures (as of {self._cot_report.report_date}):
- Money Managers Net Position: {mm.net_position:,} contracts
- Money Managers Change: {mm.change_from_prev:+,} from previous week
- Market Signal: {self._cot_report.get_sentiment_signal()}

Consider this institutional positioning data in your analysis."""

    def _extract_entities(self, text: str) -> list[str]:
        """Extract gold market entities from text."""
        if not text:
            return []
        
        entities = []
        text_upper = text.upper()
        
        # Central banks
        if "FED" in text_upper or "FEDERAL RESERVE" in text_upper:
            entities.append("FED")
        if "ECB" in text_upper:
            entities.append("ECB")
        if "BOE" in text_upper:
            entities.append("BOE")
        if "BOJ" in text_upper:
            entities.append("BOJ")
        if "PBOC" in text_upper:
            entities.append("PBOC")
        
        # Economic indicators
        if "CPI" in text_upper or "INFLATION" in text.lower():
            entities.append("CPI/Inflation")
        if "PPI" in text_upper:
            entities.append("PPI")
        if any(term in text.lower() for term in ["nfp", "non-farm", "payroll", "jobs"]):
            entities.append("NFP")
        if "GDP" in text_upper:
            entities.append("GDP")
        
        # Market factors
        if "DXY" in text_upper or "DOLLAR INDEX" in text_upper:
            entities.append("DXY")
        if any(term in text_upper for term in ["US10Y", "10-YEAR", "TREASURY"]):
            entities.append("US10Y")
        if "VIX" in text_upper:
            entities.append("VIX")
        
        # Gold-specific
        if any(term in text_upper for term in ["XAU", "XAUUSD", "SPOT GOLD"]):
            entities.append("XAU")
        if any(term in text_upper for term in ["GLD", "IAU"]):
            entities.append("Gold ETFs")
        
        return entities

    async def _post_process_result(
        self, 
        event: RawEvent, 
        sentiment: SentimentResult
    ) -> ProcessedEvent:
        """Create processed event with gold-specific extended analysis."""
        # Parse extended fields from Gemini response if available
        # For now, use fallback extraction
        entities = self._extract_entities(event.content or "")
        macro_forces = self._extract_macro_forces(event.content or "")
        key_drivers = [f.indicator.value for f in macro_forces]
        
        # Get COT signal
        cot_signal = None
        if self._cot_report and settings.enable_cot_framework:
            cot_signal = self._cot_report.get_sentiment_signal()
        
        # Determine price implication from sentiment
        price_implication = self._get_price_implication(sentiment)
        
        # Create extended analysis
        analysis = GoldSentimentAnalysis(
            sentiment=sentiment,
            macro_forces=macro_forces,
            entities=entities,
            key_drivers=key_drivers,
            price_implication=price_implication,
            confidence_factors=["gemini_gold_analysis"],
            cot_signal=cot_signal,
            time_horizon="short_term",
        )
        
        # Cache the extended analysis
        cache_key = self._get_cache_key(event.content or "")
        await self.cache.set(
            cache_key,
            analysis.model_dump(mode="json"),
            namespace=self._cache_namespace,
            ttl=settings.sentiment_cache_ttl,
        )
        
        return ProcessedEvent(
            prediction_id=event.event_id,
            event_id=event.event_id,
            source=event.source,
            content=event.content,
            sentiment=sentiment,
            entities=entities,
            symbols=event.symbols,
            keywords=key_drivers,
            processed_at=__import__('datetime').datetime.utcnow(),
            tenant_id=event.tenant_id,
            metadata={
                "macro_forces": [f.indicator.value for f in macro_forces],
                "price_implication": price_implication,
                "cot_signal": cot_signal,
                "time_horizon": analysis.time_horizon,
            }
        )

    def _get_price_implication(self, sentiment: SentimentResult) -> str:
        """Determine price implication from sentiment."""
        if sentiment.score > 0.2:
            return "bullish"
        elif sentiment.score < -0.2:
            return "bearish"
        return "neutral"

    def _extract_macro_forces(self, content: str) -> list[MacroForce]:
        """Extract macro forces from content using pattern matching."""
        if not content:
            return []

        content_lower = content.lower()
        forces = []

        for indicator_type, patterns in MACRO_PATTERNS.items():
            for pattern in patterns:
                if pattern in content_lower:
                    direction = self._determine_direction(content_lower, pattern)
                    forces.append(
                        MacroForce(
                            indicator=indicator_type,
                            value=0.0,
                            impact="medium",
                            direction=direction,
                            description=f"Detected mention of {indicator_type.value}",
                        )
                    )
                    break

        return forces

    def _determine_direction(self, content: str, keyword: str) -> str:
        """Determine if a keyword has positive or negative implication for gold."""
        idx = content.find(keyword)
        if idx == -1:
            return "neutral"

        start = max(0, idx - 50)
        end = min(len(content), idx + len(keyword) + 50)
        context = content[start:end]

        positive_words = ["rise", "rising", "up", "increase", "higher", "surge", "gain", "bullish", "strong"]
        negative_words = ["fall", "falling", "down", "decrease", "lower", "drop", "lose", "bearish", "weak"]

        pos_count = sum(1 for word in positive_words if word in context)
        neg_count = sum(1 for word in negative_words if word in context)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"

    def _create_fallback_result(self, explanation: str) -> SentimentResult:
        """Create fallback result for gold analysis."""
        # Call parent fallback but add gold-specific context
        return super()._create_fallback_result(explanation)

    def _create_processed_event_from_cache(
        self,
        event: RawEvent,
        cached_result: dict,
        prediction_id: UUID | None = None,
    ) -> ProcessedEvent:
        """Create processed event from cached extended analysis."""
        # Parse extended gold analysis from cache
        sentiment_data = cached_result.get("sentiment", cached_result)
        sentiment = SentimentResult(**sentiment_data)
        
        return ProcessedEvent(
            prediction_id=prediction_id or event.event_id,
            event_id=event.event_id,
            source=event.source,
            content=event.content,
            sentiment=sentiment,
            entities=cached_result.get("entities", []),
            symbols=event.symbols,
            keywords=cached_result.get("key_drivers", []),
            processed_at=__import__('datetime').datetime.utcnow(),
            tenant_id=event.tenant_id,
            metadata={
                "macro_forces": cached_result.get("macro_forces", []),
                "price_implication": cached_result.get("price_implication", "neutral"),
                "cot_signal": cached_result.get("cot_signal"),
                "time_horizon": cached_result.get("time_horizon", "short_term"),
            }
        )
