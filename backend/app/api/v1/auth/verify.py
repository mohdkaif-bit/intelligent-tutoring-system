"""
api/v1/auth/verify.py

Email verification endpoints.

Endpoints:
  GET  /api/v1/auth/verify         → confirm email from link (Supabase calls this)
  POST /api/v1/auth/verify/resend  → resend verification email

Flow after signup (email confirmation ON):
  1. User signs up → Supabase sends confirmation email
  2. User clicks link → Supabase redirects to /auth/verify?token_hash=...&type=email
  3. Backend calls verifyOtp → confirms the user → returns tokens
  4. Client stores tokens and enters the app
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr

from app.core.security.auth import fetch_user_profile
from app.core.security.supabase import get_anon_client

logger = logging.getLogger(__name__)
router = APIRouter()

_FRONTEND_SUCCESS_URL = "http://localhost:3000/auth/verified"
_FRONTEND_ERROR_URL   = "http://localhost:3000/auth/error"


# ── Schemas ───────────────────────────────────────────────────────────────────

class ResendRequest(BaseModel):
    email: EmailStr


class VerifyResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    message: str = "Email verified successfully."


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "/verify",
    summary="Confirm email address (Supabase redirect target)",
)
async def verify_email(
    token_hash: str | None = Query(default=None),
    type: str | None       = Query(default=None),   # "email", "signup", etc.
    error: str | None      = Query(default=None),
    error_description: str | None = Query(default=None),
) -> JSONResponse:
    """
    Supabase redirects the user here when they click the confirmation link.

    Query params Supabase sends:
      token_hash — the OTP token to verify
      type       — "email" or "signup"
      error      — present on failure

    On success, the account is confirmed and the user gets tokens.
    They can now call /auth/login normally.

    In production, redirect to your frontend success page instead of
    returning JSON — swap the JSONResponse for a RedirectResponse.
    """
    if error:
        logger.warning("Email verification error: %s — %s", error, error_description)
        return RedirectResponse(
            url=f"{_FRONTEND_ERROR_URL}?error={error}",
            status_code=status.HTTP_302_FOUND,
        )

    if not token_hash or not type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing token_hash or type parameter.",
        )

    supabase = get_anon_client()

    try:
        response = supabase.auth.verify_otp(
            {"token_hash": token_hash, "type": type}
        )
    except Exception as exc:
        msg = str(exc).lower()
        logger.warning("Email verification failed: %s", exc)

        if "expired" in msg:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Verification link has expired. Please request a new one.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already-used verification link.",
        )

    session = response.session
    user    = response.user

    if not session or not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification failed — token may already have been used.",
        )

    logger.info("Email verified for user_id=%s", user.id)

    # Option A (current): return JSON with tokens
    # Option B: redirect to frontend
    #   return RedirectResponse(
    #       url=f"{_FRONTEND_SUCCESS_URL}"
    #           f"?access_token={session.access_token}"
    #           f"&refresh_token={session.refresh_token}",
    #       status_code=302,
    #   )
    return JSONResponse(
        content=VerifyResponse(
            access_token  = session.access_token,
            refresh_token = session.refresh_token,
            expires_in    = session.expires_in,
        ).model_dump()
    )


@router.post(
    "/verify/resend",
    summary="Resend email verification link",
    status_code=status.HTTP_200_OK,
)
async def resend_verification(body: ResendRequest) -> dict:
    """
    Resend the confirmation email to the given address.

    Safe to call even if the email doesn't exist in the system
    (Supabase returns success either way to prevent email enumeration).

    Returns 200 regardless — never reveal whether the email exists.
    """
    supabase = get_anon_client()

    try:
        supabase.auth.resend(
            {"type": "signup", "email": body.email}
        )
        logger.info("Verification email resent to %s", body.email)
    except Exception as exc:
        # Log but don't surface — prevents email enumeration
        logger.warning("Resend verification error (suppressed): %s", exc)

    return {
        "success": True,
        "message": "If an account exists for this email, a verification link has been sent.",
    }