"""Health check endpoints with real service validation."""

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse

from ..config import get_settings
from ..logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter(tags=["health"])


async def check_cache() -> tuple[bool, str]:
    """Check cache connection (Firestore or fallback)."""
    try:
        from sentilyze_core import get_cache_client
        cache = get_cache_client()
        await cache.set("health_check", {"status": "ok"}, ttl=10, namespace="health")
        result = await cache.get("health_check", namespace="health")
        await cache.close()
        return True, "connected" if result else "warning"
    except Exception as e:
        logger.error("Cache health check failed", error=str(e))
        return False, str(e)


async def check_bigquery() -> tuple[bool, str]:
    """Check BigQuery connection."""
    try:
        from google.cloud import bigquery
        from sentilyze_core import get_settings as get_core_settings
        
        core_settings = get_core_settings()
        client = bigquery.Client(project=core_settings.google_cloud_project)
        
        # Try a simple query
        query = "SELECT 1 as test"
        job = client.query(query)
        row = list(job.result())[0]
        return True, "connected" if row.test == 1 else "warning"
    except Exception as e:
        logger.error("BigQuery health check failed", error=str(e))
        return False, str(e)


async def check_pubsub() -> tuple[bool, str]:
    """Check Pub/Sub connection."""
    try:
        from google.cloud import pubsub_v1
        from sentilyze_core import get_settings as get_core_settings
        
        core_settings = get_core_settings()
        publisher = pubsub_v1.PublisherClient()
        
        # Try to list topics (lightweight operation)
        project_path = f"projects/{core_settings.google_cloud_project}"
        list(publisher.list_topics(request={"project": project_path}))
        return True, "connected"
    except Exception as e:
        logger.error("PubSub health check failed", error=str(e))
        return False, str(e)


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint.
    
    Returns simple healthy status to indicate the service is running.
    This is a lightweight check suitable for load balancers.
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/ready")
async def readiness_check() -> Response:
    """Readiness check endpoint with real service validation.
    
    Checks all downstream dependencies:
    - Cache (Firestore with memory fallback)
    - BigQuery database
    - Pub/Sub messaging
    
    Returns:
        200 OK if all services are ready
        503 Service Unavailable if critical services are down
    """
    # Run all checks concurrently
    cache_ok, cache_msg = await check_cache()
    bigquery_ok, bigquery_msg = await check_bigquery()
    pubsub_ok, pubsub_msg = await check_pubsub()
    
    checks = {
        "cache": {
            "status": "healthy" if cache_ok else "unhealthy",
            "message": cache_msg,
            "type": "firestore",
        },
        "bigquery": {
            "status": "healthy" if bigquery_ok else "unhealthy",
            "message": bigquery_msg,
        },
        "pubsub": {
            "status": "healthy" if pubsub_ok else "unhealthy",
            "message": pubsub_msg,
        },
    }
    
    # Cache is not critical (has fallback), BigQuery and PubSub are critical
    all_healthy = bigquery_ok and pubsub_ok
    
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    status_text = "ready" if all_healthy else "not_ready"
    
    logger.info(
        "Readiness check completed",
        status=status_text,
        cache=cache_ok,
        bigquery=bigquery_ok,
        pubsub=pubsub_ok,
    )
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status_text,
            "service": settings.app_name,
            "version": settings.app_version,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
        },
    )


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> dict[str, Any]:
    """Liveness check endpoint.
    
    Simple check to confirm the process is running and not deadlocked.
    Kubernetes uses this to decide whether to restart the pod.
    """
    return {
        "status": "alive",
        "service": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat(),
    }
