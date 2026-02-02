"""Base sentiment analyzer with common functionality.

This module provides the BaseSentimentAnalyzer class that consolidates
all common functionality shared between market-specific analyzers.
"""

import asyncio
import hashlib
import json
import os
import random
import time
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

import vertexai
from google.api_core.exceptions import DeadlineExceeded, ResourceExhausted, ServiceUnavailable
from vertexai.generative_models import GenerativeModel, GenerationConfig

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

logger = get_logger(__name__)
settings = get_settings()


class BaseSentimentAnalyzer(ABC):
    """Abstract base class for market-specific sentiment analyzers.
    
    This class provides all common functionality:
    - Gemini initialization
    - Retry logic with exponential backoff
    - Rate limiting (RPM and daily)
    - JSON extraction from responses
    - Label normalization
    - Caching
    - Lite sentiment fallback (Google NLP)
    
    Subclasses must implement market-specific methods for prompts,
    entity extraction, and post-processing.
    """

    def __init__(self, prompt_template: str | None = None) -> None:
        self.model: GenerativeModel | None = None
        self.cache = CacheClient()
        self._gemini_semaphore = asyncio.Semaphore(max(1, int(settings.gemini_max_concurrency)))
        self._nl_client: Any | None = None
        self._initialized = False
        self._prompt_template = prompt_template or self._load_prompt_template()
        self._market_type: str = "generic"

    @property
    @abstractmethod
    def _prompt_file_name(self) -> str:
        """Return the filename for the prompt template (e.g., 'crypto_v1.txt')."""
        pass

    @property
    @abstractmethod
    def _cache_namespace(self) -> str:
        """Return the cache namespace for this analyzer (e.g., 'crypto_sentiment')."""
        pass

    def _load_prompt_template(self) -> str:
        """Load prompt template from file or use default from subclass."""
        try:
            prompt_path = os.path.join(
                os.path.dirname(__file__), 
                "prompts", 
                self._prompt_file_name
            )
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            logger.warning(f"Could not load prompt file {self._prompt_file_name}, using default: {e}")
        return self._get_default_prompt_template()

    @abstractmethod
    def _get_default_prompt_template(self) -> str:
        """Return the default prompt template for this market."""
        pass

    async def initialize(self) -> None:
        """Initialize Vertex AI and model."""
        try:
            vertexai.init(
                project=settings.vertex_ai_project_id or settings.google_cloud_project,
                location=settings.vertex_ai_location,
            )

            self.model = GenerativeModel(settings.gemini_model)
            self._initialized = True

            logger.info(
                f"{self._market_type.capitalize()} sentiment analyzer initialized",
                model=settings.gemini_model,
                location=settings.vertex_ai_location,
            )
        except Exception as e:
            raise ExternalServiceError(
                f"Failed to initialize Vertex AI: {e}",
                service="vertex_ai",
            )

    async def analyze(self, event: RawEvent, prediction_id: UUID | None = None) -> ProcessedEvent:
        """Analyze sentiment of a raw event with market-specific processing."""
        if not self._initialized:
            raise RuntimeError("Analyzer not initialized")

        # Check if content is relevant for this market
        if not self._is_content_relevant(event.content):
            return self._create_neutral_processed_event(event, prediction_id)

        # Check cache first
        cache_key = self._get_cache_key(event.content)
        cached_result = await self.cache.get(cache_key, namespace=self._cache_namespace)

        if cached_result:
            logger.debug(f"Using cached {self._market_type} sentiment result", event_id=str(event.event_id))
            return self._create_processed_event_from_cache(event, cached_result, prediction_id)

        # Determine routing: lite vs deep analysis
        use_lite = self._should_use_lite(event.content)
        routing_path = "lite" if use_lite else "deep"

        if use_lite:
            # NOTE: Cloud Natural Language API is disabled (too expensive)
            # Use free neutral fallback instead
            sentiment = self._create_fallback_result(
                "Content below processing threshold (lite mode disabled for cost control)"
            )
            routing_path = "lite"
        else:
            try:
                sentiment = await self._analyze_with_gemini(event.content)
            except (RateLimitError, ExternalServiceError) as e:
                logger.warning(
                    f"Gemini analysis failed; using neutral fallback (expensive Cloud NL API disabled)",
                    event_id=str(event.event_id),
                    error=str(e),
                )
                # CRITICAL: Do NOT use Cloud Natural Language API (too expensive)
                # Use free neutral fallback instead
                sentiment = self._create_fallback_result(
                    f"Analysis temporarily unavailable: {str(e)}"
                )

        # Normalize model used and routing path
        sentiment.routing_path = routing_path
        sentiment.model_used = self._normalize_model_used(sentiment.model_used, routing_path=routing_path)

        # Post-process and create result
        result = await self._post_process_result(event, sentiment)
        
        # Cache the result
        await self._cache_result(cache_key, result)

        return result

    def _is_content_relevant(self, content: str | None) -> bool:
        """Check if content is relevant for this market. Override for market-specific filtering."""
        return True

    def _should_use_lite(self, text: str) -> bool:
        """Decide whether to use Lite sentiment (NL API) instead of Gemini."""
        if settings.sentiment_lite_mode:
            return True
        max_chars = max(0, int(settings.sentiment_lite_max_chars))
        return len((text or "").strip()) <= max_chars if max_chars > 0 else False

    async def _analyze_lite(self, text: str) -> SentimentResult:
        """DISABLED: Analyze sentiment using Google Cloud Natural Language API.

        WARNING: Cloud Natural Language API is disabled due to cost (₺12,000+ monthly).
        This method now returns a neutral fallback response.

        History: This was causing ₺12,000+ in costs over 3 days when Gemini failed.
        See .env.production SENTIMENT_LITE_MODE=false and SENTIMENT_LITE_MAX_CHARS=0
        """
        # ALWAYS return neutral fallback - never use expensive Cloud NL API
        return SentimentResult(
            score=0.0,
            label=SentimentLabel.NEUTRAL,
            confidence=0.0,
            explanation="Lite sentiment analysis disabled (Cloud NL API too expensive)",
            model_used="fallback-neutral",
        )

    def _analyze_lite_sync(self, text: str) -> SentimentResult:
        """DISABLED: Synchronous Natural Language API sentiment call.

        CRITICAL: This method uses expensive Cloud Natural Language API and has been disabled.
        Cost: ₺12,000+ in 3 days when fallback mechanism was active.

        If you need to re-enable this:
        1. Delete the override below
        2. Set SENTIMENT_LITE_MODE=false in production
        3. Ensure GOOGLE_CLOUD_LANGUAGE is installed (poetry install --with lite)
        """
        # Safety override: Never call expensive Cloud Natural Language API
        raise RuntimeError(
            "Cloud Natural Language API is disabled due to excessive costs (₺12,000+ in 3 days). "
            "Use Gemini analysis or neutral fallback instead. "
            "See analyzer_base.py comments for re-enabling instructions."
        )

    def _label_from_score(self, score: float) -> SentimentLabel:
        """Map a numeric score [-1, 1] to SentimentLabel."""
        if score >= 0.6:
            return SentimentLabel.VERY_POSITIVE
        if score >= 0.2:
            return SentimentLabel.POSITIVE
        if score <= -0.6:
            return SentimentLabel.VERY_NEGATIVE
        if score <= -0.2:
            return SentimentLabel.NEGATIVE
        return SentimentLabel.NEUTRAL

    def _normalize_model_used(self, model_used: str | None, routing_path: str) -> str:
        """Normalize model identifiers to stable API values."""
        v = (model_used or "").strip().lower()
        
        if v in {"gcp-natural-language", "natural-language", "gcp_nlp", "google-nl", "google-nlp"}:
            return "google-nlp"
        
        if "gemini" in v:
            return v if v.startswith("gemini-") else settings.gemini_model
        
        return "google-nlp" if routing_path == "lite" else settings.gemini_model

    async def _analyze_with_gemini(self, text: str) -> SentimentResult:
        """Analyze sentiment using Gemini with rate limiting and retries."""
        if not self.model:
            raise RuntimeError("Model not initialized")

        # Get market-specific prompt
        prompt = self._build_prompt(text)

        # RPM rate limiting
        if settings.gemini_rpm_limit and settings.gemini_rpm_limit > 0:
            window = int(time.time() // 60)
            key = f"gemini:rpm:{window}"
            current = await self.cache.increment_with_ttl(
                key,
                ttl_seconds=70,
                namespace="ratelimit",
            )
            if current > settings.gemini_rpm_limit:
                retry_after = await self.cache.ttl(key, namespace="ratelimit")
                raise RateLimitError(
                    "Gemini RPM limit reached",
                    retry_after=max(1, retry_after if retry_after > 0 else 60),
                )

        # Daily limit check
        if settings.gemini_daily_limit > 0:
            today = time.strftime("%Y-%m-%d")
            daily_key = f"gemini:daily:{today}"
            daily_count = await self.cache.increment_with_ttl(
                daily_key,
                ttl_seconds=86400,
                namespace="ratelimit",
            )
            if daily_count > settings.gemini_daily_limit:
                raise RateLimitError(
                    f"Gemini daily limit reached ({settings.gemini_daily_limit} requests/day)",
                    retry_after=3600,
                )

        # Acquire semaphore for concurrency control
        try:
            await asyncio.wait_for(
                self._gemini_semaphore.acquire(),
                timeout=max(0.0, float(settings.gemini_queue_timeout_seconds)),
            )
        except asyncio.TimeoutError as e:
            raise RateLimitError("Gemini concurrency queue full", retry_after=5) from e

        try:
            return await self._call_gemini_with_retry(prompt, text)
        finally:
            self._gemini_semaphore.release()

    def _build_prompt(self, text: str) -> str:
        """Build the prompt for Gemini. Override for market-specific prompt building."""
        return self._prompt_template.format(text=text[:2000])

    async def _call_gemini_with_retry(self, prompt: str, original_text: str) -> SentimentResult:
        """Call Gemini with retry logic."""
        generation_config = GenerationConfig(
            temperature=0.1,
            max_output_tokens=1024,
            response_mime_type="application/json",
        )

        last_exc: Exception | None = None
        for attempt in range(1, max(1, int(settings.gemini_retry_max_attempts)) + 1):
            try:
                response = await self.model.generate_content_async(
                    prompt,
                    generation_config=generation_config,
                )

                response_text = self._extract_json_text(getattr(response, "text", "") or "")
                result = json.loads(response_text)

                return self._parse_gemini_result(result)

            except json.JSONDecodeError as e:
                logger.error(
                    "Failed to parse Gemini response",
                    error=str(e),
                    response_preview=(getattr(response, "text", "")[:500] if "response" in locals() else None),
                )
                return self._create_fallback_result("Failed to parse sentiment response")

            except (ResourceExhausted, ServiceUnavailable, DeadlineExceeded) as e:
                last_exc = e
                if attempt >= int(settings.gemini_retry_max_attempts):
                    break
                delay = min(8.0, (2 ** (attempt - 1))) + random.random()
                logger.warning(
                    "Gemini call failed; retrying",
                    attempt=attempt,
                    delay_seconds=delay,
                    error=str(e),
                )
                await asyncio.sleep(delay)
                continue

            except Exception as e:
                logger.error("Gemini analysis failed", error=str(e))
                raise ExternalServiceError(
                    f"Sentiment analysis failed: {e}",
                    service="vertex_ai",
                ) from e

        raise ExternalServiceError(
            f"Sentiment analysis failed after retries: {last_exc}",
            service="vertex_ai",
        )

    def _parse_gemini_result(self, result: dict) -> SentimentResult:
        """Parse Gemini JSON result into SentimentResult."""
        score = float(result.get("score", 0))
        score = max(-1.0, min(1.0, score))

        label_str = result.get("label", "neutral")
        label = self._normalize_label(label_str)

        confidence = float(result.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        return SentimentResult(
            score=score,
            label=label,
            confidence=confidence,
            explanation=result.get("explanation"),
            model_used=settings.gemini_model,
        )

    def _create_fallback_result(self, explanation: str) -> SentimentResult:
        """Create a fallback sentiment result when parsing fails."""
        return SentimentResult(
            score=0.0,
            label=SentimentLabel.NEUTRAL,
            confidence=0.0,
            explanation=explanation,
            model_used=settings.gemini_model,
        )

    @abstractmethod
    async def _post_process_result(
        self, 
        event: RawEvent, 
        sentiment: SentimentResult
    ) -> ProcessedEvent:
        """Post-process the sentiment result and create a ProcessedEvent.
        
        This is where market-specific entity extraction and extended analysis happens.
        """
        pass

    @abstractmethod
    def _extract_entities(self, text: str) -> list[str]:
        """Extract market-specific entities from text."""
        pass

    def _get_cache_key(self, content: str) -> str:
        """Generate cache key for content."""
        content_hash = hashlib.sha256(content[:200].encode()).hexdigest()[:16]
        return f"{self._cache_namespace}:{content_hash}"

    async def _cache_result(self, cache_key: str, result: ProcessedEvent) -> None:
        """Cache the processed event result."""
        await self.cache.set(
            cache_key,
            result.sentiment.model_dump(mode="json") if hasattr(result.sentiment, 'model_dump') else vars(result.sentiment),
            namespace=self._cache_namespace,
            ttl=settings.sentiment_cache_ttl,
        )

    def _create_neutral_processed_event(
        self,
        event: RawEvent,
        prediction_id: UUID | None = None,
    ) -> ProcessedEvent:
        """Create a neutral processed event for irrelevant content."""
        return ProcessedEvent(
            prediction_id=prediction_id or event.event_id,
            event_id=event.event_id,
            source=event.source,
            content=event.content,
            sentiment=SentimentResult(
                score=0.0,
                label=SentimentLabel.NEUTRAL,
                confidence=0.0,
                explanation=f"Content not related to {self._market_type} markets",
                model_used=settings.gemini_model,
            ),
            entities=[],
            symbols=event.symbols,
            keywords=[],
            processed_at=__import__('datetime').datetime.utcnow(),
            tenant_id=event.tenant_id,
        )

    def _create_processed_event_from_cache(
        self,
        event: RawEvent,
        cached_result: dict,
        prediction_id: UUID | None = None,
    ) -> ProcessedEvent:
        """Create a processed event from cached sentiment data."""
        sentiment = SentimentResult(**cached_result)
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

    def _extract_json_text(self, response_text: str) -> str:
        """Extract a JSON object string from model text.
        
        Handles various markdown code block formats and extracts valid JSON.
        """
        txt = response_text.strip()
        if not txt:
            raise json.JSONDecodeError("Empty response", txt, 0)

        # Handle markdown code blocks
        if "```json" in txt:
            txt = txt.split("```json", 1)[1]
            if "```" in txt:
                txt = txt.split("```", 1)[0]
            txt = txt.strip()
        elif "```" in txt:
            txt = txt.split("```", 1)[1]
            if "```" in txt:
                txt = txt.split("```", 1)[0]
            txt = txt.strip()

        # If already a clean JSON object
        if txt.startswith("{") and txt.endswith("}"):
            return txt

        # Find JSON object boundaries
        start = txt.find("{")
        if start == -1:
            raise json.JSONDecodeError("No JSON object start found", txt, 0)

        # Parse to find matching closing brace
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(txt)):
            ch = txt[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return txt[start : i + 1].strip()

        raise json.JSONDecodeError("Unterminated JSON object", txt, start)

    def _normalize_label(self, label: str) -> SentimentLabel:
        """Normalize label string to SentimentLabel."""
        label_map = {
            "very_positive": SentimentLabel.VERY_POSITIVE,
            "positive": SentimentLabel.POSITIVE,
            "neutral": SentimentLabel.NEUTRAL,
            "negative": SentimentLabel.NEGATIVE,
            "very_negative": SentimentLabel.VERY_NEGATIVE,
        }
        return label_map.get(label.lower(), SentimentLabel.NEUTRAL)

    async def close(self) -> None:
        """Close analyzer resources."""
        await self.cache.close()
        self._initialized = False
        logger.info(f"{self._market_type.capitalize()} sentiment analyzer closed")
