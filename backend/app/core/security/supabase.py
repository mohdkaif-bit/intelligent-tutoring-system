"""
core/security/supabase.py

Two Supabase clients, one per trust level:

  anon_client()     — uses the anon key (for actions the logged-in user
                       would perform themselves, e.g. signInWithPassword)
  admin_client()    — uses the service-role key (bypasses RLS; for
                       privileged server-side operations only)

Clients are module-level singletons — constructed once and reused.

Required env vars:
    SUPABASE_URL
    SUPABASE_ANON_KEY
    SUPABASE_SERVICE_ROLE_KEY
"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings  # adjust to your config location


@lru_cache(maxsize=1)
def get_anon_client() -> Client:
    """
    Public / anon Supabase client.

    Use for:
      - signInWithPassword (login)
      - signUp (registration)
      - signOut

    Do NOT use to read/write data — RLS will apply based on the anon key,
    not the authenticated user. For data operations use get_admin_client()
    combined with the verified user_id from the JWT.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


@lru_cache(maxsize=1)
def get_admin_client() -> Client:
    """
    Service-role Supabase client — bypasses RLS entirely.

    Use ONLY for:
      - Reading / writing user profile records
      - Server-side user management (ban, delete, etc.)
      - Background jobs

    Never expose the service role key or this client to the frontend.
    """
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
    )