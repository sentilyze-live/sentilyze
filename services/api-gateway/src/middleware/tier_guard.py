"""Tier-based access control middleware.

Enforces subscription tier limits on API endpoints:
- Asset access by tier
- Watchlist limits
- Daily prediction limits
- History depth limits

All checks are gated behind the 'user_subscriptions' feature flag.
When the flag is disabled, all requests pass through unchanged.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status

from sentilyze_core.asset_registry import can_access_asset
from sentilyze_core.feature_flags import is_feature_enabled
from sentilyze_core.subscription import (
    SubscriptionTier,
    get_tier_limits,
    get_upgrade_tier,
    get_watchlist_limit,
    TIER_PRICING_USD,
)

from ..auth import get_current_user, get_optional_user
from ..logging import get_logger

logger = get_logger(__name__)


def _extract_tier(user: dict) -> SubscriptionTier:
    """Extract subscription tier from user dict, default to FREE."""
    tier_str = user.get("tier", "free")
    try:
        return SubscriptionTier(tier_str)
    except ValueError:
        return SubscriptionTier.FREE


async def require_asset_access(
    symbol: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Dependency that checks if user's tier can access a given asset.

    If user_subscriptions flag is disabled, allows all access.
    Raises 403 with upgrade suggestion if tier is insufficient.
    """
    if not await is_feature_enabled("user_subscriptions"):
        return user

    tier = _extract_tier(user)

    if not can_access_asset(tier, symbol):
        upgrade_tier = get_upgrade_tier(tier)
        upgrade_price = TIER_PRICING_USD.get(upgrade_tier, 0) if upgrade_tier else None
        detail = f"Bu varliga erisim icin {upgrade_tier.value if upgrade_tier else 'daha yuksek'} plana yukseltmeniz gerekiyor."
        if upgrade_price:
            detail += f" (${upgrade_price}/ay)"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "tier_insufficient",
                "message": detail,
                "current_tier": tier.value,
                "required_tier": upgrade_tier.value if upgrade_tier else "enterprise",
                "upgrade_price_usd": upgrade_price,
            },
        )

    return user


async def require_watchlist_capacity(
    user: dict = Depends(get_current_user),
    current_count: int = 0,
) -> dict:
    """Dependency that checks if user has room in their watchlist.

    Args:
        user: Authenticated user dict
        current_count: Current number of items in watchlist
    """
    if not await is_feature_enabled("user_subscriptions"):
        return user

    tier = _extract_tier(user)
    limit = get_watchlist_limit(tier)

    if limit != -1 and current_count >= limit:
        upgrade_tier = get_upgrade_tier(tier)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "watchlist_limit_reached",
                "message": f"Watchlist limitinize ulastiniz ({limit}/{limit}).",
                "current_tier": tier.value,
                "watchlist_limit": limit,
                "current_count": current_count,
                "upgrade_tier": upgrade_tier.value if upgrade_tier else None,
            },
        )

    return user


async def check_prediction_limit(
    user: dict,
    daily_usage: int,
) -> bool:
    """Check if user has remaining daily prediction quota.

    Returns True if within limit, False if exceeded.
    Does not raise - caller decides how to handle.
    """
    if not await is_feature_enabled("user_subscriptions"):
        return True

    tier = _extract_tier(user)
    limits = get_tier_limits(tier)

    if limits.predictions_daily == -1:
        return True

    return daily_usage < limits.predictions_daily


async def get_history_limit_days(user: dict) -> int:
    """Get the maximum history depth in days for the user's tier.

    Returns -1 for unlimited.
    """
    if not await is_feature_enabled("user_subscriptions"):
        return -1

    tier = _extract_tier(user)
    return get_tier_limits(tier).history_days


async def check_api_access(user: dict) -> bool:
    """Check if user's tier has API access enabled."""
    if not await is_feature_enabled("user_subscriptions"):
        return True

    tier = _extract_tier(user)
    return get_tier_limits(tier).api_access


def get_user_tier(user: dict) -> SubscriptionTier:
    """Extract tier from user dict. Convenience function for routes."""
    return _extract_tier(user)
