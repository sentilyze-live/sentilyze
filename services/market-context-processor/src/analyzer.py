"""Anomaly detector for unified markets.

This module detects various anomalies in market data:
- Price-sentiment divergence
- Sudden price movements
- Volume anomalies
- Volatility spikes
- Support/resistance breakouts
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np

from sentilyze_core import get_logger

from .config import (
    AnomalySeverity,
    AnomalyType,
    MarketRegime,
    TrendDirection,
    VolatilityRegime,
    get_market_context_settings,
)

logger = get_logger(__name__)
settings = get_market_context_settings()


@dataclass
class AnomalyDetection:
    """Detected anomaly details."""
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    symbol: str
    timestamp: datetime
    description: str
    price_at_detection: float
    price_change_percent: float
    sentiment_score: Optional[float] = None
    expected_sentiment: Optional[float] = None
    volume_ratio: Optional[float] = None
    z_score: Optional[float] = None
    recommendation: Optional[str] = None
    market_type: str = "generic"


class AnomalyDetector:
    """Detects market anomalies using statistical analysis.
    
    Detection methods:
    - Z-score for price movements (beyond 2 std dev)
    - Sentiment-price divergence correlation
    - Volume anomaly detection
    - Bollinger Band breakouts
    """
    
    def __init__(self):
        self.price_move_threshold = settings.anomaly_price_move_threshold
        self.volatility_threshold = settings.anomaly_volatility_threshold
        self.volume_threshold = settings.anomaly_volume_threshold
        self.lookback_periods = settings.anomaly_lookback_periods
        self.volatility_lookback = 14
    
    async def detect_anomalies(
        self,
        prices: list[float],
        sentiments: Optional[list[float]] = None,
        volumes: Optional[list[float]] = None,
        timestamps: Optional[list[datetime]] = None,
        symbol: str = "UNKNOWN",
        support_level: Optional[float] = None,
        resistance_level: Optional[float] = None,
        market_type: str = "generic",
    ) -> list[AnomalyDetection]:
        """Detect all types of anomalies in market data.
        
        Args:
            prices: List of prices (oldest first)
            sentiments: Optional list of sentiment scores
            volumes: Optional list of volume data
            timestamps: Optional list of timestamps
            symbol: Trading symbol
            support_level: Current support level
            resistance_level: Current resistance level
            market_type: Market type (crypto/gold/generic)
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        if len(prices) < self.lookback_periods:
            logger.warning(
                "Insufficient data for anomaly detection",
                symbol=symbol,
                data_points=len(prices),
            )
            return anomalies
        
        try:
            # 1. Detect sudden price movements
            price_anomalies = self._detect_price_anomalies(
                prices, symbol, timestamps, market_type
            )
            anomalies.extend(price_anomalies)
            
            # 2. Detect price-sentiment divergence
            if sentiments and len(sentiments) >= len(prices):
                divergence_anomalies = self._detect_sentiment_divergence(
                    prices, sentiments, symbol, timestamps, market_type
                )
                anomalies.extend(divergence_anomalies)
            
            # 3. Detect volume anomalies
            if volumes and len(volumes) >= self.lookback_periods:
                volume_anomalies = self._detect_volume_anomalies(
                    prices, volumes, symbol, timestamps, market_type
                )
                anomalies.extend(volume_anomalies)
            
            # 4. Detect support/resistance breaks
            if support_level or resistance_level:
                breakout_anomalies = self._detect_breakouts(
                    prices, support_level, resistance_level, symbol, timestamps, market_type
                )
                anomalies.extend(breakout_anomalies)
            
            # 5. Detect volatility spikes
            volatility_anomalies = self._detect_volatility_spikes(
                prices, symbol, timestamps, market_type
            )
            anomalies.extend(volatility_anomalies)
            
            # Sort by severity and timestamp
            severity_order = {
                AnomalySeverity.CRITICAL: 0,
                AnomalySeverity.HIGH: 1,
                AnomalySeverity.MEDIUM: 2,
                AnomalySeverity.LOW: 3,
            }
            anomalies.sort(key=lambda x: (severity_order[x.severity], x.timestamp), reverse=True)
            
            logger.info(
                "Anomaly detection completed",
                symbol=symbol,
                anomalies_found=len(anomalies),
                critical=sum(1 for a in anomalies if a.severity == AnomalySeverity.CRITICAL),
                high=sum(1 for a in anomalies if a.severity == AnomalySeverity.HIGH),
            )
            
            return anomalies
            
        except Exception as e:
            logger.error(
                "Anomaly detection failed",
                symbol=symbol,
                error=str(e),
            )
            return []
    
    def _detect_price_anomalies(
        self,
        prices: list[float],
        symbol: str,
        timestamps: Optional[list[datetime]] = None,
        market_type: str = "generic",
    ) -> list[AnomalyDetection]:
        """Detect sudden price movements using Z-score."""
        anomalies = []
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] * 100 
                   for i in range(1, len(prices))]
        
        if len(returns) < self.lookback_periods:
            return anomalies
        
        # Calculate rolling statistics
        for i in range(self.lookback_periods, len(returns)):
            recent_returns = returns[i-self.lookback_periods:i]
            mean_return = sum(recent_returns) / len(recent_returns)
            std_return = (sum((r - mean_return) ** 2 for r in recent_returns) / len(recent_returns)) ** 0.5
            
            if std_return == 0:
                continue
            
            current_return = returns[i]
            z_score = (current_return - mean_return) / std_return
            
            # Check for significant moves
            if abs(z_score) > self.volatility_threshold:
                # Determine severity
                if abs(z_score) > 4.0:
                    severity = AnomalySeverity.CRITICAL
                elif abs(z_score) > 3.0:
                    severity = AnomalySeverity.HIGH
                elif abs(z_score) > 2.0:
                    severity = AnomalySeverity.MEDIUM
                else:
                    severity = AnomalySeverity.LOW
                
                # Determine type
                if z_score > 0:
                    if current_return > 2.0:
                        anomaly_type = AnomalyType.FLASH_PUMP
                        description = f"Flash pump detected: +{current_return:.2f}% in single period"
                        recommendation = "Consider taking profits if long"
                    else:
                        anomaly_type = AnomalyType.SUDDEN_PRICE_MOVE
                        description = f"Sudden upward move: +{current_return:.2f}%"
                        recommendation = "Monitor for continuation"
                else:
                    if current_return < -2.0:
                        anomaly_type = AnomalyType.FLASH_CRASH
                        description = f"Flash crash detected: {current_return:.2f}% in single period"
                        recommendation = "Consider buying dip if support holds"
                    else:
                        anomaly_type = AnomalyType.SUDDEN_PRICE_MOVE
                        description = f"Sudden downward move: {current_return:.2f}%"
                        recommendation = "Monitor for breakdown"
                
                timestamp = timestamps[i+1] if timestamps and i+1 < len(timestamps) else datetime.utcnow()
                
                anomaly = AnomalyDetection(
                    anomaly_type=anomaly_type,
                    severity=severity,
                    symbol=symbol,
                    timestamp=timestamp,
                    description=description,
                    price_at_detection=prices[i+1],
                    price_change_percent=current_return,
                    z_score=z_score,
                    recommendation=recommendation,
                    market_type=market_type,
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_sentiment_divergence(
        self,
        prices: list[float],
        sentiments: list[float],
        symbol: str,
        timestamps: Optional[list[datetime]] = None,
        market_type: str = "generic",
    ) -> list[AnomalyDetection]:
        """Detect price-sentiment divergence."""
        anomalies = []
        
        if len(prices) != len(sentiments):
            logger.warning(
                "Price and sentiment length mismatch",
                prices_len=len(prices),
                sentiments_len=len(sentiments),
            )
            return anomalies
        
        for i in range(1, min(len(prices), len(sentiments))):
            price_change = ((prices[i] - prices[i-1]) / prices[i-1]) * 100
            sentiment_change = sentiments[i] - sentiments[i-1]
            
            if abs(price_change) > 0.3:  # Significant price move
                # Bearish divergence: Price up, sentiment down
                if price_change > 0 and sentiment_change < -0.1:
                    if abs(price_change) > 1.0 and sentiment_change < -0.2:
                        severity = AnomalySeverity.HIGH
                    else:
                        severity = AnomalySeverity.MEDIUM
                    
                    timestamp = timestamps[i] if timestamps and i < len(timestamps) else datetime.utcnow()
                    
                    anomaly = AnomalyDetection(
                        anomaly_type=AnomalyType.PRICE_SENTIMENT_DIVERGENCE,
                        severity=severity,
                        symbol=symbol,
                        timestamp=timestamp,
                        description=f"Bearish divergence: Price +{price_change:.2f}% but sentiment dropped {sentiment_change:.2f}",
                        price_at_detection=prices[i],
                        price_change_percent=price_change,
                        sentiment_score=sentiments[i],
                        expected_sentiment=sentiments[i-1] + (price_change / 100),
                        recommendation="Caution: Price rising on weak sentiment, potential reversal",
                        market_type=market_type,
                    )
                    anomalies.append(anomaly)
                
                # Bullish divergence: Price down, sentiment up
                elif price_change < 0 and sentiment_change > 0.1:
                    if abs(price_change) > 1.0 and sentiment_change > 0.2:
                        severity = AnomalySeverity.HIGH
                    else:
                        severity = AnomalySeverity.MEDIUM
                    
                    timestamp = timestamps[i] if timestamps and i < len(timestamps) else datetime.utcnow()
                    
                    anomaly = AnomalyDetection(
                        anomaly_type=AnomalyType.PRICE_SENTIMENT_DIVERGENCE,
                        severity=severity,
                        symbol=symbol,
                        timestamp=timestamp,
                        description=f"Bullish divergence: Price {price_change:.2f}% but sentiment rose +{sentiment_change:.2f}",
                        price_at_detection=prices[i],
                        price_change_percent=price_change,
                        sentiment_score=sentiments[i],
                        expected_sentiment=sentiments[i-1] - (abs(price_change) / 100),
                        recommendation="Opportunity: Price falling on improving sentiment, potential bottom",
                        market_type=market_type,
                    )
                    anomalies.append(anomaly)
        
        return anomalies


# =============================================================================
# Regime Detection
# =============================================================================


@dataclass
class RegimeDetectionResult:
    symbol: str
    market_type: str
    regime: MarketRegime
    trend_direction: TrendDirection
    volatility_regime: VolatilityRegime
    confidence: float
    rsi_14: Optional[float]
    sma_50: Optional[float]
    sma_200: Optional[float]
    ema_20: Optional[float]
    price: float
    support_level: Optional[float]
    resistance_level: Optional[float]
    trend_strength: Optional[float]
    volume_trend: Optional[float]
    timestamp: datetime


class RegimeDetector:
    """Detect market regime and trend/volatility summary from price (and optional volume) series."""

    def __init__(self) -> None:
        # Reasonable defaults; can be made configurable later
        self.rsi_period = 14
        self.ema_period = 20
        self.support_resistance_lookback = 50
        self.vol_lookback = 30

    async def detect_regime(
        self,
        prices: list[float],
        volumes: Optional[list[float]] = None,
        symbol: str = "UNKNOWN",
        market_type: str = "generic",
    ) -> RegimeDetectionResult:
        if not prices or len(prices) < 5:
            raise ValueError("Not enough price data to detect regime")

        arr = np.asarray(prices, dtype=float)
        current_price = float(arr[-1])

        sma_50 = float(np.mean(arr[-50:])) if len(arr) >= 50 else None
        sma_200 = float(np.mean(arr[-200:])) if len(arr) >= 200 else None

        # EMA(20)
        ema_20 = None
        if len(arr) >= self.ema_period:
            alpha = 2.0 / (self.ema_period + 1.0)
            ema = float(arr[0])
            for p in arr[1:]:
                ema = alpha * float(p) + (1.0 - alpha) * ema
            ema_20 = float(ema)

        # RSI(14)
        rsi_14 = None
        if len(arr) >= self.rsi_period + 1:
            deltas = np.diff(arr)
            gains = np.where(deltas > 0, deltas, 0.0)
            losses = np.where(deltas < 0, -deltas, 0.0)
            avg_gain = float(np.mean(gains[-self.rsi_period:]))
            avg_loss = float(np.mean(losses[-self.rsi_period:]))
            if avg_loss == 0:
                rsi_14 = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_14 = float(100.0 - (100.0 / (1.0 + rs)))

        # Volatility regime based on returns std
        returns = np.diff(arr) / arr[:-1]
        vol_window = returns[-self.vol_lookback:] if len(returns) >= self.vol_lookback else returns
        vol = float(np.std(vol_window)) if len(vol_window) > 0 else 0.0

        if vol < 0.01:
            volatility_regime = VolatilityRegime.LOW
        elif vol < 0.03:
            volatility_regime = VolatilityRegime.MEDIUM
        elif vol < 0.06:
            volatility_regime = VolatilityRegime.HIGH
        else:
            volatility_regime = VolatilityRegime.EXTREME

        # Trend direction: use SMA cross if available; else compare last vs mean
        if sma_50 is not None and sma_200 is not None:
            if sma_50 > sma_200 * 1.001:
                trend_direction = TrendDirection.UP
            elif sma_50 < sma_200 * 0.999:
                trend_direction = TrendDirection.DOWN
            else:
                trend_direction = TrendDirection.SIDEWAYS
        elif sma_50 is not None:
            if current_price > sma_50 * 1.001:
                trend_direction = TrendDirection.UP
            elif current_price < sma_50 * 0.999:
                trend_direction = TrendDirection.DOWN
            else:
                trend_direction = TrendDirection.SIDEWAYS
        else:
            # fallback: compare last 5 vs previous 5
            n = min(5, len(arr) // 2)
            recent = float(np.mean(arr[-n:]))
            prev = float(np.mean(arr[-2 * n : -n]))
            if recent > prev * 1.001:
                trend_direction = TrendDirection.UP
            elif recent < prev * 0.999:
                trend_direction = TrendDirection.DOWN
            else:
                trend_direction = TrendDirection.SIDEWAYS

        # Regime heuristic
        if volatility_regime in (VolatilityRegime.HIGH, VolatilityRegime.EXTREME):
            regime = MarketRegime.VOLATILE
        elif trend_direction == TrendDirection.UP:
            regime = MarketRegime.BULL
        elif trend_direction == TrendDirection.DOWN:
            regime = MarketRegime.BEAR
        else:
            regime = MarketRegime.NEUTRAL

        # Support/resistance from recent window
        lookback = min(self.support_resistance_lookback, len(arr))
        window = arr[-lookback:]
        support_level = float(np.min(window)) if lookback >= 5 else None
        resistance_level = float(np.max(window)) if lookback >= 5 else None

        # Trend strength: normalized distance to SMA50 if available
        trend_strength = None
        if sma_50 is not None and sma_50 != 0:
            trend_strength = float((current_price - sma_50) / sma_50)

        # Volume trend: last vs mean
        volume_trend = None
        if volumes and len(volumes) >= 5:
            v = np.asarray(volumes, dtype=float)
            recent_v = float(np.mean(v[-5:]))
            mean_v = float(np.mean(v))
            if mean_v > 0:
                volume_trend = float(recent_v / mean_v)

        # Confidence heuristic (0..1)
        confidence = 0.5
        if trend_strength is not None:
            confidence = float(min(1.0, 0.5 + min(abs(trend_strength) * 5.0, 0.5)))
        if volatility_regime in (VolatilityRegime.HIGH, VolatilityRegime.EXTREME):
            confidence = float(max(0.2, confidence - 0.2))

        return RegimeDetectionResult(
            symbol=symbol,
            market_type=market_type,
            regime=regime,
            trend_direction=trend_direction,
            volatility_regime=volatility_regime,
            confidence=confidence,
            rsi_14=rsi_14,
            sma_50=sma_50,
            sma_200=sma_200,
            ema_20=ema_20,
            price=current_price,
            support_level=support_level,
            resistance_level=resistance_level,
            trend_strength=trend_strength,
            volume_trend=volume_trend,
            timestamp=datetime.utcnow(),
        )
    
    def _detect_volume_anomalies(
        self,
        prices: list[float],
        volumes: list[float],
        symbol: str,
        timestamps: Optional[list[datetime]] = None,
        market_type: str = "generic",
    ) -> list[AnomalyDetection]:
        """Detect volume anomalies."""
        anomalies = []
        
        if len(volumes) < self.lookback_periods:
            return anomalies
        
        for i in range(self.lookback_periods, len(volumes)):
            recent_volumes = volumes[i-self.lookback_periods:i]
            avg_volume = sum(recent_volumes) / len(recent_volumes)
            
            if avg_volume == 0:
                continue
            
            current_volume = volumes[i]
            volume_ratio = current_volume / avg_volume
            
            if volume_ratio > self.volume_threshold:
                price_change = ((prices[i] - prices[i-1]) / prices[i-1]) * 100 if i > 0 else 0
                
                if volume_ratio > 5.0:
                    severity = AnomalySeverity.HIGH
                elif volume_ratio > 3.0:
                    severity = AnomalySeverity.MEDIUM
                else:
                    severity = AnomalySeverity.LOW
                
                timestamp = timestamps[i] if timestamps and i < len(timestamps) else datetime.utcnow()
                
                anomaly = AnomalyDetection(
                    anomaly_type=AnomalyType.VOLUME_SPIKE,
                    severity=severity,
                    symbol=symbol,
                    timestamp=timestamp,
                    description=f"Volume spike: {volume_ratio:.1f}x average",
                    price_at_detection=prices[i],
                    price_change_percent=price_change,
                    volume_ratio=volume_ratio,
                    recommendation="High volume indicates strong conviction in move" if abs(price_change) > 0.5 else "Watch for breakout confirmation",
                    market_type=market_type,
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_breakouts(
        self,
        prices: list[float],
        support: Optional[float],
        resistance: Optional[float],
        symbol: str,
        timestamps: Optional[list[datetime]] = None,
        market_type: str = "generic",
    ) -> list[AnomalyDetection]:
        """Detect support/resistance breakouts."""
        anomalies = []
        
        if len(prices) < 2:
            return anomalies
        
        current_price = prices[-1]
        previous_price = prices[-2]
        
        # Support break (bearish)
        if support:
            buffer = support * 0.002
            if previous_price > support + buffer and current_price < support - buffer:
                timestamp = timestamps[-1] if timestamps else datetime.utcnow()
                
                anomaly = AnomalyDetection(
                    anomaly_type=AnomalyType.SUPPORT_BREAK,
                    severity=AnomalySeverity.HIGH,
                    symbol=symbol,
                    timestamp=timestamp,
                    description=f"Support break: Price fell through {support:.2f} support to {current_price:.2f}",
                    price_at_detection=current_price,
                    price_change_percent=((current_price - previous_price) / previous_price) * 100,
                    recommendation="Bearish signal: Consider reducing exposure or shorting",
                    market_type=market_type,
                )
                anomalies.append(anomaly)
        
        # Resistance break (bullish)
        if resistance:
            buffer = resistance * 0.002
            if previous_price < resistance - buffer and current_price > resistance + buffer:
                timestamp = timestamps[-1] if timestamps else datetime.utcnow()
                
                anomaly = AnomalyDetection(
                    anomaly_type=AnomalyType.RESISTANCE_BREAK,
                    severity=AnomalySeverity.HIGH,
                    symbol=symbol,
                    timestamp=timestamp,
                    description=f"Resistance break: Price broke above {resistance:.2f} to {current_price:.2f}",
                    price_at_detection=current_price,
                    price_change_percent=((current_price - previous_price) / previous_price) * 100,
                    recommendation="Bullish signal: Consider adding to position",
                    market_type=market_type,
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_volatility_spikes(
        self,
        prices: list[float],
        symbol: str,
        timestamps: Optional[list[datetime]] = None,
        market_type: str = "generic",
    ) -> list[AnomalyDetection]:
        """Detect unusual volatility using ATR."""
        anomalies = []
        
        if len(prices) < self.volatility_lookback * 2:
            return anomalies
        
        # Calculate ATR
        atr_values = []
        for i in range(1, len(prices)):
            true_range = abs(prices[i] - prices[i-1])
            atr_values.append(true_range)
        
        for i in range(self.volatility_lookback, len(atr_values)):
            recent_atr = sum(atr_values[i-self.volatility_lookback:i]) / self.volatility_lookback
            current_tr = atr_values[i]
            
            if recent_atr == 0:
                continue
            
            volatility_ratio = current_tr / recent_atr
            
            if volatility_ratio > 2.5:
                if volatility_ratio > 4.0:
                    severity = AnomalySeverity.HIGH
                else:
                    severity = AnomalySeverity.MEDIUM
                
                timestamp = timestamps[i+1] if timestamps and i+1 < len(timestamps) else datetime.utcnow()
                price_change = ((prices[i+1] - prices[i]) / prices[i]) * 100 if i+1 < len(prices) else 0
                
                anomaly = AnomalyDetection(
                    anomaly_type=AnomalyType.VOLATILITY_SPIKE,
                    severity=severity,
                    symbol=symbol,
                    timestamp=timestamp,
                    description=f"Volatility spike: {volatility_ratio:.1f}x normal range",
                    price_at_detection=prices[i+1] if i+1 < len(prices) else prices[i],
                    price_change_percent=price_change,
                    recommendation="High volatility - widen stops and reduce position size",
                    market_type=market_type,
                )
                anomalies.append(anomaly)
        
        return anomalies
