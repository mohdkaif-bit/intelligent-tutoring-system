"""
core/security/jwt.py

Verifies Supabase-issued JWTs on the backend.

Supabase newer projects use ES256 (asymmetric) — tokens are signed with
Supabase's private key and verified with their public key fetched from
the JWKS endpoint. No shared secret needed.

JWKS endpoint: https://<project>.supabase.co/auth/v1/.well-known/jwks.json

The JWKS response is cached in memory for 1 hour — only the first request
per process lifetime hits the network. Subsequent verifications are pure
local crypto, same performance as HS256.

Required env vars:
    SUPABASE_URL  — used to construct the JWKS endpoint URL
                    (SUPABASE_JWT_SECRET no longer needed for verification)
"""

from __future__ import annotations

import logging
import time
from typing import Any

import jwt
import requests
from jwt import PyJWKClient
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# Claims Supabase puts in every token
_REQUIRED_CLAIMS = {"sub", "email", "role", "aud"}

# ── JWKS client (module-level singleton) ──────────────────────────────────────
# PyJWKClient fetches the public keys once and caches them.
# lifespan=3600 means keys are refreshed from Supabase every hour.
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    """Return the module-level JWKS client, creating it on first call."""
    global _jwks_client
    if _jwks_client is None:
        jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        logger.info("Initialising JWKS client → %s", jwks_url)
        _jwks_client = PyJWKClient(
            jwks_url,
            cache_keys=True,
            lifespan=3600,          # refresh keys every hour
            cache_jwk_set=True,
        )
    return _jwks_client


# ── Token payload ─────────────────────────────────────────────────────────────

class TokenPayload:
    """Typed wrapper around the raw JWT claims dict."""

    def __init__(self, claims: dict[str, Any]) -> None:
        self._claims = claims

    # ── identity ──────────────────────────────────────────────────────────────
    @property
    def user_id(self) -> str:
        """Supabase user UUID (the `sub` claim)."""
        return self._claims["sub"]

    @property
    def email(self) -> str:
        return self._claims.get("email", "")

    @property
    def role(self) -> str:
        """Supabase role — 'authenticated' for logged-in users."""
        return self._claims.get("role", "")

    # ── app-level metadata ────────────────────────────────────────────────────
    @property
    def user_metadata(self) -> dict[str, Any]:
        return self._claims.get("user_metadata", {})

    @property
    def app_metadata(self) -> dict[str, Any]:
        return self._claims.get("app_metadata", {})

    @property
    def raw(self) -> dict[str, Any]:
        return self._claims


# ── Verification ──────────────────────────────────────────────────────────────

def verify_supabase_token(token: str) -> TokenPayload:
    """
    Decode and validate a Supabase JWT (ES256).

    Steps:
      1. Read the `kid` from the token header
      2. Fetch the matching public key from Supabase's JWKS endpoint (cached)
      3. Verify signature, expiry, and audience locally — no network call
      4. Check role == "authenticated"

    Raises HTTPException 401 on any failure.
    """
    _unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Get the public key that matches this token's `kid`
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)

        claims: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],   # accept both; Supabase uses ES256
            audience="authenticated",
            options={"require": list(_REQUIRED_CLAIMS)},
        )

    except jwt.ExpiredSignatureError:
        logger.debug("JWT expired")
        raise _unauthorized

    except jwt.InvalidAudienceError:
        logger.debug("JWT audience mismatch")
        raise _unauthorized

    except jwt.InvalidTokenError as exc:
        logger.debug("JWT invalid: %s", exc)
        raise _unauthorized

    except requests.RequestException as exc:
        # JWKS fetch failed (network issue) — fail closed
        logger.error("Failed to fetch Supabase JWKS: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable.",
        )

    except Exception as exc:
        logger.error("Unexpected error during JWT verification: %s", exc)
        raise _unauthorized

    if claims.get("role") != "authenticated":
        # Block anon / service-role tokens from reaching user endpoints
        raise _unauthorized

    return TokenPayload(claims)