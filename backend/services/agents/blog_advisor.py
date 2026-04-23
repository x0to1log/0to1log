"""Blog AI Advisor service — handles blog-specific AI actions + translate."""

import asyncio
import logging
import uuid

from pydantic import ValidationError

from core.config import settings
from core.database import get_supabase
from models.blog_advisor import (
    BlogAdviseRequest,
    BlogTranslateRequest,
    OutlineResult,
    DraftResult,
    RewriteResult,
    SuggestResult,
)
from models.advisor import (
    ReviewResult,
    ConceptCheckResult,
    VoiceCheckResult,
    RetroCheckResult,
)
from services.agents.client import get_openai_client, parse_ai_json, compat_create_kwargs
from services.agents.prompts_blog_advisor import (
    get_outline_prompt,
    get_draft_prompt,
    get_rewrite_prompt,
    get_suggest_prompt,
    get_blog_generate_prompt,
    get_blog_generate_target_prompt,
    BLOG_TRANSLATE_PROMPT,
)
from services.agents.prompts_advisor import (
    get_review_prompt,
    CONCEPTCHECK_SYSTEM_PROMPT,
    VOICECHECK_SYSTEM_PROMPT,
    RETROCHECK_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Action config for blog advisor
# ---------------------------------------------------------------------------

BLOG_ACTION_CONFIG = {
    # New blog-only actions
    "outline": {
        "model_attr": "openai_model_light",
        "prompt_fn": get_outline_prompt,
        "max_tokens": 2048,
        "validator": OutlineResult,
    },
    "draft": {
        "model_attr": "openai_model_main",
        "prompt_fn": get_draft_prompt,
        "max_tokens": 8192,
        "validator": DraftResult,
    },
    "rewrite": {
        "model_attr": "openai_model_main",
        "prompt_fn": get_rewrite_prompt,
        "max_tokens": 4096,
        "validator": RewriteResult,
    },
    "suggest": {
        "model_attr": "openai_model_light",
        "prompt_fn": get_suggest_prompt,
        "max_tokens": 2048,
        "validator": SuggestResult,
    },
    # Enhanced generate (absorbs SEO)
    "generate": {
        "model_attr": "openai_model_light",
        "prompt_fn": get_blog_generate_prompt,
        "max_tokens": 2048,
        "validator": None,  # flexible output
    },
    # Reused from news advisor (same prompts, same validators)
    "review": {
        "model_attr": "openai_model_reasoning",
        "prompt_fn": get_review_prompt,
        "max_tokens": 2048,
        "reasoning_effort": "medium",
        "validator": ReviewResult,
    },
    "conceptcheck": {
        "model_attr": "openai_model_reasoning",
        "prompt": CONCEPTCHECK_SYSTEM_PROMPT,
        "max_tokens": 2048,
        "reasoning_effort": "medium",
        "validator": ConceptCheckResult,
    },
    "voicecheck": {
        "model_attr": "openai_model_reasoning",
        "prompt": VOICECHECK_SYSTEM_PROMPT,
        "max_tokens": 2048,
        "reasoning_effort": "medium",
        "validator": VoiceCheckResult,
    },
    "retrocheck": {
        "model_attr": "openai_model_reasoning",
        "prompt": RETROCHECK_SYSTEM_PROMPT,
        "max_tokens": 2048,
        "reasoning_effort": "medium",
        "validator": RetroCheckResult,
    },
}


def _build_blog_user_prompt(req: BlogAdviseRequest) -> str:
    """Build user prompt from blog editor state."""
    parts = [
        f"Title: {req.title}",
        f"Category: {req.category}",
        f"Tags: {', '.join(req.tags)}" if req.tags else None,
        f"Slug: {req.slug}" if req.slug else None,
        f"Excerpt: {req.excerpt}" if req.excerpt else None,
        "",
        "Content:",
        req.content,
    ]
    return "\n".join(p for p in parts if p is not None)


async def run_blog_advise(req: BlogAdviseRequest) -> tuple[dict, str, int]:
    """Run a blog advisor action. Returns (result_dict, model_name, tokens_used)."""
    if req.action == "generate_bilingual":
        return await run_blog_generate_bilingual(req)

    config = BLOG_ACTION_CONFIG[req.action]
    model = getattr(settings, config["model_attr"])
    client = get_openai_client()

    user_prompt = _build_blog_user_prompt(req)

    # Resolve system prompt
    if "prompt_fn" in config:
        system_prompt = config["prompt_fn"](req.category)
    else:
        system_prompt = config["prompt"]

    # Inject language instruction based on locale
    lang = "Korean" if req.locale == "ko" else "English"
    system_prompt += f"\n\nIMPORTANT: Respond entirely in {lang}."

    logger.info("Blog advisor [%s] starting with model=%s, locale=%s", req.action, model, req.locale)

    extra = {}
    if config.get("reasoning_effort"):
        extra["reasoning_effort"] = config["reasoning_effort"]

    response = await client.chat.completions.create(
        **compat_create_kwargs(
            model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=config["max_tokens"],
            **extra,
        ),
    )

    raw = response.choices[0].message.content
    data = parse_ai_json(raw, f"BlogAdvisor-{req.action}")
    tokens = response.usage.completion_tokens if response.usage else 0

    # Validate and sanitize if validator is defined
    validator = config.get("validator")
    if validator:
        try:
            validator.model_validate(data)
        except ValidationError as e:
            logger.warning("Blog advisor [%s] validation soft-fail: %s", req.action, e)
            try:
                sanitized = validator.model_construct(**data)
                data = sanitized.model_dump()
            except Exception:
                pass  # keep raw data as last resort

    logger.info("Blog advisor [%s] completed, tokens=%d", req.action, tokens)
    return data, model, tokens


# ---------------------------------------------------------------------------
# Generate Bilingual — source extraction + target independent generation
# ---------------------------------------------------------------------------

async def run_blog_generate_bilingual(req: BlogAdviseRequest) -> tuple[dict, str, int]:
    """Generate metadata for both languages in parallel.

    Call 1: Extract metadata in source language (same as existing generate)
    Call 2: Generate metadata + content in target language (independent, not translation)
    """
    source_locale = req.locale or "en"
    target_locale = "ko" if source_locale == "en" else "en"
    source_lang = "English" if source_locale == "en" else "Korean"
    target_lang = "Korean" if target_locale == "ko" else "English"

    model_light = getattr(settings, "openai_model_light")
    model_main = getattr(settings, "openai_model_main")
    client = get_openai_client()
    user_prompt = _build_blog_user_prompt(req)

    # Source prompt: existing generate (metadata extraction) — light model
    source_system = get_blog_generate_prompt(req.category)
    source_system += f"\n\nIMPORTANT: Respond entirely in {source_lang}."

    # Target prompt: independent generation with content — main model
    target_system = get_blog_generate_target_prompt(req.category, source_lang, target_lang)

    logger.info(
        "Blog generate_bilingual starting: %s→%s, source=%s, target=%s",
        source_locale, target_locale, model_light, model_main,
    )

    resp_source, resp_target = await asyncio.gather(
        client.chat.completions.create(
            **compat_create_kwargs(
                model_light,
                messages=[
                    {"role": "system", "content": source_system},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=2048,
            ),
        ),
        client.chat.completions.create(
            **compat_create_kwargs(
                model_main,
                messages=[
                    {"role": "system", "content": target_system},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=8192,  # target includes full content
            ),
        ),
    )

    source_data = parse_ai_json(resp_source.choices[0].message.content, "BlogGenBilingual-source")
    target_data = parse_ai_json(resp_target.choices[0].message.content, "BlogGenBilingual-target")

    tokens_source = resp_source.usage.completion_tokens if resp_source.usage else 0
    tokens_target = resp_target.usage.completion_tokens if resp_target.usage else 0
    total_tokens = tokens_source + tokens_target

    logger.info(
        "Blog generate_bilingual completed: source=%d tokens, target=%d tokens",
        tokens_source, tokens_target,
    )

    return {
        "source": source_data,
        "target": target_data,
        "source_locale": source_locale,
        "target_locale": target_locale,
    }, f"{model_light}+{model_main}", total_tokens


# ---------------------------------------------------------------------------
# Translate — creates a new blog_posts row
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Generate a basic slug from text."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def _ensure_unique_slug(supabase, base_slug: str) -> str:
    """Append -2, -3, etc. if slug already exists in blog_posts."""
    slug = base_slug
    suffix = 2
    while True:
        existing = (
            supabase.table("blog_posts")
            .select("id")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
        if not existing.data:
            return slug
        slug = f"{base_slug}-{suffix}"
        suffix += 1


async def run_blog_translate(req: BlogTranslateRequest) -> tuple[dict, str, int]:
    """Translate a blog post and create a new row in blog_posts.

    Returns (result_dict, model_name, tokens_used).
    result_dict includes translated_post_id, translated_slug, etc.
    """
    target_locale = "ko" if req.locale == "en" else "en"

    supabase = get_supabase()
    if not supabase:
        raise RuntimeError("Supabase not configured")

    # Guard: check if translation already exists via source_post_id
    existing_check = (
        supabase.table("blog_posts")
        .select("id, slug, translation_group_id")
        .eq("source_post_id", req.source_post_id)
        .eq("locale", target_locale)
        .limit(1)
        .execute()
    )
    if existing_check.data:
        return {
            "already_exists": True,
            "existing_post_id": existing_check.data[0]["id"],
            "existing_slug": existing_check.data[0]["slug"],
            "target_locale": target_locale,
            "translation_group_id": existing_check.data[0].get("translation_group_id", ""),
        }, "", 0

    # Step 1: Translate via AI
    client = get_openai_client()
    model = getattr(settings, "openai_model_main")

    direction = f"{req.locale.upper()} → {target_locale.upper()}"
    user_prompt = (
        f"Translate this blog post from {direction}.\n\n"
        f"Title: {req.title}\n"
        f"Excerpt: {req.excerpt}\n"
        f"Tags: {', '.join(req.tags)}\n"
        f"Category: {req.category}\n\n"
        f"Content:\n{req.content}"
    )

    logger.info("Blog translate [%s] starting with model=%s", direction, model)

    response = await client.chat.completions.create(
        **compat_create_kwargs(
            model,
            messages=[
                {"role": "system", "content": BLOG_TRANSLATE_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=8192,
        ),
    )

    raw = response.choices[0].message.content
    translated = parse_ai_json(raw, "BlogTranslate")
    tokens = response.usage.completion_tokens if response.usage else 0

    # Step 2: Assign translation_group_id
    source_row = (
        supabase.table("blog_posts")
        .select("id, translation_group_id")
        .eq("id", req.source_post_id)
        .single()
        .execute()
    )
    source_data = source_row.data
    group_id = source_data.get("translation_group_id")

    if not group_id:
        group_id = str(uuid.uuid4())
        # Update source post with new group_id
        supabase.table("blog_posts").update(
            {"translation_group_id": group_id}
        ).eq("id", req.source_post_id).execute()

    # Step 3: Insert translated post
    raw_slug = translated.get("slug") or _slugify(translated.get("title", req.title))
    new_slug = _ensure_unique_slug(supabase, raw_slug)

    new_row = {
        "title": translated.get("title", req.title),
        "slug": new_slug,
        "locale": target_locale,
        "category": req.category,
        "status": "draft",
        "excerpt": translated.get("excerpt", ""),
        "content": translated.get("content", ""),
        "tags": translated.get("tags", req.tags),
        "translation_group_id": group_id,
        "source_post_id": req.source_post_id,
        "source": "ai-translated",
    }

    insert_result = (
        supabase.table("blog_posts")
        .insert(new_row)
        .select("id, slug")
        .single()
        .execute()
    )

    new_post = insert_result.data

    logger.info(
        "Blog translate completed: source=%s → new=%s, locale=%s, tokens=%d",
        req.source_post_id, new_post["id"], target_locale, tokens,
    )

    return {
        "already_exists": False,
        "translated_post_id": new_post["id"],
        "translated_slug": new_post["slug"],
        "target_locale": target_locale,
        "translation_group_id": group_id,
    }, model, tokens
