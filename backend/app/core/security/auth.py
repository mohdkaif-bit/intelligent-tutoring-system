"""
core/security/auth.py

High-level auth helpers used by FastAPI dependencies.

Responsibilities:
  - Fetch the user's profile row from your own `profiles` table
  - Merge Supabase JWT claims with your app-level profile data
  - Raise clean HTTP errors on auth failures

Assumes your DB has a `profiles` table with at minimum:
    id          UUID  (matches auth.users.id / JWT sub)
    email       TEXT
    full_name   TEXT
    avatar_url  TEXT  (nullable)
    created_at  TIMESTAMPTZ
    updated_at  TIMESTAMPTZ
    storage_key TEXT  (per-user storage path, for multi-user storage)

Adjust the profile schema to match yours.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, status
from postgrest.exceptions import APIError

from app.core.security.jwt import TokenPayload
from app.core.security.supabase import get_admin_client

logger = logging.getLogger(__name__)


# ── Domain model ──────────────────────────────────────────────────────────────

class AuthenticatedUser:
    """
    A fully resolved, authenticated user — JWT claims + DB profile merged.

    This is what your route handlers receive via Depends().
    Access patterns:
        user.id            → Supabase UUID string
        user.email         → verified email from JWT
        user.profile       → dict of your profiles table row
        user.storage_key   → per-user storage path (multi-user storage)
        user.full_name     → convenience shortcut into profile
        user.is_admin      → derived from app_metadata role
    """

    def __init__(self, token: TokenPayload, profile: dict[str, Any]) -> None:
        self._token = token
        self._profile = profile

    # ── identity (from JWT — always trustworthy) ──────────────────────────
    @property
    def id(self) -> str:
        return self._token.user_id

    @property
    def email(self) -> str:
        return self._token.email

    @property
    def role(self) -> str:
        return self._token.role

    # ── profile (from your DB) ────────────────────────────────────────────
    @property
    def profile(self) -> dict[str, Any]:
        return self._profile

    @property
    def full_name(self) -> str:
        return self._profile.get("full_name") or self._token.user_metadata.get("full_name", "")

    @property
    def avatar_url(self) -> str | None:
        return self._profile.get("avatar_url")

    @property
    def storage_key(self) -> str:
        """
        Per-user storage path prefix.
        Falls back to user_id if storage_key column not yet set.
        """
        return self._profile.get("storage_key") or self.id

    # ── permissions ───────────────────────────────────────────────────────
    @property
    def is_admin(self) -> bool:
        return self._token.app_metadata.get("role") == "admin"

    # ── serialisation ─────────────────────────────────────────────────────
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "storage_key": self.storage_key,
            "is_admin": self.is_admin,
            "profile": self._profile,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuthenticatedUser id={self.id} email={self.email}>"


# ── Profile fetch ─────────────────────────────────────────────────────────────

async def fetch_user_profile(user_id: str) -> dict[str, Any]:
    """
    Fetch the user's profile row from the `profiles` table.

    Uses the service-role client so RLS doesn't block the lookup.
    Raises 401 if no profile exists (user deleted / not yet seeded).
    """
    try:
        result = (
            get_admin_client()
            .table("profiles")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
    except APIError as exc:
        # PostgREST returns 406 / PGRST116 when .single() finds nothing
        if "PGRST116" in str(exc) or "406" in str(exc):
            logger.warning("Profile not found for user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User profile not found.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        logger.exception("DB error fetching profile for user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not reach the database. Try again.",
        )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User profile not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return result.data


async def resolve_authenticated_user(token: TokenPayload) -> AuthenticatedUser:
    """
    Given a verified TokenPayload, fetch the DB profile and return a
    fully-resolved AuthenticatedUser.

    This is the single entry point used by FastAPI dependencies.
    """
    profile = await fetch_user_profile(token.user_id)
    return AuthenticatedUser(token=token, profile=profile)


async def create_user_profile(
    user_id: str,
    email: str,
    full_name: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Insert a new profile row after Supabase signup.

    storage_key defaults to the user's UUID — adjust if you have a
    different per-user storage strategy (e.g. slugified username).
    """
    payload: dict[str, Any] = {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "storage_key": user_id,  # per-user storage path
        **(extra or {}),
    }

    try:
        result = (
            get_admin_client()
            .table("profiles")
            .insert(payload)
            .execute()
        )
    except APIError as exc:
        logger.exception("Failed to create profile for user_id=%s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user profile.",
        )

    return result.data[0]