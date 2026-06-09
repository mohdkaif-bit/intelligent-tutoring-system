"""
core/security/dependencies.py

FastAPI dependency functions for authentication.

These live in core/ and are the single source of truth for auth.
Route-level files in api/v1/auth/ import from here — they don't
re-implement verification logic.

Usage in a route:
    from app.core.security.dependencies import get_current_user, get_current_user_id
    from app.core.security.auth import AuthenticatedUser

    @router.get("/me")
    async def me(user: AuthenticatedUser = Depends(get_current_user)):
        return user.to_dict()

Optional user (public endpoints that behave differently when authed):
    @router.get("/feed")
    async def feed(user: AuthenticatedUser | None = Depends(get_optional_user)):
        ...

Admin-only:
    @router.delete("/users/{uid}")
    async def delete_user(user: AuthenticatedUser = Depends(require_admin)):
        ...
"""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security.auth import AuthenticatedUser, resolve_authenticated_user
from app.core.security.jwt import verify_supabase_token

logger = logging.getLogger(__name__)

# Extracts the Bearer token from the Authorization header.
# auto_error=False lets us handle the 401 ourselves with a clean message.
_bearer = HTTPBearer(auto_error=False)


# ── Primary dependency ─────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    """
    Resolve the authenticated user from the Bearer token.

    Steps:
      1. Extract Bearer token from Authorization header
      2. Verify Supabase JWT signature + expiry + audience
      3. Fetch user profile from your DB
      4. Return AuthenticatedUser

    Raises 401 on any failure.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_payload = verify_supabase_token(credentials.credentials)
    return await resolve_authenticated_user(token_payload)


# ── Convenience shortcuts ──────────────────────────────────────────────────────

async def get_current_user_id(
    user: AuthenticatedUser = Depends(get_current_user),
) -> str:
    """
    Dependency that returns just the authenticated user's UUID string.

    Use when a route only needs the ID, not the full profile:
        async def my_route(user_id: str = Depends(get_current_user_id)):
    """
    return user.id


# ── Optional auth (public endpoints) ──────────────────────────────────────────

async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser | None:
    """
    Returns the authenticated user if a valid token is present,
    otherwise returns None (does NOT raise).

    Use for endpoints that work for both guests and logged-in users.
    """
    if credentials is None:
        return None

    try:
        token_payload = verify_supabase_token(credentials.credentials)
        return await resolve_authenticated_user(token_payload)
    except HTTPException:
        return None


# ── Admin guard ────────────────────────────────────────────────────────────────

async def require_admin(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """
    Dependency that requires the user to have admin privileges.

    Admin is determined by app_metadata.role == "admin" in Supabase,
    which can only be set server-side (safe from client manipulation).

    Raises 403 if the user is not an admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return user