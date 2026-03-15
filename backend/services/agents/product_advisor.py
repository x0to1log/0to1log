"""Product AI Advisor service — generates taglines and descriptions from product URL."""

import asyncio
import logging

from core.config import settings
from models.product_advisor import ProductGenerateRequest
from services.agents.client import get_openai_client, extract_usage_metrics, parse_ai_json

logger = logging.getLogger(__name__)

GENERATE_FROM_URL_SYSTEM = """You are an editorial writer for 0to1log, an AI publication for builders and developers.
Given a product's web page content, generate:
- tagline: a punchy 1-sentence English tagline (max 15 words)
- tagline_ko: the same tagline translated naturally into Korean
- description_en: a 2-3 sentence editorial description in English explaining what the product does and why it matters
- description_ko: the same description in Korean

Respond with JSON only:
{"tagline": "...", "tagline_ko": "...", "description_en": "...", "description_ko": "..."}"""

TAGLINE_EN_SYSTEM = """You write punchy product taglines for an AI publication.
Given the product name and URL, write a single English tagline (max 15 words) that captures what the product does.
Respond with plain text only — no JSON, no quotes."""

TAGLINE_KO_SYSTEM = """AI 퍼블리케이션을 위한 제품 한줄 설명을 작성합니다.
제품명과 URL을 바탕으로 제품이 무엇을 하는지 한국어 한줄 설명(15단어 이내)을 작성하세요.
순수 텍스트만 응답하세요 — JSON, 따옴표 없이."""

DESCRIPTION_EN_SYSTEM = """You write editorial product descriptions for an AI publication aimed at builders and developers.
Given a product name and URL, write a 2-3 sentence English description covering:
1. What the product does
2. Who it's for / why it matters

Respond with plain text only."""

DESCRIPTION_KO_SYSTEM = """AI 퍼블리케이션을 위한 제품 설명을 작성합니다.
제품명과 URL을 바탕으로 다음을 다루는 한국어 2-3문장 설명을 작성하세요:
1. 제품이 무엇을 하는지
2. 누구를 위한 것인지 / 왜 중요한지

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
            lambda: tavily.search(url, max_results=1, include_raw_content=False),
        )
        content_parts = []
        for r in results.get("results", []):
            if r.get("content"):
                content_parts.append(r["content"])
        return "\n\n".join(content_parts)[:3000]
    except Exception as e:
        logger.warning("Tavily fetch failed for %s: %s", url, e)
        return ""


async def run_product_generate(body: ProductGenerateRequest) -> tuple[str | dict, str, int]:
    """Run a product AI generation action. Returns (result, model_used, tokens_used)."""
    client = get_openai_client()
    model = settings.openai_model_light

    if body.action == "generate_from_url":
        page_content = await _fetch_page_content(body.url or "")
        user_content = f"Product: {body.name or body.url}\nURL: {body.url}\n\nPage content:\n{page_content or '(not available)'}"
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": GENERATE_FROM_URL_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1024,
            temperature=0.5,
        )
        raw = response.choices[0].message.content or ""
        metrics = extract_usage_metrics(response, model)
        try:
            result = parse_ai_json(raw, "product_advisor")
        except Exception:
            result = raw.strip()
        return result, metrics["model_used"], metrics["tokens_used"]

    # Individual field generation
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
        temperature=0.5,
    )
    raw = response.choices[0].message.content or ""
    metrics = extract_usage_metrics(response, model)
    return raw.strip(), metrics["model_used"], metrics["tokens_used"]
