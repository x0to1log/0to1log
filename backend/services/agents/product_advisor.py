"""Product AI Advisor service — generates taglines and descriptions from product URL."""

import asyncio
import logging
from urllib.parse import urlparse

from core.config import settings
from models.product_advisor import ProductGenerateRequest
from services.agents.client import get_openai_client, extract_usage_metrics, parse_ai_json

logger = logging.getLogger(__name__)

GENERATE_FROM_URL_SYSTEM = """You are an editorial writer for 0to1log, an AI product curation magazine.
You write for people who are curious about AI tools — from complete beginners to experienced builders.
Your goal: given a product page's content, produce a structured JSON profile that helps readers instantly understand what this product does, how it changes their daily life, and why it matters.

## Chain-of-Thought (silent)

Before generating JSON, silently analyze:
1. What category does this fit?
2. What is the ONE thing this product does best?
3. Who is the primary user?
4. How does using this tool change someone's daily workflow?
Do NOT output this analysis — use it to inform your JSON.

## Field Definitions

1. **tagline** (EN): A sharp, specific tagline (max 12 words).
   - BAD: "AI-powered tool for developers" (vague, could be anything)
   - GOOD: "Turn any screenshot into production React code" (specific, shows value)
   - Lead with the core action/benefit, not the category

2. **tagline_ko** (KO): Natural Korean tagline — NOT a translation of EN.
   - Write as if explaining to a Korean friend who's never used AI
   - Use the format: "[핵심 기능] — [차별점 또는 대상]"
   - Example: "스크린샷 한 장으로 React 코드 생성 — 프론트엔드 속도 혁신"

3. **description_en** (EN, 2-3 sentences):
   - Sentence 1: How this tool changes your daily workflow (not "AI-powered platform that...")
   - Sentence 2: Who uses it and for what specific task
   - Sentence 3 (optional): Key differentiator vs alternatives
   - BAD: "An AI-powered platform for content creation"
   - GOOD: "Draft a week's worth of social media posts in 10 minutes by describing your brand voice and topics."

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

9. **primary_category** (one of: "assistant", "image", "video", "audio", "coding", "workflow", "builder", "platform", "research", "community"):
   - The single best-fit category for this product
   - assistant = chatbots, LLMs, search AI
   - image = image generation, design tools
   - video = video generation/editing
   - audio = TTS, music, voice
   - coding = IDEs, code generation, dev tools
   - workflow = automation, analytics, project management
   - builder = app builders, no-code, LLM frameworks
   - platform = API management, DevOps, model hosting
   - research = papers, academic tools
   - community = forums, newsletters, directories

10. **secondary_categories** (array of strings from the same set above):
    - ALL additional categories that apply — do not limit the count
    - Empty array [] only if it truly fits just one category
    - Be generous: if a product touches coding AND workflow AND builder, include all three

11. **features** (EN, array of 3-5 strings):
    - Each: describe a specific capability as "[situation] → [result]"
    - BAD: "Advanced AI technology" (vague benefit)
    - BAD: "Supports multiple languages" (generic)
    - GOOD: "Paste a meeting transcript → get a structured summary with action items in 30 seconds"
    - GOOD: "Highlight buggy code → get a fix with explanation of what went wrong"

12. **features_ko** (KO, array of 3-5 strings):
    - Same features, naturally written in Korean
    - Keep technical terms as-is (API, LLM, RAG)

13. **use_cases** (EN, array of 2-3 strings):
    - Each: "[Specific person/role] + [specific task in specific situation]"
    - BAD: "For developers" (too broad)
    - GOOD: "A freelance designer creating 20 product mockups for an e-commerce client in one afternoon"
    - GOOD: "A college student summarizing 5 research papers for a thesis literature review"

14. **use_cases_ko** (KO, array of 2-3 strings):
    - "[구체적 대상]이 [구체적 상황]에서 [구체적 작업]할 때" format

15. **getting_started** (EN, array of exactly 3 strings):
    - Step 1: How to sign up or access the tool
    - Step 2: First meaningful action to take
    - Step 3: Your first success moment — what you'll achieve within 5 minutes
    - Each step: one sentence, start with a verb
    - GOOD: ["Create a free account at chat.openai.com", "Ask your first question or upload a file to analyze", "Watch it summarize a 10-page document into 5 bullet points — your first AI 'aha' moment"]

16. **getting_started_ko** (KO, array of exactly 3 strings):
    - Same 3 steps in natural Korean

17. **pricing_detail** (EN, markdown string):
    - A concise markdown table or bullet list of pricing plans
    - Include plan name, price, and key limits/features per plan
    - If pricing is not available on the page, use null
    - GOOD: "| Plan | Price | Includes |\\n|---|---|---|\\n| Free | $0 | 10 messages/day |\\n| Plus | $20/mo | Unlimited, GPT-4o |"

18. **pricing_detail_ko** (KO, markdown string):
    - Same pricing info in Korean. Translate plan descriptions, keep $ prices as-is

## Examples

### ChatGPT (assistant)
```json
{
  "tagline": "Ask anything, get answers with sources and files",
  "tagline_ko": "뭐든 물어보면 답해주는 AI — 파일 분석부터 코딩까지 한 곳에서",
  "description_en": "Ask a question, upload a document, or paste code — get a thoughtful answer in seconds. Handles everything from drafting emails to analyzing spreadsheets to debugging code, all in a single conversation. The default starting point for anyone discovering what AI can do.",
  "description_ko": "질문을 하거나, 문서를 올리거나, 코드를 붙여넣으면 몇 초 만에 답을 받습니다. 이메일 작성, 스프레드시트 분석, 코드 디버깅까지 하나의 대화에서 처리합니다. AI가 처음이라면 여기서 시작하세요.",
  "pricing": "freemium",
  "platform": ["web", "ios", "android", "api", "desktop"],
  "korean_support": true,
  "tags": ["llm", "chatbot", "productivity", "code-assistant", "writing"],
  "primary_category": "assistant",
  "secondary_categories": ["coding"],
  "features": ["Upload a PDF or spreadsheet → get a summary or analysis in seconds", "Paste buggy code → get a working fix with an explanation of what went wrong", "Describe an image you need → DALL-E generates it right in the chat", "Ask a question about current events → get an answer with web sources", "Build a Custom GPT → automate a workflow you repeat every week"],
  "features_ko": ["PDF나 스프레드시트 업로드 → 몇 초 만에 요약 또는 분석 완료", "버그 있는 코드 붙여넣기 → 원인 설명과 함께 수정 코드 제공", "필요한 이미지 설명 → DALL-E가 채팅에서 바로 생성", "최신 이슈 질문 → 웹 출처와 함께 답변 제공", "Custom GPT 만들기 → 매주 반복하는 워크플로우 자동화"],
  "use_cases": ["An office worker drafting and polishing 10 client emails during a morning commute", "A student summarizing 5 research papers for a thesis literature review", "A startup founder generating a pitch deck outline from a rough product description"],
  "use_cases_ko": ["출근길에 클라이언트 이메일 10개를 작성하고 다듬는 직장인", "학위 논문 문헌 조사를 위해 논문 5편을 요약하는 대학원생", "대략적인 제품 설명에서 피치덱 아웃라인을 뽑아내는 스타트업 대표"],
  "getting_started": ["Create a free account at chat.openai.com", "Upload a document and ask 'Summarize the key findings in 5 bullets'", "Watch it condense 10 pages into 5 clear points — your first AI productivity win"],
  "getting_started_ko": ["chat.openai.com에서 무료 계정 생성", "문서를 업로드하고 '핵심 내용을 5개 포인트로 요약해줘'라고 요청", "10페이지가 5줄로 정리되는 걸 확인 — 첫 번째 AI 생산성 경험"],
  "pricing_detail": "| Plan | Price | Includes |\\n|---|---|---|\\n| Free | $0 | GPT-4o mini, limited GPT-4o |\\n| Plus | $20/mo | Unlimited GPT-4o, DALL-E, Advanced Voice |\\n| Team | $30/mo/seat | Collaboration, longer context, admin console |",
  "pricing_detail_ko": "| 플랜 | 가격 | 포함 내용 |\\n|---|---|---|\\n| Free | $0 | GPT-4o mini, 제한적 GPT-4o |\\n| Plus | $20/월 | GPT-4o 무제한, DALL-E, Advanced Voice |\\n| Team | $30/월/인 | 협업, 더 긴 컨텍스트, 관리자 콘솔 |"
}
```

### Cursor (coding)
```json
{
  "tagline": "AI-native code editor that writes, refactors, and debugs with you",
  "tagline_ko": "코드 작성·리팩토링·디버깅을 AI와 함께 — VS Code 기반 AI 코딩 에디터",
  "description_en": "Highlight code and ask a question, describe a function in plain English and watch it appear, or refactor an entire file with one prompt. Built on VS Code so all your extensions still work. Developers report finishing tasks in half the time.",
  "description_ko": "코드를 드래그해서 질문하고, 함수를 자연어로 설명하면 자동 생성되고, 한 줄 프롬프트로 파일 전체를 리팩토링합니다. VS Code 기반이라 기존 확장 프로그램이 그대로 작동합니다.",
  "pricing": "freemium",
  "platform": ["desktop"],
  "korean_support": false,
  "tags": ["ide", "code-generation", "refactoring", "developer-tools"],
  "primary_category": "coding",
  "secondary_categories": [],
  "features": ["Type a comment describing what you need → code appears below it automatically", "Select a function and ask 'refactor this' → get a cleaner version with explanation", "Chat with your entire codebase using @-mentions for files and symbols", "Supports Claude, GPT-4o, and custom model endpoints", "Built on VS Code — all your extensions and keybindings carry over"],
  "features_ko": ["필요한 기능을 주석으로 설명 → 아래에 코드가 자동 생성", "함수를 선택하고 '리팩토링해줘' → 설명과 함께 개선된 코드 제공", "@멘션으로 파일과 심볼을 지정해 코드베이스 전체와 대화", "Claude, GPT-4o, 커스텀 모델 엔드포인트 지원", "VS Code 기반 — 기존 확장 프로그램과 키바인딩 그대로 사용"],
  "use_cases": ["A backend developer refactoring a 3-year-old codebase across 50 files in a day", "A team prototyping a new API endpoint with AI-assisted code generation in 30 minutes", "A solo indie hacker building a full-stack app without leaving their editor"],
  "use_cases_ko": ["3년 된 코드베이스를 하루 만에 50개 파일에 걸쳐 리팩토링하는 백엔드 개발자", "AI 코드 생성으로 30분 만에 새 API 엔드포인트를 프로토타이핑하는 팀", "에디터를 떠나지 않고 풀스택 앱을 만드는 1인 개발자"],
  "getting_started": ["Download Cursor from cursor.com", "Open an existing project or create a new one", "Press Cmd+K, describe a function in English, and watch it generate working code in seconds"],
  "getting_started_ko": ["cursor.com에서 Cursor 다운로드", "기존 프로젝트를 열거나 새 프로젝트 생성", "Cmd+K를 누르고 함수를 설명하면 몇 초 만에 동작하는 코드가 생성되는 걸 확인"],
  "pricing_detail": "| Plan | Price | Includes |\\n|---|---|---|\\n| Hobby | $0 | 2000 completions/mo |\\n| Pro | $20/mo | Unlimited, fast models |\\n| Business | $40/mo/seat | Admin, SSO, audit logs |",
  "pricing_detail_ko": "| 플랜 | 가격 | 포함 내용 |\\n|---|---|---|\\n| Hobby | $0 | 월 2000 완성 |\\n| Pro | $20/월 | 무제한, 빠른 모델 |\\n| Business | $40/월/인 | 관리자, SSO, 감사 로그 |"
}
```

## Self-Verification Checklist

Before returning, verify your output:
- tagline is ≤12 words and starts with a verb or specific noun
- tagline does NOT contain: "AI-powered", "revolutionary", "cutting-edge", "innovative", "game-changing"
- description_en sentence 1 describes HOW the tool changes your workflow, not a category label
- features follow the "[situation] → [result]" pattern
- use_cases include a specific person/role AND a specific task
- getting_started step 3 describes a concrete first success, not a power-user tip
- If information is not available from the page content, use null or empty array — do NOT fabricate

## Output Format

Respond with JSON only:
{
  "tagline": "...",
  "tagline_ko": "...",
  "description_en": "...",
  "description_ko": "...",
  "pricing": "freemium",
  "platform": ["web", "api"],
  "korean_support": false,
  "tags": ["llm", "chatbot"],
  "primary_category": "assistant",
  "secondary_categories": ["coding"],
  "features": ["...", "..."],
  "features_ko": ["...", "..."],
  "use_cases": ["...", "..."],
  "use_cases_ko": ["...", "..."],
  "getting_started": ["Step 1", "Step 2", "Step 3"],
  "getting_started_ko": ["1단계", "2단계", "3단계"],
  "pricing_detail": "| Plan | Price | Includes |\\n|---|---|---|\\n| Free | $0 | ... |",
  "pricing_detail_ko": "| 플랜 | 가격 | 포함 |\\n|---|---|---|\\n| Free | $0 | ... |"
}"""

ENRICH_SYSTEM = """You are an editorial reviewer for 0to1log, an AI product curation magazine.
Given a product's basic info and real user reviews/articles, produce enrichment data that helps AI beginners understand HOW to use this tool in their daily life and make an informed decision.

## Field Definitions

1. **scenarios** (EN, array of exactly 5 objects):
   Each object: {"title": string, "steps": string}
   - title: A specific real-world task in max 10 words
     - BAD: "Content Creation" (vague category)
     - GOOD: "Turn a meeting recording into a team summary"
   - steps: 2-3 short sentences describing the concrete workflow. Use → arrows between steps.
     - BAD: "Use the tool to create content" (vague)
     - GOOD: "Upload the recording → ask 'Summarize key decisions and action items' → paste into Slack #team-updates"
   - Cover 5 diverse situations: work, study, personal, creative, side-project
   - Target: someone who has NEVER used AI tools before

2. **scenarios_ko** (KO, array of exactly 5 objects):
   - Same 5 scenarios, naturally written in Korean — NOT translations
   - Write as if explaining to a Korean friend

3. **pros_cons** (EN, object):
   {"pros": [string, string, string], "cons": [string, string, string]}
   - Each: one factual observation in one sentence, based on actual evidence
   - pros: specific strengths backed by features or reviews
     - BAD: "Great AI technology" (vague marketing)
     - GOOD: "Free tier includes GPT-4o mini with no daily message limit"
   - cons: honest limitations, NOT attacks or comparisons
     - BAD: "Worse than competitors" (subjective)
     - GOOD: "Korean language responses are noticeably less fluent than English"
   - Base on actual user reviews and page content, not assumptions
   - If reviews are not available, base on observable product features/limitations

4. **pros_cons_ko** (KO, object):
   - Same structure, naturally written in Korean

5. **difficulty** (one of: "beginner", "intermediate", "advanced"):
   - beginner: sign up and use immediately, no technical knowledge needed (e.g., ChatGPT, Midjourney)
   - intermediate: some setup or learning curve, but no coding required (e.g., n8n cloud, Notion AI)
   - advanced: requires API keys, coding, or significant technical configuration (e.g., LangChain, self-hosted tools)

## Example

For ChatGPT:
```json
{
  "scenarios": [
    {"title": "Summarize a 30-page report in 1 minute", "steps": "Upload the PDF → ask 'Summarize the key findings in 5 bullet points' → copy the summary into your email or Slack."},
    {"title": "Draft a polished email reply in 10 seconds", "steps": "Paste the email you received → ask 'Write a professional reply agreeing to the meeting but suggesting Thursday instead' → review and send."},
    {"title": "Explain a confusing concept for a presentation", "steps": "Ask 'Explain blockchain to a non-technical audience in 3 sentences' → use the response in your slide deck."},
    {"title": "Create a week of social media posts", "steps": "Describe your brand and audience → ask 'Generate 5 LinkedIn posts about AI productivity tips' → edit the tone and schedule them."},
    {"title": "Debug code without searching Stack Overflow", "steps": "Paste your error message and code → ask 'What's wrong and how do I fix it?' → get a working solution with explanation."}
  ],
  "scenarios_ko": [
    {"title": "30페이지 보고서를 1분 만에 요약하기", "steps": "PDF를 업로드 → '핵심 내용을 5개 포인트로 요약해줘'라고 요청 → 이메일이나 슬랙에 붙여넣기."},
    {"title": "정중한 이메일 답장을 10초 만에 작성하기", "steps": "받은 이메일을 붙여넣기 → '회의에 동의하되 목요일로 제안하는 답장 작성해줘' → 확인 후 발송."},
    {"title": "발표 자료용으로 어려운 개념 쉽게 설명하기", "steps": "'블록체인을 비전문가에게 3문장으로 설명해줘'라고 요청 → 슬라이드에 활용."},
    {"title": "일주일치 SNS 게시물 한 번에 만들기", "steps": "브랜드와 타겟 독자를 설명 → 'AI 생산성 팁에 대한 LinkedIn 게시물 5개 만들어줘' → 톤 수정 후 예약 발행."},
    {"title": "Stack Overflow 없이 코드 디버깅하기", "steps": "에러 메시지와 코드를 붙여넣기 → '뭐가 잘못됐고 어떻게 고치는지 알려줘' → 설명과 함께 해결책 받기."}
  ],
  "pros_cons": {
    "pros": ["Free tier is genuinely usable — no daily message limit on GPT-4o mini", "Handles text, images, files, code, and voice in one interface", "Custom GPTs let you build specialized assistants without coding"],
    "cons": ["Korean responses are noticeably less natural than English", "Free tier has limited access to the latest GPT-4o model", "Cannot access real-time information without enabling web browsing"]
  },
  "pros_cons_ko": {
    "pros": ["무료 플랜이 실사용 가능 — GPT-4o mini 일일 메시지 제한 없음", "텍스트, 이미지, 파일, 코드, 음성을 하나의 인터페이스에서 처리", "Custom GPT로 코딩 없이 전문 어시스턴트 제작 가능"],
    "cons": ["한국어 응답이 영어보다 자연스럽지 않은 편", "무료 플랜에서 최신 GPT-4o 모델 접근이 제한적", "웹 브라우징을 켜지 않으면 실시간 정보에 접근 불가"]
  },
  "difficulty": "beginner"
}
```

## Self-Verification

- scenarios cover 5 DIFFERENT situations (not all work-related)
- Each scenario title is a concrete task, not a category
- Each scenario steps use → arrows and are actionable
- pros_cons are factual observations, not marketing language
- cons are honest but not hostile
- difficulty accurately reflects the signup-to-first-use experience

## Output Format

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


async def _fetch_review_content(name: str) -> str:
    """Search for product reviews and use cases via Tavily."""
    if not name or not settings.tavily_api_key:
        return ""
    try:
        from tavily import TavilyClient
        tavily = TavilyClient(api_key=settings.tavily_api_key)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda n=name: tavily.search(
                f"{n} review use cases pros cons",
                max_results=3,
            ),
        )
        parts = [r.get("content", "") for r in results.get("results", []) if r.get("content")]
        return "\n\n".join(parts)[:3000]
    except Exception as e:
        logger.warning("Tavily review search failed for %s: %s", name, e)
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
            model=model,
            messages=[
                {"role": "system", "content": GENERATE_FROM_URL_SYSTEM},
                {"role": "user", "content": call1_user},
            ],
            max_tokens=1500,
            temperature=0.6,
        )
        call2_task = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": ENRICH_SYSTEM},
                {"role": "user", "content": call2_user},
            ],
            max_tokens=1500,
            temperature=0.6,
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
            metrics2 = extract_usage_metrics(resp2, model)
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

        return result, model, total_tokens

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
