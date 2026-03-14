"""Daily News Pipeline — v4 sequential orchestrator.

Flow: Collect → Rank → Research EN → Research KO → Business EN → Business KO
     → Terms → Done.

No artifact system — resume is handled by checking saved EN posts in DB.
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Literal, Optional

from core.config import settings
from core.database import get_supabase
from models.business import BusinessPost
from models.ranking import (
    NewsCandidate,
    NewsRankingResult,
    RankedCandidate,
    RelatedPicks,
)
from models.research import ResearchPost
from services.agents import generate_business_post, generate_research_post, rank_candidates
from services.agents.translate import translate_post
from services.news_collection import collect_all_news
from services.quality import compute_quality

logger = logging.getLogger(__name__)

STALE_THRESHOLD_SECONDS = 3600  # 1 hour
RESEARCH_MIN_RELEVANCE_SCORE = 0.85
RESEARCH_HIGH_SIGNAL_SCORE = 0.95
RESEARCH_TITLE_SIMILARITY_THRESHOLD = 0.88
PIPELINE_MODE_RESUME = "resume"
PIPELINE_MODE_FORCE_REFRESH = "force_refresh"
PipelineMode = Literal["resume", "force_refresh"]


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

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


def _candidate_from_saved_row(row: dict[str, Any]) -> NewsCandidate:
    return NewsCandidate(
        title=row.get("title") or "",
        url=row.get("url") or "",
        snippet=row.get("snippet") or "",
        source=row.get("source") or "unknown",
    )


def _ranked_from_saved_row(row: dict[str, Any]) -> RankedCandidate:
    return RankedCandidate(
        title=row.get("title") or "",
        url=row.get("url") or "",
        snippet=row.get("snippet") or "",
        source=row.get("source") or "unknown",
        assigned_type=row.get("assigned_type") or "unknown",
        relevance_score=float(row.get("relevance_score") or 0.0),
        ranking_reason=row.get("ranking_reason"),
    )


def _ranking_from_saved_candidates(rows: list[dict[str, Any]]) -> NewsRankingResult:
    ranking = NewsRankingResult(related_picks=None)
    related = {}

    for row in rows:
        assigned_type = row.get("assigned_type")
        if not assigned_type:
            continue

        ranked = _ranked_from_saved_row(row)
        if assigned_type == "research":
            ranking.research_pick = ranked
        elif assigned_type == "business_main":
            ranking.business_main_pick = ranked
        elif assigned_type in {"big_tech", "industry_biz", "new_tools"}:
            related[assigned_type] = ranked

    if related:
        ranking.related_picks = RelatedPicks(
            big_tech=related.get("big_tech"),
            industry_biz=related.get("industry_biz"),
            new_tools=related.get("new_tools"),
        )

    return ranking


def normalize_pipeline_error(error: str | Exception | None) -> str:
    raw = str(error or "").strip()
    if not raw:
        return ""

    content_too_short_match = re.search(
        r"Content too short:\s*(\d+)\s*chars\s*\(min\s*(\d+)\)",
        raw,
        flags=re.IGNORECASE,
    )
    if content_too_short_match:
        actual, minimum = content_too_short_match.groups()
        if "BusinessPost" in raw:
            field_match = re.search(
                r"BusinessPost\s*\n([a-z_]+)\s*\n",
                raw,
                flags=re.IGNORECASE,
            )
            field_name = field_match.group(1) if field_match else None
            if field_name == "content_analysis":
                return f"Business analysis too short: {actual} / {minimum} chars."
            if field_name and field_name.startswith("content_"):
                persona = field_name.removeprefix("content_").replace("_", " ")
                return f"Business {persona} persona too short: {actual} / {minimum} chars."
            return f"Business post too short: {actual} / {minimum} chars."
        return f"Research post too short: {actual} / {minimum} chars."

    return raw.splitlines()[0]


# ---------------------------------------------------------------------------
# Novelty gate (research deduplication)
# ---------------------------------------------------------------------------

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


def _get_research_gate_decision(
    candidate: RankedCandidate,
    latest_post: dict | None,
) -> dict[str, Any]:
    score = candidate.relevance_score or 0.0
    latest_url = ((latest_post or {}).get("url") or "").rstrip("/")
    candidate_url = (candidate.url or "").rstrip("/")
    title_similarity = _title_similarity(candidate.title, (latest_post or {}).get("title", ""))

    if score < RESEARCH_MIN_RELEVANCE_SCORE:
        return {
            "skip": True,
            "reason": "low_relevance",
            "relevance_score": score,
            "title_similarity": title_similarity,
            "latest_url": latest_url,
            "candidate_url": candidate_url,
        }

    if latest_url and candidate_url and latest_url == candidate_url:
        return {
            "skip": True,
            "reason": "same_url",
            "relevance_score": score,
            "title_similarity": title_similarity,
            "latest_url": latest_url,
            "candidate_url": candidate_url,
        }

    very_high_signal_override = (
        latest_url != candidate_url and score >= RESEARCH_HIGH_SIGNAL_SCORE
    )
    if title_similarity >= RESEARCH_TITLE_SIMILARITY_THRESHOLD and not very_high_signal_override:
        return {
            "skip": True,
            "reason": "similar_title",
            "relevance_score": score,
            "title_similarity": title_similarity,
            "latest_url": latest_url,
            "candidate_url": candidate_url,
        }

    return {
        "skip": False,
        "reason": "pass",
        "relevance_score": score,
        "title_similarity": title_similarity,
        "latest_url": latest_url,
        "candidate_url": candidate_url,
    }


def _should_skip_research_candidate(
    candidate: RankedCandidate,
    latest_post: dict | None,
) -> bool:
    return _get_research_gate_decision(candidate, latest_post)["skip"]


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
) -> tuple[RankedCandidate | None, dict[str, Any]]:
    if not candidate:
        return None, {"skip": True, "reason": "missing_candidate"}

    latest_post = _get_latest_research_post(exclude_batch_id=batch_id)
    decision = _get_research_gate_decision(candidate, latest_post)
    if decision["skip"]:
        logger.info(
            "Research pick gated out for batch %s: score=%.2f title=%s latest=%s",
            batch_id,
            candidate.relevance_score,
            candidate.title[:120],
            (latest_post or {}).get("title", "-")[:120],
        )
        return None, decision

    return candidate, decision


# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------

def log_pipeline_stage(
    run_id: str,
    pipeline_type: str,
    status: str,
    *,
    attempt: int = 0,
    post_type: str | None = None,
    locale: str | None = None,
    input_summary: str | None = None,
    output_summary: str | None = None,
    error_message: str | None = None,
    duration_ms: int | None = None,
    model_used: str | None = None,
    tokens_used: int | None = None,
    cost_usd: float | None = None,
    debug_meta: dict[str, Any] | None = None,
) -> None:
    client = get_supabase()
    if not client:
        return

    client.table("pipeline_logs").insert(
        {
            "run_id": run_id,
            "pipeline_type": pipeline_type,
            "status": status,
            "attempt": attempt,
            "post_type": post_type,
            "locale": locale,
            "input_summary": input_summary,
            "output_summary": output_summary,
            "error_message": error_message,
            "duration_ms": duration_ms,
            "model_used": model_used,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
            "debug_meta": debug_meta or {},
        }
    ).execute()


# ---------------------------------------------------------------------------
# Pipeline lock (distributed)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Candidate persistence
# ---------------------------------------------------------------------------

def _save_candidates(
    candidates: list[NewsCandidate],
    ranking: NewsRankingResult,
    batch_id: str,
) -> None:
    """Save ranked candidates to news_candidates table."""
    client = get_supabase()
    if not client:
        return

    try:
        client.table("news_candidates").delete().eq("batch_id", batch_id).execute()
    except Exception as exc:
        logger.warning("Failed to clear existing candidate snapshot for %s: %s", batch_id, exc)

    assigned: dict[str, tuple[str, float, str]] = {}
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


def _load_saved_ranking_snapshot(
    batch_id: str,
) -> tuple[list[NewsCandidate], NewsRankingResult] | None:
    client = get_supabase()
    if not client:
        return None

    try:
        result = (
            client.table("news_candidates")
            .select("title,url,snippet,source,assigned_type,relevance_score,ranking_reason")
            .eq("batch_id", batch_id)
            .execute()
        )
        rows = result.data if result and result.data else []
    except Exception as exc:
        logger.warning("Failed to load saved candidate snapshot for %s: %s", batch_id, exc)
        return None

    if not rows:
        return None

    if not any(row.get("assigned_type") for row in rows):
        return None

    candidates = [_candidate_from_saved_row(row) for row in rows]
    ranking = _ranking_from_saved_candidates(rows)
    return candidates, ranking


# ---------------------------------------------------------------------------
# Post DB layer
# ---------------------------------------------------------------------------

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
    """Save research post. Returns (post_id, translation_group_id)."""
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
        "source_cards": [card.model_dump() for card in post.source_cards] if post.source_cards else None,
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
    """Save business post. Returns (post_id, translation_group_id)."""
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
        "content_analysis": post.content_analysis,
        "content_beginner": post.content_beginner,
        "content_learner": post.content_learner,
        "content_expert": post.content_expert,
        "fact_pack": post.fact_pack if post.fact_pack else None,
        "source_cards": post.source_cards if post.source_cards else None,
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


# ---------------------------------------------------------------------------
# Resume helpers (saved EN post reuse)
# ---------------------------------------------------------------------------

def _get_saved_post_row(
    batch_id: str,
    post_type: str,
    locale: str,
) -> dict[str, Any] | None:
    client = get_supabase()
    if not client:
        return None

    try:
        result = (
            client.table("news_posts")
            .select("*")
            .eq("pipeline_batch_id", batch_id)
            .eq("post_type", post_type)
            .eq("locale", locale)
            .eq("category", "ai-news")
            .maybe_single()
            .execute()
        )
        return result.data if result and result.data else None
    except Exception as exc:
        logger.warning(
            "Failed to load saved %s/%s post for batch %s: %s",
            post_type, locale, batch_id, exc,
        )
        return None


def _load_saved_translation_source(
    batch_id: str,
    post_type: str,
) -> dict[str, Any] | None:
    """Return saved EN row only if KO doesn't exist yet (= needs translation)."""
    en_row = _get_saved_post_row(batch_id, post_type, "en")
    ko_row = _get_saved_post_row(batch_id, post_type, "ko")
    if en_row and not ko_row:
        return en_row
    return None


def _hydrate_research_post(row: dict[str, Any]) -> ResearchPost:
    return ResearchPost.model_validate(
        {
            "has_news": bool(row.get("content_original")),
            "title": row.get("title") or "",
            "slug": row.get("slug") or "",
            "content_original": row.get("content_original"),
            "no_news_notice": row.get("no_news_notice"),
            "recent_fallback": row.get("recent_fallback"),
            "guide_items": row.get("guide_items"),
            "source_urls": row.get("source_urls") or [],
            "news_temperature": row.get("news_temperature") or 3,
            "tags": row.get("tags") or [],
            "excerpt": row.get("excerpt") or "",
            "focus_items": row.get("focus_items") or [],
            "source_cards": row.get("source_cards") or [],
        }
    )


def _hydrate_business_post(row: dict[str, Any]) -> BusinessPost:
    return BusinessPost.model_validate(
        {
            "title": row.get("title") or "",
            "slug": row.get("slug") or "",
            "content_analysis": row.get("content_analysis") or "",
            "content_beginner": row.get("content_beginner") or "",
            "content_learner": row.get("content_learner") or "",
            "content_expert": row.get("content_expert") or "",
            "fact_pack": row.get("fact_pack") or {},
            "source_cards": row.get("source_cards") or [],
            "guide_items": row.get("guide_items"),
            "related_news": row.get("related_news"),
            "source_urls": row.get("source_urls") or [],
            "news_temperature": row.get("news_temperature") or 3,
            "tags": row.get("tags") or [],
            "excerpt": row.get("excerpt") or "",
            "focus_items": row.get("focus_items") or [],
        }
    )


# ---------------------------------------------------------------------------
# Handbook term extraction (non-fatal)
# ---------------------------------------------------------------------------

async def _extract_and_create_terms(
    content_parts: list[str], batch_id: str
) -> None:
    """Extract technical terms from generated posts and create handbook drafts."""
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

        try:
            content, model, tokens = await generate_term_content(
                term_name,
                korean_name=item.get("korean_name", ""),
            )
        except Exception as e:
            logger.warning("Generate failed for term '%s': %s", term_name, e)
            continue

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


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def run_daily_pipeline(batch_id: str, mode: PipelineMode = PIPELINE_MODE_RESUME) -> None:
    """Main pipeline orchestrator: collect → rank → generate → translate → save."""
    if mode not in {PIPELINE_MODE_RESUME, PIPELINE_MODE_FORCE_REFRESH}:
        mode = PIPELINE_MODE_RESUME

    run_id = await acquire_pipeline_lock(batch_id)
    if not run_id:
        return

    try:
        logger.info("Pipeline %s started (run_id=%s)", batch_id, run_id)
        log_pipeline_stage(
            run_id,
            "pipeline",
            "started",
            input_summary=f"daily:{batch_id}",
            debug_meta={"batch_id": batch_id, "mode": mode},
        )

        # ---------------------------------------------------------------
        # Step 1: Collect news (or reuse saved snapshot)
        # ---------------------------------------------------------------
        saved_snapshot = (
            _load_saved_ranking_snapshot(batch_id)
            if mode == PIPELINE_MODE_RESUME
            else None
        )
        reused_snapshot = saved_snapshot is not None

        collect_started = _now()
        if saved_snapshot:
            candidates, ranking = saved_snapshot
        else:
            candidates = await collect_all_news(batch_id)
        log_pipeline_stage(
            run_id,
            "collect",
            "success",
            duration_ms=int((_now() - collect_started).total_seconds() * 1000),
            output_summary=(
                f"Reused {len(candidates)} saved candidates"
                if reused_snapshot
                else f"Collected {len(candidates)} candidates"
            ),
            debug_meta={
                "candidate_count": len(candidates),
                "reused_candidates": reused_snapshot,
            },
        )
        if not candidates:
            logger.warning("No candidates for batch %s, finishing early", batch_id)
            await release_pipeline_lock(run_id, "success")
            return

        # ---------------------------------------------------------------
        # Step 2: Rank candidates
        # ---------------------------------------------------------------
        rank_started = _now()
        rank_usage: dict[str, Any] = {}
        if not reused_snapshot:
            try:
                ranking = await rank_candidates(candidates, usage_recorder=rank_usage)
            except Exception:
                log_pipeline_stage(
                    run_id, "rank", "failed",
                    duration_ms=int((_now() - rank_started).total_seconds() * 1000),
                    output_summary="Ranking failed",
                    model_used=rank_usage.get("model_used"),
                    tokens_used=rank_usage.get("tokens_used"),
                    cost_usd=rank_usage.get("cost_usd"),
                )
                raise

        ranking.research_pick, research_gate = _apply_research_novelty_gate(
            ranking.research_pick, batch_id
        )
        log_pipeline_stage(
            run_id, "rank", "success",
            duration_ms=int((_now() - rank_started).total_seconds() * 1000),
            output_summary="Reused saved ranking" if reused_snapshot else "Ranking completed",
            model_used=rank_usage.get("model_used"),
            tokens_used=rank_usage.get("tokens_used"),
            cost_usd=rank_usage.get("cost_usd"),
            debug_meta={
                "research_pick": ranking.research_pick.title if ranking.research_pick else None,
                "business_pick": ranking.business_main_pick.title if ranking.business_main_pick else None,
                "reused_ranking": reused_snapshot,
            },
        )
        log_pipeline_stage(
            run_id,
            "research.novelty_gate",
            "no_news" if research_gate.get("skip") else "success",
            post_type="research",
            locale="en",
            output_summary=research_gate.get("reason"),
            debug_meta=research_gate,
        )

        # Save candidates
        if not reused_snapshot:
            try:
                _save_candidates(candidates, ranking, batch_id)
            except Exception as e:
                logger.error("Failed to save candidates (non-fatal): %s", e)

        context = _build_context(candidates)

        # ---------------------------------------------------------------
        # Step 3-A: Research EN
        # ---------------------------------------------------------------
        logger.info("Research EN generation for batch %s...", batch_id)
        research_started = _now()
        research_usage: dict[str, Any] = {}

        saved_research_en_row = (
            _load_saved_translation_source(batch_id, "research")
            if mode == PIPELINE_MODE_RESUME
            else None
        )

        if saved_research_en_row:
            research_post = _hydrate_research_post(saved_research_en_row)
            en_research_id = saved_research_en_row["id"]
            research_tg_id = saved_research_en_row.get("translation_group_id") or str(uuid.uuid4())
            logger.info("Reusing saved EN research post: %s", en_research_id)
        else:
            try:
                research_post = await generate_research_post(
                    ranking.research_pick,
                    context,
                    batch_id,
                    usage_recorder=research_usage,
                )
            except Exception:
                log_pipeline_stage(
                    run_id, "research.generate.en", "failed",
                    post_type="research", locale="en",
                    duration_ms=int((_now() - research_started).total_seconds() * 1000),
                    output_summary="Research EN draft failed",
                    model_used=research_usage.get("model_used"),
                    tokens_used=research_usage.get("tokens_used"),
                    cost_usd=research_usage.get("cost_usd"),
                )
                raise

            en_research_id, research_tg_id = _save_research_post(
                research_post, batch_id, locale="en"
            )
            log_pipeline_stage(
                run_id, "save.research.en", "success",
                post_type="research", locale="en",
                output_summary=en_research_id,
            )

        log_pipeline_stage(
            run_id, "research.generate.en",
            "no_news" if not research_post.has_news else "success",
            post_type="research", locale="en",
            duration_ms=int((_now() - research_started).total_seconds() * 1000),
            output_summary=research_post.title,
            model_used=research_usage.get("model_used"),
            tokens_used=research_usage.get("tokens_used"),
            cost_usd=research_usage.get("cost_usd"),
            debug_meta={
                "research_en_len": len(research_post.content_original or ""),
                "has_news": research_post.has_news,
                "resumed_from_saved_en": saved_research_en_row is not None,
                "input_tokens": research_usage.get("input_tokens"),
                "output_tokens": research_usage.get("output_tokens"),
                "attempts": research_usage.get("attempts", 1),
            },
        )
        logger.info("EN research post ready: %s", research_post.title)

        # ---------------------------------------------------------------
        # Step 3-A-KO: Research translation
        # ---------------------------------------------------------------
        logger.info("Translating research post to Korean for batch %s...", batch_id)
        research_tr_started = _now()

        try:
            ko_research_data, research_tr_usage = await translate_post(
                research_post.model_dump(), "research",
            )
            ko_research = ResearchPost.model_validate(ko_research_data)
        except Exception:
            log_pipeline_stage(
                run_id, "research.translate.ko", "failed",
                post_type="research", locale="ko",
                duration_ms=int((_now() - research_tr_started).total_seconds() * 1000),
                output_summary="Research KO translation failed",
            )
            raise

        log_pipeline_stage(
            run_id, "research.translate.ko",
            "no_news" if not ko_research.has_news else "success",
            post_type="research", locale="ko",
            duration_ms=int((_now() - research_tr_started).total_seconds() * 1000),
            output_summary=ko_research.title,
            model_used=research_tr_usage.get("model_used"),
            tokens_used=research_tr_usage.get("tokens_used"),
            cost_usd=research_tr_usage.get("cost_usd"),
            debug_meta={
                "research_ko_len": len(ko_research.content_original or ""),
                "has_news": ko_research.has_news,
                "resumed_from_saved_en": saved_research_en_row is not None,
                "input_tokens": research_tr_usage.get("input_tokens"),
                "output_tokens": research_tr_usage.get("output_tokens"),
                "attempts": research_tr_usage.get("attempts", 1),
            },
        )
        ko_research_id, _ = _save_research_post(
            ko_research, batch_id,
            locale="ko",
            translation_group_id=research_tg_id,
            source_post_id=en_research_id,
        )
        log_pipeline_stage(
            run_id, "save.research.ko", "success",
            post_type="research", locale="ko",
            output_summary=ko_research_id,
        )
        research_quality_score, research_quality_flags = compute_quality(ko_research.model_dump())
        log_pipeline_stage(
            run_id, "quality.research", "success",
            post_type="research", locale="ko",
            debug_meta={
                "quality_score": research_quality_score,
                "quality_flags": research_quality_flags,
            },
        )
        logger.info("KO research post saved (source_post_id=%s)", en_research_id)

        # ---------------------------------------------------------------
        # Step 3-B: Business EN (Expert-First 2-Call Cascade)
        # ---------------------------------------------------------------
        logger.info("Starting business post generation for batch %s...", batch_id)
        if ranking.business_main_pick:
            business_started = _now()

            saved_business_en_row = (
                _load_saved_translation_source(batch_id, "business")
                if mode == PIPELINE_MODE_RESUME
                else None
            )

            if saved_business_en_row:
                business_post = _hydrate_business_post(saved_business_en_row)
                en_business_id = saved_business_en_row["id"]
                business_tg_id = saved_business_en_row.get("translation_group_id") or str(uuid.uuid4())
                business_usage = {}
                expert_usage = {}
                derive_usage = {}
                logger.info("Reusing saved EN business post: %s", en_business_id)
            else:
                try:
                    business_post, business_usage, expert_usage, derive_usage = await generate_business_post(
                        ranking.business_main_pick,
                        ranking.related_picks,
                        context,
                        batch_id,
                    )
                except Exception:
                    log_pipeline_stage(
                        run_id, "business.generate.en", "failed",
                        post_type="business", locale="en",
                        duration_ms=int((_now() - business_started).total_seconds() * 1000),
                        output_summary="Business EN draft failed",
                    )
                    raise

                en_business_id, business_tg_id = _save_business_post(
                    business_post, batch_id, locale="en"
                )
                log_pipeline_stage(
                    run_id, "save.business.en", "success",
                    post_type="business", locale="en",
                    output_summary=en_business_id,
                    model_used=business_usage.get("model_used"),
                    tokens_used=business_usage.get("tokens_used"),
                    cost_usd=business_usage.get("cost_usd"),
                )

            log_pipeline_stage(
                run_id, "business.generate.en", "success",
                post_type="business", locale="en",
                duration_ms=int((_now() - business_started).total_seconds() * 1000),
                output_summary=business_post.title,
                debug_meta={
                    "business_analysis_len": len(business_post.content_analysis or ""),
                    "persona_lengths": {
                        "beginner": len(business_post.content_beginner or ""),
                        "learner": len(business_post.content_learner or ""),
                        "expert": len(business_post.content_expert or ""),
                    },
                    "fact_pack_keys": list((business_post.fact_pack or {}).keys()),
                    "source_card_count": len(business_post.source_cards or []),
                    "resumed_from_saved_en": saved_business_en_row is not None,
                    "input_tokens": business_usage.get("input_tokens"),
                    "output_tokens": business_usage.get("output_tokens"),
                    "expert_call_tokens": {
                        "input": expert_usage.get("input_tokens"),
                        "output": expert_usage.get("output_tokens"),
                    },
                    "derive_call_tokens": {
                        "input": derive_usage.get("input_tokens"),
                        "output": derive_usage.get("output_tokens"),
                    },
                    "attempts": {
                        "expert": expert_usage.get("attempts", 1),
                        "derive": derive_usage.get("attempts", 1),
                    },
                },
            )
            logger.info("EN business post ready: %s", business_post.title)

            # -----------------------------------------------------------
            # Step 3-B-KO: Business translation
            # -----------------------------------------------------------
            logger.info("Translating business post to Korean for batch %s...", batch_id)
            business_tr_started = _now()

            try:
                ko_business_data, business_tr_usage = await translate_post(
                    business_post.model_dump(), "business",
                )
                ko_business = BusinessPost.model_validate(ko_business_data)
            except Exception:
                log_pipeline_stage(
                    run_id, "business.translate.ko", "failed",
                    post_type="business", locale="ko",
                    duration_ms=int((_now() - business_tr_started).total_seconds() * 1000),
                    output_summary="Business KO translation failed",
                )
                raise

            log_pipeline_stage(
                run_id, "business.translate.ko", "success",
                post_type="business", locale="ko",
                duration_ms=int((_now() - business_tr_started).total_seconds() * 1000),
                output_summary=ko_business.title,
                model_used=business_tr_usage.get("model_used"),
                tokens_used=business_tr_usage.get("tokens_used"),
                cost_usd=business_tr_usage.get("cost_usd"),
                debug_meta={
                    "business_analysis_len": len(ko_business.content_analysis or ""),
                    "persona_lengths": {
                        "beginner": len(ko_business.content_beginner or ""),
                        "learner": len(ko_business.content_learner or ""),
                        "expert": len(ko_business.content_expert or ""),
                    },
                    "input_tokens": business_tr_usage.get("input_tokens"),
                    "output_tokens": business_tr_usage.get("output_tokens"),
                    "attempts": business_tr_usage.get("attempts", 1),
                },
            )
            ko_business_id, _ = _save_business_post(
                ko_business, batch_id,
                locale="ko",
                translation_group_id=business_tg_id,
                source_post_id=en_business_id,
            )
            log_pipeline_stage(
                run_id, "save.business.ko", "success",
                post_type="business", locale="ko",
                output_summary=ko_business_id,
            )
            business_quality_score, business_quality_flags = compute_quality(ko_business.model_dump())
            log_pipeline_stage(
                run_id, "quality.business", "success",
                post_type="business", locale="ko",
                debug_meta={
                    "quality_score": business_quality_score,
                    "quality_flags": business_quality_flags,
                },
            )
            logger.info("KO business post saved (source_post_id=%s)", en_business_id)
        else:
            logger.warning("No business_main_pick for batch %s, skipping business post", batch_id)

        # ---------------------------------------------------------------
        # Step 4: Handbook term extraction (non-fatal)
        # ---------------------------------------------------------------
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
        raw_error = str(e)
        log_pipeline_stage(
            run_id,
            "pipeline",
            "failed",
            error_message=raw_error,
            debug_meta={"raw_error": raw_error},
        )
        await release_pipeline_lock(run_id, "failed", normalize_pipeline_error(raw_error))
        raise
