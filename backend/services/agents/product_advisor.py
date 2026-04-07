"""Product AI Advisor service — generates taglines and descriptions from product URL."""

import asyncio
import logging
from urllib.parse import urlparse

from core.config import settings
from models.product_advisor import ProductGenerateRequest
from services.agents.client import get_openai_client, extract_usage_metrics, parse_ai_json, compat_create_kwargs

logger = logging.getLogger(__name__)

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
- Tagline format: "[핵심 기능] — [차별점 또는 대상]"

## Fields

1. **name_ko** (string or null): Korean transliteration ONLY if commonly used.
   - "미드저니" for Midjourney (Korean transliteration is common)
   - null for ChatGPT (Koreans say "ChatGPT" as-is)

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
- assistant: chatbots, LLMs, search AI
- image: image generation, editing, design tools
- video: video generation, editing
- audio: TTS, music, voice, transcription
- coding: IDEs, code generation, dev tools
- workflow: automation, analytics, project management
- builder: app builders, no-code, LLM frameworks
- platform: API management, model hosting, DevOps
- research: papers, academic tools
- community: forums, newsletters, directories

Product nature:
- tool: standalone app users interact with directly
- platform: hosts or serves other tools/models
- service: managed cloud service
- library: code dependency (pip install, npm install)
- framework: developer scaffold for building apps
- community: directory, forum, or content hub

Target audience: the PRIMARY user, not everyone who might use it.

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


async def run_product_generate(body: ProductGenerateRequest) -> tuple[str | dict, str, int]:
    """Run a product AI generation action. Returns (result, model_used, tokens_used)."""
    client = get_openai_client()

    if body.action == "generate_from_url":
        model = settings.openai_model_main
        product_name = body.name or body.url or ""

        # Step 1: Fetch page content + reviews in parallel
        page_content, review_content = await asyncio.gather(
            _fetch_page_content(body.url or ""),
            _fetch_review_content(product_name),
        )

        # Step 2: Call 1 (profile) + Call 2 (enrichment) in parallel
        call1_user = f"Product: {product_name}\nURL: {body.url}\n\nPage content:\n{page_content or '(not available)'}"
        call2_user = (
            f"Product: {product_name}\nURL: {body.url}\n\n"
            f"Page content:\n{page_content or '(not available)'}\n\n"
            f"Reviews & user experiences:\n{review_content or '(not available)'}"
        )

        call1_task = client.chat.completions.create(
            **compat_create_kwargs(
                model,
                messages=[
                    {"role": "system", "content": PROFILE_EN_SYSTEM},
                    {"role": "user", "content": call1_user},
                ],
                max_tokens=2000,
                temperature=0.4,
                response_format={"type": "json_object"},
            ),
        )
        enrichment_model = settings.openai_model_light
        call2_task = client.chat.completions.create(
            **compat_create_kwargs(
                enrichment_model,
                messages=[
                    {"role": "system", "content": ENRICH_SYSTEM},
                    {"role": "user", "content": call2_user},
                ],
                max_tokens=2000,
                temperature=0.5,
                response_format={"type": "json_object"},
            ),
        )

        resp1, resp2 = await asyncio.gather(call1_task, call2_task, return_exceptions=True)

        # Parse Call 1 (profile)
        total_tokens = 0
        if isinstance(resp1, Exception):
            logger.error("Product profile generation failed: %s", resp1)
            result: dict = {}
        else:
            metrics1 = extract_usage_metrics(resp1, model)
            total_tokens += metrics1["tokens_used"]
            raw1 = resp1.choices[0].message.content or ""
            try:
                result = parse_ai_json(raw1, "product_advisor_profile")
            except Exception:
                result = {}

        # Parse Call 2 (enrichment) and merge
        if isinstance(resp2, Exception):
            logger.error("Product enrichment generation failed: %s", resp2)
        else:
            metrics2 = extract_usage_metrics(resp2, enrichment_model)
            total_tokens += metrics2["tokens_used"]
            raw2 = resp2.choices[0].message.content or ""
            try:
                enrich = parse_ai_json(raw2, "product_advisor_enrich")
                if isinstance(enrich, dict) and isinstance(result, dict):
                    result.update(enrich)
            except Exception:
                logger.warning("Failed to parse enrichment response")

        # Add logo_url if AI didn't provide one
        if isinstance(result, dict) and not result.get("logo_url"):
            logo = _resolve_logo_url(body.url or "")
            if logo:
                result["logo_url"] = logo

        # Auto-generate search corpus from merged results
        if isinstance(result, dict) and result:
            corpus_context = "\n".join([
                f"Name: {product_name}",
                f"Category: {result.get('primary_category', '')}",
                f"Tags: {', '.join(result.get('tags', []))}",
                f"Description: {result.get('description_en', '')}",
                f"Features: {'; '.join(result.get('features', []))}",
                f"Use cases: {'; '.join(result.get('use_cases', []))}",
            ])
            try:
                corpus_resp = await client.chat.completions.create(
                    **compat_create_kwargs(
                        settings.openai_model_light,
                        messages=[
                            {"role": "system", "content": SEARCH_CORPUS_SYSTEM},
                            {"role": "user", "content": f"Product: {product_name}\nURL: {body.url}\n\n{corpus_context}"},
                        ],
                        max_tokens=800,
                        temperature=0.7,
                    ),
                )
                corpus_metrics = extract_usage_metrics(corpus_resp, settings.openai_model_light)
                total_tokens += corpus_metrics["tokens_used"]
                result["search_corpus"] = (corpus_resp.choices[0].message.content or "").strip()
            except Exception as e:
                logger.warning("Search corpus generation failed: %s", e)

        return result, model, total_tokens

    if body.action == "pricing_detail":
        model = settings.openai_model_light
        product_name = body.name or body.url or ""
        # Search for pricing info (Tavily with Exa fallback)
        pricing_context = ""
        loop = asyncio.get_event_loop()
        if settings.tavily_api_key:
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
                pricing_context = "\n\n".join(parts)[:5000]
            except Exception as e:
                logger.warning("Tavily pricing search failed for %s, trying Exa: %s", product_name, e)
        if not pricing_context and settings.exa_api_key:
            try:
                from exa_py import Exa
                exa = Exa(api_key=settings.exa_api_key)
                exa_res = await loop.run_in_executor(
                    None,
                    lambda: exa.search_and_contents(
                        f"{product_name} pricing plans cost",
                        num_results=3, text={"max_characters": 2000},
                    ),
                )
                parts = [(r.text or "")[:2000] for r in exa_res.results if r.text]
                pricing_context = "\n\n".join(parts)[:5000]
            except Exception as e:
                logger.warning("Exa pricing search also failed for %s: %s", product_name, e)

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
                temperature=0.3,
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
                temperature=0.7,
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
            temperature=0.6,
        ),
    )
    raw = response.choices[0].message.content or ""
    metrics = extract_usage_metrics(response, model)
    return raw.strip(), metrics["model_used"], metrics["tokens_used"]
