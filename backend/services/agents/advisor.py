"""AI Advisor agent handlers — post actions + deep verify + handbook."""

import asyncio
import logging
import re

import httpx
from pydantic import ValidationError

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
from services.agents.client import extract_usage_metrics, get_openai_client, merge_usage_metrics, parse_ai_json
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
        "model_attr": "openai_model_main",
        "prompt": FACTCHECK_SYSTEM_PROMPT,
        "max_tokens": 4096,
        "temperature": 0.2,
        "validator": FactcheckResult,
    },
    "conceptcheck": {
        "model_attr": "openai_model_light",
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

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )

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
    model = getattr(settings, "openai_model_main")
    total_tokens = 0

    # Step 1: Extract claims
    user_prompt = _build_user_prompt(req)
    resp1 = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": DEEPVERIFY_CLAIM_EXTRACT_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=2048,
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
        loop = asyncio.get_event_loop()

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
        model=model,
        messages=[
            {"role": "system", "content": DEEPVERIFY_VERIFY_PROMPT},
            {"role": "user", "content": verify_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=4096,
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
            loop = asyncio.get_event_loop()
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


def _fetch_handbook_term_map() -> dict[str, str]:
    """Fetch {term_name: slug} map of published handbook terms."""
    supabase = get_supabase()
    if not supabase:
        return {}
    try:
        result = supabase.table("handbook_terms").select("term, slug").eq("status", "published").execute()
        return {t["term"]: t["slug"] for t in (result.data or [])}
    except Exception:
        return {}


def _auto_link_handbook_terms(content: str, handbook_map: dict[str, str]) -> str:
    """Replace first occurrence of each handbook term with a markdown link.

    Longer terms are matched first to avoid partial matches.
    Already-linked terms (inside [...]) are skipped.
    """
    linked: set[str] = set()
    for term, slug in sorted(handbook_map.items(), key=lambda x: -len(x[0])):
        if slug in linked:
            continue
        pattern = re.compile(r'(?<!\[)(' + re.escape(term) + r')(?!\])', re.IGNORECASE)
        if pattern.search(content):
            content = pattern.sub(f'[\\1](/handbook/{slug}/)', content, count=1)
            linked.add(slug)
    return content


# --- Section assembly: JSON keys → markdown ---

BASIC_SECTIONS_KO = [
    ("basic_ko_1_plain", "## 💡 쉽게 이해하기"),
    ("basic_ko_2_example", "## 🍎 예시와 비유"),
    ("basic_ko_3_glance", "## 📊 한눈에 보기"),
    ("basic_ko_4_why", "## ❓ 왜 중요한가"),
    ("basic_ko_5_where", "## 🔧 실제로 어디서 쓰이나"),
    ("basic_ko_6_caution", "## ⚠️ 주의할 점"),
    ("basic_ko_7_comm", "## 💬 대화에서는 이렇게"),
    ("basic_ko_8_related", "## 🔗 함께 알면 좋은 용어"),
]

BASIC_SECTIONS_EN = [
    ("basic_en_1_plain", "## 💡 Plain Explanation"),
    ("basic_en_2_example", "## 🍎 Example & Analogy"),
    ("basic_en_3_glance", "## 📊 At a Glance"),
    ("basic_en_4_why", "## ❓ Why It Matters"),
    ("basic_en_5_where", "## 🔧 Where It's Used"),
    ("basic_en_6_caution", "## ⚠️ Precautions"),
    ("basic_en_7_comm", "## 💬 Communication"),
    ("basic_en_8_related", "## 🔗 Related Terms"),
]

ADVANCED_SECTIONS_KO = [
    ("adv_ko_1_technical", "## 💡 기술적 설명"),
    ("adv_ko_2_formulas", "## 📐 핵심 수식 & 도표"),
    ("adv_ko_3_howworks", "## 🏗️ 동작 원리"),
    ("adv_ko_4_code", "## 💻 코드 예시"),
    ("adv_ko_5_practical", "## ✅ 실무 활용 & 주의점"),
    ("adv_ko_6_why", "## ❓ 왜 중요한가"),
    ("adv_ko_7_comm", "## 💬 업계 대화 맥락"),
    ("adv_ko_8_refs", "## 📚 참조 링크"),
    ("adv_ko_9_related", "## 🔗 관련 기술 & 비교"),
]

ADVANCED_SECTIONS_EN = [
    ("adv_en_1_technical", "## 💡 Technical Description"),
    ("adv_en_2_formulas", "## 📐 Key Formulas & Diagrams"),
    ("adv_en_3_howworks", "## 🏗️ How It Works"),
    ("adv_en_4_code", "## 💻 Code Example"),
    ("adv_en_5_practical", "## ✅ Practical Use & Precautions"),
    ("adv_en_6_why", "## ❓ Why It Matters"),
    ("adv_en_7_comm", "## 💬 Industry Communication"),
    ("adv_en_8_refs", "## 📚 Reference Links"),
    ("adv_en_9_related", "## 🔗 Related & Comparison"),
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
) -> tuple[dict, dict, list[str]]:
    """Auto-generate all empty fields for a handbook term via 3 LLM calls.

    Call 1: meta + KO Basic (term_full, korean_full, categories, definition, body_basic_ko)
    Call 2: EN Basic (body_basic_en, with KO definition as context)
    Call 3: Advanced (body_advanced, with definition as context)

    Args:
        source: "manual" (admin editor) or "pipeline" (auto-extraction)

    Returns (merged_data, merged_usage, warnings).
    """
    user_prompt = _build_handbook_user_prompt(req)
    warnings: list[str] = []
    supabase = get_supabase()

    def _log_handbook_stage(stage: str, usage: dict) -> None:
        """Log a handbook generate stage to pipeline_logs. Never raises."""
        if not supabase:
            return
        try:
            supabase.table("pipeline_logs").insert({
                "pipeline_type": stage,
                "status": "success",
                "input_summary": f"term={req.term}",
                "model_used": usage.get("model_used"),
                "tokens_used": usage.get("tokens_used"),
                "cost_usd": usage.get("cost_usd"),
                "debug_meta": {
                    "term": req.term,
                    "source": source,
                    "input_tokens": usage.get("input_tokens"),
                    "output_tokens": usage.get("output_tokens"),
                },
            }).execute()
        except Exception as e:
            logger.warning("Failed to log handbook %s stage: %s", stage, e)

    # --- Call 1: Meta + KO Basic ---
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
    usage1 = extract_usage_metrics(resp1, model)

    logger.info(
        "Handbook generate call 1 (basic KO) for '%s': %d tokens",
        req.term, usage1.get("tokens_used", 0),
    )
    _log_handbook_stage("handbook.generate.basic", usage1)

    # --- Call 2: EN Basic (with KO definition as context) ---
    en_basic_prompt = (
        f"{user_prompt}\n\n"
        f"--- Context from Call 1 ---\n"
        f"Definition (KO): {basic_data.get('definition_ko', '')}\n"
        f"Definition (EN): {basic_data.get('definition_en', '')}"
    )

    resp2 = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": GENERATE_BASIC_EN_PROMPT},
            {"role": "user", "content": en_basic_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=16000,
    )
    en_basic_data = parse_ai_json(resp2.choices[0].message.content, "Handbook-generate-basic-en")
    usage2 = extract_usage_metrics(resp2, model)

    logger.info(
        "Handbook generate call 2 (basic EN) for '%s': %d tokens",
        req.term, usage2.get("tokens_used", 0),
    )
    _log_handbook_stage("handbook.generate.basic.en", usage2)

    # --- Call 3: Advanced (with definition as context) ---
    definition_context = basic_data.get("definition_en", "") or en_basic_data.get("definition_en", "") or req.definition_en
    definition_ko_context = basic_data.get("definition_ko", "") or req.definition_ko
    advanced_prompt = (
        f"{user_prompt}\n\n"
        f"--- Context from Call 1 ---\n"
        f"Definition (EN): {definition_context}\n"
        f"Definition (KO): {definition_ko_context}"
    )

    resp3 = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": GENERATE_ADVANCED_PROMPT},
            {"role": "user", "content": advanced_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=16000,
    )
    advanced_data = parse_ai_json(resp3.choices[0].message.content, "Handbook-generate-advanced")
    usage3 = extract_usage_metrics(resp3, model)

    logger.info(
        "Handbook generate call 3 (advanced) for '%s': %d tokens",
        req.term, usage3.get("tokens_used", 0),
    )
    _log_handbook_stage("handbook.generate.advanced", usage3)

    # --- Merge results ---
    raw_data = {**basic_data, **en_basic_data, **advanced_data}
    merged_usage = merge_usage_metrics(merge_usage_metrics(usage1, usage2), usage3)

    # --- Assemble section keys into markdown ---
    data = _assemble_all_sections(raw_data)

    try:
        GenerateTermResult.model_validate(data)
    except ValidationError as e:
        for err in e.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            warnings.append(f"{field}: {err['msg']}")
        logger.warning("Handbook generate validation: %s", warnings)

    # Check section completeness
    for lang in ("ko", "en"):
        basic_content = data.get(f"body_basic_{lang}", "")
        if basic_content and basic_content.count("## ") < 8:
            warnings.append(f"body_basic_{lang}: only {basic_content.count('## ')}/8 sections")
        adv_content = data.get(f"body_advanced_{lang}", "")
        if adv_content and adv_content.count("## ") < 9:
            warnings.append(f"body_advanced_{lang}: only {adv_content.count('## ')}/9 sections")

    # Auto-link handbook terms in generated content
    handbook_map = _fetch_handbook_term_map()
    if handbook_map:
        for field in ("body_basic_ko", "body_basic_en", "body_advanced_ko", "body_advanced_en"):
            if data.get(field):
                data[field] = _auto_link_handbook_terms(data[field], handbook_map)

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

    # Truncate to first 4000 chars for extraction (term spotting doesn't need full text)
    preview = content[:4000]
    if len(content) > 4000:
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
) -> tuple[dict, dict]:
    """Generate full content for a handbook term. Used by pipeline auto-creation.

    Args:
        source: "pipeline" (auto-extraction) or "manual" (admin editor)

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
    data, usage, _warnings = await _run_generate_term(req, client, model, source=source)
    return data, usage
