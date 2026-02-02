"""Admin Panel FastAPI application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .db.session import close_db, init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    print(f"Starting {settings.service_name}...")
    print(f"Environment: {settings.environment}")
    print(f"Debug mode: {settings.debug}")

    # Initialize database
    if settings.is_development:
        await init_db()

    yield

    # Shutdown
    print(f"Shutting down {settings.service_name}...")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="Sentilyze Admin Panel API",
    description="Admin panel for monitoring and managing the Sentilyze platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": "1.0.0",
        "environment": settings.environment,
    }


@app.get("/ready", tags=["Health"])
async def readiness_check() -> dict:
    """Readiness check endpoint."""
    # TODO: Add database connection check
    return {
        "status": "ready",
        "service": settings.service_name,
        "checks": {
            "database": "healthy",
        },
    }


@app.get("/", tags=["Root"])
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": "Sentilyze Admin Panel API",
        "version": "1.0.0",
        "environment": settings.environment,
        "docs": f"/docs" if settings.is_development else "disabled",
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc) if settings.debug else None},
    )


# Register routers
from .api.v1.router import api_router

app.include_router(api_router, prefix="/api/v1")
