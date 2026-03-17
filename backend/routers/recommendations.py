import logging

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from core.rate_limit import limiter
from core.database import get_supabase
from services.embedding import get_similar_posts, get_for_you_posts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RecommendedPost(BaseModel):
    post_id: str
    slug: str
    title: str
    category: str
    score: float


@router.get("/similar", response_model=list[RecommendedPost])
@limiter.limit("30/minute")
async def similar_posts(
    request: Request,
    post_id: str = Query(..., min_length=1, max_length=256),
    locale: str = Query(default="en", pattern=r"^(en|ko)$"),
):
    """Return similar posts to the given post_id using vector similarity."""
    # No auth required — public endpoint
    similar = await get_similar_posts(
        post_id=post_id,
        locale=locale,
        top_k=3,
    )
    return [RecommendedPost(**p) for p in similar]


@router.get("/for-you", response_model=list[RecommendedPost])
@limiter.limit("20/minute")
async def for_you(
    request: Request,
    locale: str = Query(default="en", pattern=r"^(en|ko)$"),
    user_id: str = Query(..., min_length=1, max_length=256),
):
    """Return personalized recommendations. user_id passed as query param from SSR."""

    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    # Get recent reading history IDs (last 10 news posts)
    history = client.table("reading_history").select("item_id") \
        .eq("user_id", user_id).eq("item_type", "news") \
        .order("read_at", desc=True).limit(10).execute()
    reading_ids = [r["item_id"] for r in (history.data or [])]

    # Get bookmark IDs to exclude
    bookmarks = client.table("user_bookmarks").select("item_id") \
        .eq("user_id", user_id).eq("item_type", "news").execute()
    bookmark_ids = [r["item_id"] for r in (bookmarks.data or [])]

    posts = await get_for_you_posts(
        reading_history_ids=reading_ids,
        locale=locale,
        top_k=6,
        exclude_ids=bookmark_ids,
    )
    return [RecommendedPost(**p) for p in posts]
