"""AI Advisor agent handlers — post actions + deep verify + handbook."""

import asyncio
import logging
import re

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
from services.agents.client import build_completion_kwargs, extract_usage_metrics, get_openai_client, merge_usage_metrics, parse_ai_json
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
        "temperature": 0.3,
        "validator": GenerateResult,
    },
    "seo": {
        "model_attr": "openai_model_light",
        "prompt_fn": get_seo_prompt,
        "max_tokens": 2048,
        "temperature": 0.5,
        "validator": SeoResult,
    },
    "review": {
        "model_attr": "openai_model_light",
        "prompt_fn": get_review_prompt,
        "max_tokens": 2048,
        "temperature": 0.2,
        "validator": ReviewResult,
    },
    "factcheck": {
        "model_attr": "openai_model_reasoning",
        "prompt": FACTCHECK_SYSTEM_PROMPT,
        "max_tokens": 4096,
        "temperature": 0.2,
        "validator": FactcheckResult,
    },
    "conceptcheck": {
        "model_attr": "openai_model_reasoning",
        "prompt": CONCEPTCHECK_SYSTEM_PROMPT,
        "max_tokens": 2048,
        "temperature": 0.2,
        "validator": ConceptCheckResult,
    },
    "voicecheck": {
        "model_attr": "openai_model_light",
        "prompt": VOICECHECK_SYSTEM_PROMPT,
        "max_tokens": 2048,
        "temperature": 0.3,
        "validator": VoiceCheckResult,
    },
    "retrocheck": {
        "model_attr": "openai_model_light",
        "prompt": RETROCHECK_SYSTEM_PROMPT,
        "max_tokens": 2048,
        "temperature": 0.2,
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
        temperature=config["temperature"],
        response_format={"type": "json_object"},
    )
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
    resp1 = await client.chat.completions.create(
        **build_completion_kwargs(
            model=model,
            messages=[
                {"role": "system", "content": DEEPVERIFY_CLAIM_EXTRACT_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=2048,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
    )
    claims_data = parse_ai_json(resp1.choices[0].message.content, "DeepVerify-extract")
    total_tokens += resp1.usage.completion_tokens if resp1.usage else 0
    claims = claims_data.get("claims", [])

    if not claims:
        return {
            "claims": [],
            "broken_links": [],
            "overall_confidence": "high",
            "confidence_reason": "No verifiable claims found in the content",
        }, model, total_tokens

    # Step 2: Search each claim via Tavily
    search_results = {}
    if settings.tavily_api_key:
        from tavily import TavilyClient
        tavily = TavilyClient(api_key=settings.tavily_api_key)
        loop = asyncio.get_running_loop()

        async def search_claim(claim_text: str) -> list[dict]:
            try:
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
                logger.warning("Tavily search failed for claim: %s", e)
                return []

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

    resp2 = await client.chat.completions.create(
        **build_completion_kwargs(
            model=model,
            messages=[
                {"role": "system", "content": DEEPVERIFY_VERIFY_PROMPT},
                {"role": "user", "content": verify_prompt},
            ],
            max_tokens=4096,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
    )
    verify_data = parse_ai_json(resp2.choices[0].message.content, "DeepVerify-verify")
    total_tokens += resp2.usage.completion_tokens if resp2.usage else 0

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
        f"Categories: {', '.join(req.categories)}" if req.categories else None,
    ]
    # Include available content
    for lang in ("ko", "en"):
        defn = getattr(req, f"definition_{lang}", "")
        basic = getattr(req, f"body_basic_{lang}", "")
        advanced = getattr(req, f"body_advanced_{lang}", "")
        if any([defn, basic, advanced]):
            parts.append(f"\n--- Content ({lang.upper()}) ---")
            if defn:
                parts.append(f"Definition: {defn}")
            if basic:
                parts.append(f"Body (Basic):\n{basic}")
            if advanced:
                parts.append(f"Body (Advanced):\n{advanced}")
    return "\n".join(p for p in parts if p is not None)


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
        model=model,
        messages=[
            {"role": "system", "content": RELATED_TERMS_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=2048,
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
        model=model,
        messages=[
            {"role": "system", "content": TRANSLATE_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=4096,
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


async def _search_term_context(term: str) -> str:
    """Search web for term context using Tavily. Returns formatted reference text."""
    if not settings.tavily_api_key:
        return ""
    try:
        tavily = TavilyClient(api_key=settings.tavily_api_key)
        loop = asyncio.get_running_loop()
        results = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: tavily.search(
                    query=f"{term} AI technology explained",
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
            content = r.get("content", "")[:600]
            parts.append(f"### [{i}] {title}\nURL: {url}\n{content}")
        return "## Reference Materials (from web search)\n\n" + "\n\n".join(parts)
    except Exception as e:
        logger.warning("Tavily search failed for '%s': %s", term, e)
        return ""


async def _classify_term_type(term: str, categories: list[str], client, model_light: str) -> str:
    """Classify term into one of 10 types using gpt-4o-mini."""
    from services.agents.prompts_handbook_types import CLASSIFY_TERM_PROMPT, TERM_TYPES

    user_msg = f"Term: {term}\nCategories: {', '.join(categories)}"
    try:
        resp = await client.chat.completions.create(
            model=model_light,
            messages=[
                {"role": "system", "content": CLASSIFY_TERM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=100,
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = parse_ai_json(resp.choices[0].message.content, "term-classify")
        term_type = data.get("type", "concept_theory")
        if term_type not in TERM_TYPES:
            term_type = "concept_theory"
        return term_type
    except Exception as e:
        logger.warning("Term classification failed for '%s': %s", term, e)
        return "concept_theory"


async def _self_critique_advanced(
    term: str, term_type: str, advanced_content: str,
    client, model: str,
) -> tuple[bool, str, int, dict]:
    """Self-critique advanced content. Returns (needs_improvement, feedback, score, usage)."""
    from services.agents.prompts_handbook_types import SELF_CRITIQUE_PROMPT

    reasoning_model = settings.openai_model_light  # gpt-4.1-mini (o4-mini returns empty)
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
                temperature=0.2,
                response_format={"type": "json_object"},
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
        usage = extract_usage_metrics(resp, reasoning_model)
        return needs, feedback, score, usage
    except Exception as e:
        logger.warning("Self-critique failed for '%s': %s", term, e)
        return False, "", 50, {}


async def _check_handbook_quality(
    term: str, term_type: str, advanced_content: str, client,
) -> tuple[int, dict, dict]:
    """Score handbook advanced quality. Returns (score, breakdown, usage)."""
    from services.agents.prompts_handbook_types import HANDBOOK_QUALITY_CHECK_PROMPT

    system = HANDBOOK_QUALITY_CHECK_PROMPT.format(term=term, term_type=term_type)
    reasoning_model = settings.openai_model_light  # gpt-4.1-mini (o4-mini returns empty)
    try:
        resp = await client.chat.completions.create(
            **build_completion_kwargs(
                model=reasoning_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": advanced_content[:6000]},
                ],
                max_tokens=500,
                temperature=0,
                response_format={"type": "json_object"},
            )
        )
        data = parse_ai_json(resp.choices[0].message.content, "handbook-quality")
        score = data.get("score", 50)
        usage = extract_usage_metrics(resp, reasoning_model)
        return score, data, usage
    except Exception as e:
        logger.warning("Handbook quality check failed for '%s': %s", term, e)
        return 50, {}, {}


async def _self_critique_basic(
    term: str, term_type: str,
    basic_ko_content: str, basic_en_content: str,
    client, model: str,
) -> tuple[bool, bool, str, str, int, int, dict]:
    """Self-critique basic KO+EN content in one call (gpt-4.1-mini).

    Returns (ko_needs, en_needs, ko_feedback, en_feedback,
             ko_score, en_score, usage).
    """
    from services.agents.prompts_handbook_types import BASIC_SELF_CRITIQUE_PROMPT

    light_model = settings.openai_model_light
    system = BASIC_SELF_CRITIQUE_PROMPT.format(term=term, term_type=term_type)
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
                temperature=0.2,
                response_format={"type": "json_object"},
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
        usage = extract_usage_metrics(resp, light_model)
        return ko_needs, en_needs, ko_feedback, en_feedback, ko_score, en_score, usage
    except Exception as e:
        logger.warning("Basic self-critique failed for '%s': %s", term, e)
        return False, False, "", "", 50, 50, {}


async def _check_basic_quality(
    term: str, term_type: str, basic_content: str, client,
) -> tuple[int, dict, dict]:
    """Score handbook basic quality. Returns (score, breakdown, usage)."""
    from services.agents.prompts_handbook_types import BASIC_QUALITY_CHECK_PROMPT

    system = BASIC_QUALITY_CHECK_PROMPT.format(term=term, term_type=term_type)
    reasoning_model = settings.openai_model_light  # gpt-4.1-mini (consistent with advanced quality check)
    try:
        resp = await client.chat.completions.create(
            **build_completion_kwargs(
                model=reasoning_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": basic_content[:6000]},
                ],
                max_tokens=500,
                temperature=0,
                response_format={"type": "json_object"},
            )
        )
        data = parse_ai_json(resp.choices[0].message.content, "basic-quality")
        score = data.get("score", 50)
        usage = extract_usage_metrics(resp, reasoning_model)
        return score, data, usage
    except Exception as e:
        logger.warning("Basic quality check failed for '%s': %s", term, e)
        return 50, {}, {}


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




# --- Section assembly: JSON keys → markdown ---

# Sections 1-4: Core (always visible), 5-8: Learn More (collapsible on frontend)
BASIC_SECTIONS_KO = [
    ("basic_ko_1_plain", "## 쉽게 이해하기"),
    ("basic_ko_2_example", "## 예시와 비유"),
    ("basic_ko_3_glance", "## 한눈에 보기"),
    ("basic_ko_4_why", "## 왜 중요한가"),
    ("basic_ko_5_where", "## 실제로 어디서 쓰이나"),
    ("basic_ko_6_caution", "## 주의할 점"),
    ("basic_ko_7_comm", "## 대화에서는 이렇게"),
    ("basic_ko_8_related", "## 함께 알면 좋은 용어"),
]

# Sections 1-4: Core (always visible), 5-8: Learn More (collapsible on frontend)
BASIC_SECTIONS_EN = [
    ("basic_en_1_plain", "## Plain Explanation"),
    ("basic_en_2_example", "## Example & Analogy"),
    ("basic_en_3_glance", "## At a Glance"),
    ("basic_en_4_why", "## Why It Matters"),
    ("basic_en_5_where", "## Where It's Used"),
    ("basic_en_6_caution", "## Precautions"),
    ("basic_en_7_comm", "## Communication"),
    ("basic_en_8_related", "## Related Terms"),
]

ADVANCED_SECTIONS_KO = [
    ("adv_ko_1_technical", "## 기술적 설명"),
    ("adv_ko_2_formulas", "## 핵심 수식 & 도표"),
    ("adv_ko_3_howworks", "## 동작 원리"),
    ("adv_ko_4_code", "## 코드 예시"),
    ("adv_ko_5_practical", "## 실무 활용 & 주의점"),
    ("adv_ko_6_why", "## 왜 중요한가"),
    ("adv_ko_7_comm", "## 업계 대화 맥락"),
    ("adv_ko_8_refs", "## 참조 링크"),
    ("adv_ko_9_related", "## 관련 기술 & 비교"),
]

ADVANCED_SECTIONS_EN = [
    ("adv_en_1_technical", "## Technical Description"),
    ("adv_en_2_formulas", "## Key Formulas & Diagrams"),
    ("adv_en_3_howworks", "## How It Works"),
    ("adv_en_4_code", "## Code Example"),
    ("adv_en_5_practical", "## Practical Use & Precautions"),
    ("adv_en_6_why", "## Why It Matters"),
    ("adv_en_7_comm", "## Industry Communication"),
    ("adv_en_8_refs", "## Reference Links"),
    ("adv_en_9_related", "## Related & Comparison"),
]


def _assemble_markdown(data: dict, sections: list[tuple[str, str]]) -> str:
    """Assemble section-per-key JSON data into markdown with H2 headers."""
    parts = []
    for key, header in sections:
        content = data.get(key, "").strip()
        if content:
            parts.append(f"{header}\n{content}")
    return "\n\n".join(parts)


def _assemble_all_sections(raw_data: dict) -> dict:
    """Convert section-per-key LLM output to body_basic/advanced_ko/en fields.

    Preserves meta fields (term_full, korean_name, etc.) and assembles
    section keys into markdown. If body_basic_ko already exists (old format),
    passes through unchanged.
    """
    data = {}

    # Copy meta fields
    for key in ("term_full", "korean_name", "korean_full", "categories",
                "definition_ko", "definition_en"):
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

    # Assemble advanced sections (or pass through if already assembled)
    if "body_advanced_ko" in raw_data:
        data["body_advanced_ko"] = raw_data["body_advanced_ko"]
    elif "adv_ko_1_technical" in raw_data:
        data["body_advanced_ko"] = _assemble_markdown(raw_data, ADVANCED_SECTIONS_KO)

    if "body_advanced_en" in raw_data:
        data["body_advanced_en"] = raw_data["body_advanced_en"]
    elif "adv_en_1_technical" in raw_data:
        data["body_advanced_en"] = _assemble_markdown(raw_data, ADVANCED_SECTIONS_EN)

    return data


async def _run_generate_term(
    req: HandbookAdviseRequest, client, model: str,
    source: str = "manual",
    article_context: str = "",
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
    # Tavily search runs first — results are used by ALL calls (basic + advanced)
    tavily_context = await _search_term_context(req.term)

    user_prompt = _build_handbook_user_prompt(req)
    # Combine article_context (pipeline) + Tavily results
    combined_ref = ""
    if article_context:
        combined_ref += (
            "--- Source Article (use as factual reference) ---\n"
            "Base your content on the facts in this article. "
            "Write the handbook entry in reference style, not news style.\n\n"
            f"{article_context[:4000]}\n\n"
        )
    if tavily_context:
        combined_ref += f"{tavily_context}\n\n"
    if combined_ref:
        user_prompt += (
            "\n\n" + combined_ref +
            "Use the above reference materials as factual sources. "
            "Cite specific numbers, dates, and URLs from them.\n"
        )
    warnings: list[str] = []
    supabase = get_supabase()

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
            if extra_meta:
                meta.update(extra_meta)
            supabase.table("pipeline_logs").insert({
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

    # --- Call 1: Meta + KO Basic (with retry if KO sections missing) ---
    for _call1_attempt in range(2):
        resp1 = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": GENERATE_BASIC_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=16000,
        )
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

    # --- Type classification (for advanced depth guide) ---
    from services.agents.prompts_handbook_types import get_type_depth_guide

    term_type = await _classify_term_type(
        req.term, req.categories or basic_data.get("categories", []),
        client, settings.openai_model_light,
    )
    logger.info("Term '%s' classified as type: %s, tavily_chars: %d",
                req.term, term_type, len(tavily_context))

    # --- Call 2 (EN Basic) + Call 3 (KO Advanced) — PARALLEL ---
    # Both depend only on Call 1 output, so they can run concurrently.
    # user_prompt already includes Tavily + article context (applied to all calls)
    en_basic_prompt = (
        f"{user_prompt}\n\n"
        f"--- Context from Call 1 ---\n"
        f"Definition (KO): {basic_data.get('definition_ko', '')}\n"
        f"Definition (EN): {basic_data.get('definition_en', '')}"
    )

    definition_context = basic_data.get("definition_en", "") or req.definition_en
    definition_ko_context = basic_data.get("definition_ko", "") or req.definition_ko
    advanced_prompt = (
        f"{user_prompt}\n\n"
        f"--- Context from Call 1 ---\n"
        f"Definition (EN): {definition_context}\n"
        f"Definition (KO): {definition_ko_context}\n"
        f"Term Type: {term_type}"
    )

    # Inject type-specific depth guide into advanced system prompts
    type_guide = get_type_depth_guide(term_type)
    adv_ko_system = f"{GENERATE_ADVANCED_PROMPT}\n\n{type_guide}"
    adv_en_system = f"{GENERATE_ADVANCED_EN_PROMPT}\n\n{type_guide}"

    resp2, resp3 = await asyncio.gather(
        client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": GENERATE_BASIC_EN_PROMPT},
                {"role": "user", "content": en_basic_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=16000,
        ),
        client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": adv_ko_system},
                {"role": "user", "content": advanced_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=16000,
        ),
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
    basic_ko_preview = "\n\n".join(
        f"## {k}: {v[:1000]}" for k, v in basic_data.items() if k.startswith("basic_ko_")
    )
    basic_en_preview = "\n\n".join(
        f"## {k}: {v[:1000]}" for k, v in en_basic_data.items() if k.startswith("basic_en_")
    )

    call4_task = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": adv_en_system},
            {"role": "user", "content": advanced_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=16000,
    )
    basic_critique_task = _self_critique_basic(
        req.term, term_type, basic_ko_preview, basic_en_preview, client, model,
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
        improved_ko_system = f"{GENERATE_BASIC_PROMPT}\n\n## Reviewer Feedback (MUST address):\n{basic_ko_feedback}"
        resp1b = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": improved_ko_system},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=16000, temperature=0.35,
            response_format={"type": "json_object"},
        )
        improved_basic = parse_ai_json(resp1b.choices[0].message.content, "Handbook-basic-ko-improved")
        for k, v in improved_basic.items():
            if k.startswith("basic_ko_"):
                basic_data[k] = v
        usage1b = extract_usage_metrics(resp1b, model)
        basic_critique_usage = merge_usage_metrics(basic_critique_usage, usage1b)
        _log_handbook_stage("handbook.generate.basic.ko.improved", usage1b)

    if basic_en_needs and basic_en_feedback:
        logger.info("Regenerating basic EN for '%s' with critique feedback", req.term)
        improved_en_system = f"{GENERATE_BASIC_EN_PROMPT}\n\n## Reviewer Feedback (MUST address):\n{basic_en_feedback}"
        resp2b = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": improved_en_system},
                {"role": "user", "content": en_basic_prompt},
            ],
            max_tokens=16000, temperature=0.35,
            response_format={"type": "json_object"},
        )
        en_basic_data = parse_ai_json(resp2b.choices[0].message.content, "Handbook-basic-en-improved")
        usage2b = extract_usage_metrics(resp2b, model)
        basic_critique_usage = merge_usage_metrics(basic_critique_usage, usage2b)
        _log_handbook_stage("handbook.generate.basic.en.improved", usage2b)

    if basic_critique_usage:
        _log_handbook_stage("handbook.self_critique.basic", basic_critique_usage)

    # --- Self-critique advanced KO content ---
    adv_ko_preview = "\n\n".join(
        f"## {k}: {v[:1000]}" for k, v in advanced_ko_data.items() if k.startswith("adv_ko_")
    )
    needs_improvement, critique_feedback, critique_score, critique_usage = (
        await _self_critique_advanced(req.term, term_type, adv_ko_preview, client, model)
    )
    logger.info(
        "Self-critique for '%s': score=%d, needs_improvement=%s",
        req.term, critique_score, needs_improvement,
    )

    # Only regenerate if score is below threshold (not just needs_improvement flag)
    if needs_improvement and critique_feedback and critique_score < 75:
        logger.info("Regenerating advanced KO for '%s' with critique feedback", req.term)
        improved_system = f"{adv_ko_system}\n\n## Reviewer Feedback (MUST address these):\n{critique_feedback}"
        resp3b = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": improved_system},
                {"role": "user", "content": advanced_prompt},
            ],
            max_tokens=16000, temperature=0.35,
            response_format={"type": "json_object"},
        )
        advanced_ko_data = parse_ai_json(resp3b.choices[0].message.content, "Handbook-adv-ko-improved")
        usage3b = extract_usage_metrics(resp3b, model)
        critique_usage = merge_usage_metrics(critique_usage, usage3b)
        _log_handbook_stage("handbook.generate.advanced.ko.improved", usage3b)

    if critique_usage:
        _log_handbook_stage("handbook.self_critique", critique_usage)

    # --- Self-critique advanced EN content ---
    adv_en_preview = "\n\n".join(
        f"## {k}: {v[:1000]}" for k, v in advanced_en_data.items() if k.startswith("adv_en_")
    )
    en_needs_improvement, en_critique_feedback, en_critique_score, en_critique_usage = (
        await _self_critique_advanced(req.term, term_type, adv_en_preview, client, model)
    )
    logger.info(
        "Self-critique EN for '%s': score=%d, needs_improvement=%s",
        req.term, en_critique_score, en_needs_improvement,
    )

    if en_needs_improvement and en_critique_feedback and en_critique_score < 75:
        logger.info("Regenerating advanced EN for '%s' with critique feedback", req.term)
        improved_en_adv_system = f"{adv_en_system}\n\n## Reviewer Feedback (MUST address these):\n{en_critique_feedback}"
        resp4b = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": improved_en_adv_system},
                {"role": "user", "content": advanced_prompt},
            ],
            max_tokens=16000, temperature=0.35,
            response_format={"type": "json_object"},
        )
        advanced_en_data = parse_ai_json(resp4b.choices[0].message.content, "Handbook-adv-en-improved")
        usage4b = extract_usage_metrics(resp4b, model)
        en_critique_usage = merge_usage_metrics(en_critique_usage, usage4b)
        _log_handbook_stage("handbook.generate.advanced.en.improved", usage4b)

    if en_critique_usage:
        _log_handbook_stage("handbook.self_critique.en", en_critique_usage)

    # --- Merge results ---
    raw_data = {**basic_data, **en_basic_data, **advanced_ko_data, **advanced_en_data}
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

    try:
        GenerateTermResult.model_validate(data)
    except ValidationError as e:
        for err in e.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            warnings.append(f"{field}: {err['msg']}")
        logger.warning("Handbook generate validation: %s", warnings)

    # Check section completeness (including empty detection)
    for lang in ("ko", "en"):
        basic_content = data.get(f"body_basic_{lang}", "")
        if not basic_content.strip():
            warnings.append(f"body_basic_{lang}: EMPTY — content generation failed")
        elif basic_content.count("## ") < 8:
            warnings.append(f"body_basic_{lang}: only {basic_content.count('## ')}/8 sections")
        adv_content = data.get(f"body_advanced_{lang}", "")
        if not adv_content.strip():
            warnings.append(f"body_advanced_{lang}: EMPTY — content generation failed")
        elif adv_content.count("## ") < 9:
            warnings.append(f"body_advanced_{lang}: only {adv_content.count('## ')}/9 sections")

    # Post-processing step 1: Validate reference URLs in advanced sections
    for field in ("body_advanced_ko", "body_advanced_en"):
        if data.get(field):
            data[field] = await _validate_ref_urls(data[field])

    # Quality check on assembled advanced content
    adv_combined = f"{data.get('body_advanced_ko', '')}\n\n{data.get('body_advanced_en', '')}"
    quality_score = None
    if adv_combined.strip():
        quality_score, quality_breakdown, quality_usage = await _check_handbook_quality(
            req.term, term_type, adv_combined, client,
        )
        if quality_usage:
            merged_usage = merge_usage_metrics(merged_usage, quality_usage)
        data["quality_score"] = quality_score
        data["quality_breakdown"] = quality_breakdown
        data["term_type"] = term_type
        if quality_score < 60:
            warnings.append(f"Advanced quality score: {quality_score}/100 — review recommended")
        logger.info("Handbook quality for '%s': %d/100 (type=%s)", req.term, quality_score, term_type)
        _log_handbook_stage("handbook.quality_check", quality_usage or {},
                            extra_meta={"quality_score": quality_score, "term_type": term_type})

    # Quality check on assembled basic content
    basic_combined = f"{data.get('body_basic_ko', '')}\n\n{data.get('body_basic_en', '')}"
    basic_quality_score = None
    if basic_combined.strip():
        basic_quality_score, basic_quality_breakdown, basic_quality_usage = (
            await _check_basic_quality(req.term, term_type, basic_combined, client)
        )
        if basic_quality_usage:
            merged_usage = merge_usage_metrics(merged_usage, basic_quality_usage)
        data["basic_quality_score"] = basic_quality_score
        data["basic_quality_breakdown"] = basic_quality_breakdown
        if basic_quality_score is not None and basic_quality_score < 60:
            warnings.append(f"Basic quality score: {basic_quality_score}/100 — review recommended")
        logger.info("Basic quality for '%s': %d/100", req.term, basic_quality_score or 0)
        _log_handbook_stage("handbook.quality_check.basic", basic_quality_usage or {},
                            extra_meta={"basic_quality_score": basic_quality_score, "term_type": term_type})

    # Record to dedicated quality scores table
    if supabase:
        try:
            import re
            term_slug = re.sub(r'[^a-z0-9]+', '-', req.term.lower().strip()).strip('-')
            base_row = {"term_slug": term_slug, "term_type": term_type, "source": source}
            if req.term_id:
                base_row["term_id"] = req.term_id

            if quality_score is not None:
                supabase.table("handbook_quality_scores").insert({
                    **base_row,
                    "score": quality_score,
                    "breakdown": {"level": "advanced", **quality_breakdown},
                }).execute()
            if basic_quality_score is not None:
                supabase.table("handbook_quality_scores").insert({
                    **base_row,
                    "score": basic_quality_score,
                    "breakdown": {"level": "basic", **basic_quality_breakdown},
                }).execute()
        except Exception as e:
            logger.warning("Failed to record handbook quality score: %s", e)

    logger.info(
        "Handbook generate completed for '%s', total_tokens=%d, warnings=%d",
        req.term, merged_usage.get("tokens_used", 0), len(warnings),
    )
    return data, merged_usage, warnings


# --- Pipeline Term Extraction Helpers ---

async def extract_terms_from_content(content: str) -> tuple[list[dict], dict]:
    """Extract technical terms from article content. Uses light model for cost.

    Returns (terms_list, usage_metrics_dict).
    """
    client = get_openai_client()
    model = getattr(settings, "openai_model_light")

    # Truncate to first 8000 chars for extraction
    preview = content[:8000]
    if len(content) > 8000:
        preview += "\n[... truncated]"

    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EXTRACT_TERMS_PROMPT},
            {"role": "user", "content": preview},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=2048,
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


async def generate_term_content(
    term_name: str, korean_name: str = "", source: str = "pipeline",
    article_context: str = "",
) -> tuple[dict, dict]:
    """Generate full content for a handbook term. Used by pipeline auto-creation.

    Args:
        source: "pipeline" (auto-extraction) or "manual" (admin editor)
        article_context: source news article text for grounding (prevents hallucination)

    Returns (content_data, usage_metrics_dict).
    """
    req = HandbookAdviseRequest(
        action="generate",
        term_id="",
        term=term_name,
        korean_name=korean_name,
    )
    client = get_openai_client()
    model = getattr(settings, "openai_model_main")
    data, usage, warnings = await _run_generate_term(
        req, client, model, source=source, article_context=article_context,
    )
    if warnings:
        data["_warnings"] = warnings
    return data, usage
