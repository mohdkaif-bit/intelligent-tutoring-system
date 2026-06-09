"""
api/v1/auth/dependencies.py

Route-level auth dependency re-exports.

These are thin pass-throughs to core/security/dependencies.py.
Having them here keeps the api/v1/auth package self-contained and
lets you add route-specific middleware here later if needed.

Usage inside api/v1/auth routes:
    from app.api.v1.auth.dependencies import CurrentUser, CurrentUserId

    @router.get("/me")
    async def me(user: CurrentUser):
        return user.to_dict()
"""

from typing import Annotated

from fastapi import Depends

from app.core.security.auth import AuthenticatedUser
from app.core.security.dependencies import (
    get_current_user,
    get_current_user_id,
    get_optional_user,
    require_admin,
)

# Typed aliases — use these in route signatures for cleaner code
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
CurrentUserId = Annotated[str, Depends(get_current_user_id)]
OptionalUser = Annotated[AuthenticatedUser | None, Depends(get_optional_user)]
AdminUser = Annotated[AuthenticatedUser, Depends(require_admin)]

__all__ = [
    "CurrentUser",
    "CurrentUserId",
    "OptionalUser",
    "AdminUser",
    # raw depends in case needed
    "get_current_user",
    "get_current_user_id",
    "get_optional_user",
    "require_admin",
]