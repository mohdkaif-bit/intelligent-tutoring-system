"""
api/v1/auth/__init__.py

Combines all auth sub-routers into a single router mounted by the v1 router.

In your api/v1/__init__.py:
    from app.api.v1.auth import router as auth_router
    v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])

Endpoints exposed:
    POST   /auth/signup           Register with email + password
    POST   /auth/login            Login with email + password
    POST   /auth/refresh          Refresh token pair
    GET    /auth/google           Initiate Google OAuth
    GET    /auth/google/callback  Google OAuth callback (Supabase redirects here)
    GET    /auth/verify           Email confirmation link target
    POST   /auth/verify/resend    Resend confirmation email
"""

from fastapi import APIRouter

from app.api.v1.auth import google, login, refresh, signup, verify

router = APIRouter()

router.include_router(login.router)
router.include_router(signup.router)
router.include_router(refresh.router)
router.include_router(google.router)
router.include_router(verify.router)

__all__ = ["router"]