from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config import settings

bearer_scheme = HTTPBearer()


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> str:
    """Dependency: validates admin Bearer token. Phase 2 — full auth TBD."""
    # TODO: implement proper admin token validation in Phase 2
    raise HTTPException(status_code=501, detail="Admin auth not implemented yet")
