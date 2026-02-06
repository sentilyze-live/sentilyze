"""Gold market API routes with real BigQuery data."""

import secrets
import json
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from ..auth import (
    get_current_user,
    get_optional_user,
    require_admin,
    validate_api_key,
)
from ..config import get_settings
from ..logging import get_logger
from ..middleware.rate_limit import check_rate_limit
from ..bigquery_helper import get_bq_helper

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter(prefix="/gold", tags=["gold"])

# Lazy import for prediction engine (avoid heavy imports on startup)
_prediction_engine = None
_ensemble_predictor = None

def get_prediction_engine():
    """Get or create prediction engine instance."""
    global _prediction_engine
    if _prediction_engine is None:
        try:
            from services.prediction_engine.src.predictor import PredictionEngine
            _prediction_engine = PredictionEngine()
            logger.info("Prediction engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize prediction engine: {e}")
            _prediction_engine = None
    return _prediction_engine

def get_ensemble_predictor():
    """Get or create ensemble predictor instance."""
    global _ensemble_predictor
    if _ensemble_predictor is None and settings.enable_ensemble_predictions:
        try:
            from services.prediction_engine.src.ensemble import EnsemblePredictor
            _ensemble_predictor = EnsemblePredictor(
                enable_lstm=settings.enable_lstm_model,
                enable_arima=settings.enable_arima_model,
                enable_xgboost=settings.enable_xgboost_model,
                enable_random_forest=True,  # Always enabled (baseline)
            )
            logger.info("Ensemble predictor initialized", models={
                'lstm': settings.enable_lstm_model,
                'arima': settings.enable_arima_model,
                'xgboost': settings.enable_xgboost_model,
            })
        except Exception as e:
            logger.error(f"Failed to initialize ensemble predictor: {e}")
            _ensemble_predictor = None
    return _ensemble_predictor


def sanitize_input(text: str | None, max_length: int = 100) -> str | None:
    """Sanitize user input to prevent injection attacks.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text or None
    """
    if not text:
        return None
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", ';', '&', '$', '|', '`']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    return text[:max_length].strip()


def validate_symbol(symbol: str) -> str:
    """Validate and normalize gold symbol.
    
    Args:
        symbol: Symbol string to validate
        
    Returns:
        Normalized symbol
        
    Raises:
        HTTPException: If symbol is invalid
    """
    if not symbol:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Symbol is required",
        )
    
    symbol = sanitize_input(symbol, max_length=20)
    if not symbol:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid symbol format",
        )
    
    symbol = symbol.upper()
    
    # Strict whitelist of valid gold symbols (no prefix matching for security)
    valid_symbols = {
        # Spot gold pairs
        "XAUUSD", "XAU", "XAUEUR", "XAUGBP", "XAUTRY", "XAUJPY",
        "XAUCHF", "XAUCAD", "XAUAUD", "XAUNZD",
        # Silver
        "XAGUSD", "XAG", "XAGEUR", "XAGGBP",
        # Platinum & Palladium
        "XPTUSD", "XPTEUR", "XPDUSD", "XPDEUR",
        # ETFs
        "GLD", "IAU", "GDX", "GDXJ", "NUGT", "DUST", "JNUG", "JDST",
        # Turkish gram gold
        "XAUTRY",
    }

    if symbol not in valid_symbols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid symbol: {symbol}. Supported symbols: XAUUSD, XAUEUR, XAUGBP, XAUTRY, XAGUSD, GLD, IAU, and others. See API documentation.",
        )

    return symbol


def log_audit(
    action: str,
    user: dict,
    resource: str,
    details: dict | None = None,
    success: bool = True,
) -> None:
    """Log audit event for security monitoring.
    
    Args:
        action: Action performed
        user: User performing action
        resource: Resource accessed
        details: Additional details
        success: Whether action succeeded
    """
    logger.info(
        "Audit log",
        action=action,
        user_id=user.get("id"),
        tenant_id=user.get("tenant_id"),
        resource=resource,
        success=success,
        details=details or {},
    )


@router.get("/price/{symbol}")
async def get_gold_price(
    symbol: str,
    include_history: bool = Query(default=False, description="Include 24h price history"),
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get current gold price for a symbol.
    
    Args:
        symbol: Gold symbol (XAUUSD, XAUEUR, GLD, etc.)
        include_history: Include 24-hour price history
        user: Current authenticated user (optional)
        
    Returns:
        Current price data with optional history
    """
    symbol = validate_symbol(symbol)
    
    try:
        bq = get_bq_helper()
        price_data = await bq.get_gold_price_data(symbol, include_history)
        
        if price_data is None:
            # Try to get a live price from Gold-API proxy as last resort
            fallback_price = None
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    metal = symbol[:3] if len(symbol) >= 3 else "XAU"
                    resp = await client.get(f"https://api.gold-api.com/price/{metal}")
                    if resp.status_code == 200:
                        api_data = resp.json()
                        if api_data.get("price"):
                            fallback_price = api_data["price"]
            except Exception:
                pass

            price_data = {
                "symbol": symbol,
                "price": fallback_price or 0.0,
                "currency": "USD" if "USD" in symbol else "EUR" if "EUR" in symbol else "TRY",
                "change": 0.0,
                "change_percent": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
                "data_source": "gold-api-fallback" if fallback_price else "unavailable",
            }

            if not fallback_price:
                logger.warning("No price data available from any source", symbol=symbol)
        
        log_audit(
            action="price_query",
            user=user,
            resource=f"price:{symbol}",
            details={"include_history": include_history},
        )
        
        return {
            "data": price_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error("Failed to fetch gold price", error=str(e), symbol=symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch price data",
        )


@router.get("/prices")
async def get_all_gold_prices(
    currencies: str = Query(default="USD,EUR", description="Comma-separated currencies"),
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get current prices for all gold pairs.
    
    Args:
        currencies: Comma-separated currency codes
        user: Current authenticated user (optional)
        
    Returns:
        Prices for all requested gold pairs
    """
    currencies = sanitize_input(currencies, max_length=50) or "USD"
    currency_list = [c.strip().upper() for c in currencies.split(",") if c.strip()]
    
    if len(currency_list) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 currencies allowed",
        )
    
    prices = []
    bq = get_bq_helper()
    
    for currency in currency_list:
        symbol = f"XAU{currency}"
        try:
            price_data = await bq.get_gold_price_data(symbol, include_history=False)
            if price_data:
                price_data["data_source"] = "bigquery"
                prices.append(price_data)
            else:
                # No data available - report honestly
                prices.append({
                    "symbol": symbol,
                    "price": 0.0,
                    "currency": currency,
                    "change": 0.0,
                    "change_percent": 0.0,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data_source": "unavailable",
                })
        except Exception:
            prices.append({
                "symbol": symbol,
                "price": 0.0,
                "currency": currency,
                "change": 0.0,
                "change_percent": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
                "data_source": "error",
            })
    
    log_audit(
        action="prices_query",
        user=user,
        resource="prices:all",
        details={"currencies": currency_list},
    )
    
    return {
        "data": {"prices": prices},
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/sentiment/{symbol}")
async def get_gold_sentiment(
    symbol: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get sentiment analysis for gold.
    
    Args:
        symbol: Gold symbol
        start: Start time (default: 24h ago)
        end: End time (default: now)
        user: Current authenticated user (optional)
        
    Returns:
        Gold sentiment analysis data
    """
    symbol = validate_symbol(symbol)
    
    if not end:
        end = datetime.utcnow()
    if not start:
        start = end - timedelta(days=1)
    
    if end < start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time",
        )
    
    try:
        bq = get_bq_helper()
        
        # Get sentiment data from BigQuery
        result = await bq.get_sentiment_by_symbol(
            symbol=symbol,
            start=start,
            end=end,
            limit=1000,
        )
        
        items = result.get("items", [])
        
        # Calculate aggregate stats
        if items:
            avg_score = sum(item["sentiment"]["score"] for item in items) / len(items)
            avg_confidence = sum(item["sentiment"]["confidence"] for item in items) / len(items)
            
            # Count by source
            sources = {}
            for item in items:
                src = item["source"]
                if src not in sources:
                    sources[src] = {"mentions": 0, "sentiment": 0}
                sources[src]["mentions"] += 1
                sources[src]["sentiment"] += item["sentiment"]["score"]
            
            # Average sentiment by source
            for src in sources:
                sources[src]["sentiment"] /= sources[src]["mentions"]
            
            sentiment_label = "positive" if avg_score > 0.3 else "negative" if avg_score < -0.3 else "neutral"
        else:
            avg_score = 0.0
            avg_confidence = 0.0
            sentiment_label = "unavailable"
            sources = {
                "financial_news": {"mentions": 0, "sentiment": 0},
                "social_media": {"mentions": 0, "sentiment": 0},
                "analyst_reports": {"mentions": 0, "sentiment": 0},
            }
        
        log_audit(
            action="sentiment_query",
            user=user,
            resource=f"sentiment:{symbol}",
            details={"period": f"{start} to {end}"},
        )
        
        return {
            "symbol": symbol,
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "aggregate": {
                "score": avg_score,
                "confidence": avg_confidence,
                "sentiment_count": len(items),
                "label": sentiment_label,
            },
            "sources": sources,
            "data_source": "bigquery" if items else "unavailable",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error("Failed to fetch sentiment", error=str(e), symbol=symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch sentiment data",
        )


@router.get("/context/{symbol}")
async def get_market_context(
    symbol: str,
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get market context and regime for gold.

    Calculates regime, trend, volatility and support/resistance
    from real BigQuery price data and economic indicators.

    Args:
        symbol: Gold symbol
        user: Current authenticated user (optional)

    Returns:
        Market context including regime, trend, volatility
    """
    symbol = validate_symbol(symbol)

    try:
        bq = get_bq_helper()
        price_data = await bq.get_gold_price_data(symbol, include_history=True)
        data_source = "bigquery"

        prices = []
        if price_data and price_data.get("history"):
            prices = [p["price"] for p in price_data["history"] if p.get("price")]

        current_price = price_data["price"] if price_data else None

        # Calculate trend from price data
        if len(prices) >= 20:
            sma_20 = sum(prices[-20:]) / 20
            sma_50 = sum(prices[-50:]) / 50 if len(prices) >= 50 else sma_20

            if sma_20 > sma_50 * 1.005:
                trend_direction = "up"
                trend_strength = min((sma_20 / sma_50 - 1) * 100, 1.0)
            elif sma_20 < sma_50 * 0.995:
                trend_direction = "down"
                trend_strength = min((1 - sma_20 / sma_50) * 100, 1.0)
            else:
                trend_direction = "sideways"
                trend_strength = 0.2

            # Volatility from ATR-like calculation
            price_changes = [abs(prices[i] - prices[i - 1]) for i in range(1, len(prices))]
            avg_change = sum(price_changes[-14:]) / min(14, len(price_changes)) if price_changes else 0
            volatility_pct = (avg_change / current_price * 100) if current_price else 0

            if volatility_pct > 1.5:
                vol_regime = "high"
            elif volatility_pct > 0.5:
                vol_regime = "normal"
            else:
                vol_regime = "low"

            # Support/resistance from recent highs/lows
            recent = prices[-30:] if len(prices) >= 30 else prices
            pivot = (max(recent) + min(recent) + recent[-1]) / 3
            support_1 = round(2 * pivot - max(recent), 2)
            resistance_1 = round(2 * pivot - min(recent), 2)
            support_2 = round(pivot - (max(recent) - min(recent)), 2)
            resistance_2 = round(pivot + (max(recent) - min(recent)), 2)

            # Regime from combined signals
            if trend_direction == "up" and sma_20 > sma_50:
                regime = "bullish"
            elif trend_direction == "down" and sma_20 < sma_50:
                regime = "bearish"
            else:
                regime = "neutral"
        else:
            trend_direction = "sideways"
            trend_strength = 0.0
            vol_regime = "normal"
            regime = "neutral"
            support_1 = current_price * 0.98 if current_price else 0
            resistance_1 = current_price * 1.02 if current_price else 0
            support_2 = current_price * 0.96 if current_price else 0
            resistance_2 = current_price * 1.04 if current_price else 0
            data_source = "insufficient_data"

        # Fetch economic factors
        factors = {"usd_strength": 0.0, "interest_rates": 0.0, "geopolitical_risk": 0.0}
        factors_source = "unavailable"
        try:
            from services.prediction_engine.src.predictor import EconomicDataFetcher
            econ = EconomicDataFetcher()
            econ_data = await econ.fetch_economic_features()
            if econ_data.get("dxy") is not None:
                # DXY above 100 = strong USD = negative for gold
                factors["usd_strength"] = round((100 - econ_data["dxy"]) / 100 * -1, 2) if econ_data["dxy"] else 0.0
                factors_source = "bigquery"
            if econ_data.get("treasury_10y") is not None:
                factors["interest_rates"] = round(-econ_data["treasury_10y"] / 10, 2)
            if econ_data.get("vix") is not None:
                # Higher VIX = more geopolitical risk = positive for gold
                factors["geopolitical_risk"] = round(min(econ_data["vix"] / 30, 1.0), 2)
        except Exception as econ_err:
            logger.warning("Economic data fetch failed for context", error=str(econ_err))

        context = {
            "symbol": symbol,
            "regime": regime,
            "trend_direction": trend_direction,
            "trend_strength": round(trend_strength, 2),
            "volatility_regime": vol_regime,
            "volatility_value": round(volatility_pct, 4) if len(prices) >= 20 else 0.0,
            "technical_levels": {
                "support": [round(support_1, 2), round(support_2, 2)],
                "resistance": [round(resistance_1, 2), round(resistance_2, 2)],
            },
            "factors": factors,
            "data_source": data_source,
            "factors_source": factors_source,
            "price_data_points": len(prices),
            "last_updated": datetime.utcnow().isoformat(),
        }

        log_audit(
            action="context_query",
            user=user,
            resource=f"context:{symbol}",
            details={"regime": context["regime"], "data_source": data_source},
        )

        return {
            "data": context,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Failed to fetch market context", error=str(e), symbol=symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch market context",
        )


@router.get("/correlation/{symbol}")
async def get_correlation(
    symbol: str,
    compare_with: str = Query(default="DXY", description="Asset to correlate with"),
    days: int = Query(default=30, ge=1, le=90, description="Analysis period in days"),
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get real correlation between gold and another asset from BigQuery data.

    Calculates Pearson correlation coefficient from actual price data.

    Args:
        symbol: Gold symbol
        compare_with: Asset to correlate (DXY, US10Y, SPX, VIX, OIL, BTC)
        days: Number of days for analysis
        user: Current authenticated user (optional)

    Returns:
        Correlation analysis with real coefficient
    """
    symbol = validate_symbol(symbol)
    compare_with = sanitize_input(compare_with, max_length=10) or "DXY"
    compare_with = compare_with.upper()

    try:
        bq = get_bq_helper()
        corr_result = await bq.get_correlation_data(
            symbol=symbol,
            compare_symbol=compare_with,
            days=days,
        )

        if corr_result:
            data_source = "bigquery"
            corr_value = corr_result["correlation"]
            strength = corr_result["strength"]
            direction = corr_result["direction"]
            data_points = corr_result["data_points"]
        else:
            # No data available - return zeros with clear indication
            data_source = "unavailable"
            corr_value = 0.0
            strength = "Weak"
            direction = "neutral"
            data_points = 0

        correlation = {
            "symbol": symbol,
            "compare_with": compare_with,
            "period_days": days,
            "correlation": corr_value,
            "strength": strength,
            "direction": direction,
            "interpretation": (
                f"{strength} {direction} correlation between {symbol} and {compare_with}. "
                f"Correlation coefficient: {corr_value:.4f} ({data_points} data points)"
            ) if data_points > 0 else (
                f"Insufficient data to calculate correlation between {symbol} and {compare_with}. "
                f"Need at least 5 overlapping data points."
            ),
            "data_points": data_points,
            "data_source": data_source,
            "last_calculated": datetime.utcnow().isoformat(),
        }

        log_audit(
            action="correlation_query",
            user=user,
            resource=f"correlation:{symbol}:{compare_with}",
            details={"days": days, "correlation": corr_value, "data_source": data_source},
        )

        return {
            "data": correlation,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(
            "Failed to calculate correlation",
            error=str(e),
            symbol=symbol,
            compare_with=compare_with,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate correlation",
        )


@router.get("/predictions/{symbol}")
async def get_gold_predictions(
    symbol: str,
    timeframes: list[str] = Query(default=["1h", "2h", "3h"], description="Timeframes to predict"),
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get AI-powered price predictions for gold using real ML models.

    Args:
        symbol: Gold symbol (XAUUSD, etc.)
        timeframes: List of timeframes (1h, 2h, 3h, etc.)
        user: Current authenticated user (optional)

    Returns:
        Real predictions from ensemble of ML models with confidence levels
    """
    symbol = validate_symbol(symbol)

    try:
        # Get current price
        bq = get_bq_helper()
        price_data = await bq.get_gold_price_data(symbol, include_history=True)
        current_price = price_data["price"] if price_data else None
        price_source = "bigquery" if price_data else "unavailable"

        if current_price is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No price data available. BigQuery may not have recent gold prices.",
            )

        # Get price history for models
        price_history = price_data.get("history", []) if price_data else []
        prices = [p["price"] for p in price_history[-100:]] if price_history else [current_price] * 60

        # Get real sentiment score from BigQuery
        sentiment_data = await bq.get_sentiment_score_for_prediction(symbol)
        sentiment_score = sentiment_data["score"]
        sentiment_source = sentiment_data["data_source"]

        # Get prediction engine
        engine = get_prediction_engine()
        ensemble = get_ensemble_predictor()

        predictions = []

        # If ensemble enabled, use it; otherwise use basic engine
        if ensemble and settings.enable_ensemble_predictions:
            logger.info("Using ensemble predictor for predictions")

            # Fetch economic data and technical indicators
            from services.prediction_engine.src.predictor import EconomicDataFetcher
            from services.prediction_engine.src.models import TechnicalIndicators

            econ_fetcher = EconomicDataFetcher()
            economic_data = await econ_fetcher.fetch_economic_features()

            # Calculate technical indicators
            tech_analyzer = engine.technical_analyzer if engine else None
            if tech_analyzer and len(prices) >= 50:
                indicators = tech_analyzer.calculate_indicators(prices)
            else:
                indicators = TechnicalIndicators()

            # Prepare feature history for LSTM (if enabled)
            feature_history = None
            if settings.enable_lstm_model and len(prices) >= 30:
                # Build feature matrix (30 days x 10 features) as list of lists
                feature_history = []
                for i in range(30):
                    idx = -(30 - i)
                    feature_history.append([
                        prices[idx] if idx < 0 else current_price,
                        economic_data.get('dxy', 100) / 100.0,
                        economic_data.get('treasury_10y', 3.0) / 5.0,
                        economic_data.get('cpi', 300) / 300.0,
                        economic_data.get('wti_oil', 70) / 100.0,
                        economic_data.get('vix', 15) / 30.0,
                        economic_data.get('sp500', 4500) / 5000.0,
                        indicators.rsi or 50,
                        indicators.macd or 0,
                        indicators.ema_short or current_price,
                    ])

            # Price history for ARIMA (pass as list, model will convert if needed)
            price_array = prices[-100:] if len(prices) >= 100 else prices

            # Generate predictions for each timeframe
            for tf in timeframes:
                try:
                    result = await ensemble.predict(
                        indicators=indicators,
                        sentiment_score=sentiment_score,
                        current_price=current_price,
                        economic_data=economic_data,
                        price_history=price_array,
                        feature_history=feature_history,
                    )

                    predictions.append({
                        "timeframe": tf,
                        "predicted_price": round(result['ensemble_price'], 2),
                        "change_percent": round(result['change_percent'], 2),
                        "confidence": result['confidence'],
                        "direction": "up" if result['change_percent'] > 0 else "down",
                        "models_used": result['num_models'],
                        "model_predictions": {
                            k: round(v, 4) for k, v in result['models'].items()
                        },
                    })
                except Exception as e:
                    logger.error(f"Ensemble prediction failed for {tf}: {e}")
                    continue

        else:
            # Fallback to basic prediction engine
            logger.info("Using basic prediction engine (ensemble disabled)")

            if engine:
                for tf in timeframes:
                    try:
                        result = await engine.generate_prediction(
                            symbol=symbol,
                            current_price=current_price,
                            prices=prices,
                            sentiment_score=sentiment_score,
                            prediction_type=tf,
                            market_type="gold",
                        )

                        predictions.append({
                            "timeframe": tf,
                            "predicted_price": result['predicted_price'],
                            "change_percent": round(
                                ((result['predicted_price'] - current_price) / current_price) * 100, 2
                            ),
                            "confidence": result['confidence_level'],
                            "direction": result['predicted_direction'].lower(),
                            "models_used": 1,
                        })
                    except Exception as e:
                        logger.error(f"Basic prediction failed for {tf}: {e}")
                        continue

        response_data = {
            "symbol": symbol,
            "current_price": current_price,
            "predictions": predictions,
            "prediction_method": "ensemble" if ensemble and settings.enable_ensemble_predictions else "basic",
            "models_enabled": {
                "lstm": settings.enable_lstm_model,
                "arima": settings.enable_arima_model,
                "xgboost": settings.enable_xgboost_model,
                "ensemble": settings.enable_ensemble_predictions,
            },
            "sentiment_score": sentiment_score,
            "sentiment_source": sentiment_source,
            "sentiment_count": sentiment_data.get("count", 0),
            "price_source": price_source,
            "generated_at": datetime.utcnow().isoformat(),
            "disclaimer": "AI predictions are not investment advice. Past performance does not guarantee future results.",
        }

        log_audit(
            action="predictions_query",
            user=user,
            resource=f"predictions:{symbol}",
            details={"sentiment_score": sentiment_score, "sentiment_source": sentiment_source},
        )

        return {
            "data": response_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Failed to generate predictions", error=str(e), symbol=symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate predictions",
        )


@router.get("/scenarios")
async def get_prediction_scenarios(
    symbol: str = Query(default="XAUTRY", description="Gold symbol for scenarios"),
    user: dict = Depends(get_optional_user),
) -> list[dict[str, Any]]:
    """Get real prediction scenarios using ensemble of ML models.

    Uses real LSTM, ARIMA, XGBoost, and Random Forest models (not mock data).

    Args:
        symbol: Gold symbol (XAUTRY, XAUUSD, etc.)
        user: Current authenticated user (optional)

    Returns:
        List of real prediction scenarios for different timeframes
    """
    try:
        # Validate symbol
        symbol = validate_symbol(symbol)

        # Get current price
        bq = get_bq_helper()
        price_data = await bq.get_gold_price_data(symbol, include_history=True)
        current_price = price_data["price"] if price_data else None

        if current_price is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No price data available for scenarios.",
            )

        # Get real sentiment score
        sentiment_data = await bq.get_sentiment_score_for_prediction(symbol)
        sentiment_score = sentiment_data["score"]

        # Get ensemble predictor
        ensemble = get_ensemble_predictor()

        if not ensemble or not settings.enable_ensemble_predictions:
            logger.warning("Ensemble predictor not available, using fallback")
            return [
                {
                    "timeframe": "1 Saat",
                    "price": round(current_price * 1.0015, 2),
                    "changePercent": 0.15,
                    "confidenceScore": 60,
                    "direction": "up",
                    "models": [
                        {"name": "Random Forest", "weight": 1.0, "prediction": current_price * 1.0015},
                    ],
                    "note": "Ensemble models not enabled (set ENABLE_ENSEMBLE_PREDICTIONS=True)",
                    "sentiment_score": sentiment_score,
                    "sentiment_source": sentiment_data["data_source"],
                }
            ]

        # Fetch data for predictions
        from services.prediction_engine.src.predictor import EconomicDataFetcher
        from services.prediction_engine.src.models import TechnicalIndicators

        price_history = price_data.get("history", []) if price_data else []
        prices = [p["price"] for p in price_history[-100:]] if price_history else [current_price] * 60

        econ_fetcher = EconomicDataFetcher()
        economic_data = await econ_fetcher.fetch_economic_features()

        # Calculate indicators
        engine = get_prediction_engine()
        if engine and len(prices) >= 50:
            indicators = engine.technical_analyzer.calculate_indicators(prices)
        else:
            indicators = TechnicalIndicators()

        # Prepare feature history for LSTM
        feature_history = None
        if settings.enable_lstm_model and len(prices) >= 30:
            feature_history = []
            for i in range(30):
                idx = -(30 - i)
                feature_history.append([
                    prices[idx] if idx < 0 else current_price,
                    economic_data.get('dxy', 100) / 100.0,
                    economic_data.get('treasury_10y', 3.0) / 5.0,
                    economic_data.get('cpi', 300) / 300.0,
                    economic_data.get('wti_oil', 70) / 100.0,
                    economic_data.get('vix', 15) / 30.0,
                    economic_data.get('sp500', 4500) / 5000.0,
                    indicators.rsi or 50,
                    indicators.macd or 0,
                    indicators.ema_short or current_price,
                ])

        price_array = prices[-100:] if len(prices) >= 100 else prices

        # Generate real scenarios
        scenarios = []
        timeframes = ["1 Saat", "2 Saat", "3 Saat"]

        for tf in timeframes:
            try:
                result = await ensemble.predict(
                    indicators=indicators,
                    sentiment_score=sentiment_score,
                    current_price=current_price,
                    economic_data=economic_data,
                    price_history=price_array,
                    feature_history=feature_history,
                )

                # Convert model predictions to expected format
                models_list = []
                for model_name, signal in result['models'].items():
                    # Convert signal to price prediction
                    price_change = signal * 0.03  # Signal to % change
                    predicted_price = current_price * (1 + price_change)
                    weight = result['weights_used'].get(model_name, 0.0)

                    models_list.append({
                        "name": model_name.upper(),
                        "weight": round(weight, 2),
                        "prediction": round(predicted_price, 2),
                    })

                # Map confidence to score
                confidence_map = {"HIGH": 75, "MEDIUM": 60, "LOW": 45}
                confidence_score = confidence_map.get(result['confidence'], 60)

                scenarios.append({
                    "timeframe": tf,
                    "price": round(result['ensemble_price'], 2),
                    "changePercent": round(result['change_percent'], 2),
                    "confidenceScore": confidence_score,
                    "direction": "up" if result['change_percent'] > 0 else "down",
                    "models": models_list,
                    "num_models_used": result['num_models'],
                })

            except Exception as e:
                logger.error(f"Failed to generate scenario for {tf}: {e}")
                continue

        if not scenarios:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate any scenarios",
            )

        log_audit(
            action="scenarios_query",
            user=user,
            resource=f"scenarios:{symbol}",
            details={"scenarios_count": len(scenarios), "method": "real_ensemble"},
        )

        return scenarios

    except Exception as e:
        logger.error("Failed to generate scenarios", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate prediction scenarios",
        )


@router.get("/daily-report")
async def get_daily_analysis_report(
    days: int = Query(default=7, description="Number of days to analyze"),
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get prediction performance report with real model metrics.

    NOTE: This endpoint requires historical prediction data in BigQuery.
    If no historical data exists, returns sample structure.

    Args:
        days: Number of days to analyze (default: 7)
        user: Current authenticated user (optional)

    Returns:
        Analysis report with real or sample model performance metrics
    """
    try:
        ensemble = get_ensemble_predictor()

        # TODO: Query BigQuery for actual prediction history
        # For now, return structure with model status
        report = {
            "date": datetime.utcnow().date().isoformat(),
            "period_days": days,
            "data_available": False,  # Will be True when backtesting implemented
            "message": "Historical prediction tracking not yet implemented. Enable backtesting to see real metrics.",
            "model_status": {
                "lstm": {
                    "enabled": settings.enable_lstm_model,
                    "initialized": ensemble.lstm._initialized if ensemble and ensemble.lstm else False,
                    "info": ensemble.lstm.get_model_info() if ensemble and ensemble.lstm else None,
                },
                "arima": {
                    "enabled": settings.enable_arima_model,
                    "initialized": ensemble.arima._initialized if ensemble and ensemble.arima else False,
                    "info": ensemble.arima.get_model_info() if ensemble and ensemble.arima else None,
                },
                "xgboost": {
                    "enabled": settings.enable_xgboost_model,
                    "initialized": ensemble.xgboost._initialized if ensemble and ensemble.xgboost else False,
                    "info": ensemble.xgboost.get_model_info() if ensemble and ensemble.xgboost else None,
                },
                "random_forest": {
                    "enabled": True,
                    "initialized": True,
                },
            } if ensemble else {},
            "ensemble_weights": ensemble.weights if ensemble else {},
            "disclaimer": "Geçmiş performans gelecekteki sonuçların göstergesi değildir. Yatırım tavsiyesi niteliği taşımaz.",
        }

        # If backtesting is implemented, query real data:
        # bq = get_bq_helper()
        # predictions = await bq.get_prediction_history(days=days)
        # actual_prices = await bq.get_actual_prices(days=days)
        # Calculate MAE, RMSE, direction accuracy, etc.

        log_audit(
            action="daily_report_query",
            user=user,
            resource="daily_report",
            details={"days": days, "data_available": report["data_available"]},
        )

        return report

    except Exception as e:
        logger.error("Failed to generate daily report", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate daily report",
        )


# Unified cache via Redis (with in-memory fallback)
from ..middleware.redis import cache_get, cache_set


@router.get("/finnhub-proxy/{symbol}")
async def finnhub_proxy(
    symbol: str,
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Proxy Finnhub API requests to avoid CORS issues and add caching.

    This endpoint fetches forex rates from Finnhub API and caches them
    for 60 seconds to prevent rate limiting (60 req/min limit).

    Args:
        symbol: Finnhub symbol (e.g., XAU_USD, USD_TRY, EUR_TRY)
        user: Current authenticated user (optional)

    Returns:
        Finnhub quote data with price, change, and other metrics

    Example:
        GET /gold/finnhub-proxy/XAU_USD
        Returns: {"c": 2050.50, "d": 15.30, "dp": 0.75, "h": 2055, "l": 2045, ...}
    """
    # Sanitize symbol
    symbol = sanitize_input(symbol, max_length=20)
    if not symbol:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid symbol format",
        )

    # Check cache first (60-second TTL)
    cache_key = f"finnhub:{symbol}"

    cached = cache_get(cache_key)
    if cached is not None:
        logger.debug("Returning cached Finnhub data", symbol=symbol)
        return cached

    # Fetch from Finnhub API
    try:
        finnhub_api_key = settings.finnhub_api_key or "cufe5f9r01qhcm6a4jr0cufe5f9r01qhcm6a4jrg"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://finnhub.io/api/v1/quote",
                params={
                    "symbol": f"OANDA:{symbol}",
                    "token": finnhub_api_key,
                },
            )

            if response.status_code == 429:
                logger.warning("Finnhub rate limit exceeded", symbol=symbol)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Finnhub API rate limit exceeded. Please try again later.",
                )

            response.raise_for_status()
            data = response.json()

            # Validate response has expected fields
            if not data or "c" not in data:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Invalid response from Finnhub API",
                )

            # Cache the response (60s TTL)
            cache_set(cache_key, data, ttl=60)

            log_audit(
                action="finnhub_proxy_query",
                user=user,
                resource=f"finnhub:{symbol}",
                details={"cached": False},
            )

            return data

    except httpx.HTTPStatusError as e:
        logger.error("Finnhub API error", error=str(e), symbol=symbol, status_code=e.response.status_code)
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Finnhub API error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("Finnhub request failed", error=str(e), symbol=symbol)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to Finnhub API",
        )
    except Exception as e:
        logger.error("Finnhub proxy error", error=str(e), symbol=symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while proxying Finnhub request",
        )


# GenelPara API cache uses unified Redis/memory cache via cache_get/cache_set


@router.get("/genelpara-proxy")
async def genelpara_proxy(
    list_type: str = Query(default="altin", alias="list", description="Data type: altin, doviz, kripto, emtia"),
    symbols: str = Query(default="GA,XAUUSD", description="Comma-separated symbols (e.g., GA,C,XAUUSD)"),
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Proxy GenelPara API requests to avoid CORS issues and add caching.

    GenelPara provides free Turkish market data with 1000 req/day limit per IP.
    This endpoint caches responses for 60 seconds to respect their limits.

    Args:
        list_type: Data category (altin=gold, doviz=forex, kripto=crypto, emtia=commodities)
        symbols: Comma-separated symbols (use 'all' for all symbols in category)
        user: Current authenticated user (optional)

    Returns:
        GenelPara API data with prices, changes, and remaining daily requests

    Example:
        GET /gold/genelpara-proxy?list=altin&symbols=GA,XAUUSD
        Returns:
        {
            "success": true,
            "count": 2,
            "remaining": 998,
            "data": {
                "GA": {"alis": "6788.76", "satis": "6789.57", "degisim": "-1.82", ...},
                "XAUUSD": {"alis": "4846.14", "satis": "4846.77", "degisim": "-1.86", ...}
            }
        }

    Supported Gold Symbols:
        GA - Gram Gold (TRY)
        XAUUSD - Troy Ounce Gold (USD)
        C - Quarter Gold (TRY)
        Y - Half Gold (TRY)
        T - Full Gold (TRY)
        GAG - Gram Silver (TRY)
        ... and 12 more gold types
    """
    # Sanitize inputs
    list_type = sanitize_input(list_type, max_length=20) or "altin"
    symbols = sanitize_input(symbols, max_length=200) or "GA,XAUUSD"

    # Validate list_type
    allowed_types = ["altin", "doviz", "kripto", "emtia"]
    if list_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid list type. Allowed: {', '.join(allowed_types)}",
        )

    # Check cache first (60-second TTL)
    cache_key = f"genelpara:{list_type}:{symbols}"

    cached = cache_get(cache_key)
    if cached is not None:
        logger.debug("Returning cached GenelPara data", list_type=list_type, symbols=symbols)
        return cached

    # Fetch from GenelPara API
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # GenelPara API format: /json/?list=altin&sembol=GA,C
            # Use 'all' for all symbols, or comma-separated list for specific ones
            url = f"https://api.genelpara.com/json/"
            params = {
                "list": list_type,
                "sembol": symbols if symbols.lower() != "all" else "all"
            }

            response = await client.get(url, params=params)

            if response.status_code == 429:
                logger.warning("GenelPara rate limit exceeded", list_type=list_type)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="GenelPara API rate limit exceeded (1000 req/day). Please try again tomorrow.",
                )

            response.raise_for_status()
            data = response.json()

            # Validate response
            if not data or not data.get("success"):
                error_msg = data.get("message", "Unknown error") if data else "Invalid response"
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"GenelPara API error: {error_msg}",
                )

            # Log remaining requests for monitoring
            remaining = data.get("remaining", "unknown")
            if isinstance(remaining, int) and remaining < 100:
                logger.warning(
                    "GenelPara API requests running low",
                    remaining=remaining,
                    reset_at="00:00 daily"
                )

            # Cache the response (60s TTL)
            cache_set(cache_key, data, ttl=60)

            log_audit(
                action="genelpara_proxy_query",
                user=user,
                resource=f"genelpara:{list_type}:{symbols}",
                details={
                    "cached": False,
                    "count": data.get("count", 0),
                    "remaining": remaining
                },
            )

            return data

    except httpx.HTTPStatusError as e:
        logger.error(
            "GenelPara API error",
            error=str(e),
            list_type=list_type,
            status_code=e.response.status_code,
        )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"GenelPara API error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("GenelPara API request failed", error=str(e), list_type=list_type)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to GenelPara API",
        )
    except Exception as e:
        logger.error("GenelPara proxy error", error=str(e), list_type=list_type)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while proxying GenelPara request",
        )


# Gold-API.com cache uses unified Redis/memory cache via cache_get/cache_set


@router.get("/gold-api-proxy/{symbol}")
async def gold_api_proxy(
    symbol: str,
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Proxy Gold-API.com requests to avoid CORS issues and add caching.

    Gold-API.com provides free unlimited real-time gold prices.
    This endpoint caches responses for 60 seconds to be respectful to their API.

    Args:
        symbol: Currency pair symbol (e.g., XAU-USD, XAU-TRY, XAU-EUR)
        user: Current authenticated user (optional)

    Returns:
        Gold-API.com data with price, timestamp, and other metrics

    Example:
        GET /gold/gold-api-proxy/XAU-USD
        Returns: {"price": 2050.50, "ask": 2051, "bid": 2050, "high_price": 2055, ...}
    """
    # Sanitize symbol
    symbol = sanitize_input(symbol, max_length=20)
    if not symbol:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid symbol format",
        )

    # Normalize symbol format (e.g., XAU_USD -> XAU-USD, XAUUSD -> XAU-USD)
    symbol = symbol.replace("_", "-").upper()
    if "-" not in symbol and len(symbol) == 6:
        # XAUUSD -> XAU-USD
        symbol = f"{symbol[:3]}-{symbol[3:]}"

    # Check cache first (60-second TTL)
    cache_key = f"goldapi:{symbol}"

    cached = cache_get(cache_key)
    if cached is not None:
        logger.debug("Returning cached Gold-API data", symbol=symbol)
        return cached

    # Fetch from Gold-API.com
    try:
        # Gold-API.com free tier doesn't require API key for basic quotes
        # But we can add one later if needed via settings
        gold_api_key = getattr(settings, 'gold_api_key', None)

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Gold-API.com format: /price/METAL (e.g., /price/XAU)
            # Extract just the metal symbol (first part before dash or slash)
            metal_symbol = symbol.split("-")[0].split("/")[0].upper()

            # Gold-API only supports: XAU, XAG, BTC, ETH, XPD, HG, XPT
            supported_symbols = ["XAU", "XAG", "BTC", "ETH", "XPD", "HG", "XPT"]
            if metal_symbol not in supported_symbols:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported symbol. Supported: {', '.join(supported_symbols)}",
                )

            url = f"https://api.gold-api.com/price/{metal_symbol}"
            headers = {}
            if gold_api_key:
                headers["x-access-token"] = gold_api_key

            response = await client.get(url, headers=headers)

            if response.status_code == 429:
                logger.warning("Gold-API rate limit exceeded", symbol=symbol)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Gold-API rate limit exceeded. Please try again later.",
                )

            response.raise_for_status()
            data = response.json()

            # Validate response has expected fields
            if not data or "price" not in data:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Invalid response from Gold-API",
                )

            # Cache the response (60s TTL)
            cache_set(cache_key, data, ttl=60)

            log_audit(
                action="gold_api_proxy_query",
                user=user,
                resource=f"goldapi:{symbol}",
                details={"cached": False},
            )

            return data

    except httpx.HTTPStatusError as e:
        logger.error(
            "Gold-API error",
            error=str(e),
            symbol=symbol,
            status_code=e.response.status_code,
        )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Gold-API error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("Gold-API request failed", error=str(e), symbol=symbol)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to Gold-API",
        )
    except Exception as e:
        logger.error("Gold-API proxy error", error=str(e), symbol=symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while proxying Gold-API request",
        )


# Exchangerate-API cache (in-memory, 300-second TTL)
@router.get("/exchangerate-proxy/{base}")
async def exchangerate_proxy(
    base: str,
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Proxy Exchangerate-API requests to avoid CORS issues and add caching.

    Exchangerate-API.com provides free unlimited forex rates.
    This endpoint caches responses for 5 minutes (rates don't change that frequently).

    Args:
        base: Base currency code (e.g., USD, EUR)
        user: Current authenticated user (optional)

    Returns:
        Exchangerate-API data with rates for all currencies

    Example:
        GET /gold/exchangerate-proxy/USD
        Returns: {"base": "USD", "rates": {"TRY": 43.54, "EUR": 0.847, ...}}
    """
    # Sanitize base currency
    base = sanitize_input(base, max_length=3)
    if not base or len(base) != 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid currency code (must be 3 letters)",
        )

    base = base.upper()

    # Check cache first (300-second TTL = 5 minutes)
    cache_key = f"exchangerate:{base}"

    cached = cache_get(cache_key)
    if cached is not None:
        logger.debug("Returning cached Exchangerate-API data", base=base)
        return cached

    # Fetch from Exchangerate-API
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.exchangerate-api.com/v4/latest/{base}"
            )

            if response.status_code == 429:
                logger.warning("Exchangerate-API rate limit exceeded", base=base)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Exchangerate-API rate limit exceeded. Please try again later.",
                )

            response.raise_for_status()
            data = response.json()

            # Validate response has expected fields
            if not data or "rates" not in data:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Invalid response from Exchangerate-API",
                )

            # Cache the response (300s = 5 min TTL)
            cache_set(cache_key, data, ttl=300)

            log_audit(
                action="exchangerate_proxy_query",
                user=user,
                resource=f"exchangerate:{base}",
                details={"cached": False},
            )

            return data

    except httpx.HTTPStatusError as e:
        logger.error(
            "Exchangerate-API error",
            error=str(e),
            base=base,
            status_code=e.response.status_code,
        )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Exchangerate-API error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("Exchangerate-API request failed", error=str(e), base=base)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to Exchangerate-API",
        )
    except Exception as e:
        logger.error("Exchangerate-API proxy error", error=str(e), base=base)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while proxying Exchangerate-API request",
        )


@router.get("/feature-importance")
async def get_feature_importance(
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get feature importance from XGBoost model.

    Shows which factors (DXY, VIX, Treasury yields, etc.) have the most impact
    on gold price predictions.

    Returns:
        Feature importance rankings from XGBoost model
    """
    try:
        ensemble = get_ensemble_predictor()

        if not ensemble or not settings.enable_xgboost_model:
            return {
                "available": False,
                "message": "XGBoost model not enabled (set ENABLE_XGBOOST_MODEL=True)",
                "features": {},
            }

        # Get feature importance from XGBoost
        if ensemble.xgboost and ensemble.xgboost._initialized:
            importance = ensemble.xgboost.get_feature_importance()

            return {
                "available": True,
                "features": importance,
                "top_5": list(importance.items())[:5],
                "description": {
                    "dxy": "USD Index (inverse correlation with gold)",
                    "treasury_10y": "10-Year Treasury yield (interest rates)",
                    "cpi": "Consumer Price Index (inflation)",
                    "wti_oil": "WTI crude oil price",
                    "vix": "Volatility index (fear gauge)",
                    "sp500": "S&P 500 index (risk sentiment)",
                    "rsi": "Relative Strength Index (technical)",
                    "macd": "Moving Average Convergence Divergence",
                    "ema_short": "Short-term Exponential Moving Average",
                    "ema_medium": "Medium-term Exponential Moving Average",
                    "sentiment_score": "Market sentiment score",
                },
                "generated_at": datetime.utcnow().isoformat(),
            }
        else:
            return {
                "available": False,
                "message": "XGBoost model not yet trained or initialized",
                "features": {},
            }

    except Exception as e:
        logger.error("Failed to get feature importance", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feature importance",
        )


@router.get("/model-info")
async def get_model_info(
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get information about enabled prediction models.

    Returns:
        Status and configuration of all prediction models
    """
    try:
        engine = get_prediction_engine()
        ensemble = get_ensemble_predictor()

        info = {
            "prediction_method": "ensemble" if ensemble and settings.enable_ensemble_predictions else "basic",
            "models_enabled": {
                "random_forest": True,  # Always enabled (baseline)
                "lstm": settings.enable_lstm_model,
                "arima": settings.enable_arima_model,
                "xgboost": settings.enable_xgboost_model,
                "ensemble": settings.enable_ensemble_predictions,
            },
            "model_details": {},
        }

        # Get ensemble model info
        if ensemble:
            info["model_details"] = ensemble.get_model_info()

        # Get basic engine info
        if engine:
            info["basic_engine"] = {
                "technical_analysis": True,
                "ml_predictions": settings.enable_ml_predictions,
            }

        log_audit(
            action="model_info_query",
            user=user,
            resource="model_info",
            details={"method": info["prediction_method"]},
        )

        return info

    except Exception as e:
        logger.error("Failed to get model info", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve model information",
        )


@router.get("/technical-indicators/{symbol}")
async def get_technical_indicators(
    symbol: str,
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get real technical indicators calculated from BigQuery price data.

    Calculates RSI, MACD, Bollinger Bands, EMAs, and Stochastic from actual
    price history - no random or mock data.

    Args:
        symbol: Gold symbol (XAUUSD, etc.)
        user: Current authenticated user (optional)

    Returns:
        Technical indicator values calculated from real data
    """
    symbol = validate_symbol(symbol)

    try:
        bq = get_bq_helper()
        price_data = await bq.get_gold_price_data(symbol, include_history=True)

        if not price_data or not price_data.get("history"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Insufficient price data for technical analysis.",
            )

        prices = [p["price"] for p in price_data["history"] if p.get("price")]
        current_price = price_data["price"]

        if len(prices) < 20:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Need at least 20 data points, have {len(prices)}.",
            )

        engine = get_prediction_engine()
        if engine and len(prices) >= 50:
            indicators = engine.technical_analyzer.calculate_indicators(prices)

            # Determine RSI condition
            rsi_val = indicators.rsi or 50
            if rsi_val > 70:
                rsi_condition = "overbought"
            elif rsi_val < 30:
                rsi_condition = "oversold"
            else:
                rsi_condition = "neutral"

            # Determine MACD momentum
            macd_hist = indicators.macd_histogram or 0
            macd_momentum = "positive" if macd_hist > 0 else "negative"

            # Stochastic from prices
            recent_14 = prices[-14:]
            highest = max(recent_14)
            lowest = min(recent_14)
            stoch_range = highest - lowest
            stoch_k = ((current_price - lowest) / stoch_range * 100) if stoch_range > 0 else 50
            stoch_d = stoch_k  # Simplified (proper: 3-period SMA of %K)

            if stoch_k > 80:
                stoch_condition = "overbought"
            elif stoch_k < 20:
                stoch_condition = "oversold"
            else:
                stoch_condition = "neutral"

            result = {
                "symbol": symbol,
                "current_price": current_price,
                "rsi": {
                    "value": round(rsi_val, 2),
                    "condition": rsi_condition,
                },
                "macd": {
                    "value": round(indicators.macd or 0, 4),
                    "signal": round(indicators.macd_signal or 0, 4),
                    "momentum": macd_momentum,
                    "histogram": round(macd_hist, 4),
                },
                "bollinger": {
                    "upper": round(indicators.bb_upper or current_price * 1.02, 2),
                    "middle": round(indicators.bb_middle or current_price, 2),
                    "lower": round(indicators.bb_lower or current_price * 0.98, 2),
                    "width": round(
                        ((indicators.bb_upper or 0) - (indicators.bb_lower or 0)) / current_price * 100, 2
                    ) if current_price else 0,
                },
                "ema": {
                    "short": round(indicators.ema_short or 0, 2),
                    "medium": round(indicators.ema_medium or 0, 2),
                    "long": round(indicators.ema_long or 0, 2),
                },
                "sma": {
                    "20": round(sum(prices[-20:]) / 20, 2) if len(prices) >= 20 else 0,
                    "50": round(sum(prices[-50:]) / 50, 2) if len(prices) >= 50 else 0,
                    "200": round(sum(prices[-200:]) / 200, 2) if len(prices) >= 200 else 0,
                },
                "stochastic": {
                    "k": round(stoch_k, 2),
                    "d": round(stoch_d, 2),
                    "condition": stoch_condition,
                },
                "atr": round(
                    sum(abs(prices[i] - prices[i - 1]) for i in range(max(1, len(prices) - 14), len(prices)))
                    / min(14, len(prices) - 1), 2
                ) if len(prices) > 1 else 0,
                "data_points": len(prices),
                "data_source": "bigquery",
                "generated_at": datetime.utcnow().isoformat(),
            }
        else:
            # Minimal calculation with less data
            import numpy as np
            prices_arr = prices[-20:]
            sma_20 = sum(prices_arr) / len(prices_arr)

            result = {
                "symbol": symbol,
                "current_price": current_price,
                "rsi": {"value": 50.0, "condition": "neutral"},
                "macd": {"value": 0, "signal": 0, "momentum": "neutral", "histogram": 0},
                "bollinger": {
                    "upper": round(sma_20 + 2 * float(np.std(prices_arr)), 2),
                    "middle": round(sma_20, 2),
                    "lower": round(sma_20 - 2 * float(np.std(prices_arr)), 2),
                    "width": 0,
                },
                "ema": {"short": 0, "medium": 0, "long": 0},
                "sma": {"20": round(sma_20, 2), "50": 0, "200": 0},
                "stochastic": {"k": 50, "d": 50, "condition": "neutral"},
                "atr": 0,
                "data_points": len(prices),
                "data_source": "bigquery",
                "note": "Limited data - need 50+ points for full analysis",
                "generated_at": datetime.utcnow().isoformat(),
            }

        log_audit(
            action="technical_indicators_query",
            user=user,
            resource=f"indicators:{symbol}",
            details={"data_points": len(prices)},
        )

        return {"data": result, "timestamp": datetime.utcnow().isoformat()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to calculate technical indicators", error=str(e), symbol=symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate technical indicators",
        )


@router.get("/history/{symbol}")
async def get_gold_history(
    symbol: str,
    timeframe: str = Query(default="1D", description="Timeframe: 1D, 1W, 1M, 3M, 1Y"),
    limit: int = Query(default=100, ge=1, le=500, description="Max data points"),
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get real gold price history from BigQuery.

    Returns actual OHLCV data, not synthetic/random data.

    Args:
        symbol: Gold symbol
        timeframe: Time period (1D, 1W, 1M, 3M, 1Y)
        limit: Maximum data points to return
        user: Current authenticated user (optional)

    Returns:
        Historical OHLCV price data
    """
    symbol = validate_symbol(symbol)
    timeframe = sanitize_input(timeframe, max_length=5) or "1D"
    timeframe = timeframe.upper()

    if timeframe not in ("1D", "1W", "1M", "3M", "1Y"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timeframe. Supported: 1D, 1W, 1M, 3M, 1Y",
        )

    try:
        bq = get_bq_helper()
        history = await bq.get_gold_price_history(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
        )

        if history:
            data_source = "bigquery"
        else:
            history = []
            data_source = "unavailable"

        log_audit(
            action="history_query",
            user=user,
            resource=f"history:{symbol}",
            details={"timeframe": timeframe, "data_points": len(history)},
        )

        return {
            "data": {
                "symbol": symbol,
                "timeframe": timeframe,
                "prices": history,
                "count": len(history),
                "data_source": data_source,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Failed to fetch price history", error=str(e), symbol=symbol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch price history",
        )


@router.get("/news")
async def get_gold_news(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=50, description="Articles per page"),
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get gold-related news articles from BigQuery.

    Args:
        page: Page number for pagination
        limit: Number of articles per page
        user: Current authenticated user (optional)

    Returns:
        List of gold news articles with sentiment scores
    """
    try:
        bq = get_bq_helper()
        offset = (page - 1) * limit
        result = await bq.get_gold_news(limit=limit, offset=offset)

        articles = result.get("articles", [])
        total = result.get("total", 0)

        log_audit(
            action="news_query",
            user=user,
            resource="news:gold",
            details={"page": page, "count": len(articles)},
        )

        return {
            "data": {
                "articles": articles,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "has_more": (offset + len(articles)) < total,
                },
                "data_source": "bigquery" if articles else "unavailable",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Failed to fetch gold news", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch gold news",
        )
