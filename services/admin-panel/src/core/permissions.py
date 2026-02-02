"""Role-based access control (RBAC) permissions."""

from typing import Callable

from fastapi import Depends, HTTPException, status

from ..models import User
from .auth import get_current_user


class PermissionChecker:
    """Dependency class for checking user permissions."""

    def __init__(self, required_permissions: list[str]):
        """
        Initialize permission checker.

        Args:
            required_permissions: List of required permissions
        """
        self.required_permissions = required_permissions

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        """
        Check if user has required permissions.

        Args:
            current_user: Current authenticated user

        Returns:
            User: Current user if permissions are satisfied

        Raises:
            HTTPException: If user doesn't have required permissions
        """
        # Superusers always have access
        if current_user.is_superuser:
            return current_user

        # Check if user has all required permissions
        user_permissions = current_user.all_permissions

        # If user has wildcard permission, allow all
        if "*" in user_permissions:
            return current_user

        # Check each required permission
        for permission in self.required_permissions:
            if not self._check_permission(permission, user_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission} required",
                )

        return current_user

    @staticmethod
    def _check_permission(required: str, user_permissions: set[str]) -> bool:
        """
        Check if a specific permission is granted.

        Supports wildcard permissions like "read:*".

        Args:
            required: Required permission
            user_permissions: User's permissions

        Returns:
            bool: True if permission is granted
        """
        # Exact match
        if required in user_permissions:
            return True

        # Wildcard match (e.g., "read:*" grants "read:services", "read:analytics")
        parts = required.split(":")
        if len(parts) == 2:
            action, resource = parts
            wildcard = f"{action}:*"
            if wildcard in user_permissions:
                return True

        return False


def require_permission(*permissions: str) -> Callable:
    """
    Dependency factory for requiring specific permissions.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_permission("admin:write"))])
        async def admin_endpoint():
            ...

    Args:
        permissions: Required permissions

    Returns:
        PermissionChecker: Permission checker dependency
    """
    return PermissionChecker(list(permissions))


# Predefined permission checkers
require_admin = PermissionChecker(["*"])
require_read_services = PermissionChecker(["read:services"])
require_write_services = PermissionChecker(["write:services"])
require_read_analytics = PermissionChecker(["read:analytics"])
require_write_analytics = PermissionChecker(["write:analytics"])
require_read_logs = PermissionChecker(["read:logs"])
require_read_config = PermissionChecker(["read:config"])
require_write_config = PermissionChecker(["write:config"])
require_read_users = PermissionChecker(["read:users"])
require_write_users = PermissionChecker(["write:users"])
