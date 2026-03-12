import logging
import re
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Optional

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


def _build_stage_logger(
    run_id: str,
    *,
    post_type: str,
    locale: str,
) -> Any:
    def _logger(
        stage_name: str,
        status: str,
        attempt: int,
        debug_meta: dict[str, Any] | None,
        output_summary: str | None,
        model_used: str | None = None,
        tokens_used: int | None = None,
        cost_usd: float | None = None,
    ) -> None:
        log_pipeline_stage(
            run_id,
            stage_name,
            status,
            attempt=attempt,
            post_type=post_type,
            locale=locale,
            output_summary=output_summary,
            debug_meta=debug_meta,
            model_used=model_used,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
        )

    return _logger


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
        "content_analysis": post.content_analysis,
        "content_beginner": post.content_beginner,
        "content_learner": post.content_learner,
        "content_expert": post.content_expert,
        "fact_pack": [item.model_dump() for item in post.fact_pack] if post.fact_pack else None,
        "source_cards": [card.model_dump() for card in post.source_cards] if post.source_cards else None,
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
            post_type,
            locale,
            batch_id,
            exc,
        )
        return None


def _load_saved_translation_source(
    batch_id: str,
    post_type: str,
) -> dict[str, Any] | None:
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
            "fact_pack": row.get("fact_pack") or [],
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


def _artifact_payload_from_state(partial_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate": partial_state.get("candidate") or {},
        "fact_pack": partial_state.get("fact_pack") or [],
        "source_cards": partial_state.get("source_cards") or [],
        "analysis_data": partial_state.get("analysis_data") or {},
        "persona_payloads": partial_state.get("persona_payloads") or {},
    }


def _partial_state_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    payload = artifact.get("payload") or {}
    return {
        "candidate": payload.get("candidate") or {
            "title": artifact.get("candidate_title"),
            "url": artifact.get("candidate_url"),
            "batch_id": artifact.get("batch_id"),
        },
        "fact_pack": payload.get("fact_pack") or [],
        "source_cards": payload.get("source_cards") or [],
        "analysis_data": payload.get("analysis_data") or {},
        "persona_payloads": payload.get("persona_payloads") or {},
        "completed_stages": artifact.get("completed_stages") or [],
    }


def _create_pipeline_artifact(
    *,
    run_id: str,
    run_key: str,
    batch_id: str,
    post_type: str,
    locale: str,
    candidate_title: str,
    candidate_url: str,
    status: str,
    completed_stages: list[str],
    failed_stage: str | None,
    last_validation_error: str | None,
    payload: dict[str, Any],
    resumed_from_artifact_id: str | None = None,
) -> dict[str, Any] | None:
    client = get_supabase()
    if not client:
        return None

    result = (
        client.table("pipeline_artifacts")
        .insert(
            {
                "run_id": run_id,
                "run_key": run_key,
                "batch_id": batch_id,
                "post_type": post_type,
                "locale": locale,
                "candidate_title": candidate_title,
                "candidate_url": candidate_url,
                "status": status,
                "completed_stages": completed_stages,
                "failed_stage": failed_stage,
                "last_validation_error": last_validation_error,
                "payload": payload,
                "resumed_from_artifact_id": resumed_from_artifact_id,
                "updated_at": _now_iso(),
            }
        )
        .execute()
    )
    return result.data[0] if result and result.data else None


def _update_pipeline_artifact(
    artifact_id: str,
    *,
    status: str,
    completed_stages: list[str],
    failed_stage: str | None,
    last_validation_error: str | None,
    payload: dict[str, Any],
) -> None:
    client = get_supabase()
    if not client:
        return

    (
        client.table("pipeline_artifacts")
        .update(
            {
                "status": status,
                "completed_stages": completed_stages,
                "failed_stage": failed_stage,
                "last_validation_error": last_validation_error,
                "payload": payload,
                "updated_at": _now_iso(),
            }
        )
        .eq("id", artifact_id)
        .execute()
    )


def _set_pipeline_artifact_status(artifact_id: str, status: str) -> None:
    client = get_supabase()
    if not client:
        return
    (
        client.table("pipeline_artifacts")
        .update({"status": status, "updated_at": _now_iso()})
        .eq("id", artifact_id)
        .execute()
    )


def _find_latest_partial_artifact(
    batch_id: str,
    post_type: str,
    locale: str,
    candidate_url: str,
) -> dict[str, Any] | None:
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("pipeline_artifacts")
            .select("*")
            .eq("batch_id", batch_id)
            .eq("post_type", post_type)
            .eq("locale", locale)
            .eq("candidate_url", candidate_url)
            .eq("status", "partial")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        data = result.data if result else None
        if isinstance(data, list) and data:
            return data[0]
    except Exception as exc:
        logger.warning("Failed to load partial artifact for %s %s: %s", post_type, candidate_url, exc)
    return None


def _prepare_business_artifact_resume(
    run_id: str,
    run_key: str,
    batch_id: str,
    candidate: RankedCandidate,
) -> tuple[str | None, dict[str, Any] | None]:
    existing = _find_latest_partial_artifact(
        batch_id=batch_id,
        post_type="business",
        locale="en",
        candidate_url=candidate.url,
    )
    if not existing:
        return None, None

    partial_state = _partial_state_from_artifact(existing)
    _set_pipeline_artifact_status(existing["id"], "superseded")
    created = _create_pipeline_artifact(
        run_id=run_id,
        run_key=run_key,
        batch_id=batch_id,
        post_type="business",
        locale="en",
        candidate_title=candidate.title,
        candidate_url=candidate.url,
        status="partial",
        completed_stages=partial_state.get("completed_stages") or [],
        failed_stage=existing.get("failed_stage"),
        last_validation_error=existing.get("last_validation_error"),
        payload=_artifact_payload_from_state(partial_state),
        resumed_from_artifact_id=existing["id"],
    )
    return (created or {}).get("id"), partial_state


def _build_business_artifact_recorder(
    run_id: str,
    run_key: str,
    batch_id: str,
    candidate: RankedCandidate,
    initial_artifact_id: str | None = None,
) -> tuple[Any, dict[str, str | None]]:
    artifact_ref: dict[str, str | None] = {"artifact_id": initial_artifact_id}

    def _recorder(
        partial_state: dict[str, Any],
        status: str,
        failed_stage: str | None,
        last_validation_error: str | None,
    ) -> None:
        if artifact_ref["artifact_id"] is None:
            created = _create_pipeline_artifact(
                run_id=run_id,
                run_key=run_key,
                batch_id=batch_id,
                post_type="business",
                locale="en",
                candidate_title=candidate.title,
                candidate_url=candidate.url,
                status=status,
                completed_stages=partial_state.get("completed_stages") or [],
                failed_stage=failed_stage,
                last_validation_error=last_validation_error,
                payload=_artifact_payload_from_state(partial_state),
            )
            artifact_ref["artifact_id"] = (created or {}).get("id")
            return

        _update_pipeline_artifact(
            artifact_ref["artifact_id"],
            status=status,
            completed_stages=partial_state.get("completed_stages") or [],
            failed_stage=failed_stage,
            last_validation_error=last_validation_error,
            payload=_artifact_payload_from_state(partial_state),
        )

    return _recorder, artifact_ref


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
        log_pipeline_stage(
            run_id,
            "pipeline",
            "started",
            input_summary=f"daily:{batch_id}",
            debug_meta={"batch_id": batch_id},
        )

        # Step 1: Collect news from all sources
        collect_started = _now()
        candidates = await collect_all_news(batch_id)
        log_pipeline_stage(
            run_id,
            "collect",
            "success",
            duration_ms=int((_now() - collect_started).total_seconds() * 1000),
            output_summary=f"Collected {len(candidates)} candidates",
            debug_meta={"candidate_count": len(candidates)},
        )
        if not candidates:
            logger.warning("No candidates for batch %s, finishing early", batch_id)
            await release_pipeline_lock(run_id, "success")
            return

        # Step 2: Rank candidates
        rank_started = _now()
        rank_usage: dict[str, Any] = {}
        try:
            ranking = await rank_candidates(candidates, usage_recorder=rank_usage)
        except Exception:
            log_pipeline_stage(
                run_id,
                "rank",
                "failed",
                duration_ms=int((_now() - rank_started).total_seconds() * 1000),
                output_summary="Ranking failed",
                model_used=rank_usage.get("model_used"),
                tokens_used=rank_usage.get("tokens_used"),
                cost_usd=rank_usage.get("cost_usd"),
                debug_meta={
                    "input_tokens": rank_usage.get("input_tokens"),
                    "output_tokens": rank_usage.get("output_tokens"),
                },
            )
            raise
        ranking.research_pick, research_gate = _apply_research_novelty_gate(
            ranking.research_pick, batch_id
        )
        log_pipeline_stage(
            run_id,
            "rank",
            "success",
            duration_ms=int((_now() - rank_started).total_seconds() * 1000),
            output_summary="Ranking completed",
            model_used=rank_usage.get("model_used"),
            tokens_used=rank_usage.get("tokens_used"),
            cost_usd=rank_usage.get("cost_usd"),
            debug_meta={
                "research_pick": ranking.research_pick.title if ranking.research_pick else None,
                "business_pick": ranking.business_main_pick.title if ranking.business_main_pick else None,
                "input_tokens": rank_usage.get("input_tokens"),
                "output_tokens": rank_usage.get("output_tokens"),
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

        # Step 2b: Save candidates + ranking to DB
        try:
            _save_candidates(candidates, ranking, batch_id)
        except Exception as e:
            logger.error("Failed to save candidates (non-fatal): %s", e)

        # Build context string from candidates for the writing agents
        context = _build_context(candidates)

        # Step 3-A: Generate EN research post
        logger.info("Calling research AI agent for batch %s...", batch_id)
        research_started = _now()
        research_usage: dict[str, Any] = {}
        saved_research_en_row = _load_saved_translation_source(batch_id, "research")
        if saved_research_en_row:
            research_post = _hydrate_research_post(saved_research_en_row)
            en_research_id = saved_research_en_row["id"]
            research_tg_id = saved_research_en_row.get("translation_group_id") or str(uuid.uuid4())
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
                    run_id,
                    "research.generate.en",
                    "failed",
                    post_type="research",
                    locale="en",
                    duration_ms=int((_now() - research_started).total_seconds() * 1000),
                    output_summary="Research EN draft failed",
                    model_used=research_usage.get("model_used"),
                    tokens_used=research_usage.get("tokens_used"),
                    cost_usd=research_usage.get("cost_usd"),
                    debug_meta={
                        "research_en_len": None,
                        "has_news": ranking.research_pick is not None,
                        "input_tokens": research_usage.get("input_tokens"),
                        "output_tokens": research_usage.get("output_tokens"),
                    },
                )
                raise
        log_pipeline_stage(
            run_id,
            "research.generate.en",
            "no_news" if not research_post.has_news else "success",
            post_type="research",
            locale="en",
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
            },
        )
        logger.info("EN research post generated: %s", research_post.title)
        if not saved_research_en_row:
            en_research_id, research_tg_id = _save_research_post(
                research_post, batch_id, locale="en"
            )
            log_pipeline_stage(
                run_id,
                "save.research.en",
                "success",
                post_type="research",
                locale="en",
                output_summary=en_research_id,
            )

        # Step 3-A-KO: Translate research post to Korean
        logger.info("Translating research post to Korean for batch %s...", batch_id)
        research_translate_started = _now()
        research_translate_usage: dict[str, Any] = {}
        try:
            ko_research_data = await translate_post(
                research_post.model_dump(),
                "research",
                usage_recorder=research_translate_usage,
            )
            ko_research = ResearchPost.model_validate(ko_research_data)
        except Exception:
            log_pipeline_stage(
                run_id,
                "research.translate.ko",
                "failed",
                post_type="research",
                locale="ko",
                duration_ms=int((_now() - research_translate_started).total_seconds() * 1000),
                output_summary="Research KO translation failed",
                model_used=research_translate_usage.get("model_used"),
                tokens_used=research_translate_usage.get("tokens_used"),
                cost_usd=research_translate_usage.get("cost_usd"),
                debug_meta={
                    "research_ko_len": None,
                    "has_news": research_post.has_news,
                    "input_tokens": research_translate_usage.get("input_tokens"),
                    "output_tokens": research_translate_usage.get("output_tokens"),
                },
            )
            raise
        log_pipeline_stage(
            run_id,
            "research.translate.ko",
            "no_news" if not ko_research.has_news else "success",
            post_type="research",
            locale="ko",
            duration_ms=int((_now() - research_translate_started).total_seconds() * 1000),
            output_summary=ko_research.title,
            model_used=research_translate_usage.get("model_used"),
            tokens_used=research_translate_usage.get("tokens_used"),
            cost_usd=research_translate_usage.get("cost_usd"),
            debug_meta={
                "research_ko_len": len(ko_research.content_original or ""),
                "has_news": ko_research.has_news,
                "input_tokens": research_translate_usage.get("input_tokens"),
                "output_tokens": research_translate_usage.get("output_tokens"),
            },
        )
        ko_research_id, _ = _save_research_post(
            ko_research, batch_id,
            locale="ko",
            translation_group_id=research_tg_id,
            source_post_id=en_research_id,
        )
        log_pipeline_stage(
            run_id,
            "save.research.ko",
            "success",
            post_type="research",
            locale="ko",
            output_summary=ko_research_id,
        )
        logger.info("KO research post saved (source_post_id=%s)", en_research_id)

        # Step 3-B: Generate EN business post (skip if no business pick)
        logger.info("Starting business post generation for batch %s...", batch_id)
        if ranking.business_main_pick:
            business_started = _now()
            saved_business_en_row = _load_saved_translation_source(batch_id, "business")
            artifact_id = None
            if saved_business_en_row:
                business_post = _hydrate_business_post(saved_business_en_row)
                en_business_id = saved_business_en_row["id"]
                business_tg_id = saved_business_en_row.get("translation_group_id") or str(uuid.uuid4())
            else:
                artifact_id, partial_state = _prepare_business_artifact_resume(
                    run_id,
                    f"daily:{batch_id}",
                    batch_id,
                    ranking.business_main_pick,
                )
                artifact_recorder, artifact_ref = _build_business_artifact_recorder(
                    run_id,
                    f"daily:{batch_id}",
                    batch_id,
                    ranking.business_main_pick,
                    initial_artifact_id=artifact_id,
                )
                try:
                    business_post = await generate_business_post(
                        ranking.business_main_pick,
                        ranking.related_picks,
                        context,
                        batch_id,
                        stage_logger=_build_stage_logger(run_id, post_type="business", locale="en"),
                        partial_state=partial_state,
                        artifact_recorder=artifact_recorder,
                    )
                except Exception:
                    log_pipeline_stage(
                        run_id,
                        "business.generate.en",
                        "failed",
                        post_type="business",
                        locale="en",
                        duration_ms=int((_now() - business_started).total_seconds() * 1000),
                        output_summary="Business EN draft failed",
                    )
                    raise
                artifact_id = artifact_ref["artifact_id"]
            log_pipeline_stage(
                run_id,
                "business.generate.en",
                "success",
                post_type="business",
                locale="en",
                duration_ms=int((_now() - business_started).total_seconds() * 1000),
                output_summary=business_post.title,
                debug_meta={
                    "business_analysis_len": len(business_post.content_analysis or ""),
                    "persona_lengths": {
                        "beginner": len(business_post.content_beginner or ""),
                        "learner": len(business_post.content_learner or ""),
                        "expert": len(business_post.content_expert or ""),
                    },
                    "fact_pack_count": len(business_post.fact_pack or []),
                    "source_card_count": len(business_post.source_cards or []),
                    "resumed_from_saved_en": saved_business_en_row is not None,
                    "resumed_from_partial": artifact_id is not None and saved_business_en_row is None,
                },
            )
            logger.info("EN business post generated: %s", business_post.title)
            if not saved_business_en_row:
                en_business_id, business_tg_id = _save_business_post(
                    business_post, batch_id, locale="en"
                )
                log_pipeline_stage(
                    run_id,
                    "save.business.en",
                    "success",
                    post_type="business",
                    locale="en",
                    output_summary=en_business_id,
                )
            if artifact_id:
                _set_pipeline_artifact_status(artifact_id, "consumed")

            # Step 3-B-KO: Translate business post to Korean
            logger.info("Translating business post to Korean for batch %s...", batch_id)
            business_translate_started = _now()
            business_translate_usage: dict[str, Any] = {}
            try:
                ko_business_data = await translate_post(
                    business_post.model_dump(),
                    "business",
                    usage_recorder=business_translate_usage,
                )
                ko_business = BusinessPost.model_validate(ko_business_data)
            except Exception:
                log_pipeline_stage(
                    run_id,
                    "business.translate.ko",
                    "failed",
                    post_type="business",
                    locale="ko",
                    duration_ms=int((_now() - business_translate_started).total_seconds() * 1000),
                    output_summary="Business KO translation failed",
                    model_used=business_translate_usage.get("model_used"),
                    tokens_used=business_translate_usage.get("tokens_used"),
                    cost_usd=business_translate_usage.get("cost_usd"),
                    debug_meta={
                        "business_analysis_len": None,
                        "persona_lengths": None,
                        "input_tokens": business_translate_usage.get("input_tokens"),
                        "output_tokens": business_translate_usage.get("output_tokens"),
                    },
                )
                raise
            log_pipeline_stage(
                run_id,
                "business.translate.ko",
                "success",
                post_type="business",
                locale="ko",
                duration_ms=int((_now() - business_translate_started).total_seconds() * 1000),
                output_summary=ko_business.title,
                model_used=business_translate_usage.get("model_used"),
                tokens_used=business_translate_usage.get("tokens_used"),
                cost_usd=business_translate_usage.get("cost_usd"),
                debug_meta={
                    "business_analysis_len": len(ko_business.content_analysis or ""),
                    "persona_lengths": {
                        "beginner": len(ko_business.content_beginner or ""),
                        "learner": len(ko_business.content_learner or ""),
                        "expert": len(ko_business.content_expert or ""),
                    },
                    "fact_pack_count": len(ko_business.fact_pack or []),
                    "source_card_count": len(ko_business.source_cards or []),
                    "input_tokens": business_translate_usage.get("input_tokens"),
                    "output_tokens": business_translate_usage.get("output_tokens"),
                },
            )
            ko_business_id, _ = _save_business_post(
                ko_business, batch_id,
                locale="ko",
                translation_group_id=business_tg_id,
                source_post_id=en_business_id,
            )
            log_pipeline_stage(
                run_id,
                "save.business.ko",
                "success",
                post_type="business",
                locale="ko",
                output_summary=ko_business_id,
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
