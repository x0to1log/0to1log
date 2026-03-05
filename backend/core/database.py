from supabase import create_client, Client
from core.config import settings

_client: Client | None = None


def get_supabase() -> Client | None:
    """Return Supabase client with service key. Returns None if not configured."""
    global _client
    if _client is None and settings.supabase_url and settings.supabase_service_key:
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client
