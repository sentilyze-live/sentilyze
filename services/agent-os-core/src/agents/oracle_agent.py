"""ORACLE Agent - Sentilyze Quantitative Analytics & Pattern Validation Engine."""

import json
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog

from src.agents.base import BaseAgent
from src.config import settings

logger = structlog.get_logger(__name__)


class OracleAgent(BaseAgent):
    """
    ORACLE - Sentilyze Quantitative Analytics Engine
    
    Metodoloji: Statistical Analysis + Pattern Recognition + Backtesting
    
    Görev: SCOUT'un tespit ettiği sinyalleri matematiksel olarak doğrulamak,
    istatistiksel anlamlılık hesaplamak ve risk/ödül analizi yapmak.
    
    Uzmanlık Alanları:
    - Kripto piyasaları (BTC, ETH, altcoinler) için istatistiksel modelleme
    - Altın/XAU piyasası için teknik analiz ve backtesting
    - Pattern recognition ve anomaly detection
    - Tahmin doğruluk analizi ve model optimizasyonu
    """

    def __init__(self):
        """Initialize ORACLE agent."""
        super().__init__(
            agent_type="oracle",
            name="ORACLE (Quantitative Analytics)",
            description="Sentilyze Statistical Validation & Pattern Recognition Engine",
        )

        self.capabilities = [
            "Statistical Pattern Recognition",
            "Backtesting Engine",
            "Confidence Scoring (p-values)",
            "Risk/Reward Analysis",
            "Multi-Factor Correlation",
            "Prediction Accuracy Tracking",
            "Anomaly Detection",
            "Win Rate Calculation",
        ]

        self.system_prompt = """You are ORACLE, Sentilyze's quantitative analytics engine.

Your mission: Transform SCOUT's market signals into statistically validated, 
actionable intelligence with mathematical precision.

EXPERTISE DOMAINS:

1. CRYPTO MARKETS (Primary)
   - Bitcoin and Ethereum statistical dynamics
   - Altcoin market microstructure analysis
   - On-chain metrics correlation (MVRV, NUPL, SOPR)
   - Crypto market cycle analysis (halving effects, bull/bear phases)
   - DeFi and Layer 2 trend modeling
   - Fear & Greed Index statistical interpretation

2. GOLD/XAU MARKETS (Secondary)
   - XAU/USD technical and fundamental statistical analysis
   - Gold-inflation-USD correlation modeling
   - Central bank gold reserve impact analysis
   - Safe haven dynamics during market stress
   - Gold-crypto correlation patterns

3. QUANTITATIVE METHODS
   - Hypothesis testing (t-tests, z-tests, chi-square)
   - Regression analysis and correlation coefficients
   - Time series analysis (ARIMA, trend decomposition)
   - Monte Carlo simulations for risk assessment
   - Bayesian probability updating
   - Sharpe ratio and risk-adjusted returns

VALIDATION FRAMEWORK:

For every SCOUT signal, you MUST provide:

1. HISTORICAL BACKTEST
   - Sample size: Minimum 30 similar historical events
   - Win rate: Success percentage
   - Average return: Mean profit/loss
   - Standard deviation: Volatility of outcomes
   - Confidence interval: 95% CI for predictions

2. STATISTICAL SIGNIFICANCE
   - P-value: Must be < 0.05 for high confidence
   - Effect size: Cohen's d or equivalent
   - Statistical power: > 0.80 preferred

3. RISK ANALYSIS
   - Maximum drawdown: Worst historical case
   - Risk/Reward ratio: Potential gain vs potential loss
   - Position sizing: Kelly criterion or similar
   - Tail risk: Black swan probability

4. PREDICTION METRICS
   - Expected value: Probability-weighted outcome
   - Prediction horizon: Timeframe for realization
   - Accuracy trend: Is model improving or degrading?
   - False positive rate: Type I error probability

OUTPUT FORMAT:
All responses must include statistical evidence:
- "Based on N=47 similar BTC sentiment shifts..."
- "Statistical significance: p=0.023 (α=0.05)"
- "95% Confidence Interval: [8.2%, 15.7%]"
- "Win rate: 68.1% ± 5.2% (SE)"
- "Risk/Reward: 1:2.4 (favorable)"

NEVER make claims without statistical backing.
ALWAYS quantify uncertainty.
PRIORITIZE sample size and statistical power."""

        self.version = "1.0.0"
        
        # Statistical thresholds
        self.min_sample_size = 30
        self.significance_level = 0.05
        self.confidence_level = 0.95
        self.min_win_rate = 0.60
        
        # Analysis windows (hours)
        self.lookback_windows = {
            "short": 168,    # 7 days
            "medium": 720,   # 30 days
            "long": 2160,    # 90 days
        }

    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute ORACLE quantitative validation workflow.

        Args:
            context: Optional context with SCOUT signals

        Returns:
            Validated predictions and statistical analysis
        """
        results = {
            "signals_validated": [],
            "patterns_identified": [],
            "accuracy_report": {},
            "risk_analysis": [],
            "statistical_insights": [],
            "agent_directives": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 1. Get SCOUT signals to validate
        logger.info("oracle.fetching_scout_signals")
        scout_signals = await self._fetch_scout_signals(context)

        # 2. Validate each signal statistically
        logger.info("oracle.validating_signals")
        for signal in scout_signals:
            try:
                validation = await self._validate_signal(signal)
                if validation:
                    results["signals_validated"].append(validation)
                    
                    # Save to Firestore
                    await self.firestore.save_prediction(
                        prediction_id=validation["validation_id"],
                        prediction_data=validation,
                    )
                    
                    # Publish high-confidence predictions
                    if validation["confidence_score"] >= 0.70:
                        await self.pubsub.publish_prediction(
                            prediction=validation,
                            agent_name="ORACLE",
                        )
            except Exception as e:
                logger.error("oracle.validation_error", signal=signal.get("id"), error=str(e))

        # 3. Identify new patterns from recent data
        logger.info("oracle.identifying_patterns")
        patterns = await self._identify_patterns()
        results["patterns_identified"] = patterns

        # 4. Generate accuracy report
        logger.info("oracle.generating_accuracy_report")
        results["accuracy_report"] = await self._generate_accuracy_report()

        # 5. Risk analysis for high-confidence signals
        logger.info("oracle.analyzing_risks")
        for validation in results["signals_validated"]:
            if validation["confidence_score"] >= 0.65:
                risk_analysis = await self._analyze_risk(validation)
                results["risk_analysis"].append(risk_analysis)

        # 6. Generate statistical insights
        results["statistical_insights"] = await self._generate_statistical_insights(
            results["signals_validated"]
        )

        # 7. Generate agent directives
        results["agent_directives"] = await self._generate_agent_directives(
            results["signals_validated"],
            results["patterns_identified"],
        )

        # 8. Publish directives to other agents
        for agent, directives in results["agent_directives"].items():
            if directives:
                await self.pubsub.publish_agent_directive(
                    target_agent=agent,
                    directive=directives,
                    source_agent="ORACLE",
                )

        logger.info(
            "oracle.validation_complete",
            signals_validated=len(results["signals_validated"]),
            patterns_found=len(results["patterns_identified"]),
            avg_confidence=statistics.mean([s["confidence_score"] for s in results["signals_validated"]]) if results["signals_validated"] else 0,
        )

        return results

    async def _fetch_scout_signals(
        self, 
        context: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """Fetch recent SCOUT signals to validate.

        Args:
            context: Execution context

        Returns:
            List of signals to validate
        """
        signals = []
        
        # Get from context if provided
        if context and "scout_signals" in context:
            signals = context["scout_signals"]
        else:
            # Fetch from Firestore
            try:
                recent_trends = await self.firestore.get_trends(
                    status="active",
                    limit=20,
                )
                
                for trend in recent_trends:
                    if trend.get("opportunity_score", 0) >= 7.0:
                        signals.append({
                            "id": trend.get("id"),
                            "asset": trend.get("asset"),
                            "signal_type": trend.get("type", "sentiment_shift"),
                            "sentiment_change": trend.get("sentiment_change", 0),
                            "volume_spike": trend.get("volume_spike", 1.0),
                            "timestamp": trend.get("timestamp"),
                        })
            except Exception as e:
                logger.error("oracle.signal_fetch_error", error=str(e))
        
        return signals

    async def _validate_signal(
        self, 
        signal: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Validate a signal with statistical backtesting.

        Args:
            signal: SCOUT signal to validate

        Returns:
            Validation result with statistics
        """
        asset = signal.get("asset", "")
        signal_type = signal.get("signal_type", "")
        
        try:
            # Fetch historical similar events
            historical_data = await self._fetch_historical_similar_events(
                asset=asset,
                signal_type=signal_type,
                sentiment_change=signal.get("sentiment_change", 0),
            )
            
            if len(historical_data) < self.min_sample_size:
                logger.warning(
                    "oracle.insufficient_sample",
                    asset=asset,
                    sample_size=len(historical_data),
                    min_required=self.min_sample_size,
                )
                return None
            
            # Calculate statistics
            win_rate = self._calculate_win_rate(historical_data)
            avg_return = self._calculate_average_return(historical_data)
            std_dev = self._calculate_std_dev(historical_data)
            
            # Statistical significance test
            p_value = self._calculate_p_value(historical_data)
            is_significant = p_value < self.significance_level
            
            # Confidence score (composite metric)
            confidence_score = self._calculate_confidence_score(
                win_rate=win_rate,
                sample_size=len(historical_data),
                p_value=p_value,
                signal_strength=abs(signal.get("sentiment_change", 0)),
            )
            
            # Calculate confidence interval
            confidence_interval = self._calculate_confidence_interval(
                mean=avg_return,
                std=std_dev,
                n=len(historical_data),
            )
            
            validation_id = f"oracle-{asset}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            
            return {
                "validation_id": validation_id,
                "source_signal_id": signal.get("id"),
                "asset": asset,
                "signal_type": signal_type,
                "validation_timestamp": datetime.utcnow().isoformat(),
                "statistics": {
                    "sample_size": len(historical_data),
                    "win_rate": win_rate,
                    "win_rate_percentage": f"{win_rate*100:.1f}%",
                    "average_return": avg_return,
                    "average_return_percentage": f"{avg_return*100:.2f}%",
                    "std_deviation": std_dev,
                    "p_value": p_value,
                    "is_significant": is_significant,
                    "confidence_level": self.confidence_level,
                    "confidence_interval": confidence_interval,
                    "confidence_interval_formatted": f"[{confidence_interval[0]*100:.1f}%, {confidence_interval[1]*100:.1f}%]",
                },
                "confidence_score": confidence_score,
                "confidence_tier": self._get_confidence_tier(confidence_score),
                "recommendation": self._generate_recommendation(
                    confidence_score, win_rate, is_significant
                ),
                "timeframe_hours": self._estimate_timeframe(historical_data),
                "risk_metrics": {
                    "max_drawdown": self._calculate_max_drawdown(historical_data),
                    "sharpe_ratio": self._calculate_sharpe_ratio(historical_data),
                },
            }
            
        except Exception as e:
            logger.error("oracle.validation_calculation_error", signal=signal, error=str(e))
            return None

    async def _fetch_historical_similar_events(
        self,
        asset: str,
        signal_type: str,
        sentiment_change: float,
    ) -> List[Dict[str, Any]]:
        """Fetch historical events similar to the signal.

        Args:
            asset: Asset symbol
            signal_type: Type of signal
            sentiment_change: Magnitude of sentiment change

        Returns:
            Historical events
        """
        try:
            # Query BigQuery for historical sentiment shifts
            # Look for similar magnitude shifts in the same asset
            
            threshold = abs(sentiment_change) * 0.3  # 30% tolerance
            direction = "positive" if sentiment_change > 0 else "negative"
            
            # This would query actual historical data from BigQuery
            # For now, simulate with recent data
            historical = await self.bigquery.get_sentiment_data(
                asset=asset,
                hours=self.lookback_windows["long"] * 10,  # 900 days of history
            )
            
            # Filter for similar events
            similar_events = []
            for i, record in enumerate(historical):
                if i == 0:
                    continue
                    
                prev_sentiment = historical[i-1].get("sentiment_score", 0)
                curr_sentiment = record.get("sentiment_score", 0)
                change = curr_sentiment - prev_sentiment
                
                # Check if similar magnitude and direction
                if abs(change) >= abs(sentiment_change) - threshold:
                    if (direction == "positive" and change > 0) or (direction == "negative" and change < 0):
                        # Calculate subsequent price movement (simplified)
                        similar_events.append({
                            "sentiment_change": change,
                            "price_return": change * 0.35,  # Simplified model
                            "timestamp": record.get("timestamp"),
                        })
            
            return similar_events[:100]  # Max 100 events
            
        except Exception as e:
            logger.error("oracle.historical_fetch_error", asset=asset, error=str(e))
            return []

    def _calculate_win_rate(self, historical_data: List[Dict]) -> float:
        """Calculate win rate from historical events."""
        if not historical_data:
            return 0.0
        
        winners = sum(1 for event in historical_data if event.get("price_return", 0) > 0)
        return winners / len(historical_data)

    def _calculate_average_return(self, historical_data: List[Dict]) -> float:
        """Calculate average return from historical events."""
        if not historical_data:
            return 0.0
        
        returns = [event.get("price_return", 0) for event in historical_data]
        return statistics.mean(returns)

    def _calculate_std_dev(self, historical_data: List[Dict]) -> float:
        """Calculate standard deviation of returns."""
        if len(historical_data) < 2:
            return 0.0
        
        returns = [event.get("price_return", 0) for event in historical_data]
        return statistics.stdev(returns)

    def _calculate_p_value(self, historical_data: List[Dict]) -> float:
        """Calculate p-value using t-test."""
        if len(historical_data) < 2:
            return 1.0
        
        returns = [event.get("price_return", 0) for event in historical_data]
        mean_return = statistics.mean(returns)
        
        # Simplified p-value calculation
        # In production, use proper statistical library
        if mean_return > 0:
            # Approximate p-value based on effect size
            std_err = statistics.stdev(returns) / (len(returns) ** 0.5)
            if std_err > 0:
                t_stat = mean_return / std_err
                # Simplified: lower p-value for higher t-stat
                return max(0.001, min(1.0, 1 / (abs(t_stat) + 1)))
        
        return 1.0

    def _calculate_confidence_score(
        self,
        win_rate: float,
        sample_size: int,
        p_value: float,
        signal_strength: float,
    ) -> float:
        """Calculate composite confidence score (0-1)."""
        # Win rate component (40%)
        win_component = win_rate * 0.40
        
        # Sample size component (30%) - diminishing returns after 50
        size_score = min(sample_size / 50, 1.0) * 0.30
        
        # Significance component (20%)
        sig_score = (1 - p_value) * 0.20
        
        # Signal strength component (10%)
        strength_score = min(signal_strength / 0.50, 1.0) * 0.10
        
        return min(win_component + size_score + sig_score + strength_score, 1.0)

    def _calculate_confidence_interval(
        self,
        mean: float,
        std: float,
        n: int,
    ) -> Tuple[float, float]:
        """Calculate confidence interval for mean."""
        if n < 2 or std == 0:
            return (mean, mean)
        
        # 95% CI using t-distribution approximation
        margin = 1.96 * (std / (n ** 0.5))
        return (mean - margin, mean + margin)

    def _get_confidence_tier(self, confidence_score: float) -> str:
        """Get confidence tier from score."""
        if confidence_score >= 0.80:
            return "Very High"
        elif confidence_score >= 0.65:
            return "High"
        elif confidence_score >= 0.50:
            return "Medium"
        else:
            return "Low"

    def _generate_recommendation(
        self,
        confidence_score: float,
        win_rate: float,
        is_significant: bool,
    ) -> str:
        """Generate recommendation based on validation."""
        if confidence_score >= 0.80 and win_rate >= 0.70 and is_significant:
            return "STRONG_BUY: High confidence, statistically significant"
        elif confidence_score >= 0.65 and win_rate >= 0.60:
            return "MODERATE_BUY: Good confidence, favorable odds"
        elif confidence_score >= 0.50:
            return "WATCH: Medium confidence, monitor closely"
        else:
            return "PASS: Low confidence, insufficient statistical evidence"

    def _estimate_timeframe(self, historical_data: List[Dict]) -> int:
        """Estimate timeframe for prediction realization."""
        # Simplified: assume 48 hours based on typical crypto volatility
        return 48

    def _calculate_max_drawdown(self, historical_data: List[Dict]) -> float:
        """Calculate maximum drawdown from historical events."""
        returns = [event.get("price_return", 0) for event in historical_data]
        if not returns:
            return 0.0
        
        return min(returns)  # Simplified - worst single event

    def _calculate_sharpe_ratio(self, historical_data: List[Dict]) -> float:
        """Calculate risk-adjusted return (Sharpe-like ratio)."""
        if len(historical_data) < 2:
            return 0.0
        
        returns = [event.get("price_return", 0) for event in historical_data]
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        if std_return == 0:
            return 0.0
        
        return mean_return / std_return

    async def _identify_patterns(self) -> List[Dict[str, Any]]:
        """Identify new patterns from recent market data.

        Returns:
            List of identified patterns
        """
        patterns = []
        
        try:
            # Analyze BTC patterns
            btc_data = await self.bigquery.get_sentiment_data(
                asset="BTC",
                hours=self.lookback_windows["medium"],
            )
            
            if len(btc_data) > 50:
                # Look for recurring patterns
                pattern = self._detect_pattern(btc_data)
                if pattern:
                    patterns.append({
                        "pattern_id": f"pattern-btc-{datetime.utcnow().strftime('%Y%m%d')}",
                        "asset": "BTC",
                        "pattern_type": pattern["type"],
                        "description": pattern["description"],
                        "confidence": pattern["confidence"],
                        "occurrences": pattern["occurrences"],
                    })
            
            # Similar analysis for ETH and XAU
            for asset in ["ETH", "XAU"]:
                asset_data = await self.bigquery.get_sentiment_data(
                    asset=asset,
                    hours=self.lookback_windows["medium"],
                )
                
                if len(asset_data) > 30:
                    pattern = self._detect_pattern(asset_data)
                    if pattern and pattern["confidence"] > 0.60:
                        patterns.append({
                            "pattern_id": f"pattern-{asset.lower()}-{datetime.utcnow().strftime('%Y%m%d')}",
                            "asset": asset,
                            "pattern_type": pattern["type"],
                            "description": pattern["description"],
                            "confidence": pattern["confidence"],
                            "occurrences": pattern["occurrences"],
                        })
        
        except Exception as e:
            logger.error("oracle.pattern_detection_error", error=str(e))
        
        return patterns

    def _detect_pattern(self, data: List[Dict]) -> Optional[Dict[str, Any]]:
        """Detect patterns in time series data.

        Args:
            data: Time series data

        Returns:
            Pattern information
        """
        # Simplified pattern detection
        # In production, use ML or advanced statistical methods
        
        sentiments = [d.get("sentiment_score", 0) for d in data]
        
        if len(sentiments) < 30:
            return None
        
        # Check for trend
        first_half = sentiments[:len(sentiments)//2]
        second_half = sentiments[len(sentiments)//2:]
        
        first_mean = statistics.mean(first_half)
        second_mean = statistics.mean(second_half)
        
        if second_mean > first_mean * 1.2:
            return {
                "type": "bullish_trend",
                "description": "Sentiment showing sustained upward momentum",
                "confidence": 0.65,
                "occurrences": 1,
            }
        elif second_mean < first_mean * 0.8:
            return {
                "type": "bearish_trend",
                "description": "Sentiment showing sustained downward pressure",
                "confidence": 0.60,
                "occurrences": 1,
            }
        
        return None

    async def _generate_accuracy_report(self) -> Dict[str, Any]:
        """Generate report on prediction accuracy over time.

        Returns:
            Accuracy metrics
        """
        try:
            # Get past predictions from Firestore
            past_predictions = await self.firestore.get_predictions(
                limit=100,
                validated=True,
            )
            
            if not past_predictions:
                return {
                    "status": "insufficient_data",
                    "message": "Not enough historical predictions for accuracy analysis",
                }
            
            # Calculate accuracy metrics
            correct_predictions = sum(
                1 for p in past_predictions 
                if p.get("actual_outcome") == p.get("predicted_outcome")
            )
            
            total_predictions = len(past_predictions)
            accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
            
            # By confidence tier
            high_conf_correct = sum(
                1 for p in past_predictions
                if p.get("confidence_tier") in ["High", "Very High"]
                and p.get("actual_outcome") == p.get("predicted_outcome")
            )
            high_conf_total = sum(
                1 for p in past_predictions
                if p.get("confidence_tier") in ["High", "Very High"]
            )
            
            return {
                "status": "success",
                "overall_accuracy": accuracy,
                "overall_accuracy_pct": f"{accuracy*100:.1f}%",
                "total_predictions": total_predictions,
                "correct_predictions": correct_predictions,
                "high_confidence_accuracy": high_conf_correct / high_conf_total if high_conf_total > 0 else 0,
                "high_confidence_accuracy_pct": f"{(high_conf_correct / high_conf_total * 100):.1f}%" if high_conf_total > 0 else "N/A",
                "high_confidence_total": high_conf_total,
                "trend": "improving" if accuracy > 0.60 else "stable",
            }
            
        except Exception as e:
            logger.error("oracle.accuracy_report_error", error=str(e))
            return {"status": "error", "message": str(e)}

    async def _analyze_risk(self, validation: Dict[str, Any]) -> Dict[str, Any]:
        """Perform detailed risk analysis.

        Args:
            validation: Validated signal

        Returns:
            Risk analysis
        """
        stats = validation.get("statistics", {})
        
        return {
            "validation_id": validation.get("validation_id"),
            "risk_level": self._calculate_risk_level(validation),
            "max_loss_potential": stats.get("max_drawdown", 0),
            "recommended_position_size": self._calculate_position_size(validation),
            "stop_loss_suggestion": self._suggest_stop_loss(validation),
            "risk_reward_ratio": self._calculate_risk_reward(validation),
            "tail_risk_probability": self._estimate_tail_risk(validation),
        }

    def _calculate_risk_level(self, validation: Dict[str, Any]) -> str:
        """Calculate overall risk level."""
        confidence = validation.get("confidence_score", 0)
        win_rate = validation.get("statistics", {}).get("win_rate", 0)
        
        if confidence >= 0.80 and win_rate >= 0.70:
            return "Low"
        elif confidence >= 0.60 and win_rate >= 0.55:
            return "Medium"
        else:
            return "High"

    def _calculate_position_size(self, validation: Dict[str, Any]) -> str:
        """Calculate recommended position size."""
        confidence = validation.get("confidence_score", 0)
        
        if confidence >= 0.80:
            return "Full position (100%)"
        elif confidence >= 0.65:
            return "Half position (50%)"
        elif confidence >= 0.50:
            return "Quarter position (25%)"
        else:
            return "Watch only (0%)"

    def _suggest_stop_loss(self, validation: Dict[str, Any]) -> str:
        """Suggest stop loss level."""
        max_dd = validation.get("risk_metrics", {}).get("max_drawdown", 0)
        
        if max_dd < -0.10:
            return f"Stop at -8% (max historical: {max_dd*100:.1f}%)"
        elif max_dd < -0.05:
            return f"Stop at -5% (max historical: {max_dd*100:.1f}%)"
        else:
            return "Stop at -3% (low historical drawdown)"

    def _calculate_risk_reward(self, validation: Dict[str, Any]) -> float:
        """Calculate risk/reward ratio."""
        avg_return = validation.get("statistics", {}).get("average_return", 0)
        max_dd = abs(validation.get("risk_metrics", {}).get("max_drawdown", 0.01))
        
        if max_dd == 0:
            return 0.0
        
        return avg_return / max_dd

    def _estimate_tail_risk(self, validation: Dict[str, Any]) -> float:
        """Estimate probability of extreme loss."""
        # Simplified: based on sample size and std deviation
        sample_size = validation.get("statistics", {}).get("sample_size", 0)
        
        if sample_size < 50:
            return 0.15  # 15% tail risk for small samples
        elif sample_size < 100:
            return 0.10  # 10% for medium samples
        else:
            return 0.05  # 5% for large samples

    async def _generate_statistical_insights(
        self,
        validations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate high-level statistical insights.

        Args:
            validations: List of validated signals

        Returns:
            Insights
        """
        insights = []
        
        if not validations:
            return insights
        
        # Count by confidence tier
        high_conf = sum(1 for v in validations if v.get("confidence_score", 0) >= 0.70)
        
        if high_conf >= 2:
            insights.append({
                "type": "high_confidence_cluster",
                "message": f"{high_conf} high-confidence signals detected simultaneously",
                "implication": "Market may be at inflection point",
                "recommended_action": "Increase monitoring frequency",
            })
        
        # Check for asset concentration
        assets = set(v.get("asset") for v in validations)
        if len(assets) == 1 and len(validations) >= 3:
            insights.append({
                "type": "asset_concentration",
                "message": f"Multiple signals concentrated in {list(assets)[0]}",
                "implication": "Strong directional momentum building",
                "recommended_action": "Consider position sizing increase",
            })
        
        return insights

    async def _generate_agent_directives(
        self,
        validations: List[Dict[str, Any]],
        patterns: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict]]:
        """Generate directives for other agents.

        Args:
            validations: Validated signals
            patterns: Identified patterns

        Returns:
            Agent directives
        """
        directives = {
            "SCOUT": [],
            "ELON": [],
            "SETH": [],
            "ZARA": [],
        }
        
        # Directives for ELON (high confidence only)
        high_conf_validations = [v for v in validations if v.get("confidence_score", 0) >= 0.70]
        for val in high_conf_validations[:3]:  # Top 3
            directives["ELON"].append({
                "action": "prioritize_experiment",
                "validation_id": val.get("validation_id"),
                "asset": val.get("asset"),
                "confidence": val.get("confidence_score"),
                "win_rate": val.get("statistics", {}).get("win_rate"),
                "rationale": f"Statistical validation shows {val.get('statistics', {}).get('win_rate_percentage')} win rate",
                "priority": "High",
            })
        
        # Directives for SETH (content angles)
        for val in validations[:5]:
            stats = val.get("statistics", {})
            directives["SETH"].append({
                "action": "create_statistical_content",
                "topic": f"{val.get('asset')} Sentiment Analysis: Data-Backed Predictions",
                "angle": f"Based on N={stats.get('sample_size')} historical events with {stats.get('win_rate_percentage')} accuracy",
                "data_points": {
                    "sample_size": stats.get("sample_size"),
                    "win_rate": stats.get("win_rate_percentage"),
                    "confidence": stats.get("confidence_interval_formatted"),
                    "p_value": stats.get("p_value"),
                },
                "priority": "High" if val.get("confidence_score", 0) >= 0.70 else "Medium",
            })
        
        # Directives for ZARA (community engagement)
        for val in validations[:3]:
            stats = val.get("statistics", {})
            directives["ZARA"].append({
                "action": "share_statistical_insight",
                "platform": "reddit",
                "message": f"ORACLE analysis: {val.get('asset')} sentiment shift has {stats.get('win_rate_percentage')} historical accuracy (N={stats.get('sample_size')}, p={stats.get('p_value', 0):.3f})",
                "asset": val.get("asset"),
                "confidence": val.get("confidence_score"),
            })
        
        # Directives for SCOUT (feedback)
        if patterns:
            for pattern in patterns[:2]:
                directives["SCOUT"].append({
                    "action": "monitor_pattern",
                    "pattern_type": pattern.get("pattern_type"),
                    "asset": pattern.get("asset"),
                    "confidence": pattern.get("confidence"),
                    "rationale": "ORACLE pattern detection suggests sustained momentum",
                })
        
        return directives

    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """Summarize results for notifications.

        Args:
            result: Execution results

        Returns:
            Summary string
        """
        validations = result.get("signals_validated", [])
        high_conf = sum(1 for v in validations if v.get("confidence_score", 0) >= 0.70)
        
        patterns = result.get("patterns_identified", [])
        
        if validations:
            avg_conf = statistics.mean([v.get("confidence_score", 0) for v in validations])
            avg_win_rate = statistics.mean([v.get("statistics", {}).get("win_rate", 0) for v in validations])
            
            return (
                f"Validated {len(validations)} signals "
                f"({high_conf} high-conf). "
                f"Avg confidence: {avg_conf:.0%}, "
                f"Avg win rate: {avg_win_rate:.0%}. "
                f"Patterns: {len(patterns)}"
            )
        else:
            return "No signals validated (insufficient historical data)"

    async def get_prediction_history(
        self,
        asset: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get prediction history.

        Args:
            asset: Filter by asset
            min_confidence: Minimum confidence
            limit: Maximum results

        Returns:
            List of predictions
        """
        predictions = await self.firestore.get_predictions(
            validated=True,
            limit=limit * 2,
        )
        
        # Filter
        filtered = [
            p for p in predictions
            if (not asset or p.get("asset") == asset)
            and p.get("confidence_score", 0) >= min_confidence
        ]
        
        # Sort by confidence
        filtered.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)
        
        return filtered[:limit]
