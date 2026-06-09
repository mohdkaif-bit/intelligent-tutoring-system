"""
api/v1/auth/signup.py

POST /api/v1/auth/signup

Creates a new Supabase Auth user. The DB trigger handle_new_user()
automatically inserts the matching profile row.

Flow (email confirmation ON — production):
  1. Validate request body
  2. Call Supabase signUp
  3. Supabase sends confirmation email → return 202 (pending verification)
  4. User clicks link → /auth/verify confirms them → they can now login

Flow (email confirmation OFF — dev only):
  1-2. Same as above
  3. Session returned immediately → fetch profile → return 201 with tokens
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security.auth import fetch_user_profile
from app.core.security.supabase import get_anon_client

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter.")
        return v


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    avatar_url: str | None
    storage_key: str
    created_at: str | None = None


class SignupResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile


class SignupPendingResponse(BaseModel):
    """Returned when email confirmation is required."""
    status: str = "pending_verification"
    message: str
    email: str


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post(
    "/signup",
    summary="Register a new user",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Account created, tokens returned (email confirm OFF)"},
        202: {"model": SignupPendingResponse, "description": "Confirmation email sent"},
        409: {"description": "Email already registered"},
    },
)
async def signup(body: SignupRequest):
    """
    Register a new account.

    **Email confirmation ON (production):**
    Returns 202 — user must click the confirmation link before logging in.
    The link calls GET /auth/verify which confirms the account and returns tokens.

    **Email confirmation OFF (dev):**
    Returns 201 with tokens immediately — same flow as before.
    """
    supabase = get_anon_client()

    # 1. Create Supabase Auth user
    try:
        auth_response = supabase.auth.sign_up(
            {
                "email": body.email,
                "password": body.password,
                "options": {
                    "data": {"full_name": body.full_name},
                    # Tell Supabase where to redirect after email confirmation
                    "email_redirect_to": "http://localhost:8000/api/v1/auth/verify",
                },
            }
        )
    except Exception as exc:
        _handle_auth_error(exc)

    user    = auth_response.user
    session = auth_response.session

    # 2a. Email confirmation required — session is None
    #     Supabase has sent the confirmation email already.
    if session is None:
        logger.info("Signup pending email confirmation for %s", body.email)
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=SignupPendingResponse(
                message=(
                    "Account created. Please check your email and click the "
                    "confirmation link to activate your account."
                ),
                email=body.email,
            ).model_dump(),
        )

    # 2b. Email confirmation OFF (dev) — session returned immediately
    #     DB trigger has already created the profile row.
    await asyncio.sleep(0.3)  # let the trigger commit
    profile = await fetch_user_profile(user.id)

    logger.info("Signup complete (no confirmation required) for user_id=%s", user.id)

    return SignupResponse(
        access_token  = session.access_token,
        refresh_token = session.refresh_token,
        expires_in    = session.expires_in,
        user          = UserProfile(
            id          = profile["id"],
            email       = profile["email"],
            full_name   = profile.get("full_name", body.full_name),
            avatar_url  = profile.get("avatar_url"),
            storage_key = profile["storage_key"],
            created_at  = profile.get("created_at"),
        ),
    )


# ── Error mapping ─────────────────────────────────────────────────────────────

def _handle_auth_error(exc: Exception) -> None:
    msg = str(exc).lower()
    logger.debug("Supabase auth error during signup: %s", exc)

    if "already registered" in msg or "user already exists" in msg:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    if "password" in msg:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Password rejected by auth provider: {exc}",
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Authentication service error. Please try again.",
    )