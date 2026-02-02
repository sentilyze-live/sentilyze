"""Authentication API endpoints."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import get_current_user
from ...core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_refresh_token,
    verify_password,
    verify_refresh_token,
)
from ...db.session import get_db
from ...models import Session, User
from ...schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserInfo,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    User login endpoint.

    Returns JWT access and refresh tokens.
    """
    # Get user by username
    result = await db.execute(select(User).where(User.username == login_data.username))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Check if account is locked
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked. Please try again later.",
        )

    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        # Increment failed login attempts
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(failed_login_attempts=user.failed_login_attempts + 1)
        )
        await db.commit()

        # Lock account if too many failed attempts
        if user.failed_login_attempts + 1 >= 5:
            locked_until = datetime.utcnow() + timedelta(minutes=15)
            await db.execute(
                update(User).where(User.id == user.id).values(locked_until=locked_until)
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Too many failed login attempts. Account locked for 15 minutes.",
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Create tokens
    token_data = {"sub": str(user.id), "username": user.username, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Store refresh token in database
    session = Session(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh_token),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        expires_at=datetime.utcnow() + timedelta(days=7),
        last_activity_at=datetime.utcnow(),
    )
    db.add(session)

    # Update user last login and reset failed attempts
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(last_login_at=datetime.utcnow(), failed_login_attempts=0, locked_until=None)
    )

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=1800,  # 30 minutes
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    """
    try:
        # Decode refresh token
        payload = decode_token(refresh_data.refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        # Verify refresh token exists in database
        result = await db.execute(select(Session).where(Session.user_id == user_id))
        sessions = result.scalars().all()

        valid_session = None
        for session in sessions:
            if verify_refresh_token(refresh_data.refresh_token, session.refresh_token_hash):
                if not session.is_expired:
                    valid_session = session
                    break

        if not valid_session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Create new tokens
        token_data = {"sub": str(user.id), "username": user.username, "email": user.email}
        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)

        # Update session
        valid_session.refresh_token_hash = hash_refresh_token(new_refresh_token)
        valid_session.last_activity_at = datetime.utcnow()
        await db.commit()

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=1800,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Logout user and invalidate all sessions.
    """
    # Delete all user sessions
    await db.execute(select(Session).where(Session.user_id == current_user.id))
    await db.commit()

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserInfo:
    """
    Get current user information.
    """
    return UserInfo(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        roles=current_user.role_names,
        permissions=list(current_user.all_permissions),
    )


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Change user password.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )

    # Update password
    from ...core.security import get_password_hash

    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(hashed_password=get_password_hash(password_data.new_password))
    )
    await db.commit()

    return {"message": "Password changed successfully"}
