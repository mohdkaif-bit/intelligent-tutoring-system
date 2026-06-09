"""
api/v1/auth/login.py

POST /api/v1/auth/login

Authenticates with Supabase using email + password.
Returns Supabase tokens (pass-through) plus the user's profile from your DB.

Flow:
  1. Call Supabase signInWithPassword
  2. If successful, fetch profile from your DB
  3. Return tokens + merged profile data
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.core.security.auth import fetch_user_profile
from app.core.security.supabase import get_anon_client

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    avatar_url: str | None
    storage_key: str
    is_admin: bool = False


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate with email and password",
)
async def login(body: LoginRequest) -> LoginResponse:
    """
    Sign in with email and password.

    Returns Supabase auth tokens the client should store, plus the user's
    profile enriched with app-level data (full_name, storage_key, etc.).

    Raises 401 for invalid credentials, 403 if the account is banned/disabled.
    """
    supabase = get_anon_client()

    # 1. Authenticate with Supabase
    try:
        auth_response = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as exc:
        _handle_auth_error(exc)

    session = auth_response.session
    user = auth_response.user

    if session is None or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Fetch profile from your DB
    profile = await fetch_user_profile(user.id)

    # 3. Derive is_admin from Supabase app_metadata (server-controlled, safe)
    app_metadata: dict = user.app_metadata or {}
    is_admin = app_metadata.get("role") == "admin"

    return LoginResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        user=UserProfile(
            id=profile["id"],
            email=profile["email"],
            full_name=profile.get("full_name", ""),
            avatar_url=profile.get("avatar_url"),
            storage_key=profile.get("storage_key", user.id),
            is_admin=is_admin,
        ),
    )


# ── Error mapping ─────────────────────────────────────────────────────────────

def _handle_auth_error(exc: Exception) -> None:
    msg = str(exc).lower()
    logger.debug("Supabase auth error during login: %s", exc)

    if "invalid login credentials" in msg or "invalid credentials" in msg:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if "email not confirmed" in msg:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please confirm your email address before signing in.",
        )
    if "banned" in msg or "disabled" in msg:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled. Contact support.",
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Authentication service error. Please try again.",
    )