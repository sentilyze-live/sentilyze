"""Real-time sentiment aggregator with time-windowed analysis.

Aggregates sentiment data from multiple sources with configurable
time windows for different trading strategies:
- 5-minute window for scalping
- 15-minute window for short-term
- 1-hour window for intraday
- 24-hour window for daily/swing
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional


class SentimentSource(str, Enum):
    """Source of sentiment data."""

    TWITTER = "twitter"
    REDDIT = "reddit"
    NEWS = "news"
    FORUM = "forum"
    TELEGRAM = "telegram"


@dataclass
class SentimentDataPoint:
    """Single sentiment data point."""

    source: SentimentSource
    score: float  # -1 to 1
    confidence: float  # 0 to 1
    timestamp: datetime
    text_sample: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class AggregatedSentiment:
    """Aggregated sentiment for a time window."""

    window: str  # "5m", "15m", "1h", "24h"
    score: float  # -1 to 1
    confidence: float  # 0 to 1
    data_point_count: int
    source_breakdown: dict[str, float]  # Source -> average score
    trend: str  # "rising", "falling", "stable"
    volatility: float  # Standard deviation of scores
    spike_detected: bool
    spike_magnitude: Optional[float] = None
    oldest_timestamp: Optional[datetime] = None
    newest_timestamp: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "window": self.window,
            "score": round(self.score, 3),
            "confidence": round(self.confidence, 3),
            "data_point_count": self.data_point_count,
            "source_breakdown": {k: round(v, 3) for k, v in self.source_breakdown.items()},
            "trend": self.trend,
            "volatility": round(self.volatility, 3),
            "spike_detected": self.spike_detected,
            "spike_magnitude": round(self.spike_magnitude, 3) if self.spike_magnitude else None,
            "oldest_timestamp": self.oldest_timestamp.isoformat() if self.oldest_timestamp else None,
            "newest_timestamp": self.newest_timestamp.isoformat() if self.newest_timestamp else None,
        }


class RealtimeSentimentAggregator:
    """Aggregates sentiment data with multiple time windows.

    Maintains rolling windows of sentiment data for different timeframes,
    enabling real-time analysis for various trading strategies.

    Windows:
    - 5m: For scalping (max 500 data points)
    - 15m: For short-term (max 1000 data points)
    - 1h: For intraday (max 3000 data points)
    - 24h: For swing/daily (max 10000 data points)
    """

    # Window configurations: (duration in minutes, max data points)
    WINDOW_CONFIG = {
        "5m": (5, 500),
        "15m": (15, 1000),
        "1h": (60, 3000),
        "24h": (1440, 10000),
    }

    # Source weights for aggregation
    SOURCE_WEIGHTS = {
        SentimentSource.TWITTER: 0.35,
        SentimentSource.REDDIT: 0.25,
        SentimentSource.NEWS: 0.25,
        SentimentSource.FORUM: 0.10,
        SentimentSource.TELEGRAM: 0.05,
    }

    # Spike detection threshold (standard deviations)
    SPIKE_THRESHOLD = 2.0

    def __init__(self):
        """Initialize aggregator with empty windows."""
        self._windows: dict[str, deque[SentimentDataPoint]] = {
            window: deque(maxlen=max_size)
            for window, (_, max_size) in self.WINDOW_CONFIG.items()
        }

        # Track recent scores for trend detection
        self._recent_averages: dict[str, deque[float]] = {
            window: deque(maxlen=10) for window in self.WINDOW_CONFIG
        }

    def add_sentiment(
        self,
        source: SentimentSource,
        score: float,
        confidence: float = 0.7,
        text_sample: Optional[str] = None,
        metadata: Optional[dict] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Add a sentiment data point to all windows.

        Args:
            source: Source of sentiment (twitter, news, etc.)
            score: Sentiment score (-1 to 1)
            confidence: Confidence in the score (0 to 1)
            text_sample: Optional sample of source text
            metadata: Optional additional metadata
            timestamp: Optional timestamp (defaults to now)
        """
        data_point = SentimentDataPoint(
            source=source,
            score=max(-1, min(1, score)),  # Clamp to [-1, 1]
            confidence=max(0, min(1, confidence)),
            timestamp=timestamp or datetime.now(timezone.utc),
            text_sample=text_sample[:200] if text_sample else None,
            metadata=metadata or {},
        )

        # Add to all windows
        for window in self._windows:
            self._windows[window].append(data_point)

    def get_aggregated_score(
        self,
        window: str,
        source_filter: Optional[list[SentimentSource]] = None,
    ) -> AggregatedSentiment:
        """Get aggregated sentiment for a time window.

        Args:
            window: Time window ("5m", "15m", "1h", "24h")
            source_filter: Optional list of sources to include

        Returns:
            AggregatedSentiment with score, confidence, and metadata
        """
        if window not in self._windows:
            raise ValueError(f"Invalid window: {window}. Must be one of {list(self.WINDOW_CONFIG.keys())}")

        # Get window duration
        duration_minutes, _ = self.WINDOW_CONFIG[window]
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=duration_minutes)

        # Filter data points by time and source
        data_points = [
            dp
            for dp in self._windows[window]
            if dp.timestamp >= cutoff_time
            and (source_filter is None or dp.source in source_filter)
        ]

        if not data_points:
            return AggregatedSentiment(
                window=window,
                score=0.0,
                confidence=0.0,
                data_point_count=0,
                source_breakdown={},
                trend="stable",
                volatility=0.0,
                spike_detected=False,
            )

        # Calculate weighted average score
        total_weight = 0.0
        weighted_score = 0.0
        weighted_confidence = 0.0
        source_scores: dict[str, list[float]] = {}

        for dp in data_points:
            weight = self.SOURCE_WEIGHTS.get(dp.source, 0.1) * dp.confidence
            weighted_score += dp.score * weight
            weighted_confidence += dp.confidence * weight
            total_weight += weight

            # Track scores by source
            source_key = dp.source.value
            if source_key not in source_scores:
                source_scores[source_key] = []
            source_scores[source_key].append(dp.score)

        if total_weight == 0:
            avg_score = 0.0
            avg_confidence = 0.0
        else:
            avg_score = weighted_score / total_weight
            avg_confidence = weighted_confidence / total_weight

        # Calculate source breakdown
        source_breakdown = {
            source: sum(scores) / len(scores) for source, scores in source_scores.items()
        }

        # Calculate volatility (standard deviation)
        scores = [dp.score for dp in data_points]
        if len(scores) > 1:
            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            volatility = variance ** 0.5
        else:
            volatility = 0.0

        # Detect trend
        trend = self._detect_trend(window, avg_score)

        # Detect spike
        spike_detected, spike_magnitude = self._detect_spike(window, avg_score, volatility)

        # Get timestamps
        timestamps = [dp.timestamp for dp in data_points]

        return AggregatedSentiment(
            window=window,
            score=avg_score,
            confidence=avg_confidence,
            data_point_count=len(data_points),
            source_breakdown=source_breakdown,
            trend=trend,
            volatility=volatility,
            spike_detected=spike_detected,
            spike_magnitude=spike_magnitude,
            oldest_timestamp=min(timestamps),
            newest_timestamp=max(timestamps),
        )

    def detect_sentiment_spike(
        self,
        window: str,
        threshold: float = 0.3,
    ) -> tuple[bool, Optional[float]]:
        """Detect sudden sentiment changes.

        Args:
            window: Time window to check
            threshold: Minimum change to consider a spike

        Returns:
            Tuple of (spike_detected, magnitude)
        """
        if len(self._recent_averages[window]) < 3:
            return False, None

        recent = list(self._recent_averages[window])
        current = recent[-1]
        previous_avg = sum(recent[:-1]) / len(recent[:-1])

        change = current - previous_avg

        if abs(change) >= threshold:
            return True, change

        return False, None

    def get_source_sentiment(
        self,
        source: SentimentSource,
        window: str = "1h",
    ) -> dict:
        """Get sentiment for a specific source.

        Args:
            source: Source to filter by
            window: Time window

        Returns:
            Dict with score, count, and recent samples
        """
        aggregated = self.get_aggregated_score(window, source_filter=[source])

        # Get recent samples
        duration_minutes, _ = self.WINDOW_CONFIG[window]
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=duration_minutes)

        recent_samples = [
            dp.text_sample
            for dp in self._windows[window]
            if dp.source == source
            and dp.timestamp >= cutoff_time
            and dp.text_sample
        ][-5:]  # Last 5 samples

        return {
            "source": source.value,
            "window": window,
            "score": round(aggregated.score, 3),
            "data_point_count": aggregated.data_point_count,
            "recent_samples": recent_samples,
        }

    def get_all_windows(self) -> dict[str, AggregatedSentiment]:
        """Get aggregated sentiment for all windows.

        Returns:
            Dict mapping window name to AggregatedSentiment
        """
        return {window: self.get_aggregated_score(window) for window in self.WINDOW_CONFIG}

    def _detect_trend(self, window: str, current_score: float) -> str:
        """Detect sentiment trend based on recent averages."""
        # Store current average
        self._recent_averages[window].append(current_score)

        if len(self._recent_averages[window]) < 3:
            return "stable"

        recent = list(self._recent_averages[window])

        # Compare first half to second half
        half = len(recent) // 2
        first_half_avg = sum(recent[:half]) / half
        second_half_avg = sum(recent[half:]) / (len(recent) - half)

        diff = second_half_avg - first_half_avg

        if diff > 0.1:
            return "rising"
        elif diff < -0.1:
            return "falling"
        else:
            return "stable"

    def _detect_spike(
        self,
        window: str,
        current_score: float,
        volatility: float,
    ) -> tuple[bool, Optional[float]]:
        """Detect if current score is a spike.

        Uses z-score based on volatility.
        """
        if len(self._recent_averages[window]) < 5:
            return False, None

        recent = list(self._recent_averages[window])
        historical_mean = sum(recent[:-1]) / len(recent[:-1])

        if volatility == 0:
            return False, None

        # Calculate z-score
        z_score = (current_score - historical_mean) / volatility

        if abs(z_score) >= self.SPIKE_THRESHOLD:
            return True, current_score - historical_mean

        return False, None

    def clear_window(self, window: str) -> None:
        """Clear all data from a specific window."""
        if window in self._windows:
            self._windows[window].clear()
            self._recent_averages[window].clear()

    def clear_all(self) -> None:
        """Clear all windows."""
        for window in self._windows:
            self.clear_window(window)

    def get_stats(self) -> dict:
        """Get statistics about the aggregator state."""
        return {
            "windows": {
                window: {
                    "data_points": len(self._windows[window]),
                    "max_capacity": self.WINDOW_CONFIG[window][1],
                    "recent_averages": len(self._recent_averages[window]),
                }
                for window in self._windows
            },
            "source_weights": {k.value: v for k, v in self.SOURCE_WEIGHTS.items()},
        }
