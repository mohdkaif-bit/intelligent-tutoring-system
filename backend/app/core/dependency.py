"""
core/dependency.py

Drop-in replacement for the old stub file.

Anything that was importing from here continues to work unchanged.
All real logic lives in core/security/.

Before (stub):
    from app.core.dependency import get_current_user_id

After (production — same import, real auth):
    from app.core.dependency import get_current_user_id  # ← unchanged
"""

# Re-export everything from the security package so existing imports don't break
from app.core.security.dependencies import (  # noqa: F401
    get_current_user,
    get_current_user_id,
    get_optional_user,
    require_admin,
)
from app.core.security.auth import AuthenticatedUser  # noqa: F401