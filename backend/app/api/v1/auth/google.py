"""
api/v1/auth/google.py

Google OAuth via Supabase — backend redirect flow.

Endpoints:
  GET /api/v1/auth/google           → redirects user to Google consent screen
  GET /api/v1/auth/google/callback  → Supabase calls this after Google auth

Flow:
  1. Client hits /auth/google
  2. Backend asks Supabase for the Google OAuth URL
  3. Backend redirects user to Google
  4. User signs in on Google
  5. Supabase handles the code exchange, creates/finds the user
  6. Supabase redirects to /auth/google/callback with tokens in the URL fragment
  7. Backend extracts tokens, fetches/creates profile, returns clean JSON
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel

from app.core.security.auth import create_user_profile, fetch_user_profile
from app.core.security.supabase import get_anon_client, get_admin_client

logger = logging.getLogger(__name__)
router = APIRouter()

# Where to send the user after successful OAuth on the frontend
_FRONTEND_SUCCESS_URL = "http://localhost:3000/auth/callback"
_FRONTEND_ERROR_URL   = "http://localhost:3000/auth/error"


# ── Response schema ───────────────────────────────────────────────────────────

class OAuthUserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    avatar_url: str | None
    storage_key: str
    is_admin: bool = False
    provider: str = "google"


class OAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: OAuthUserProfile


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "/google",
    summary="Initiate Google OAuth login",
    response_class=RedirectResponse,
    status_code=status.HTTP_302_FOUND,
)
async def google_login() -> RedirectResponse:
    """
    Redirects the user to Google's consent screen via Supabase OAuth.

    The client simply navigates to this URL — no body needed.
    After Google auth, Supabase redirects to /auth/google/callback.
    """
    supabase = get_anon_client()

    try:
        response = supabase.auth.sign_in_with_oauth(
            {
                "provider": "google",
                "options": {
                    # Supabase will redirect to this URL after Google auth.
                    # Must match exactly what you added in Supabase → URL Configuration → Redirect URLs.
                    "redirect_to": "http://localhost:8000/api/v1/auth/google/callback",
                    # Request profile + email scopes
                    "scopes": "openid email profile",
                    "query_params": {
                        "access_type": "offline",   # get refresh_token from Google
                        "prompt": "select_account",  # always show account picker
                    },
                },
            }
        )
    except Exception as exc:
        logger.error("Failed to generate Google OAuth URL: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach authentication service.",
        )

    if not response.url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Authentication service did not return a redirect URL.",
        )

    logger.info("Redirecting user to Google OAuth: %s", response.url[:60])
    return RedirectResponse(url=response.url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/google/callback",
    summary="Google OAuth callback — called by Supabase",
)
async def google_callback(
    code: str | None  = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> JSONResponse:
    """
    Supabase redirects here after the user authenticates with Google.

    Query params Supabase sends:
      code  — authorization code to exchange for tokens
      error — present only on failure

    On success: returns tokens + enriched profile as JSON.
    In production you'd redirect to the frontend with tokens in the URL
    or set HttpOnly cookies — adjust _FRONTEND_SUCCESS_URL accordingly.
    """
    # ── Handle OAuth errors from Google / Supabase ────────────────────────────
    if error:
        logger.warning("Google OAuth error: %s — %s", error, error_description)
        return RedirectResponse(
            url=f"{_FRONTEND_ERROR_URL}?error={error}",
            status_code=status.HTTP_302_FOUND,
        )

    if not code:
        logger.warning("Google callback called with no code and no error")
        return RedirectResponse(
            url=f"{_FRONTEND_ERROR_URL}?error=missing_code",
            status_code=status.HTTP_302_FOUND,
        )

    # ── Exchange code for session ─────────────────────────────────────────────
    supabase = get_anon_client()

    try:
        session_response = supabase.auth.exchange_code_for_session({"auth_code": code})
    except Exception as exc:
        logger.error("Code exchange failed: %s", exc)
        return RedirectResponse(
            url=f"{_FRONTEND_ERROR_URL}?error=code_exchange_failed",
            status_code=status.HTTP_302_FOUND,
        )

    session = session_response.session
    user    = session_response.user

    if not session or not user:
        logger.error("Code exchange succeeded but session/user is None")
        return RedirectResponse(
            url=f"{_FRONTEND_ERROR_URL}?error=session_missing",
            status_code=status.HTTP_302_FOUND,
        )

    logger.info("Google OAuth success for user_id=%s email=%s", user.id, user.email)

    # ── Fetch or create profile ───────────────────────────────────────────────
    # Supabase may or may not have fired the DB trigger for OAuth users
    # (it depends on whether this is a first sign-in). We upsert to be safe.
    profile = await _get_or_create_profile(user)

    # ── Build response ────────────────────────────────────────────────────────
    app_metadata: dict = user.app_metadata or {}
    is_admin = app_metadata.get("role") == "admin"

    full_name = (
        profile.get("full_name")
        or (user.user_metadata or {}).get("full_name")
        or (user.user_metadata or {}).get("name")
        or ""
    )
    avatar_url = (
        profile.get("avatar_url")
        or (user.user_metadata or {}).get("avatar_url")
        or (user.user_metadata or {}).get("picture")
    )

    payload = OAuthResponse(
        access_token  = session.access_token,
        refresh_token = session.refresh_token,
        expires_in    = session.expires_in,
        user          = OAuthUserProfile(
            id          = profile["id"],
            email       = profile["email"],
            full_name   = full_name,
            avatar_url  = avatar_url,
            storage_key = profile.get("storage_key", user.id),
            is_admin    = is_admin,
        ),
    )

    # Redirect to frontend callback page with tokens in query params.
    # The frontend reads them, stores them via supabase.auth.setSession(),
    # then redirects the user into the app.
    return RedirectResponse(
        url=(
            f"{_FRONTEND_SUCCESS_URL}"
            f"?access_token={session.access_token}"
            f"&refresh_token={session.refresh_token}"
            f"&expires_in={session.expires_in}"
        ),
        status_code=status.HTTP_302_FOUND,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_create_profile(user) -> dict:
    """
    Fetch the profile row, creating it if it doesn't exist yet.

    For Google OAuth first-time sign-ins, the DB trigger may have already
    created the row. For subsequent sign-ins it definitely exists.
    We try fetch first, then insert on miss.
    """
    try:
        return await fetch_user_profile(user.id)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_401_UNAUTHORIZED:
            raise

    # Profile missing — create it (first Google sign-in, trigger may have missed it)
    logger.info("Creating profile for new Google user %s", user.id)
    user_metadata: dict = user.user_metadata or {}

    full_name = (
        user_metadata.get("full_name")
        or user_metadata.get("name")
        or user.email.split("@")[0]
    )
    avatar_url = (
        user_metadata.get("avatar_url")
        or user_metadata.get("picture")
    )

    return await create_user_profile(
        user_id   = user.id,
        email     = user.email,
        full_name = full_name,
        extra     = {"avatar_url": avatar_url} if avatar_url else None,
    )