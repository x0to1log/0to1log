"""AI Advisor agent handlers — post actions + deep verify + handbook."""

import asyncio
import json
import logging
import re
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError
from tavily import TavilyClient

from core.config import settings
from models.advisor import (
    AiAdviseRequest,
    GenerateResult,
    SeoResult,
    ReviewResult,
    FactcheckResult,
    DeepVerifyResult,
    ConceptCheckResult,
    VoiceCheckResult,
    RetroCheckResult,
    HandbookAdviseRequest,
    RelatedTermsResult,
    TranslateResult,
    GenerateTermResult,
    ExtractTermsResult,
)
from services.agents.client import build_completion_kwargs, compat_create_kwargs, extract_usage_metrics, get_openai_client, merge_usage_metrics, parse_ai_json, with_flex_retry
from core.database import get_supabase
from services.agents.prompts_advisor import (
    get_generate_prompt,
    get_seo_prompt,
    get_review_prompt,
    FACTCHECK_SYSTEM_PROMPT,
    CONCEPTCHECK_SYSTEM_PROMPT,
    VOICECHECK_SYSTEM_PROMPT,
    RETROCHECK_SYSTEM_PROMPT,
    DEEPVERIFY_CLAIM_EXTRACT_PROMPT,
    DEEPVERIFY_VERIFY_PROMPT,
    RELATED_TERMS_PROMPT,
    TRANSLATE_PROMPT,
    GENERATE_BASIC_PROMPT,
    GENERATE_BASIC_EN_PROMPT,
    GENERATE_ADVANCED_PROMPT,
    GENERATE_ADVANCED_EN_PROMPT,
    EXTRACT_TERMS_PROMPT,
)

logger = logging.getLogger(__name__)

# Model + config per action
# "prompt_fn": callable(category) -> str  for category-aware actions
# "prompt": str  for category-agnostic actions
ACTION_CONFIG = {
    "generate": {
        "model_attr": "openai_model_main",
        "prompt_fn": get_generate_prompt,
        "max_tokens": 4096,
        "validator": GenerateResult,
    },
    "seo": {
        "model_attr": "openai_model_light",
        "prompt_fn": get_seo_prompt,
        "max_tokens": 2048,
        "validator": SeoResult,
    },
    "review": {
        "model_attr": "openai_model_reasoning",
        "prompt_fn": get_review_prompt,
        "max_tokens": 2048,
        "reasoning_effort": "medium",
        "service_tier": "flex",
        "prompt_cache_key": "advisor-review",
        "validator": ReviewResult,
    },
    "factcheck": {
        "model_attr": "openai_model_reasoning",
        "prompt": FACTCHECK_SYSTEM_PROMPT,
        "max_tokens": 4096,
        "reasoning_effort": "medium",
        "service_tier": "flex",
        "prompt_cache_key": "advisor-factcheck",
        "validator": FactcheckResult,
    },
    "conceptcheck": {
        "model_attr": "openai_model_reasoning",
        "prompt": CONCEPTCHECK_SYSTEM_PROMPT,
        "max_tokens": 2048,
        "reasoning_effort": "medium",
        "service_tier": "flex",
        "prompt_cache_key": "advisor-conceptcheck",
        "validator": ConceptCheckResult,
    },
    "voicecheck": {
        "model_attr": "openai_model_reasoning",
        "prompt": VOICECHECK_SYSTEM_PROMPT,
        "max_tokens": 2048,
        "reasoning_effort": "medium",
        "service_tier": "flex",
        "prompt_cache_key": "advisor-voicecheck",
        "validator": VoiceCheckResult,
    },
    "retrocheck": {
        "model_attr": "openai_model_reasoning",
        "prompt": RETROCHECK_SYSTEM_PROMPT,
        "max_tokens": 2048,
        "reasoning_effort": "medium",
        "service_tier": "flex",
        "prompt_cache_key": "advisor-retrocheck",
        "validator": RetroCheckResult,
    },
}


def _build_user_prompt(req: AiAdviseRequest) -> str:
    """Build user prompt from editor state."""
    parts = [
        f"Title: {req.title}",
        f"Category: {req.category}",
        f"Post type: {req.post_type}" if req.post_type else None,
        f"Tags: {', '.join(req.tags)}" if req.tags else None,
        f"Slug: {req.slug}" if req.slug else None,
        f"Excerpt: {req.excerpt}" if req.excerpt else None,
        "",
        "Content:",
        req.content,
    ]
    return "\n".join(p for p in parts if p is not None)


def _build_seo_user_prompt(req: AiAdviseRequest) -> str:
    """Build SEO user prompt — truncate content for cost efficiency."""
    content_preview = req.content[:2000]
    if len(req.content) > 2000:
        content_preview += "\n[... truncated for analysis]"
    parts = [
        f"Title: {req.title}",
        f"Excerpt: {req.excerpt}" if req.excerpt else None,
        f"Tags: {', '.join(req.tags)}" if req.tags else None,
        "",
        "Content (first 2000 chars):",
        content_preview,
    ]
    return "\n".join(p for p in parts if p is not None)


def _log_advisor_call(
    stage: str,
    usage: dict,
    extra_meta: dict | None = None,
) -> None:
    """Log one admin-editor advisor call to pipeline_logs. Never raises.

    Parallels _log_handbook_stage but lives at module scope so
    run_advise / run_deep_verify can share it (blog_advisor has its
    own helper with a distinct pipeline_type prefix).

    stage:
        'advisor.<action>' for news editor actions
        'advisor.deepverify.step1' / 'advisor.deepverify.step2'

    Fields recorded mirror _log_handbook_stage so admin analytics can
    treat handbook and advisor logs uniformly: tokens_used / cost_usd
    on the row, plus input/output/cached/reasoning_tokens + service_tier
    on debug_meta. Guard on `is not None` for cached/reasoning so zero
    values (minimal reasoning / no cache hit) still surface.
    """
    supabase = get_supabase()
    if not supabase:
        return
    try:
        meta = {
            "source": "manual",
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
        }
        if usage.get("cached_tokens") is not None:
            meta["cached_tokens"] = usage["cached_tokens"]
        if usage.get("reasoning_tokens") is not None:
            meta["reasoning_tokens"] = usage["reasoning_tokens"]
        if usage.get("service_tier"):
            meta["service_tier"] = usage["service_tier"]
        if extra_meta:
            meta.update(extra_meta)
        supabase.table("pipeline_logs").insert({
            "pipeline_type": stage,
            "status": "success",
            "model_used": usage.get("model_used"),
            "tokens_used": usage.get("tokens_used"),
            "cost_usd": usage.get("cost_usd"),
            "debug_meta": meta,
        }).execute()
    except Exception as e:
        logger.warning("Failed to log advisor %s stage: %s", stage, e)


async def run_advise(req: AiAdviseRequest) -> tuple[dict, str, int]:
    """Run an advisor action. Returns (result_dict, model_name, tokens_used)."""
    config = ACTION_CONFIG[req.action]
    model = getattr(settings, config["model_attr"])
    client = get_openai_client()

    user_prompt = (
        _build_seo_user_prompt(req) if req.action == "seo"
        else _build_user_prompt(req)
    )

    logger.info("Advisor [%s] starting with model=%s", req.action, model)

    # Resolve system prompt: category-aware (prompt_fn) or static (prompt)
    if "prompt_fn" in config:
        system_prompt = config["prompt_fn"](req.category)
    else:
        system_prompt = config["prompt"]

    completion_kwargs = build_completion_kwargs(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=config["max_tokens"],
        response_format={"type": "json_object"},
    )
    for key in ("reasoning_effort", "service_tier", "prompt_cache_key", "verbosity"):
        if config.get(key):
            completion_kwargs[key] = config[key]
    response = await client.chat.completions.create(**completion_kwargs)

    raw = response.choices[0].message.content
    data = parse_ai_json(raw, f"Advisor-{req.action}")
    tokens = response.usage.completion_tokens if response.usage else 0

    # Validate against action-specific schema
    validator = config["validator"]
    try:
        validator.model_validate(data)
    except ValidationError as e:
        logger.warning("Advisor [%s] validation soft-fail: %s", req.action, e)
        # Return raw data anyway — partial results are still useful

    usage = extract_usage_metrics(response, model)
    _log_advisor_call(
        f"advisor.{req.action}",
        usage,
        extra_meta={"post_id": req.post_id} if getattr(req, "post_id", None) else None,
    )

    logger.info("Advisor [%s] completed, tokens=%d", req.action, tokens)
    return data, model, tokens


# --- Deep Verify (Tavily-backed 2-step fact-check) ---

async def _extract_urls_from_content(content: str) -> list[str]:
    """Extract markdown link URLs from content."""
    return re.findall(r'\[.*?\]\((https?://[^\s)]+)\)', content)


async def _check_url(url: str) -> dict | None:
    """HEAD-check a URL and return broken link info if failed."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.head(url)
            if resp.status_code >= 400:
                return {"url": url, "status_code": resp.status_code, "error": f"HTTP {resp.status_code}"}
    except httpx.TimeoutException:
        return {"url": url, "status_code": 0, "error": "Timeout"}
    except httpx.RequestError as e:
        return {"url": url, "status_code": 0, "error": str(e)[:100]}
    return None


async def run_deep_verify(req: AiAdviseRequest) -> tuple[dict, str, int]:
    """2-step deep verification: extract claims → search → verify."""
    client = get_openai_client()
    model = settings.openai_model_reasoning
    total_tokens = 0

    # Step 1: Extract claims
    user_prompt = _build_user_prompt(req)
    step1_kwargs = build_completion_kwargs(
        model=model,
        messages=[
            {"role": "system", "content": DEEPVERIFY_CLAIM_EXTRACT_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=2048,
        response_format={"type": "json_object"},
        reasoning_effort="medium",
        service_tier="flex",
        prompt_cache_key="advisor-deepverify-step1",
    )
    resp1 = await client.chat.completions.create(**step1_kwargs)
    claims_data = parse_ai_json(resp1.choices[0].message.content, "DeepVerify-extract")
    total_tokens += resp1.usage.completion_tokens if resp1.usage else 0
    usage1 = extract_usage_metrics(resp1, model)
    _log_advisor_call(
        "advisor.deepverify.step1",
        usage1,
        extra_meta={"post_id": getattr(req, "post_id", None)} if getattr(req, "post_id", None) else None,
    )
    claims = claims_data.get("claims", [])

    if not claims:
        return {
            "claims": [],
            "broken_links": [],
            "overall_confidence": "high",
            "confidence_reason": "No verifiable claims found in the content",
        }, model, total_tokens

    # Step 2: Search each claim via Tavily (Exa fallback)
    search_results = {}
    loop = asyncio.get_running_loop()

    async def search_claim(claim_text: str) -> list[dict]:
        # Try Tavily first
        if settings.tavily_api_key:
            try:
                from tavily import TavilyClient
                tavily = TavilyClient(api_key=settings.tavily_api_key)
                result = await loop.run_in_executor(
                    None,
                    lambda: tavily.search(
                        query=claim_text,
                        search_depth="advanced",
                        max_results=3,
                    ),
                )
                return result.get("results", [])
            except Exception as e:
                logger.warning("Tavily search failed for claim, trying Exa: %s", e)
        # Exa fallback
        if settings.exa_api_key:
            try:
                from exa_py import Exa
                exa = Exa(api_key=settings.exa_api_key)
                exa_res = await loop.run_in_executor(
                    None,
                    lambda: exa.search_and_contents(
                        claim_text, num_results=3, text={"max_characters": 3000},
                    ),
                )
                return [{"title": r.title, "url": r.url, "content": (r.text or "")[:3000]} for r in exa_res.results]
            except Exception as e:
                logger.warning("Exa search also failed for claim: %s", e)
        return []

    if settings.tavily_api_key or settings.exa_api_key:
        tasks = [search_claim(c["claim"]) for c in claims]
        results = await asyncio.gather(*tasks)
        for i, c in enumerate(claims):
            search_results[c["claim"]] = results[i]

    # Step 2b: Check URLs in content
    urls = await _extract_urls_from_content(req.content)
    broken_links = []
    if urls:
        link_checks = await asyncio.gather(*[_check_url(u) for u in urls[:20]])
        broken_links = [bl for bl in link_checks if bl is not None]

    # Step 3: Verify claims with search evidence
    verify_input = []
    for c in claims:
        evidence = search_results.get(c["claim"], [])
        evidence_text = "\n".join(
            f"- [{e.get('title', '')}]({e.get('url', '')}): {e.get('content', '')[:300]}"
            for e in evidence
        ) or "No search results found."
        verify_input.append(f"Claim: {c['claim']}\nSearch evidence:\n{evidence_text}")

    verify_prompt = "\n\n---\n\n".join(verify_input)

    step2_kwargs = build_completion_kwargs(
        model=model,
        messages=[
            {"role": "system", "content": DEEPVERIFY_VERIFY_PROMPT},
            {"role": "user", "content": verify_prompt},
        ],
        max_tokens=4096,
        response_format={"type": "json_object"},
        reasoning_effort="medium",
        service_tier="flex",
        prompt_cache_key="advisor-deepverify-step2",
    )
    resp2 = await client.chat.completions.create(**step2_kwargs)
    verify_data = parse_ai_json(resp2.choices[0].message.content, "DeepVerify-verify")
    total_tokens += resp2.usage.completion_tokens if resp2.usage else 0
    usage2 = extract_usage_metrics(resp2, model)
    _log_advisor_call(
        "advisor.deepverify.step2",
        usage2,
        extra_meta={"post_id": getattr(req, "post_id", None)} if getattr(req, "post_id", None) else None,
    )

    # Merge broken links into result
    verify_data["broken_links"] = broken_links

    # Soft validate
    try:
        DeepVerifyResult.model_validate(verify_data)
    except ValidationError as e:
        logger.warning("DeepVerify validation soft-fail: %s", e)

    logger.info("DeepVerify completed, claims=%d, tokens=%d", len(claims), total_tokens)
    return verify_data, model, total_tokens


# --- Handbook AI Advisor ---

def _build_handbook_user_prompt(req: HandbookAdviseRequest) -> str:
    """Build user prompt from handbook editor state."""
    parts = [
        f"Term: {req.term}",
        f"Korean name: {req.korean_name}" if req.korean_name else None,
        f"English full name: {req.term_full}" if req.term_full else None,
        f"Korean full name: {req.korean_full}" if req.korean_full else None,
        f"Categories: {', '.join(req.categories)}" if req.categories else None,
    ]
    # Include available content
    for lang in ("ko", "en"):
        summary = getattr(req, f"summary_{lang}", "")
        defn = getattr(req, f"definition_{lang}", "")
        basic = getattr(req, f"body_basic_{lang}", "")
        advanced = getattr(req, f"body_advanced_{lang}", "")
        hero = getattr(req, f"hero_news_context_{lang}", "")
        refs = getattr(req, f"references_{lang}", [])
        if any([summary, defn, basic, advanced, hero, refs]):
            parts.append(f"\n--- Content ({lang.upper()}) ---")
            if summary:
                parts.append(f"Learner summary: {summary}")
            if defn:
                parts.append(f"Definition: {defn}")
            if hero:
                parts.append(f"Hero News Context:\n{hero}")
            if basic:
                parts.append(f"Body (Basic):\n{basic}")
            if advanced:
                parts.append(f"Body (Advanced):\n{advanced}")
            if refs:
                refs_json = json.dumps(refs, ensure_ascii=False, indent=2)
                parts.append(f"References:\n{refs_json[:2000]}")
    return "\n".join(p for p in parts if p is not None)


def _build_handbook_classification_context(
    req: HandbookAdviseRequest,
    article_context: str = "",
) -> str:
    """Build a short context snippet for planner-style type classification."""
    parts = []
    if req.definition_ko:
        parts.append(f"Definition KO: {req.definition_ko[:400]}")
    if req.definition_en:
        parts.append(f"Definition EN: {req.definition_en[:400]}")
    if req.body_basic_ko:
        parts.append(f"Basic KO excerpt: {req.body_basic_ko[:500]}")
    if req.body_basic_en:
        parts.append(f"Basic EN excerpt: {req.body_basic_en[:500]}")
    if article_context:
        parts.append(f"Source article excerpt: {article_context[:800]}")
    return "\n".join(parts)[:1800]


def _build_translate_user_prompt(req: HandbookAdviseRequest) -> tuple[str, str, str]:
    """Build translate prompt. Returns (user_prompt, source_lang, target_lang)."""
    # Determine source language (whichever has more content)
    ko_content = " ".join(filter(None, [
        req.definition_ko, req.body_basic_ko, req.body_advanced_ko,
    ]))
    en_content = " ".join(filter(None, [
        req.definition_en, req.body_basic_en, req.body_advanced_en,
    ]))

    # Allow forced direction override
    if req.force_direction == "ko2en":
        force_source, force_target = "ko", "en"
    elif req.force_direction == "en2ko":
        force_source, force_target = "en", "ko"
    else:
        force_source, force_target = "", ""

    if force_source:
        source_lang, target_lang = force_source, force_target
    elif len(ko_content) >= len(en_content):
        source_lang, target_lang = "ko", "en"
    else:
        source_lang, target_lang = "en", "ko"

    if source_lang == "ko":
        fields = {
            "definition": req.definition_ko,
            "body_basic": req.body_basic_ko,
            "body_advanced": req.body_advanced_ko,
        }
    else:
        fields = {
            "definition": req.definition_en,
            "body_basic": req.body_basic_en,
            "body_advanced": req.body_advanced_en,
        }

    parts = [
        f"Term: {req.term}",
        f"Translate from {source_lang.upper()} to {target_lang.upper()}",
        "",
    ]
    for field_name, value in fields.items():
        if value:
            parts.append(f"## {field_name}\n{value}")
    return "\n".join(parts), source_lang, target_lang


async def run_handbook_advise(req: HandbookAdviseRequest) -> tuple[dict, str, int, list[str]]:
    """Run a handbook advisor action. Returns (result, model, tokens, warnings)."""
    client = get_openai_client()
    model = getattr(settings, "openai_model_main")

    if req.action == "related_terms":
        data, model, tokens = await _run_related_terms(req, client, model)
        return data, model, tokens, []
    elif req.action == "translate":
        data, model, tokens = await _run_translate(req, client, model)
        return data, model, tokens, []
    elif req.action == "generate":
        data, usage, warnings = await _run_generate_term(req, client, model)
        return data, usage.get("model_used", model), usage.get("tokens_used", 0), warnings
    elif req.action in ("factcheck", "deepverify"):
        # Reuse news editor's factcheck/deepverify with handbook content
        content_parts = [
            f"Term: {req.term}",
            f"Definition (KO): {req.definition_ko}" if req.definition_ko else "",
            f"Definition (EN): {req.definition_en}" if req.definition_en else "",
            f"Body Basic (KO):\n{req.body_basic_ko}" if req.body_basic_ko else "",
            f"Body Basic (EN):\n{req.body_basic_en}" if req.body_basic_en else "",
            f"Body Advanced (KO):\n{req.body_advanced_ko}" if req.body_advanced_ko else "",
            f"Body Advanced (EN):\n{req.body_advanced_en}" if req.body_advanced_en else "",
        ]
        content = "\n\n".join(p for p in content_parts if p)
        fake_req = AiAdviseRequest(
            action=req.action, post_id="", title=req.term,
            content=content, category="study",
        )
        if req.action == "deepverify":
            data, model, tokens = await run_deep_verify(fake_req)
        else:
            data, model, tokens = await run_advise(fake_req)
        return data, model, tokens, []
    else:
        raise ValueError(f"Unknown handbook action: {req.action}")


async def _run_related_terms(req: HandbookAdviseRequest, client, model: str) -> tuple[dict, str, int]:
    """Get related terms via LLM + Exa semantic search + DB matching."""
    user_prompt = _build_handbook_user_prompt(req)

    # Step 1: LLM suggests related terms
    resp = await client.chat.completions.create(
        **compat_create_kwargs(
            model,
            messages=[
                {"role": "system", "content": RELATED_TERMS_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=2048,
            prompt_cache_key="hb-related-terms",
        )
    )
    data = parse_ai_json(resp.choices[0].message.content, "Handbook-related_terms")
    tokens = resp.usage.completion_tokens if resp.usage else 0

    related = data.get("related_terms", [])

    # Step 2: Exa semantic search for additional terms (if configured)
    if settings.exa_api_key and req.term:
        try:
            from exa_py import Exa
            exa = Exa(api_key=settings.exa_api_key)
            loop = asyncio.get_running_loop()
            # Build context-aware query using definition if available
            definition = req.definition_en or req.definition_ko or ""
            exa_query = f"{req.term}: {definition[:200]}" if definition else f"technical concepts related to {req.term} in AI and software engineering"
            exa_results = await loop.run_in_executor(
                None,
                lambda: exa.search(
                    exa_query,
                    num_results=5,
                    type="neural",
                ),
            )
            # Extract terms from Exa results and merge with LLM suggestions
            existing_terms = {r["term"].lower() for r in related}
            for result in exa_results.results:
                title = result.title or ""
                # Use short titles as potential term names
                if title and len(title) < 60 and title.lower() not in existing_terms:
                    related.append({
                        "term": title,
                        "reason": f"Discovered via semantic search — related to {req.term}",
                    })
                    existing_terms.add(title.lower())
        except Exception as e:
            logger.warning("Exa search failed for related terms: %s", e)

    # Step 3: Check DB for existing terms
    supabase = get_supabase()
    for item in related:
        term_name = item.get("term", "")
        if not term_name:
            continue
        try:
            # Search by term name (exact ILIKE)
            result = supabase.table("handbook_terms").select("slug").ilike("term", term_name).limit(1).execute()
            if not result.data:
                # Also try korean_name
                result = supabase.table("handbook_terms").select("slug").ilike("korean_name", term_name).limit(1).execute()
            if result.data:
                item["exists_in_db"] = True
                item["slug"] = result.data[0]["slug"]
            else:
                item["exists_in_db"] = False
                item["slug"] = ""
        except Exception as e:
            logger.warning("DB lookup failed for term '%s': %s", term_name, e)
            item["exists_in_db"] = False
            item["slug"] = ""

    data["related_terms"] = related

    try:
        RelatedTermsResult.model_validate(data)
    except ValidationError as e:
        logger.warning("Handbook related_terms validation soft-fail: %s", e)

    return data, model, tokens


async def _run_translate(req: HandbookAdviseRequest, client, model: str) -> tuple[dict, str, int]:
    """Translate handbook term content between KO and EN."""
    user_prompt, source_lang, target_lang = _build_translate_user_prompt(req)

    resp = await client.chat.completions.create(
        **compat_create_kwargs(
            model,
            messages=[
                {"role": "system", "content": TRANSLATE_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=4096,
            prompt_cache_key="hb-translate",
        )
    )
    data = parse_ai_json(resp.choices[0].message.content, "Handbook-translate")
    tokens = resp.usage.completion_tokens if resp.usage else 0

    data["source_lang"] = source_lang
    data["target_lang"] = target_lang

    try:
        TranslateResult.model_validate(data)
    except ValidationError as e:
        logger.warning("Handbook translate validation soft-fail: %s", e)

    return data, model, tokens


CATEGORY_SEARCH_QUERIES: dict[str, str] = {
    "cs-fundamentals": "{term} tutorial documentation site:developer.mozilla.org OR site:geeksforgeeks.org",
    "math-statistics": "{term} mathematical definition proof statistics Khan Academy OR textbook",
    "ml-fundamentals": "{term} machine learning algorithm sklearn tutorial explained",
    "deep-learning": "{term} neural network architecture paper explained",
    "llm-genai": "{term} large language model generative AI explained",
    "data-engineering": "{term} data pipeline architecture documentation",
    "infra-hardware": "{term} infrastructure GPU deployment benchmark documentation",
    "safety-ethics": "{term} AI safety alignment regulation explained",
    "products-platforms": "{term} official documentation API release notes",
}


SURFACE_EVIDENCE_HINTS: dict[str, dict[str, str]] = {
    "tavily": {
        "paper": "research paper explained",
        "docs": "official docs guide overview",
        "benchmark": "performance benchmark comparison",
        "community": "practical examples tutorial",
        "code": "github examples tutorial",
    },
    "brave": {
        "paper": "site:arxiv.org OR site:paperswithcode.com",
        "docs": "site:docs.* OR site:developer.* OR official documentation",
        "benchmark": "benchmark pricing performance",
        "community": "site:github.com OR site:stackoverflow.com",
        "code": "site:github.com examples",
    },
    "exa": {
        "paper": "research paper deep explanation",
        "docs": "official docs architecture deep dive",
        "benchmark": "benchmark analysis workload comparison",
        "community": "practical architecture walkthrough",
        "code": "implementation deep dive",
    },
}

INTENT_QUERY_HINTS: dict[str, str] = {
    "understand": "explained clearly how it works",
    "compare": "alternatives comparison tradeoffs",
    "build": "implementation architecture usage",
    "debug": "failure modes troubleshooting mitigation",
    "evaluate": "measurement interpretation limitations",
}


def _build_type_aware_search_query(
    term: str,
    categories: list[str] | None,
    term_type: str,
    subtype: str | None,
    surface: str,
    intent: str = "understand",
) -> str:
    """Build a retrieval query that blends category framing with type-aware evidence needs."""
    from services.agents.prompts_handbook_types import get_evidence_priorities, get_type_query_focus

    primary_category = categories[0] if categories else ""
    category_template = (
        CATEGORY_SEARCH_QUERIES.get(primary_category)
        if surface == "tavily"
        else BRAVE_CATEGORY_QUERIES.get(primary_category)
        if surface == "brave"
        else None
    )
    base = category_template.format(term=term) if category_template else term

    evidence_priorities = get_evidence_priorities(term_type, subtype)
    evidence_hints = SURFACE_EVIDENCE_HINTS.get(surface, SURFACE_EVIDENCE_HINTS["tavily"])
    source_terms = " ".join(evidence_hints.get(item, item) for item in evidence_priorities[:2])
    focus = get_type_query_focus(term_type, subtype)
    intent_hint = INTENT_QUERY_HINTS.get(intent, INTENT_QUERY_HINTS["understand"])

    if surface == "exa" and "paper" in evidence_priorities[:2]:
        return f"{term} {focus} {intent_hint} research paper deep explanation"
    return f"{base} {focus} {intent_hint} {source_terms}".strip()


async def _search_term_context(
    term: str,
    categories: list[str] | None = None,
    term_type: str = "foundational_concept",
    subtype: str | None = None,
    intent: str = "understand",
) -> str:
    """Search web for term context using Tavily. Category-aware queries."""
    if not settings.tavily_api_key:
        return ""
    try:
        query = _build_type_aware_search_query(term, categories, term_type, subtype, "tavily", intent)

        tavily = TavilyClient(api_key=settings.tavily_api_key)
        loop = asyncio.get_running_loop()
        results = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: tavily.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5,
                    include_raw_content=False,
                ),
            ),
            timeout=30,
        )
        if not results.get("results"):
            return ""
        parts = []
        for i, r in enumerate(results["results"], 1):
            title = r.get("title", "")
            url = r.get("url", "")
            content = r.get("content", "")[:1500]
            parts.append(f"### [{i}] {title}\nURL: {url}\n{content}")
        return "## Reference Materials (from web search)\n\n" + "\n\n".join(parts)
    except Exception as e:
        logger.warning("Tavily search failed for '%s': %s", term, e)
        return ""


BRAVE_CATEGORY_QUERIES: dict[str, str] = {
    "cs-fundamentals": "{term} site:stackoverflow.com OR site:developer.mozilla.org tutorial",
    "math-statistics": "{term} site:mathworld.wolfram.com OR site:en.wikipedia.org mathematical definition",
    "ml-fundamentals": "{term} site:scikit-learn.org OR site:github.com machine learning implementation",
    "deep-learning": "{term} site:arxiv.org OR site:github.com neural network implementation",
    "llm-genai": "{term} site:huggingface.co OR site:github.com large language model",
    "data-engineering": "{term} site:github.com OR site:docs.databricks.com data pipeline",
    "infra-hardware": "{term} site:developer.nvidia.com OR site:kubernetes.io documentation",
    "safety-ethics": "{term} AI safety alignment site:arxiv.org OR site:openai.com",
    "products-platforms": "{term} official documentation site:docs.* OR site:github.com",
}


async def _search_brave_context(
    term: str,
    categories: list[str] | None = None,
    term_type: str = "foundational_concept",
    subtype: str | None = None,
    intent: str = "understand",
) -> str:
    """Search Brave for developer-focused references (docs, GitHub, SO)."""
    if not settings.brave_api_key:
        return ""
    try:
        import httpx

        query = _build_type_aware_search_query(term, categories, term_type, subtype, "brave", intent)

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 5},
                headers={"X-Subscription-Token": settings.brave_api_key, "Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = data.get("web", {}).get("results", [])
        if not results:
            return ""
        parts = []
        for i, r in enumerate(results[:5], 1):
            title = r.get("title", "")
            url = r.get("url", "")
            desc = r.get("description", "")[:800]
            parts.append(f"### [{i}] {title}\nURL: {url}\n{desc}")
        return "## Developer Reference Materials (from Brave Search)\n\n" + "\n\n".join(parts)
    except Exception as e:
        logger.warning("Brave search failed for '%s': %s", term, e)
        return ""


async def _search_deep_context(
    term: str,
    categories: list[str] | None = None,
    term_type: str = "foundational_concept",
    subtype: str | None = None,
    intent: str = "understand",
) -> str:
    """Search Exa for deep term context (full text). Used for Advanced content generation."""
    if not settings.exa_api_key:
        return ""
    try:
        from exa_py import Exa
        exa = Exa(api_key=settings.exa_api_key)
        loop = asyncio.get_running_loop()
        query = _build_type_aware_search_query(term, categories, term_type, subtype, "exa", intent)
        results = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: exa.search_and_contents(
                    query,
                    type="auto",
                    num_results=3,
                    text={"max_characters": 10000},
                ),
            ),
            timeout=20,
        )
        if not hasattr(results, "results") or not results.results:
            # Retry without category restriction
            results = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: exa.search_and_contents(
                        f"{term} {query} in depth",
                        type="auto",
                        num_results=3,
                        text={"max_characters": 10000},
                    ),
                ),
                timeout=20,
            )
        if not hasattr(results, "results") or not results.results:
            return ""
        parts = []
        for i, r in enumerate(results.results, 1):
            title = r.title or ""
            url = r.url or ""
            text = (r.text or "")[:8000]
            parts.append(f"### [{i}] {title}\nURL: {url}\n{text}")
        context = "## Deep Reference Materials (from Exa full text)\n\n" + "\n\n".join(parts)
        logger.info("Exa deep context for '%s': %d results, %d chars", term, len(results.results), len(context))
        return context
    except ImportError:
        logger.warning("exa_py not installed, skipping deep context")
        return ""
    except Exception as e:
        logger.warning("Exa deep search failed for '%s': %s", term, e)
        return ""


async def _classify_term_type(
    term: str,
    categories: list[str],
    context_snippet: str,
    client,
    model_light: str,
    term_type_hint: str = "",
) -> tuple[str, str | None, list[str], str, float]:
    """Classify term type + intent + volatility before retrieval and generation."""
    from services.agents.prompts_handbook_types import (
        CLASSIFY_TERM_PROMPT, TERM_TYPES,
        TYPE_SUBTYPE_VALUES, normalize_term_subtype,
        INTENT_VALUES, VOLATILITY_VALUES,
        DEFAULT_INTENT_BY_TYPE, DEFAULT_VOLATILITY_BY_TYPE,
        get_term_planner_override,
    )

    override = get_term_planner_override(term)
    if override:
        term_type = str(override["type"])
        subtype = normalize_term_subtype(term_type, override.get("subtype"))
        intents = [i for i in override.get("intent", DEFAULT_INTENT_BY_TYPE[term_type]) if i in INTENT_VALUES]
        volatility = str(override.get("volatility", DEFAULT_VOLATILITY_BY_TYPE[term_type]))
        return term_type, subtype, intents or ["understand"], volatility, 1.0

    hinted_type = str(term_type_hint or "").strip()
    if hinted_type in TERM_TYPES:
        return (
            hinted_type,
            None,
            DEFAULT_INTENT_BY_TYPE.get(hinted_type, ["understand"]),
            DEFAULT_VOLATILITY_BY_TYPE.get(hinted_type, "stable"),
            1.0,
        )

    user_msg = (
        f"Term: {term}\n"
        f"Categories: {', '.join(categories)}\n"
        f"Context:\n{context_snippet or 'No extra context.'}"
    )
    try:
        resp = await client.chat.completions.create(
            **compat_create_kwargs(
                model_light,
                messages=[
                    {"role": "system", "content": CLASSIFY_TERM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=200,
                response_format={"type": "json_object"},
                prompt_cache_key="hb-classify",
            )
        )
        data = parse_ai_json(resp.choices[0].message.content, "term-classify")

        term_type = data.get("type", "foundational_concept")
        if term_type not in TERM_TYPES:
            term_type = "foundational_concept"
        subtype = normalize_term_subtype(term_type, data.get("subtype"))
        if term_type not in TYPE_SUBTYPE_VALUES:
            subtype = None

        raw_intent = data.get("intent", DEFAULT_INTENT_BY_TYPE.get(term_type, ["understand"]))
        if isinstance(raw_intent, str):
            raw_intent = [raw_intent]
        intent_list = [i for i in raw_intent if i in INTENT_VALUES] or ["understand"]

        volatility = data.get("volatility", DEFAULT_VOLATILITY_BY_TYPE.get(term_type, "stable"))
        if volatility not in VOLATILITY_VALUES:
            volatility = DEFAULT_VOLATILITY_BY_TYPE.get(term_type, "stable")

        confidence = data.get("confidence", 0.5)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        return term_type, subtype, intent_list, volatility, confidence
    except Exception as e:
        logger.warning("Term classification failed for '%s': %s", term, e)
        return "foundational_concept", None, ["understand"], "stable", 0.0


async def _self_critique_advanced(
    term: str, term_type: str, advanced_content: str,
    client, model: str,
    reference_context: str = "",
) -> tuple[bool, str, int, dict]:
    """CoVe-style self-critique: verify claims against references + depth check."""
    from services.agents.prompts_handbook_types import COVE_CRITIQUE_PROMPT, SELF_CRITIQUE_PROMPT

    reasoning_model = settings.openai_model_reasoning  # gpt-5-mini for critique
    # Use CoVe when reference context is available, fall back to legacy otherwise
    if reference_context:
        system = COVE_CRITIQUE_PROMPT.format(
            term=term, term_type=term_type,
            reference_context=reference_context[:3000],
        )
    else:
        system = SELF_CRITIQUE_PROMPT.format(term=term, term_type=term_type)
    try:
        resp = await client.chat.completions.create(
            **build_completion_kwargs(
                model=reasoning_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": advanced_content[:8000]},
                ],
                max_tokens=2000,
                response_format={"type": "json_object"},
                prompt_cache_key="hb-critique-advanced",
                service_tier="flex",
            )
        )
        data = parse_ai_json(resp.choices[0].message.content, "self-critique")
        needs = data.get("needs_improvement", False)
        score = data.get("score", 50)
        feedback = ""
        if needs and data.get("improvements"):
            feedback = "\n".join(
                f"- {imp['section']}: {imp['suggestion']}"
                for imp in data["improvements"]
            )
        usage = extract_usage_metrics(resp, reasoning_model, requested_service_tier="flex")
        return needs, feedback, score, usage
    except Exception as e:
        logger.warning("Self-critique failed for '%s': %s", term, e)
        return False, "", 50, {}


_CODE_FENCE_RE = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)
_SCHEMA_DOLLAR_RE = re.compile(r"(?<![`$])\$(ref|defs|schema)\b")
_MIXED_SCRIPT_ARTIFACT_RE = re.compile(r"[\uac00-\ud7a3][语义汉简体][\uac00-\ud7a3]|[\uac00-\ud7a3][语义汉简体]|[语义汉简体][\uac00-\ud7a3]")
_HIGH_RISK_REFERENCE_CLAIM_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    r"NVIDIA|"
    r"Kimi(?:-[A-Za-z0-9]+)+|"
    r"Sonnet\s+\d+(?:\.\d+)?|"
    r"Claude\s+\d+(?:\.\d+)?|"
    r"Gemini\s+\d+(?:\.\d+)?|"
    r"GPT-\d+(?:\.\d+)?|"
    r"F1\s+\d+(?:\.\d+)?%"
    r")(?![A-Za-z0-9])",
    re.IGNORECASE,
)


def _extract_markdown_code_fences(markdown: str) -> list[dict[str, str]]:
    fences: list[dict[str, str]] = []
    for match in _CODE_FENCE_RE.finditer(markdown or ""):
        fences.append({
            "language": (match.group(1) or "").strip(),
            "body": match.group(2) or "",
        })
    return fences


def _transform_outside_code_fences(text: str, transform) -> str:
    if "```" not in text:
        return transform(text)
    parts = re.split(r"(```.*?```)", text, flags=re.DOTALL)
    return "".join(part if part.startswith("```") else transform(part) for part in parts)


def _sanitize_schema_dollar_identifiers(text: str) -> str:
    """Render JSON Schema identifiers as inline code, not single-dollar math."""
    if "$" not in (text or ""):
        return text

    def _replace(part: str) -> str:
        return _SCHEMA_DOLLAR_RE.sub(lambda m: f"`${m.group(1)}`", part)

    return _transform_outside_code_fences(text, _replace)


def _validate_python_code_fences(markdown: str) -> list[str]:
    """Return warnings for fenced Python snippets that do not parse."""
    import ast

    warnings: list[str] = []
    for idx, fence in enumerate(_extract_markdown_code_fences(markdown), start=1):
        language = fence["language"].lower()
        if language not in {"python", "py"} and not language.startswith("python "):
            continue
        try:
            ast.parse(fence["body"])
        except SyntaxError as exc:
            detail = f"{exc.msg} at line {exc.lineno}" if exc.lineno else exc.msg
            warnings.append(f"invalid Python code fence {idx}: {detail}")
    return warnings


def _detect_mixed_script_artifacts(text: str) -> list[str]:
    """Detect likely CJK mojibake/artifacts embedded inside Korean prose."""
    warnings: list[str] = []
    for match in _MIXED_SCRIPT_ARTIFACT_RE.finditer(text or ""):
        start = max(0, match.start() - 20)
        end = min(len(text), match.end() + 20)
        snippet = text[start:end].replace("\n", " ")
        warnings.append(f"mixed-script artifact near '{snippet}'")
    return warnings


def _normalize_reference_claim_text(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _reference_claim_blob(data: dict) -> str:
    parts: list[str] = []
    for locale in ("ko", "en"):
        refs = data.get(f"references_{locale}") or []
        if not isinstance(refs, list):
            continue
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            for key in ("title", "authors", "venue", "type", "url", "annotation"):
                value = ref.get(key)
                if value:
                    parts.append(str(value))
    return _normalize_reference_claim_text(" ".join(parts))


def _detect_unsupported_reference_claims(data: dict) -> list[str]:
    """Warn when high-risk named/version/metric claims do not appear in final refs."""
    reference_blob = _reference_claim_blob(data)
    if not reference_blob:
        return []

    text = "\n".join(
        str(data.get(field) or "")
        for field in (
            "summary_ko",
            "summary_en",
            "definition_ko",
            "definition_en",
            "body_basic_ko",
            "body_basic_en",
            "body_advanced_ko",
            "body_advanced_en",
            "hero_news_context_ko",
            "hero_news_context_en",
        )
    )
    warnings: list[str] = []
    seen: set[str] = set()
    for match in _HIGH_RISK_REFERENCE_CLAIM_RE.finditer(text):
        claim = match.group(0).strip()
        claim_key = _normalize_reference_claim_text(claim)
        if not claim_key or claim_key in seen:
            continue
        seen.add(claim_key)
        if claim_key not in reference_blob:
            warnings.append(
                f"unsupported reference claim: '{claim}' is not present in final references"
            )
    return warnings


def _apply_handbook_safety_postprocess(data: dict) -> list[str]:
    warnings: list[str] = []
    text_fields = (
        "summary_ko",
        "summary_en",
        "definition_ko",
        "definition_en",
        "body_basic_ko",
        "body_basic_en",
        "body_advanced_ko",
        "body_advanced_en",
        "hero_news_context_ko",
        "hero_news_context_en",
    )
    for field in text_fields:
        value = data.get(field)
        if not isinstance(value, str) or not value:
            continue
        sanitized = _sanitize_schema_dollar_identifiers(value)
        if sanitized != value:
            data[field] = sanitized
            value = sanitized
            warnings.append(f"{field}: escaped JSON Schema dollar identifiers")
        for warning in _validate_python_code_fences(value):
            warnings.append(f"{field}: {warning}")
        for warning in _detect_mixed_script_artifacts(value):
            warnings.append(f"{field}: {warning}")
    warnings.extend(_detect_unsupported_reference_claims(data))
    return warnings


_HANDBOOK_TEXT_FIELDS = (
    "summary_ko",
    "summary_en",
    "definition_ko",
    "definition_en",
    "body_basic_ko",
    "body_basic_en",
    "body_advanced_ko",
    "body_advanced_en",
    "hero_news_context_ko",
    "hero_news_context_en",
)

_CONTEXT_WINDOW_CODE_CONTRACT = (
    "preflight_budget",
    "reserve_output_tokens",
    "compact_history",
    "fail_fast",
)

_RELATED_TAGS_BY_LOCALE = {
    "ko": {"선행", "대안", "확장"},
    "en": {"prerequisite", "alternative", "extension"},
}

_RELATED_TAG_MAP_BY_LOCALE = {
    "ko": {
        "prerequisites": "선행",
        "alternatives": "대안",
        "extensions": "확장",
    },
    "en": {
        "prerequisites": "prerequisite",
        "alternatives": "alternative",
        "extensions": "extension",
    },
}

_INTERNAL_RELATED_PATTERNS_BY_TERM = {
    "attention": (
        r"\bq\s*/\s*k\s*/\s*v\b",
        r"\bquery\s*/\s*key\s*/\s*value\b",
        r"\bq\s+k\s+v\b",
        r"\bquery\b",
        r"\bkey\b",
        r"\bvalue\b",
    ),
    "transformer": (
        r"\bresidual\s+connection\b",
        r"\blayer\s+norm(?:alization)?\b",
        r"\bposition-wise\s+ffn\b",
        r"\bfeed[-\s]?forward\s+network\b",
    ),
    "adam": (
        r"\bfirst\s+moment\b",
        r"\bsecond\s+moment\b",
        r"\brunning\s+average\b",
        r"\bmoment\s+estimat",
    ),
    "cuda": (
        r"\bcuda\s+kernel\b",
        r"\bthread\s+block\b",
        r"\bwarp\b",
        r"\bgrid\s+dimension\b",
    ),
}


def _extract_warning_claim(warning: str) -> str:
    match = re.search(r"unsupported reference claim: '([^']+)'", warning or "")
    return match.group(1) if match else ""


def _find_text_field_containing(data: dict, needle: str) -> str:
    if not needle:
        return ""
    needle_lower = needle.lower()
    for field in _HANDBOOK_TEXT_FIELDS:
        value = data.get(field)
        if isinstance(value, str) and needle_lower in value.lower():
            return field
    return ""


def _make_remediation_issue(
    code: str,
    severity: str,
    section: str = "",
    locale: str = "",
    message: str = "",
    suggested_action: str = "",
    evidence: object | None = None,
) -> dict:
    return {
        "code": code,
        "severity": severity,
        "section": section,
        "locale": locale,
        "message": message,
        "suggested_action": suggested_action,
        "evidence": evidence,
    }


def _extract_python_function_names(markdown: str) -> set[str]:
    names: set[str] = set()
    for fence in _extract_markdown_code_fences(markdown or ""):
        body = fence["body"]
        names.update(re.findall(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", body, flags=re.MULTILINE))
    return names


def _required_code_contract_keywords(data: dict) -> tuple[str, ...]:
    term_text = " ".join(
        str(data.get(field) or "")
        for field in ("term", "term_full", "korean_full")
    ).lower()
    code_text = "\n".join(
        fence["body"]
        for field in ("body_advanced_ko", "body_advanced_en")
        for fence in _extract_markdown_code_fences(str(data.get(field) or ""))
    ).lower()
    # Only the Context Window term has this exact required contract. Other
    # terms can legitimately reuse helper names such as preflight_budget or
    # compact_history without promising the whole context-window budget model.
    if "context window" in term_text or all(
        keyword in code_text for keyword in _CONTEXT_WINDOW_CODE_CONTRACT
    ):
        return _CONTEXT_WINDOW_CODE_CONTRACT
    return ()


def _primary_category_from_content(data: dict) -> str | None:
    categories = data.get("categories")
    if isinstance(categories, list):
        return str(categories[0]).strip() if categories else None
    if isinstance(categories, str):
        return categories.strip() or None
    return None


def _effective_code_mode_hint(data: dict) -> str:
    explicit = str(data.get("code_mode_hint") or "").strip()
    if explicit:
        return explicit

    term_type = str(data.get("term_type") or "").strip()
    term_subtype = str(data.get("term_subtype") or "").strip() or None
    reference_strength = str(data.get("reference_strength") or "")
    code_mode = decide_code_mode(
        term_type,
        term_subtype,
        reference_strength,
        bool(data.get("has_clear_io_contract")),
        bool(data.get("has_official_spec_signal")),
        bool(data.get("insufficient_info_flag")),
    )

    try:
        from services.agents.prompts_handbook_types import get_artifact_policy

        artifact_policy = get_artifact_policy(
            term_type,
            term_subtype,
            _primary_category_from_content(data),
        )
        if artifact_policy.get("code_mode") == "no-code":
            return "no-code"
    except Exception:
        pass
    return code_mode


def _detect_code_isomorphism_issues(data: dict) -> list[dict]:
    code_mode = _effective_code_mode_hint(data)
    if code_mode == "no-code":
        return []

    ko_body = str(data.get("body_advanced_ko") or "")
    en_body = str(data.get("body_advanced_en") or "")
    ko_fences = _extract_markdown_code_fences(ko_body)
    en_fences = _extract_markdown_code_fences(en_body)
    if not ko_fences and not en_fences:
        return []

    required = _required_code_contract_keywords(data)
    ko_text = "\n".join(fence["body"] for fence in ko_fences)
    en_text = "\n".join(fence["body"] for fence in en_fences)
    ko_missing = [keyword for keyword in required if keyword not in ko_text]
    en_missing = [keyword for keyword in required if keyword not in en_text]
    ko_funcs = _extract_python_function_names(ko_body)
    en_funcs = _extract_python_function_names(en_body)
    function_overlap_ok = True
    if ko_funcs or en_funcs:
        shared = ko_funcs & en_funcs
        larger = max(len(ko_funcs), len(en_funcs), 1)
        function_overlap_ok = (len(shared) / larger) >= 0.5

    if len(ko_fences) != len(en_fences) or ko_missing or en_missing or not function_overlap_ok:
        return [
            _make_remediation_issue(
                "code_not_isomorphic",
                "high",
                "adv_ko_3_code,adv_en_3_code",
                "",
                "KO/EN code sections do not describe the same system contract.",
                "Rewrite both code sections from the same contract.",
                {
                    "ko_missing": ko_missing,
                    "en_missing": en_missing,
                    "ko_functions": sorted(ko_funcs),
                    "en_functions": sorted(en_funcs),
                    "ko_fences": len(ko_fences),
                    "en_fences": len(en_fences),
                },
            )
        ]
    return []


def _detect_provider_drift_issue(data: dict) -> list[dict]:
    term_text = f"{data.get('term_full', '')} {data.get('korean_full', '')}".lower()
    if "context window" not in term_text and "context window" not in str(data.get("body_advanced_en", "")).lower():
        return []
    combined = f"{data.get('body_advanced_ko', '')}\n{data.get('body_advanced_en', '')}".lower()
    provider_markers = ("extended thinking", "tool_result", "signed thinking", "kimi", "sonnet")
    core_markers = ("token budget", "truncation", "compaction", "rag", "attention cost")
    provider_hits = [marker for marker in provider_markers if marker in combined]
    core_hits = [marker for marker in core_markers if marker in combined]
    if len(provider_hits) >= 2 and len(core_hits) < 2:
        return [
            _make_remediation_issue(
                "advanced_provider_drift",
                "medium",
                "body_advanced_ko,body_advanced_en",
                "",
                "Advanced content is drifting toward provider-specific examples instead of core mechanism.",
                "Refocus advanced sections on token budget, truncation, compaction, RAG tradeoff, and attention cost.",
                {"provider_hits": provider_hits, "core_hits": core_hits},
            )
        ]
    return []


def _detect_markdown_structure_issues(data: dict) -> list[dict]:
    issues: list[dict] = []
    for field in ("body_basic_ko", "body_basic_en", "body_advanced_ko", "body_advanced_en"):
        text = str(data.get(field) or "")
        if not text:
            continue
        inline_headings = len(re.findall(r"(?<!\n)\s##\s+", text))
        glued_code_headings = len(re.findall(r"(?m)^##[^\n`]*```", text))
        if inline_headings or glued_code_headings:
            issues.append(
                _make_remediation_issue(
                    "markdown_structure_broken",
                    "high",
                    field,
                    "ko" if field.endswith("_ko") else "en",
                    "Markdown headings are not separated by line breaks.",
                    "Put every ## heading and every fenced code block on its own line.",
                    {
                        "inline_headings": inline_headings,
                        "glued_code_headings": glued_code_headings,
                    },
                )
            )
        h2_count = len(re.findall(r"(?m)^##\s+", text))
        if field.startswith("body_basic_") and h2_count and h2_count < 7:
            issues.append(
                _make_remediation_issue(
                    "basic_sections_incomplete",
                    "high",
                    field,
                    "ko" if field.endswith("_ko") else "en",
                    f"Basic body has {h2_count}/7 H2 sections.",
                    "Restore all 7 Basic sections with one H2 heading per section.",
                    {"h2_count": h2_count, "expected": 7},
                )
            )
        if field.startswith("body_advanced_"):
            locale = "ko" if field.endswith("_ko") else "en"
            expected = len(ADVANCED_SECTIONS_KO if locale == "ko" else ADVANCED_SECTIONS_EN)
            if h2_count and h2_count < expected:
                issues.append(
                    _make_remediation_issue(
                        "advanced_sections_incomplete",
                        "high",
                        field,
                        locale,
                        f"Advanced body has {h2_count}/{expected} H2 sections.",
                        "Restore every required Advanced section with one H2 heading per section.",
                        {"h2_count": h2_count, "expected": expected},
                    )
                )
    return issues


def _extract_h2_headings(markdown: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"(?m)^##\s+(.+?)\s*$", markdown or "")]


def _headers_from_sections(sections: list[tuple[str, str]]) -> list[str]:
    return [header.removeprefix("## ").strip() for _, header in sections]


def _detect_canonical_heading_issues(data: dict) -> list[dict]:
    issues: list[dict] = []
    expected_basic = {
        "ko": _headers_from_sections(BASIC_SECTIONS_KO),
        "en": _headers_from_sections(BASIC_SECTIONS_EN),
    }
    for locale in ("ko", "en"):
        field = f"body_basic_{locale}"
        headings = _extract_h2_headings(str(data.get(field) or ""))
        if headings and headings != expected_basic[locale]:
            issues.append(
                _make_remediation_issue(
                    "basic_heading_shape_invalid",
                    "high",
                    field,
                    locale,
                    "Basic section headings do not match the canonical handbook shape.",
                    "Restore the exact Basic H2 headings and order; rewrite content under those headings only.",
                    {"actual": headings, "expected": expected_basic[locale]},
                )
            )

        field = f"body_advanced_{locale}"
        headings = _extract_h2_headings(str(data.get(field) or ""))
        advanced_sections = _advanced_sections_for_mode(
            locale,
            _effective_code_mode_hint(data),
            data.get("term_type"),
            data.get("term_subtype"),
        )
        expected_advanced = _headers_from_sections(advanced_sections)
        expected_without_specs = _headers_from_sections(
            [(key, header) for key, header in advanced_sections if not key.endswith("_specs")]
        )
        allowed_shapes = [expected_advanced]
        if expected_without_specs != expected_advanced:
            allowed_shapes.append(expected_without_specs)
        if headings and headings not in allowed_shapes:
            issues.append(
                _make_remediation_issue(
                    "advanced_heading_shape_invalid",
                    "high",
                    field,
                    locale,
                    "Advanced section headings do not match the canonical handbook shape.",
                    "Restore the exact Advanced H2 headings and order; rewrite content under those headings only.",
                    {"actual": headings, "expected": expected_advanced, "allowed": allowed_shapes},
                )
            )
    return issues


def _normalize_related_term_name(value: str) -> str:
    text = (value or "").lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^0-9a-z가-힣]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _self_related_names(data: dict) -> set[str]:
    names: set[str] = set()
    for field in ("term", "term_full", "korean_name", "korean_full"):
        value = str(data.get(field) or "").strip()
        if not value:
            continue
        for part in [value, *re.findall(r"\(([^)]+)\)", value)]:
            normalized = _normalize_related_term_name(part)
            if normalized:
                names.add(normalized)
        normalized_without_parenthetical = _normalize_related_term_name(re.sub(r"\([^)]*\)", "", value))
        if normalized_without_parenthetical:
            names.add(normalized_without_parenthetical)
    return names


def _term_family_keys(data: dict) -> set[str]:
    keys: set[str] = set()
    for name in _self_related_names(data):
        if name:
            keys.add(name)
        if "attention" in name or "어텐션" in name:
            keys.add("attention")
        if "transformer" in name or "트랜스포머" in name:
            keys.add("transformer")
        if name == "adam" or "adam optimizer" in name:
            keys.add("adam")
        if name == "cuda" or "쿠다" in name:
            keys.add("cuda")
    return keys


def _extract_related_section(markdown: str, locale: str) -> str:
    headings = (
        ("선행·대안·확장 개념", "선행", "대안", "확장")
        if locale == "ko"
        else ("Prerequisites, Alternatives, and Extensions",)
    )
    lines = (markdown or "").splitlines()
    collecting = False
    collected: list[str] = []
    for line in lines:
        if line.startswith("## "):
            title = line.removeprefix("## ").strip()
            if any(marker in title for marker in headings):
                collecting = True
                collected = []
                continue
            if collecting:
                break
        elif collecting:
            collected.append(line)
    return "\n".join(collected).strip()


def _parse_related_bullets(section: str) -> list[dict]:
    bullets: list[dict] = []
    pattern = re.compile(r"(?m)^-\s*\(([^)]+)\)\s+\*\*([^*]+)\*\*\s*(?:—|-|–)\s*(.+)$")
    for match in pattern.finditer(section or ""):
        bullets.append(
            {
                "tag": match.group(1).strip(),
                "term": match.group(2).strip(),
                "relationship": match.group(3).strip(),
            }
        )
    return bullets


def _is_internal_related_component(term: str, data: dict) -> bool:
    normalized = _normalize_related_term_name(term)
    if not normalized:
        return False
    for family in _term_family_keys(data):
        for pattern in _INTERNAL_RELATED_PATTERNS_BY_TERM.get(family, ()):
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                return True
    return False


def _detect_related_term_issues(data: dict) -> list[dict]:
    issues: list[dict] = []
    self_names = _self_related_names(data)
    for locale in ("ko", "en"):
        field = f"body_advanced_{locale}"
        section = _extract_related_section(str(data.get(field) or ""), locale)
        if not section:
            continue
        bullets = _parse_related_bullets(section)
        valid_tags = _RELATED_TAGS_BY_LOCALE[locale]
        seen_terms: set[str] = set()
        bad_terms: list[dict] = []
        bad_tags: list[str] = []
        for bullet in bullets:
            tag = bullet["tag"]
            term = bullet["term"]
            normalized = _normalize_related_term_name(term)
            if tag not in valid_tags:
                bad_tags.append(tag)
            if normalized and normalized in seen_terms:
                bad_terms.append({"term": term, "reason": "duplicate related term"})
            seen_terms.add(normalized)
            if normalized and normalized in self_names:
                bad_terms.append({"term": term, "reason": "alias or same term"})
            if _is_internal_related_component(term, data):
                bad_terms.append({"term": term, "reason": "internal component, not a related concept"})

        if bad_tags:
            issues.append(
                _make_remediation_issue(
                    "related_tag_mismatch",
                    "high",
                    f"adv_{locale}_7_related",
                    locale,
                    "Related section uses non-canonical category tags for this locale.",
                    "Use only the canonical related tags for this locale.",
                    {"tags": bad_tags, "expected": sorted(valid_tags)},
                )
            )
        if bad_terms:
            issues.append(
                _make_remediation_issue(
                    "related_term_rule_violation",
                    "high",
                    f"adv_{locale}_7_related",
                    locale,
                    "Related section contains aliases, duplicates, or internal components.",
                    "Replace them with separate prerequisite, alternative, or extension concepts.",
                    {"violations": bad_terms},
                )
            )
    return issues


def _dedupe_remediation_issues(issues: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()
    for issue in issues:
        evidence = issue.get("evidence") if isinstance(issue.get("evidence"), dict) else {}
        evidence_key = str(evidence.get("claim") or "") if issue.get("code") == "unsupported_reference_claim" else ""
        key = (
            str(issue.get("code") or ""),
            str(issue.get("section") or ""),
            str(issue.get("locale") or ""),
            evidence_key,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped


def _build_handbook_remediation_issues(data: dict, warnings: list[str]) -> list[dict]:
    issues: list[dict] = []
    definition_en = str(data.get("definition_en") or "")
    definition_ko = str(data.get("definition_ko") or "")
    if len(definition_en) > 480:
        issues.append(
            _make_remediation_issue(
                "definition_too_long",
                "medium",
                "definition_en",
                "en",
                f"definition_en has {len(definition_en)} chars; target ceiling is 480.",
                "Compress to one or two dense sentences.",
                {"chars": len(definition_en), "ceiling": 480},
            )
        )
    if len(definition_ko) > 260:
        issues.append(
            _make_remediation_issue(
                "definition_too_long",
                "medium",
                "definition_ko",
                "ko",
                f"definition_ko has {len(definition_ko)} chars; target ceiling is 260.",
                "Compress to one or two dense Korean sentences.",
                {"chars": len(definition_ko), "ceiling": 260},
            )
        )

    references_ko = data.get("references_ko") if isinstance(data.get("references_ko"), list) else []
    references_en = data.get("references_en") if isinstance(data.get("references_en"), list) else []
    reference_strength = str(data.get("reference_strength") or "").lower()
    ref_count = max(len(references_ko), len(references_en))
    primary_count = max(_count_primary_references(references_ko), _count_primary_references(references_en))
    ref_warning = any(re.search(r"refs_(?:ko|en):\s*\d+\s+items\s+<\s+3", warning or "") for warning in warnings or [])
    if reference_strength == "low" or ref_warning:
        try:
            from services.agents.prompts_handbook_types import get_term_generation_override

            term_candidates = (
                data.get("term"),
                data.get("term_full"),
                data.get("korean_full"),
                data.get("korean_name"),
            )
            has_override = any(get_term_generation_override(str(term or "")) for term in term_candidates)
        except Exception:
            has_override = False
        severity = "high" if has_override else "medium"
        issues.append(
            _make_remediation_issue(
                "weak_reference_set",
                severity,
                "references_ko,references_en",
                "",
                f"Reference set is too weak for admin-ready review: strength={reference_strength or 'unknown'}, refs={ref_count}, primary={primary_count}.",
                "Use curated/direct references or rerun source selection before considering publish review.",
                {
                    "reference_strength": reference_strength or "unknown",
                    "reference_count": ref_count,
                    "primary_count": primary_count,
                    "core_override_term": has_override,
                },
            )
        )

    for warning in warnings or []:
        claim = _extract_warning_claim(warning)
        if claim:
            issues.append(
                _make_remediation_issue(
                    "unsupported_reference_claim",
                    "high",
                    _find_text_field_containing(data, claim),
                    "",
                    warning,
                    "Remove the unsupported sentence or generalize it without adding new references.",
                    {"claim": claim},
                )
            )
        elif "invalid Python code fence" in warning:
            issues.append(
                _make_remediation_issue(
                    "invalid_code_fence",
                    "high",
                    _find_text_field_containing(data, "```python"),
                    "",
                    warning,
                    "Rewrite the affected code fence as valid Python or pseudocode.",
                )
            )
        elif "code capsule too large" in warning:
            issues.append(
                _make_remediation_issue(
                    "code_capsule_too_large",
                    "medium",
                    "body_advanced_ko,body_advanced_en",
                    "",
                    warning,
                    "Shorten the code capsule while preserving the same system model.",
                )
            )

    adv_ko = str(data.get("body_advanced_ko") or "")
    if re.search(r"\((prerequisite|alternative|extension)\)", adv_ko, flags=re.IGNORECASE):
        issues.append(
            _make_remediation_issue(
                "ko_related_tag_mismatch",
                "medium",
                "adv_ko_7_related",
                "ko",
                "KO related section uses English relation tags.",
                "Use Korean relation tags: (선행), (대안), (확장).",
            )
        )

    for locale in ("ko", "en"):
        body = str(data.get(f"body_advanced_{locale}") or "")
        for idx, fence in enumerate(_extract_markdown_code_fences(body), start=1):
            line_count = len([line for line in fence["body"].splitlines() if line.strip()])
            if len(fence["body"]) > 3500 or line_count > 55:
                issues.append(
                    _make_remediation_issue(
                        "code_capsule_too_large",
                        "medium",
                        f"body_advanced_{locale}",
                        locale,
                        f"adv_{locale} code fence {idx} has {len(fence['body'])} chars/{line_count} lines; target is one compact handbook-screen capsule.",
                        "Shorten the code capsule while preserving the same system model.",
                        {
                            "chars": len(fence["body"]),
                            "ceiling": 3500,
                            "lines": line_count,
                            "line_ceiling": 55,
                            "fence": idx,
                        },
                    )
                )

    issues.extend(_detect_code_isomorphism_issues(data))
    issues.extend(_detect_provider_drift_issue(data))
    issues.extend(_detect_markdown_structure_issues(data))
    issues.extend(_detect_canonical_heading_issues(data))
    issues.extend(_detect_related_term_issues(data))
    return _dedupe_remediation_issues(issues)


def _remove_claim_sentences_from_part(part: str, reference_blob: str) -> tuple[str, list[str]]:
    if not part:
        return part, []
    removed: list[str] = []
    pieces = re.split(r"(?<=[.!?。！？])\s+", part)
    kept: list[str] = []
    for piece in pieces:
        claims = []
        for match in _HIGH_RISK_REFERENCE_CLAIM_RE.finditer(piece):
            claim = match.group(0).strip()
            if _normalize_reference_claim_text(claim) not in reference_blob:
                claims.append(claim)
        if claims:
            removed.extend(claims)
            continue
        kept.append(piece)
    return " ".join(p for p in kept if p).strip(), removed


def _remove_unsupported_reference_claim_sentences(data: dict) -> list[str]:
    reference_blob = _reference_claim_blob(data)
    if not reference_blob:
        return []
    removed_claims: list[str] = []
    for field in _HANDBOOK_TEXT_FIELDS:
        value = data.get(field)
        if not isinstance(value, str) or not value:
            continue

        def _replace_code_fence_claims(match: re.Match) -> str:
            fence = match.group(0)
            updated = fence
            for claim_match in _HIGH_RISK_REFERENCE_CLAIM_RE.finditer(fence):
                claim = claim_match.group(0).strip()
                if _normalize_reference_claim_text(claim) in reference_blob:
                    continue
                removed_claims.append(claim)
                replacement = "your-model" if re.search(r"(gpt|claude|gemini|sonnet|kimi)", claim, re.IGNORECASE) else "supported-value"
                updated = updated.replace(claim, replacement)
            return updated

        value_with_code_generalized = re.sub(
            r"```.*?```",
            _replace_code_fence_claims,
            value,
            flags=re.DOTALL,
        )

        def _replace(part: str) -> str:
            cleaned, removed = _remove_claim_sentences_from_part(part, reference_blob)
            removed_claims.extend(removed)
            return cleaned

        cleaned_value = _transform_outside_code_fences(value_with_code_generalized, _replace)
        if cleaned_value != value:
            data[field] = cleaned_value
    deduped: list[str] = []
    seen: set[str] = set()
    for claim in removed_claims:
        key = _normalize_reference_claim_text(claim)
        if key and key not in seen:
            seen.add(key)
            deduped.append(claim)
    return deduped


def _build_admin_draft_quality_gate(issues: list[dict], generation_gate: dict | None) -> dict:
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for issue in issues or []:
        severity = str(issue.get("severity") or "low")
        if severity not in severity_counts:
            severity = "low"
        severity_counts[severity] += 1

    generation_status = str((generation_gate or {}).get("status") or "unknown")
    if severity_counts["high"] > 0:
        status = "blocked_for_publish"
    elif severity_counts["medium"] > 0 or generation_status not in {"pass", "unknown"}:
        status = "needs_remediation"
    else:
        status = "admin_ready"

    return {
        "status": status,
        "draft_save_allowed": True,
        "publish_review_allowed": status == "admin_ready",
        "issue_counts": severity_counts,
        "remaining_issue_codes": [str(issue.get("code") or "") for issue in issues or []],
        "generation_gate_status": generation_status,
    }


def _target_fields_for_remediation_issues(issues: list[dict]) -> list[str]:
    fields: list[str] = []
    for issue in issues or []:
        section = str(issue.get("section") or "")
        if section:
            fields.extend(part.strip() for part in section.split(",") if part.strip())
            continue
        code = str(issue.get("code") or "")
        if code == "unsupported_reference_claim":
            continue
        if code == "code_not_isomorphic":
            fields.extend(["body_advanced_ko", "body_advanced_en"])
    normalized: list[str] = []
    for field in fields:
        if field.startswith("adv_"):
            field = "body_advanced_ko" if "_ko_" in field else "body_advanced_en"
        if field not in normalized and field in {
            "body_basic_ko",
            "body_basic_en",
            "definition_ko",
            "definition_en",
            "body_advanced_ko",
            "body_advanced_en",
            "hero_news_context_ko",
            "hero_news_context_en",
        }:
            normalized.append(field)
    return normalized


def _build_handbook_remediation_user_prompt(term: str, data: dict, issues: list[dict]) -> str:
    target_fields = _target_fields_for_remediation_issues(issues)
    targets = {field: data.get(field, "") for field in target_fields}
    references = {
        "references_ko": data.get("references_ko", []),
        "references_en": data.get("references_en", []),
    }
    payload = {
        "term": term,
        "issues": issues,
        "target_fields": targets,
        "references": references,
    }
    return (
        "Rewrite only the listed target_fields for admin draft remediation.\n"
        "Do not regenerate unrelated fields. Do not add new references.\n"
        "Remove unsupported claims instead of inventing citations.\n"
        "If rewriting KO/EN code, make both locales implement the same system model.\n"
        "For code_capsule_too_large issues, shorten only the code or pseudocode section inside the target field; "
        "preserve existing markdown headings and do not rewrite non-code sections. "
        "Keep one compact fenced capsule, remove helper boilerplate/test harnesses, and keep the same contract.\n"
        "When rewriting Advanced fields, use practical system-design depth: runtime boundaries, "
        "component responsibilities, validation gates, failure paths, observability, and cost/latency tradeoffs. "
        "Do not make academic formalism, equations, or paper taxonomy the backbone unless the term is a metric, "
        "loss, math/statistics concept, or algorithm with a standard formula.\n"
        "Return a JSON object whose keys are only target field names.\n\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
    )


def _apply_handbook_remediation_patch(data: dict, patch_data: dict, allowed_fields: list[str]) -> list[str]:
    applied: list[str] = []
    for field in allowed_fields:
        value = patch_data.get(field)
        if isinstance(value, str) and value.strip():
            data[field] = value.strip()
            applied.append(field)
    return applied


async def _run_handbook_targeted_remediation(
    term: str,
    data: dict,
    warnings: list[str],
    client,
    model: str,
) -> tuple[dict, dict]:
    issues_before = _build_handbook_remediation_issues(data, warnings)
    removed_claims = _remove_unsupported_reference_claim_sentences(data)
    warnings_after_local = _apply_handbook_safety_postprocess(data)
    issues_after_local = _build_handbook_remediation_issues(data, warnings_after_local)
    llm_issues = [
        issue for issue in issues_after_local
        if issue.get("code") not in {"unsupported_reference_claim"}
    ]
    target_fields = _target_fields_for_remediation_issues(llm_issues)
    usage: dict = {}
    applied_fields: list[str] = []

    if target_fields:
        prompt = _build_handbook_remediation_user_prompt(term, data, llm_issues)
        resp = await client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a handbook draft remediation editor. "
                            "Patch only requested fields, preserve factual grounding, and return JSON only. "
                            "For Advanced patches, prefer architecture-review depth over academic formalism."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=6000,
                prompt_cache_key="hb-remediate-targeted",
                reasoning_effort="low",
                service_tier="flex",
            )
        )
        patch_data = parse_ai_json(resp.choices[0].message.content, "Handbook-remediate-targeted")
        applied_fields = _apply_handbook_remediation_patch(data, patch_data, target_fields)
        usage = extract_usage_metrics(resp, model)

    final_warnings = _apply_handbook_safety_postprocess(data)
    final_issues = _build_handbook_remediation_issues(data, final_warnings)
    meta = {
        "status": "applied" if (removed_claims or applied_fields) else "no_issues",
        "issues_before": issues_before,
        "issues_after": final_issues,
        "removed_claims": removed_claims,
        "applied_fields": applied_fields,
    }
    return usage, meta


def _hydrate_existing_draft_generation_metadata(term: str, data: dict) -> None:
    """Restore transient generation metadata for existing DB drafts.

    Some metadata, such as term_subtype and code_mode_hint, is produced during
    generation but not stored on handbook_terms. Existing-draft remediation
    still needs it to apply the same structural rules as generation.
    """
    try:
        from services.agents.prompts_handbook_types import (
            DEFAULT_INTENT_BY_TYPE,
            DEFAULT_VOLATILITY_BY_TYPE,
            get_artifact_policy,
            get_term_planner_override,
            normalize_term_subtype,
        )
    except Exception:
        return

    term_candidates = (
        term,
        data.get("term"),
        data.get("term_full"),
        data.get("korean_full"),
        data.get("korean_name"),
    )
    override = None
    for candidate in term_candidates:
        override = get_term_planner_override(str(candidate or ""))
        if override:
            break

    if override:
        override_type = str(override.get("type") or "")
        if override_type and not str(data.get("term_type") or "").strip():
            data["term_type"] = override_type

        effective_type = str(data.get("term_type") or override_type or "").strip()
        override_subtype = normalize_term_subtype(effective_type, override.get("subtype"))
        if override_subtype and not str(data.get("term_subtype") or "").strip():
            data["term_subtype"] = override_subtype

        if not data.get("facet_intent"):
            data["facet_intent"] = list(
                override.get("intent") or DEFAULT_INTENT_BY_TYPE.get(effective_type, ["understand"])
            )
        if not str(data.get("facet_volatility") or "").strip():
            data["facet_volatility"] = str(
                override.get("volatility")
                or DEFAULT_VOLATILITY_BY_TYPE.get(effective_type, "stable")
            )
        data.setdefault("facet_type_confidence", 1.0)

    if str(data.get("code_mode_hint") or "").strip():
        return

    term_type = str(data.get("term_type") or "").strip()
    if not term_type:
        return

    term_subtype = str(data.get("term_subtype") or "").strip() or None
    policy = get_artifact_policy(term_type, term_subtype, _primary_category_from_content(data))
    code_mode = str(policy.get("code_mode") or "").strip()
    if code_mode and code_mode != "contextual":
        data["code_mode_hint"] = code_mode


async def remediate_handbook_draft_content(
    term: str,
    data: dict,
    *,
    client=None,
    model: str | None = None,
    apply_llm: bool = False,
) -> tuple[dict, dict, list[dict], dict]:
    """Analyze or remediate an existing draft payload without regenerating it."""
    working = dict(data or {})
    _hydrate_existing_draft_generation_metadata(term, working)
    client = client or get_openai_client()
    model = model or getattr(settings, "openai_model_main")
    warnings = _apply_handbook_safety_postprocess(working)
    if apply_llm:
        usage, remediation_meta = await _run_handbook_targeted_remediation(
            term,
            working,
            warnings,
            client,
            model,
        )
        issues = remediation_meta.get("issues_after", [])
    else:
        usage = {}
        issues = _build_handbook_remediation_issues(working, warnings)
        remediation_meta = {
            "status": "dry_run",
            "issues_before": issues,
            "issues_after": issues,
            "removed_claims": [],
            "applied_fields": [],
        }
    gate = _build_admin_draft_quality_gate(issues, working.get("generation_gate"))
    working["_remediation_issues"] = issues
    working["_quality_gate"] = gate
    working["_remediation_status"] = remediation_meta["status"]
    return working, usage, issues, remediation_meta


def _check_handbook_structural_penalties(data: dict) -> tuple[int, list[str]]:
    """Score handbook structural quality via deterministic code checks.

    Mirrors the news pipeline's _check_structural_penalties() pattern:
    granular per-violation penalties, per-check caps, total cap at 40.
    Returns (penalty: 0-40, warnings: list of human-readable issues).

    This runs inline during generation (pure Python, no API calls, <1ms)
    and provides the "structural health" component of the hybrid quality
    score. The semantic component comes from the optional LLM quality
    check which may or may not run.
    """
    import re as _re

    penalty = 0
    warnings: list[str] = []

    def _count_h2(body: str) -> int:
        if not body:
            return 0
        count = body.count("\n## ")
        if body.startswith("## "):
            count += 1
        return count

    def _sentence_count(text: str) -> int:
        if not text:
            return 0
        # Split on period/question/exclamation followed by space or end
        sentences = [s for s in _re.split(r'[.。?!]\s', text) if len(s.strip()) > 10]
        return max(1, len(sentences))

    # --- Check 1: Advanced section completeness (-3/missing, cap -15) ---
    check1_penalty = 0
    for locale in ["ko", "en"]:
        body = data.get(f"body_advanced_{locale}", "") or ""
        h2 = _count_h2(body)
        expected = _expected_advanced_sections(
            data.get("code_mode_hint"),
            data.get("term_type"),
            data.get("term_subtype"),
        )
        missing = max(0, expected - h2)
        if missing > 0:
            p = missing * 3
            check1_penalty += p
            warnings.append(f"adv_{locale}: {h2}/{expected} sections (-{p})")
    penalty += min(check1_penalty, 15)

    # --- Check 2: Basic section completeness (-2/missing, cap -10) ---
    check2_penalty = 0
    for locale in ["ko", "en"]:
        body = data.get(f"body_basic_{locale}", "") or ""
        h2 = _count_h2(body)
        missing = max(0, 7 - h2)
        if missing > 0:
            p = missing * 2
            check2_penalty += p
            warnings.append(f"basic_{locale}: {h2}/7 sections (-{p})")
    penalty += min(check2_penalty, 10)

    # --- Check 3: Definition structure (-5 if <2 sents, -3 if >5, cap -5) ---
    check3_penalty = 0
    # Length ceilings tied to prompt spec: 1 sentence default (encyclopedia-lede),
    # 2 sentences only if the 2nd adds a distinct chunk.
    # Target: ~280-420 EN / ~150-230 KO. Over-length routes to queue via pipeline warning hook.
    DEF_CHAR_CEILING = {"ko": 260, "en": 480}
    DEF_SENTENCE_MAX = {"ko": 2, "en": 2}  # both: hard max 2
    for locale in ["ko", "en"]:
        defn = data.get(f"definition_{locale}", "") or ""
        if not defn:
            check3_penalty += 5
            warnings.append(f"definition_{locale} missing (-5)")
        else:
            sc = _sentence_count(defn)
            if sc > DEF_SENTENCE_MAX[locale]:
                check3_penalty += 3
                warnings.append(f"definition_{locale}: {sc} sentences, over {DEF_SENTENCE_MAX[locale]}-sentence ceiling — use subordinate clauses instead of splitting (-3)")
            dlen = len(defn)
            if dlen > DEF_CHAR_CEILING[locale]:
                check3_penalty += 3
                warnings.append(f"definition_{locale}: {dlen} chars exceeds ceiling {DEF_CHAR_CEILING[locale]} — compress clauses or drop optional 2nd sentence (-3)")
    penalty += min(check3_penalty, 5)

    # --- Check 4: §5 pitfalls ❌/✅ markers (-5 if missing) ---
    adv_ko = data.get("body_advanced_ko", "") or ""
    if adv_ko and "❌" not in adv_ko:
        penalty += 5
        warnings.append("§5 pitfalls: ❌ markers missing in adv_ko (-5)")

    # --- Check 5: §7 category tags (-5 if missing, cap -5) ---
    check5_penalty = 0
    if adv_ko and not any(t in adv_ko for t in ["(선행)", "(대안)", "(확장)"]):
        check5_penalty += 3
        warnings.append("§7 adv_ko: category tags (선행/대안/확장) missing (-3)")
    adv_en = data.get("body_advanced_en", "") or ""
    if adv_en and not any(t in adv_en for t in ["(prerequisite)", "(alternative)", "(extension)"]):
        check5_penalty += 3
        warnings.append("§7 adv_en: category tags missing (-3)")
    penalty += min(check5_penalty, 5)

    # --- Check 6: §4 tradeoffs labels (-3 if missing) ---
    if adv_ko and "이럴 때 적합" not in adv_ko and "이럴 때 부적합" not in adv_ko:
        penalty += 3
        warnings.append("§4 tradeoffs: 적합/부적합 labels missing in adv_ko (-3)")

    # --- Check 7: References (-3 per violation, cap -6) ---
    check7_penalty = 0
    for locale in ["ko", "en"]:
        refs = data.get(f"references_{locale}", []) or []
        if len(refs) < 3:
            check7_penalty += 3
            warnings.append(f"refs_{locale}: {len(refs)} items < 3 (-3)")
        else:
            primary = sum(1 for r in refs if (r.get("tier") if isinstance(r, dict) else "") == "primary")
            if primary < 2:
                check7_penalty += 2
                warnings.append(f"refs_{locale}: {primary} primary < 2 (-2)")
    penalty += min(check7_penalty, 6)

    # --- Check 8: Hero news context (-3 per missing locale, cap -6) ---
    check8_penalty = 0
    for locale in ["ko", "en"]:
        if not data.get(f"hero_news_context_{locale}"):
            check8_penalty += 3
            warnings.append(f"hero_{locale} missing (-3)")
    penalty += min(check8_penalty, 6)

    # --- Check 9: Advanced section depth (-1 per thin section, cap -5) ---
    check9_penalty = 0
    for locale in ["ko", "en"]:
        body = data.get(f"body_advanced_{locale}", "") or ""
        if not body:
            continue
        sections = _re.split(r"\n## ", body)
        for i, sec in enumerate(sections):
            sec_text = sec.strip()
            if sec_text and len(sec_text) < 200:
                check9_penalty += 1
                if check9_penalty <= 3:  # only log first 3 to avoid noise
                    warnings.append(f"adv_{locale} section {i}: {len(sec_text)} chars < 200 (-1)")
    penalty += min(check9_penalty, 5)

    # --- Check 10: Advanced total body length (-5 if under 6000) ---
    adv_total = len(adv_ko) + len(adv_en)
    if adv_total < 6000:
        penalty += 5
        warnings.append(f"adv total: {adv_total} chars < 6000 (-5)")

    # --- Check 11: Code section budget (-3 per overlong code section, cap -6) ---
    is_capability_spec = data.get("term_type") == "capability_feature_spec"
    soft_code_budget = 3500
    soft_code_line_budget = 55
    code_budget = 5000 if is_capability_spec else 7000
    code_penalty = 0
    for locale in ["ko", "en"]:
        body = data.get(f"body_advanced_{locale}", "") or ""
        for idx, code in enumerate(_extract_markdown_code_fences(body), start=1):
            line_count = len([line for line in code["body"].splitlines() if line.strip()])
            if len(code["body"]) > soft_code_budget or line_count > soft_code_line_budget:
                warnings.append(
                    f"adv_{locale} code capsule too large: fence {idx} has "
                    f"{len(code['body'])} chars/{line_count} lines > compact capsule target"
                )
            if len(code["body"]) > code_budget:
                code_penalty += 3
                warnings.append(
                    f"adv_{locale} code section too long: fence {idx} has {len(code['body'])} chars > {code_budget} (-3)"
                )
    penalty += min(code_penalty, 6)

    # --- Check 12: Korean name present (-1 if missing) ---
    if not data.get("korean_name"):
        penalty += 1
        warnings.append("korean_name missing (-1)")

    return min(penalty, 40), warnings


def _aggregate_quality_sub_scores(
    llm_output: dict, dimension_names: tuple[str, ...], max_raw: int = 100,
) -> tuple[int | None, dict]:
    """Aggregate LLM sub-scores into a normalized 0-100 total + per-dimension totals.

    Code (not LLM) computes arithmetic to avoid LLM arithmetic drift.
    Each sub-score is 0-10. `max_raw` is the sum of all possible sub-scores for
    this rubric (e.g., 9 subs × 10 = 90 for advanced, 10 × 10 = 100 for basic);
    the raw sum is then rescaled to 0-100 so grade thresholds stay comparable.

    Returns (total_0_100, annotated_breakdown) or (None, {}) if output malformed.
    """
    if not isinstance(llm_output, dict):
        return None, {}
    breakdown: dict = {}
    raw_total = 0
    any_found = False
    for dim in dimension_names:
        dim_data = llm_output.get(dim)
        if not isinstance(dim_data, dict):
            breakdown[dim] = {"_subtotal": 0, "_missing": True}
            continue
        dim_total = 0
        sub_entries: dict = {}
        for sub_name, sub_val in dim_data.items():
            if not isinstance(sub_val, dict):
                continue
            raw = sub_val.get("score", 0)
            try:
                s = int(raw)
            except (TypeError, ValueError):
                s = 0
            s = max(0, min(10, s))
            sub_entries[sub_name] = {
                "score": s,
                "evidence": str(sub_val.get("evidence", ""))[:500],
            }
            dim_total += s
            any_found = True
        breakdown[dim] = {**sub_entries, "_subtotal": dim_total}
        raw_total += dim_total
    if not any_found:
        return None, {}
    if max_raw <= 0:
        return None, {}
    normalized = int(round(raw_total * 100 / max_raw))
    return min(100, normalized), breakdown


# Advanced: 3+2+2+2 = 9 subs × 10 = 90 raw max. source_grounding removed
# because handbook structure stores sources in a dedicated references field,
# not as inline citations in body_advanced (unlike news digests).
_ADVANCED_DIMENSIONS = (
    "technical_depth", "accuracy", "uniqueness", "structural_completeness",
)
_ADVANCED_MAX_RAW = 90

# Basic: 3+3+2+2 = 10 subs × 10 = 100 raw max.
_BASIC_DIMENSIONS = (
    "engagement", "accuracy", "uniqueness", "structural_completeness",
)
_BASIC_MAX_RAW = 100


def _build_bilingual_judge_content(
    ko_body: str,
    en_body: str,
    max_chars_per_locale: int | None = None,
) -> str:
    """Construct a labeled user message for the bilingual quality judge.

    The judge sees KO and EN content as two parallel locale versions of the
    same term. Labels are required so the judge's Bilingual Content Contract
    (see HANDBOOK_QUALITY_CHECK_PROMPT / BASIC_QUALITY_CHECK_PROMPT) can
    reference "the KO section" / "the EN section" meaningfully.

    Missing locales are preserved as explicit placeholders so the judge can
    downscore the missing-language sub-scores instead of silently treating
    them as "present but empty".

    `max_chars_per_locale`, when set, truncates each locale to that many
    chars BEFORE concatenation. This guarantees each locale gets equal
    evidence visibility regardless of the other's length — without it, a
    rich KO body would consume the post-concat truncation budget at the
    call site and starve EN.
    """
    ko_section = ko_body.strip() if ko_body and ko_body.strip() else "(no Korean content provided)"
    en_section = en_body.strip() if en_body and en_body.strip() else "(no English content provided)"
    if max_chars_per_locale is not None and max_chars_per_locale > 0:
        ko_section = ko_section[:max_chars_per_locale]
        en_section = en_section[:max_chars_per_locale]
    return f"## Korean (KO)\n\n{ko_section}\n\n## English (EN)\n\n{en_section}"


async def _check_handbook_quality(
    term: str, term_type: str, advanced_content: str, client,
) -> tuple[int | None, dict, dict]:
    """Score handbook advanced quality. Returns (score, breakdown, usage).
    Returns (None, {}, {}) on failure — NOT a default score.

    Quality judgment is made by LLM on 10 sub-scores (0-10 each, 4 dimensions).
    Arithmetic aggregation to a 0-100 total is done in code, not the LLM,
    to avoid arithmetic drift in the judge output.
    """
    from services.agents.prompts_handbook_types import HANDBOOK_QUALITY_CHECK_PROMPT

    system = HANDBOOK_QUALITY_CHECK_PROMPT.format(term=term, term_type=term_type)
    reasoning_model = settings.openai_model_reasoning  # gpt-5-mini for quality check
    try:
        resp = await client.chat.completions.create(
            **build_completion_kwargs(
                model=reasoning_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": advanced_content},
                ],
                max_tokens=1800,
                response_format={"type": "json_object"},
                prompt_cache_key="hb-quality-advanced",
                service_tier="flex",
            )
        )
        data = parse_ai_json(resp.choices[0].message.content, "handbook-quality")
        total, breakdown = _aggregate_quality_sub_scores(data, _ADVANCED_DIMENSIONS, _ADVANCED_MAX_RAW)
        usage = extract_usage_metrics(resp, reasoning_model, requested_service_tier="flex")
        if total is None:
            logger.warning("Handbook quality check returned malformed sub-scores for '%s'", term)
            return None, {}, usage
        return total, {"sub_scores": breakdown, "raw": data}, usage
    except Exception as e:
        logger.warning("Handbook quality check failed for '%s': %s", term, e)
        return None, {}, {}


async def _self_critique_basic(
    term: str, term_type: str,
    basic_ko_content: str, basic_en_content: str,
    client, model: str,
    reference_context: str = "",
) -> tuple[bool, bool, str, str, int, int, dict]:
    """Self-critique basic KO+EN content in one call (gpt-5-mini).

    Returns (ko_needs, en_needs, ko_feedback, en_feedback,
             ko_score, en_score, usage).
    """
    from services.agents.prompts_handbook_types import BASIC_SELF_CRITIQUE_PROMPT

    light_model = settings.openai_model_reasoning  # gpt-5-mini for critique
    system = BASIC_SELF_CRITIQUE_PROMPT.format(term=term, term_type=term_type)
    if reference_context:
        system += (
            "\n\n## Reference Materials (for verifying product-technology claims)\n"
            + reference_context[:2000]
        )
    combined = f"## Korean Basic\n{basic_ko_content}\n\n## English Basic\n{basic_en_content}"
    try:
        resp = await client.chat.completions.create(
            **build_completion_kwargs(
                model=light_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": combined[:6000]},
                ],
                max_tokens=1500,
                response_format={"type": "json_object"},
                prompt_cache_key="hb-critique-basic",
                service_tier="flex",
            )
        )
        data = parse_ai_json(resp.choices[0].message.content, "basic-self-critique")
        ko_needs = data.get("ko_needs_improvement", False)
        en_needs = data.get("en_needs_improvement", False)
        ko_score = data.get("ko_score", 50)
        en_score = data.get("en_score", 50)
        ko_feedback = ""
        en_feedback = ""
        if ko_needs and data.get("ko_improvements"):
            ko_feedback = "\n".join(
                f"- {imp['section']}: {imp['suggestion']}"
                for imp in data["ko_improvements"]
            )
        if en_needs and data.get("en_improvements"):
            en_feedback = "\n".join(
                f"- {imp['section']}: {imp['suggestion']}"
                for imp in data["en_improvements"]
            )
        usage = extract_usage_metrics(resp, light_model, requested_service_tier="flex")
        return ko_needs, en_needs, ko_feedback, en_feedback, ko_score, en_score, usage
    except Exception as e:
        logger.warning("Basic self-critique failed for '%s': %s", term, e)
        return False, False, "", "", 50, 50, {}


async def _check_basic_quality(
    term: str, term_type: str, basic_content: str, client,
) -> tuple[int | None, dict, dict]:
    """Score handbook basic quality. Returns (score, breakdown, usage).

    Same sub-score aggregation pattern as advanced — LLM produces 10 sub-scores
    with evidence, code computes the total.
    """
    from services.agents.prompts_handbook_types import BASIC_QUALITY_CHECK_PROMPT

    system = BASIC_QUALITY_CHECK_PROMPT.format(term=term, term_type=term_type)
    reasoning_model = settings.openai_model_reasoning  # gpt-5-mini for quality check
    try:
        resp = await client.chat.completions.create(
            **build_completion_kwargs(
                model=reasoning_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": basic_content},
                ],
                max_tokens=1800,
                response_format={"type": "json_object"},
                prompt_cache_key="hb-quality-basic",
                service_tier="flex",
            )
        )
        data = parse_ai_json(resp.choices[0].message.content, "basic-quality")
        total, breakdown = _aggregate_quality_sub_scores(data, _BASIC_DIMENSIONS, _BASIC_MAX_RAW)
        usage = extract_usage_metrics(resp, reasoning_model, requested_service_tier="flex")
        if total is None:
            logger.warning("Basic quality check returned malformed sub-scores for '%s'", term)
            return None, {}, usage
        return total, {"sub_scores": breakdown, "raw": data}, usage
    except Exception as e:
        logger.warning("Basic quality check failed for '%s': %s", term, e)
        return None, {}, {}


def _build_generation_gate(
    advanced_score: int,
    basic_score: int,
    classification_confidence: float,
    structural_penalty: int,
) -> dict:
    """Build a small gate result for downstream save/publish decisions."""
    status = "pass"
    reasons: list[str] = []

    if classification_confidence < 0.35:
        status = "blocked"
        reasons.append("classification_confidence_below_min")
    elif classification_confidence < 0.55:
        status = "review_required"
        reasons.append("classification_confidence_below_review_threshold")

    if advanced_score < 55:
        status = "blocked"
        reasons.append("advanced_quality_below_min")
    elif advanced_score < 70 and status != "blocked":
        status = "review_required"
        reasons.append("advanced_quality_below_review_threshold")

    if basic_score < 55:
        status = "blocked"
        reasons.append("basic_quality_below_min")
    elif basic_score < 70 and status != "blocked":
        status = "review_required"
        reasons.append("basic_quality_below_review_threshold")

    if structural_penalty >= 25 and status == "pass":
        status = "review_required"
        reasons.append("structural_penalty_high")

    return {
        "status": status,
        "auto_save_allowed": status == "pass",
        "review_required": status != "pass",
        "reasons": reasons,
        "thresholds": {
            "advanced_min": 70,
            "basic_min": 70,
            "confidence_min": 0.55,
        },
    }


def _contains_insufficient_info(*chunks: str) -> bool:
    markers = (
        "해당 주제에 대한 검증된 정보가 부족합니다",
        "검증된 정보가 부족합니다",
        "공식 정의",
        "확인할 수 없어",
        "information on this topic is limited",
        "verified information is limited",
        "cannot confirm",
        "official documentation",
    )
    haystack = "\n".join(chunk for chunk in chunks if chunk).lower()
    return any(marker.lower() in haystack for marker in markers)


def _count_primary_references(reference_items: list[dict] | None) -> int:
    refs = reference_items or []
    return sum(1 for item in refs if str(item.get("tier", "")).lower() == "primary")


def _has_official_docs_reference(reference_items: list[dict] | None) -> bool:
    refs = reference_items or []
    for item in refs:
        if str(item.get("type", "")).lower() != "docs":
            continue
        title = str(item.get("title", "")).lower()
        venue = str(item.get("venue", "")).lower()
        annotation = str(item.get("annotation", "")).lower()
        url = str(item.get("url", "")).lower()
        if (
            "official" in title
            or "official" in annotation
            or "docs" in venue
            or "developer" in url
            or "docs." in url
        ):
            return True
    return False


def _has_clear_io_contract_signal(term_type: str, term_subtype: str | None, *chunks: str) -> bool:
    if term_type in {
        "protocol_format_data_structure",
        "capability_feature_spec",
        "library_framework_sdk",
        "data_storage_indexing_system",
        "system_workflow_pattern",
    }:
        return True
    text = "\n".join(chunk for chunk in chunks if chunk).lower()
    io_markers = (
        "json",
        "schema",
        "request",
        "response",
        "payload",
        "parameter",
        "argument",
        "api",
        "endpoint",
        "function",
        "tool call",
        "인자",
        "파라미터",
        "스키마",
        "호출",
    )
    return any(marker in text for marker in io_markers)


def _derive_reference_strength(
    reference_items: list[dict] | None,
    has_official_spec_signal: bool,
) -> str:
    refs = reference_items or []
    primary_refs = _count_primary_references(refs)
    if len(refs) >= 4 and primary_refs >= 2 and has_official_spec_signal:
        return "high"
    if len(refs) >= 3 and primary_refs >= 1:
        return "medium"
    return "low"


def _extract_reference_host(url: str) -> str:
    host = urlparse((url or "").strip()).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _is_official_reference(item: dict) -> bool:
    host = _extract_reference_host(str(item.get("url", "")))
    authors = str(item.get("authors", "")).lower()
    venue = str(item.get("venue", "")).lower()
    ref_type = str(item.get("type", "")).lower()
    official_hosts = (
        "openai.com",
        "anthropic.com",
        "ai.google.dev",
        "developers.google.com",
        "docs.aws.amazon.com",
        "learn.microsoft.com",
        "cloud.google.com",
    )
    return (
        host.endswith(official_hosts)
        or "official" in venue
        or "docs" in venue
        or ref_type == "docs"
        or any(org in authors for org in ("openai", "anthropic", "google", "aws", "microsoft"))
    )


def _score_reference_directness(term: str, item: dict) -> int:
    title = str(item.get("title", "")).lower()
    annotation = str(item.get("annotation", "")).lower()
    url = str(item.get("url", "")).lower()
    normalized_term = re.sub(r"[^a-z0-9]+", " ", (term or "").lower()).strip()
    term_tokens = [token for token in normalized_term.split() if len(token) >= 3]
    score = 0
    for token in term_tokens:
        if token in title:
            score += 2
        if token in annotation:
            score += 1
        if token in url:
            score += 1
    if _is_official_reference(item):
        score += 2
    if str(item.get("tier", "")).lower() == "primary":
        score += 1
    return score


def _evaluate_reference_candidates(
    term: str,
    term_type: str,
    term_subtype: str | None,
    references_ko: list[dict] | None,
    references_en: list[dict] | None,
) -> dict:
    from services.agents.prompts_handbook_types import get_reference_blocklist

    blocked_hosts = set(get_reference_blocklist(term_type, term_subtype))
    blocked_hosts_found: set[str] = set()
    candidate_by_url: dict[str, dict] = {}

    for item in [*(references_ko or []), *(references_en or [])]:
        url = str(item.get("url", "")).strip()
        if not url:
            continue
        host = _extract_reference_host(url)
        if any(host == blocked or host.endswith(f".{blocked}") for blocked in blocked_hosts):
            blocked_hosts_found.add(host)
            continue
        score = _score_reference_directness(term, item)
        if score <= 0:
            continue
        enriched = dict(item)
        enriched["_directness_score"] = score
        current = candidate_by_url.get(url)
        if current is None or score > current.get("_directness_score", -1):
            candidate_by_url[url] = enriched

    accepted_references = sorted(
        candidate_by_url.values(),
        key=lambda item: (
            0 if str(item.get("tier", "")).lower() == "primary" else 1,
            0 if _is_official_reference(item) else 1,
            -int(item.get("_directness_score", 0)),
            item.get("title", ""),
        ),
    )
    primary_count = _count_primary_references(accepted_references)
    has_official_docs = any(_is_official_reference(item) for item in accepted_references)
    directness_score = sum(int(item.get("_directness_score", 0)) for item in accepted_references)
    reference_strength = _derive_reference_strength(accepted_references, has_official_docs)

    return {
        "reference_strength": reference_strength,
        "primary_count": primary_count,
        "has_official_docs": has_official_docs,
        "directness_score": directness_score,
        "blocked_hosts_found": sorted(blocked_hosts_found),
        "accepted_references": [
            {k: v for k, v in item.items() if not str(k).startswith("_")}
            for item in accepted_references
        ],
    }


def _synchronize_reference_sets(
    accepted_references: list[dict],
    references_ko: list[dict] | None,
    references_en: list[dict] | None,
) -> tuple[list[dict], list[dict]]:
    ko_by_url = {str(item.get("url", "")).strip(): dict(item) for item in (references_ko or []) if item.get("url")}
    en_by_url = {str(item.get("url", "")).strip(): dict(item) for item in (references_en or []) if item.get("url")}
    synced_ko: list[dict] = []
    synced_en: list[dict] = []

    for accepted in accepted_references:
        url = str(accepted.get("url", "")).strip()
        if not url:
            continue
        ko_item = dict(ko_by_url.get(url) or en_by_url.get(url) or accepted)
        en_item = dict(en_by_url.get(url) or ko_by_url.get(url) or accepted)
        synced_ko.append(ko_item)
        synced_en.append(en_item)

    return synced_ko, synced_en


def _summarize_mechanism_text(*chunks: str, limit: int = 320) -> str:
    text = " ".join(chunk.strip() for chunk in chunks if chunk and chunk.strip())
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(sentences[:2]).strip()
    if len(summary) > limit:
        return summary[:limit].rstrip() + "..."
    return summary


def decide_code_mode(
    term_type: str,
    term_subtype: str | None,
    reference_strength: str,
    has_clear_io_contract: bool,
    has_official_spec_signal: bool,
    insufficient_info_flag: bool,
) -> str:
    if insufficient_info_flag:
        return "no-code"

    if term_type == "foundational_concept" and term_subtype in {"policy_discourse", "standard_regulation"}:
        return "no-code"

    if term_type in {"problem_failure_mode", "metric_benchmark"}:
        return "no-code"

    if term_type in {
        "foundational_concept",
        "model_algorithm_family",
        "training_optimization_method",
        "retrieval_knowledge_system",
        "system_workflow_pattern",
    }:
        return "pseudocode"

    if reference_strength == "high" and has_clear_io_contract and has_official_spec_signal:
        return "real-code"

    if term_type in {
        "data_storage_indexing_system",
        "protocol_format_data_structure",
        "capability_feature_spec",
        "library_framework_sdk",
        "hardware_runtime_infra",
        "product_platform_service",
    }:
        return "pseudocode"

    return "no-code"


def _build_code_mode_metadata(
    term_type: str,
    term_subtype: str | None,
    basic_data: dict,
    brave_context: str,
    deep_context: str,
    reference_eval: dict | None = None,
    primary_category: str | None = None,
) -> dict:
    references_ko = basic_data.get("references_ko", []) or []
    references_en = basic_data.get("references_en", []) or []
    merged_refs = [*references_ko, *references_en]
    mechanism_summary = _summarize_mechanism_text(
        basic_data.get("definition_ko", ""),
        basic_data.get("definition_en", ""),
        basic_data.get("basic_ko_1_plain", ""),
        basic_data.get("basic_en_1_plain", ""),
    )
    accepted_refs = (reference_eval or {}).get("accepted_references") or merged_refs
    has_official_spec_signal = bool((reference_eval or {}).get("has_official_docs")) or bool(brave_context.strip()) or _has_official_docs_reference(accepted_refs)
    has_clear_io_contract = _has_clear_io_contract_signal(
        term_type,
        term_subtype,
        mechanism_summary,
        basic_data.get("basic_ko_1_plain", ""),
        basic_data.get("basic_en_1_plain", ""),
    )
    insufficient_info_flag = _contains_insufficient_info(
        basic_data.get("definition_ko", ""),
        basic_data.get("definition_en", ""),
        basic_data.get("basic_ko_1_plain", ""),
        basic_data.get("basic_en_1_plain", ""),
    )
    reference_strength = str((reference_eval or {}).get("reference_strength") or _derive_reference_strength(accepted_refs, has_official_spec_signal))
    code_mode_hint = decide_code_mode(
        term_type,
        term_subtype,
        reference_strength,
        has_clear_io_contract,
        has_official_spec_signal,
        insufficient_info_flag,
    )
    try:
        from services.agents.prompts_handbook_types import get_artifact_policy

        artifact_policy = get_artifact_policy(term_type, term_subtype, primary_category)
        if artifact_policy.get("code_mode") == "no-code":
            code_mode_hint = "no-code"
    except Exception:
        pass
    vendor_lock_in_risk = (
        "high"
        if term_type in {"product_platform_service", "capability_feature_spec"} and term_subtype != "ecosystem_platform"
        else "medium"
        if term_type in {"library_framework_sdk", "hardware_runtime_infra", "data_storage_indexing_system"}
        else "low"
    )

    return {
        "code_mode_hint": code_mode_hint,
        "mechanism_summary": mechanism_summary,
        "has_clear_io_contract": has_clear_io_contract,
        "has_official_spec_signal": has_official_spec_signal,
        "reference_strength": reference_strength,
        "vendor_lock_in_risk": vendor_lock_in_risk,
        "insufficient_info_flag": insufficient_info_flag,
    }


def _select_source_context_for_field(
    term_type: str,
    term_subtype: str | None,
    field: str,
    source_bundle: dict[str, str],
) -> str:
    from services.agents.prompts_handbook_types import get_field_source_priority

    selected_chunks: list[str] = []
    seen_chunks: set[str] = set()
    for source_name in get_field_source_priority(term_type, field, term_subtype):
        chunk = (source_bundle.get(source_name) or "").strip()
        if not chunk or chunk in seen_chunks:
            continue
        selected_chunks.append(chunk)
        seen_chunks.add(chunk)
    return "\n\n".join(selected_chunks)


def _should_include_advanced_specs(term_type: str | None, term_subtype: str | None = None) -> bool:
    """Return whether the numeric specs block is meaningful for this term kind."""
    if not term_type:
        return False
    try:
        from services.agents.prompts_handbook_types import get_artifact_policy

        policy = get_artifact_policy(term_type, term_subtype)
        if policy.get("specs_mode") == "off":
            return False
        if policy.get("specs_mode") in {"optional", "required"}:
            return True
    except Exception:
        pass
    return term_type in {
        "model_algorithm_family",
        "metric_benchmark",
        "product_platform_service",
        "hardware_runtime_infra",
    }


ADVANCED_SPECS_SECTION_KO = ("adv_ko_specs", "## 핵심 스펙 (parameters, FLOPs, 벤치마크)")
ADVANCED_SPECS_SECTION_EN = ("adv_en_specs", "## Key Specifications (parameters, FLOPs, benchmarks)")


def _advanced_specs_section_for_type(
    locale: str,
    term_type: str | None = None,
    term_subtype: str | None = None,
) -> tuple[str, str]:
    key = f"adv_{locale}_specs"
    if locale == "ko":
        if term_type == "product_platform_service":
            return key, "## 핵심 한도·가격·운영 스펙"
        if term_type == "hardware_runtime_infra":
            return key, "## 핵심 하드웨어·런타임 스펙"
        if term_type == "metric_benchmark":
            return key, "## 핵심 평가 스펙"
        return ADVANCED_SPECS_SECTION_KO

    if term_type == "product_platform_service":
        return key, "## Key Limits, Pricing, and Operational Specs"
    if term_type == "hardware_runtime_infra":
        return key, "## Key Hardware and Runtime Specs"
    if term_type == "metric_benchmark":
        return key, "## Key Evaluation Specs"
    return ADVANCED_SPECS_SECTION_EN


def _section_header_for_code_mode(locale: str, code_mode: str | None) -> str:
    if code_mode == "no-code":
        return "## 운영 패턴과 검수 절차" if locale == "ko" else "## Operational Pattern and Review Procedure"
    return "## 코드 또는 의사코드" if locale == "ko" else "## Code or Pseudocode"


def _advanced_sections_for_mode(
    locale: str,
    code_mode: str | None,
    term_type: str | None = None,
    term_subtype: str | None = None,
) -> list[tuple[str, str]]:
    sections = list(ADVANCED_SECTIONS_KO if locale == "ko" else ADVANCED_SECTIONS_EN)
    code_key = f"adv_{locale}_3_code"
    code_header = _section_header_for_code_mode(locale, code_mode)
    sections = [
        (key, code_header if key == code_key else header)
        for key, header in sections
    ]
    if _should_include_advanced_specs(term_type, term_subtype):
        specs_section = _advanced_specs_section_for_type(locale, term_type, term_subtype)
        sections.insert(1, specs_section)
        return sections
    return sections


def _expected_advanced_sections(
    code_mode: str | None,
    term_type: str | None = None,
    term_subtype: str | None = None,
) -> int:
    return len(_advanced_sections_for_mode("en", code_mode, term_type, term_subtype))


async def _validate_ref_urls(content: str) -> str:
    """HEAD-check markdown link URLs in content. Remove broken links, keep text.

    Converts ``[Display Name](URL) — description`` to ``Display Name — description``
    when the URL returns 4xx/5xx or times out.
    """
    link_pattern = re.compile(r'\[([^\]]+)\]\((https?://[^\s)]+)\)')
    matches = list(link_pattern.finditer(content))
    if not matches:
        return content

    # Collect unique URLs to check (deduplicate)
    urls_to_check: dict[str, bool] = {}
    for m in matches:
        url = m.group(2)
        if url not in urls_to_check:
            urls_to_check[url] = True  # assume valid until checked

    # HEAD check all URLs concurrently with timeout
    async def _head_check(url: str) -> tuple[str, bool]:
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.head(url)
                if resp.status_code in (403, 405):
                    resp = await client.get(url)
                return url, resp.status_code < 400
        except (httpx.TimeoutException, httpx.RequestError):
            return url, True  # assume valid on timeout — don't strip on network error

    results = await asyncio.gather(
        *[_head_check(u) for u in urls_to_check],
        return_exceptions=True,
    )
    for result in results:
        if isinstance(result, tuple):
            url, is_valid = result
            urls_to_check[url] = is_valid

    # Replace broken links: [text](url) → text
    broken_count = 0
    for m in reversed(matches):  # reverse to preserve positions
        url = m.group(2)
        if not urls_to_check.get(url, False):
            display_text = m.group(1)
            content = content[:m.start()] + display_text + content[m.end():]
            broken_count += 1

    if broken_count:
        logger.info("Removed %d broken reference links", broken_count)
    return content


# Well-known entities that don't need verification
_ENTITY_ALLOWLIST = {
    "python", "javascript", "typescript", "java", "go", "rust", "c++",
    "linux", "windows", "macos", "ios", "android",
    "google", "microsoft", "amazon", "meta", "apple", "nvidia", "openai", "anthropic",
    "github", "stack overflow", "wikipedia", "arxiv",
    "pytorch", "tensorflow", "keras", "scikit-learn", "numpy", "pandas",
    "docker", "kubernetes", "aws", "gcp", "azure",
    "transformer", "bert", "gpt", "llama", "gemini", "claude",
    "sql", "nosql", "redis", "postgresql", "mongodb",
    "http", "https", "tcp", "udp", "rest", "graphql", "grpc",
}


async def _extract_novel_entities(
    generated_content: str, reference_text: str, client, model_light: str,
) -> list[str]:
    """Extract proper nouns from generated content that don't appear in references."""
    try:
        resp = await client.chat.completions.create(
            **compat_create_kwargs(
                model_light,
                messages=[
                    {"role": "system", "content": (
                        "Extract all specific proper nouns from the text: system names, framework names, "
                        "protocol names, paper titles, product names, benchmark names. "
                        'Return JSON: {"entities": ["name1", "name2"]}'
                    )},
                    {"role": "user", "content": generated_content[:6000]},
                ],
                response_format={"type": "json_object"},
                max_tokens=500,
                prompt_cache_key="hb-extract-novel",
            )
        )
        data = parse_ai_json(resp.choices[0].message.content, "entity-extract")
        entities = data.get("entities", [])
    except Exception as e:
        logger.warning("Entity extraction failed: %s", e)
        return []

    # Filter: keep only entities NOT in reference text and NOT in allowlist
    ref_lower = reference_text.lower()
    novel = []
    for ent in entities:
        ent_stripped = ent.strip()
        if not ent_stripped or len(ent_stripped) < 3:
            continue
        if ent_stripped.lower() in _ENTITY_ALLOWLIST:
            continue
        if ent_stripped.lower() in ref_lower:
            continue
        novel.append(ent_stripped)
    return novel[:10]  # Cap at 10 to limit API calls


async def _verify_entities(entities: list[str]) -> list[dict]:
    """Verify entities via Brave Search. Returns [{entity, verified, result_count}]."""
    if not settings.brave_api_key or not entities:
        return [{"entity": e, "verified": True, "result_count": -1} for e in entities]
    try:
        import httpx
    except ImportError:
        return [{"entity": e, "verified": True, "result_count": -1} for e in entities]

    async def _check_one(entity: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=8) as http:
                resp = await http.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": f'"{entity}" technology OR software OR AI', "count": 1},
                    headers={
                        "X-Subscription-Token": settings.brave_api_key,
                        "Accept": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                count = len(data.get("web", {}).get("results", []))
                return {"entity": entity, "verified": count > 0, "result_count": count}
        except Exception:
            return {"entity": entity, "verified": True, "result_count": -1}  # Assume valid on error

    results = await asyncio.gather(*[_check_one(e) for e in entities])
    return list(results)


# --- Section assembly: JSON keys → markdown ---

# Sections 1-4: Core (always visible), 5-8: Learn More (collapsible on frontend)
BASIC_SECTIONS_KO = [
    ("basic_ko_1_plain", "## 쉽게 이해하기"),
    ("basic_ko_2_example", "## 비유와 예시"),
    ("basic_ko_3_glance", "## 한눈에 비교"),
    ("basic_ko_4_impact", "## 어디서 왜 중요한가"),
    ("basic_ko_5_caution", "## 자주 하는 오해"),
    ("basic_ko_6_comm", "## 대화에서는 이렇게"),
    ("basic_ko_7_related", "## 함께 읽으면 좋은 용어"),
]

BASIC_SECTIONS_EN = [
    ("basic_en_1_plain", "## Plain Explanation"),
    ("basic_en_2_example", "## Examples & Analogies"),
    ("basic_en_3_glance", "## At a Glance"),
    ("basic_en_4_impact", "## Where and Why It Matters"),
    ("basic_en_5_caution", "## Common Misconceptions"),
    ("basic_en_6_comm", "## How It Sounds in Conversation"),
    ("basic_en_7_related", "## Related Reading"),
]

ADVANCED_SECTIONS_KO = [
    ("adv_ko_1_mechanism", "## 기술적 정의와 동작 원리"),
    ("adv_ko_2_formulas", "## 핵심 수식·아키텍처·도표"),
    ("adv_ko_3_code", "## 코드 또는 의사코드"),
    # NOTE: Display order swapped — pitfalls (concrete failures) before tradeoffs
    # (strategic judgment). Knowing what breaks helps reason about when to use.
    # JSON keys keep their numeric labels (4_tradeoffs, 5_pitfalls) so existing
    # LLM outputs still parse, but the assembled markdown places §5 content
    # before §4 content.
    ("adv_ko_5_pitfalls", "## 프로덕션 함정"),
    ("adv_ko_4_tradeoffs", "## 트레이드오프와 언제 무엇을 쓰나"),
    ("adv_ko_6_comm", "## 업계 대화 맥락"),
    ("adv_ko_7_related", "## 선행·대안·확장 개념"),
]

ADVANCED_SECTIONS_EN = [
    ("adv_en_1_mechanism", "## Technical Definition & How It Works"),
    ("adv_en_2_formulas", "## Formulas, Architecture, and Diagrams"),
    ("adv_en_3_code", "## Code or Pseudocode"),
    # See KO comment above — same swap.
    ("adv_en_5_pitfalls", "## Production Pitfalls"),
    ("adv_en_4_tradeoffs", "## Tradeoffs — When to Use What"),
    ("adv_en_6_comm", "## Industry Communication"),
    ("adv_en_7_related", "## Prerequisites, Alternatives, and Extensions"),
]


def _render_structured_relations(rel: dict, locale: str = "en") -> str:
    """Render structured Relations dict as canonical (tag) **term** — relationship bullets.

    Tag-first order matches the writer prompt's rule that the parenthesized tag
    precedes the bolded term.
    """
    bullets: list[str] = []
    tag_map = _RELATED_TAG_MAP_BY_LOCALE.get(locale, _RELATED_TAG_MAP_BY_LOCALE["en"])
    for category, tag in tag_map.items():
        for entry in rel.get(category, []) or []:
            term = (entry.get("term") or "").strip()
            relationship = (entry.get("relationship") or "").strip()
            if term and relationship:
                bullets.append(f"- ({tag}) **{term}** — {relationship}")
    return "\n".join(bullets)


_RELATED_TAG_ALIASES = {
    "basic": {
        "ko": {
            "기초": "기초",
            "선행": "기초",
            "before": "기초",
            "prerequisite": "기초",
            "prerequisites": "기초",
            "유사": "유사",
            "대안": "유사",
            "similar": "유사",
            "alternative": "유사",
            "alternatives": "유사",
            "심화": "심화",
            "확장": "심화",
            "next": "심화",
            "extension": "심화",
            "extensions": "심화",
        },
        "en": {
            "기초": "before",
            "선행": "before",
            "before": "before",
            "prerequisite": "before",
            "prerequisites": "before",
            "유사": "similar",
            "대안": "similar",
            "similar": "similar",
            "alternative": "similar",
            "alternatives": "similar",
            "심화": "next",
            "확장": "next",
            "next": "next",
            "extension": "next",
            "extensions": "next",
        },
    },
    "advanced": {
        "ko": {
            "기초": "선행",
            "선행": "선행",
            "before": "선행",
            "prerequisite": "선행",
            "prerequisites": "선행",
            "유사": "대안",
            "대안": "대안",
            "similar": "대안",
            "alternative": "대안",
            "alternatives": "대안",
            "심화": "확장",
            "확장": "확장",
            "next": "확장",
            "extension": "확장",
            "extensions": "확장",
            "open-weight": "확장",
            "open weight": "확장",
        },
        "en": {
            "기초": "prerequisite",
            "선행": "prerequisite",
            "before": "prerequisite",
            "prerequisite": "prerequisite",
            "prerequisites": "prerequisite",
            "유사": "alternative",
            "대안": "alternative",
            "similar": "alternative",
            "alternative": "alternative",
            "alternatives": "alternative",
            "심화": "extension",
            "확장": "extension",
            "next": "extension",
            "extension": "extension",
            "extensions": "extension",
            "open-weight": "extension",
            "open weight": "extension",
        },
    },
}


_RELATED_FALLBACK_RELATIONSHIP = {
    ("basic", "ko", "기초"): "이 용어를 먼저 이해하면 본문을 읽기 쉽습니다.",
    ("basic", "ko", "유사"): "비슷한 선택지와 차이를 비교할 때 함께 보면 좋습니다.",
    ("basic", "ko", "심화"): "다음 단계로 더 깊게 연결되는 개념입니다.",
    ("basic", "en", "before"): "Read this first to understand the surrounding concept.",
    ("basic", "en", "similar"): "Compare this nearby option against the current term.",
    ("basic", "en", "next"): "Read this next to go deeper from the current term.",
    ("advanced", "ko", "선행"): "이 개념을 먼저 이해하면 시스템 경계를 더 정확히 볼 수 있습니다.",
    ("advanced", "ko", "대안"): "같은 문제를 다른 방식으로 풀 때 비교할 수 있는 선택지입니다.",
    ("advanced", "ko", "확장"): "이 용어를 실제 시스템으로 확장할 때 함께 검토할 개념입니다.",
    ("advanced", "en", "prerequisite"): "Understand this first to reason about system boundaries.",
    ("advanced", "en", "alternative"): "Compare this when choosing a different design path.",
    ("advanced", "en", "extension"): "Use this to extend the current term into a broader system.",
}


def _canonical_related_tag(tag: str, *, locale: str, level: str) -> str | None:
    normalized = re.sub(r"\s+", " ", str(tag or "").strip().lower())
    return _RELATED_TAG_ALIASES.get(level, {}).get(locale, {}).get(normalized)


def _fallback_related_relationship(*, locale: str, level: str, tag: str) -> str:
    return _RELATED_FALLBACK_RELATIONSHIP.get((level, locale, tag), "Related concept to read next.")


def _split_related_terms(term_text: str) -> list[str]:
    """Split obvious multi-term related bullets without splitting parentheticals."""
    text = (term_text or "").strip()
    if not text:
        return []
    if "," not in text:
        return [text]
    parts = [part.strip() for part in text.split(",") if part.strip()]
    return parts or [text]


def _normalize_related_bullet_line(line: str, *, locale: str, level: str) -> list[str]:
    stripped = (line or "").strip()
    if not stripped.startswith("-"):
        return [line]

    body = stripped[1:].strip()
    tag = ""
    rest = ""
    paren_match = re.match(r"^\(([^)]+)\)\s+(.+)$", body)
    if paren_match:
        tag = paren_match.group(1).strip()
        rest = paren_match.group(2).strip()
    else:
        colon_match = re.match(r"^([^:：]+)[:：]\s+(.+)$", body)
        if colon_match:
            tag = colon_match.group(1).strip()
            rest = colon_match.group(2).strip()

    canonical_tag = _canonical_related_tag(tag, locale=locale, level=level)
    if not canonical_tag or not rest:
        return [line]

    # Accept existing canonical bold form, but normalize dash variants.
    bold_match = re.match(r"^\*\*([^*]+)\*\*\s*(?:—|–|-)?\s*(.*)$", rest)
    if bold_match:
        term_text = bold_match.group(1).strip()
        relationship = bold_match.group(2).strip()
    else:
        split_match = re.match(r"^(.+?)\s+(?:—|–|-)\s+(.+)$", rest)
        if split_match:
            term_text = split_match.group(1).strip()
            relationship = split_match.group(2).strip()
        else:
            term_text = rest.strip()
            relationship = ""

    terms = _split_related_terms(term_text)
    normalized_lines: list[str] = []
    for term in terms:
        clean_term = term.strip().strip("*").strip()
        if not clean_term:
            continue
        clean_relationship = relationship or _fallback_related_relationship(
            locale=locale,
            level=level,
            tag=canonical_tag,
        )
        normalized_lines.append(f"- ({canonical_tag}) **{clean_term}** — {clean_relationship}")
    return normalized_lines or [line]


def _normalize_related_bullets_for_frontend(content: str, *, locale: str, level: str) -> str:
    """Canonicalize related bullets for the frontend related-term row transformer."""
    if not content:
        return content
    lines: list[str] = []
    for line in content.splitlines():
        if line.strip().startswith("-"):
            lines.extend(_normalize_related_bullet_line(line, locale=locale, level=level))
        else:
            lines.append(line)
    return "\n".join(lines).strip()


def _normalize_related_sections_for_frontend(markdown: str, *, locale: str, level: str) -> str:
    """Normalize Basic/Advanced related sections in assembled markdown."""
    if not markdown:
        return markdown
    heading = (
        "함께 읽으면 좋은 용어"
        if locale == "ko" and level == "basic"
        else "Related Reading"
        if locale == "en" and level == "basic"
        else "선행·대안·확장 개념"
        if locale == "ko"
        else "Prerequisites, Alternatives, and Extensions"
    )
    pattern = re.compile(rf"(?ms)^(##\s+{re.escape(heading)}\s*\n)(.*?)(?=^##\s+|\Z)")

    def _replace(match: re.Match) -> str:
        normalized = _normalize_related_bullets_for_frontend(
            match.group(2).strip(),
            locale=locale,
            level=level,
        )
        return f"{match.group(1)}{normalized}"

    return pattern.sub(_replace, markdown)


def _render_structured_specs(specs: dict) -> str:
    """Render structured Specs dict as a bullet list of concrete numbers.

    Empty values and the literal sentinel 'not_published' are omitted. If no
    concrete values or benchmark rows remain, return an empty string so broad
    concepts like Attention/LLM/GPU do not show a hollow specs section.
    """
    lines: list[str] = []
    field_order = [
        ("parameters", "Parameters"),
        ("context_window", "Context window"),
        ("training_data", "Training data"),
        ("compute_cost", "Compute cost"),
        ("latency_throughput", "Latency / throughput"),
    ]
    for key, label in field_order:
        value = specs.get(key)
        value_str = value.strip() if isinstance(value, str) else ""
        if value_str and value_str != "not_published":
            lines.append(f"- **{label}**: {value_str}")

    benchmarks = specs.get("benchmarks") or []
    if benchmarks:
        benchmark_lines: list[str] = []
        for b in benchmarks:
            if not isinstance(b, dict):
                continue
            name = (b.get("name") or "").strip()
            score = (b.get("score") or "").strip()
            ctx = (b.get("context") or "").strip()
            if name and score:
                ctx_part = f" — {ctx}" if ctx else ""
                benchmark_lines.append(f"  - {name}: {score}{ctx_part}")
        if benchmark_lines:
            lines.append("- **Benchmarks**:")
            lines.extend(benchmark_lines)
    return "\n".join(lines)


def _section_value_to_text(
    key: str,
    raw_value: object,
    *,
    serialize_unknown_structures: bool = False,
) -> str:
    """Normalize section values before markdown assembly or prompt previews."""
    if isinstance(raw_value, dict):
        if key.endswith("_7_related"):
            locale = "ko" if "_ko_" in key else "en"
            return _render_structured_relations(raw_value, locale=locale).strip()
        if key.endswith("_specs"):
            return _render_structured_specs(raw_value).strip()
        if serialize_unknown_structures:
            return json.dumps(raw_value, ensure_ascii=False, default=str).strip()
        return ""
    if isinstance(raw_value, str):
        value = raw_value.strip()
        if key.endswith("_7_related"):
            locale = "ko" if "_ko_" in key else "en"
            level = "basic" if key.startswith("basic_") else "advanced"
            return _normalize_related_bullets_for_frontend(
                value,
                locale=locale,
                level=level,
            ).strip()
        return value
    if raw_value is None:
        return ""
    if serialize_unknown_structures:
        return json.dumps(raw_value, ensure_ascii=False, default=str).strip()
    return ""


def _build_section_preview(data: dict, prefix: str, max_chars: int = 1000) -> str:
    parts: list[str] = []
    for key, raw_value in data.items():
        if not key.startswith(prefix):
            continue
        content = _section_value_to_text(
            key,
            raw_value,
            serialize_unknown_structures=True,
        )
        if content:
            parts.append(f"## {key}: {content[:max_chars]}")
    return "\n\n".join(parts)


def _assemble_markdown(data: dict, sections: list[tuple[str, str]]) -> str:
    """Assemble section-per-key JSON data into markdown with H2 headers.

    Section value can be a string (legacy/most sections) or a dict (structured
    fields like `adv_*_7_related`). Dicts dispatch to a type-specific renderer
    by key suffix; strings pass through verbatim. Empty values omit the section.
    """
    parts: list[str] = []
    for key, header in sections:
        content = _section_value_to_text(key, data.get(key))
        if content:
            parts.append(f"{header}\n{content}")
    return "\n\n".join(parts)


def _normalize_tradeoff_labels_for_frontend(markdown: str, locale: str) -> str:
    """Keep tradeoff sections in the p/ul/p/ul shape expected by the frontend grid."""
    if not markdown:
        return markdown

    if locale == "ko":
        good_label = "이럴 때 적합:"
        bad_label = "이럴 때 부적합:"
        aliases = {
            r"적합:": good_label,
            r"이럴 때 적합:": good_label,
            r"적합한 경우:": good_label,
            r"부적합:": bad_label,
            r"이럴 때 부적합:": bad_label,
            r"부적합한 경우:": bad_label,
        }
    else:
        good_label = "Suitable:"
        bad_label = "Unsuitable:"
        aliases = {
            r"Suitable:": good_label,
            r"Unsuitable:": bad_label,
        }

    normalized = markdown
    for alias, canonical in aliases.items():
        normalized = re.sub(
            rf"^[ \t]*{alias}[ \t]*$",
            canonical,
            normalized,
            flags=re.M | re.I if locale == "en" else re.M,
        )

    for label in (good_label, bad_label):
        normalized = re.sub(
            rf"^[ \t]*{re.escape(label)}[ \t]*\n+",
            f"{label}\n\n",
            normalized,
            flags=re.M,
        )
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"([^\n])## ", r"\1\n\n## ", normalized)
    return normalized


def _derive_learner_summary_from_basic(body_basic: str) -> str:
    """Fallback learner summary derived from the first Basic section."""
    if not body_basic:
        return ""
    stripped = re.sub(r"^##\s+[^\n]*\n+", "", body_basic.strip(), count=1)
    next_heading = stripped.find("\n##")
    first_section = stripped[:next_heading].strip() if next_heading > 0 else stripped.strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", first_section) if p.strip()]
    return "\n\n".join(paragraphs[:2]).strip()


def _assemble_all_sections(raw_data: dict) -> dict:
    """Convert section-per-key LLM output to body_basic/advanced_ko/en fields.

    Preserves meta fields (term_full, korean_name, etc.) and assembles
    section keys into markdown. If body_basic_ko already exists (old format),
    passes through unchanged.
    """
    data = {}

    # Copy meta fields
    for key in (
        "term_full",
        "korean_name",
        "korean_full",
        "categories",
        "summary_ko",
        "summary_en",
        "definition_ko",
        "definition_en",
        "term_type",
        "term_subtype",
        "facet_intent",
        "facet_volatility",
        "facet_type_confidence",
        "generation_gate",
        "code_mode_hint",
        "mechanism_summary",
        "has_clear_io_contract",
        "has_official_spec_signal",
        "reference_strength",
        "vendor_lock_in_risk",
        "insufficient_info_flag",
    ):
        if key in raw_data:
            data[key] = raw_data[key]

    # Copy level-independent fields (hero card, references).
    # These are rendered outside the Basic/Advanced body switcher.
    for key in ("hero_news_context_ko", "hero_news_context_en",
                "references_ko", "references_en"):
        if key in raw_data:
            data[key] = raw_data[key]

    # Assemble basic sections (or pass through if already assembled)
    if "body_basic_ko" in raw_data:
        data["body_basic_ko"] = raw_data["body_basic_ko"]
    elif "basic_ko_1_plain" in raw_data:
        data["body_basic_ko"] = _assemble_markdown(raw_data, BASIC_SECTIONS_KO)

    if "body_basic_en" in raw_data:
        data["body_basic_en"] = raw_data["body_basic_en"]
    elif "basic_en_1_plain" in raw_data:
        data["body_basic_en"] = _assemble_markdown(raw_data, BASIC_SECTIONS_EN)

    if not data.get("summary_ko"):
        data["summary_ko"] = _derive_learner_summary_from_basic(data.get("body_basic_ko", ""))
    if not data.get("summary_en"):
        data["summary_en"] = _derive_learner_summary_from_basic(data.get("body_basic_en", ""))

    # Assemble advanced sections (or pass through if already assembled)
    if "body_advanced_ko" in raw_data:
        data["body_advanced_ko"] = raw_data["body_advanced_ko"]
    elif "adv_ko_1_mechanism" in raw_data:
        data["body_advanced_ko"] = _assemble_markdown(
            raw_data,
            _advanced_sections_for_mode(
                "ko",
                raw_data.get("code_mode_hint"),
                raw_data.get("term_type"),
                raw_data.get("term_subtype"),
            ),
        )

    if "body_advanced_en" in raw_data:
        data["body_advanced_en"] = raw_data["body_advanced_en"]
    elif "adv_en_1_mechanism" in raw_data:
        data["body_advanced_en"] = _assemble_markdown(
            raw_data,
            _advanced_sections_for_mode(
                "en",
                raw_data.get("code_mode_hint"),
                raw_data.get("term_type"),
                raw_data.get("term_subtype"),
            ),
        )

    # Post-process: fix bold markdown with parenthetical abbreviations
    # **term(abbreviation)** or **term (abbreviation)** → **term** (abbreviation)
    import re
    def _fix_bold_parens(m: re.Match) -> str:
        term_part = m.group(1).rstrip()  # strip trailing space before (
        abbrev = m.group(2)
        return f"**{term_part}** ({abbrev})"
    for field in ("body_basic_ko", "body_basic_en", "body_advanced_ko", "body_advanced_en"):
        if data.get(field):
            data[field] = re.sub(r'\*\*([^*]+?)\s*\(([^)]+)\)\*\*', _fix_bold_parens, data[field])
    if data.get("body_advanced_ko"):
        data["body_advanced_ko"] = _normalize_tradeoff_labels_for_frontend(
            data["body_advanced_ko"],
            "ko",
        )
    if data.get("body_advanced_en"):
        data["body_advanced_en"] = _normalize_tradeoff_labels_for_frontend(
            data["body_advanced_en"],
            "en",
        )
    if data.get("body_basic_ko"):
        data["body_basic_ko"] = _normalize_related_sections_for_frontend(
            data["body_basic_ko"],
            locale="ko",
            level="basic",
        )
    if data.get("body_basic_en"):
        data["body_basic_en"] = _normalize_related_sections_for_frontend(
            data["body_basic_en"],
            locale="en",
            level="basic",
        )
    if data.get("body_advanced_ko"):
        data["body_advanced_ko"] = _normalize_related_sections_for_frontend(
            data["body_advanced_ko"],
            locale="ko",
            level="advanced",
        )
    if data.get("body_advanced_en"):
        data["body_advanced_en"] = _normalize_related_sections_for_frontend(
            data["body_advanced_en"],
            locale="en",
            level="advanced",
        )

    return data


def _build_code_section_user_prompt(
    req: HandbookAdviseRequest,
    code_mode: str,
    locale: str,
    definition_ko: str,
    definition_en: str,
    mechanism_summary: str,
    advanced_non_code_sections: dict,
    references: list[dict] | None,
) -> str:
    section_prefix = f"adv_{locale}_"
    non_code_keys = [
        f"{section_prefix}1_mechanism",
        f"{section_prefix}2_formulas",
        f"{section_prefix}4_tradeoffs",
        f"{section_prefix}5_pitfalls",
        f"{section_prefix}6_comm",
        f"{section_prefix}7_related",
    ]
    parts = [
        f"Term: {req.term}",
        f"Korean name: {req.korean_name}" if req.korean_name else None,
        f"Code mode: {code_mode}",
        f"Target locale: {locale}",
        f"Definition KO: {definition_ko}" if definition_ko else None,
        f"Definition EN: {definition_en}" if definition_en else None,
        f"Mechanism summary: {mechanism_summary}" if mechanism_summary else None,
        "",
        "Generate only section 3. Keep it consistent with the non-code advanced sections below.",
    ]
    for key in non_code_keys:
        value = _section_value_to_text(
            key,
            advanced_non_code_sections.get(key),
            serialize_unknown_structures=True,
        )
        if value:
            parts.append(f"\n## {key}\n{value[:1800]}")
    if references:
        refs_json = json.dumps(references[:6], ensure_ascii=False, indent=2)
        parts.append(f"\n## References\n{refs_json}")
    return "\n".join(part for part in parts if part is not None)


def _extract_code_section_text(section_data: dict, locale: str) -> str:
    return (section_data.get(f"adv_{locale}_3_code") or "").strip()


def _normalize_quality_score_value(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _handbook_quality_grade(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def _combine_handbook_quality_score(semantic: int | None, penalty: int) -> int:
    if semantic is not None:
        return max(0, semantic - penalty)
    return max(0, 100 - penalty * 2)


def _record_handbook_quality_scores(supabase, data: dict, source: str = "manual") -> int:
    """Insert fresh advanced/basic handbook quality score rows for an existing draft.

    Existing draft rescores must use the stored handbook slug/id. Deriving a slug
    from the English term can orphan scores when the DB slug was normalized or
    manually adjusted.
    """
    if not supabase:
        return 0

    term_slug = str(data.get("slug") or "").strip()
    if not term_slug:
        term = str(data.get("term") or "").lower().strip()
        term_slug = re.sub(r"[^a-z0-9]+", "-", term).strip("-")
    if not term_slug:
        return 0

    base_row = {
        "term_slug": term_slug,
        "term_type": data.get("term_type") or "unknown",
        "source": source,
    }
    if data.get("id"):
        base_row["term_id"] = data["id"]

    quality_data = data.get("quality") or {}
    inserted = 0
    for level in ("advanced", "basic"):
        quality = quality_data.get(level) or {}
        score = _normalize_quality_score_value(quality.get("total"))
        if score is None:
            continue
        supabase.table("handbook_quality_scores").insert({
            **base_row,
            "score": score,
            "breakdown": {"level": level, **quality},
        }).execute()
        inserted += 1
    return inserted


async def rescore_existing_handbook_quality(
    term: str,
    content: dict,
    *,
    client=None,
    run_semantic: bool = False,
) -> tuple[dict, dict, list[str]]:
    """Recompute quality metadata for an existing handbook draft without regenerating content."""
    data = dict(content or {})
    term_type = str(data.get("term_type") or "unknown")

    structural_penalty, structural_warnings = _check_handbook_structural_penalties(data)
    warnings = list(structural_warnings)
    merged_usage: dict = {}

    semantic_score = None
    semantic_breakdown = {}
    basic_semantic_score = None
    basic_semantic_breakdown = {}

    if run_semantic:
        active_client = client or get_openai_client()
        adv_combined = _build_bilingual_judge_content(
            data.get("body_advanced_ko", ""),
            data.get("body_advanced_en", ""),
            max_chars_per_locale=8000,
        )
        if adv_combined.strip():
            semantic_score, semantic_breakdown, quality_usage = await _check_handbook_quality(
                term,
                term_type,
                adv_combined,
                active_client,
            )
            if quality_usage:
                merged_usage = merge_usage_metrics(merged_usage, quality_usage)

        basic_combined = _build_bilingual_judge_content(
            data.get("body_basic_ko", ""),
            data.get("body_basic_en", ""),
            max_chars_per_locale=4000,
        )
        if basic_combined.strip():
            basic_semantic_score, basic_semantic_breakdown, basic_quality_usage = await _check_basic_quality(
                term,
                term_type,
                basic_combined,
                active_client,
            )
            if basic_quality_usage:
                merged_usage = merge_usage_metrics(merged_usage, basic_quality_usage)

    adv_final = _combine_handbook_quality_score(semantic_score, structural_penalty)
    basic_final = _combine_handbook_quality_score(basic_semantic_score, structural_penalty)

    data["quality"] = {
        "advanced": {
            "total": adv_final,
            "grade": _handbook_quality_grade(adv_final),
            "structural_penalty": structural_penalty,
            "structural_warnings": structural_warnings,
            "semantic_score": semantic_score,
            "semantic_breakdown": semantic_breakdown if semantic_score is not None else None,
            "method": "hybrid" if semantic_score is not None else "structural-only",
        },
        "basic": {
            "total": basic_final,
            "grade": _handbook_quality_grade(basic_final),
            "semantic_score": basic_semantic_score,
            "semantic_breakdown": basic_semantic_breakdown if basic_semantic_score is not None else None,
            "method": "hybrid" if basic_semantic_score is not None else "structural-only",
        },
    }
    data["quality_score"] = adv_final
    data["basic_quality_score"] = basic_final

    generation_gate = _build_generation_gate(
        adv_final,
        basic_final,
        1.0,
        structural_penalty,
    )
    data["generation_gate"] = generation_gate
    if generation_gate["status"] != "pass":
        warnings.append(
            f"Generation gate: {generation_gate['status']} ({', '.join(generation_gate['reasons'])})"
        )
    if adv_final < 55:
        warnings.append(f"Advanced quality: {adv_final}/100 ({_handbook_quality_grade(adv_final)}) — regen recommended")
    elif adv_final < 70:
        warnings.append(f"Advanced quality: {adv_final}/100 ({_handbook_quality_grade(adv_final)}) — review recommended")
    if basic_final < 55:
        warnings.append(f"Basic quality: {basic_final}/100 ({_handbook_quality_grade(basic_final)}) — regen recommended")
    elif basic_final < 70:
        warnings.append(f"Basic quality: {basic_final}/100 ({_handbook_quality_grade(basic_final)}) — review recommended")

    issues = _build_handbook_remediation_issues(data, warnings)
    admin_quality_gate = _build_admin_draft_quality_gate(issues, generation_gate)
    data["_warnings"] = warnings
    data["_remediation_issues"] = issues
    data["_quality_gate"] = admin_quality_gate
    data["_remediation_status"] = "quality_rescore"
    return data, merged_usage, warnings


async def _run_generate_term(
    req: HandbookAdviseRequest, client, model: str,
    source: str = "manual",
    article_context: str = "",
    log_run_id: str | None = None,
) -> tuple[dict, dict, list[str]]:
    """Auto-generate all empty fields for a handbook term via 4 LLM calls.

    Call 1: meta + KO Basic (term_full, korean_full, categories, definition, body_basic_ko)
    Call 2: EN Basic (body_basic_en, with KO definition as context)
    Call 3: KO Advanced (body_advanced_ko, with definition as context)
    Call 4: EN Advanced (body_advanced_en, with definition as context)

    Args:
        source: "manual" (admin editor) or "pipeline" (auto-extraction)
        article_context: source news article for grounding (pipeline only)

    Returns (merged_data, merged_usage, warnings).
    """
    # Run all searches in parallel — results are source-role labeled
    categories_list = req.categories if req.categories else []
    classification_context = _build_handbook_classification_context(req, article_context)
    term_type, term_subtype, intent_list, volatility, type_confidence = await _classify_term_type(
        req.term,
        categories_list,
        classification_context,
        client,
        settings.openai_model_nano,
        term_type_hint=req.term_type_hint,
    )
    primary_intent = intent_list[0] if intent_list else "understand"
    logger.info(
        "Term '%s' classified before retrieval: type=%s subtype=%s intent=%s volatility=%s confidence=%.2f",
        req.term, term_type, term_subtype, intent_list, volatility, type_confidence,
    )
    tavily_context, brave_context, deep_context = await asyncio.gather(
        _search_term_context(req.term, categories=categories_list, term_type=term_type, subtype=term_subtype, intent=primary_intent),
        _search_brave_context(req.term, categories=categories_list, term_type=term_type, subtype=term_subtype, intent=primary_intent),
        _search_deep_context(req.term, categories=categories_list, term_type=term_type, subtype=term_subtype, intent=primary_intent),
    )
    from services.agents.prompts_handbook_types import get_term_generation_override

    term_generation_override = get_term_generation_override(req.term)
    curated_context = ""
    if term_generation_override:
        curated_context = str(term_generation_override.get("reference_context", "")).strip()

    source_bundle = {
        "curated": curated_context,
        "brave": brave_context,
        "exa": deep_context,
        "tavily": tavily_context,
    }

    user_prompt = _build_handbook_user_prompt(req)
    call1_contexts: list[str] = []
    if article_context:
        call1_contexts.append(
            "## Source Article (PRIMARY factual reference)\n"
            "Base your content on facts from this article. "
            "Write the handbook entry in reference style, not news style.\n\n"
            f"{article_context[:4000]}\n\n"
        )
    for field_name in ("definition", "hero", "basic", "references"):
        selected = _select_source_context_for_field(term_type, term_subtype, field_name, source_bundle)
        if selected and selected not in call1_contexts:
            call1_contexts.append(selected)
    combined_ref = "\n\n".join(call1_contexts)
    if combined_ref:
        user_prompt += (
            "\n\n" + combined_ref +
            "## Source Usage Rules\n"
            "- Use Source Article as your PRIMARY factual reference.\n"
            "- Use Reference Materials for recent context and examples.\n"
            "- Prioritize official docs and direct sources for definition and references.\n"
            "- Use recent/news sources mainly for hero context and fresh examples.\n"
            "- ONLY cite facts from the materials above. If a topic is not covered, "
            "state that information is limited rather than generating from memory.\n"
        )
    warnings: list[str] = []
    supabase = get_supabase()
    draft_smoke_mode = bool(req.skip_self_critique and req.skip_quality_check)
    generation_max_tokens = 12000 if draft_smoke_mode else 24000
    generation_reasoning_effort = "low" if draft_smoke_mode else "high"
    draft_smoke_guide = """
## Draft Smoke Mode
- Generate a complete but compact draft for admin review, not a polished publish candidate.
- Keep every required section present, but avoid exhaustive catalogs, long examples, and repeated caveats.
- Prefer concise paragraphs and tight bullets over long prose.
- Keep code sections to one compact code capsule.
- Do not spend tokens on self-review language; downstream quality passes are disabled for this run.
""".strip()

    def _log_handbook_stage(stage: str, usage: dict, extra_meta: dict | None = None) -> None:
        """Log a handbook generate stage to pipeline_logs. Never raises."""
        if not supabase:
            return
        try:
            meta = {
                "term": req.term,
                "source": source,
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
            }
            if usage.get("cached_tokens") is not None:
                meta["cached_tokens"] = usage["cached_tokens"]
            if usage.get("reasoning_tokens") is not None:
                meta["reasoning_tokens"] = usage["reasoning_tokens"]
            if usage.get("service_tier"):
                meta["service_tier"] = usage["service_tier"]
            if extra_meta:
                meta.update(extra_meta)
            supabase.table("pipeline_logs").insert({
                "run_id": log_run_id,
                "pipeline_type": stage,
                "status": "success",
                "input_summary": f"term={req.term}",
                "model_used": usage.get("model_used"),
                "tokens_used": usage.get("tokens_used"),
                "cost_usd": usage.get("cost_usd"),
                "debug_meta": meta,
            }).execute()
        except Exception as e:
            logger.warning("Failed to log handbook %s stage: %s", stage, e)

    # --- Build category-specific prompt blocks ---
    from services.agents.prompts_handbook_types import (
        build_artifact_policy_block,
        build_category_block,
        get_section_weight_guide,
        get_type_basic_guide,
        get_type_depth_guide,
    )

    primary_cat = categories_list[0] if categories_list else ""
    category_block = build_category_block(primary_cat)
    basic_type_guide = get_type_basic_guide(term_type, term_subtype)
    type_guide = get_type_depth_guide(term_type, term_subtype)
    section_weight_guide = get_section_weight_guide(term_type, primary_intent, term_subtype)
    basic_ko_system = GENERATE_BASIC_PROMPT
    if category_block:
        basic_ko_system += f"\n\n{category_block}"
    basic_ko_system += f"\n\n{basic_type_guide}"
    if section_weight_guide:
        basic_ko_system += f"\n\n{section_weight_guide}"
    if term_generation_override:
        basic_ko_focus_guide = str(term_generation_override.get("basic_ko_focus_guide", "")).strip()
        if basic_ko_focus_guide:
            basic_ko_system += f"\n\n{basic_ko_focus_guide}"
    if draft_smoke_mode:
        basic_ko_system += f"\n\n{draft_smoke_guide}"

    # --- Call 1: Meta + KO Basic (with retry if KO sections missing) ---
    for _call1_attempt in range(2):
        async def _call1_gen():
            return await client.chat.completions.create(
                **compat_create_kwargs(
                    model,
                    messages=[
                        {"role": "system", "content": basic_ko_system},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=generation_max_tokens,
                    prompt_cache_key="hb-generate-basic",
                    reasoning_effort=generation_reasoning_effort,
                    service_tier="flex",
                )
            )
        resp1 = await with_flex_retry(_call1_gen)
        basic_data = parse_ai_json(resp1.choices[0].message.content, "Handbook-generate-basic")
        usage1_attempt = extract_usage_metrics(resp1, model)
        if _call1_attempt == 0:
            usage1 = usage1_attempt
        else:
            usage1 = merge_usage_metrics(usage1, usage1_attempt)

        # Check if KO basic sections were generated
        has_ko_basic = bool(basic_data.get("basic_ko_1_plain", "").strip())
        if has_ko_basic:
            break
        if _call1_attempt == 0:
            logger.warning(
                "Handbook Call 1 for '%s': KO basic missing, retrying (attempt 2)",
                req.term,
            )

    logger.info(
        "Handbook generate call 1 (basic KO) for '%s': %d tokens, ko_present=%s",
        req.term, usage1.get("tokens_used", 0), has_ko_basic,
    )
    _log_handbook_stage("handbook.generate.basic", usage1)
    if term_generation_override:
        override_refs_ko = [dict(item) for item in term_generation_override.get("references_ko", [])]
        override_refs_en = [dict(item) for item in term_generation_override.get("references_en", [])]
        if override_refs_ko:
            basic_data["references_ko"] = override_refs_ko
        if override_refs_en:
            basic_data["references_en"] = override_refs_en
    reference_eval = _evaluate_reference_candidates(
        req.term,
        term_type,
        term_subtype,
        basic_data.get("references_ko", []),
        basic_data.get("references_en", []),
    )
    synced_refs_ko, synced_refs_en = _synchronize_reference_sets(
        reference_eval["accepted_references"],
        basic_data.get("references_ko", []),
        basic_data.get("references_en", []),
    )
    basic_data["references_ko"] = synced_refs_ko
    basic_data["references_en"] = synced_refs_en
    if reference_eval["blocked_hosts_found"]:
        warnings.append(
            "reference filter removed low-trust hosts: "
            + ", ".join(reference_eval["blocked_hosts_found"])
        )
    code_mode_meta = _build_code_mode_metadata(
        term_type,
        term_subtype,
        basic_data,
        brave_context,
        deep_context,
        reference_eval=reference_eval,
        primary_category=primary_cat,
    )
    if term_generation_override:
        code_mode_meta["code_mode_hint"] = str(term_generation_override.get("preferred_code_mode", "real-code"))
        code_mode_meta["reference_strength"] = str(reference_eval.get("reference_strength", "high"))
        code_mode_meta["has_official_spec_signal"] = bool(reference_eval.get("has_official_docs", True))
        code_mode_meta["has_clear_io_contract"] = True

    # deep_context and brave_context already fetched in parallel above
    logger.info(
        "Term '%s': tavily=%d chars, brave=%d chars, exa=%d chars",
        req.term, len(tavily_context), len(brave_context), len(deep_context),
    )

    # --- Call 2 (EN Basic) + Call 3 (KO Advanced) — PARALLEL ---
    # Both depend only on Call 1 output, so they can run concurrently.
    # user_prompt already includes Tavily + Brave + article context (applied to all calls)
    en_basic_prompt = (
        f"{user_prompt}\n\n"
        f"--- Context from Call 1 ---\n"
        f"Definition (KO): {basic_data.get('definition_ko', '')}\n"
        f"Definition (EN): {basic_data.get('definition_en', '')}"
    )

    definition_context = basic_data.get("definition_en", "") or req.definition_en
    definition_ko_context = basic_data.get("definition_ko", "") or req.definition_ko

    # Build Basic body context (post-redesign 7-section assembly).
    # Truncate each language to 3000 chars to keep total context budget reasonable
    # (Advanced prompt ~4k tokens + Basic context ~1.5k tokens, well under 16k max).
    basic_ko_body_for_ctx = _assemble_markdown(basic_data, BASIC_SECTIONS_KO)[:3000]
    basic_en_body_for_ctx = (
        _assemble_markdown(basic_data, BASIC_SECTIONS_EN)[:3000]
        if any(k.startswith("basic_en_") for k in basic_data)
        else "(Basic EN not yet generated — Call 2 runs in parallel)"
    )

    advanced_prompt = (
        f"{user_prompt}\n\n"
        f"--- Context from Call 1 ---\n"
        f"Definition (EN): {definition_context}\n"
        f"Definition (KO): {definition_ko_context}\n"
        f"Term Type: {term_type}\n"
        f"Term Subtype: {term_subtype or 'none'}\n"
        f"\n--- Basic KO body (DO NOT duplicate analogies, examples, or phrasing) ---\n"
        f"{basic_ko_body_for_ctx}\n"
        f"\n--- Basic EN body (DO NOT duplicate) ---\n"
        f"{basic_en_body_for_ctx}"
    )
    advanced_contexts: list[str] = []
    for field_name in ("advanced", "references"):
        selected = _select_source_context_for_field(term_type, term_subtype, field_name, source_bundle)
        if selected and selected not in advanced_contexts:
            advanced_contexts.append(selected)
    if advanced_contexts:
        advanced_prompt += (
            "\n\n--- Selected Reference Context for Advanced Sections ---\n"
            + "\n\n".join(advanced_contexts)
            + "\n\nUse these sources primarily for mechanism, the policy-selected technical artifact, tradeoffs, pitfalls, and references."
        )

    # Inject type-specific guides into system prompts
    type_guide = get_type_depth_guide(term_type, term_subtype)
    basic_type_guide = get_type_basic_guide(term_type, term_subtype)

    # Section weight guide based on type × intent
    primary_intent = intent_list[0] if intent_list else "understand"
    section_weight_guide = get_section_weight_guide(term_type, primary_intent, term_subtype)
    term_focus_guide = ""
    code_contract_guide = ""
    advanced_ko_focus_guide = ""
    artifact_policy_block = build_artifact_policy_block(
        term_type,
        term_subtype,
        primary_cat,
        str(code_mode_meta.get("code_mode_hint") or ""),
    )
    if term_generation_override:
        term_focus_guide = str(term_generation_override.get("advanced_focus_guide", "")).strip()
        code_contract_guide = str(term_generation_override.get("code_contract_guide", "")).strip()
        advanced_ko_focus_guide = str(term_generation_override.get("advanced_ko_focus_guide", "")).strip()

    # EN Basic: category block + basic type guide + section weight
    basic_en_system = GENERATE_BASIC_EN_PROMPT
    if category_block:
        basic_en_system += f"\n\n{category_block}"
    basic_en_system += f"\n\n{basic_type_guide}"
    if section_weight_guide:
        basic_en_system += f"\n\n{section_weight_guide}"
    if draft_smoke_mode:
        basic_en_system += f"\n\n{draft_smoke_guide}"

    # Advanced: category block + type depth guide + section weight
    adv_ko_system = GENERATE_ADVANCED_PROMPT
    if category_block:
        adv_ko_system += f"\n\n{category_block}"
    adv_ko_system += f"\n\n{type_guide}"
    if section_weight_guide:
        adv_ko_system += f"\n\n{section_weight_guide}"
    if artifact_policy_block:
        adv_ko_system += f"\n\n{artifact_policy_block}"
    if term_focus_guide:
        adv_ko_system += f"\n\n{term_focus_guide}"
    if advanced_ko_focus_guide:
        adv_ko_system += f"\n\n{advanced_ko_focus_guide}"
    if code_contract_guide:
        adv_ko_system += f"\n\n{code_contract_guide}"
    if draft_smoke_mode:
        adv_ko_system += f"\n\n{draft_smoke_guide}"
    adv_en_system = GENERATE_ADVANCED_EN_PROMPT
    if category_block:
        adv_en_system += f"\n\n{category_block}"
    adv_en_system += f"\n\n{type_guide}"
    if section_weight_guide:
        adv_en_system += f"\n\n{section_weight_guide}"
    if artifact_policy_block:
        adv_en_system += f"\n\n{artifact_policy_block}"
    if term_focus_guide:
        adv_en_system += f"\n\n{term_focus_guide}"
    if code_contract_guide:
        adv_en_system += f"\n\n{code_contract_guide}"
    if draft_smoke_mode:
        adv_en_system += f"\n\n{draft_smoke_guide}"

    async def _call2_gen():
        return await client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": basic_en_system},
                    {"role": "user", "content": en_basic_prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=generation_max_tokens,
                prompt_cache_key="hb-generate-en-basic",
                reasoning_effort=generation_reasoning_effort,
                service_tier="flex",
            )
        )

    async def _call3_gen():
        return await client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": adv_ko_system},
                    {"role": "user", "content": advanced_prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=generation_max_tokens,
                prompt_cache_key="hb-generate-advanced",
                reasoning_effort=generation_reasoning_effort,
                service_tier="flex",
            )
        )

    resp2, resp3 = await asyncio.gather(
        with_flex_retry(_call2_gen),
        with_flex_retry(_call3_gen),
    )

    en_basic_data = parse_ai_json(resp2.choices[0].message.content, "Handbook-generate-basic-en")
    usage2 = extract_usage_metrics(resp2, model)
    logger.info(
        "Handbook generate call 2 (basic EN) for '%s': %d tokens",
        req.term, usage2.get("tokens_used", 0),
    )
    _log_handbook_stage("handbook.generate.basic.en", usage2)

    advanced_ko_data = parse_ai_json(resp3.choices[0].message.content, "Handbook-generate-advanced-ko")
    usage3 = extract_usage_metrics(resp3, model)
    logger.info(
        "Handbook generate call 3 (advanced KO) for '%s': %d tokens",
        req.term, usage3.get("tokens_used", 0),
    )
    _log_handbook_stage("handbook.generate.advanced.ko", usage3)

    # --- Call 4 (EN Advanced) + Basic Self-Critique — PARALLEL ---
    basic_ko_preview = _build_section_preview(basic_data, "basic_ko_")
    basic_en_preview = _build_section_preview(en_basic_data, "basic_en_")

    # Build a Call 4-specific prompt that includes the actual EN Basic body now that
    # Call 2 has finished. This lets Call 4 (EN Advanced) explicitly differentiate
    # from the EN Basic that the reader will see right above it. Call 3 (KO Advanced)
    # already used `advanced_prompt` with a placeholder for EN Basic.
    basic_en_body_for_ctx_real = _assemble_markdown(en_basic_data, BASIC_SECTIONS_EN)[:3000]
    advanced_en_prompt = (
        f"{user_prompt}\n\n"
        f"--- Context from Call 1 ---\n"
        f"Definition (EN): {definition_context}\n"
        f"Definition (KO): {definition_ko_context}\n"
        f"Term Type: {term_type}\n"
        f"Term Subtype: {term_subtype or 'none'}\n"
        f"\n--- Basic KO body (DO NOT duplicate analogies, examples, or phrasing) ---\n"
        f"{basic_ko_body_for_ctx}\n"
        f"\n--- Basic EN body (DO NOT duplicate) ---\n"
        f"{basic_en_body_for_ctx_real}"
    )
    if advanced_contexts:
        advanced_en_prompt += (
            "\n\n--- Selected Reference Context for Advanced Sections ---\n"
            + "\n\n".join(advanced_contexts)
            + "\n\nUse these sources primarily for mechanism, the policy-selected technical artifact, tradeoffs, pitfalls, and references."
        )

    async def _call4_gen():
        return await client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": adv_en_system},
                    {"role": "user", "content": advanced_en_prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=generation_max_tokens,
                prompt_cache_key="hb-generate-en-advanced",
                reasoning_effort=generation_reasoning_effort,
                service_tier="flex",
            )
        )
    call4_task = with_flex_retry(_call4_gen)
    if req.skip_self_critique:
        resp4 = await call4_task
        basic_critique_result = (False, False, "", "", 0, 0, {})
    else:
        basic_critique_task = _self_critique_basic(
            req.term, term_type, basic_ko_preview, basic_en_preview, client, model,
            reference_context=f"{tavily_context}\n{brave_context}",
        )
        resp4, basic_critique_result = await asyncio.gather(call4_task, basic_critique_task)

    advanced_en_data = parse_ai_json(resp4.choices[0].message.content, "Handbook-generate-advanced-en")
    usage4 = extract_usage_metrics(resp4, model)
    logger.info(
        "Handbook generate call 4 (advanced EN) for '%s': %d tokens",
        req.term, usage4.get("tokens_used", 0),
    )
    _log_handbook_stage("handbook.generate.advanced.en", usage4)

    # --- Process basic self-critique results ---
    (
        basic_ko_needs, basic_en_needs,
        basic_ko_feedback, basic_en_feedback,
        basic_ko_score, basic_en_score,
        basic_critique_usage,
    ) = basic_critique_result
    logger.info(
        "Basic self-critique for '%s': ko_score=%d, en_score=%d, ko_needs=%s, en_needs=%s",
        req.term, basic_ko_score, basic_en_score, basic_ko_needs, basic_en_needs,
    )

    if basic_ko_needs and basic_ko_feedback:
        logger.info("Regenerating basic KO for '%s' with critique feedback", req.term)
        improved_ko_system = basic_ko_system + f"\n\n## Reviewer Feedback (MUST address):\n{basic_ko_feedback}"
        async def _call1b_gen():
            return await client.chat.completions.create(
                **compat_create_kwargs(
                    model,
                    messages=[
                        {"role": "system", "content": improved_ko_system},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=24000,
                    response_format={"type": "json_object"},
                    prompt_cache_key="hb-regen-basic",
                    reasoning_effort="high",
                    service_tier="flex",
                )
            )
        resp1b = await with_flex_retry(_call1b_gen)
        improved_basic = parse_ai_json(resp1b.choices[0].message.content, "Handbook-basic-ko-improved")
        for k, v in improved_basic.items():
            if k.startswith("basic_ko_"):
                basic_data[k] = v
        usage1b = extract_usage_metrics(resp1b, model)
        basic_critique_usage = merge_usage_metrics(basic_critique_usage, usage1b)
        _log_handbook_stage("handbook.generate.basic.ko.improved", usage1b)

    if basic_en_needs and basic_en_feedback:
        logger.info("Regenerating basic EN for '%s' with critique feedback", req.term)
        improved_en_system = basic_en_system + f"\n\n## Reviewer Feedback (MUST address):\n{basic_en_feedback}"
        async def _call2b_gen():
            return await client.chat.completions.create(
                **compat_create_kwargs(
                    model,
                    messages=[
                        {"role": "system", "content": improved_en_system},
                        {"role": "user", "content": en_basic_prompt},
                    ],
                    max_tokens=24000,
                    response_format={"type": "json_object"},
                    prompt_cache_key="hb-regen-en-basic",
                    reasoning_effort="high",
                    service_tier="flex",
                )
            )
        resp2b = await with_flex_retry(_call2b_gen)
        en_basic_data = parse_ai_json(resp2b.choices[0].message.content, "Handbook-basic-en-improved")
        usage2b = extract_usage_metrics(resp2b, model)
        basic_critique_usage = merge_usage_metrics(basic_critique_usage, usage2b)
        _log_handbook_stage("handbook.generate.basic.en.improved", usage2b)

    if basic_critique_usage:
        _log_handbook_stage("handbook.self_critique.basic", basic_critique_usage)

    # --- Self-critique advanced KO content ---
    adv_ko_preview = _build_section_preview(advanced_ko_data, "adv_ko_")
    reference_for_critique = "\n".join(
        chunk
        for chunk in [
            _select_source_context_for_field(term_type, term_subtype, "definition", source_bundle),
            _select_source_context_for_field(term_type, term_subtype, "advanced", source_bundle),
            _select_source_context_for_field(term_type, term_subtype, "references", source_bundle),
        ]
        if chunk
    )
    if req.skip_self_critique:
        needs_improvement, critique_feedback, critique_score, critique_usage = (False, "", 0, {})
    else:
        needs_improvement, critique_feedback, critique_score, critique_usage = (
            await _self_critique_advanced(
                req.term, term_type, adv_ko_preview, client, model,
                reference_context=reference_for_critique,
            )
        )
    logger.info(
        "Self-critique for '%s': score=%d, needs_improvement=%s",
        req.term, critique_score, needs_improvement,
    )

    # Only regenerate if score is below threshold (not just needs_improvement flag)
    if needs_improvement and critique_feedback and critique_score < 75:
        logger.info("Regenerating advanced KO for '%s' with critique feedback", req.term)
        improved_system = f"{adv_ko_system}\n\n## Reviewer Feedback (MUST address these):\n{critique_feedback}"
        async def _call3b_gen():
            return await client.chat.completions.create(
                **compat_create_kwargs(
                    model,
                    messages=[
                        {"role": "system", "content": improved_system},
                        {"role": "user", "content": advanced_prompt},
                    ],
                    max_tokens=24000,
                    response_format={"type": "json_object"},
                    prompt_cache_key="hb-regen-advanced",
                    reasoning_effort="high",
                    service_tier="flex",
                )
            )
        resp3b = await with_flex_retry(_call3b_gen)
        advanced_ko_data = parse_ai_json(resp3b.choices[0].message.content, "Handbook-adv-ko-improved")
        usage3b = extract_usage_metrics(resp3b, model)
        critique_usage = merge_usage_metrics(critique_usage, usage3b)
        _log_handbook_stage("handbook.generate.advanced.ko.improved", usage3b)

    if critique_usage:
        _log_handbook_stage("handbook.self_critique", critique_usage)

    # --- Self-critique advanced EN content ---
    adv_en_preview = _build_section_preview(advanced_en_data, "adv_en_")
    if req.skip_self_critique:
        en_needs_improvement, en_critique_feedback, en_critique_score, en_critique_usage = (False, "", 0, {})
    else:
        en_needs_improvement, en_critique_feedback, en_critique_score, en_critique_usage = (
            await _self_critique_advanced(
                req.term, term_type, adv_en_preview, client, model,
                reference_context=reference_for_critique,
            )
        )
    logger.info(
        "Self-critique EN for '%s': score=%d, needs_improvement=%s",
        req.term, en_critique_score, en_needs_improvement,
    )

    if en_needs_improvement and en_critique_feedback and en_critique_score < 75:
        logger.info("Regenerating advanced EN for '%s' with critique feedback", req.term)
        improved_en_adv_system = f"{adv_en_system}\n\n## Reviewer Feedback (MUST address these):\n{en_critique_feedback}"
        async def _call4b_gen():
            return await client.chat.completions.create(
                **compat_create_kwargs(
                    model,
                    messages=[
                        {"role": "system", "content": improved_en_adv_system},
                        {"role": "user", "content": advanced_en_prompt},
                    ],
                    max_tokens=24000,
                    response_format={"type": "json_object"},
                    prompt_cache_key="hb-regen-en-advanced",
                    reasoning_effort="high",
                    service_tier="flex",
                )
            )
        resp4b = await with_flex_retry(_call4b_gen)
        advanced_en_data = parse_ai_json(resp4b.choices[0].message.content, "Handbook-adv-en-improved")
        usage4b = extract_usage_metrics(resp4b, model)
        en_critique_usage = merge_usage_metrics(en_critique_usage, usage4b)
        _log_handbook_stage("handbook.generate.advanced.en.improved", usage4b)

    if en_critique_usage:
        _log_handbook_stage("handbook.self_critique.en", en_critique_usage)

    # --- Merge results ---
    raw_data = {
        **basic_data,
        **en_basic_data,
        **advanced_ko_data,
        **advanced_en_data,
        **code_mode_meta,
        "term_type": term_type,
        "term_subtype": term_subtype,
        "facet_intent": intent_list,
        "facet_volatility": volatility,
        "facet_type_confidence": type_confidence,
    }
    merged_usage = merge_usage_metrics(
        merge_usage_metrics(usage1, usage2),
        merge_usage_metrics(usage3, usage4),
    )
    if basic_critique_usage:
        merged_usage = merge_usage_metrics(merged_usage, basic_critique_usage)
    if critique_usage:
        merged_usage = merge_usage_metrics(merged_usage, critique_usage)
    if en_critique_usage:
        merged_usage = merge_usage_metrics(merged_usage, en_critique_usage)

    # --- Assemble section keys into markdown ---
    data = _assemble_all_sections(raw_data)
    final_refs_ko, final_refs_en = _synchronize_reference_sets(
        reference_eval["accepted_references"],
        data.get("references_ko", []),
        data.get("references_en", []),
    )
    data["references_ko"] = final_refs_ko
    data["references_en"] = final_refs_en
    data["reference_strength"] = str(reference_eval.get("reference_strength", data.get("reference_strength", "")))
    data["has_official_spec_signal"] = bool(reference_eval.get("has_official_docs", data.get("has_official_spec_signal", False)))
    if term_generation_override:
        data["code_mode_hint"] = str(term_generation_override.get("preferred_code_mode", data.get("code_mode_hint", "")))

    safety_warnings = _apply_handbook_safety_postprocess(data)
    remediation_status = "not_requested"
    remediation_meta: dict = {
        "status": remediation_status,
        "issues_before": _build_handbook_remediation_issues(data, safety_warnings),
        "issues_after": _build_handbook_remediation_issues(data, safety_warnings),
        "removed_claims": [],
        "applied_fields": [],
    }
    if req.remediate_after_generation:
        try:
            remediation_usage, remediation_meta = await _run_handbook_targeted_remediation(
                req.term,
                data,
                safety_warnings,
                client,
                model,
            )
            remediation_status = str(remediation_meta.get("status") or "applied")
            if remediation_usage:
                merged_usage = merge_usage_metrics(merged_usage, remediation_usage)
                _log_handbook_stage(
                    "handbook.remediate.targeted",
                    remediation_usage,
                    extra_meta={
                        "remediation_status": remediation_status,
                        "applied_fields": remediation_meta.get("applied_fields", []),
                        "removed_claims": remediation_meta.get("removed_claims", []),
                    },
                )
            safety_warnings = _apply_handbook_safety_postprocess(data)
        except Exception as e:
            remediation_status = "failed"
            remediation_meta = {
                **remediation_meta,
                "status": remediation_status,
                "error": str(e),
            }
            logger.warning("Handbook targeted remediation failed for '%s': %s", req.term, e)
    warnings.extend(safety_warnings)

    try:
        GenerateTermResult.model_validate(data)
    except ValidationError as e:
        for err in e.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            warnings.append(f"{field}: {err['msg']}")
        logger.warning("Handbook generate validation: %s", warnings)

    # Check section completeness (including empty detection)
    # Basic: 7 sections. Advanced: 7 sections. (Post-redesign, both languages.)
    _basic_expected = {"ko": 7, "en": 7}
    expected_advanced = _expected_advanced_sections(
        data.get("code_mode_hint"),
        data.get("term_type"),
        data.get("term_subtype"),
    )
    for lang in ("ko", "en"):
        basic_content = data.get(f"body_basic_{lang}", "")
        expected_basic = _basic_expected[lang]
        if not basic_content.strip():
            warnings.append(f"body_basic_{lang}: EMPTY — content generation failed")
        elif basic_content.count("## ") < expected_basic:
            warnings.append(
                f"body_basic_{lang}: only {basic_content.count('## ')}/{expected_basic} sections"
            )
        adv_content = data.get(f"body_advanced_{lang}", "")
        if not adv_content.strip():
            warnings.append(f"body_advanced_{lang}: EMPTY — content generation failed")
        elif adv_content.count("## ") < expected_advanced:
            warnings.append(
                f"body_advanced_{lang}: only {adv_content.count('## ')}/{expected_advanced} sections"
            )

    if not req.skip_post_generation_checks:
        # Post-processing step 1: Validate reference URLs in advanced sections
        for field in ("body_advanced_ko", "body_advanced_en"):
            if data.get(field):
                data[field] = await _validate_ref_urls(data[field])

        # Post-processing step 2: Entity verification (detect hallucinated proper nouns)
        all_generated = " ".join(
            data.get(f, "") for f in ("body_basic_ko", "body_basic_en", "body_advanced_ko", "body_advanced_en")
        )
        all_references = f"{tavily_context}\n{brave_context}\n{deep_context}\n{article_context}"
        try:
            novel_entities = await _extract_novel_entities(
                all_generated, all_references, client, settings.openai_model_nano,
            )
            if novel_entities:
                verification_results = await _verify_entities(novel_entities)
                unverified = [v for v in verification_results if not v["verified"]]
                if unverified:
                    entity_names = [v["entity"] for v in unverified]
                    warnings.append(f"Unverified entities detected: {', '.join(entity_names)}")
                    logger.warning(
                        "Handbook '%s': %d unverified entities: %s",
                        req.term, len(unverified), entity_names,
                    )
        except Exception as e:
            logger.warning("Entity verification failed for '%s': %s", req.term, e)

    # ── Hybrid quality scoring ──────────────────────────────────────────
    # Phase 1: Structural penalties (code, always runs, free, <1ms)
    structural_penalty, structural_warnings = _check_handbook_structural_penalties(data)
    warnings.extend(structural_warnings)

    # Metadata fields (written regardless of quality check)
    data["term_type"] = term_type
    data["term_subtype"] = term_subtype
    data["facet_intent"] = intent_list
    data["facet_volatility"] = volatility
    data["facet_type_confidence"] = type_confidence

    # Phase 2: Semantic quality via LLM (optional, costs ~$0.10/term)
    semantic_score = None
    semantic_breakdown = {}
    basic_semantic_score = None
    basic_semantic_breakdown = {}

    if not req.skip_quality_check:
        # Advanced semantic check
        adv_combined = _build_bilingual_judge_content(
            data.get("body_advanced_ko", ""),
            data.get("body_advanced_en", ""),
            max_chars_per_locale=8000,
        )
        if adv_combined.strip():
            try:
                semantic_score, semantic_breakdown, quality_usage = await _check_handbook_quality(
                    req.term, term_type, adv_combined, client,
                )
                if quality_usage:
                    merged_usage = merge_usage_metrics(merged_usage, quality_usage)
                if semantic_score is not None:
                    _log_handbook_stage("handbook.quality_check", quality_usage or {},
                                        extra_meta={"semantic_score": semantic_score, "term_type": term_type})
            except Exception as e:
                logger.warning("Advanced quality check failed for '%s': %s", req.term, e)

        # Basic semantic check
        basic_combined = _build_bilingual_judge_content(
            data.get("body_basic_ko", ""),
            data.get("body_basic_en", ""),
            max_chars_per_locale=4000,
        )
        if basic_combined.strip():
            try:
                basic_semantic_score, basic_semantic_breakdown, basic_quality_usage = (
                    await _check_basic_quality(req.term, term_type, basic_combined, client)
                )
                if basic_quality_usage:
                    merged_usage = merge_usage_metrics(merged_usage, basic_quality_usage)
                if basic_semantic_score is not None:
                    _log_handbook_stage("handbook.quality_check.basic", basic_quality_usage or {},
                                        extra_meta={"basic_semantic_score": basic_semantic_score})
            except Exception as e:
                logger.warning("Basic quality check failed for '%s': %s", req.term, e)

    # Phase 3: Combine scores (news pipeline pattern: semantic - penalty)
    def _combine_quality(semantic: int | None, penalty: int) -> int:
        if semantic is not None:
            return max(0, semantic - penalty)
        return max(0, 100 - penalty * 2)

    def _grade(score: int) -> str:
        if score >= 85:
            return "A"
        if score >= 70:
            return "B"
        if score >= 55:
            return "C"
        return "D"

    adv_final = _combine_quality(semantic_score, structural_penalty)
    basic_final = _combine_quality(basic_semantic_score, structural_penalty)

    data["quality"] = {
        "advanced": {
            "total": adv_final,
            "grade": _grade(adv_final),
            "structural_penalty": structural_penalty,
            "structural_warnings": structural_warnings,
            "semantic_score": semantic_score,
            "semantic_breakdown": semantic_breakdown if semantic_score is not None else None,
            "method": "hybrid" if semantic_score is not None else "structural-only",
        },
        "basic": {
            "total": basic_final,
            "grade": _grade(basic_final),
            "semantic_score": basic_semantic_score,
            "semantic_breakdown": basic_semantic_breakdown if basic_semantic_score is not None else None,
            "method": "hybrid" if basic_semantic_score is not None else "structural-only",
        },
    }

    # Legacy compatibility: keep top-level quality_score for existing consumers
    data["quality_score"] = adv_final
    data["basic_quality_score"] = basic_final
    generation_gate = _build_generation_gate(
        adv_final,
        basic_final,
        type_confidence,
        structural_penalty,
    )
    data["generation_gate"] = generation_gate
    if generation_gate["status"] != "pass":
        warnings.append(
            f"Generation gate: {generation_gate['status']} ({', '.join(generation_gate['reasons'])})"
        )

    # Grade-based warnings
    if adv_final < 55:
        warnings.append(f"Advanced quality: {adv_final}/100 ({_grade(adv_final)}) — regen recommended")
    elif adv_final < 70:
        warnings.append(f"Advanced quality: {adv_final}/100 ({_grade(adv_final)}) — review recommended")
    if basic_final < 55:
        warnings.append(f"Basic quality: {basic_final}/100 ({_grade(basic_final)}) — regen recommended")
    elif basic_final < 70:
        warnings.append(f"Basic quality: {basic_final}/100 ({_grade(basic_final)}) — review recommended")

    logger.info(
        "Handbook quality for '%s': adv=%d/%s basic=%d/%s (structural_penalty=%d, method=%s)",
        req.term, adv_final, _grade(adv_final), basic_final, _grade(basic_final),
        structural_penalty, data["quality"]["advanced"]["method"],
    )

    # Record to dedicated quality scores table
    if supabase:
        try:
            import re as _re
            term_slug = _re.sub(r'[^a-z0-9]+', '-', req.term.lower().strip()).strip('-')

            # Resolve actual UUID — batch scripts use fake term_ids like "batch-regen-xxx"
            actual_id = None
            if req.term_id:
                try:
                    import uuid
                    uuid.UUID(req.term_id)
                    actual_id = req.term_id
                except ValueError:
                    pass
            if not actual_id:
                row = supabase.table("handbook_terms").select("id").eq("slug", term_slug).limit(1).execute()
                if row.data:
                    actual_id = row.data[0]["id"]

            base_row = {"term_slug": term_slug, "term_type": term_type, "source": source}
            if actual_id:
                base_row["term_id"] = actual_id

            quality_data = data.get("quality", {})
            adv_q = quality_data.get("advanced", {})
            basic_q = quality_data.get("basic", {})

            adv_score = _normalize_quality_score_value(adv_q.get("total"))
            if adv_score is not None:
                supabase.table("handbook_quality_scores").insert({
                    **base_row,
                    "score": adv_score,
                    "breakdown": {"level": "advanced", **adv_q},
                }).execute()
            basic_score = _normalize_quality_score_value(basic_q.get("total"))
            if basic_score is not None:
                supabase.table("handbook_quality_scores").insert({
                    **base_row,
                    "score": basic_score,
                    "breakdown": {"level": "basic", **basic_q},
                }).execute()
        except Exception as e:
            logger.warning("Failed to record handbook quality score: %s", e)

    # Post-process: convert single-dollar math $...$ to double-dollar $$...$$
    # Single $ conflicts with currency in the markdown renderer (singleDollarTextMath=false)
    import re
    def _fix_single_dollar_math(text: str) -> str:
        """Convert $...$ math to $$...$$ while preserving currency like $2."""
        result = []
        i = 0
        while i < len(text):
            if text[i] == '$' and (i + 1 < len(text)) and text[i + 1] != '$':
                # Possible single-dollar math start
                # Check if it looks like currency ($2, $15, $100M)
                if i + 1 < len(text) and text[i + 1].isdigit():
                    result.append(text[i])
                    i += 1
                    continue
                # Find closing $
                end = text.find('$', i + 1)
                if end > i + 1:
                    inner = text[i + 1:end]
                    # Only convert if inner contains math-like characters
                    has_math = any(c in inner for c in ('_', '^', '{', '\\')) or re.search(r'[A-Z]\(|\\[a-z]|[=+<>]|\d[a-z]', inner)
                    if has_math and end + 1 < len(text) and text[end + 1] == '$':
                        # Already $$, skip
                        result.append(text[i])
                        i += 1
                    elif has_math:
                        result.append('$$')
                        result.append(inner)
                        result.append('$$')
                        i = end + 1
                        continue
                    else:
                        result.append(text[i])
                        i += 1
                        continue
                else:
                    result.append(text[i])
                    i += 1
            elif text[i] == '$' and (i + 1 < len(text)) and text[i + 1] == '$':
                # Already double dollar, skip both
                result.append('$$')
                i += 2
                # Find closing $$
                close = text.find('$$', i)
                if close >= 0:
                    result.append(text[i:close])
                    result.append('$$')
                    i = close + 2
                continue
            else:
                result.append(text[i])
                i += 1
        return ''.join(result)

    _BACKSLASH_TEXT_BRACE = "\x5ctext{"  # \text{ — avoids \t being parsed as tab

    def _clean_math_blocks(text: str) -> str:
        """Remove code artifacts accidentally embedded inside LaTeX math blocks.

        Handles cases where LLM mixes Python code into LaTeX, e.g.:
        \\text{cos").replace("\\n", " ")\\text{ine} → \\text{cosine}
        """
        tex_marker = _BACKSLASH_TEXT_BRACE  # \text{
        code_artifacts = ('.replace(', '.join(', '.split(', '.strip(', '.format(')
        result = text
        for artifact in code_artifacts:
            art_idx = result.find(artifact)
            while art_idx != -1:
                before = result[:art_idx]
                text_start = before.rfind(tex_marker)
                if text_start == -1:
                    break
                after_art = result[art_idx:]
                next_text_rel = after_art.find(tex_marker)
                if next_text_rel == -1:
                    break
                next_text_abs = art_idx + next_text_rel
                next_brace_start = next_text_abs + len(tex_marker)
                next_brace_end = result.find('}', next_brace_start)
                if next_brace_end == -1:
                    break
                first_content_start = text_start + len(tex_marker)
                first_alpha = ''.join(c for c in result[first_content_start:art_idx] if c.isalpha())
                second_content = result[next_brace_start:next_brace_end]
                merged = tex_marker + first_alpha + second_content + '}'
                result = result[:text_start] + merged + result[next_brace_end + 1:]
                art_idx = result.find(artifact)
        return result

    for key, val in data.items():
        if isinstance(val, str) and '$' in val:
            converted = _fix_single_dollar_math(val)
            converted = _clean_math_blocks(converted)
            if converted != val:
                logger.info("Fixed math formatting in field '%s'", key)
                data[key] = converted

    # Post-process: remove floating citation numbers [1], [2] etc. outside code blocks
    def _strip_floating_citations(text: str) -> str:
        """Remove [N] citation markers that aren't in code blocks or reference headers."""
        lines = text.split('\n')
        result_lines = []
        in_code = False
        for line in lines:
            if line.strip().startswith('```'):
                in_code = not in_code
                result_lines.append(line)
                continue
            if in_code:
                result_lines.append(line)
                continue
            # Skip reference header lines like "### [1] Title"
            if re.match(r'^#{1,4}\s+\[\d+\]', line):
                result_lines.append(line)
                continue
            # Remove (\[N]) and \[N] patterns (escaped bracket with optional parens)
            cleaned = re.sub(r'\s*\(\\?\[\d{1,2}\]\)', '', line)  # (\[2]) or ([2])
            # Remove standalone \[N]
            cleaned = re.sub(r'\s*\\\[\d{1,2}\]', '', cleaned)
            # Remove [N] not followed by ( — not a markdown link
            cleaned = re.sub(r'\s*\[(\d{1,2})\](?!\()', '', cleaned)
            # Remove (see [N]), (per [N]) including bracket variants
            cleaned = re.sub(r'\s*\((?:see |per )\[?\d{1,2}\]?\)', '', cleaned)
            result_lines.append(cleaned)
        return '\n'.join(result_lines)

    for field in ("body_advanced_ko", "body_advanced_en"):
        if data.get(field):
            original = data[field]
            cleaned = _strip_floating_citations(original)
            if cleaned != original:
                removed = len(original) - len(cleaned)
                logger.info("Stripped floating citations from '%s' (%d chars removed)", field, removed)
                data[field] = cleaned

    final_remediation_issues = _build_handbook_remediation_issues(data, warnings)
    admin_quality_gate = _build_admin_draft_quality_gate(
        final_remediation_issues,
        data.get("generation_gate"),
    )
    data["_remediation_issues"] = final_remediation_issues
    data["_quality_gate"] = admin_quality_gate
    data["_remediation_status"] = remediation_status
    data["_remediation_meta"] = remediation_meta

    # Add search source metadata for UI display.
    # Stored inside the result dict (non-underscore key) alongside other
    # metadata like term_type / facet_intent. The router also propagates
    # this to the top-level HandbookAdviseResponse.search_sources field
    # so API consumers see a consistent contract.
    search_sources = []
    if tavily_context:
        search_sources.append("Tavily")
    if brave_context:
        search_sources.append("Brave")
    if deep_context:
        search_sources.append("Exa")
    data["search_sources"] = search_sources
    # Ensure facet data is always present (for pipeline DB storage)
    data.setdefault("term_type", term_type)
    data.setdefault("term_subtype", term_subtype)
    data.setdefault("facet_intent", intent_list)
    data.setdefault("facet_volatility", volatility)

    logger.info(
        "Handbook generate completed for '%s', total_tokens=%d, warnings=%d, sources=%s",
        req.term, merged_usage.get("tokens_used", 0), len(warnings), search_sources,
    )
    return data, merged_usage, warnings


# --- Pipeline Term Extraction Helpers ---

async def extract_terms_from_content(content: str) -> tuple[list[dict], dict]:
    """Extract technical terms from article content. Uses light model for cost.

    Returns (terms_list, usage_metrics_dict).
    """
    client = get_openai_client()
    model = getattr(settings, "openai_model_nano")

    # Truncate to first 24000 chars for extraction (gpt-5-nano supports 128K)
    preview = content[:24000]
    if len(content) > 24000:
        preview += "\n[... truncated]"

    resp = await client.chat.completions.create(
        **compat_create_kwargs(
            model,
            messages=[
                {"role": "system", "content": EXTRACT_TERMS_PROMPT},
                {"role": "user", "content": preview},
            ],
            response_format={"type": "json_object"},
            max_tokens=2048,
            prompt_cache_key="hb-extract-terms",
        )
    )
    data = parse_ai_json(resp.choices[0].message.content, "Extract-terms")
    usage = extract_usage_metrics(resp, model)

    try:
        ExtractTermsResult.model_validate(data)
    except ValidationError as e:
        logger.warning("Extract terms validation soft-fail: %s", e)

    terms = data.get("terms", [])
    logger.info("Extracted %d terms, tokens=%d", len(terms), usage.get("tokens_used", 0))
    return terms, usage


async def gate_candidate_terms(
    candidates: list[dict], existing_terms: list[str],
) -> list[dict]:
    """Evaluate candidate terms through the handbook gate before generation.

    Uses nano model to classify candidates as accept, queue, or reject.
    Returns one decision object per candidate term.
    """
    if not candidates:
        return []

    from services.agents.prompts_advisor import TERM_GATE_PROMPT

    client = get_openai_client()
    model = getattr(settings, "openai_model_nano")

    existing_str = ", ".join(existing_terms[:500])  # cap at 500 for token budget

    prompt = TERM_GATE_PROMPT.format(existing_terms=existing_str)
    user_msg = json.dumps({"candidates": candidates}, ensure_ascii=False)

    try:
        resp = await client.chat.completions.create(
            **build_completion_kwargs(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=1000,
                response_format={"type": "json_object"},
                prompt_cache_key="hb-gate",
            )
        )
        data = parse_ai_json(resp.choices[0].message.content, "term-gate")
        decisions = {d["term"]: d for d in data.get("decisions", [])}

        resolved_decisions: list[dict] = []
        accepted_count = 0
        queued_count = 0
        rejected_count = 0
        for candidate in candidates:
            term = candidate.get("term", "")
            decision_info = decisions.get(term, {})
            decision = str(decision_info.get("decision", "accept")).lower()
            if decision not in {"accept", "queue", "reject"}:
                decision = "accept"
            reason = decision_info.get("reason", "")
            resolved_decisions.append({
                "term": term,
                "decision": decision,
                "reason": reason,
            })
            if decision == "reject":
                rejected_count += 1
            elif decision == "queue":
                queued_count += 1
            else:
                accepted_count += 1

        logger.info(
            "Term gate: %d candidates -> %d accepted, %d queued, %d rejected",
            len(candidates), accepted_count, queued_count, rejected_count,
        )
        return resolved_decisions
    except Exception as e:
        logger.warning("Term gate failed, accepting all candidates: %s", e)
        return [
            {
                "term": candidate.get("term", ""),
                "decision": "accept",
                "reason": "gate failure fallback",
            }
            for candidate in candidates
        ]


async def generate_term_content(
    term_name: str, korean_name: str = "", source: str = "pipeline",
    article_context: str = "",
    categories: list[str] | None = None,
    term_type_hint: str = "",
    log_run_id: str | None = None,
    skip_quality_check: bool = False,
    skip_self_critique: bool = False,
    skip_post_generation_checks: bool = False,
    remediate_after_generation: bool = False,
) -> tuple[dict, dict]:
    """Generate full content for a handbook term. Used by pipeline auto-creation.

    Args:
        source: "pipeline" (auto-extraction) or "manual" (admin editor)
        article_context: source news article text for grounding (prevents hallucination)
        categories: pre-classified categories for category-aware search queries

    Returns (content_data, usage_metrics_dict).
    """
    req = HandbookAdviseRequest(
        action="generate",
        term_id="",
        term=term_name,
        korean_name=korean_name,
        categories=categories or [],
        term_type_hint=term_type_hint,
        skip_quality_check=skip_quality_check,
        skip_self_critique=skip_self_critique,
        skip_post_generation_checks=skip_post_generation_checks,
        remediate_after_generation=remediate_after_generation,
    )
    client = get_openai_client()
    model = getattr(settings, "openai_model_main")
    data, usage, warnings = await _run_generate_term(
        req, client, model, source=source, article_context=article_context, log_run_id=log_run_id,
    )
    if warnings:
        data["_warnings"] = warnings
    return data, usage
