"""API Gateway main application with unified features."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .logging import configure_logging, get_logger
from .middleware.rate_limit import rate_limit_middleware, close_rate_limiter
from .middleware.redis import init_redis, close_redis, cache_info
from .routes import register_routers

settings = get_settings()
logger = get_logger(__name__)


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connected", connections=len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("WebSocket disconnected", connections=len(self.active_connections))

    async def broadcast(self, message: dict) -> None:
        """Broadcast message to all connections."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


# Global connection manager
manager = ConnectionManager()


# WebSocket origin helpers (CORS middleware does not apply to WS)
def _normalize_origin(value: str | None) -> str | None:
    """Normalize origin header value."""
    if value is None:
        return None
    normalized = value.strip().lower()
    normalized = normalized.rstrip("/")
    return normalized or None


def _is_origin_allowed(origin: str | None) -> bool:
    """Check if WebSocket origin is allowed."""
    normalized_origin = _normalize_origin(origin)
    
    # Non-browser clients may omit Origin; allow them by default
    if normalized_origin is None:
        return True

    allowed_origins = settings.get_allowed_origins_list()
    
    # If "*" is configured, allow any Origin
    if "*" in allowed_origins:
        return True

    normalized_allowed = {_normalize_origin(o) for o in allowed_origins}
    normalized_allowed.discard(None)

    return normalized_origin in normalized_allowed


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    configure_logging(
        log_level=settings.log_level,
        service_name="api-gateway",
        environment=settings.environment,
    )
    logger.info(
        "Starting API Gateway",
        version=settings.app_version,
        environment=settings.environment,
    )
    logger.info(
        "Features enabled",
        crypto=settings.feature_crypto_routes,
        gold=settings.feature_gold_routes,
        sentiment=settings.feature_sentiment_routes,
        analytics=settings.feature_analytics_routes,
        websocket=settings.feature_websocket,
    )

    # Initialize Redis cache
    redis_connected = await init_redis()
    logger.info("Cache initialized", backend="redis" if redis_connected else "memory")

    yield

    # Shutdown
    logger.info("Shutting down API Gateway")
    await close_redis()
    await close_rate_limiter()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Unified API Gateway for Sentilyze - Crypto and Gold Market Analysis",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins_list(),
    allow_credentials=settings.cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
@app.middleware("http")
async def rate_limit(request, call_next):
    """Apply rate limiting."""
    return await rate_limit_middleware(request, call_next)

# Register all routes
register_routers(app)


# WebSocket endpoint (if enabled)
if settings.feature_websocket:
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time updates."""
        # Origin allowlist for browser clients
        origin = websocket.headers.get("origin")
        if not _is_origin_allowed(origin):
            logger.warning("WebSocket rejected by origin", origin=origin)
            await websocket.close(code=1008)
            return

        await manager.connect(websocket)
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                
                # Echo back with acknowledgment
                await websocket.send_json({
                    "type": "ack",
                    "message": "Connected to Sentilyze real-time feed",
                    "received": data,
                })
        except WebSocketDisconnect:
            manager.disconnect(websocket)
        except Exception as e:
            logger.error("WebSocket error", error=str(e))
            manager.disconnect(websocket)


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "description": "Unified API Gateway for Crypto and Gold Market Analysis",
        "environment": settings.environment,
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "ready": "/ready",
            "live": "/live",
        },
        "features": {
            "crypto": settings.feature_crypto_routes,
            "gold": settings.feature_gold_routes,
            "sentiment": settings.feature_sentiment_routes,
            "analytics": settings.feature_analytics_routes,
            "websocket": settings.feature_websocket,
        },
    }


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "cache": cache_info(),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
    )
