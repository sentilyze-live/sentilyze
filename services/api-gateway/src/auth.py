"""Authentication handlers with JWT and API Key support."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

# Anonymous user for optional auth
ANONYMOUS_USER = {
    "id": None,
    "email": None,
    "tenant_id": "public",
    "scopes": [],
}

# Empty token sentinels
EMPTY_TOKEN_SENTINELS = {"", "null", "undefined", "None"}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    
    if not settings.jwt_secret:
        raise ValueError("JWT secret not configured")
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        if not settings.jwt_secret:
            raise ValueError("JWT secret not configured")
        
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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current user from JWT token (required).
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        User data from token
        
    Raises:
        HTTPException: If authentication fails
    """
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "id": user_id,
        "email": payload.get("email"),
        "tenant_id": payload.get("tenant_id", "default"),
        "scopes": payload.get("scopes", []),
    }


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
) -> dict:
    """Get current user from JWT token (optional).
    
    Returns anonymous user if no valid token provided.
    
    Args:
        credentials: Optional HTTP Authorization credentials
        
    Returns:
        User data or anonymous user
    """
    if credentials is None:
        return ANONYMOUS_USER.copy()
    
    token = (credentials.credentials or "").strip()
    if token.lower() in EMPTY_TOKEN_SENTINELS:
        return ANONYMOUS_USER.copy()
    
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            return ANONYMOUS_USER.copy()
        return {
            "id": user_id,
            "email": payload.get("email"),
            "tenant_id": payload.get("tenant_id", "default"),
            "scopes": payload.get("scopes", []),
        }
    except HTTPException:
        return ANONYMOUS_USER.copy()


async def validate_api_key(request: Request, expected_key: Optional[str] = None) -> str:
    """Validate API key from request header.
    
    Args:
        request: FastAPI request
        expected_key: Expected API key (defaults to admin_api_key from settings)
        
    Returns:
        Validated key identifier
        
    Raises:
        HTTPException: If API key is invalid
    """
    if expected_key is None:
        expected_key = settings.admin_api_key
    
    # If no API key configured in settings, skip validation
    if not expected_key:
        return "jwt_only"
    
    api_key = request.headers.get(settings.api_key_header)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(api_key, expected_key):
        client_ip = request.client.host if request.client else "unknown"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return "valid"


class RoleChecker:
    """Role-based access control dependency."""
    
    def __init__(self, required_roles: list[str]) -> None:
        self.required_roles = required_roles
    
    def __call__(self, user: dict = Depends(get_current_user)) -> dict:
        """Check if user has required roles."""
        user_roles = user.get("scopes", [])
        
        if not any(role in user_roles for role in self.required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        return user


# Common role checkers
require_admin = RoleChecker(["admin"])
require_user = RoleChecker(["user", "admin"])


async def require_admin_or_api_key(
    request: Request,
    user: dict = Depends(get_optional_user),
) -> dict:
    """Require either admin role or valid API key.
    
    Args:
        request: FastAPI request
        user: User from optional JWT auth
        
    Returns:
        User data
        
    Raises:
        HTTPException: If neither admin nor valid API key
    """
    # Check if user has admin role
    if "admin" in user.get("scopes", []):
        return user
    
    # Check API key
    await validate_api_key(request)
    
    return user
