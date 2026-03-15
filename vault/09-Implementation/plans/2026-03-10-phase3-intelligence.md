# Phase 3-Intelligence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Shared embedding layer (Pinecone) powering reader recommendations + admin quality gate, analytics, and topic suggestion.

**Architecture:** On post publish, OpenAI text-embedding-3-small embeds title+excerpt+category+tags → stored in Pinecone index `news-posts`. Reader recommendations query this index for similar/personalized posts. Admin tools use DB aggregates (quality flags, engagement counts, Tavily topics).

**Tech Stack:** OpenAI embeddings (text-embedding-3-small, 1536 dims), Pinecone Python SDK v5+, FastAPI background tasks, Astro SSR fetch

**Reference:** `docs/plans/2026-03-10-phase3-intelligence-design.md`

---

## Task 1: Dependencies + Config

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/core/config.py`
- Modify: `backend/.env.example`

**Step 1: Add Pinecone to requirements**

In `backend/requirements.txt`, add after `openai>=1.0.0`:
```
pinecone>=5.0.0
```

**Step 2: Add settings to config**

Read `backend/core/config.py` first. Add to the `Settings` class:
```python
pinecone_api_key: str = ""
pinecone_index_name: str = "news-posts"
```

**Step 3: Update .env.example**

Add:
```
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=news-posts
```

**Step 4: Install in venv**

```bash
cd backend && .venv/Scripts/pip install pinecone>=5.0.0
```
Expected: Successfully installed pinecone-...

**Step 5: Verify import**

```bash
cd backend && .venv/Scripts/python -c "from pinecone import Pinecone; print('ok')"
```
Expected: `ok`

**Step 6: Commit**

```bash
git add backend/requirements.txt backend/core/config.py backend/.env.example
git commit -m "feat: add pinecone dependency + config settings"
```

---

## Task 2: Create Pinecone Index

One-time setup. The index must exist before any upsert.

**Step 1: Create index via Pinecone MCP**

Use the `mcp__plugin_pinecone_pinecone__create-index-for-model` tool:
- index_name: `news-posts`
- model: `text-embedding-3-small`
- cloud: `aws`
- region: `us-east-1`

OR create manually in Pinecone dashboard:
- Name: `news-posts`
- Dimensions: `1536`
- Metric: `cosine`
- Pod type: Serverless

**Step 2: Verify index exists**

```bash
# Use describe-index MCP tool with name "news-posts"
# Expected: index shows Ready status
```

---

## Task 3: Embedding Service

**Files:**
- Create: `backend/services/embedding.py`
- Create: `backend/tests/test_embedding.py`

**Step 1: Write the failing test**

Create `backend/tests/test_embedding.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_build_embed_text():
    from services.embedding import _build_embed_text
    text = _build_embed_text(
        title="GPT-5 Released",
        excerpt="OpenAI releases GPT-5",
        category="ai-news",
        tags=["openai", "llm"],
    )
    assert "GPT-5 Released" in text
    assert "OpenAI releases GPT-5" in text
    assert "ai-news" in text
    assert "openai" in text


@pytest.mark.asyncio
async def test_embed_post_calls_openai_and_pinecone():
    from services.embedding import embed_post

    mock_embedding = [0.1] * 1536
    mock_openai = AsyncMock()
    mock_openai.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=mock_embedding)]
    )
    mock_index = MagicMock()
    mock_index.upsert = MagicMock()

    with patch("services.embedding._get_openai_client", return_value=mock_openai), \
         patch("services.embedding._get_pinecone_index", return_value=mock_index):
        await embed_post(
            post_id="abc-123",
            title="GPT-5 Released",
            excerpt="OpenAI releases GPT-5",
            category="ai-news",
            tags=["openai"],
            locale="en",
            slug="gpt-5-released",
            published_at="2026-03-10",
        )

    mock_openai.embeddings.create.assert_called_once()
    mock_index.upsert.assert_called_once()
    call_kwargs = mock_index.upsert.call_args
    vectors = call_kwargs[1]["vectors"] if "vectors" in call_kwargs[1] else call_kwargs[0][0]
    assert vectors[0]["id"] == "abc-123"
    assert vectors[0]["values"] == mock_embedding
    assert vectors[0]["metadata"]["locale"] == "en"
```

**Step 2: Run test to verify it fails**

```bash
cd backend && .venv/Scripts/python -m pytest tests/test_embedding.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'services.embedding'`

**Step 3: Create embedding service**

Create `backend/services/embedding.py`:
```python
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
        model="text-embedding-3-small",
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

    # Fetch the post's own vector
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

    # Fetch vectors for recent history (up to 5)
    history_ids = reading_history_ids[:5]
    fetch_result = index.fetch(ids=history_ids)
    vectors = [v.values for v in fetch_result.vectors.values()]
    if not vectors:
        return []

    # Average the vectors
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
```

**Step 4: Run tests to verify they pass**

```bash
cd backend && .venv/Scripts/python -m pytest tests/test_embedding.py -v
```
Expected: 2 tests PASS

**Step 5: Commit**

```bash
git add backend/services/embedding.py backend/tests/test_embedding.py
git commit -m "feat: embedding service (embed_post, get_similar, get_for_you, embed_backfill)"
```

---

## Task 4: Pipeline Integration + Backfill Cron

**Files:**
- Modify: `backend/services/pipeline.py`
- Modify: `backend/routers/cron.py`

**Step 1: Add embed step to pipeline**

In `backend/services/pipeline.py`, after the existing imports add:
```python
from services.embedding import embed_post
```

In `run_daily_pipeline()`, after `_extract_and_create_terms(...)` (Step 4), add Step 5:
```python
        # Step 5: Embed published posts into Pinecone (non-fatal)
        try:
            # Embed the EN posts that were just published
            # Note: only published posts are useful for recommendations
            # Draft posts are skipped — embed on publish via admin
            pass  # Will embed on admin publish action; pipeline saves as draft
        except Exception as e:
            logger.error("Embedding step failed (non-fatal): %s", e)
```

Wait — pipeline saves posts as `status: "draft"`. Embedding should happen when admin **publishes** a post.

So instead, add embed call to the admin publish endpoint in `admin.py`.

**Step 2: Add embed to admin publish**

Read `backend/routers/admin.py` and find the publish endpoint (look for `status: "published"` update). After the DB update succeeds, add a background task to embed the post:

```python
from services.embedding import embed_post

# Inside the publish endpoint, after DB update:
background_tasks.add_task(
    embed_post,
    post_id=str(post["id"]),
    title=post.get("title", ""),
    excerpt=post.get("excerpt", "") or "",
    category=post.get("category", "") or "",
    tags=post.get("tags", []) or [],
    locale=post.get("locale", "en"),
    slug=post.get("slug", ""),
    published_at=post.get("published_at", "") or "",
)
```

You'll need to add `background_tasks: BackgroundTasks` param to the publish endpoint signature if not present.

**Step 3: Add embed-backfill cron endpoint**

In `backend/routers/cron.py`, add after the existing imports:
```python
from services.embedding import embed_backfill
```

Add new endpoint:
```python
@router.post(
    "/cron/embed-backfill",
    status_code=202,
    response_model=PipelineAcceptedResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid cron secret"},
    },
)
@limiter.limit("2/minute")
async def run_embed_backfill(
    request: Request,
    background_tasks: BackgroundTasks,
    locale: Optional[str] = Query(None, description="Filter by locale (en/ko). Defaults to all."),
    _: None = Depends(verify_cron_secret),
):
    """Backfill Pinecone embeddings for all published posts."""
    background_tasks.add_task(embed_backfill, locale)
    msg = f"Embed backfill queued" + (f" for locale={locale}" if locale else " for all locales")
    return PipelineAcceptedResponse(accepted=True, message=msg)
```

**Step 4: Lint check**

```bash
cd backend && .venv/Scripts/python -m ruff check .
```
Expected: 0 errors (or only pre-existing issues)

**Step 5: Commit**

```bash
git add backend/services/pipeline.py backend/routers/admin.py backend/routers/cron.py
git commit -m "feat: embed posts on publish + /cron/embed-backfill endpoint"
```

---

## Task 5: Recommendations Backend Router

**Files:**
- Create: `backend/routers/recommendations.py`
- Modify: `backend/main.py`

**Step 1: Create recommendations router**

Create `backend/routers/recommendations.py`:
```python
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core.rate_limit import limiter
from core.security import get_optional_user
from services.embedding import get_similar_posts, get_for_you_posts
from core.database import get_supabase

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
    post_id: str,
    locale: str = "en",
    user=Depends(get_optional_user),
):
    """Return similar posts to the given post_id using vector similarity."""
    exclude_ids: list[str] = []

    # If logged in, exclude already-read posts
    if user:
        client = get_supabase()
        if client:
            result = client.table("reading_history").select("item_id") \
                .eq("user_id", user.id).eq("item_type", "news").execute()
            exclude_ids = [r["item_id"] for r in (result.data or [])]

    similar = await get_similar_posts(
        post_id=post_id,
        locale=locale,
        top_k=3,
        exclude_ids=exclude_ids,
    )
    return [RecommendedPost(**p) for p in similar]


@router.get("/for-you", response_model=list[RecommendedPost])
@limiter.limit("20/minute")
async def for_you(
    request: Request,
    locale: str = "en",
    user=Depends(get_optional_user),
):
    """Return personalized recommendations based on reading history."""
    if not user:
        raise HTTPException(status_code=401, detail="Login required for personalized recommendations")

    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    # Get recent reading history IDs (last 5 news posts)
    history = client.table("reading_history").select("item_id") \
        .eq("user_id", user.id).eq("item_type", "news") \
        .order("read_at", desc=True).limit(10).execute()
    reading_ids = [r["item_id"] for r in (history.data or [])]

    # Get bookmark IDs to exclude
    bookmarks = client.table("user_bookmarks").select("item_id") \
        .eq("user_id", user.id).eq("item_type", "news").execute()
    bookmark_ids = [r["item_id"] for r in (bookmarks.data or [])]

    posts = await get_for_you_posts(
        reading_history_ids=reading_ids,
        locale=locale,
        top_k=6,
        exclude_ids=bookmark_ids,
    )
    return [RecommendedPost(**p) for p in posts]
```

**Step 2: Check if get_optional_user exists**

Search `backend/core/security.py` for `get_optional_user`. If it doesn't exist, add it:
```python
async def get_optional_user(request: Request):
    """Returns user if authenticated, None otherwise. Does not raise."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
```

**Step 3: Register router in main.py**

In `backend/main.py`, add after existing router registrations:
```python
from routers.recommendations import router as recommendations_router
app.include_router(recommendations_router)
```

**Step 4: Lint check**

```bash
cd backend && .venv/Scripts/python -m ruff check .
```
Expected: 0 errors

**Step 5: Commit**

```bash
git add backend/routers/recommendations.py backend/main.py backend/core/security.py
git commit -m "feat: recommendations router (similar + for-you endpoints)"
```

---

## Task 6: Similar Articles — Frontend

**Files:**
- Modify: `frontend/src/pages/en/news/[slug].astro`
- Modify: `frontend/src/pages/ko/news/[slug].astro`
- Modify: `frontend/src/components/newsprint/NewsprintSideRail.astro`

**Step 1: Fetch similar posts in EN slug page**

In `frontend/src/pages/en/news/[slug].astro`, in the `if (post)` block, add after `focusItems`:
```typescript
// Fetch similar posts from recommendations API
let similarPosts: { post_id: string; slug: string; title: string; category: string }[] = [];
const fastapiUrl = import.meta.env.FASTAPI_URL;
if (fastapiUrl && post.id) {
  try {
    const res = await fetch(
      `${fastapiUrl}/recommendations/similar?post_id=${post.id}&locale=en`,
      { signal: AbortSignal.timeout(3000) }
    );
    if (res.ok) {
      similarPosts = await res.json();
    }
  } catch {
    // Non-fatal: fall back to empty
  }
}
```

**Step 2: Pass similarPosts to NewsprintSideRail**

In the same file, update the NewsprintSideRail usage:
```astro
<NewsprintSideRail
  locale="en"
  posts={recentPosts}
  focusItems={focusItems}
  relatedNews={post?.related_news}
  similarPosts={similarPosts}
/>
```

**Step 3: Repeat for KO slug page**

Apply the same changes to `frontend/src/pages/ko/news/[slug].astro`:
- Fetch similar with `locale=ko`
- Pass `similarPosts={similarPosts}` prop

**Step 4: Add similarPosts prop + section to NewsprintSideRail**

In `frontend/src/components/newsprint/NewsprintSideRail.astro`, add to Props interface:
```typescript
interface SimilarPost {
  post_id: string;
  slug: string;
  title: string;
  category: string;
}

interface Props {
  locale: 'en' | 'ko';
  posts: RailPost[];
  focusItems: string[];
  relatedNews?: RelatedNews | null;
  similarPosts?: SimilarPost[];
  basePath?: string;
}
```

Destructure: `const { locale, posts, focusItems, relatedNews, similarPosts = [], basePath } = Astro.props;`

Add section after the Related News section:
```astro
{similarPosts.length > 0 && (
  <>
    <div style="margin-top: 1.5rem;"></div>
    <section>
      <h3 class="newsprint-section-title">{isKo ? '비슷한 글' : 'You Might Also Like'}</h3>
      <div class="newsprint-stack">
        {similarPosts.map((p) => (
          <a class="newsprint-card" href={`${resolvedBasePath}/${p.slug}/`}>
            <strong class="newsprint-rail-link">{p.title}</strong>
            {getCategoryLabel(locale, p.category) && (
              <span class="newsprint-category newsprint-rail-category">
                {getCategoryLabel(locale, p.category)}
              </span>
            )}
          </a>
        ))}
      </div>
    </section>
  </>
)}
```

**Step 5: Build check**

```bash
cd frontend && npm run build
```
Expected: 0 errors

**Step 6: Commit**

```bash
git add frontend/src/pages/en/news/[slug].astro frontend/src/pages/ko/news/[slug].astro frontend/src/components/newsprint/NewsprintSideRail.astro
git commit -m "feat: similar posts recommendations on article detail page"
```

---

## Task 7: For-You Tab in Library

**Files:**
- Modify: `frontend/src/pages/library/index.astro`

**Step 1: Read the full library page first**

```bash
# Read frontend/src/pages/library/index.astro fully to understand tab structure
```

**Step 2: Add 추천 tab copy**

In the `copy` object, add:
```typescript
// Korean:
tabRecommended: '추천 읽기',
emptyRecommended: '읽기 기록이 쌓이면 맞춤 추천이 생겨요',

// English:
tabRecommended: 'For You',
emptyRecommended: 'Read a few articles and we\'ll suggest more',
```

**Step 3: Fetch recommended posts server-side**

After the existing Supabase data fetches, add:
```typescript
let recommendedPosts: { post_id: string; slug: string; title: string; category: string }[] = [];
const fastapiUrl = import.meta.env.FASTAPI_URL;
if (fastapiUrl && accessToken) {
  try {
    const res = await fetch(
      `${fastapiUrl}/recommendations/for-you?locale=${locale}`,
      {
        headers: { Authorization: `Bearer ${accessToken}` },
        signal: AbortSignal.timeout(4000),
      }
    );
    if (res.ok) recommendedPosts = await res.json();
  } catch {
    // Non-fatal
  }
}
```

**Step 4: Add tab button**

In the tab row (where tabSaved, tabRead, tabProgress buttons are), add:
```astro
<button
  class={`library-tab-btn${activeTab === 'recommended' ? ' library-tab-btn--active' : ''}`}
  data-tab="recommended"
>
  {copy.tabRecommended}
</button>
```

**Step 5: Add tab panel**

After the existing tab panels, add:
```astro
<div class="library-tab-panel" id="tab-recommended" style={activeTab === 'recommended' ? '' : 'display:none'}>
  {recommendedPosts.length === 0 ? (
    <p class="library-empty">{copy.emptyRecommended}</p>
  ) : (
    <div class="library-book-row">
      {recommendedPosts.map((p) => (
        <a class="library-book-card" href={`/${locale}/news/${p.slug}/`}>
          <div class="library-book-spine" style={`background:${spineColor(p.category)}`}></div>
          <div class="library-book-info">
            <p class="library-book-title">{p.title}</p>
          </div>
        </a>
      ))}
    </div>
  )}
</div>
```

**Step 6: Check tab switching JS handles the new tab**

Find the existing tab-switching script and ensure it covers `recommended` tab. The existing JS likely uses `data-tab` attribute — the new button will work automatically if the pattern is the same.

**Step 7: Build check**

```bash
cd frontend && npm run build
```
Expected: 0 errors

**Step 8: Commit**

```bash
git add frontend/src/pages/library/index.astro
git commit -m "feat: for-you recommendation tab in library page"
```

---

## Task 8: Quality Gate

**Files:**
- Create: `backend/services/quality.py`
- Modify: `backend/services/pipeline.py` (add quality score step)
- Modify: `backend/routers/admin.py` (expose quality in draft list)

**Step 1: Create quality service**

Create `backend/services/quality.py`:
```python
from typing import Any


MIN_CONTENT_CHARS = 3000
GUIDE_FIELDS = ("one_liner", "action_item", "critical_gotcha", "rotating_item")
RELATED_NEWS_KEYS = ("big_tech", "industry_biz", "new_tools")


def compute_quality(post: dict[str, Any]) -> tuple[int, dict[str, bool]]:
    """Compute quality score (0-4) and flags dict for a post.

    Returns (score, flags) where flags marks missing items as True.
    Score: 4=Ready, 3=Minor, 2=Review, 1-0=Incomplete.
    """
    flags: dict[str, bool] = {}

    # Check content length (business: learner; research: original)
    content = (
        post.get("content_learner") or
        post.get("content_original") or
        ""
    )
    flags["short_content"] = len(content) < MIN_CONTENT_CHARS

    # Check guide_items
    guide = post.get("guide_items") or {}
    flags["missing_guide_items"] = not all(guide.get(f) for f in GUIDE_FIELDS)

    # Check related_news
    related = post.get("related_news") or {}
    flags["missing_related_news"] = not all(related.get(k) for k in RELATED_NEWS_KEYS)

    # Check og_image
    flags["missing_og_image"] = not post.get("og_image_url")

    missing_count = sum(flags.values())
    score = max(0, 4 - missing_count)

    return score, flags
```

**Step 2: Write a test for quality**

In `backend/tests/test_quality.py`:
```python
from services.quality import compute_quality


def test_perfect_post():
    post = {
        "content_learner": "x" * 3001,
        "guide_items": {
            "one_liner": "a", "action_item": "b",
            "critical_gotcha": "c", "rotating_item": "d",
        },
        "related_news": {"big_tech": {...}, "industry_biz": {...}, "new_tools": {...}},
        "og_image_url": "https://example.com/img.jpg",
    }
    score, flags = compute_quality(post)
    assert score == 4
    assert not any(flags.values())


def test_empty_post():
    score, flags = compute_quality({})
    assert score == 0
    assert all(flags.values())


def test_partial_post():
    post = {
        "content_learner": "x" * 3001,
        "guide_items": {"one_liner": "a"},  # incomplete
    }
    score, flags = compute_quality(post)
    assert flags["missing_guide_items"] is True
    assert flags["short_content"] is False
    assert score == 2
```

**Step 3: Run tests**

```bash
cd backend && .venv/Scripts/python -m pytest tests/test_quality.py -v
```
Expected: all PASS

**Step 4: Save quality score after post save in pipeline**

In `backend/services/pipeline.py`, add import:
```python
from services.quality import compute_quality
```

Add a helper to save quality score after `_save_post`:
```python
def _update_quality_score(client, post_id: str, post_data: dict) -> None:
    """Compute and persist quality score for a post."""
    try:
        score, flags = compute_quality(post_data)
        client.table("news_posts").update({
            "quality_score": score,
            "quality_flags": flags,
        }).eq("id", post_id).execute()
    except Exception as e:
        logger.warning("Quality score update failed for %s: %s", post_id, e)
```

Call this after `_save_research_post` and `_save_business_post` return post_id.

**Step 5: DB migration for quality columns**

Run in Supabase SQL editor:
```sql
ALTER TABLE news_posts ADD COLUMN IF NOT EXISTS quality_score integer DEFAULT NULL;
ALTER TABLE news_posts ADD COLUMN IF NOT EXISTS quality_flags jsonb DEFAULT NULL;
```

**Step 6: Expose quality in admin drafts list**

In `backend/routers/admin.py`, update the `/drafts` select query to include the new columns:
```python
.select(
    "id, title, slug, category, post_type, status, "
    "news_temperature, pipeline_batch_id, quality_score, quality_flags, "
    "created_at, updated_at"
)
```

Update `PostDraftListItem` model in `backend/models/posts.py` to accept optional quality fields:
```python
quality_score: Optional[int] = None
quality_flags: Optional[dict] = None
```

**Step 7: Add quality badge to admin list UI**

In the admin drafts table (find the admin frontend file — likely `frontend/src/pages/admin/index.astro` or similar), add a quality badge column. For each draft with `quality_score`:
- score 4: `✅ Ready`
- score 3: `⚠️ Minor`
- score 2: `⚠️ Review`
- score ≤ 1: `❌ Incomplete`

**Step 8: Build + lint**

```bash
cd backend && .venv/Scripts/python -m ruff check .
cd frontend && npm run build
```
Expected: 0 errors

**Step 9: Commit**

```bash
git add backend/services/quality.py backend/tests/test_quality.py backend/services/pipeline.py backend/routers/admin.py backend/models/posts.py
git commit -m "feat: quality gate (score + flags) on pipeline save + admin drafts badge"
```

---

## Task 9: Analytics Dashboard

**Files:**
- Modify: `backend/routers/admin.py`
- Modify: Admin dashboard UI (find the file with admin index page)

**Step 1: Add analytics endpoint**

In `backend/routers/admin.py`, add:
```python
from datetime import date, timedelta

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

    # Top posts by likes
    likes = client.table("news_likes").select("post_id, news_posts(title, slug, category)") \
        .gte("created_at", since).execute()

    # Top posts by bookmarks
    bookmarks = client.table("user_bookmarks").select("item_id, news_posts!item_id(title, slug, category)") \
        .eq("item_type", "news").gte("created_at", since).execute()

    # Top posts by reads
    reads = client.table("reading_history").select("item_id") \
        .eq("item_type", "news").gte("read_at", since).execute()

    # Aggregate counts
    from collections import Counter
    like_counts = Counter(r["post_id"] for r in (likes.data or []))
    read_counts = Counter(r["item_id"] for r in (reads.data or []))
    bookmark_counts = Counter(r["item_id"] for r in (bookmarks.data or []))

    # Get post metadata for top IDs
    all_ids = list(set(list(like_counts.keys())[:20] + list(read_counts.keys())[:20]))
    posts_meta = {}
    if all_ids:
        meta = client.table("news_posts").select("id, title, slug, category") \
            .in_("id", all_ids).execute()
        posts_meta = {p["id"]: p for p in (meta.data or [])}

    top_posts = [
        {
            "post_id": pid,
            "title": posts_meta.get(pid, {}).get("title", ""),
            "slug": posts_meta.get(pid, {}).get("slug", ""),
            "category": posts_meta.get(pid, {}).get("category", ""),
            "likes": like_counts.get(pid, 0),
            "reads": read_counts.get(pid, 0),
            "bookmarks": bookmark_counts.get(pid, 0),
        }
        for pid in set(list(like_counts.keys()) + list(read_counts.keys()))
    ]
    top_posts.sort(key=lambda x: x["reads"] + x["likes"] * 2, reverse=True)

    return {
        "days": days,
        "total_likes": sum(like_counts.values()),
        "total_reads": sum(read_counts.values()),
        "total_bookmarks": sum(bookmark_counts.values()),
        "top_posts": top_posts[:10],
    }
```

**Step 2: Add analytics section to admin dashboard**

Find the admin dashboard page (likely `frontend/src/pages/admin/index.astro`). Add an analytics card that:
- Fetches `GET /api/admin/analytics` (via frontend API proxy)
- Shows total_reads, total_likes, total_bookmarks as stat cards
- Shows top_posts table with title + engagement counts

This is a client-side fetch via `<script>` since admin pages use vanilla JS:
```javascript
async function loadAnalytics() {
  const res = await fetch('/api/admin/analytics');
  if (!res.ok) return;
  const data = await res.json();
  // Render stats into DOM
  document.getElementById('stat-reads').textContent = data.total_reads;
  document.getElementById('stat-likes').textContent = data.total_likes;
  document.getElementById('stat-bookmarks').textContent = data.total_bookmarks;
}
document.addEventListener('astro:page-load', loadAnalytics);
```

You'll also need a frontend API route `frontend/src/pages/api/admin/analytics.ts` that proxies to the backend with the admin auth token.

**Step 3: Build + lint**

```bash
cd backend && .venv/Scripts/python -m ruff check .
cd frontend && npm run build
```
Expected: 0 errors

**Step 4: Commit**

```bash
git add backend/routers/admin.py frontend/src/pages/api/admin/analytics.ts frontend/src/pages/admin/index.astro
git commit -m "feat: admin analytics endpoint + dashboard engagement stats"
```

---

## Task 10: Topic Suggestion

**Files:**
- Modify: `backend/routers/admin.py`
- Modify: Admin dashboard UI

**Step 1: Add suggest-topics endpoint**

In `backend/routers/admin.py`, add:
```python
from tavily import TavilyClient

@router.post("/suggest-topics", responses=ERROR_RESPONSES)
@limiter.limit("5/minute")
async def suggest_topics(
    request: Request,
    _user=Depends(require_admin),
):
    """Suggest next pipeline batch topics using recent posts + trending news."""
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    from datetime import date, timedelta
    from openai import AsyncOpenAI
    from collections import Counter

    since = (date.today() - timedelta(days=14)).isoformat()

    # Recent published posts (last 14 days)
    recent = client.table("news_posts").select("title, category, tags") \
        .eq("status", "published").gte("published_at", since).execute()
    recent_posts = recent.data or []

    # Category distribution
    categories = Counter(p.get("category", "") for p in recent_posts)
    all_tags = [t for p in recent_posts for t in (p.get("tags") or [])]
    top_tags = [t for t, _ in Counter(all_tags).most_common(10)]
    recent_titles = [p["title"] for p in recent_posts[:10]]

    # Fetch trending news via Tavily
    tavily_results = []
    if settings.tavily_api_key:
        try:
            tavily = TavilyClient(api_key=settings.tavily_api_key)
            search = tavily.search("AI news today", max_results=5)
            tavily_results = [r.get("title", "") for r in search.get("results", [])]
        except Exception as e:
            logger.warning("Tavily search failed: %s", e)

    # GPT-4o-mini suggestion
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = f"""You are an AI news editor. Suggest 5 topics for the next pipeline batch.

Recently covered titles (avoid repetition):
{chr(10).join(f'- {t}' for t in recent_titles)}

Trending today:
{chr(10).join(f'- {t}' for t in tavily_results)}

Top tags used: {', '.join(top_tags)}

Return exactly 5 topic suggestions as a JSON array of strings. Each suggestion should be a specific, newsworthy AI topic not already covered. Example format:
["Topic 1", "Topic 2", "Topic 3", "Topic 4", "Topic 5"]"""

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=512,
    )

    import json
    try:
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        # Handle both {"topics": [...]} and [...] responses
        if isinstance(parsed, list):
            topics = parsed
        else:
            topics = next((v for v in parsed.values() if isinstance(v, list)), [])
    except Exception:
        topics = []

    return {"topics": topics[:5]}
```

**Step 2: Add frontend API proxy**

Create `frontend/src/pages/api/admin/suggest-topics.ts`:
```typescript
import type { APIRoute } from 'astro';

export const POST: APIRoute = async ({ request, locals }) => {
  if (!locals.isAdmin) {
    return new Response(JSON.stringify({ error: 'Forbidden' }), { status: 403 });
  }

  const fastapiUrl = import.meta.env.FASTAPI_URL;
  const res = await fetch(`${fastapiUrl}/admin/suggest-topics`, {
    method: 'POST',
    headers: {
      'x-admin-token': import.meta.env.ADMIN_SECRET || '',
      'Content-Type': 'application/json',
    },
  });

  const data = await res.json();
  return new Response(JSON.stringify(data), {
    status: res.status,
    headers: { 'Content-Type': 'application/json' },
  });
};
```

Note: Check how other admin API routes pass auth to the backend (may use different header). Match the existing pattern.

**Step 3: Add Topic Suggestion UI to admin dashboard**

In admin dashboard, add a "Suggest Topics" button that:
1. Calls `POST /api/admin/suggest-topics`
2. Shows loading state
3. Renders the 5 suggested topics as clickable chips

```javascript
async function suggestTopics() {
  const btn = document.getElementById('btn-suggest-topics');
  btn.disabled = true;
  btn.textContent = 'Thinking…';

  try {
    const res = await fetch('/api/admin/suggest-topics', { method: 'POST' });
    const data = await res.json();
    const container = document.getElementById('topic-suggestions');
    container.innerHTML = data.topics.map(t =>
      `<span class="admin-topic-chip">${t}</span>`
    ).join('');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Suggest Topics';
  }
}
```

Add CSS for `.admin-topic-chip` in `global.css`.

**Step 4: Build + lint**

```bash
cd backend && .venv/Scripts/python -m ruff check .
cd frontend && npm run build
```
Expected: 0 errors

**Step 5: Commit**

```bash
git add backend/routers/admin.py frontend/src/pages/api/admin/suggest-topics.ts frontend/src/pages/admin/index.astro frontend/src/styles/global.css
git commit -m "feat: topic suggestion endpoint + admin dashboard UI"
```

---

## Verification Checklist

After all tasks complete:

1. `cd backend && .venv/Scripts/python -m ruff check .` — 0 errors
2. `cd backend && .venv/Scripts/python -m pytest tests/ -v --tb=short` — embedding + quality tests pass
3. `cd frontend && npm run build` — 0 errors
4. Run embed backfill: `curl -X POST "BACKEND_URL/cron/embed-backfill" -H "x-cron-secret: SECRET"`
5. Visit an article detail page → "You Might Also Like" section appears at bottom of sidebar
6. Visit /library logged in → "For You" tab shows recommended posts
7. Admin drafts list → quality badge (✅/⚠️/❌) visible per post
8. Admin dashboard → total reads/likes/bookmarks stats visible
9. Admin dashboard → "Suggest Topics" button → 5 AI topic suggestions returned

---

## Task Execution Order

```
Task 1 (Dependencies)
  → Task 2 (Create Pinecone Index)
    → Task 3 (Embedding Service)
      → Task 4 (Pipeline + Cron)
        → Task 5 (Recommendations Router)
          → Task 6 (Similar Frontend)
          → Task 7 (For-You Library)

Task 8 (Quality Gate) — parallel with Tasks 5-7
Task 9 (Analytics) — parallel with Tasks 5-7
Task 10 (Topic Suggestion) — parallel with Tasks 5-7
```

## Related Plans

- [[plans/2026-03-10-phase3-intelligence-design|Phase 3 설계]]
