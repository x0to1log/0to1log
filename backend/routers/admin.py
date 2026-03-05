from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/drafts")
async def list_drafts():
    raise HTTPException(status_code=501, detail="Not implemented (Phase 2)")


@router.get("/drafts/{slug}")
async def get_draft(slug: str):
    raise HTTPException(status_code=501, detail="Not implemented (Phase 2)")
