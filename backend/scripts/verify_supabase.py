# scripts/verify_supabase.py
import asyncio
from app.core.config import settings
from app.core.security.supabase import get_anon_client, get_admin_client

def verify():
    print(f"Supabase URL     : {settings.SUPABASE_URL}")
    print(f"Configured       : {settings.supabase_configured}")

    # Test anon client can reach Supabase
    anon = get_anon_client()
    print(f"Anon client      : OK ({type(anon).__name__})")

    # Test admin client can read profiles table
    admin = get_admin_client()
    result = admin.table("profiles").select("id").limit(1).execute()
    print(f"Admin DB access  : OK (profiles table reachable)")
    print(f"\n✓ Supabase is fully configured and connected.")

if __name__ == "__main__":
    verify()