"""GCP helpers (Secret Manager, topic constants) for Sentilyze Core.

This module is intentionally small and dependency-light:
- Secrets are fetched at runtime from GCP Secret Manager
- Secret values are NEVER logged
"""

from __future__ import annotations

import asyncio
from typing import Optional

from google.api_core.exceptions import NotFound
from google.cloud import secretmanager

from ..exceptions import ConfigurationError
from ..logging import get_logger
from . import get_settings

logger = get_logger(__name__)

# Topic name constants (bronze == raw events)
TOPIC_RAW_EVENTS = "raw-events"
TOPIC_PROCESSED_EVENTS = "processed-events"
TOPIC_ALERTS = "alerts"

# Secret IDs (as created in GCP Secret Manager)
# Crypto API keys
SECRET_COINGECKO_API_KEY = "COINGECKO_API_KEY"
SECRET_FINNHUB_API_KEY = "FINNHUB_API_KEY"
SECRET_EODHD_API_KEY = "EODHD_API_KEY"
SECRET_BINANCE_API_KEY = "BINANCE_API_KEY"

# Gold/Metals API keys
SECRET_GOLDAPI_API_KEY = "GOLDAPI_API_KEY"
SECRET_METALS_API_KEY = "METALS_API_KEY"
SECRET_TWELVE_DATA_API_KEY = "TWELVE_DATA_API_KEY"

# Common
SECRET_ALPHAVANTAGE_API_KEY = "ALPHAVANTAGE_API_KEY"
SECRET_TELEGRAM_BOT_TOKEN = "TELEGRAM_BOT_TOKEN"

_client_lock = asyncio.Lock()
_client: secretmanager.SecretManagerServiceAsyncClient | None = None

_secret_cache_lock = asyncio.Lock()
_secret_cache: dict[str, str] = {}


async def _get_client() -> secretmanager.SecretManagerServiceAsyncClient:
    global _client
    async with _client_lock:
        if _client is None:
            _client = secretmanager.SecretManagerServiceAsyncClient()
        return _client


def _resolve_project_id(explicit_project_id: Optional[str] = None) -> str:
    if explicit_project_id:
        return explicit_project_id
    settings = get_settings()
    return settings.google_cloud_project or settings.pubsub_project_id


async def access_secret(
    secret_id: str,
    *,
    project_id: Optional[str] = None,
    version: str = "latest",
) -> str:
    """Access a secret value from GCP Secret Manager (async).

    Args:
        secret_id: Secret resource id (not the full path)
        project_id: GCP project id; defaults to Settings.google_cloud_project
        version: Secret version (default: "latest")
    """
    project = _resolve_project_id(project_id)
    name = f"projects/{project}/secrets/{secret_id}/versions/{version}"
    client = await _get_client()
    response = await client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8")


async def get_secret_cached(
    secret_id: str,
    *,
    project_id: Optional[str] = None,
    version: str = "latest",
) -> str:
    cache_key = f"{project_id or ''}:{secret_id}:{version}"
    async with _secret_cache_lock:
        if cache_key in _secret_cache:
            return _secret_cache[cache_key]

    value = await access_secret(secret_id, project_id=project_id, version=version)

    async with _secret_cache_lock:
        _secret_cache[cache_key] = value
    return value


async def try_get_secret(
    secret_id: str,
    *,
    project_id: Optional[str] = None,
    version: str = "latest",
) -> Optional[str]:
    """Best-effort secret fetch. Returns None if secret/version not found."""
    try:
        return await get_secret_cached(secret_id, project_id=project_id, version=version)
    except NotFound:
        return None


async def load_ingestion_api_keys_from_secret_manager(
    *,
    project_id: Optional[str] = None,
    market_type: str = "all",
) -> dict[str, Optional[str]]:
    """Load ingestion-related API keys from Secret Manager in parallel.

    Args:
        project_id: GCP project id
        market_type: 'crypto', 'gold', or 'all' to filter which keys to load

    Returns:
        Dictionary of API keys
    """
    settings = get_settings()
    secrets_to_fetch = []

    if market_type in ("crypto", "all") and settings.enable_crypto_market:
        secrets_to_fetch.extend([
            ("binance", SECRET_BINANCE_API_KEY),
            ("coingecko", SECRET_COINGECKO_API_KEY),
            ("finnhub", SECRET_FINNHUB_API_KEY),
        ])

    if market_type in ("gold", "all") and settings.enable_gold_market:
        secrets_to_fetch.extend([
            ("goldapi", SECRET_GOLDAPI_API_KEY),
            ("metals_api", SECRET_METALS_API_KEY),
            ("twelve_data", SECRET_TWELVE_DATA_API_KEY),
        ])

    # Always include common secrets
    secrets_to_fetch.extend([
        ("alpha_vantage", SECRET_ALPHAVANTAGE_API_KEY),
        ("eodhd", SECRET_EODHD_API_KEY),
        ("telegram", SECRET_TELEGRAM_BOT_TOKEN),
    ])

    async def _fetch(name: str, secret_name: str) -> tuple[str, Optional[str]]:
        v = await try_get_secret(secret_name, project_id=project_id)
        if v is None:
            logger.warning("Secret not found", secret_id=secret_name, service=name)
        else:
            logger.info("Secret loaded", secret_id=secret_name, service=name)
        return (name, v)

    results = await asyncio.gather(
        *[_fetch(name, secret) for name, secret in secrets_to_fetch]
    )

    return {name: value for name, value in results}


def require_secret(value: Optional[str], *, name: str) -> str:
    if not value:
        raise ConfigurationError(
            f"Missing required secret: {name}",
            details={"secret": name},
        )
    return value
