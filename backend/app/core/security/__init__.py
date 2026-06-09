"""
core/security/__init__.py

Public API of the security package.
Import from here rather than from submodules directly.

    from app.core.security import get_current_user, AuthenticatedUser
"""

from app.core.security.auth import AuthenticatedUser, create_user_profile, fetch_user_profile
from app.core.security.dependencies import (
    get_current_user,
    get_current_user_id,
    get_optional_user,
    require_admin,
)
from app.core.security.jwt import TokenPayload, verify_supabase_token
from app.core.security.supabase import get_admin_client, get_anon_client

__all__ = [
    # user model
    "AuthenticatedUser",
    # dependencies
    "get_current_user",
    "get_current_user_id",
    "get_optional_user",
    "require_admin",
    # jwt
    "TokenPayload",
    "verify_supabase_token",
    # supabase clients
    "get_admin_client",
    "get_anon_client",
    # profile helpers
    "create_user_profile",
    "fetch_user_profile",
]