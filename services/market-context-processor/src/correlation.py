"""Correlation analyzer for unified markets.

This module calculates correlations between assets and implements
Granger causality testing for sentiment-price relationships.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np

from sentilyze_core import get_logger
from sentilyze_core.exceptions import ExternalServiceError

from .config import CorrelationStrength, get_market_context_settings

logger = get_logger(__name__)
settings = get_market_context_settings()


@dataclass
class CorrelationResult:
    """Correlation analysis result."""
    primary_symbol: str
    secondary_symbol: str
    correlation: float
    correlation_strength: CorrelationStrength
    period_days: int
    sample_size: int
    p_value: Optional[float] = None
    rolling_correlations: Optional[list[dict]] = None
    lag_analysis: Optional[dict] = None
    interpretation: str = ""
    timestamp: datetime = None
    market_type: str = "generic"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class GrangerCausalityResult:
    """Granger causality test result."""
    cause_variable: str
    effect_variable: str
    lag_hours: int
    f_statistic: float
    p_value: float
    is_causal: bool
    interpretation: str
    timestamp: datetime = None
    market_type: str = "generic"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class CorrelationAnalyzer:
    """Analyzes correlations between assets.
    
    Uses Pearson correlation coefficient and rolling window analysis.
    Also implements Granger causality for sentiment-price relationship.
    """
    
    def __init__(self):
        self.min_sample_size = settings.correlation_min_sample_size
        self.default_period_days = settings.correlation_default_period_days
        self.rolling_window = settings.correlation_rolling_window
    
    async def calculate_correlation(
        self,
        primary_prices: list[float],
        secondary_prices: list[float],
        primary_symbol: str = "PRIMARY",
        secondary_symbol: str = "SECONDARY",
        period_days: int = 30,
        calculate_lag: bool = True,
        market_type: str = "generic",
    ) -> CorrelationResult:
        """Calculate correlation between two price series."""
        if len(primary_prices) != len(secondary_prices):
            raise ExternalServiceError(
                "Price series must have same length",
                service="correlation_analyzer",
            )
        
        if len(primary_prices) < self.min_sample_size:
            logger.warning(
                "Insufficient data for correlation",
                primary=primary_symbol,
                secondary=secondary_symbol,
                samples=len(primary_prices),
                required=self.min_sample_size,
            )
            return self._create_insufficient_data_result(
                primary_symbol, secondary_symbol, period_days, market_type
            )
        
        try:
            correlation = self._pearson_correlation(primary_prices, secondary_prices)
            strength = self._classify_correlation_strength(correlation)
            
            rolling = self._calculate_rolling_correlation(
                primary_prices, secondary_prices, window=self.rolling_window
            )
            
            lag_analysis = None
            if calculate_lag:
                lag_analysis = self._analyze_lead_lag(
                    primary_prices, secondary_prices, max_lag=5
                )
            
            interpretation = self._generate_interpretation(
                primary_symbol, secondary_symbol, correlation, strength, lag_analysis
            )
            
            return CorrelationResult(
                primary_symbol=primary_symbol,
                secondary_symbol=secondary_symbol,
                correlation=correlation,
                correlation_strength=strength,
                period_days=period_days,
                sample_size=len(primary_prices),
                rolling_correlations=rolling,
                lag_analysis=lag_analysis,
                interpretation=interpretation,
                market_type=market_type,
            )
            
        except Exception as e:
            logger.error(
                "Correlation calculation failed",
                primary=primary_symbol,
                secondary=secondary_symbol,
                error=str(e),
            )
            raise ExternalServiceError(
                f"Correlation calculation failed: {e}",
                service="correlation_analyzer",
            ) from e
    
    async def analyze_sentiment_price_causality(
        self,
        prices: list[float],
        sentiments: list[float],
        symbol: str = "UNKNOWN",
        max_lag_hours: int = 24,
        market_type: str = "generic",
    ) -> GrangerCausalityResult:
        """Test if sentiment Granger-causes price movements."""
        if len(prices) != len(sentiments):
            raise ExternalServiceError(
                "Price and sentiment series must have same length",
                service="correlation_analyzer",
            )
        
        if len(prices) < self.min_sample_size:
            return GrangerCausalityResult(
                cause_variable="sentiment",
                effect_variable=f"{symbol}_price",
                lag_hours=0,
                f_statistic=0.0,
                p_value=1.0,
                is_causal=False,
                interpretation="Insufficient data for causality test",
                market_type=market_type,
            )
        
        try:
            best_lag = 0
            best_f_stat = 0.0
            best_p_value = 1.0
            
            price_changes = [
                (prices[i] - prices[i-1]) / prices[i-1] * 100
                for i in range(1, len(prices))
            ]
            
            for lag in range(1, min(max_lag_hours + 1, len(price_changes) // 4)):
                if lag >= len(sentiments):
                    break
                
                f_stat, p_value = self._simple_f_test(
                    price_changes[lag:],
                    sentiments[:-lag],
                )
                
                if p_value < best_p_value and f_stat > best_f_stat:
                    best_p_value = p_value
                    best_f_stat = f_stat
                    best_lag = lag
            
            is_causal = best_p_value < 0.05 and best_f_stat > 2.0
            
            if is_causal:
                interpretation = (
                    f"Sentiment Granger-causes {symbol} price movements "
                    f"with a {best_lag} hour lag. "
                    f"Sentiment changes precede price changes, suggesting "
                    f"predictive value for trading strategies."
                )
            else:
                interpretation = (
                    f"No significant Granger causality detected between sentiment "
                    f"and {symbol} price at any lag up to {max_lag_hours} hours. "
                    f"Price movements may be driven by other factors."
                )
            
            return GrangerCausalityResult(
                cause_variable="sentiment",
                effect_variable=f"{symbol}_price",
                lag_hours=best_lag,
                f_statistic=best_f_stat,
                p_value=best_p_value,
                is_causal=is_causal,
                interpretation=interpretation,
                market_type=market_type,
            )
            
        except Exception as e:
            logger.error(
                "Causality test failed",
                symbol=symbol,
                error=str(e),
            )
            return GrangerCausalityResult(
                cause_variable="sentiment",
                effect_variable=f"{symbol}_price",
                lag_hours=0,
                f_statistic=0.0,
                p_value=1.0,
                is_causal=False,
                interpretation=f"Test failed: {str(e)}",
                market_type=market_type,
            )
    
    def _pearson_correlation(self, x: list[float], y: list[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        n = len(x)
        if n != len(y) or n == 0:
            return 0.0
        
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        sum_sq_x = sum((xi - mean_x) ** 2 for xi in x)
        sum_sq_y = sum((yi - mean_y) ** 2 for yi in y)
        
        denominator = (sum_sq_x * sum_sq_y) ** 0.5
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _classify_correlation_strength(self, correlation: float) -> CorrelationStrength:
        """Classify correlation strength."""
        abs_corr = abs(correlation)
        
        if abs_corr >= 0.8:
            if correlation > 0:
                return CorrelationStrength.VERY_STRONG_POSITIVE
            else:
                return CorrelationStrength.VERY_STRONG_NEGATIVE
        elif abs_corr >= 0.6:
            if correlation > 0:
                return CorrelationStrength.STRONG_POSITIVE
            else:
                return CorrelationStrength.STRONG_NEGATIVE
        elif abs_corr >= 0.4:
            if correlation > 0:
                return CorrelationStrength.MODERATE_POSITIVE
            else:
                return CorrelationStrength.MODERATE_NEGATIVE
        else:
            return CorrelationStrength.WEAK
    
    def _calculate_rolling_correlation(
        self,
        x: list[float],
        y: list[float],
        window: int = 10,
    ) -> list[dict]:
        """Calculate rolling correlation over time."""
        rolling = []
        
        for i in range(window, len(x)):
            window_x = x[i-window:i]
            window_y = y[i-window:i]
            
            corr = self._pearson_correlation(window_x, window_y)
            
            rolling.append({
                "index": i,
                "correlation": round(corr, 3),
                "timestamp": i,
            })
        
        return rolling
    
    def _analyze_lead_lag(
        self,
        x: list[float],
        y: list[float],
        max_lag: int = 5,
    ) -> dict:
        """Analyze lead-lag relationship between two series."""
        best_lag = 0
        best_correlation = 0.0
        
        correlations = {}
        
        for lag in range(-max_lag, max_lag + 1):
            if lag == 0:
                corr = self._pearson_correlation(x, y)
            elif lag > 0:
                corr = self._pearson_correlation(x[lag:], y[:-lag])
            else:
                lag_abs = abs(lag)
                corr = self._pearson_correlation(x[:-lag_abs], y[lag_abs:])
            
            correlations[lag] = round(corr, 3)
            
            if abs(corr) > abs(best_correlation):
                best_correlation = corr
                best_lag = lag
        
        if best_lag > 0:
            leader = "secondary"
            lagger = "primary"
        elif best_lag < 0:
            leader = "primary"
            lagger = "secondary"
        else:
            leader = "none"
            lagger = "none"
        
        return {
            "optimal_lag": best_lag,
            "optimal_correlation": round(best_correlation, 3),
            "leader": leader,
            "lagger": lagger,
            "all_correlations": correlations,
        }
    
    def _simple_f_test(
        self,
        dependent: list[float],
        independent: list[float],
    ) -> tuple[float, float]:
        """Simple F-test for Granger causality."""
        n = len(dependent)
        
        if n < 3 or len(independent) != n:
            return 0.0, 1.0
        
        mean_dep = sum(dependent) / n
        mean_ind = sum(independent) / n
        
        numerator = sum((independent[i] - mean_ind) * (dependent[i] - mean_dep) for i in range(n))
        denominator = sum((independent[i] - mean_ind) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0, 1.0
        
        slope = numerator / denominator
        intercept = mean_dep - slope * mean_ind
        
        predicted = [intercept + slope * independent[i] for i in range(n)]
        
        ss_res = sum((dependent[i] - predicted[i]) ** 2 for i in range(n))
        ss_tot = sum((dependent[i] - mean_dep) ** 2 for i in range(n))
        
        if ss_res == 0:
            return 999.0, 0.001
        
        ms_reg = (ss_tot - ss_res) / 1
        ms_res = ss_res / (n - 2)
        
        if ms_res == 0:
            return 999.0, 0.001
        
        f_stat = ms_reg / ms_res
        
        if f_stat > 10:
            p_value = 0.001
        elif f_stat > 5:
            p_value = 0.01
        elif f_stat > 2:
            p_value = 0.05
        else:
            p_value = 0.2
        
        return f_stat, p_value
    
    def _generate_interpretation(
        self,
        primary: str,
        secondary: str,
        correlation: float,
        strength: CorrelationStrength,
        lag_analysis: Optional[dict],
    ) -> str:
        """Generate human-readable interpretation."""
        parts = []
        
        if abs(correlation) > 0.7:
            parts.append(f"Strong {'positive' if correlation > 0 else 'negative'} correlation")
        elif abs(correlation) > 0.4:
            parts.append(f"Moderate {'positive' if correlation > 0 else 'negative'} correlation")
        else:
            parts.append("Weak correlation")
        
        parts.append(f"({correlation:.2f}) between {primary} and {secondary}")
        
        if lag_analysis and lag_analysis.get("optimal_lag", 0) != 0:
            lag = lag_analysis["optimal_lag"]
            if lag_analysis["leader"] == "secondary":
                parts.append(f"{secondary} leads {primary} by {abs(lag)} periods")
            else:
                parts.append(f"{primary} leads {secondary} by {abs(lag)} periods")
        
        return " ".join(parts)
    
    def _create_insufficient_data_result(
        self,
        primary: str,
        secondary: str,
        period_days: int,
        market_type: str,
    ) -> CorrelationResult:
        """Create result for insufficient data."""
        return CorrelationResult(
            primary_symbol=primary,
            secondary_symbol=secondary,
            correlation=0.0,
            correlation_strength=CorrelationStrength.WEAK,
            period_days=period_days,
            sample_size=0,
            interpretation=f"Insufficient data to calculate correlation between {primary} and {secondary}",
            market_type=market_type,
        )
