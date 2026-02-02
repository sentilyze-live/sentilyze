#!/usr/bin/env python3
"""Unified Ingestion Service for Sentilyze.

This service merges collectors from both v3 (crypto) and Gold projects:
- v3: Reddit, RSS, Binance
- Gold: GoldAPI, Finnhub, Turkish scrapers
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sentilyze_core import configure_logging, DataSource, RawEvent, get_logger, get_settings
from sentilyze_core.logging import get_logger

from .collectors import (
    BinanceCollector,
    CryptoPanicCollector,
    FinnhubNewsCollector,
    FredCollector,
    GoldAPICollector,
    LunarCrushCollector,
    RedditCollector,
    RSSCollector,
    SantimentCollector,
    TurkishScrapersCollector,
)
from .publisher import EventPublisher
from .scheduler import CollectionScheduler

logger = get_logger(__name__)
settings = get_settings()

# Global collector instances
collector_instances: dict[str, Any] = {}
event_publisher: EventPublisher | None = None
scheduler: CollectionScheduler | None = None

# Track initialization failures for health checks
collector_init_failures: dict[str, str] = {}
collector_init_status: dict[str, bool] = {}


def _require_ingestion_admin(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Optional admin guard for manual trigger endpoints.

    - If `INGESTION_ADMIN_API_KEY` is set, require `X-API-Key` to match it.
    - If not set, rely on platform-level protection (Cloud Run IAM / network).
    """
    expected = settings.ingestion_admin_api_key
    if expected is None:
        return
    if x_api_key == expected:
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    configure_logging(
        log_level=settings.log_level,
        service_name="ingestion",
        environment=settings.environment,
    )
    logger.info("Starting unified ingestion service")
    if settings.environment == "production" and not settings.ingestion_admin_api_key:
        logger.warning(
            "INGESTION_ADMIN_API_KEY is not set; relying on platform-level auth for /collect endpoints"
        )

    global event_publisher, collector_instances, scheduler

    # Initialize event publisher
    event_publisher = EventPublisher()
    await event_publisher.initialize()

    # Initialize collectors based on feature flags
    # v3 Collectors (Crypto)
    if settings.enable_reddit_collector and settings.reddit_client_id:
        try:
            collector = RedditCollector(event_publisher)
            await collector.initialize()
            collector_instances["reddit"] = collector
            collector_init_status["reddit"] = True
            logger.info("Reddit collector initialized")
        except Exception as e:
            collector_init_failures["reddit"] = str(e)
            collector_init_status["reddit"] = False
            logger.error("Failed to initialize Reddit collector", error=str(e))

    if settings.enable_rss_collector:
        try:
            collector = RSSCollector(event_publisher)
            await collector.initialize()
            collector_instances["rss"] = collector
            collector_init_status["rss"] = True
            logger.info("RSS collector initialized")
        except Exception as e:
            collector_init_failures["rss"] = str(e)
            collector_init_status["rss"] = False
            logger.error("Failed to initialize RSS collector", error=str(e))

    if settings.enable_binance_collector:
        try:
            collector = BinanceCollector(event_publisher)
            await collector.initialize()
            collector_instances["binance"] = collector
            collector_init_status["binance"] = True
            logger.info("Binance collector initialized")
        except Exception as e:
            collector_init_failures["binance"] = str(e)
            collector_init_status["binance"] = False
            logger.error("Failed to initialize Binance collector", error=str(e))

    # Gold Collectors
    if settings.enable_goldapi_collector and settings.goldapi_api_key:
        try:
            collector = GoldAPICollector(
                publisher=event_publisher,
                api_key=settings.goldapi_api_key,
                symbols=settings.goldapi_symbols or ["XAU"],
                currencies=settings.goldapi_currencies or ["USD", "EUR", "TRY"],
                interval=settings.goldapi_interval or 60,
            )
            await collector.initialize()
            collector_instances["goldapi"] = collector
            collector_init_status["goldapi"] = True
            logger.info("GoldAPI collector initialized")
        except Exception as e:
            collector_init_failures["goldapi"] = str(e)
            collector_init_status["goldapi"] = False
            logger.error("Failed to initialize GoldAPI collector", error=str(e))

    if settings.enable_finnhub_collector and settings.finnhub_api_key:
        try:
            collector = FinnhubNewsCollector(
                publisher=event_publisher,
                api_key=settings.finnhub_api_key,
                symbols=settings.finnhub_symbols or ["GLD", "IAU", "XAU"],
                interval_seconds=settings.finnhub_interval or 300,
            )
            await collector.initialize()
            collector_instances["finnhub"] = collector
            collector_init_status["finnhub"] = True
            logger.info("Finnhub collector initialized")
        except Exception as e:
            collector_init_failures["finnhub"] = str(e)
            collector_init_status["finnhub"] = False
            logger.error("Failed to initialize Finnhub collector", error=str(e))

    if settings.enable_turkish_scrapers:
        try:
            collector = TurkishScrapersCollector(event_publisher)
            await collector.initialize()
            collector_instances["turkish_scrapers"] = collector
            collector_init_status["turkish_scrapers"] = True
            logger.info("Turkish scrapers collector initialized")
        except Exception as e:
            collector_init_failures["turkish_scrapers"] = str(e)
            collector_init_status["turkish_scrapers"] = False
            logger.error("Failed to initialize Turkish scrapers", error=str(e))

    # LunarCrush Collector (Crypto Social Sentiment)
    if settings.enable_lunarcrush_collector and settings.lunarcrush_api_key:
        try:
            collector = LunarCrushCollector(
                publisher=event_publisher,
                api_key=settings.lunarcrush_api_key,
                symbols=settings.lunarcrush_symbols or ["BTC", "ETH", "BNB", "SOL", "ADA", "XRP"],
            )
            await collector.initialize()
            collector_instances["lunarcrush"] = collector
            collector_init_status["lunarcrush"] = True
            logger.info("LunarCrush collector initialized")
        except Exception as e:
            collector_init_failures["lunarcrush"] = str(e)
            collector_init_status["lunarcrush"] = False
            logger.error("Failed to initialize LunarCrush collector", error=str(e))

    # CryptoPanic Collector (Crypto News)
    if settings.enable_cryptopanic_collector and settings.cryptopanic_api_key:
        try:
            collector = CryptoPanicCollector(
                publisher=event_publisher,
                api_key=settings.cryptopanic_api_key,
                currencies=settings.cryptopanic_currencies or ["BTC", "ETH", "BNB", "SOL", "ADA", "XRP"],
                filter_type=settings.cryptopanic_filter,
            )
            await collector.initialize()
            collector_instances["cryptopanic"] = collector
            collector_init_status["cryptopanic"] = True
            logger.info("CryptoPanic collector initialized")
        except Exception as e:
            collector_init_failures["cryptopanic"] = str(e)
            collector_init_status["cryptopanic"] = False
            logger.error("Failed to initialize CryptoPanic collector", error=str(e))

    # Santiment Collector (On-chain Metrics)
    if settings.enable_santiment_collector and settings.santiment_api_key:
        try:
            collector = SantimentCollector(
                publisher=event_publisher,
                api_key=settings.santiment_api_key,
                assets=settings.santiment_assets or ["bitcoin", "ethereum", "binance-coin", "solana", "cardano", "ripple"],
                metrics=settings.santiment_metrics,
            )
            await collector.initialize()
            collector_instances["santiment"] = collector
            collector_init_status["santiment"] = True
            logger.info("Santiment collector initialized")
        except Exception as e:
            collector_init_failures["santiment"] = str(e)
            collector_init_status["santiment"] = False
            logger.error("Failed to initialize Santiment collector", error=str(e))

    # FRED Collector (Federal Reserve Economic Data)
    if settings.enable_fred_collector and settings.fred_api_key:
        try:
            collector = FredCollector(
                publisher=event_publisher,
                api_key=settings.fred_api_key,
                series=settings.fred_series,
            )
            await collector.initialize()
            collector_instances["fred"] = collector
            collector_init_status["fred"] = True
            logger.info("FRED collector initialized")
        except Exception as e:
            collector_init_failures["fred"] = str(e)
            collector_init_status["fred"] = False
            logger.error("Failed to initialize FRED collector", error=str(e))

    # Initialize scheduler for periodic collection
    if settings.enable_scheduler:
        scheduler = CollectionScheduler(collector_instances, event_publisher)
        await scheduler.start()
        logger.info("Collection scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down ingestion service")

    if scheduler:
        await scheduler.stop()

    for name, collector in collector_instances.items():
        try:
            await collector.close()
            logger.info(f"Collector {name} closed")
        except Exception as e:
            logger.error(f"Error closing collector {name}", error=str(e))

    if event_publisher:
        await event_publisher.close()


app = FastAPI(
    title="Sentilyze Unified Ingestion Service",
    description="Unified data ingestion service for crypto and gold market data",
    version="4.0.0",
    lifespan=lifespan,
)

# CORS middleware - credentials disabled for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Health check endpoint with detailed collector status."""
    active_collectors = list(collector_instances.keys())
    
    # Determine overall health - healthy if critical collectors are running
    # Consider failed initializations that shouldn't be critical
    total_expected = sum([
        1 if settings.enable_reddit_collector and settings.reddit_client_id else 0,
        1 if settings.enable_rss_collector else 0,
        1 if settings.enable_binance_collector else 0,
        1 if settings.enable_goldapi_collector and settings.goldapi_api_key else 0,
        1 if settings.enable_finnhub_collector and settings.finnhub_api_key else 0,
        1 if settings.enable_turkish_scrapers else 0,
    ])
    
    total_active = len(active_collectors)
    health_status = "healthy" if total_active > 0 or total_expected == 0 else "degraded"
    
    return {
        "status": health_status,
        "service": "ingestion",
        "collectors": {
            "active": active_collectors,
            "expected": total_expected,
            "active_count": total_active,
        },
        "initialization": {
            "status": collector_init_status,
            "failures": {
                name: error for name, error in collector_init_failures.items()
            } if collector_init_failures else None,
        },
        "version": "4.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["health"])
async def readiness_check() -> dict:
    """Readiness check endpoint."""
    checks = {
        "publisher": event_publisher is not None,
        "reddit": collector_instances.get("reddit") is not None if settings.enable_reddit_collector else True,
        "rss": collector_instances.get("rss") is not None if settings.enable_rss_collector else True,
        "binance": collector_instances.get("binance") is not None if settings.enable_binance_collector else True,
        "goldapi": collector_instances.get("goldapi") is not None if settings.enable_goldapi_collector else True,
        "finnhub": collector_instances.get("finnhub") is not None if settings.enable_finnhub_collector else True,
        "turkish_scrapers": collector_instances.get("turkish_scrapers") is not None if settings.enable_turkish_scrapers else True,
    }

    all_ready = all(checks.values())

    if not all_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not ready", "checks": checks},
        )

    return {"status": "ready", "checks": checks}


@app.post("/collect/reddit", tags=["collectors"])
async def trigger_reddit_collection(
    subreddit: str | None = None,
    limit: int = 100,
    _: None = Depends(_require_ingestion_admin),
) -> dict:
    """Manually trigger Reddit collection."""
    collector = collector_instances.get("reddit")
    if not collector:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reddit collector not initialized",
        )

    try:
        count = await collector.collect(subreddit=subreddit, limit=limit)
        return {"status": "success", "collected": count, "source": "reddit"}
    except Exception as e:
        logger.error("Reddit collection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Collection failed: {str(e)}",
        )


@app.post("/collect/rss", tags=["collectors"])
async def trigger_rss_collection(
    feed_url: str | None = None,
    _: None = Depends(_require_ingestion_admin),
) -> dict:
    """Manually trigger RSS collection."""
    collector = collector_instances.get("rss")
    if not collector:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RSS collector not initialized",
        )

    try:
        count = await collector.collect(feed_url=feed_url)
        return {"status": "success", "collected": count, "source": "rss"}
    except Exception as e:
        logger.error("RSS collection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Collection failed: {str(e)}",
        )


@app.post("/collect/binance", tags=["collectors"])
async def trigger_binance_collection(
    symbol: str | None = None,
    _: None = Depends(_require_ingestion_admin),
) -> dict:
    """Manually trigger Binance collection."""
    collector = collector_instances.get("binance")
    if not collector:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Binance collector not initialized",
        )

    try:
        count = await collector.collect(symbol=symbol)
        return {"status": "success", "collected": count, "source": "binance"}
    except Exception as e:
        logger.error("Binance collection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Collection failed: {str(e)}",
        )


@app.post("/collect/goldapi", tags=["collectors"])
async def trigger_goldapi_collection(
    symbol: str | None = None,
    _: None = Depends(_require_ingestion_admin),
) -> dict:
    """Manually trigger GoldAPI collection."""
    collector = collector_instances.get("goldapi")
    if not collector:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GoldAPI collector not initialized",
        )

    try:
        events = await collector.collect(symbol=symbol)
        message_ids = await collector.publish_events(events)
        return {"status": "success", "collected": len(events), "published": len(message_ids), "source": "goldapi"}
    except Exception as e:
        logger.error("GoldAPI collection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Collection failed: {str(e)}",
        )


@app.post("/collect/finnhub", tags=["collectors"])
async def trigger_finnhub_collection(
    symbol: str | None = None,
    _: None = Depends(_require_ingestion_admin),
) -> dict:
    """Manually trigger Finnhub news collection."""
    collector = collector_instances.get("finnhub")
    if not collector:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Finnhub collector not initialized",
        )

    try:
        events = await collector.collect(symbol=symbol)
        message_ids = await collector.publish_events(events)
        return {"status": "success", "collected": len(events), "published": len(message_ids), "source": "finnhub"}
    except Exception as e:
        logger.error("Finnhub collection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Collection failed: {str(e)}",
        )


@app.post("/collect/turkish", tags=["collectors"])
async def trigger_turkish_collection(
    source: str | None = None,
    _: None = Depends(_require_ingestion_admin),
) -> dict:
    """Manually trigger Turkish scrapers collection.
    
    Args:
        source: Specific scraper to run (truncgil, harem_altin, nadir_doviz, tcmb)
    """
    collector = collector_instances.get("turkish_scrapers")
    if not collector:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Turkish scrapers not initialized",
        )

    try:
        if source:
            events = await collector.collect_from_source(source)
        else:
            events = await collector.collect_all()
        message_ids = await collector.publish_events(events)
        return {
            "status": "success", 
            "collected": len(events), 
            "published": len(message_ids), 
            "source": "turkish_scrapers",
            "requested_source": source,
        }
    except Exception as e:
        logger.error("Turkish scrapers collection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Collection failed: {str(e)}",
        )


@app.post("/collect/all", tags=["collectors"])
async def trigger_all_collection(
    _: None = Depends(_require_ingestion_admin),
) -> dict:
    """Trigger collection from all enabled collectors."""
    results = {}
    total_collected = 0

    for name, collector in collector_instances.items():
        try:
            if name in ["goldapi", "finnhub", "turkish_scrapers"]:
                events = await collector.collect()
                message_ids = await collector.publish_events(events)
                results[name] = {"status": "success", "collected": len(events), "published": len(message_ids)}
                total_collected += len(events)
            else:
                count = await collector.collect()
                results[name] = {"status": "success", "collected": count}
                total_collected += count
        except Exception as e:
            logger.error(f"Collection failed for {name}", error=str(e))
            results[name] = {"status": "error", "error": str(e)}

    return {
        "status": "completed",
        "results": results,
        "total_collected": total_collected,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/status", tags=["status"])
async def get_status(
    _: None = Depends(_require_ingestion_admin),
) -> dict:
    """Get collector status and metrics."""
    status_info = {}
    
    for name in ["reddit", "rss", "binance", "goldapi", "finnhub", "turkish_scrapers"]:
        enabled_attr = f"enable_{name}_collector"
        if name == "turkish_scrapers":
            enabled_attr = "enable_turkish_scrapers"
        
        status_info[name] = {
            "enabled": getattr(settings, enabled_attr, False),
            "initialized": name in collector_instances,
        }

    return {
        "service": "ingestion",
        "version": "4.0.0",
        "collectors": status_info,
        "scheduler_enabled": settings.enable_scheduler,
        "active_collectors": list(collector_instances.keys()),
    }


@app.get("/collectors/{collector_name}/config", tags=["status"])
async def get_collector_config(
    collector_name: str,
    _: None = Depends(_require_ingestion_admin),
) -> dict:
    """Get configuration for a specific collector."""
    configs = {
        "reddit": {
            "default_subreddits": collector_instances["reddit"].DEFAULT_SUBREDDITS if "reddit" in collector_instances else None,
            "crypto_symbols": collector_instances["reddit"].CRYPTO_SYMBOLS if "reddit" in collector_instances else None,
        },
        "rss": {
            "default_feeds": collector_instances["rss"].DEFAULT_FEEDS if "rss" in collector_instances else None,
        },
        "binance": {
            "default_symbols": collector_instances["binance"].DEFAULT_SYMBOLS if "binance" in collector_instances else None,
        },
        "goldapi": {
            "symbols": settings.goldapi_symbols,
            "currencies": settings.goldapi_currencies,
            "interval": settings.goldapi_interval,
        },
        "finnhub": {
            "symbols": settings.finnhub_symbols,
            "interval": settings.finnhub_interval,
        },
        "turkish_scrapers": {
            "sources": ["truncgil", "harem_altin", "nadir_doviz", "tcmb"],
        },
    }
    
    if collector_name not in configs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collector {collector_name} not found",
        )
    
    return {
        "collector": collector_name,
        "config": configs.get(collector_name),
        "enabled": getattr(settings, f"enable_{collector_name}_collector".replace("turkish_scrapers", "turkish_scrapers"), False),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development if hasattr(settings, "is_development") else False,
    )
