"""
api/v1/auth/refresh.py

POST /api/v1/auth/refresh

Exchanges a Supabase refresh_token for a new access_token + refresh_token pair.

Supabase refresh tokens are single-use — after calling this, the old
refresh_token is invalidated and the new one must be stored.

Flow:
  1. Call Supabase setSession (or refreshSession) with the refresh token
  2. Return the new token pair + updated profile (in case profile changed)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.core.security.supabase import get_anon_client

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Refresh access token",
)
async def refresh_token(body: RefreshRequest) -> RefreshResponse:
    """
    Exchange a refresh token for a new token pair.

    The old refresh token is immediately invalidated by Supabase.
    The client must replace both tokens with the new values.

    Raises 401 if the refresh token is expired, invalid, or already used.
    """
    supabase = get_anon_client()

    try:
        # set_session validates the refresh_token and issues new tokens
        auth_response = supabase.auth.set_session(
            access_token="",  # placeholder; Supabase will replace it
            refresh_token=body.refresh_token,
        )
    except Exception as exc:
        _handle_refresh_error(exc)

    session = auth_response.session
    user = auth_response.user

    if session is None or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("Token refreshed for user_id=%s", user.id)

    return RefreshResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        user_id=user.id,
    )


# ── Error mapping ─────────────────────────────────────────────────────────────

def _handle_refresh_error(exc: Exception) -> None:
    msg = str(exc).lower()
    logger.debug("Supabase auth error during token refresh: %s", exc)

    if any(k in msg for k in ("invalid", "expired", "not found", "already used")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Authentication service error. Please try again.",
    )