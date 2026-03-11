import logging
from typing import Optional

from openai import AsyncOpenAI
from pinecone import Pinecone

from core.config import settings
from core.database import get_supabase

logger = logging.getLogger(__name__)

_openai_client: Optional[AsyncOpenAI] = None
_pinecone_index = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is None:
        if not settings.pinecone_api_key:
            raise RuntimeError("PINECONE_API_KEY not configured")
        pc = Pinecone(api_key=settings.pinecone_api_key)
        _pinecone_index = pc.Index(settings.pinecone_index_name)
    return _pinecone_index


def _build_embed_text(
    title: str,
    excerpt: str,
    category: str,
    tags: list[str],
) -> str:
    """Combine post fields into a single string for embedding."""
    tag_str = " ".join(tags) if tags else ""
    return f"{title}\n{excerpt}\n{category}\n{tag_str}".strip()


async def embed_post(
    post_id: str,
    title: str,
    excerpt: str,
    category: str,
    tags: list[str],
    locale: str,
    slug: str,
    published_at: str,
) -> None:
    """Generate embedding for a post and upsert to Pinecone."""
    if not settings.pinecone_api_key:
        logger.warning("Pinecone not configured, skipping embed for post %s", post_id)
        return
    text = _build_embed_text(title, excerpt or "", category or "", tags or [])
    client = _get_openai_client()

    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    vector = response.data[0].embedding

    index = _get_pinecone_index()
    index.upsert(vectors=[{
        "id": post_id,
        "values": vector,
        "metadata": {
            "locale": locale,
            "category": category or "",
            "slug": slug,
            "title": title,
            "published_at": published_at or "",
        },
    }])
    logger.info("Embedded post %s (%s/%s)", post_id, locale, slug)


async def get_similar_posts(
    post_id: str,
    locale: str,
    top_k: int = 4,
    exclude_ids: Optional[list[str]] = None,
) -> list[dict]:
    """Return similar posts from Pinecone, excluding the source post and optionally read posts."""
    if not settings.pinecone_api_key:
        return []

    index = _get_pinecone_index()

    fetch_result = index.fetch(ids=[post_id])
    if post_id not in fetch_result.vectors:
        logger.warning("Post %s not found in Pinecone index", post_id)
        return []

    vector = fetch_result.vectors[post_id].values
    exclude = set(exclude_ids or [])
    exclude.add(post_id)

    results = index.query(
        vector=vector,
        top_k=top_k + len(exclude),
        filter={"locale": {"$eq": locale}},
        include_metadata=True,
    )

    matches = [
        {
            "post_id": m.id,
            "slug": m.metadata.get("slug", ""),
            "title": m.metadata.get("title", ""),
            "category": m.metadata.get("category", ""),
            "score": round(m.score, 3),
        }
        for m in results.matches
        if m.id not in exclude
    ]
    return matches[:top_k]


async def get_for_you_posts(
    reading_history_ids: list[str],
    locale: str,
    top_k: int = 6,
    exclude_ids: Optional[list[str]] = None,
) -> list[dict]:
    """Return personalized posts by averaging reading history embeddings."""
    if not settings.pinecone_api_key or not reading_history_ids:
        return []

    index = _get_pinecone_index()

    history_ids = reading_history_ids[:5]
    fetch_result = index.fetch(ids=history_ids)
    vectors = [v.values for v in fetch_result.vectors.values()]
    if not vectors:
        return []

    dims = len(vectors[0])
    avg_vector = [sum(v[i] for v in vectors) / len(vectors) for i in range(dims)]

    exclude = set(exclude_ids or []) | set(reading_history_ids)

    results = index.query(
        vector=avg_vector,
        top_k=top_k + len(exclude),
        filter={"locale": {"$eq": locale}},
        include_metadata=True,
    )

    matches = [
        {
            "post_id": m.id,
            "slug": m.metadata.get("slug", ""),
            "title": m.metadata.get("title", ""),
            "category": m.metadata.get("category", ""),
            "score": round(m.score, 3),
        }
        for m in results.matches
        if m.id not in exclude
    ]
    return matches[:top_k]


async def embed_backfill(locale: Optional[str] = None) -> int:
    """Embed all published posts that may not be in Pinecone yet."""
    client_sb = get_supabase()
    if not client_sb:
        logger.error("Supabase not configured")
        return 0

    query = (
        client_sb.table("news_posts")
        .select("id, title, excerpt, category, tags, locale, slug, published_at")
        .eq("status", "published")
    )
    if locale:
        query = query.eq("locale", locale)

    result = query.execute()
    posts = result.data or []

    count = 0
    for post in posts:
        try:
            await embed_post(
                post_id=post["id"],
                title=post.get("title", ""),
                excerpt=post.get("excerpt", "") or "",
                category=post.get("category", "") or "",
                tags=post.get("tags", []) or [],
                locale=post.get("locale", "en"),
                slug=post.get("slug", ""),
                published_at=post.get("published_at", "") or "",
            )
            count += 1
        except Exception as e:
            logger.error("Backfill failed for post %s: %s", post.get("id"), e)

    logger.info("Embed backfill complete: %d posts indexed", count)
    return count
