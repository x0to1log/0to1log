import logging
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Optional

from core.database import get_supabase
from services.news_collection import collect_all_news
from services.agents import rank_candidates, generate_research_post, generate_business_post
from services.agents.translate import translate_post
from core.config import settings
from models.ranking import NewsCandidate, NewsRankingResult, RankedCandidate
from models.research import ResearchPost
from models.business import BusinessPost

logger = logging.getLogger(__name__)

STALE_THRESHOLD_SECONDS = 3600  # 1 hour
RESEARCH_MIN_RELEVANCE_SCORE = 0.85
RESEARCH_HIGH_SIGNAL_SCORE = 0.95
RESEARCH_TITLE_SIMILARITY_THRESHOLD = 0.88


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _parse_dt(dt_str: str) -> datetime:
    """Parse ISO datetime string to timezone-aware datetime."""
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _build_context(candidates: list[NewsCandidate]) -> str:
    """Build a context string from collected candidates for writing agents."""
    lines: list[str] = []
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}. [{c.source}] {c.title}\n   URL: {c.url}\n   {c.snippet}")
    return "\n\n".join(lines)


def _normalize_title_for_similarity(title: str) -> str:
    normalized = "".join(
        char.lower() if char.isalnum() else " "
        for char in (title or "")
    )
    return " ".join(normalized.split())


def _title_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(
        None,
        _normalize_title_for_similarity(left),
        _normalize_title_for_similarity(right),
    ).ratio()


def _should_skip_research_candidate(
    candidate: RankedCandidate,
    latest_post: dict | None,
) -> bool:
    score = candidate.relevance_score or 0.0
    if score < RESEARCH_MIN_RELEVANCE_SCORE:
        return True

    if not latest_post:
        return False

    latest_url = (latest_post.get("url") or "").rstrip("/")
    candidate_url = (candidate.url or "").rstrip("/")
    if latest_url and candidate_url and latest_url == candidate_url:
        return True

    title_similarity = _title_similarity(candidate.title, latest_post.get("title", ""))
    very_high_signal_override = (
        latest_url != candidate_url and score >= RESEARCH_HIGH_SIGNAL_SCORE
    )
    if title_similarity >= RESEARCH_TITLE_SIMILARITY_THRESHOLD and not very_high_signal_override:
        return True

    return False


def _get_latest_research_post(exclude_batch_id: str | None = None) -> dict | None:
    client = get_supabase()
    if not client:
        return None

    try:
        query = (
            client.table("news_posts")
            .select("title,url,created_at,pipeline_batch_id")
            .eq("category", "ai-news")
            .eq("post_type", "research")
            .eq("locale", "en")
        )
        if exclude_batch_id:
            query = query.neq("pipeline_batch_id", exclude_batch_id)

        result = query.order("created_at", desc=True).limit(1).execute()
        data = result.data if result else None
        if isinstance(data, list) and data:
            return data[0]
    except Exception as exc:
        logger.warning("Failed to load latest research post for novelty gate: %s", exc)

    return None


def _apply_research_novelty_gate(
    candidate: RankedCandidate | None,
    batch_id: str,
) -> RankedCandidate | None:
    if not candidate:
        return None

    latest_post = _get_latest_research_post(exclude_batch_id=batch_id)
    if _should_skip_research_candidate(candidate, latest_post):
        logger.info(
            "Research pick gated out for batch %s: score=%.2f title=%s latest=%s",
            batch_id,
            candidate.relevance_score,
            candidate.title[:120],
            (latest_post or {}).get("title", "-")[:120],
        )
        return None

    return candidate


async def acquire_pipeline_lock(batch_id: str) -> Optional[str]:
    """Attempt to acquire a pipeline lock for the given batch.

    Returns run_id if lock acquired, None if skipped.

    Lock rules:
    - success → skip (already done)
    - running < 1h → skip (in progress)
    - running >= 1h → UPDATE existing row (stale recovery)
    - failed → UPDATE existing row (retry)
    - no record → INSERT new row
    """
    client = get_supabase()
    if not client:
        logger.error("Supabase not configured, cannot acquire lock")
        return None

    run_key = f"daily:{batch_id}"

    existing = (
        client.table("pipeline_runs")
        .select("*")
        .eq("run_key", run_key)
        .maybe_single()
        .execute()
    )

    row = existing.data if existing else None
    if row:
        status = row["status"]

        if status == "success":
            logger.info("Pipeline %s already succeeded, skipping", run_key)
            return None

        if status == "running":
            started = _parse_dt(row["started_at"])
            elapsed = (_now() - started).total_seconds()
            if elapsed < STALE_THRESHOLD_SECONDS:
                logger.info("Pipeline %s still running (%ds), skipping", run_key, int(elapsed))
                return None
            # Stale lock: UPDATE existing row to reclaim
            logger.warning("Pipeline %s stale (%.0fs), recovering lock", run_key, elapsed)
            client.table("pipeline_runs").update({
                "status": "running",
                "started_at": _now_iso(),
                "finished_at": None,
                "last_error": "stale lock recovered",
            }).eq("run_key", run_key).execute()
            return row["id"]

        if status == "failed":
            # Failed: UPDATE existing row for retry
            logger.info("Pipeline %s previously failed, retrying", run_key)
            client.table("pipeline_runs").update({
                "status": "running",
                "started_at": _now_iso(),
                "finished_at": None,
                "last_error": None,
            }).eq("run_key", run_key).execute()
            return row["id"]

    # No existing record: INSERT new
    result = (
        client.table("pipeline_runs")
        .insert({"run_key": run_key, "status": "running"})
        .execute()
    )
    run_id = result.data[0]["id"]
    logger.info("Pipeline lock acquired: %s (run_id=%s)", run_key, run_id)
    return run_id


async def release_pipeline_lock(
    run_id: str,
    status: str,
    error: Optional[str] = None,
) -> None:
    """Release a pipeline lock by updating its status."""
    client = get_supabase()
    if not client:
        return

    update_data = {
        "status": status,
        "finished_at": _now_iso(),
    }
    if error:
        update_data["last_error"] = error

    client.table("pipeline_runs").update(update_data).eq("id", run_id).execute()
    logger.info("Pipeline lock released: run_id=%s status=%s", run_id, status)


def _save_candidates(
    candidates: list[NewsCandidate],
    ranking: NewsRankingResult,
    batch_id: str,
) -> None:
    """Save ranked candidates to news_candidates table."""
    client = get_supabase()
    if not client:
        return

    # Build a lookup of assigned types from ranking result
    assigned: dict[str, tuple[str, float, str]] = {}  # url → (type, score, reason)
    for pick, ptype in [
        (ranking.research_pick, "research"),
        (ranking.business_main_pick, "business_main"),
    ]:
        if pick:
            assigned[pick.url] = (ptype, pick.relevance_score, pick.ranking_reason)
    if ranking.related_picks:
        for ptype, pick in [
            ("big_tech", ranking.related_picks.big_tech),
            ("industry_biz", ranking.related_picks.industry_biz),
            ("new_tools", ranking.related_picks.new_tools),
        ]:
            if pick:
                assigned[pick.url] = (ptype, pick.relevance_score, pick.ranking_reason)

    rows = []
    for c in candidates:
        info = assigned.get(c.url)
        rows.append({
            "batch_id": batch_id,
            "title": c.title,
            "url": c.url,
            "snippet": c.snippet,
            "source": c.source,
            "assigned_type": info[0] if info else None,
            "relevance_score": info[1] if info else None,
            "ranking_reason": info[2] if info else None,
            "status": "selected" if info else "pending",
        })

    client.table("news_candidates").insert(rows).execute()
    logger.info("Saved %d candidates to news_candidates", len(rows))


def _save_post(client, row: dict, batch_id: str, post_type: str, locale: str) -> str:
    """Insert or update a post. Returns the post id.

    Uses select-then-insert/update because the unique index
    (uq_posts_daily_ai_type) is a partial index with a WHERE clause,
    which supabase-py's upsert(on_conflict=...) cannot handle.
    """
    existing = (
        client.table("news_posts")
        .select("id")
        .eq("pipeline_batch_id", batch_id)
        .eq("post_type", post_type)
        .eq("locale", locale)
        .eq("category", "ai-news")
        .maybe_single()
        .execute()
    )

    if existing and existing.data:
        post_id = existing.data["id"]
        client.table("news_posts").update(row).eq("id", post_id).execute()
        logger.info("%s/%s post updated: id=%s slug=%s", post_type, locale, post_id, row["slug"])
    else:
        result = client.table("news_posts").insert(row).execute()
        post_id = result.data[0]["id"]
        logger.info("%s/%s post inserted: id=%s slug=%s", post_type, locale, post_id, row["slug"])

    return post_id


def _save_research_post(
    post: ResearchPost,
    batch_id: str,
    locale: str = "en",
    translation_group_id: str | None = None,
    source_post_id: str | None = None,
) -> tuple[str, str]:
    """Save research post to posts table.

    Returns (post_id, translation_group_id).
    """
    client = get_supabase()
    if not client:
        return "", ""

    if not translation_group_id:
        translation_group_id = str(uuid.uuid4())

    slug_suffix = "-ko" if locale == "ko" else ""
    row = {
        "title": post.title,
        "slug": f"{post.slug}{slug_suffix}",
        "locale": locale,
        "category": "ai-news",
        "post_type": "research",
        "status": "draft",
        "content_original": post.content_original,
        "no_news_notice": post.no_news_notice,
        "recent_fallback": post.recent_fallback,
        "guide_items": post.guide_items.model_dump() if post.guide_items else None,
        "source_urls": post.source_urls,
        "news_temperature": post.news_temperature,
        "tags": post.tags,
        "excerpt": post.excerpt or None,
        "focus_items": post.focus_items if post.focus_items else None,
        "pipeline_batch_id": batch_id,
        "translation_group_id": translation_group_id,
    }
    if source_post_id:
        row["source_post_id"] = source_post_id

    post_id = _save_post(client, row, batch_id, "research", locale)
    return post_id, translation_group_id


def _save_business_post(
    post: BusinessPost,
    batch_id: str,
    locale: str = "en",
    translation_group_id: str | None = None,
    source_post_id: str | None = None,
) -> tuple[str, str]:
    """Save business post to posts table.

    Returns (post_id, translation_group_id).
    """
    client = get_supabase()
    if not client:
        return "", ""

    if not translation_group_id:
        translation_group_id = str(uuid.uuid4())

    slug_suffix = "-ko" if locale == "ko" else ""
    row = {
        "title": post.title,
        "slug": f"{post.slug}{slug_suffix}",
        "locale": locale,
        "category": "ai-news",
        "post_type": "business",
        "status": "draft",
        "content_beginner": post.content_beginner,
        "content_learner": post.content_learner,
        "content_expert": post.content_expert,
        "guide_items": post.guide_items.model_dump() if post.guide_items else None,
        "related_news": post.related_news.model_dump() if post.related_news else None,
        "source_urls": post.source_urls,
        "news_temperature": post.news_temperature,
        "tags": post.tags,
        "excerpt": post.excerpt or None,
        "focus_items": post.focus_items if post.focus_items else None,
        "pipeline_batch_id": batch_id,
        "translation_group_id": translation_group_id,
    }
    if source_post_id:
        row["source_post_id"] = source_post_id

    post_id = _save_post(client, row, batch_id, "business", locale)
    return post_id, translation_group_id


async def _extract_and_create_terms(
    content_parts: list[str], batch_id: str
) -> None:
    """Extract technical terms from generated posts and create handbook drafts.

    Non-fatal: failures here do NOT break the pipeline.
    """
    from services.agents.advisor import extract_terms_from_content, generate_term_content

    combined = "\n\n---\n\n".join(p for p in content_parts if p)
    if not combined.strip():
        return

    terms, _, _ = await extract_terms_from_content(combined)
    if not terms:
        logger.info("No terms extracted for batch %s", batch_id)
        return

    client = get_supabase()
    if not client:
        return

    created = 0
    max_terms = settings.max_auto_terms_per_run

    for item in terms:
        if created >= max_terms:
            break

        term_name = item.get("term", "").strip()
        if not term_name:
            continue

        # Check if term already exists (ILIKE for case-insensitive)
        try:
            existing = (
                client.table("handbook_terms")
                .select("id")
                .ilike("term", term_name)
                .limit(1)
                .execute()
            )
            if existing.data:
                continue
        except Exception as e:
            logger.warning("DB check failed for term '%s': %s", term_name, e)
            continue

        # Generate content for the new term
        try:
            content, model, tokens = await generate_term_content(
                term_name,
                korean_name=item.get("korean_name", ""),
            )
        except Exception as e:
            logger.warning("Generate failed for term '%s': %s", term_name, e)
            continue

        # Build row from generated content
        slug = term_name.lower().strip().replace(" ", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")

        row = {
            "term": term_name,
            "slug": slug,
            "status": "draft",
            "korean_name": content.get("korean_name", item.get("korean_name", "")),
            "categories": content.get("categories", []),
            "definition_ko": content.get("definition_ko", ""),
            "definition_en": content.get("definition_en", ""),
            "body_basic_ko": content.get("body_basic_ko", ""),
            "body_basic_en": content.get("body_basic_en", ""),
            "body_advanced_ko": content.get("body_advanced_ko", ""),
            "body_advanced_en": content.get("body_advanced_en", ""),
            "source": "pipeline",
        }

        try:
            client.table("handbook_terms").insert(row).execute()
            created += 1
            logger.info("Auto-created handbook draft: '%s' (batch=%s)", term_name, batch_id)
        except Exception as e:
            logger.warning("Insert failed for term '%s': %s", term_name, e)

    logger.info("Pipeline term extraction: %d terms created for batch %s", created, batch_id)


async def run_daily_pipeline(batch_id: str) -> None:
    """Main pipeline orchestrator: collect → rank → generate → save to DB."""
    run_id = await acquire_pipeline_lock(batch_id)
    if not run_id:
        return

    try:
        logger.info("Pipeline %s started (run_id=%s)", batch_id, run_id)

        # Step 1: Collect news from all sources
        candidates = await collect_all_news(batch_id)
        if not candidates:
            logger.warning("No candidates for batch %s, finishing early", batch_id)
            await release_pipeline_lock(run_id, "success")
            return

        # Step 2: Rank candidates
        ranking = await rank_candidates(candidates)
        ranking.research_pick = _apply_research_novelty_gate(ranking.research_pick, batch_id)

        # Step 2b: Save candidates + ranking to DB
        try:
            _save_candidates(candidates, ranking, batch_id)
        except Exception as e:
            logger.error("Failed to save candidates (non-fatal): %s", e)

        # Build context string from candidates for the writing agents
        context = _build_context(candidates)

        # Step 3-A: Generate EN research post
        logger.info("Calling research AI agent for batch %s...", batch_id)
        research_post = await generate_research_post(
            ranking.research_pick, context, batch_id
        )
        logger.info("EN research post generated: %s", research_post.title)
        en_research_id, research_tg_id = _save_research_post(
            research_post, batch_id, locale="en"
        )

        # Step 3-A-KO: Translate research post to Korean
        logger.info("Translating research post to Korean for batch %s...", batch_id)
        ko_research_data = await translate_post(
            research_post.model_dump(), "research"
        )
        ko_research = ResearchPost.model_validate(ko_research_data)
        _save_research_post(
            ko_research, batch_id,
            locale="ko",
            translation_group_id=research_tg_id,
            source_post_id=en_research_id,
        )
        logger.info("KO research post saved (source_post_id=%s)", en_research_id)

        # Step 3-B: Generate EN business post (skip if no business pick)
        logger.info("Starting business post generation for batch %s...", batch_id)
        if ranking.business_main_pick:
            business_post = await generate_business_post(
                ranking.business_main_pick, ranking.related_picks, context, batch_id
            )
            logger.info("EN business post generated: %s", business_post.title)
            en_business_id, business_tg_id = _save_business_post(
                business_post, batch_id, locale="en"
            )

            # Step 3-B-KO: Translate business post to Korean
            logger.info("Translating business post to Korean for batch %s...", batch_id)
            ko_business_data = await translate_post(
                business_post.model_dump(), "business"
            )
            ko_business = BusinessPost.model_validate(ko_business_data)
            _save_business_post(
                ko_business, batch_id,
                locale="ko",
                translation_group_id=business_tg_id,
                source_post_id=en_business_id,
            )
            logger.info("KO business post saved (source_post_id=%s)", en_business_id)
        else:
            logger.warning("No business_main_pick for batch %s, skipping business post", batch_id)

        # Step 4: Extract and create handbook terms from generated content
        try:
            content_parts = [research_post.content_original or ""]
            if ranking.business_main_pick:
                content_parts.extend([
                    business_post.content_beginner or "",
                    business_post.content_learner or "",
                    business_post.content_expert or "",
                ])
            await _extract_and_create_terms(content_parts, batch_id)
        except Exception as e:
            logger.error("Term extraction failed (non-fatal): %s", e)

        logger.info("Pipeline %s completed — EN+KO posts saved to DB", batch_id)
        await release_pipeline_lock(run_id, "success")
    except Exception as e:
        logger.error("Pipeline %s failed: %s", batch_id, e)
        await release_pipeline_lock(run_id, "failed", str(e))
        raise
