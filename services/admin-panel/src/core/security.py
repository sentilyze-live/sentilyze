"""Security utilities for authentication and authorization."""

import secrets
from datetime import datetime, timedelta
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Data to encode in token
        expires_delta: Optional expiration time delta

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_refresh_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT refresh token.

    Args:
        data: Data to encode in token
        expires_delta: Optional expiration time delta

    Returns:
        str: Encoded JWT refresh token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify JWT token.

    Args:
        token: JWT token to decode

    Returns:
        dict: Decoded token payload

    Raises:
        JWTError: If token is invalid or expired
    """
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return payload


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.

    Returns:
        tuple: (api_key, key_hash)
            - api_key: The full API key to return to user
            - key_hash: Hashed key to store in database
    """
    # Generate random key (32 bytes = 64 hex chars)
    key = secrets.token_urlsafe(32)

    # Create prefix for identification (first 8 chars)
    prefix = key[:8]

    # Hash the full key for storage
    key_hash = get_password_hash(key)

    return key, key_hash


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash.

    Args:
        plain_key: Plain API key
        hashed_key: Hashed API key from database

    Returns:
        bool: True if key matches
    """
    return verify_password(plain_key, hashed_key)


def hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token for storage.

    Args:
        token: Refresh token to hash

    Returns:
        str: Hashed token
    """
    return get_password_hash(token)


def verify_refresh_token(plain_token: str, hashed_token: str) -> bool:
    """
    Verify a refresh token against its hash.

    Args:
        plain_token: Plain refresh token
        hashed_token: Hashed token from database

    Returns:
        bool: True if token matches
    """
    return verify_password(plain_token, hashed_token)
