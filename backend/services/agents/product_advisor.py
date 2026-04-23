"""Product AI Advisor service — generates taglines and descriptions from product URL."""

import asyncio
import json
import logging
import time
from urllib.parse import urlparse

from core.config import settings
from models.product_advisor import ProductGenerateRequest
from services.agents.client import get_openai_client, extract_usage_metrics, parse_ai_json, compat_create_kwargs

logger = logging.getLogger(__name__)

# Bump this when any generation prompt changes materially.
PROMPT_VERSION = "2026-04-23-v1"

PROFILE_EN_SYSTEM = """You are an editorial writer for 0to1log, an AI product curation magazine.
Given a product page's content, produce a JSON profile that helps readers understand what this product does and why it matters.

## Fields

1. **name** (string): Official product name with exact casing from the product's website.
   - Do NOT add "AI" or "Tool" unless it's part of the official name.

2. **tagline** (string, max 12 words): Sharp, specific tagline.
   - BAD: "AI-powered tool for developers" (vague, could be anything)
   - GOOD: "Turn any screenshot into production React code" (specific, shows value)

3. **description_en** (string, 2-3 sentences):
   - Sentence 1: How this tool changes your daily workflow (not "AI-powered platform that...")
   - Sentence 2: Who uses it and for what specific task
   - Sentence 3 (optional): Key differentiator vs alternatives

4. **pricing** (one of: "free", "freemium", "paid", "enterprise", or null)

5. **platform** (array of: "web", "ios", "android", "api", "desktop"): Infer from download links, app store badges, API docs.

6. **korean_support** (boolean): true only if Korean UI or documentation exists.

7. **tags** (array, 3-5 lowercase keywords): e.g. ["llm", "chatbot", "productivity"]

8. **primary_category** (one of: "assistant", "image", "video", "audio", "coding", "workflow", "builder", "platform", "research", "community")

9. **secondary_categories** (array from same set): ALL additional categories that apply.

10. **features** (array, 3-5 strings): Each follows "[situation] → [result]" format.
    - BAD: "Advanced AI technology" (vague)
    - GOOD: "Paste a meeting transcript → get a structured summary with action items in 30 seconds"
    - IMPORTANT: If Extracted Facts lists technical_specs or unique_features, you MUST incorporate them into features. For example, if facts say "200K token context window", a feature should mention it: "Upload a 200-page document → get a full summary using the 200K token context window"

11. **use_cases** (array, 2-3 strings): Each follows "[Specific person/role] + [specific task in specific situation]".
    - BAD: "For developers" (too broad)
    - GOOD: "A freelance designer creating 20 product mockups for an e-commerce client in one afternoon"

12. **getting_started** (array, exactly 3 strings):
    - Step 1: How to sign up or access
    - Step 2: First meaningful action
    - Step 3: First success moment — what you achieve within 5 minutes

13. **pricing_detail** (string or null): Markdown table of pricing plans. Only include plans visible on the page. If gated, use null.

## Example

```json
{
  "name": "Cursor",
  "tagline": "AI-native code editor that writes, refactors, and debugs with you",
  "description_en": "Highlight code and ask a question, describe a function in plain English and watch it appear. Built on VS Code so all your extensions still work.",
  "pricing": "freemium",
  "platform": ["desktop"],
  "korean_support": false,
  "tags": ["ide", "code-generation", "developer-tools"],
  "primary_category": "coding",
  "secondary_categories": [],
  "features": ["Type a comment → code appears below automatically", "Select a function and ask 'refactor this' → cleaner version with explanation", "Chat with your entire codebase using @-mentions"],
  "use_cases": ["A backend developer refactoring a 3-year-old codebase across 50 files in a day", "A solo indie hacker building a full-stack app without leaving their editor"],
  "getting_started": ["Download Cursor from cursor.com", "Open an existing project", "Press Cmd+K, describe a function, and watch it generate working code"],
  "pricing_detail": "| Plan | Price | Includes |\\n|---|---|---|\\n| Hobby | $0 | 2000 completions/mo |\\n| Pro | $20/mo | Unlimited |"
}
```

Respond with JSON only."""

PROFILE_KO_SYSTEM = """You are a Korean editorial writer for 0to1log, an AI product curation magazine for Korean readers.
Given the English profile of a product, write the Korean version of specific fields.

## Important
- Write NATURALLY in Korean — this is NOT a translation task.
- Use the English profile as factual reference, but choose different angles and expressions.
- Technical terms (API, LLM, RAG) stay in English. Add brief Korean context only if the term is obscure.
- Tagline: max 25 characters (Korean). Format: "[핵심 기능] — [차별점]"
  - BAD: "Drive·Gmail·Docs에서 바로 물어보고 즉시 정리 — Google Workspace 작업을 빠르게 끝내는 도우미" (too long, 42 chars)
  - GOOD: "Drive·Gmail 즉시 요약 — Workspace AI 도우미" (22 chars)

## Fields

1. **name_ko** (string or null): Korean transliteration ONLY if commonly used in Korean tech community.
   - "미드저니" for Midjourney, "클로드" for Claude, "제미나이" for Gemini, "퍼플렉시티" for Perplexity
   - null for ChatGPT, Cursor, GitHub Copilot (Koreans use the English name as-is)
   - When in doubt, prefer providing a transliteration over null — Korean readers appreciate it

2. **tagline_ko** (string): Natural Korean tagline, NOT a translation of the English one.

3. **description_ko** (string, 2-3 sentences): Same structure as EN but naturally written for Korean readers.

4. **features_ko** (array): Same features, naturally rewritten in Korean. Keep technical terms in English.

5. **use_cases_ko** (array): Korean use cases using "[구체적 대상]이 [구체적 상황]에서 [구체적 작업]할 때" format.

6. **getting_started_ko** (array, exactly 3 strings): Same 3 steps, natural Korean.

7. **pricing_detail_ko** (string or null): Same pricing table in Korean. Keep $ prices as-is, translate plan descriptions.

## Example

For a coding tool (EN tagline: "AI-native code editor that writes, refactors, and debugs with you"):
```json
{
  "name_ko": null,
  "tagline_ko": "코드 작성·리팩토링·디버깅을 AI와 함께 — VS Code 기반 AI 에디터",
  "description_ko": "코드를 드래그해서 질문하고, 함수를 자연어로 설명하면 자동 생성됩니다. VS Code 기반이라 기존 확장이 그대로 작동합니다.",
  "features_ko": ["주석으로 설명 → 아래에 코드 자동 생성", "함수 선택 후 '리팩토링해줘' → 개선된 코드 제공", "@멘션으로 코드베이스 전체와 대화"],
  "use_cases_ko": ["3년 된 코드베이스를 하루 만에 리팩토링하는 백엔드 개발자", "에디터를 떠나지 않고 풀스택 앱을 만드는 1인 개발자"],
  "getting_started_ko": ["cursor.com에서 다운로드", "기존 프로젝트 열기", "Cmd+K를 누르고 함수를 설명하면 코드가 생성"],
  "pricing_detail_ko": "| 플랜 | 가격 | 포함 |\\n|---|---|---|\\n| Hobby | $0 | 월 2000 완성 |\\n| Pro | $20/월 | 무제한 |"
}
```

Respond with JSON only."""

ENRICH_SYSTEM = """You are an editorial reviewer for 0to1log, an AI product curation magazine.
Given a product's profile and user reviews, produce enrichment data for AI beginners.

## Rules
- If reviews say "(not available)", base ALL fields on the product page. Do NOT fabricate opinions or experiences.
- scenarios: cover 5 diverse situations (work, study, personal, creative, side-project). Target someone who has NEVER used AI.
- pros: exactly 3, backed by evidence. cons: 1-3, only what you can support. If no reviews, at most 1 con from observable facts.
- editor_note: editorial "we" voice ("worth trying if", "best suited for"). No first-person claims.
- scenarios_ko, pros_cons_ko, editor_note_ko: naturally written Korean, NOT translations. Same count as EN versions.

## Fields

| Field | Type | Notes |
|-------|------|-------|
| scenarios | [{title, steps}] × 5 | title: specific task ≤10 words. steps: 2-3 sentences with → arrows |
| scenarios_ko | [{title, steps}] × 5 | Same 5 scenarios in natural Korean |
| pros_cons | {pros: [×3], cons: [×1-3]} | Factual one-sentence observations. BAD: "Great AI". GOOD: "Free tier includes GPT-4o mini with no limit" |
| pros_cons_ko | {pros: [×3], cons: [×1-3]} | Same count, natural Korean |
| difficulty | "beginner" / "intermediate" / "advanced" | beginner=no setup, intermediate=some learning, advanced=coding required |
| editor_note | string (1-2 sentences) | BAD: "I use this every day". GOOD: "Worth trying if you draft emails regularly" |
| editor_note_ko | string (1-2 sentences) | "추천합니다", "적합합니다" voice |
| korean_quality_note | string or null | null if no Korean support. Otherwise describe actual quality. |

Respond with JSON only."""

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
- Sentence 1: How this tool changes your daily workflow (not "AI-powered platform that...")
- Sentence 2: Who uses it and for what specific task
- Sentence 3 (optional): Key differentiator vs alternatives
Respond with plain text only."""

DESCRIPTION_KO_SYSTEM = """AI 제품 큐레이션 매거진을 위한 제품 설명을 작성합니다.
제품명과 URL을 바탕으로 한국어 2-3문장 설명을 작성하세요:
- 1문장: 이 도구가 당신의 일상 작업을 어떻게 바꾸는지 (막연한 "AI 기반 플랫폼"은 금지)
- 2문장: 누가 어떤 작업에 사용하는지
- 3문장 (선택): 대안 대비 핵심 차별점
순수 텍스트만 응답하세요."""

SEARCH_CORPUS_SYSTEM = """You generate search keywords for an AI product directory.
Given a product's name, URL, category, tagline, description, features, and use cases,
produce a single block of space-separated keywords and short phrases that a user might type
when looking for this kind of tool.

## Requirements

1. Include ALL of these keyword types:
   - Product name variants: full name, abbreviations, common misspellings
   - Korean name/transliteration if applicable
   - Intent phrases (KO): "~하고 싶을 때", "~하는 방법", "~하려면", "~추천"
   - Intent phrases (EN): "how to ~", "best tool for ~", "~ alternative"
   - Action verbs (KO+EN): what the user DOES with this tool
   - Synonyms and related terms for core functionality
   - Target audience keywords: roles, industries, skill levels
   - Problem keywords: what pain point does this solve?
   - Comparison terms: "vs", "alternative to [competitor]"
   - Category and subcategory terms in both languages

2. Format: One continuous block of text. No JSON, no bullets, no line breaks.
   Just space-separated words and short phrases.

3. Length: 150-300 words. Be comprehensive but not repetitive.

4. Language: Mix Korean and English naturally. Korean users often search in mixed language.

## Example

For a product like "Runway" (video generation):
runway 런웨이 영상 생성 비디오 만들기 동영상 제작 AI영상 영상편집 영상만들고싶을때 동영상만들기 video generation video editing text to video 텍스트로영상 광고영상제작 뮤직비디오 숏폼 shorts 릴스 모션그래픽 motion graphics animate 애니메이션 영상AI추천 video ai tool 마케터 크리에이터 유튜버 콘텐츠제작 영상편집도구 무료영상편집 video creator alternative to premiere 프리미어대안 영상자동생성 ai video editor 영상제작방법 how to make ai video best video ai ...

Respond with the keyword text only — no explanation, no formatting."""

CLASSIFY_PRODUCT_SYSTEM = """Classify this AI product into structured categories.
Given the product name, URL, and page content excerpt, return JSON:

{
  "primary_category": "one of the categories below",
  "product_nature": "one of: tool, platform, service, library, framework, community",
  "target_audience": "one of: beginner, creator, developer, business, researcher",
  "key_differentiator": "one phrase, max 10 words"
}

Categories: assistant, image, video, audio, coding, workflow, builder, platform, research, community
- assistant: chatbots, conversational AI, LLMs with a chat interface, search AI. If the PRIMARY use is "ask questions and get answers" → assistant. Products like ChatGPT, Claude, Gemini, Perplexity are assistants even if they also have an API.
- image: image generation, editing, design tools
- video: video generation, editing
- audio: TTS, music, voice, transcription
- coding: IDEs, code generation, dev tools (Cursor, GitHub Copilot, Replit)
- workflow: automation, analytics, project management (n8n, Zapier)
- builder: app builders, no-code, LLM frameworks (Langchain, Flowise)
- platform: ONLY for products whose PRIMARY purpose is hosting/serving OTHER models or providing infrastructure. Examples: AWS Bedrock, Replicate, Hugging Face Inference. A product that has an API is NOT automatically a platform.
- research: papers, academic tools
- community: forums, newsletters, directories

## Disambiguation Rules
- "Has an API" does NOT make it a platform. ChatGPT has an API but it's an assistant.
- "Supports multiple models" does NOT make it a platform unless hosting models IS the core product.
- If end users primarily use a chat/conversation interface → assistant
- If developers primarily use it to host/deploy/serve models → platform
- If the product is an LLM with both chat UI and API → assistant (the chat UI is the primary product)

Product nature:
- tool: standalone app users interact with directly (most products)
- platform: hosts or serves other tools/models (Replicate, HuggingFace)
- service: managed cloud service (AWS Bedrock, Azure OpenAI)
- library: code dependency (pip install, npm install)
- framework: developer scaffold for building apps
- community: directory, forum, or content hub

Target audience: the PRIMARY user, not everyone who might use it.

## secondary_categories rules
- secondary_categories should NOT include the primary_category (no duplicates).
- Do NOT add "platform" to secondary_categories for products like ChatGPT, Claude, Gemini — having an API does not make it a platform.
- Only add "platform" if the product genuinely hosts/serves OTHER people's models (e.g., Hugging Face is an assistant AND a platform).

Respond with JSON only."""

EXTRACT_FACTS_SYSTEM = """Extract structured facts about this AI product from the provided sources.
Return JSON:
{
  "official_name": "exact name from the product's website",
  "core_capability": "the ONE thing this product does best, max 15 words",
  "technical_specs": ["specific capabilities with numbers/versions, e.g. '200K token context window'"],
  "unique_features": ["features that distinguish from competitors — use the product's official feature names, e.g. 'Artifacts', 'Deep Research', 'Gems'"],
  "pricing_tiers": [{"name": "Free", "price": "$0", "key_limits": "..."}] or null,
  "platforms": ["web", "ios", "android", "api", "desktop"],
  "integrations": ["named integrations, e.g. 'Google Workspace', 'Slack'"],
  "limitations_observed": ["limitations mentioned in sources"],
  "korean_support_evidence": "direct quote about Korean language support, or 'No Korean support information found in sources'"
}

Rules:
- ONLY include facts explicitly stated in the provided sources.
- For technical_specs: numbers matter — context window size, model count, supported language count, etc.
- For unique_features: use official feature names from the product page, NOT generic descriptions like "AI-powered".
- For pricing_tiers: null if no pricing info in sources. Include all tiers visible.
- Empty array or null for fields with no evidence.

Respond with JSON only."""

CATEGORY_GUIDES = {
    "assistant": {
        "feature_focus": "Model capabilities, context window size, multimodal support (image/file/voice), plugin/tool ecosystem, conversation memory",
        "use_case_frame": "[Non-technical person] using AI to [specific daily task] at [work/school/home]",
        "getting_started_note": "Step 1: sign up (free tier). Step 3: first 'wow' moment — describe a concrete result the user sees",
        "tagline_rule": "Lead with what the user DOES, not what the AI IS. BAD: 'Advanced AI assistant'. GOOD: 'Ask anything, get answers with sources and files'",
        "anti_patterns": "Do not say 'powered by GPT/Claude'. Avoid comparing to other assistants unless it's a key differentiator.",
    },
    "image": {
        "feature_focus": "Output quality/resolution, style diversity, editing capabilities (inpainting, outpainting, upscale), input types (text/image/sketch), generation speed",
        "use_case_frame": "[Creative professional or hobbyist] creating [specific visual content] for [specific purpose]",
        "getting_started_note": "Step 1: access method (web/Discord/API). Step 3: first generated image with approximate wait time",
        "tagline_rule": "Lead with the creative outcome. BAD: 'AI image generator'. GOOD: 'Turn a text prompt into publication-quality art in 60 seconds'",
        "anti_patterns": "Do not omit output resolution or watermark policy. Mention style control options.",
    },
    "video": {
        "feature_focus": "Output resolution and duration, rendering time, style/motion control, input types (text/image/video), watermark policy, export formats",
        "use_case_frame": "[Content creator or marketer] producing [specific video type] for [platform or purpose]",
        "getting_started_note": "Step 1: access method. Step 3: first video clip with approximate render time",
        "tagline_rule": "Lead with the creation outcome. BAD: 'AI video platform'. GOOD: 'Turn a text prompt into a cinematic 10-second clip'",
        "anti_patterns": "Do not omit rendering time, output duration limits, or resolution caps.",
    },
    "audio": {
        "feature_focus": "Voice quality/naturalness, supported languages, voice cloning capabilities, real-time vs batch, audio format support, latency",
        "use_case_frame": "[Creator or professional] producing [specific audio content] in [language or context]",
        "getting_started_note": "Step 1: access method. Step 3: first audio output with quality description",
        "tagline_rule": "Lead with the audio outcome. BAD: 'AI voice tool'. GOOD: 'Clone any voice and generate natural speech in 29 languages'",
        "anti_patterns": "Do not omit supported languages or voice quality limitations.",
    },
    "coding": {
        "feature_focus": "Supported languages/frameworks, IDE integration method (extension/standalone/fork), code completion quality, context awareness (codebase-wide or file-level), diff/refactor capabilities",
        "use_case_frame": "[Developer role] doing [specific coding task] in [specific language/framework]",
        "getting_started_note": "Step 1: installation method, not just 'sign up'. Step 3: coding 'aha' moment — describe the first generated/fixed code",
        "tagline_rule": "Lead with the coding action. BAD: 'AI coding assistant for developers'. GOOD: 'Edit code by describing changes in plain English'",
        "anti_patterns": "Do not say 'AI-powered IDE'. Mention specific model support (GPT-4o, Claude, etc.) if available.",
    },
    "workflow": {
        "feature_focus": "Number of app integrations, trigger types (webhook/cron/event), self-host option, visual builder quality, code extensibility, execution limits",
        "use_case_frame": "[Role] automating [specific multi-step process] between [specific apps]",
        "getting_started_note": "Step 1: sign up or self-host command. Step 3: first automation running end-to-end",
        "tagline_rule": "Lead with the automation outcome. BAD: 'AI workflow automation'. GOOD: 'Connect 400+ apps in visual workflows — no code for simple, full JS for complex'",
        "anti_patterns": "Do not omit execution limits or pricing tier differences. Mention self-host option if available.",
    },
    "builder": {
        "feature_focus": "No-code/low-code level, deployment options (hosted/self-host), template library, supported AI models, database integration, collaboration features",
        "use_case_frame": "[Non-developer or developer] building [specific app type] without [specific technical skill]",
        "getting_started_note": "Step 1: sign up or install. Step 3: first deployed app or working prototype",
        "tagline_rule": "Lead with what gets built. BAD: 'No-code AI app builder'. GOOD: 'Build and deploy an AI chatbot in 10 minutes without writing code'",
        "anti_patterns": "Do not conflate no-code and low-code. Be specific about what requires coding.",
    },
    "platform": {
        "feature_focus": "Available models/services, API design (REST/SDK/GraphQL), latency/throughput SLA, pricing model (per-token/per-request/seat), security certifications, region availability",
        "use_case_frame": "[Developer or team] integrating [specific AI capability] into [production application]",
        "getting_started_note": "Step 1: API key or account setup. Step 3: first successful API call with response",
        "tagline_rule": "Lead with the developer value. BAD: 'AI platform for enterprise'. GOOD: 'Access 50+ AI models through one unified API with guaranteed uptime'",
        "anti_patterns": "Do not use marketing language ('enterprise-grade', 'cutting-edge'). Include specific model names and pricing if available.",
    },
    "research": {
        "feature_focus": "Paper access scope (arXiv/PubMed/all), search quality (semantic vs keyword), citation tools, summarization quality, full-text availability",
        "use_case_frame": "[Researcher or student] doing [specific research task] for [academic purpose]",
        "getting_started_note": "Step 1: sign up. Step 3: first useful paper found or summary generated",
        "tagline_rule": "Lead with the research outcome. BAD: 'AI research tool'. GOOD: 'Find and summarize relevant papers from 200M+ articles in seconds'",
        "anti_patterns": "Do not overstate paper coverage. Be specific about which databases are indexed.",
    },
    "community": {
        "feature_focus": "Active user count, content types (posts/tools/datasets/models), curation method (algorithmic/editorial), contribution model, API access",
        "use_case_frame": "[AI enthusiast or professional] discovering [specific resource type] for [specific purpose]",
        "getting_started_note": "Step 1: create account. Step 3: first useful resource discovered or shared",
        "tagline_rule": "Lead with what users find or do. BAD: 'AI community platform'. GOOD: 'Discover, share, and deploy 500K+ open-source AI models'",
        "anti_patterns": "Do not inflate user numbers. Be specific about what type of community it is.",
    },
}


def build_product_category_guide(classification: dict) -> str:
    """Build a category-specific guide string for prompt injection."""
    category = classification.get("primary_category", "assistant")
    nature = classification.get("product_nature", "tool")
    audience = classification.get("target_audience", "beginner")
    differentiator = classification.get("key_differentiator", "")
    guide = CATEGORY_GUIDES.get(category, CATEGORY_GUIDES["assistant"])
    parts = [
        f"## Category-Specific Guide: {category} ({nature} for {audience})",
    ]
    if differentiator:
        parts.append(f"Key differentiator: {differentiator}")
    parts.extend([
        f"Feature emphasis: {guide['feature_focus']}",
        f"Use case format: {guide['use_case_frame']}",
        f"Getting started: {guide['getting_started_note']}",
        f"Tagline: {guide['tagline_rule']}",
        f"Avoid: {guide['anti_patterns']}",
    ])
    return "\n".join(parts)


PRODUCT_GROUNDING_RULES = """## Factual Grounding (MANDATORY)
1. Base ALL claims on the provided page content and reviews.
2. If information is not available, use null or empty array — do NOT fabricate.
3. NEVER fabricate: pricing numbers, user counts, funding amounts, partnership claims.
4. For pricing_detail: only include plans visible on the product page. If pricing is gated behind signup, state that instead of guessing.
5. For features: describe only capabilities confirmed by the page content.
6. For korean_support: only set true if Korean UI or documentation is explicitly mentioned."""


async def _fetch_page_content(url: str) -> str:
    """Fetch product page content using Tavily, with Exa fallback."""
    if not url:
        return ""
    loop = asyncio.get_event_loop()
    # Try Tavily first
    if settings.tavily_api_key:
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=settings.tavily_api_key)
            results = await loop.run_in_executor(
                None,
                lambda: tavily.search(url, max_results=1, include_raw_content=True),
            )
            content_parts = []
            for r in results.get("results", []):
                raw = r.get("raw_content") or r.get("content") or ""
                if raw:
                    content_parts.append(raw)
            if content_parts:
                return "\n\n".join(content_parts)[:4000]
        except Exception as e:
            logger.warning("Tavily fetch failed for %s, trying Exa: %s", url, e)
    # Exa fallback
    if settings.exa_api_key:
        try:
            from exa_py import Exa
            exa = Exa(api_key=settings.exa_api_key)
            exa_res = await loop.run_in_executor(
                None,
                lambda: exa.search_and_contents(url, num_results=1, text={"max_characters": 4000}),
            )
            if exa_res.results:
                return (exa_res.results[0].text or "")[:4000]
        except Exception as e:
            logger.warning("Exa fetch also failed for %s: %s", url, e)
    return ""


async def _fetch_features_content(url: str) -> str:
    """Fetch product features/about page content using Tavily."""
    if not url or not settings.tavily_api_key:
        return ""
    loop = asyncio.get_event_loop()
    base = url.rstrip("/")
    for path in ["/features", "/product", "/about"]:
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=settings.tavily_api_key)
            target = f"{base}{path}"
            results = await loop.run_in_executor(
                None,
                lambda u=target: tavily.search(u, max_results=1, include_raw_content=True),
            )
            for r in results.get("results", []):
                raw = r.get("raw_content") or r.get("content") or ""
                if raw and len(raw) > 200:
                    return raw[:3000]
        except Exception as e:
            logger.debug("Features fetch failed for %s%s: %s", base, path, e)
    return ""


async def _search_brave_product(name: str, url: str) -> str:
    """Search Brave for technical specs, features, and changelog."""
    if not settings.brave_api_key or not name:
        return ""
    try:
        import httpx
        domain = urlparse(url).netloc if url else ""
        query = f'"{name}" features specifications OR pricing OR "context window" OR "language support"'
        if domain:
            query += f" site:{domain}"
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 5},
                headers={
                    "X-Subscription-Token": settings.brave_api_key,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        results = data.get("web", {}).get("results", [])
        if not results:
            return ""
        parts = []
        for r in results[:5]:
            title = r.get("title", "")
            r_url = r.get("url", "")
            desc = r.get("description", "")[:800]
            extra = r.get("extra_snippets", [])
            snippet = "\n".join(extra[:2]) if extra else desc
            parts.append(f"[{title}]({r_url})\n{snippet}")
        return ("## Technical References (Brave Search)\n\n" + "\n\n".join(parts))[:3000]
    except Exception as e:
        logger.debug("Brave product search failed for %s: %s", name, e)
        return ""


async def _extract_product_facts(
    name: str, url: str, sources: dict[str, str],
    client, model: str,
) -> tuple[dict, int]:
    """Extract structured facts from multiple sources. Returns (facts_dict, tokens_used)."""
    source_text_parts = []
    label_map = {
        "homepage": "## Homepage Content",
        "features": "## Features Page Content",
        "brave": "## Technical References (Brave Search)",
    }
    for key, label in label_map.items():
        if sources.get(key):
            source_text_parts.append(f"{label}\n\n{sources[key]}")
    if not source_text_parts:
        return {}, 0

    combined = "\n\n---\n\n".join(source_text_parts)[:8000]
    user_content = f"Product: {name}\nURL: {url}\n\n{combined}"

    try:
        resp = await client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": EXTRACT_FACTS_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=500,
                response_format={"type": "json_object"},
                prompt_cache_key="product-extract-facts",
            ),
        )
        metrics = extract_usage_metrics(resp, model)
        raw = resp.choices[0].message.content or ""
        result = parse_ai_json(raw, "product_facts")
        return result, metrics["tokens_used"]
    except Exception as e:
        logger.warning("Fact extraction failed for %s: %s", name, e)
        return {}, 0


async def _fetch_review_content(name: str) -> str:
    """Search for product reviews and use cases via Tavily, with Exa fallback."""
    if not name:
        return ""
    loop = asyncio.get_event_loop()
    # Try Tavily first
    if settings.tavily_api_key:
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=settings.tavily_api_key)
            results = await loop.run_in_executor(
                None,
                lambda n=name: tavily.search(
                    f"{n} review use cases pros cons",
                    max_results=3,
                ),
            )
            parts = [r.get("content", "") for r in results.get("results", []) if r.get("content")]
            if parts:
                return "\n\n".join(parts)[:3000]
        except Exception as e:
            logger.warning("Tavily review search failed for %s, trying Exa: %s", name, e)
    # Exa fallback
    if settings.exa_api_key:
        try:
            from exa_py import Exa
            exa = Exa(api_key=settings.exa_api_key)
            exa_res = await loop.run_in_executor(
                None,
                lambda n=name: exa.search_and_contents(
                    f"{n} review use cases pros cons",
                    num_results=3, text={"max_characters": 3000},
                ),
            )
            parts = [f"[{r.title}]({r.url})\n{(r.text or '')[:3000]}" for r in exa_res.results]
            if parts:
                return "\n\n".join(parts)[:3000]
        except Exception as e:
            logger.warning("Exa review search also failed for %s: %s", name, e)
    return ""


def _resolve_logo_url(url: str) -> str | None:
    """Generate a logo URL from the product domain using Clearbit/Google fallback."""
    if not url:
        return None
    try:
        domain = urlparse(url).netloc
        if not domain:
            return None
        if domain.startswith("www."):
            domain = domain[4:]
        return f"https://logo.clearbit.com/{domain}"
    except Exception:
        return None


async def _log_generation(
    product_slug: str | None,
    action: str,
    prompt_version: str,
    model_used: str,
    tokens_used: int,
    duration_ms: int,
    success: bool,
    error_message: str | None,
    facts: dict | None,
    validation_warnings: list[str] | None,
) -> None:
    """Insert a row into product_generation_logs. Never raises."""
    try:
        from core.database import get_supabase
        sb = get_supabase()
        sb.table("product_generation_logs").insert({
            "product_slug": product_slug,
            "action": action,
            "prompt_version": prompt_version,
            "model_used": model_used,
            "tokens_used": tokens_used,
            "duration_ms": duration_ms,
            "success": success,
            "error_message": error_message,
            "facts": facts,
            "validation_warnings": validation_warnings,
        }).execute()
    except Exception as e:
        logger.warning("Failed to log product generation: %s", e)


# Buzzword blocklist for taglines — ordered by frequency
_TAGLINE_BUZZWORDS = (
    "ai-powered", "revolutionary", "cutting-edge", "game-changing",
    "innovative", "industry-leading", "next-generation", "state-of-the-art",
)


def _check_profile_format(profile: dict) -> list[str]:
    """Deterministic format checks — no LLM. Returns list of warning strings."""
    warnings: list[str] = []

    tagline = (profile.get("tagline") or "").strip()
    if tagline:
        words = tagline.split()
        if len(words) > 12:
            warnings.append(f"tagline exceeds 12 words ({len(words)})")
        lower = tagline.lower()
        hits = [w for w in _TAGLINE_BUZZWORDS if w in lower]
        if hits:
            warnings.append(f"tagline contains buzzword: {', '.join(hits)}")

    tagline_ko = (profile.get("tagline_ko") or "").strip()
    if tagline_ko and len(tagline_ko) > 25:
        warnings.append(f"tagline_ko exceeds 25 chars ({len(tagline_ko)})")

    features = profile.get("features") or []
    if not (3 <= len(features) <= 5):
        warnings.append(f"features count off (got {len(features)}, expected 3-5)")
    for f in features:
        if isinstance(f, str) and "→" not in f:
            warnings.append(f"feature missing → pattern: {f[:60]}")

    features_ko = profile.get("features_ko") or []
    if features and features_ko and len(features) != len(features_ko):
        warnings.append(f"features EN/KO count mismatch ({len(features)} vs {len(features_ko)})")

    if profile.get("pricing_detail") is None and profile.get("pricing") in ("freemium", "paid", "enterprise"):
        warnings.append("pricing is not free but pricing_detail is null")

    primary = profile.get("primary_category")
    secondary = profile.get("secondary_categories") or []
    if primary in secondary:
        warnings.append(f"primary_category '{primary}' duplicated in secondary_categories")

    return warnings


async def _classify_product(name: str, url: str, facts: dict, client, model: str) -> dict:
    """Classify product into category, nature, audience, and differentiator."""
    if facts:
        facts_summary = json.dumps(facts, indent=2, ensure_ascii=False)[:1500]
        user_content = f"Product: {name}\nURL: {url}\n\nExtracted facts:\n{facts_summary}"
    else:
        user_content = f"Product: {name}\nURL: {url}"
    try:
        resp = await client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": CLASSIFY_PRODUCT_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=200,
                response_format={"type": "json_object"},
                prompt_cache_key="product-classify",
            ),
        )
        metrics = extract_usage_metrics(resp, model)
        raw = resp.choices[0].message.content or ""
        result = parse_ai_json(raw, "product_classify")
        return {**result, "_tokens": metrics["tokens_used"]}
    except Exception as e:
        logger.warning("Product classification failed, using defaults: %s", e)
        return {
            "primary_category": "assistant",
            "product_nature": "tool",
            "target_audience": "beginner",
            "key_differentiator": "",
            "_tokens": 0,
        }


async def _generate_en_profile(
    facts: dict, page_content: str, review_content: str, system_prompt: str,
    client, model: str,
) -> tuple[dict, int]:
    """Generate EN-only product profile. Returns (profile_dict, tokens_used)."""
    parts = []
    if facts:
        parts.append(f"## Extracted Facts\n{json.dumps(facts, indent=2, ensure_ascii=False)}")
    parts.append(f"## Raw Source (additional context)\n{page_content or '(not available)'}")
    parts.append(f"## Reviews & User Experiences\n{review_content or '(not available)'}")
    user_content = "\n\n".join(parts)
    resp = await client.chat.completions.create(
        **compat_create_kwargs(
            model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=2000,
            response_format={"type": "json_object"},
            prompt_cache_key="product-en-profile",
        ),
    )
    metrics = extract_usage_metrics(resp, model)
    raw = resp.choices[0].message.content or ""
    result = parse_ai_json(raw, "product_en_profile")
    return result, metrics["tokens_used"]


async def _generate_ko_profile(
    en_profile: dict, facts: dict, category_guide: str, client, model: str,
) -> tuple[dict, int]:
    """Generate KO-only fields using EN profile + facts as context. Returns (ko_dict, tokens_used)."""
    en_summary = (
        f"Product: {en_profile.get('name', '')}\n"
        f"Tagline: {en_profile.get('tagline', '')}\n"
        f"Description: {en_profile.get('description_en', '')}\n"
        f"Features: {'; '.join(en_profile.get('features', []))}\n"
        f"Use cases: {'; '.join(en_profile.get('use_cases', []))}\n"
        f"Getting started: {'; '.join(en_profile.get('getting_started', []))}\n"
        f"Pricing detail: {en_profile.get('pricing_detail', '(none)')}"
    )
    if facts:
        if facts.get("technical_specs"):
            en_summary += f"\n\nTechnical specs: {json.dumps(facts['technical_specs'], ensure_ascii=False)}"
        if facts.get("unique_features"):
            en_summary += f"\nUnique features: {json.dumps(facts['unique_features'], ensure_ascii=False)}"
        if facts.get("korean_support_evidence"):
            en_summary += f"\nKorean support evidence: {facts['korean_support_evidence']}"
    ko_system = PROFILE_KO_SYSTEM
    if category_guide:
        ko_system += "\n\n" + category_guide
    resp = await client.chat.completions.create(
        **compat_create_kwargs(
            model,
            messages=[
                {"role": "system", "content": ko_system},
                {"role": "user", "content": f"English profile for reference:\n\n{en_summary}"},
            ],
            max_tokens=1500,
            response_format={"type": "json_object"},
            prompt_cache_key="product-ko-profile",
        ),
    )
    metrics = extract_usage_metrics(resp, model)
    raw = resp.choices[0].message.content or ""
    result = parse_ai_json(raw, "product_ko_profile")
    return result, metrics["tokens_used"]


async def _generate_enrichment(
    en_profile: dict, review_content: str, category_guide: str,
    client, model: str,
) -> tuple[dict, int]:
    """Generate enrichment data (scenarios, pros_cons, etc.). Returns (enrich_dict, tokens_used)."""
    en_summary = (
        f"Product: {en_profile.get('name', '')}\n"
        f"Category: {en_profile.get('primary_category', '')}\n"
        f"Description: {en_profile.get('description_en', '')}\n"
        f"Features: {'; '.join(en_profile.get('features', []))}\n"
        f"Use cases: {'; '.join(en_profile.get('use_cases', []))}"
    )
    enrich_system = ENRICH_SYSTEM
    if category_guide:
        enrich_system += "\n\n" + category_guide
    user_content = (
        f"{en_summary}\n\n"
        f"Reviews & user experiences:\n{review_content or '(not available)'}"
    )
    resp = await client.chat.completions.create(
        **compat_create_kwargs(
            model,
            messages=[
                {"role": "system", "content": enrich_system},
                {"role": "user", "content": user_content},
            ],
            max_tokens=2000,
            response_format={"type": "json_object"},
            prompt_cache_key="product-enrichment",
        ),
    )
    metrics = extract_usage_metrics(resp, model)
    raw = resp.choices[0].message.content or ""
    result = parse_ai_json(raw, "product_enrichment")
    return result, metrics["tokens_used"]


async def run_product_generate(body: ProductGenerateRequest) -> tuple[str | dict, str, int]:
    """Run a product AI generation action. Returns (result, model_used, tokens_used)."""
    client = get_openai_client()
    start_time = time.monotonic()

    if body.action == "generate_from_url":
        product_name = body.name or body.url or ""

        # Step 0: 4-source parallel search
        page_content, features_content, brave_content, review_content = await asyncio.gather(
            _fetch_page_content(body.url or ""),
            _fetch_features_content(body.url or ""),
            _search_brave_product(product_name, body.url or ""),
            _fetch_review_content(product_name),
        )

        # Step 0.5: Fact extraction (gpt-5-nano)
        sources: dict[str, str] = {}
        if page_content:
            sources["homepage"] = page_content
        if features_content:
            sources["features"] = features_content
        if brave_content:
            sources["brave"] = brave_content
        facts, facts_tokens = await _extract_product_facts(
            product_name, body.url or "", sources,
            client, settings.openai_model_nano,
        )
        total_tokens = facts_tokens
        logger.info("Facts extracted: %d specs, %d features, pricing=%s",
                     len(facts.get("technical_specs", [])),
                     len(facts.get("unique_features", [])),
                     "yes" if facts.get("pricing_tiers") else "no")

        # Step 1: Classify product (gpt-5-nano, uses facts)
        classification = await _classify_product(
            product_name, body.url or "", facts,
            client, settings.openai_model_nano,
        )
        total_tokens += classification.pop("_tokens", 0)
        category_guide = build_product_category_guide(classification)
        logger.info("Product classified: %s", classification)

        # Step 2: Generate EN profile (gpt-5, with gpt-5-mini fallback; hard-fail if both fail)
        en_system = PROFILE_EN_SYSTEM + "\n\n" + category_guide + "\n\n" + PRODUCT_GROUNDING_RULES
        try:
            en_profile, en_tokens = await _generate_en_profile(
                facts, page_content, review_content, en_system,
                client, settings.openai_model_main,
            )
            total_tokens += en_tokens
        except Exception as e:
            logger.warning("EN profile gpt-5 failed: %s, retrying with gpt-5-mini", e)
            try:
                en_profile, en_tokens = await _generate_en_profile(
                    facts, page_content, review_content, en_system,
                    client, settings.openai_model_light,
                )
                total_tokens += en_tokens
                logger.info("EN profile recovered with gpt-5-mini fallback")
            except Exception as e2:
                logger.error("EN profile fallback also failed: %s", e2)
                await _log_generation(
                    product_slug=body.slug,
                    action=body.action,
                    prompt_version=PROMPT_VERSION,
                    model_used="multiple",
                    tokens_used=total_tokens,
                    duration_ms=int((time.monotonic() - start_time) * 1000),
                    success=False,
                    error_message=str(e2),
                    facts=facts if isinstance(facts, dict) else None,
                    validation_warnings=None,
                )
                raise

        # Step 3+4+5: KO profile + enrichment + search corpus (parallel, gpt-5-mini)
        corpus_context = "\n".join([
            f"Name: {product_name}",
            f"Category: {en_profile.get('primary_category', '')}",
            f"Tags: {', '.join(en_profile.get('tags', []))}",
            f"Description: {en_profile.get('description_en', '')}",
            f"Features: {'; '.join(en_profile.get('features', []))}",
            f"Use cases: {'; '.join(en_profile.get('use_cases', []))}",
        ])

        ko_task = _generate_ko_profile(en_profile, facts, category_guide, client, settings.openai_model_light)
        enrich_task = _generate_enrichment(en_profile, review_content, category_guide, client, settings.openai_model_light)
        corpus_task = client.chat.completions.create(
            **compat_create_kwargs(
                settings.openai_model_light,
                messages=[
                    {"role": "system", "content": SEARCH_CORPUS_SYSTEM},
                    {"role": "user", "content": f"Product: {product_name}\nURL: {body.url}\n\n{corpus_context}"},
                ],
                max_tokens=800,
            ),
        )

        ko_result, enrich_result, corpus_resp = await asyncio.gather(
            ko_task, enrich_task, corpus_task,
            return_exceptions=True,
        )

        # Merge results
        result: dict = {**en_profile}

        if isinstance(ko_result, tuple) and not isinstance(ko_result, Exception):
            ko_data, ko_tokens = ko_result
            if isinstance(ko_data, dict):
                result.update(ko_data)
            total_tokens += ko_tokens
        elif isinstance(ko_result, Exception):
            logger.error("KO profile generation failed: %s", ko_result)

        if isinstance(enrich_result, tuple) and not isinstance(enrich_result, Exception):
            enrich_data, enrich_tokens = enrich_result
            if isinstance(enrich_data, dict):
                result.update(enrich_data)
            total_tokens += enrich_tokens
        elif isinstance(enrich_result, Exception):
            logger.error("Enrichment generation failed: %s", enrich_result)

        if not isinstance(corpus_resp, Exception):
            corpus_metrics = extract_usage_metrics(corpus_resp, settings.openai_model_light)
            total_tokens += corpus_metrics["tokens_used"]
            result["search_corpus"] = (corpus_resp.choices[0].message.content or "").strip()
        else:
            logger.warning("Search corpus generation failed: %s", corpus_resp)

        # Logo fallback
        if not result.get("logo_url"):
            logo = _resolve_logo_url(body.url or "")
            if logo:
                result["logo_url"] = logo

        # Use classification's primary_category as authoritative
        if classification.get("primary_category"):
            result["primary_category"] = classification["primary_category"]

        # Post-processing: assistants should not have "platform" in secondary
        if result.get("primary_category") == "assistant":
            sc = result.get("secondary_categories", [])
            result["secondary_categories"] = [c for c in sc if c != "platform"]

        # Deterministic format validation (no LLM cost)
        result["_validation_warnings"] = _check_profile_format(result)
        if result["_validation_warnings"]:
            logger.info("Profile validation warnings: %s", result["_validation_warnings"])

        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_generation(
            product_slug=body.slug,
            action=body.action,
            prompt_version=PROMPT_VERSION,
            model_used=settings.openai_model_main,
            tokens_used=total_tokens,
            duration_ms=duration_ms,
            success=True,
            error_message=None,
            facts=facts if isinstance(facts, dict) else None,
            validation_warnings=result.get("_validation_warnings"),
        )

        return result, settings.openai_model_main, total_tokens

    if body.action == "pricing_detail":
        model = settings.openai_model_light
        product_name = body.name or body.url or ""
        loop = asyncio.get_event_loop()

        # --- 3-source parallel pricing search ---

        async def _crawl_pricing_url() -> str:
            """Step A: Direct crawl of {url}/pricing via Tavily."""
            if not body.url or not settings.tavily_api_key:
                return ""
            try:
                from tavily import TavilyClient
                tavily = TavilyClient(api_key=settings.tavily_api_key)
                base = body.url.rstrip("/")
                pricing_url = f"{base}/pricing"
                result = await loop.run_in_executor(
                    None,
                    lambda: tavily.search(pricing_url, max_results=1, include_raw_content=True),
                )
                for r in result.get("results", []):
                    raw = r.get("raw_content") or r.get("content") or ""
                    if raw:
                        return f"## Source: Direct pricing page crawl ({pricing_url})\n\n{raw[:3000]}"
            except Exception as e:
                logger.debug("Direct pricing crawl failed for %s: %s", body.url, e)
            return ""

        async def _brave_pricing_search() -> str:
            """Step B: Brave web search for pricing page (no site: restriction for cross-domain pricing)."""
            if not settings.brave_api_key:
                return ""
            try:
                import httpx
                query = f'"{product_name}" pricing plans cost monthly'
                async with httpx.AsyncClient(timeout=10) as http:
                    resp = await http.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        params={"q": query, "count": 3},
                        headers={"X-Subscription-Token": settings.brave_api_key, "Accept": "application/json"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                results = data.get("web", {}).get("results", [])
                if not results:
                    return ""
                parts = []
                for r in results[:3]:
                    title = r.get("title", "")
                    url = r.get("url", "")
                    desc = r.get("description", "")[:600]
                    extra = r.get("extra_snippets", [])
                    snippet = "\n".join(extra[:2]) if extra else desc
                    parts.append(f"[{title}]({url})\n{snippet}")
                return "## Source: Brave Search (official pricing)\n\n" + "\n\n".join(parts)
            except Exception as e:
                logger.debug("Brave pricing search failed for %s: %s", product_name, e)
            return ""

        async def _tavily_pricing_search() -> str:
            """Step C: Tavily general search (fallback)."""
            if not settings.tavily_api_key:
                return ""
            try:
                from tavily import TavilyClient
                tavily = TavilyClient(api_key=settings.tavily_api_key)
                results = await loop.run_in_executor(
                    None,
                    lambda: tavily.search(
                        f"{product_name} pricing plans cost",
                        max_results=3,
                        include_raw_content=True,
                    ),
                )
                parts = []
                for r in results.get("results", []):
                    raw = r.get("raw_content") or r.get("content") or ""
                    if raw:
                        parts.append(raw[:2000])
                if parts:
                    return "## Source: Tavily Search (general pricing info)\n\n" + "\n\n".join(parts)
            except Exception as e:
                logger.debug("Tavily pricing search failed for %s: %s", product_name, e)
            return ""

        # Run A+B+C in parallel, merge non-empty results
        crawl_result, brave_result, tavily_result = await asyncio.gather(
            _crawl_pricing_url(), _brave_pricing_search(), _tavily_pricing_search(),
        )
        pricing_parts = [p for p in [crawl_result, brave_result, tavily_result] if p]
        pricing_context = "\n\n---\n\n".join(pricing_parts)[:6000]

        system = """You research and verify product pricing information.
Given a product name and pricing page content, produce a JSON object with:
1. **pricing** (one of: "free", "freemium", "paid", "enterprise", or null)
2. **pricing_detail** (EN, markdown table): plan name, price, and key features per plan
3. **pricing_detail_ko** (KO, markdown table): same info in Korean, keep $ prices as-is

Rules:
- ONLY include pricing info that is explicitly stated in the provided content
- If pricing info is not available, set pricing_detail and pricing_detail_ko to null
- Do NOT fabricate pricing tiers or prices
- Use markdown table format: "| Plan | Price | Includes |\\n|---|---|---|\\n| ... |"

Respond with JSON only."""

        user_content = (
            f"Product: {product_name}\nURL: {body.url}\n\n"
            f"Pricing page content:\n{pricing_context or '(not available)'}"
        )
        if body.context:
            user_content += f"\n\nExisting product info:\n{body.context}"

        response = await client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=800,
            ),
        )
        raw = response.choices[0].message.content or ""
        metrics = extract_usage_metrics(response, model)
        try:
            result = parse_ai_json(raw, "product_pricing")
        except Exception:
            result = raw.strip()
        return result, metrics["model_used"], metrics["tokens_used"]

    if body.action == "generate_search_corpus":
        model = settings.openai_model_light
        context_parts = []
        if body.name:
            context_parts.append(f"Product: {body.name}")
        if body.url:
            context_parts.append(f"URL: {body.url}")
        if body.context:
            context_parts.append(f"Product details:\n{body.context}")
        user_content = "\n".join(context_parts) or "Generate search keywords for this AI product."

        response = await client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": SEARCH_CORPUS_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=800,
            ),
        )
        raw = response.choices[0].message.content or ""
        metrics = extract_usage_metrics(response, model)
        return raw.strip(), metrics["model_used"], metrics["tokens_used"]

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
        **compat_create_kwargs(
            model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=512,
        ),
    )
    raw = response.choices[0].message.content or ""
    metrics = extract_usage_metrics(response, model)
    return raw.strip(), metrics["model_used"], metrics["tokens_used"]
