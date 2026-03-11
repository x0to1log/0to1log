import logging
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from core.database import get_supabase
from core.rate_limit import limiter
from core.security import require_admin
from models.posts import (
    PostDraftListItem,
    PostDraftDetail,
    PostPublishResponse,
    PostUpdateRequest,
    ErrorResponse,
)
from services.embedding import embed_post

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
@limiter.limit("30/minute")
async def list_drafts(request: Request, _user=Depends(require_admin)):
    """List all posts with status='draft'."""
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    result = (
        client.table("news_posts")
        .select(
            "id, title, slug, category, post_type, status, "
            "news_temperature, pipeline_batch_id, quality_score, quality_flags, "
            "created_at, updated_at"
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
@limiter.limit("30/minute")
async def get_draft(request: Request, slug: str, _user=Depends(require_admin)):
    """Get a single draft by slug with full detail."""
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    result = (
        client.table("news_posts")
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
@limiter.limit("10/minute")
async def publish_post(request: Request, post_id: str, background_tasks: BackgroundTasks, _user=Depends(require_admin)):
    """Change post status from draft to published."""
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    now = datetime.now(timezone.utc).isoformat()

    result = (
        client.table("news_posts")
        .update({"status": "published", "published_at": now})
        .eq("id", post_id)
        .eq("status", "draft")
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Post not found or not a draft")

    row = result.data[0]
    background_tasks.add_task(
        embed_post,
        post_id=str(row["id"]),
        title=row.get("title", ""),
        excerpt=row.get("excerpt", "") or "",
        category=row.get("category", "") or "",
        tags=row.get("tags", []) or [],
        locale=row.get("locale", "en"),
        slug=row.get("slug", ""),
        published_at=row.get("published_at", "") or "",
    )
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
@limiter.limit("10/minute")
async def update_post(request: Request, post_id: str, body: PostUpdateRequest, _user=Depends(require_admin)):
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
        client.table("news_posts")
        .update(update_data)
        .eq("id", post_id)
        .eq("status", "draft")
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Post not found or not a draft")

    return PostDraftDetail.model_validate(result.data[0])


@router.get("/analytics", responses=ERROR_RESPONSES)
@limiter.limit("10/minute")
async def get_analytics(
    request: Request,
    days: int = 30,
    _user=Depends(require_admin),
):
    """Return engagement analytics for published posts."""
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    since = (date.today() - timedelta(days=days)).isoformat()

    # Fetch engagement data since cutoff
    likes_res = client.table("news_likes").select("post_id").gte("created_at", since).execute()
    reads_res = client.table("reading_history").select("item_id").eq("item_type", "news").gte("read_at", since).execute()
    bookmarks_res = client.table("user_bookmarks").select("item_id").eq("item_type", "news").gte("created_at", since).execute()

    like_counts = Counter(r["post_id"] for r in (likes_res.data or []))
    read_counts = Counter(r["item_id"] for r in (reads_res.data or []))
    bookmark_counts = Counter(r["item_id"] for r in (bookmarks_res.data or []))

    # Get post metadata for top IDs
    all_ids = list({*list(like_counts.keys())[:20], *list(read_counts.keys())[:20]})
    posts_meta: dict[str, dict] = {}
    if all_ids:
        meta = client.table("news_posts").select("id, title, slug, category").in_("id", all_ids).execute()
        posts_meta = {p["id"]: p for p in (meta.data or [])}

    top_ids = set(list(like_counts.keys()) + list(read_counts.keys()))
    top_posts = sorted(
        [
            {
                "post_id": pid,
                "title": posts_meta.get(pid, {}).get("title", ""),
                "slug": posts_meta.get(pid, {}).get("slug", ""),
                "category": posts_meta.get(pid, {}).get("category", ""),
                "likes": like_counts.get(pid, 0),
                "reads": read_counts.get(pid, 0),
                "bookmarks": bookmark_counts.get(pid, 0),
            }
            for pid in top_ids
        ],
        key=lambda x: x["reads"] + x["likes"] * 2,
        reverse=True,
    )

    return {
        "days": days,
        "total_likes": sum(like_counts.values()),
        "total_reads": sum(read_counts.values()),
        "total_bookmarks": sum(bookmark_counts.values()),
        "top_posts": top_posts[:10],
    }
