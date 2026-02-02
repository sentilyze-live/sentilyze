"""Authentication endpoints for API Gateway."""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..auth import (
    create_access_token,
    get_current_user,
    get_optional_user,
    get_password_hash,
    verify_password,
    validate_api_key,
)
from ..config import get_settings
from ..logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token")
async def login(request: Request) -> dict[str, Any]:
    """Login endpoint to obtain JWT token.
    
    This is a simplified implementation. In production,
    validate credentials against a user database.
    
    Request body should contain:
    - username: User identifier
    - password: User password
    
    Returns:
        Access token and token type
    """
    # For demonstration - in production, validate against database
    # This example accepts any credentials and returns a demo token
    
    # TODO: Implement proper user authentication with database
    # For now, return a demo token for testing
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    
    access_token = create_access_token(
        data={
            "sub": "demo_user",
            "email": "demo@example.com",
            "tenant_id": "default",
            "scopes": ["user"],
        },
        expires_delta=access_token_expires,
    )
    
    logger.info("Token generated", user_id="demo_user")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


@router.get("/me")
async def get_current_user_info(
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Get current authenticated user information.
    
    Args:
        user: Current user from JWT token
        
    Returns:
        User information
    """
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "tenant_id": user.get("tenant_id"),
        "scopes": user.get("scopes", []),
    }


@router.get("/verify")
async def verify_token(
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Verify that the current token is valid.
    
    Args:
        user: Current user from JWT token
        
    Returns:
        Verification status
    """
    return {
        "valid": True,
        "user_id": user.get("id"),
        "tenant_id": user.get("tenant_id"),
    }


@router.post("/refresh")
async def refresh_token(
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Refresh the current access token.
    
    Args:
        user: Current user from JWT token
        
    Returns:
        New access token
    """
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    
    access_token = create_access_token(
        data={
            "sub": user.get("id"),
            "email": user.get("email"),
            "tenant_id": user.get("tenant_id"),
            "scopes": user.get("scopes", []),
        },
        expires_delta=access_token_expires,
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


@router.post("/api-key/validate")
async def validate_api_key_endpoint(
    request: Request,
) -> dict[str, Any]:
    """Validate an API key.
    
    Args:
        request: FastAPI request with X-API-Key header
        
    Returns:
        Validation result
    """
    try:
        await validate_api_key(request)
        return {
            "valid": True,
            "key_type": "admin",
        }
    except HTTPException as e:
        raise e
