import logging

from fastapi import Header, HTTPException

from core.config import settings
from core.database import get_supabase

logger = logging.getLogger(__name__)


async def require_admin(authorization: str = Header(None)):
    """Dependency: validates Bearer token and checks admin_users table.
    Returns the authenticated user object.
    Raises 401 for missing/invalid token, 403 for non-admin users.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.removeprefix("Bearer ")
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        user_response = client.auth.get_user(token)
        user = user_response.user
    except Exception:
        logger.warning("Invalid auth token presented")
        raise HTTPException(status_code=401, detail="Invalid token")

    result = (
        client.table("admin_users")
        .select("email")
        .eq("email", user.email)
        .eq("is_active", True)
        .maybe_single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=403, detail="Not an admin")

    return user


def verify_cron_secret(x_cron_secret: str = Header(None, alias="x-cron-secret")):
    """Dependency: validates x-cron-secret header matches configured secret."""
    if not settings.cron_secret:
        logger.error("CRON_SECRET is not configured — cron endpoints are disabled")
        raise HTTPException(status_code=503, detail="Cron not configured")
    if not x_cron_secret or x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=401, detail="Invalid cron secret")
