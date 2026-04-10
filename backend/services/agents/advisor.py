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
from services.agents.client import build_completion_kwargs, compat_create_kwargs, extract_usage_metrics, get_openai_client, merge_usage_metrics, parse_ai_json
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
        "model_attr": "openai_model_reasoning",
        "prompt_fn": get_review_prompt,
        "max_tokens": 2048,
        "temperature": 0.2,
        "reasoning_effort": "medium",
        "validator": ReviewResult,
    },
    "factcheck": {
        "model_attr": "openai_model_reasoning",
        "prompt": FACTCHECK_SYSTEM_PROMPT,
        "max_tokens": 4096,
        "temperature": 0.2,
        "reasoning_effort": "medium",
        "validator": FactcheckResult,
    },
    "conceptcheck": {
        "model_attr": "openai_model_reasoning",
        "prompt": CONCEPTCHECK_SYSTEM_PROMPT,
        "max_tokens": 2048,
        "temperature": 0.2,
        "reasoning_effort": "medium",
        "validator": ConceptCheckResult,
    },
    "voicecheck": {
        "model_attr": "openai_model_reasoning",
        "prompt": VOICECHECK_SYSTEM_PROMPT,
        "max_tokens": 2048,
        "temperature": 0.3,
        "reasoning_effort": "medium",
        "validator": VoiceCheckResult,
    },
    "retrocheck": {
        "model_attr": "openai_model_reasoning",
        "prompt": RETROCHECK_SYSTEM_PROMPT,
        "max_tokens": 2048,
        "temperature": 0.2,
        "reasoning_effort": "medium",
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
    if config.get("reasoning_effort"):
        completion_kwargs["reasoning_effort"] = config["reasoning_effort"]
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
    step1_kwargs = build_completion_kwargs(
        model=model,
        messages=[
            {"role": "system", "content": DEEPVERIFY_CLAIM_EXTRACT_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=2048,
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    step1_kwargs["reasoning_effort"] = "medium"
    resp1 = await client.chat.completions.create(**step1_kwargs)
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
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    step2_kwargs["reasoning_effort"] = "medium"
    resp2 = await client.chat.completions.create(**step2_kwargs)
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
        **compat_create_kwargs(
            model,
            messages=[
                {"role": "system", "content": RELATED_TERMS_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=2048,
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
            temperature=0.2,
            max_tokens=4096,
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


async def _search_term_context(term: str, categories: list[str] | None = None) -> str:
    """Search web for term context using Tavily. Category-aware queries."""
    if not settings.tavily_api_key:
        return ""
    try:
        # Build category-aware query
        query = f"{term} AI technology explained"
        if categories:
            primary_cat = categories[0]
            template = CATEGORY_SEARCH_QUERIES.get(primary_cat)
            if template:
                query = template.format(term=term)

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


async def _search_brave_context(term: str, categories: list[str] | None = None) -> str:
    """Search Brave for developer-focused references (docs, GitHub, SO)."""
    if not settings.brave_api_key:
        return ""
    try:
        import httpx

        query = f"{term} official documentation OR github"
        if categories:
            template = BRAVE_CATEGORY_QUERIES.get(categories[0])
            if template:
                query = template.format(term=term)

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


async def _search_deep_context(term: str) -> str:
    """Search Exa for deep term context (full text). Used for Advanced content generation."""
    if not settings.exa_api_key:
        return ""
    try:
        from exa_py import Exa
        exa = Exa(api_key=settings.exa_api_key)
        loop = asyncio.get_running_loop()
        results = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: exa.search_and_contents(
                    f"{term} AI technology deep explanation tutorial",
                    type="auto",
                    num_results=3,
                    text={"max_characters": 10000},
                    category="research paper",
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
                        f"{term} AI technology explained in depth",
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
    term: str, categories: list[str], client, model_light: str,
) -> tuple[str, list[str], str]:
    """Classify term type + intent + volatility in one LLM call.

    Returns (type_str, intent_list, volatility_str).
    """
    from services.agents.prompts_handbook_types import (
        CLASSIFY_TERM_PROMPT, TERM_TYPES,
        INTENT_VALUES, VOLATILITY_VALUES,
    )

    user_msg = f"Term: {term}\nCategories: {', '.join(categories)}"
    try:
        resp = await client.chat.completions.create(
            **compat_create_kwargs(
                model_light,
                messages=[
                    {"role": "system", "content": CLASSIFY_TERM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=200,
                temperature=0,
                response_format={"type": "json_object"},
            )
        )
        data = parse_ai_json(resp.choices[0].message.content, "term-classify")

        # Type: validate against TERM_TYPES, fallback to "concept" for unknown values
        term_type = data.get("type", "concept")
        if term_type not in TERM_TYPES:
            term_type = "concept"

        # Intent: validate, default to ["understand"]
        raw_intent = data.get("intent", ["understand"])
        if isinstance(raw_intent, str):
            raw_intent = [raw_intent]
        intent_list = [i for i in raw_intent if i in INTENT_VALUES] or ["understand"]

        # Volatility: validate, default to "stable"
        volatility = data.get("volatility", "stable")
        if volatility not in VOLATILITY_VALUES:
            volatility = "stable"

        return term_type, intent_list, volatility
    except Exception as e:
        logger.warning("Term classification failed for '%s': %s", term, e)
        return "concept", ["understand"], "stable"


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
    reasoning_model = settings.openai_model_reasoning  # gpt-5-mini for quality check
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
    reference_context: str = "",
) -> tuple[bool, bool, str, str, int, int, dict]:
    """Self-critique basic KO+EN content in one call (gpt-4.1-mini).

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
    reasoning_model = settings.openai_model_reasoning  # gpt-5-mini for quality check
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
                temperature=0,
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
    ("adv_ko_4_tradeoffs", "## 트레이드오프와 언제 무엇을 쓰나"),
    ("adv_ko_5_pitfalls", "## 프로덕션 함정"),
    ("adv_ko_6_comm", "## 업계 대화 맥락"),
    ("adv_ko_7_related", "## 선행·대안·확장 개념"),
]

ADVANCED_SECTIONS_EN = [
    ("adv_en_1_mechanism", "## Technical Definition & How It Works"),
    ("adv_en_2_formulas", "## Formulas, Architecture, and Diagrams"),
    ("adv_en_3_code", "## Code or Pseudocode"),
    ("adv_en_4_tradeoffs", "## Tradeoffs — When to Use What"),
    ("adv_en_5_pitfalls", "## Production Pitfalls"),
    ("adv_en_6_comm", "## Industry Communication"),
    ("adv_en_7_related", "## Prerequisites, Alternatives, and Extensions"),
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

    # Copy level-independent fields (hero card, references, sidebar)
    # These are rendered outside the Basic/Advanced body switcher.
    for key in ("hero_news_context_ko", "hero_news_context_en",
                "references_ko", "references_en",
                "sidebar_checklist_ko", "sidebar_checklist_en"):
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
    # Run all searches in parallel — results are source-role labeled
    categories_list = req.categories if req.categories else []
    tavily_context, brave_context, deep_context = await asyncio.gather(
        _search_term_context(req.term, categories=categories_list),
        _search_brave_context(req.term, categories=categories_list),
        _search_deep_context(req.term),
    )

    user_prompt = _build_handbook_user_prompt(req)
    # Assemble source-role labeled reference context
    combined_ref = ""
    if article_context:
        combined_ref += (
            "## Source Article (PRIMARY factual reference)\n"
            "Base your content on facts from this article. "
            "Write the handbook entry in reference style, not news style.\n\n"
            f"{article_context[:4000]}\n\n"
        )
    if tavily_context:
        combined_ref += (
            f"{tavily_context}\n"
            "SOURCE ROLE: Recent context, examples, and news. "
            "Good for: basic_*_2_example, basic_*_5_where, basic_*_0_summary.\n\n"
        )
    if brave_context:
        combined_ref += (
            f"{brave_context}\n"
            "SOURCE ROLE: Official documentation, code references, Stack Overflow. "
            "Good for: adv_*_4_code, adv_*_1_technical, adv_*_8_refs.\n\n"
        )
    if combined_ref:
        user_prompt += (
            "\n\n" + combined_ref +
            "## Source Usage Rules\n"
            "- Use Source Article as your PRIMARY factual reference.\n"
            "- Use Reference Materials for recent context and examples.\n"
            "- Use Developer Reference Materials for code patterns and official docs.\n"
            "- ONLY cite facts from the materials above. If a topic is not covered, "
            "state that information is limited rather than generating from memory.\n"
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

    # --- Build category-specific prompt blocks ---
    from services.agents.prompts_handbook_types import build_category_block, get_type_basic_guide, get_section_weight_guide

    primary_cat = categories_list[0] if categories_list else ""
    category_block = build_category_block(primary_cat)
    basic_ko_system = GENERATE_BASIC_PROMPT
    if category_block:
        basic_ko_system += f"\n\n{category_block}"

    # --- Call 1: Meta + KO Basic (with retry if KO sections missing) ---
    for _call1_attempt in range(2):
        resp1 = await client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": basic_ko_system},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=16000,
            )
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

    term_type, intent_list, volatility = await _classify_term_type(
        req.term, req.categories or basic_data.get("categories", []),
        client, settings.openai_model_nano,
    )
    logger.info(
        "Term '%s' classified: type=%s, intent=%s, volatility=%s",
        req.term, term_type, intent_list, volatility,
    )

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
    advanced_prompt = (
        f"{user_prompt}\n\n"
        f"--- Context from Call 1 ---\n"
        f"Definition (EN): {definition_context}\n"
        f"Definition (KO): {definition_ko_context}\n"
        f"Term Type: {term_type}"
    )
    if brave_context:
        advanced_prompt += f"\n\n{brave_context}\nSOURCE ROLE: Official docs, code references. Use for adv_*_4_code, adv_*_8_refs."
    if deep_context:
        advanced_prompt += f"\n\n{deep_context}\nSOURCE ROLE: Deep technical papers. Use for adv_*_2_formulas, adv_*_3_howworks, adv_*_1_technical."

    # Inject type-specific guides into system prompts
    type_guide = get_type_depth_guide(term_type)
    basic_type_guide = get_type_basic_guide(term_type)

    # Section weight guide based on type × intent
    primary_intent = intent_list[0] if intent_list else "understand"
    section_weight_guide = get_section_weight_guide(term_type, primary_intent)

    # EN Basic: category block + basic type guide + section weight
    basic_en_system = GENERATE_BASIC_EN_PROMPT
    if category_block:
        basic_en_system += f"\n\n{category_block}"
    basic_en_system += f"\n\n{basic_type_guide}"
    if section_weight_guide:
        basic_en_system += f"\n\n{section_weight_guide}"

    # Advanced: category block + type depth guide + section weight
    adv_ko_system = GENERATE_ADVANCED_PROMPT
    if category_block:
        adv_ko_system += f"\n\n{category_block}"
    adv_ko_system += f"\n\n{type_guide}"
    if section_weight_guide:
        adv_ko_system += f"\n\n{section_weight_guide}"

    adv_en_system = GENERATE_ADVANCED_EN_PROMPT
    if category_block:
        adv_en_system += f"\n\n{category_block}"
    adv_en_system += f"\n\n{type_guide}"
    if section_weight_guide:
        adv_en_system += f"\n\n{section_weight_guide}"

    resp2, resp3 = await asyncio.gather(
        client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": basic_en_system},
                    {"role": "user", "content": en_basic_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=16000,
            )
        ),
        client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": adv_ko_system},
                    {"role": "user", "content": advanced_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=16000,
            )
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
        **compat_create_kwargs(
            model,
            messages=[
                {"role": "system", "content": adv_en_system},
                {"role": "user", "content": advanced_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=16000,
        )
    )
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
        improved_ko_system = f"{GENERATE_BASIC_PROMPT}\n\n## Reviewer Feedback (MUST address):\n{basic_ko_feedback}"
        resp1b = await client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": improved_ko_system},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=16000, temperature=0.35,
                response_format={"type": "json_object"},
            )
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
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": improved_en_system},
                    {"role": "user", "content": en_basic_prompt},
                ],
                max_tokens=16000, temperature=0.35,
                response_format={"type": "json_object"},
            )
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
    reference_for_critique = f"{tavily_context}\n{brave_context}\n{deep_context}"
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
        resp3b = await client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": improved_system},
                    {"role": "user", "content": advanced_prompt},
                ],
                max_tokens=16000, temperature=0.35,
                response_format={"type": "json_object"},
            )
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
        resp4b = await client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": improved_en_adv_system},
                    {"role": "user", "content": advanced_prompt},
                ],
                max_tokens=16000, temperature=0.35,
                response_format={"type": "json_object"},
            )
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
    # Basic: 7 sections. Advanced: 7 sections. (Post-redesign, both languages.)
    _basic_expected = {"ko": 7, "en": 7}
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
        elif adv_content.count("## ") < 7:
            warnings.append(f"body_advanced_{lang}: only {adv_content.count('## ')}/7 sections")

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
        data["facet_intent"] = intent_list
        data["facet_volatility"] = volatility
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

    # Add search source metadata for UI display
    search_sources = []
    if tavily_context:
        search_sources.append("Tavily")
    if brave_context:
        search_sources.append("Brave")
    if deep_context:
        search_sources.append("Exa")
    data["_search_sources"] = search_sources
    # Ensure facet data is always present (for pipeline DB storage)
    data.setdefault("term_type", term_type)
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

    # Truncate to first 24000 chars for extraction (gpt-4.1-mini supports 128K)
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
            temperature=0.2,
            max_tokens=2048,
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
    """Filter candidate terms through LLM gate before generation.

    Uses nano model to reject duplicates, too-specific, or non-established terms.
    Returns only accepted candidates.
    """
    if not candidates:
        return []

    from services.agents.prompts_advisor import TERM_GATE_PROMPT

    client = get_openai_client()
    model = getattr(settings, "openai_model_nano")

    # Format existing terms as compact list
    existing_str = ", ".join(existing_terms[:500])  # cap at 500 for token budget
    candidate_names = [c.get("term", "") for c in candidates]

    prompt = TERM_GATE_PROMPT.format(existing_terms=existing_str)
    user_msg = f"Candidates to evaluate:\n{', '.join(candidate_names)}"

    try:
        resp = await client.chat.completions.create(
            **build_completion_kwargs(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=1000,
                temperature=0,
                response_format={"type": "json_object"},
            )
        )
        data = parse_ai_json(resp.choices[0].message.content, "term-gate")
        decisions = {d["term"]: d for d in data.get("decisions", [])}

        accepted = []
        for candidate in candidates:
            term = candidate.get("term", "")
            decision = decisions.get(term, {})
            if decision.get("decision") == "reject":
                logger.info(
                    "Gate rejected '%s': %s", term, decision.get("reason", "no reason"),
                )
            else:
                accepted.append(candidate)

        logger.info(
            "Term gate: %d candidates → %d accepted, %d rejected",
            len(candidates), len(accepted), len(candidates) - len(accepted),
        )
        return accepted
    except Exception as e:
        logger.warning("Term gate failed, passing all candidates: %s", e)
        return candidates  # fail-open: don't block pipeline on gate failure


async def generate_term_content(
    term_name: str, korean_name: str = "", source: str = "pipeline",
    article_context: str = "",
    categories: list[str] | None = None,
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
    )
    client = get_openai_client()
    model = getattr(settings, "openai_model_main")
    data, usage, warnings = await _run_generate_term(
        req, client, model, source=source, article_context=article_context,
    )
    if warnings:
        data["_warnings"] = warnings
    return data, usage
