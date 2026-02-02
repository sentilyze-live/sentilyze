"""Authentication middleware for API Gateway."""

import re
from typing import Callable, Optional

from fastapi import HTTPException, Request, status

from ..config import get_settings
from ..logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class AuthMiddleware:
    """Authentication middleware for request validation."""
    
    def __init__(self) -> None:
        self.public_paths: set[str] = {
            "/",
            "/health",
            "/ready",
            "/live",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
        self.public_prefixes: tuple[str, ...] = (
            "/static/",
            "/assets/",
        )
    
    def is_public_path(self, path: str) -> bool:
        """Check if path is public (no auth required).
        
        Args:
            path: Request path
            
        Returns:
            True if public path
        """
        if path in self.public_paths:
            return True
        
        return any(path.startswith(prefix) for prefix in self.public_prefixes)
    
    async def extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request.
        
        Args:
            request: FastAPI request
            
        Returns:
            Token string or None
        """
        auth_header = request.headers.get("authorization", "")
        
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        
        return None
    
    async def validate_token(self, token: str) -> dict:
        """Validate JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token invalid
        """
        from jose import JWTError, jwt
        
        try:
            if not settings.jwt_secret:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="JWT secret not configured",
                )
            
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )


# Global middleware instance
auth_middleware = AuthMiddleware()


async def auth_middleware_handler(
    request: Request,
    call_next: Callable,
) -> None:
    """Authentication middleware handler.
    
    This middleware:
    1. Allows public paths without authentication
    2. Validates JWT token for protected paths
    3. Attaches user info to request state
    
    Args:
        request: FastAPI request
        call_next: Next handler
        
    Returns:
        Response
    """
    path = request.url.path
    
    # Allow public paths
    if auth_middleware.is_public_path(path):
        return await call_next(request)
    
    # Extract and validate token for protected paths
    token = await auth_middleware.extract_token(request)
    
    if token:
        try:
            payload = await auth_middleware.validate_token(token)
            # Attach user info to request state
            request.state.user = {
                "id": payload.get("sub"),
                "email": payload.get("email"),
                "tenant_id": payload.get("tenant_id", "default"),
                "scopes": payload.get("scopes", []),
            }
        except HTTPException:
            # Token invalid but let endpoint decide if auth is required
            request.state.user = None
    else:
        request.state.user = None
    
    return await call_next(request)
