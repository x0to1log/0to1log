"""Product AI Advisor service — generates taglines and descriptions from product URL."""

import asyncio
import logging
from urllib.parse import urlparse

from core.config import settings
from models.product_advisor import ProductGenerateRequest
from services.agents.client import get_openai_client, extract_usage_metrics, parse_ai_json

logger = logging.getLogger(__name__)

GENERATE_FROM_URL_SYSTEM = """You are an editorial writer for 0to1log, an AI product curation magazine.

You write for builders and developers who are evaluating AI tools.

Given a product page's content, generate these fields:

1. **tagline** (EN): A sharp, specific tagline (max 12 words).
   - BAD: "AI-powered tool for developers" (vague, could be anything)
   - GOOD: "Turn any screenshot into production React code" (specific, shows value)
   - Lead with the core action/benefit, not the category

2. **tagline_ko** (KO): Natural Korean tagline — NOT a translation of EN.
   - Write as if explaining to a Korean developer friend
   - Use the format: "[핵심 기능] — [차별점 또는 대상]"
   - Example: "스크린샷 한 장으로 React 코드 생성 — 프론트엔드 속도 혁신"

3. **description_en** (EN, 2-3 sentences):
   - Sentence 1: What it does concretely (not "AI-powered platform that...")
   - Sentence 2: Who uses it and for what specific workflow
   - Sentence 3 (optional): Key differentiator vs alternatives

4. **description_ko** (KO, 2-3 sentences):
   - Same structure but naturally written for Korean readers
   - Use technical terms as-is (API, LLM, RAG) with brief context if needed

5. **pricing** (one of: "free", "freemium", "paid", "enterprise", or null):
   - Infer from the page content (free tier? pricing page mentions?)
   - null if truly cannot determine

6. **platform** (array of applicable: "web", "ios", "android", "api", "desktop"):
   - Infer from download links, app store badges, API docs mentions
   - Empty array [] if cannot determine

7. **korean_support** (boolean):
   - true if Korean language UI or Korean documentation exists
   - false if unsure

8. **tags** (array of 3-5 lowercase keyword strings):
   - e.g. ["llm", "chatbot", "productivity", "code-generation"]
   - Empty array [] if cannot determine

Respond with JSON only:
{
  "tagline": "...",
  "tagline_ko": "...",
  "description_en": "...",
  "description_ko": "...",
  "pricing": "freemium",
  "platform": ["web", "api"],
  "korean_support": false,
  "tags": ["llm", "chatbot"]
}"""

TAGLINE_EN_SYSTEM = """You write punchy product taglines for an AI publication.
Given the product name and URL, write a single English tagline (max 12 words).
- BAD: "AI-powered tool for developers" (vague)
- GOOD: "Turn any screenshot into production React code" (specific, shows value)
Respond with plain text only — no JSON, no quotes."""

TAGLINE_KO_SYSTEM = """AI 제품 큐레이션 매거진을 위한 한줄 설명을 작성합니다.
제품명과 URL을 바탕으로 한국어 한줄 설명을 작성하세요.
- "[핵심 기능] — [차별점 또는 대상]" 형식
- 영어 번역이 아닌, 한국어 개발자에게 자연스럽게 설명하듯
순수 텍스트만 응답하세요 — JSON, 따옴표 없이."""

DESCRIPTION_EN_SYSTEM = """You write editorial product descriptions for an AI publication aimed at builders and developers.
Given a product name and URL, write a 2-3 sentence English description:
- Sentence 1: What it does concretely (not "AI-powered platform that...")
- Sentence 2: Who uses it and for what specific workflow
- Sentence 3 (optional): Key differentiator vs alternatives
Respond with plain text only."""

DESCRIPTION_KO_SYSTEM = """AI 제품 큐레이션 매거진을 위한 제품 설명을 작성합니다.
제품명과 URL을 바탕으로 한국어 2-3문장 설명을 작성하세요:
- 1문장: 구체적으로 무엇을 하는지 (막연한 "AI 기반 플랫폼"은 금지)
- 2문장: 누가 어떤 작업에 사용하는지
- 3문장 (선택): 대안 대비 핵심 차별점
순수 텍스트만 응답하세요."""


async def _fetch_page_content(url: str) -> str:
    """Fetch product page content using Tavily, with graceful fallback."""
    if not url or not settings.tavily_api_key:
        return ""
    try:
        from tavily import TavilyClient
        tavily = TavilyClient(api_key=settings.tavily_api_key)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: tavily.search(url, max_results=1, include_raw_content=True),
        )
        content_parts = []
        for r in results.get("results", []):
            raw = r.get("raw_content") or r.get("content") or ""
            if raw:
                content_parts.append(raw)
        return "\n\n".join(content_parts)[:4000]
    except Exception as e:
        logger.warning("Tavily fetch failed for %s: %s", url, e)
        return ""


def _resolve_logo_url(url: str) -> str | None:
    """Generate a logo URL from the product domain using Clearbit/Google fallback."""
    if not url:
        return None
    try:
        domain = urlparse(url).netloc
        if not domain:
            return None
        # Remove www. prefix for cleaner logo lookup
        if domain.startswith("www."):
            domain = domain[4:]
        return f"https://logo.clearbit.com/{domain}"
    except Exception:
        return None


async def run_product_generate(body: ProductGenerateRequest) -> tuple[str | dict, str, int]:
    """Run a product AI generation action. Returns (result, model_used, tokens_used)."""
    client = get_openai_client()

    if body.action == "generate_from_url":
        model = settings.openai_model_main
        page_content = await _fetch_page_content(body.url or "")
        user_content = f"Product: {body.name or body.url}\nURL: {body.url}\n\nPage content:\n{page_content or '(not available)'}"
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": GENERATE_FROM_URL_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1500,
            temperature=0.6,
        )
        raw = response.choices[0].message.content or ""
        metrics = extract_usage_metrics(response, model)
        try:
            result = parse_ai_json(raw, "product_advisor")
        except Exception:
            result = raw.strip()

        # Add logo_url if AI didn't provide one
        if isinstance(result, dict) and not result.get("logo_url"):
            logo = _resolve_logo_url(body.url or "")
            if logo:
                result["logo_url"] = logo

        return result, metrics["model_used"], metrics["tokens_used"]

    # Individual field generation
    model = settings.openai_model_light
    system_map = {
        "tagline_en": TAGLINE_EN_SYSTEM,
        "tagline_ko": TAGLINE_KO_SYSTEM,
        "description_en": DESCRIPTION_EN_SYSTEM,
        "description_ko": DESCRIPTION_KO_SYSTEM,
    }
    system_prompt = system_map[body.action]
    user_parts = []
    if body.name:
        user_parts.append(f"Product: {body.name}")
    if body.url:
        user_parts.append(f"URL: {body.url}")
    if body.context:
        user_parts.append(f"Context: {body.context}")
    user_content = "\n".join(user_parts) or "Generate a tagline for this AI product."

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=512,
        temperature=0.6,
    )
    raw = response.choices[0].message.content or ""
    metrics = extract_usage_metrics(response, model)
    return raw.strip(), metrics["model_used"], metrics["tokens_used"]
