"""Gold market API routes with real BigQuery data."""

import secrets
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from google.cloud import firestore

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


def create_fallback_scenario(timeframe: str, current_price: float, sentiment: float = 0.0) -> dict[str, Any]:
    """Create basic scenario when ensemble predictor fails.

    Args:
        timeframe: Timeframe string (e.g., "1 Saat", "2 Saat")
        current_price: Current price to base prediction on
        sentiment: Sentiment score (-1 to 1) to adjust prediction

    Returns:
        Scenario dictionary with fallback prediction
    """
    try:
        # Extract hours from timeframe (e.g., "1" from "1 Saat")
        tf_hours = int(timeframe.split()[0])
    except (IndexError, ValueError):
        tf_hours = 1  # Default to 1 hour if parsing fails

    # Simple prediction: 0.1% increase per hour + sentiment adjustment
    base_change = 0.1 * tf_hours
    sentiment_adjustment = sentiment * 0.05
    change_pct = base_change + sentiment_adjustment

    predicted_price = current_price * (1 + change_pct / 100)

    return {
        "timeframe": timeframe,
        "price": round(predicted_price, 2),
        "changePercent": round(change_pct, 2),
        "confidenceScore": 50,  # Low confidence for fallback
        "direction": "up" if change_pct > 0 else "down",
        "models": [{"name": "FALLBACK", "weight": 1.0, "prediction": round(predicted_price, 2)}],
        "num_models_used": 1,
        "sentiment_score": sentiment,
        "sentiment_source": "fallback",
        "note": "Using fallback prediction (ensemble unavailable)"
    }


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
                # Fallback to Gold-API.com for real-time data
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.get("https://api.gold-api.com/price/XAU")
                        if resp.status_code == 200:
                            gold_data = resp.json()
                            base_price = gold_data.get("price", 0)
                            if base_price > 0:
                                # Calculate actual current price (Gold-API returns USD price)
                                if currency == "USD":
                                    current_price = base_price
                                elif currency == "TRY":
                                    # Get TRY/USD rate from GenelPara proxy (cached)
                                    current_price = base_price * 43.5  # Approximate for now
                                elif currency == "EUR":
                                    current_price = base_price * 0.92  # Approximate EUR/USD
                                else:
                                    current_price = base_price

                                prices.append({
                                    "symbol": symbol,
                                    "price": round(current_price, 2),
                                    "currency": currency,
                                    "change": 0.0,  # Not available from Gold-API
                                    "change_percent": 0.0,
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "data_source": "gold-api.com",
                                })
                                continue
                except Exception as e:
                    logger.warning(f"Gold-API fallback failed for {symbol}", error=str(e))

                # Final fallback: unavailable
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
        logger.error("Market context generation failed", error=str(e), symbol=symbol)

        # Return neutral fallback context
        return {
            "data": {
                "symbol": symbol,
                "regime": "neutral",
                "trend_direction": "sideways",
                "trend_strength": 0.5,
                "volatility_regime": "normal",
                "volatility_value": 0.5,
                "technical_levels": {
                    "support": [],
                    "resistance": [],
                },
                "factors": {
                    "usd_strength": 0,
                    "interest_rates": 0,
                    "geopolitical_risk": 0,
                },
                "data_source": "fallback",
                "disclaimer": "Fallback piyasa bağlamı - gerçek veri kullanılamıyor",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


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

        # Fallback to gold-api.com if no BigQuery data
        if current_price is None or current_price == 0:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    metal = symbol[:3] if len(symbol) >= 3 else "XAU"
                    currency = "USD" if "USD" in symbol else "TRY" if "TRY" in symbol else "EUR"
                    resp = await client.get(f"https://api.gold-api.com/price/{metal}")
                    if resp.status_code == 200:
                        api_data = resp.json()
                        if api_data.get("price"):
                            current_price = api_data["price"]
                            # Create minimal price_data for predictions
                            price_data = {
                                "symbol": symbol,
                                "price": current_price,
                                "currency": currency,
                                "change": 0.0,
                                "change_percent": 0.0,
                                "timestamp": datetime.utcnow().isoformat(),
                                "history": [],  # No history from fallback
                            }
                            price_source = "gold-api-fallback"
                            logger.info("Using gold-api.com fallback for predictions", symbol=symbol, price=current_price)
            except Exception as e:
                logger.error("Failed to get fallback price for predictions", error=str(e), symbol=symbol)

        if current_price is None or current_price == 0:
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

        # Fallback to gold-api.com if no BigQuery data
        if current_price is None or current_price == 0:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    metal = symbol[:3] if len(symbol) >= 3 else "XAU"
                    currency = "USD" if "USD" in symbol else "TRY" if "TRY" in symbol else "EUR"

                    # Get gold price in USD from gold-api.com
                    resp = await client.get(f"https://api.gold-api.com/price/{metal}")
                    if resp.status_code == 200:
                        api_data = resp.json()
                        usd_ounce_price = api_data.get("price")

                        if usd_ounce_price:
                            # Convert to TRY if needed
                            if "TRY" in symbol:
                                # Get USD/TRY exchange rate
                                try:
                                    forex_resp = await client.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=3.0)
                                    if forex_resp.status_code == 200:
                                        forex_data = forex_resp.json()
                                        usd_try_rate = forex_data.get("rates", {}).get("TRY", 43.5)  # Fallback to ~43.5
                                    else:
                                        usd_try_rate = 43.5  # Use approximate rate if API fails
                                except Exception:
                                    usd_try_rate = 43.5  # Use approximate rate if API fails

                                # Convert from ounce to gram for XAUTRY
                                # 1 troy ounce = 31.1035 grams
                                try_ounce_price = usd_ounce_price * usd_try_rate
                                current_price = try_ounce_price / 31.1035  # Convert to price per gram

                                logger.info(
                                    "Converted USD ounce price to TRY gram",
                                    usd_ounce=usd_ounce_price,
                                    usd_try_rate=usd_try_rate,
                                    try_gram=current_price,
                                )
                            else:
                                # Use USD price directly for XAUUSD
                                current_price = usd_ounce_price

                            # Create minimal price_data for scenarios
                            price_data = {
                                "symbol": symbol,
                                "price": current_price,
                                "currency": currency,
                                "change": 0.0,
                                "change_percent": 0.0,
                                "timestamp": datetime.utcnow().isoformat(),
                                "history": [],  # No history from fallback
                            }
                            logger.info("Using gold-api.com fallback for scenarios", symbol=symbol, price=current_price)
            except Exception as e:
                logger.error("Failed to get fallback price for scenarios", error=str(e), symbol=symbol)

        if current_price is None or current_price == 0:
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
            logger.warning("Ensemble predictor not available, using fallback for all timeframes")
            # Create fallback scenarios for all 3 timeframes
            fallback_scenarios = [
                create_fallback_scenario("1 Saat", current_price, sentiment_score),
                create_fallback_scenario("2 Saat", current_price, sentiment_score),
                create_fallback_scenario("3 Saat", current_price, sentiment_score),
            ]

            # Group by timeframe
            scenarios_by_timeframe = {
                '1h': [fallback_scenarios[0]],
                '2h': [fallback_scenarios[1]],
                '3h': [fallback_scenarios[2]]
            }

            # Calculate ensemble metrics
            ensemble_prediction = sum(s.get('price', 0) for s in fallback_scenarios) / len(fallback_scenarios)
            ensemble_confidence = sum(s.get('confidenceScore', 0) for s in fallback_scenarios) / len(fallback_scenarios)

            # Return structured response
            return {
                "data": {
                    "symbol": symbol,
                    "ensemble_prediction": round(ensemble_prediction, 2),
                    "ensemble_confidence": round(ensemble_confidence, 2),
                    "scenarios": scenarios_by_timeframe,
                },
                "timestamp": datetime.utcnow().isoformat()
            }

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
                # Validate ensemble is ready before attempting prediction
                if not ensemble or not hasattr(ensemble, 'predict'):
                    logger.warning(f"Ensemble predictor not ready for {tf}, using fallback")
                    scenarios.append(create_fallback_scenario(tf, current_price, sentiment_score))
                    continue

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
                    "sentiment_score": sentiment_score,
                    "sentiment_source": sentiment_data["data_source"],
                })

            except Exception as e:
                # Log full traceback for debugging
                logger.error(
                    f"Scenario generation failed for {tf}",
                    exc_info=True,
                    extra={"timeframe": tf, "symbol": symbol, "error": str(e)}
                )

                # Add fallback scenario instead of skipping completely
                scenarios.append(create_fallback_scenario(tf, current_price, sentiment_score))

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

        # Group scenarios by timeframe for frontend
        scenarios_by_timeframe = {
            '1h': [],
            '2h': [],
            '3h': []
        }

        for scenario in scenarios:
            tf = scenario.get('timeframe', '')
            # Map timeframe to frontend format
            if '1' in tf or tf == '1h':
                scenarios_by_timeframe['1h'].append(scenario)
            elif '2' in tf or tf == '2h':
                scenarios_by_timeframe['2h'].append(scenario)
            elif '3' in tf or tf == '3h':
                scenarios_by_timeframe['3h'].append(scenario)

        # Calculate ensemble metrics
        ensemble_prediction = sum(s.get('price', 0) for s in scenarios) / len(scenarios) if scenarios else 0
        ensemble_confidence = sum(s.get('confidenceScore', 0) for s in scenarios) / len(scenarios) if scenarios else 0

        # Return structured response (transformation middleware will convert to camelCase)
        return {
            "data": {
                "symbol": symbol,
                "ensemble_prediction": round(ensemble_prediction, 2),
                "ensemble_confidence": round(ensemble_confidence, 2),
                "scenarios": scenarios_by_timeframe,
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("Failed to generate scenarios", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate prediction scenarios",
        )


@router.get("/scalping-forecast")
async def get_scalping_forecast(
    symbol: str = Query(default="XAUTRY", description="Gold symbol for scalping prediction"),
    minutes: int = Query(default=15, ge=5, le=30, description="Forecast timeframe in minutes (5-30)"),
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get ultra short-term scalping forecast (5-30 minutes).

    Most reliable timeframe: 15-20 minutes
    - 5-10 min: Too volatile, high noise
    - 15-20 min: Optimal - Technical indicators stabilize, sufficient data
    - 20-30 min: External factors increase risk

    Uses high-frequency technical indicators optimized for scalping:
    - 1-minute candlestick data
    - Fast RSI (period=7)
    - Quick MACD (12,26,9)
    - Bollinger Bands (period=20)
    - Volume analysis

    Args:
        symbol: Gold symbol (XAUTRY, XAUUSD, etc.)
        minutes: Forecast timeframe in minutes (default: 15)
        user: Current authenticated user (optional)

    Returns:
        Scalping forecast with high-frequency indicators
    """
    try:
        symbol = validate_symbol(symbol)

        # Get current price
        bq = get_bq_helper()
        price_data = await bq.get_gold_price_data(symbol, include_history=True)
        current_price = price_data["price"] if price_data else None

        if current_price is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No price data available for scalping forecast.",
            )

        # Get sentiment
        sentiment_data = await bq.get_sentiment_score_for_prediction(symbol)
        sentiment_score = sentiment_data["score"]

        # Get high-frequency data (last 100 data points ~ 100 minutes for 1min candles)
        price_history = price_data.get("history", []) if price_data else []
        prices = [p["price"] for p in price_history[-100:]] if price_history else [current_price] * 100

        # Calculate fast technical indicators for scalping
        engine = get_prediction_engine()
        if engine and len(prices) >= 20:
            # Use actual indicators
            indicators = engine.technical_analyzer.calculate_indicators(prices)

            # Calculate additional scalping-specific metrics
            price_volatility = (max(prices[-20:]) - min(prices[-20:])) / current_price * 100
            recent_momentum = (prices[-1] - prices[-5]) / prices[-5] * 100 if len(prices) >= 5 else 0
        else:
            from services.prediction_engine.src.models import TechnicalIndicators
            indicators = TechnicalIndicators()
            price_volatility = 0.5
            recent_momentum = 0.0

        # Get ensemble predictor
        ensemble = get_ensemble_predictor()

        if not ensemble or not settings.enable_ensemble_predictions:
            # Fallback: simple momentum-based prediction
            momentum_factor = recent_momentum * 0.1
            predicted_change = momentum_factor

            return {
                "timeframe": f"{minutes} Dakika",
                "timeframe_minutes": minutes,
                "current_price": round(current_price, 2),
                "predicted_price": round(current_price * (1 + predicted_change / 100), 2),
                "changePercent": round(predicted_change, 3),
                "confidenceScore": 50,
                "direction": "up" if predicted_change > 0 else "down" if predicted_change < 0 else "neutral",
                "volatility_percent": round(price_volatility, 2),
                "momentum_5min": round(recent_momentum, 3),
                "indicators": {
                    "rsi": round(indicators.rsi or 50, 1),
                    "macd": round(indicators.macd or 0, 3),
                    "bollinger_position": "middle",  # Simplified
                },
                "recommendation": "hold" if abs(predicted_change) < 0.1 else ("buy" if predicted_change > 0 else "sell"),
                "risk_level": "high" if price_volatility > 1.0 else "medium" if price_volatility > 0.5 else "low",
                "note": "Ensemble models not enabled - using momentum fallback",
            }

        # Use ensemble for prediction
        from services.prediction_engine.src.predictor import EconomicDataFetcher

        econ_fetcher = EconomicDataFetcher()
        economic_data = await econ_fetcher.fetch_economic_features()

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

        result = await ensemble.predict(
            indicators=indicators,
            sentiment_score=sentiment_score,
            current_price=current_price,
            economic_data=economic_data,
            price_history=prices[-100:],
            feature_history=feature_history,
        )

        # Adjust prediction for shorter timeframe (scale down from 1h baseline)
        scaling_factor = minutes / 60.0  # Scale from 1-hour predictions
        adjusted_change = result['change_percent'] * scaling_factor

        # Determine Bollinger position
        if indicators.bollinger_upper and indicators.bollinger_lower:
            if current_price > indicators.bollinger_upper:
                bollinger_pos = "above_upper"
            elif current_price < indicators.bollinger_lower:
                bollinger_pos = "below_lower"
            else:
                bollinger_pos = "middle"
        else:
            bollinger_pos = "unknown"

        # Risk assessment
        if price_volatility > 1.0 or abs(adjusted_change) > 0.5:
            risk_level = "high"
        elif price_volatility > 0.5 or abs(adjusted_change) > 0.2:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Trading recommendation
        if result['confidence'] == "LOW" or abs(adjusted_change) < 0.05:
            recommendation = "hold"
        elif adjusted_change > 0.1:
            recommendation = "buy"
        elif adjusted_change < -0.1:
            recommendation = "sell"
        else:
            recommendation = "hold"

        confidence_map = {"HIGH": 75, "MEDIUM": 60, "LOW": 45}
        confidence_score = confidence_map.get(result['confidence'], 60)

        # Adjust confidence for shorter timeframes (less reliable)
        if minutes < 15:
            confidence_score = max(40, confidence_score - 15)
        elif minutes >= 20:
            confidence_score = max(45, confidence_score - 10)

        log_audit(
            action="scalping_forecast",
            user=user,
            resource=f"scalping:{symbol}:{minutes}min",
            details={"timeframe_minutes": minutes, "confidence": result['confidence']},
        )

        return {
            "timeframe": f"{minutes} Dakika",
            "timeframe_minutes": minutes,
            "current_price": round(current_price, 2),
            "predicted_price": round(current_price * (1 + adjusted_change / 100), 2),
            "changePercent": round(adjusted_change, 3),
            "confidenceScore": confidence_score,
            "direction": "up" if adjusted_change > 0 else "down" if adjusted_change < 0 else "neutral",
            "volatility_percent": round(price_volatility, 2),
            "momentum_5min": round(recent_momentum, 3),
            "indicators": {
                "rsi": round(indicators.rsi or 50, 1),
                "rsi_condition": "overbought" if (indicators.rsi or 50) > 70 else "oversold" if (indicators.rsi or 50) < 30 else "neutral",
                "macd": round(indicators.macd or 0, 3),
                "macd_momentum": "positive" if (indicators.macd or 0) > 0 else "negative",
                "bollinger_position": bollinger_pos,
                "ema_short": round(indicators.ema_short or current_price, 2),
                "ema_medium": round(indicators.ema_medium or current_price, 2),
            },
            "recommendation": recommendation,
            "risk_level": risk_level,
            "models_used": result['num_models'],
            "ensemble_confidence": result['confidence'],
            "note": f"Optimal scalping timeframe: 15-20 minutes. Current: {minutes} minutes.",
        }

    except Exception as e:
        logger.error("Failed to generate scalping forecast", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate scalping forecast",
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
        # For now, return mock data based on current model weights
        # When backtesting is implemented, replace with real metrics

        # Calculate mock accuracy metrics based on ensemble weights
        # Higher weight = better historical performance (simulated)
        weights = ensemble.weights if ensemble else {
            'lstm': 0.35,
            'xgboost': 0.25,
            'arima': 0.20,
            'random_forest': 0.20
        }

        # Generate mock daily predictions count (3 timeframes * 16 updates per day)
        total_predictions = 48 * days

        # Simulate overall accuracy (weighted average of model accuracies)
        model_accuracies = {
            'lstm': 0.75,
            'xgboost': 0.70,
            'arima': 0.68,
            'random_forest': 0.74
        }

        overall_accuracy = sum(
            model_accuracies.get(model, 0.7) * weight
            for model, weight in weights.items()
        )

        correct_predictions = int(total_predictions * overall_accuracy)

        report = {
            "date": datetime.utcnow().date().isoformat(),
            "period_days": days,
            "data_available": False,  # Will be True when backtesting implemented
            "message": "Mock data based on model weights. Enable backtesting for real metrics.",
            "overall_accuracy": round(overall_accuracy, 2),
            "total_predictions": total_predictions,
            "correct_predictions": correct_predictions,
            "models": [
                {
                    "model_name": "LSTM",
                    "accuracy": model_accuracies['lstm'],
                    "predictions_count": int(total_predictions * weights['lstm']),
                    "weight": weights['lstm'],
                    "enabled": settings.enable_lstm_model if ensemble else True,
                },
                {
                    "model_name": "XGBoost",
                    "accuracy": model_accuracies['xgboost'],
                    "predictions_count": int(total_predictions * weights['xgboost']),
                    "weight": weights['xgboost'],
                    "enabled": settings.enable_xgboost_model if ensemble else True,
                },
                {
                    "model_name": "ARIMA",
                    "accuracy": model_accuracies['arima'],
                    "predictions_count": int(total_predictions * weights['arima']),
                    "weight": weights['arima'],
                    "enabled": settings.enable_arima_model if ensemble else True,
                },
                {
                    "model_name": "Random Forest",
                    "accuracy": model_accuracies['random_forest'],
                    "predictions_count": int(total_predictions * weights['random_forest']),
                    "weight": weights['random_forest'],
                    "enabled": True,
                },
            ],
            "model_status": {
                "lstm": {
                    "enabled": settings.enable_lstm_model if ensemble else True,
                    "initialized": ensemble.lstm._initialized if ensemble and ensemble.lstm else False,
                    "info": ensemble.lstm.get_model_info() if ensemble and ensemble.lstm else None,
                },
                "arima": {
                    "enabled": settings.enable_arima_model if ensemble else True,
                    "initialized": ensemble.arima._initialized if ensemble and ensemble.arima else False,
                    "info": ensemble.arima.get_model_info() if ensemble and ensemble.arima else None,
                },
                "xgboost": {
                    "enabled": settings.enable_xgboost_model if ensemble else True,
                    "initialized": ensemble.xgboost._initialized if ensemble and ensemble.xgboost else False,
                    "info": ensemble.xgboost.get_model_info() if ensemble and ensemble.xgboost else None,
                },
                "random_forest": {
                    "enabled": True,
                    "initialized": True,
                },
            } if ensemble else {},
            "ensemble_weights": weights,
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


def track_genelpara_request():
    """Track daily GenelPara API requests in Firestore.

    Stores atomic counter for daily usage to monitor quota consumption.
    Logs warnings at 80% (800 requests) and 95% (950 requests) thresholds.

    Returns:
        int: Current daily request count, or None if tracking fails
    """
    try:
        db = firestore.Client()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        doc_ref = db.collection("genelpara_usage").document(today)

        # Atomic increment
        doc_ref.set({"count": firestore.Increment(1), "date": today}, merge=True)

        # Get current count
        doc = doc_ref.get()
        current_count = doc.to_dict().get("count", 0) if doc.exists else 0

        # Log warnings at thresholds
        if current_count >= 950:
            logger.error("GenelPara quota critical", count=current_count, threshold="95%", limit=1000)
        elif current_count >= 800:
            logger.warning("GenelPara quota warning", count=current_count, threshold="80%", limit=1000)

        return current_count
    except Exception as e:
        logger.error("Failed to track GenelPara request", error=str(e))
        return None


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
        # Add cache indicator if not present
        if "meta" not in cached:
            cached["meta"] = {}
        cached["meta"]["cached"] = True
        cached["meta"]["source"] = "genelpara"
        return cached

    # Track request before making API call
    daily_count = track_genelpara_request()

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

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (compatible; Sentilyze/1.0)",
            }

            logger.debug(
                "Requesting GenelPara API",
                url=url,
                params=params,
                list_type=list_type,
                symbols=symbols,
                daily_count=daily_count,
            )

            response = await client.get(url, params=params, headers=headers)

            if response.status_code == 415:
                logger.error(
                    "GenelPara returned 415 Unsupported Media Type",
                    url=str(response.url),
                    request_headers=dict(response.request.headers),
                    response_text=response.text[:200],
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="GenelPara API format error. Using fallback data source.",
                )

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

            # Add metadata to response
            data["meta"] = {
                "cached": False,
                "daily_requests": daily_count,
                "source": "genelpara",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Cache the response (60s TTL)
            cache_set(cache_key, data, ttl=60)

            log_audit(
                action="genelpara_proxy_query",
                user=user,
                resource=f"genelpara:{list_type}:{symbols}",
                details={
                    "cached": False,
                    "count": data.get("count", 0),
                    "remaining": remaining,
                    "daily_count": daily_count
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


@router.get("/genelpara-stats")
async def genelpara_stats(
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get GenelPara API usage statistics and quota monitoring.

    Returns daily usage, remaining quota, and health status.
    Useful for monitoring rate limit consumption and planning API calls.

    Returns:
        dict: Statistics including:
            - status: "healthy" | "degraded" | "critical"
            - requests_today: Number of requests made today
            - remaining_quota: Requests remaining before hitting daily limit
            - daily_limit: Total daily limit (1000)
            - quota_percentage: Percentage of quota used
            - reset_in_seconds: Seconds until quota resets (Turkey time midnight)
            - reset_at: ISO timestamp of next reset

    Example:
        GET /gold/genelpara-stats
        Returns:
        {
            "status": "healthy",
            "requests_today": 245,
            "remaining_quota": 755,
            "daily_limit": 1000,
            "quota_percentage": 24.5,
            "reset_in_seconds": 34567,
            "reset_at": "2026-02-07T00:00:00+03:00"
        }
    """
    try:
        db = firestore.Client()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        doc = db.collection("genelpara_usage").document(today).get()

        count = doc.to_dict().get("count", 0) if doc.exists else 0
        remaining = max(0, 1000 - count)

        # Calculate reset time (next midnight Turkey time = UTC+3)
        now = datetime.now(timezone.utc)
        turkey_tz = timezone(timedelta(hours=3))  # UTC+3
        turkey_now = now.astimezone(turkey_tz)
        next_midnight = (turkey_now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        reset_in_seconds = int((next_midnight - turkey_now).total_seconds())

        # Determine health status
        status_value = "healthy"
        if remaining < 50:
            status_value = "critical"
        elif remaining < 200:
            status_value = "degraded"

        return {
            "status": status_value,
            "requests_today": count,
            "remaining_quota": remaining,
            "daily_limit": 1000,
            "quota_percentage": round((count / 1000) * 100, 2),
            "reset_in_seconds": reset_in_seconds,
            "reset_at": next_midnight.isoformat(),
        }
    except Exception as e:
        logger.error("Failed to get GenelPara stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics",
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

    except HTTPException as e:
        if e.status_code == 503:
            # Create fallback indicators from external price APIs
            logger.warning("BigQuery unavailable, using fallback indicators for %s", symbol)

            # Get current price from gold-api.com
            current_price = 2100  # Default
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get("https://api.gold-api.com/price/XAU")
                    if resp.status_code == 200:
                        data = resp.json()
                        current_price = data.get("price", 2100)
            except Exception:
                pass

            # Return basic fallback indicators
            return {
                "data": {
                    "symbol": symbol,
                    "current_price": current_price,
                    "rsi": {"value": 50, "condition": "neutral"},
                    "macd": {"value": 0, "signal": 0, "momentum": "neutral", "histogram": 0},
                    "bollinger": {
                        "upper": round(current_price * 1.02, 2),
                        "middle": current_price,
                        "lower": round(current_price * 0.98, 2),
                        "width": 2.0,
                    },
                    "ema": {"short": current_price, "medium": current_price, "long": current_price},
                    "sma": {"20": current_price, "50": current_price, "200": current_price},
                    "stochastic": {"k": 50, "d": 50, "condition": "neutral"},
                    "atr": 0,
                    "data_points": 0,
                    "data_source": "fallback",
                    "disclaimer": "Fallback göstergeler - BigQuery verileri kullanılamıyor",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
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
    timeframe: str = Query(default="1D", description="Timeframe: 1h, 2h, 3h, 1D, 1W, 1M, 3M, 1Y"),
    limit: int = Query(default=100, ge=1, le=500, description="Max data points"),
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Get real gold price history from BigQuery.

    Returns actual OHLCV data, not synthetic/random data.

    Args:
        symbol: Gold symbol
        timeframe: Time period (1h, 2h, 3h, 1D, 1W, 1M, 3M, 1Y)
        limit: Maximum data points to return
        user: Current authenticated user (optional)

    Returns:
        Historical OHLCV price data
    """
    symbol = validate_symbol(symbol)
    timeframe = sanitize_input(timeframe, max_length=5) or "1D"
    timeframe = timeframe.upper()

    if timeframe not in ("1H", "2H", "3H", "1D", "1W", "1M", "3M", "1Y"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timeframe. Supported: 1h, 2h, 3h, 1D, 1W, 1M, 3M, 1Y",
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


@router.get("/ai-analysis/{symbol}")
async def get_ai_technical_analysis(
    symbol: str,
    request: Request,
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """AI-powered technical analysis commentary using Moonshot Kimi 2.5 + Gemini fallback.

    Premium feature - Requires Trader or Enterprise subscription.
    Provides intelligent analysis of technical indicators with Turkish commentary.

    Features:
    - Firestore cache (60 seconds)
    - Rate limiting (100 req/min)
    - Moonshot Kimi 2.5 (primary)
    - Gemini 2.0 Flash (fallback)
    - Rule-based fallback (last resort)

    Args:
        symbol: Gold symbol (XAUUSD, XAUTRY, etc.)
        request: FastAPI request object
        user: Current authenticated user (required)

    Returns:
        AI-generated technical analysis with signals and recommendations
    """
    try:
        # Check rate limit
        client_id = (user.get("uid") if user else None) or request.client.host
        await check_rate_limit(
            client_id=client_id,
            endpoint="ai_analysis",
            max_requests=100,
            window_seconds=60,
        )

        # Check premium subscription (for now, allow demo access)
        # TODO: Enable strict premium check when auth is implemented
        user_tier = user.get("subscription_tier", "free").lower() if user else "free"
        is_premium = user_tier in ("trader", "enterprise")

        # For demo purposes, allow all users but mark as demo
        demo_mode = not is_premium

        symbol = validate_symbol(symbol)

        # Check Firestore cache first (60 second TTL)
        from sentilyze_core.firestore_cache import get_firestore_cache

        cache = get_firestore_cache()
        cache_key = f"ai_analysis:{symbol}"

        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"AI analysis cache hit for {symbol}")
            return {
                **cached,
                "cached": True,
                "cache_hit_at": datetime.utcnow().isoformat(),
            }

        # Get technical indicators
        bq = get_bq_helper()
        indicators_data = await bq.get_technical_indicators(symbol)

        if not indicators_data:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Technical indicators not available"
            )

        # Build prompt for AI
        indicators = indicators_data.get("indicators", {})
        rsi = indicators.get("rsi", {})
        macd = indicators.get("macd", {})
        bollinger = indicators.get("bollinger", {})
        sma = indicators.get("sma", {})

        prompt = f"""Sen bir profesyonel teknik analiz uzmanısın. Aşağıdaki altın ({symbol}) teknik indikatörlerini analiz et:

**Teknik İndikatörler:**
- RSI (14): {rsi.get('value', 0):.1f} ({rsi.get('condition', 'neutral')})
- MACD: {macd.get('value', 0):.3f} ({macd.get('momentum', 'neutral')} momentum)
- Bollinger Genişliği: {bollinger.get('width', 0):.2f}%
- SMA 20: ${sma.get('20', 0):.2f}
- SMA 50: ${sma.get('50', 0):.2f}

**Görevin:**
1. Kısa bir özet yaz (1-2 cümle)
2. 4 ana teknik sinyal/bulgu belirle
3. Alım-satım önerisi ver (strong_buy/buy/hold/sell/strong_sell)
4. Risk seviyesini belirle (low/medium/high)
5. Güven skoru ver (0-100)

**Önemli Kurallar:**
- Sadece teknik analiz yap, yatırım tavsiyesi verme
- "Bu analiz bilgilendirme amaçlıdır, yatırım tavsiyesi değildir" vurgusu yap
- Türkçe yaz
- JSON formatında yanıt ver

**JSON Formatı:**
{{
  "summary": "Kısa özet buraya...",
  "signals": [
    "Sinyal 1: RSI 50 civarında - trend belirsiz",
    "Sinyal 2: MACD histogramı artışta",
    "Sinyal 3: Fiyat Bollinger ortası yakınında",
    "Sinyal 4: SMA 20 > SMA 50 - orta vadeli yükseliş"
  ],
  "recommendation": "hold",
  "risk_level": "medium",
  "confidence": 68
}}

**Not:** Sadece JSON yanıt ver, başka açıklama ekleme."""

        # Try Moonshot API
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                moonshot_response = await client.post(
                    f"{settings.moonshot_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.moonshot_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.moonshot_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "Sen teknik analiz uzmanısın. Sadece JSON formatında yanıt ver, başka açıklama ekleme."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3,
                        "max_tokens": 800,
                    }
                )

                if moonshot_response.status_code == 200:
                    data = moonshot_response.json()
                    content = data["choices"][0]["message"]["content"]

                    # Parse JSON from response
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        analysis = json.loads(json_match.group())

                        log_audit(
                            action="ai_analysis",
                            user=user,
                            resource=f"ai_analysis:{symbol}",
                            details={"model": "moonshot-kimi-2.5", "confidence": analysis.get("confidence", 0)}
                        )

                        result = {
                            "symbol": symbol,
                            "analysis": analysis,
                            "model": "moonshot-kimi-2.5",
                            "generated_at": datetime.utcnow().isoformat(),
                            "disclaimer": "Bu analiz istatistiksel model çıktısıdır, yatırım tavsiyesi niteliği taşımaz.",
                            "demo_mode": demo_mode,
                            "subscription_required": "Trader veya Enterprise" if demo_mode else None,
                        }

                        # Cache for 60 seconds
                        await cache.set(cache_key, result, ttl=60)

                        return result
                    else:
                        logger.warning("Moonshot returned non-JSON response")
                        raise ValueError("Invalid JSON response from Moonshot")
                else:
                    logger.warning(f"Moonshot API error: {moonshot_response.status_code}")
                    raise ValueError(f"Moonshot API error: {moonshot_response.status_code}")

        except Exception as e:
            logger.warning(f"Moonshot AI failed: {e}, trying Gemini fallback")

            # Fallback 1: Try Gemini 2.0 Flash (Vertex AI)
            try:
                import vertexai
                from vertexai.generative_models import GenerativeModel

                vertexai.init(
                    project=settings.vertex_ai_project_id or settings.google_cloud_project,
                    location=settings.vertex_ai_location
                )

                gemini_model = GenerativeModel("gemini-2.0-flash-exp")
                gemini_response = gemini_model.generate_content(
                    f"""Sen teknik analiz uzmanısın. JSON formatında yanıt ver.

{prompt}""",
                    generation_config={
                        "temperature": 0.3,
                        "max_output_tokens": 800,
                    }
                )

                content = gemini_response.text

                # Parse JSON from response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())

                    log_audit(
                        action="ai_analysis",
                        user=user,
                        resource=f"ai_analysis:{symbol}",
                        details={"model": "gemini-2.0-flash", "confidence": analysis.get("confidence", 0)}
                    )

                    result = {
                        "symbol": symbol,
                        "analysis": analysis,
                        "model": "gemini-2.0-flash-exp",
                        "generated_at": datetime.utcnow().isoformat(),
                        "disclaimer": "Bu analiz istatistiksel model çıktısıdır, yatırım tavsiyesi niteliği taşımaz.",
                        "demo_mode": demo_mode,
                        "subscription_required": "Trader veya Enterprise" if demo_mode else None,
                    }

                    # Cache for 60 seconds
                    await cache.set(cache_key, result, ttl=60)

                    return result

            except Exception as gemini_error:
                logger.warning(f"Gemini fallback also failed: {gemini_error}, using rule-based")

            # Fallback 2: Rule-based analysis
            rsi_val = rsi.get('value', 50)
            macd_val = macd.get('value', 0)
            bollinger_width = bollinger.get('width', 2.0)

            # Determine recommendation
            signals_count = 0
            if rsi_val > 70:
                signals_count -= 2  # Overbought
            elif rsi_val < 30:
                signals_count += 2  # Oversold

            if macd_val > 0:
                signals_count += 1  # Positive momentum
            else:
                signals_count -= 1  # Negative momentum

            if sma.get('20', 0) > sma.get('50', 0):
                signals_count += 1  # Uptrend
            else:
                signals_count -= 1  # Downtrend

            # Map signals to recommendation
            if signals_count >= 3:
                recommendation = "strong_buy"
            elif signals_count >= 1:
                recommendation = "buy"
            elif signals_count <= -3:
                recommendation = "strong_sell"
            elif signals_count <= -1:
                recommendation = "sell"
            else:
                recommendation = "hold"

            # Risk level based on volatility
            if bollinger_width > 3.0:
                risk_level = "high"
            elif bollinger_width > 1.5:
                risk_level = "medium"
            else:
                risk_level = "low"

            analysis = {
                "summary": f"Teknik göstergeler karışık sinyaller veriyor. RSI {rsi.get('condition', 'nötr')} bölgede, MACD {macd.get('momentum', 'nötr')} momentum gösteriyor.",
                "signals": [
                    f"RSI {rsi_val:.1f} - {'aşırı alım bölgesinde' if rsi_val > 70 else 'aşırı satım bölgesinde' if rsi_val < 30 else 'nötr bölgede'}",
                    f"MACD {'pozitif' if macd_val > 0 else 'negatif'} momentum gösteriyor",
                    f"Bollinger genişliği {bollinger_width:.2f}% - {'yüksek volatilite' if bollinger_width > 3 else 'normal volatilite'}",
                    f"SMA 20 {'üzerinde' if sma.get('20', 0) > sma.get('50', 0) else 'altında'} SMA 50 - {'yükseliş' if sma.get('20', 0) > sma.get('50', 0) else 'düşüş'} trendi"
                ],
                "recommendation": recommendation,
                "risk_level": risk_level,
                "confidence": 55 if recommendation == "hold" else 65,
            }

            result = {
                "symbol": symbol,
                "analysis": analysis,
                "model": "rule-based-fallback",
                "generated_at": datetime.utcnow().isoformat(),
                "disclaimer": "Bu analiz istatistiksel model çıktısıdır, yatırım tavsiyesi niteliği taşımaz.",
                "demo_mode": demo_mode,
                "subscription_required": "Trader veya Enterprise" if demo_mode else None,
                "note": "AI model unavailable, using rule-based analysis"
            }

            # Cache for 60 seconds
            await cache.set(cache_key, result, ttl=60)

            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("AI analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI analysis"
        )


# ---------------------------------------------------------------------------
# Harem Gold Prices Proxy (enuygunfinans.com / Foreks data)
# ---------------------------------------------------------------------------

import re as _re

_HAREM_URL = "https://www.enuygunfinans.com/altin-fiyatlari/kaynaklar/harem/"
_HAREM_GOLD_TYPES: list[tuple[str, str]] = [
    ("Gram Altın", "GA"),
    ("Çeyrek Altın", "C"),
    ("Yarım Altın", "Y"),
    ("Tam Altın", "T"),
    ("Ata Altın", "ATA"),
]


def _parse_tr_number(text: str) -> float | None:
    """Parse Turkish-formatted number: '7.196,55' -> 7196.55"""
    if not text:
        return None
    cleaned = text.strip().replace(".", "").replace(",", ".")
    cleaned = _re.sub(r"[^\d.\-]", "", cleaned)
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _parse_harem_html(html: str) -> dict[str, Any]:
    """Parse gold prices from enuygunfinans HTML table."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, Any] = {}

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        name_text = _re.sub(r"\d{2}:\d{2}:\d{2}$", "", cells[0].get_text(strip=True)).strip()

        matched_symbol = None
        for tr_name, symbol in _HAREM_GOLD_TYPES:
            if tr_name in name_text:
                matched_symbol = symbol
                break
        if not matched_symbol:
            continue

        buy = _parse_tr_number(cells[1].get_text(strip=True))

        # Sell cell may contain appended change%: "7.358,31%0,01"
        sell_text = cells[2].get_text(strip=True)
        parts = sell_text.split("%")
        sell = _parse_tr_number(parts[0]) if parts[0] else None
        change_pct = _parse_tr_number(parts[1]) if len(parts) > 1 and parts[1] else None

        high = _parse_tr_number(cells[3].get_text(strip=True)) if len(cells) > 3 else None
        low = _parse_tr_number(cells[4].get_text(strip=True)) if len(cells) > 4 else None

        if buy or sell:
            result[matched_symbol] = {
                "alis": str(buy) if buy else "0",
                "satis": str(sell) if sell else "0",
                "degisim": "0",
                "oran": str(change_pct) if change_pct else "0",
                "yuksek": str(high) if high else "0",
                "dusuk": str(low) if low else "0",
            }

    return result


@router.get("/harem-proxy")
async def harem_proxy(
    symbols: str = Query(default="GA", description="Comma-separated symbols: GA, C, Y, T, ATA"),
    user: dict = Depends(get_optional_user),
) -> dict[str, Any]:
    """Proxy for Turkish gold prices from Harem via enuygunfinans.com (Foreks data).

    Returns buy/sell prices in TRY with the same response format as genelpara-proxy,
    making it a drop-in replacement for the frontend.

    Response format matches GenelPara for seamless fallback:
        {
            "success": true,
            "data": {
                "GA": {"alis": "7196.55", "satis": "7327.84", "degisim": "0", "oran": "0.42", ...}
            },
            "meta": {"source": "harem", "cached": false}
        }
    """
    symbols_clean = sanitize_input(symbols, max_length=100) or "GA"
    requested = {s.strip().upper() for s in symbols_clean.split(",")}

    # Check cache (60s TTL)
    cache_key = f"harem:{symbols_clean}"
    cached = cache_get(cache_key)
    if cached is not None:
        logger.debug("Returning cached Harem data", symbols=symbols_clean)
        if "meta" not in cached:
            cached["meta"] = {}
        cached["meta"]["cached"] = True
        return cached

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.5,en;q=0.3",
            },
            follow_redirects=True,
        ) as client:
            response = await client.get(_HAREM_URL)
            response.raise_for_status()

            all_prices = _parse_harem_html(response.text)
            if not all_prices:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to parse Harem gold prices (HTML structure may have changed)",
                )

            # Filter to requested symbols
            filtered = {k: v for k, v in all_prices.items() if k in requested}
            if not filtered:
                filtered = all_prices  # Return all if no match

            result: dict[str, Any] = {
                "success": True,
                "count": len(filtered),
                "data": filtered,
                "meta": {
                    "cached": False,
                    "source": "harem",
                    "provider": "enuygunfinans/foreks",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }

            cache_set(cache_key, result, ttl=60)

            log_audit(
                action="harem_proxy_query",
                user=user,
                resource=f"harem:{symbols_clean}",
                details={"cached": False, "count": len(filtered)},
            )

            return result

    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        logger.error("Harem proxy HTTP error", status_code=e.response.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Harem source returned HTTP {e.response.status_code}",
        )
    except Exception as e:
        logger.error("Harem proxy error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch Harem gold prices",
        )
