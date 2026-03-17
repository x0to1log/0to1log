"""AI News Pipeline v3 orchestrator."""
import asyncio
import logging
import time
import uuid
from datetime import date, datetime, timezone
from typing import Any

from core.config import settings
from core.database import get_supabase
from models.news_pipeline import (
    ClassifiedCandidate,
    PersonaOutput,
    PipelineResult,
)
from services.agents.advisor import extract_terms_from_content, generate_term_content
from services.agents.client import extract_usage_metrics, get_openai_client, merge_usage_metrics, parse_ai_json
from services.agents.prompts_news_pipeline import get_digest_prompt
from services.agents.ranking import classify_candidates
from services.news_collection import collect_news

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Generate a URL-safe slug from text."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')[:80]


def _fetch_handbook_slugs(supabase) -> list[str]:
    """Fetch all published handbook term slugs."""
    try:
        result = (
            supabase.table("handbook_terms")
            .select("slug")
            .eq("status", "published")
            .execute()
        )
        return [row["slug"] for row in (result.data or [])]
    except Exception as e:
        logger.warning("Failed to fetch handbook slugs: %s", e)
        return []


async def _log_stage(
    supabase,
    run_id: str,
    stage: str,
    status: str,
    start_time: float,
    *,
    input_summary: str = "",
    output_summary: str = "",
    error_message: str | None = None,
    usage: dict[str, Any] | None = None,
    post_type: str | None = None,
    locale: str | None = None,
    attempt: int | None = None,
    debug_meta: dict[str, Any] | None = None,
) -> None:
    """Log a pipeline stage to pipeline_logs. Never raises."""
    duration_ms = int((time.monotonic() - start_time) * 1000)
    usage = usage or {}

    # Merge input/output tokens into debug_meta for easy UI access
    meta = dict(debug_meta or {})
    if usage.get("input_tokens"):
        meta["input_tokens"] = usage["input_tokens"]
    if usage.get("output_tokens"):
        meta["output_tokens"] = usage["output_tokens"]

    # Build log row, omitting None values to let DB defaults apply
    # (attempt is NOT NULL DEFAULT 0, debug_meta is NOT NULL DEFAULT '{}')
    log_row: dict[str, Any] = {
        "run_id": run_id,
        "pipeline_type": stage,
        "status": status,
        "duration_ms": duration_ms,
    }
    if input_summary:
        log_row["input_summary"] = input_summary
    if output_summary:
        log_row["output_summary"] = output_summary
    if error_message:
        log_row["error_message"] = error_message
    if usage.get("model_used"):
        log_row["model_used"] = usage["model_used"]
    if usage.get("tokens_used"):
        log_row["tokens_used"] = usage["tokens_used"]
    if usage.get("cost_usd") is not None:
        log_row["cost_usd"] = usage["cost_usd"]
    if post_type:
        log_row["post_type"] = post_type
    if locale:
        log_row["locale"] = locale
    if attempt is not None:
        log_row["attempt"] = attempt
    if meta:
        log_row["debug_meta"] = meta

    try:
        supabase.table("pipeline_logs").insert(log_row).execute()
    except Exception as e:
        logger.warning("Failed to log stage %s: %s", stage, e)


def _trim(text: str | None, max_len: int = 1000) -> str:
    """Trim text to max_len for debug_meta storage."""
    if not text:
        return ""
    return text[:max_len] + ("..." if len(text) > max_len else "")


def check_existing_batch(batch_id: str) -> dict[str, Any] | None:
    """Check if data already exists for a batch_id.

    Returns info dict if data exists, None otherwise.
    """
    supabase = get_supabase()
    if not supabase:
        return None

    run_key = f"news-v2-{batch_id}"
    runs = supabase.table("pipeline_runs").select("id, status, started_at").eq("run_key", run_key).execute()
    posts = supabase.table("news_posts").select("id, status").eq("pipeline_batch_id", batch_id).execute()

    run_data = runs.data or []
    post_data = posts.data or []

    if not run_data and not post_data:
        return None

    published_count = sum(1 for p in post_data if p.get("status") == "published")
    last_run = run_data[0] if run_data else None

    return {
        "run_count": len(run_data),
        "post_count": len(post_data),
        "published_count": published_count,
        "last_status": last_run.get("status") if last_run else None,
        "last_run_at": last_run.get("started_at") if last_run else None,
    }


def cleanup_existing_batch(batch_id: str) -> dict[str, int]:
    """Delete existing pipeline data for a batch_id.

    Raises ValueError if published posts exist.
    Returns cleanup summary.
    """
    supabase = get_supabase()
    if not supabase:
        return {"deleted_runs": 0, "deleted_logs": 0, "deleted_posts": 0}

    run_key = f"news-v2-{batch_id}"

    # Check for published posts first
    published = (
        supabase.table("news_posts")
        .select("id")
        .eq("pipeline_batch_id", batch_id)
        .eq("status", "published")
        .execute()
    )
    if published.data:
        raise ValueError(
            f"{len(published.data)} published posts exist for {batch_id} — cannot overwrite"
        )

    # Get run IDs for log cleanup
    runs = supabase.table("pipeline_runs").select("id").eq("run_key", run_key).execute()
    run_ids = [r["id"] for r in (runs.data or [])]

    # Delete pipeline_logs first (no ON DELETE CASCADE)
    deleted_logs = 0
    for rid in run_ids:
        result = supabase.table("pipeline_logs").delete().eq("run_id", rid).execute()
        deleted_logs += len(result.data or [])

    # Delete pipeline_runs (pipeline_artifacts has ON DELETE CASCADE)
    if run_ids:
        supabase.table("pipeline_runs").delete().eq("run_key", run_key).execute()

    # Delete news_posts
    posts = supabase.table("news_posts").delete().eq("pipeline_batch_id", batch_id).execute()
    deleted_posts = len(posts.data or [])

    logger.info(
        "Cleaned up batch %s: %d runs, %d logs, %d posts",
        batch_id, len(run_ids), deleted_logs, deleted_posts,
    )
    return {"deleted_runs": len(run_ids), "deleted_logs": deleted_logs, "deleted_posts": deleted_posts}



async def _extract_and_create_handbook_terms(
    article_texts: list[str],
    supabase,
    run_id: str,
) -> tuple[int, list[str]]:
    """Extract AI terms from news articles and create handbook drafts.

    Returns (terms_created, errors). Never raises — errors are logged.
    """
    terms_created = 0
    errors: list[str] = []

    # Combine article texts for extraction
    combined = "\n\n---\n\n".join(article_texts)
    if not combined.strip():
        return 0, []

    # Step 1: Extract terms
    t0 = time.monotonic()
    try:
        extracted, extract_usage = await extract_terms_from_content(combined)
    except Exception as e:
        logger.warning("Handbook term extraction failed: %s", e)
        await _log_stage(
            supabase, run_id, "handbook.extract", "failed", t0,
            error_message=str(e),
        )
        return 0, [f"Term extraction failed: {e}"]

    await _log_stage(
        supabase, run_id, "handbook.extract", "success", t0,
        input_summary=f"{len(article_texts)} articles, {len(combined)} chars",
        output_summary=f"{len(extracted)} terms extracted",
        usage=extract_usage,
        debug_meta={
            "terms": [t.get("term", "") for t in extracted],
        },
    )

    if not extracted:
        return 0, []

    # Step 2: Filter, dedup, and generate content for new terms (2 at a time)
    VALID_CATEGORIES = {
        "ai-ml", "db-data", "backend", "frontend-ux", "network",
        "security", "os-core", "devops", "performance", "web3",
        "ai-business",
    }

    # Pre-filter terms before generation
    valid_terms: list[tuple[str, str, str]] = []  # (term_name, korean_name, slug)
    for term_info in extracted:
        term_name = term_info.get("term", "").strip()
        korean_name = term_info.get("korean_name", "").strip()
        if not term_name:
            continue
        if len(term_name.split()) > 3:
            logger.info("Skipping '%s' — too many words", term_name)
            continue
        lower = term_name.lower()
        if lower.endswith(("-powered", "-driven", "-based", "-enabled", "-oriented")):
            logger.info("Skipping '%s' — adjective/modifier", term_name)
            continue
        category = term_info.get("category", "")
        if category not in VALID_CATEGORIES:
            logger.info("Skipping '%s' — invalid category '%s'", term_name, category)
            continue
        slug = _slugify(term_name)
        if not slug:
            continue

        # Check if term already exists
        try:
            existing = (
                supabase.table("handbook_terms")
                .select("id")
                .or_(f"slug.eq.{slug},term.ilike.{term_name}")
                .limit(1)
                .execute()
            )
            if existing.data:
                logger.info("Handbook term '%s' already exists, skipping", term_name)
                continue
        except Exception as e:
            logger.warning("Duplicate check failed for '%s': %s", term_name, e)
            continue

        valid_terms.append((term_name, korean_name, slug))

    # Generate terms concurrently (max 2 at a time)
    sem = asyncio.Semaphore(2)

    async def _create_single_term(term_name: str, korean_name: str, slug: str) -> tuple[int, list[str]]:
        """Generate and save a single handbook term. Returns (created_count, errors)."""
        async with sem:
            t_gen = time.monotonic()
            try:
                content_data, gen_usage = await generate_term_content(
                    term_name, korean_name,
                )
            except Exception as e:
                error_msg = f"Handbook generate failed for '{term_name}': {e}"
                logger.warning(error_msg)
                await _log_stage(
                    supabase, run_id, "handbook.auto_generate", "failed", t_gen,
                    error_message=error_msg,
                    debug_meta={"term": term_name},
                )
                return 0, [error_msg]

            try:
                row = {
                    "term": term_name,
                    "slug": slug,
                    "korean_name": content_data.get("korean_name", korean_name),
                    "term_full": content_data.get("term_full", ""),
                    "korean_full": content_data.get("korean_full", ""),
                    "categories": content_data.get("categories", []),
                    "definition_ko": content_data.get("definition_ko", ""),
                    "definition_en": content_data.get("definition_en", ""),
                    "body_basic_ko": content_data.get("body_basic_ko", ""),
                    "body_basic_en": content_data.get("body_basic_en", ""),
                    "body_advanced_ko": content_data.get("body_advanced_ko", ""),
                    "body_advanced_en": content_data.get("body_advanced_en", ""),
                    "status": "draft",
                    "source": "pipeline",
                }
                result = supabase.table("handbook_terms").insert(row).execute()
                if not result.data:
                    error_msg = f"Insert returned empty for '{term_name}'"
                    logger.error(error_msg)
                    await _log_stage(
                        supabase, run_id, "handbook.auto_generate", "failed", t_gen,
                        error_message=error_msg, usage=gen_usage,
                        debug_meta={"term": term_name, "slug": slug},
                    )
                    return 0, [error_msg]

                logger.info("Created handbook draft: %s (%s)", term_name, slug)
                await _log_stage(
                    supabase, run_id, "handbook.auto_generate", "success", t_gen,
                    output_summary=f"term={term_name}, slug={slug}",
                    usage=gen_usage,
                    debug_meta={"term": term_name, "slug": slug},
                )
                return 1, []
            except Exception as e:
                error_msg = f"Failed to save handbook term '{term_name}': {e}"
                logger.error(error_msg)
                await _log_stage(
                    supabase, run_id, "handbook.auto_generate", "failed", t_gen,
                    error_message=error_msg, usage=gen_usage,
                    debug_meta={"term": term_name, "slug": slug},
                )
                return 0, [error_msg]

    if valid_terms:
        term_results = await asyncio.gather(
            *[_create_single_term(tn, kn, sl) for tn, kn, sl in valid_terms],
        )
        for created, term_errors in term_results:
            terms_created += created
            errors.extend(term_errors)

    logger.info("Handbook auto-extraction: %d terms created, %d errors", terms_created, len(errors))
    return terms_created, errors


QUALITY_CHECK_PROMPT_RESEARCH = """You are a strict quality reviewer for an AI tech news digest.

Score this Research digest on 4 criteria (0-25 each, total 0-100):

1. **Section Completeness** (25): Does it have all required sections (One-Line Summary, LLM & Models, Open Source, Papers, Technical Outlook)? Are any sections empty or too short?
2. **Source Citations** (25): Does each news item cite a source URL? Are benchmark numbers attributed?
3. **Technical Accuracy** (25): Are parameter counts, benchmarks, and technical details specific (not vague)? Are comparisons to prior work included?
4. **Language Quality** (25): Is the content natural in the target language (not translation-sounding)? Is the length adequate (min 500 chars per section)?

Return JSON:
{"score": 0-100, "sections": 0-25, "sources": 0-25, "accuracy": 0-25, "language": 0-25, "issues": ["issue1", "issue2"]}"""

QUALITY_CHECK_PROMPT_BUSINESS = """You are a strict quality reviewer for an AI business news digest.

Score this Business digest on 4 criteria (0-25 each, total 0-100):

1. **Section Completeness** (25): Does it have all required sections (One-Line Summary, Big Tech, Industry & Biz, New Tools, Connecting the Dots, Action Items)? Are any sections empty?
2. **Source Citations** (25): Does each news item cite a source URL? Are funding amounts and dates attributed?
3. **Analysis Quality** (25): Does "Connecting the Dots" actually connect news items into a trend? Are "Action Items" specific and actionable (not generic advice)?
4. **Language Quality** (25): Is the content natural in the target language? Is the length adequate?

Return JSON:
{"score": 0-100, "sections": 0-25, "sources": 0-25, "analysis": 0-25, "language": 0-25, "issues": ["issue1", "issue2"]}"""


async def _check_digest_quality(
    personas: dict[str, PersonaOutput],
    digest_type: str,
    classified: list,
    supabase,
    run_id: str,
    cumulative_usage: dict[str, Any],
) -> int:
    """Score the quality of a generated digest. Returns score 0-100."""
    t0 = time.monotonic()

    # Use expert persona EN content for quality check (most detailed)
    expert = personas.get("expert")
    if not expert or not expert.en:
        return 0

    prompt = QUALITY_CHECK_PROMPT_RESEARCH if digest_type == "research" else QUALITY_CHECK_PROMPT_BUSINESS

    try:
        client = get_openai_client()
        response = await client.chat.completions.create(
            model=settings.openai_model_light,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": expert.en[:4000]},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=512,
        )
        data = parse_ai_json(response.choices[0].message.content, f"Quality-{digest_type}")
        usage = extract_usage_metrics(response, settings.openai_model_light)
        score = int(data.get("score", 0))

        await _log_stage(
            supabase, run_id, f"quality:{digest_type}", "success", t0,
            output_summary=f"score={score}/100",
            usage=usage,
            post_type=digest_type,
            debug_meta={
                "score": score,
                "quality_score": score,
                "breakdown": {k: v for k, v in data.items() if k != "score"},
                "news_count": len(classified),
            },
        )

        logger.info("Quality check %s: score=%d/100", digest_type, score)
        return score
    except Exception as e:
        logger.warning("Quality check failed for %s: %s", digest_type, e)
        await _log_stage(
            supabase, run_id, f"quality:{digest_type}", "failed", t0,
            error_message=str(e), post_type=digest_type,
        )
        return 0


async def _generate_digest(
    classified: list[ClassifiedCandidate],
    digest_type: str,
    batch_id: str,
    handbook_slugs: list[str],
    raw_content_map: dict[str, str],
    supabase,
    run_id: str,
) -> tuple[int, list[str], dict[str, Any]]:
    """Generate a daily digest post for one category (research or business).

    Creates 3 persona versions (expert/learner/beginner) × 2 locales (en/ko).
    Returns (posts_created, errors, usage).
    """
    errors: list[str] = []
    cumulative_usage: dict[str, Any] = {}
    posts_created = 0

    if not classified:
        return 0, [], {}

    # Build user prompt from classified news items
    news_items = []
    for item in classified:
        body = raw_content_map.get(item.url, item.snippet)[:4000]
        news_items.append(
            f"### [{item.subcategory}] {item.title}\n"
            f"URL: {item.url}\n"
            f"Relevance: {item.relevance_score}\n\n"
            f"{body}"
        )
    user_prompt = "\n\n---\n\n".join(news_items)

    # Generate 3 personas
    client = get_openai_client()
    model = settings.openai_model_main
    personas: dict[str, PersonaOutput] = {}
    digest_headline = ""
    digest_headline_ko = ""

    MAX_DIGEST_RETRIES = 1  # 1 retry = 2 total attempts

    for persona_name in ("expert", "learner", "beginner"):
        t_p = time.monotonic()
        system_prompt = get_digest_prompt(digest_type, persona_name, handbook_slugs)

        for attempt in range(MAX_DIGEST_RETRIES + 1):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.4,
                    max_tokens=16000,
                )
                data = parse_ai_json(
                    response.choices[0].message.content,
                    f"Digest-{digest_type}-{persona_name}",
                )
                persona_output = PersonaOutput(
                    en=data.get("en", ""),
                    ko=data.get("ko", ""),
                )

                # Capture headline from first persona (expert)
                if not digest_headline and data.get("headline"):
                    digest_headline = data["headline"]
                if not digest_headline_ko and data.get("headline_ko"):
                    digest_headline_ko = data["headline_ko"]
                usage = extract_usage_metrics(response, model)
                cumulative_usage = merge_usage_metrics(cumulative_usage, usage)
                personas[persona_name] = persona_output

                await _log_stage(
                    supabase, run_id,
                    f"digest:{digest_type}:{persona_name}", "success", t_p,
                    output_summary=f"en={len(persona_output.en)}chars, ko={len(persona_output.ko)}chars",
                    usage=usage,
                    post_type=digest_type,
                    attempt=attempt + 1,
                    debug_meta={
                        "attempt": attempt + 1,
                        "en_length": len(persona_output.en),
                        "ko_length": len(persona_output.ko),
                        "en_preview": _trim(persona_output.en, 500),
                        "ko_preview": _trim(persona_output.ko, 500),
                        "news_count": len(classified),
                    },
                )
                break  # success — no more retries

            except Exception as e:
                logger.warning(
                    "Digest %s %s attempt %d failed: %s",
                    digest_type, persona_name, attempt + 1, e,
                )
                if attempt == MAX_DIGEST_RETRIES:
                    error_msg = f"{digest_type} {persona_name} digest failed after {attempt + 1} attempts: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    await _log_stage(
                        supabase, run_id,
                        f"digest:{digest_type}:{persona_name}", "failed", t_p,
                        error_message=error_msg, post_type=digest_type,
                        attempt=attempt + 1,
                        debug_meta={"attempt": attempt + 1},
                    )

    if len(personas) < 3:
        missing = [p for p in ("expert", "learner", "beginner") if p not in personas]
        error_msg = f"{digest_type} digest incomplete — missing personas: {missing}"
        logger.error(error_msg)
        errors.append(error_msg)
        return 0, errors, cumulative_usage

    # Quality check — score the generated digest
    quality_score = await _check_digest_quality(
        personas, digest_type, classified, supabase, run_id, cumulative_usage,
    )

    # Save EN + KO rows
    missing = [p for p in ("expert", "learner", "beginner") if p not in personas]
    if missing:
        logger.warning("Missing personas for %s digest: %s", digest_type, missing)

    t_save = time.monotonic()
    translation_group_id = str(uuid.uuid4())
    slug_base = f"{batch_id}-{digest_type}-digest"

    source_urls = [item.url for item in classified]
    digest_meta = {
        "digest_type": digest_type,
        "news_items": [
            {"title": item.title, "url": item.url, "subcategory": item.subcategory}
            for item in classified
        ],
    }

    fallback_title = classified[0].title if classified else ""
    type_label = "Research" if digest_type == "research" else "Business"

    for locale in ("en", "ko"):
        slug = slug_base if locale == "en" else f"{slug_base}-ko"
        if locale == "ko":
            ko_title = digest_headline_ko or fallback_title
            title = f"{ko_title} — AI {type_label} 데일리" if ko_title else f"AI {type_label} 데일리 — {batch_id}"
        else:
            en_title = digest_headline or fallback_title
            title = f"{en_title} — AI {type_label} Daily" if en_title else f"AI {type_label} Daily — {batch_id}"

        row = {
            "title": title,
            "slug": slug,
            "locale": locale,
            "category": "ai-news",
            "post_type": digest_type,
            "status": "draft",
            "content_expert": (personas["expert"].en if locale == "en" else personas["expert"].ko) if "expert" in personas else None,
            "content_learner": (personas["learner"].en if locale == "en" else personas["learner"].ko) if "learner" in personas else None,
            "content_beginner": (personas["beginner"].en if locale == "en" else personas["beginner"].ko) if "beginner" in personas else None,
            "source_urls": source_urls,
            "fact_pack": {**digest_meta, "quality_score": quality_score},
            "quality_score": quality_score,
            "pipeline_batch_id": batch_id,
            "published_at": f"{batch_id}T09:00:00Z",
            "pipeline_model": settings.openai_model_main,
            "translation_group_id": translation_group_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            supabase.table("news_posts").upsert(row).execute()
            posts_created += 1
            logger.info("Saved %s %s digest draft: %s", digest_type, locale, slug)
        except Exception as e:
            error_msg = f"Failed to save {digest_type} {locale} digest: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    await _log_stage(
        supabase, run_id, f"save:{digest_type}",
        "success" if posts_created > 0 else "failed", t_save,
        output_summary=f"{posts_created} digest rows saved",
        post_type=digest_type,
        debug_meta={"slug_base": slug_base, "locales": ["en", "ko"]},
    )

    return posts_created, errors, cumulative_usage



async def run_daily_pipeline(
    batch_id: str | None = None,
    target_date: str | None = None,
    skip_handbook: bool = False,
) -> PipelineResult:
    """Run the full daily AI news pipeline.

    Flow: collect → rank → (react + extract + personas) × 2 → save drafts.
    """
    if batch_id is None:
        batch_id = target_date or date.today().isoformat()

    is_backfill = False
    if target_date:
        try:
            is_backfill = datetime.strptime(target_date, "%Y-%m-%d").date() < date.today()
        except ValueError:
            pass

    supabase = get_supabase()
    if not supabase:
        return PipelineResult(
            batch_id=batch_id,
            errors=["Supabase not configured"],
        )

    total_posts = 0
    all_errors: list[str] = []
    cumulative_usage: dict[str, Any] = {}

    run_id = str(uuid.uuid4())
    try:
        supabase.table("pipeline_runs").insert({
            "id": run_id,
            "run_key": f"news-v2-{batch_id}",
            "status": "running",
        }).execute()
    except Exception as e:
        logger.warning("Failed to record pipeline run: %s", e)

    try:
        # Stage: collect
        t0 = time.monotonic()
        candidates, collect_meta = await collect_news(target_date=target_date)

        await _log_stage(
            supabase, run_id, "collect", "success" if candidates else "no_news", t0,
            input_summary=f"target_date={target_date or 'today'}",
            output_summary=f"{len(candidates)} unique candidates",
            debug_meta={
                "target_date": target_date,
                "is_backfill": is_backfill,
                "mode": "backfill" if is_backfill else "daily",
                **collect_meta,
            },
        )

        if not candidates:
            logger.info("No news candidates found, pipeline complete")
            try:
                supabase.table("pipeline_runs").update({
                    "status": "success",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "last_error": None,
                }).eq("id", run_id).execute()
            except Exception as e:
                logger.warning("Failed to update pipeline run: %s", e)
            return PipelineResult(batch_id=batch_id)

        # Stage: classify (v3 — multi-news categorization)
        t0 = time.monotonic()
        classification, classify_usage = await classify_candidates(candidates)
        cumulative_usage = merge_usage_metrics(cumulative_usage, classify_usage)

        classify_input_summary = "\n".join(
            f"[{i+1}] {c.title} ({c.url})" for i, c in enumerate(candidates)
        )
        classify_output = {
            "research": [
                {"title": c.title, "url": c.url, "subcategory": c.subcategory}
                for c in classification.research
            ],
            "business": [
                {"title": c.title, "url": c.url, "subcategory": c.subcategory}
                for c in classification.business
            ],
        }

        await _log_stage(
            supabase, run_id, "classify", "success", t0,
            input_summary=f"{len(candidates)} candidates",
            output_summary=f"research={len(classification.research)}, business={len(classification.business)}",
            usage=classify_usage,
            debug_meta={
                "llm_input": _trim(classify_input_summary),
                "llm_output": classify_output,
                "candidates_count": len(candidates),
            },
        )

        handbook_slugs = _fetch_handbook_slugs(supabase)
        raw_content_map = {c.url: c.raw_content for c in candidates if c.raw_content}

        # Generate research + business digests in parallel
        digest_tasks = []
        for digest_type, classified_items in [
            ("research", classification.research),
            ("business", classification.business),
        ]:
            if not classified_items:
                continue
            digest_tasks.append(
                _generate_digest(
                    classified=classified_items,
                    digest_type=digest_type,
                    batch_id=batch_id,
                    handbook_slugs=handbook_slugs,
                    raw_content_map=raw_content_map,
                    supabase=supabase,
                    run_id=run_id,
                )
            )

        digest_results = await asyncio.gather(*digest_tasks, return_exceptions=True)
        for result in digest_results:
            if isinstance(result, Exception):
                all_errors.append(f"Digest generation failed: {result}")
                logger.error("Digest generation exception: %s", result)
            else:
                posts, errors, usage = result
                total_posts += posts
                all_errors.extend(errors)
                cumulative_usage = merge_usage_metrics(cumulative_usage, usage)

        # Stage: summary (news only — handbook runs separately)
        t_summary = time.monotonic()
        status = "success" if not all_errors else "failed"

        await _log_stage(
            supabase, run_id, "summary", status, t_summary,
            input_summary=f"{len(candidates)} candidates",
            output_summary=f"{total_posts} posts created",
            usage=cumulative_usage,
            error_message="; ".join(all_errors) if all_errors else None,
            debug_meta={
                "mode": "backfill" if is_backfill else "daily",
                "target_date": target_date,
                "batch_id": batch_id,
                "total_posts": total_posts,
                "total_cost": cumulative_usage.get("cost_usd"),
                "research_count": len(classification.research),
                "business_count": len(classification.business),
            },
        )

        try:
            supabase.table("pipeline_runs").update({
                "status": status,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": all_errors[0] if all_errors else None,
            }).eq("id", run_id).execute()
        except Exception as e:
            logger.warning("Failed to update pipeline run: %s", e)

    except Exception as e:
        logger.error("Pipeline unexpected error: %s", e)
        all_errors.append(str(e))
        try:
            supabase.table("pipeline_runs").update({
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": str(e),
            }).eq("id", run_id).execute()
        except Exception:
            pass

    result = PipelineResult(
        batch_id=batch_id,
        posts_created=total_posts,
        errors=all_errors,
        usage=cumulative_usage,
    )
    logger.info("News pipeline complete: %d posts, %d errors", total_posts, len(all_errors))

    # Auto-trigger handbook extraction as a separate run (non-blocking)
    if total_posts > 0 and not skip_handbook:
        try:
            await run_handbook_extraction(batch_id)
        except Exception as e:
            logger.warning("Handbook extraction auto-trigger failed: %s", e)

    return result


async def run_handbook_extraction(batch_id: str) -> PipelineResult:
    """Run handbook term extraction from existing news posts. Independent pipeline run.

    Reads news_posts for the given batch_id and extracts/generates handbook terms.
    Can be called independently to retry after failure without re-running news.
    """
    supabase = get_supabase()
    if not supabase:
        return PipelineResult(batch_id=batch_id, errors=["Supabase not configured"])

    # Fetch article content from existing news posts
    try:
        posts_result = (
            supabase.table("news_posts")
            .select("content_expert, title")
            .eq("pipeline_batch_id", batch_id)
            .eq("locale", "en")
            .execute()
        )
        article_texts = [
            p.get("content_expert", "") or p.get("title", "")
            for p in (posts_result.data or [])
            if p.get("content_expert")
        ]
    except Exception as e:
        return PipelineResult(batch_id=batch_id, errors=[f"Failed to fetch posts: {e}"])

    if not article_texts:
        logger.info("No article content for handbook extraction (batch %s)", batch_id)
        return PipelineResult(batch_id=batch_id)

    # Create separate pipeline run (delete existing if retry)
    run_id = str(uuid.uuid4())
    run_key = f"handbook-extract-{batch_id}"
    all_errors: list[str] = []

    try:
        # Clean up previous run if exists (for retry support)
        old_runs = supabase.table("pipeline_runs").select("id").eq("run_key", run_key).execute()
        for old_run in (old_runs.data or []):
            supabase.table("pipeline_logs").delete().eq("run_id", old_run["id"]).execute()
        supabase.table("pipeline_runs").delete().eq("run_key", run_key).execute()
    except Exception as e:
        logger.warning("Failed to clean up old handbook run: %s", e)

    try:
        supabase.table("pipeline_runs").insert({
            "id": run_id,
            "run_key": run_key,
            "status": "running",
        }).execute()
    except Exception as e:
        logger.warning("Failed to create handbook extraction run: %s", e)

    try:
        terms_created, errors = await _extract_and_create_handbook_terms(
            article_texts, supabase, run_id,
        )
        all_errors.extend(errors)

        status = "success" if not errors else "failed"
        try:
            supabase.table("pipeline_runs").update({
                "status": status,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": errors[0] if errors else None,
            }).eq("id", run_id).execute()
        except Exception as e:
            logger.warning("Failed to update handbook run: %s", e)

        logger.info(
            "Handbook extraction complete (batch %s): %d terms, %d errors",
            batch_id, terms_created, len(errors),
        )
    except Exception as e:
        logger.error("Handbook extraction failed: %s", e)
        all_errors.append(str(e))
        try:
            supabase.table("pipeline_runs").update({
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "last_error": str(e),
            }).eq("id", run_id).execute()
        except Exception:
            pass

    return PipelineResult(
        batch_id=batch_id,
        posts_created=0,
        errors=all_errors,
    )
