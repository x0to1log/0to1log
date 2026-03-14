import logging
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from core.config import settings
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


@router.post("/suggest-topics", responses=ERROR_RESPONSES)
@limiter.limit("5/minute")
async def suggest_topics(
    request: Request,
    _user=Depends(require_admin),
):
    """Suggest next pipeline batch topics using recent posts + trending AI news."""
    import json
    from openai import AsyncOpenAI
    from tavily import TavilyClient

    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    since = (date.today() - timedelta(days=14)).isoformat()

    # Recent published posts (last 14 days)
    recent_res = (
        client.table("news_posts")
        .select("title, category, tags")
        .eq("status", "published")
        .gte("published_at", since)
        .execute()
    )
    recent_posts = recent_res.data or []

    all_tags: list[str] = [t for p in recent_posts for t in (p.get("tags") or [])]
    top_tags = [t for t, _ in Counter(all_tags).most_common(10)]
    recent_titles = [p["title"] for p in recent_posts[:10]]

    # Fetch trending news via Tavily
    tavily_results: list[str] = []
    if settings.tavily_api_key:
        try:
            tavily = TavilyClient(api_key=settings.tavily_api_key)
            search = tavily.search("latest AI news today", max_results=5)
            tavily_results = [r.get("title", "") for r in search.get("results", [])]
        except Exception as e:
            logger.warning("Tavily search failed: %s", e)

    # GPT-4o-mini suggestion
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = (
        "You are an AI news editor. Suggest 5 specific, newsworthy AI topics for the next pipeline batch.\n\n"
        "Recently covered (avoid repetition):\n"
        + "\n".join(f"- {t}" for t in recent_titles)
        + "\n\nTrending today:\n"
        + "\n".join(f"- {t}" for t in tavily_results)
        + f"\n\nTop tags used: {', '.join(top_tags)}\n\n"
        'Return a JSON object with key "topics" containing an array of 5 strings. '
        'Example: {"topics": ["Topic 1", "Topic 2", "Topic 3", "Topic 4", "Topic 5"]}'
    )

    response = await openai_client.chat.completions.create(
        model=settings.openai_model_light,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=512,
    )

    try:
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        topics = parsed.get("topics", [])
        if not isinstance(topics, list):
            topics = []
    except Exception:
        topics = []

    return {"topics": topics[:5]}


@router.delete(
    "/pipeline/{batch_id}",
    responses=ERROR_RESPONSES,
)
@limiter.limit("5/minute")
async def delete_pipeline_batch(
    request: Request,
    batch_id: str,
    _user=Depends(require_admin),
):
    """Delete all pipeline data for a given batch_id (e.g. '2026-03-14').

    Removes: news_posts, news_candidates, pipeline_logs, pipeline_runs.
    """
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    run_key = f"daily:{batch_id}"
    deleted: dict[str, int] = {}

    # 1. Find pipeline_runs row to get run_id for log cleanup
    run_row = (
        client.table("pipeline_runs")
        .select("id")
        .eq("run_key", run_key)
        .maybe_single()
        .execute()
    )
    run_id = run_row.data["id"] if run_row and run_row.data else None

    # 2. Delete pipeline_logs (FK dependency first)
    if run_id:
        logs_res = (
            client.table("pipeline_logs")
            .delete()
            .eq("run_id", run_id)
            .execute()
        )
        deleted["pipeline_logs"] = len(logs_res.data or [])

    # 3. Delete news_posts
    posts_res = (
        client.table("news_posts")
        .delete()
        .eq("pipeline_batch_id", batch_id)
        .execute()
    )
    deleted["news_posts"] = len(posts_res.data or [])

    # 4. Delete news_candidates
    candidates_res = (
        client.table("news_candidates")
        .delete()
        .eq("batch_id", batch_id)
        .execute()
    )
    deleted["news_candidates"] = len(candidates_res.data or [])

    # 5. Delete pipeline_runs (last, after logs are gone)
    if run_id:
        client.table("pipeline_runs").delete().eq("id", run_id).execute()
        deleted["pipeline_runs"] = 1

    logger.info("Deleted pipeline batch %s: %s", batch_id, deleted)
    return {"batch_id": batch_id, "deleted": deleted}
