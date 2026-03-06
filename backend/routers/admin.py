import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from core.database import get_supabase
from core.security import require_admin
from models.posts import (
    PostDraftListItem,
    PostDraftDetail,
    PostPublishResponse,
    PostUpdateRequest,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

ERROR_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Not an admin"},
}


@router.get(
    "/drafts",
    response_model=list[PostDraftListItem],
    responses=ERROR_RESPONSES,
)
async def list_drafts(_user=Depends(require_admin)):
    """List all posts with status='draft'."""
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    result = (
        client.table("posts")
        .select(
            "id, title, slug, category, post_type, status, "
            "news_temperature, pipeline_batch_id, created_at, updated_at"
        )
        .eq("status", "draft")
        .order("created_at", desc=True)
        .execute()
    )
    return [PostDraftListItem.model_validate(row) for row in result.data]


@router.get(
    "/drafts/{slug}",
    response_model=PostDraftDetail,
    responses={
        **ERROR_RESPONSES,
        404: {"model": ErrorResponse, "description": "Draft not found"},
    },
)
async def get_draft(slug: str, _user=Depends(require_admin)):
    """Get a single draft by slug with full detail."""
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    result = (
        client.table("posts")
        .select("*")
        .eq("slug", slug)
        .eq("status", "draft")
        .maybe_single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Draft not found")

    return PostDraftDetail.model_validate(result.data)


@router.patch(
    "/posts/{post_id}/publish",
    response_model=PostPublishResponse,
    responses={
        **ERROR_RESPONSES,
        404: {"model": ErrorResponse, "description": "Post not found"},
    },
)
async def publish_post(post_id: str, _user=Depends(require_admin)):
    """Change post status from draft to published."""
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    now = datetime.now(timezone.utc).isoformat()

    result = (
        client.table("posts")
        .update({"status": "published", "published_at": now})
        .eq("id", post_id)
        .eq("status", "draft")
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Post not found or not a draft")

    row = result.data[0]
    return PostPublishResponse(
        id=row["id"],
        slug=row["slug"],
        status=row["status"],
        published_at=row["published_at"],
    )


@router.patch(
    "/posts/{post_id}/update",
    response_model=PostDraftDetail,
    responses={
        **ERROR_RESPONSES,
        404: {"model": ErrorResponse, "description": "Post not found"},
    },
)
async def update_post(post_id: str, body: PostUpdateRequest, _user=Depends(require_admin)):
    """Update draft content fields."""
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields to update")

    # Serialize nested Pydantic models to dicts for JSONB columns
    for key in ("guide_items", "related_news"):
        if key in update_data and hasattr(update_data[key], "model_dump"):
            update_data[key] = update_data[key].model_dump()

    result = (
        client.table("posts")
        .update(update_data)
        .eq("id", post_id)
        .eq("status", "draft")
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Post not found or not a draft")

    return PostDraftDetail.model_validate(result.data[0])
