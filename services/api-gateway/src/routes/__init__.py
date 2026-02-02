"""API routes registration module."""

from fastapi import FastAPI

from ..config import get_settings
from ..logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Import all route modules
from .auth import router as auth_router
from .health import router as health_router
from .crypto import router as crypto_router
from .gold import router as gold_router
from .sentiment import router as sentiment_router
from .analytics import router as analytics_router
from .admin import router as admin_router
from .analysis import router as analysis_router


def register_routers(app: FastAPI) -> None:
    """Register all API routes with feature flag support.
    
    Args:
        app: FastAPI application instance
    """
    # Always include health and auth routes
    app.include_router(health_router)
    app.include_router(auth_router)
    logger.info("Registered required routes: health, auth")
    
    # Conditional routes based on feature flags
    if settings.feature_crypto_routes:
        app.include_router(crypto_router)
        logger.info("Registered route: crypto")
    
    if settings.feature_gold_routes:
        app.include_router(gold_router)
        logger.info("Registered route: gold")
    
    if settings.feature_sentiment_routes:
        app.include_router(sentiment_router)
        logger.info("Registered route: sentiment")
    
    if settings.feature_analytics_routes:
        app.include_router(analytics_router)
        logger.info("Registered route: analytics")
    
    if settings.feature_admin_routes:
        app.include_router(admin_router)
        logger.info("Registered route: admin")
    
    # Analysis routes - always enabled for core functionality
    app.include_router(analysis_router)
    logger.info("Registered route: analysis")
    
    logger.info(
        "Router registration complete",
        crypto=settings.feature_crypto_routes,
        gold=settings.feature_gold_routes,
        sentiment=settings.feature_sentiment_routes,
        analytics=settings.feature_analytics_routes,
        admin=settings.feature_admin_routes,
    )


__all__ = [
    "register_routers",
    "health_router",
    "auth_router",
    "crypto_router",
    "gold_router",
    "sentiment_router",
    "analytics_router",
    "admin_router",
]
