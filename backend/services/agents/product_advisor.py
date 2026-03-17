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
Your goal: given a product page's content, produce a structured JSON profile that helps readers instantly understand what this product does, who it's for, and why it matters.

## Chain-of-Thought (silent)

Before generating JSON, silently analyze:
1. What category does this fit?
2. What is the ONE thing this product does best?
3. Who is the primary user?
4. What differentiates it from alternatives?
Do NOT output this analysis — use it to inform your JSON.

## Field Definitions

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
    - e.g. n8n: primary="workflow", secondary=["builder", "platform"]

11. **features** (EN, array of 3-5 strings):
   - Each: one specific capability in one sentence
   - Start with a verb: "Generates...", "Supports...", "Connects..."
   - BAD: "Advanced AI technology" (vague benefit)
   - GOOD: "Generates unit tests from function signatures" (specific capability)

10. **features_ko** (KO, array of 3-5 strings):
    - Same features, naturally written in Korean
    - Keep technical terms as-is (API, LLM, RAG)

11. **use_cases** (EN, array of 2-3 strings):
    - Each: "[Who] + [when/what situation]"
    - BAD: "For developers" (too broad)
    - GOOD: "Frontend developers prototyping UI from design mockups" (specific)

12. **use_cases_ko** (KO, array of 2-3 strings):
    - "[대상]이 [상황]할 때" format

13. **getting_started** (EN, array of exactly 3 strings):
    - Step 1: How to sign up or access the tool
    - Step 2: First meaningful action to take
    - Step 3: A power-user tip or next step
    - Each step: one sentence, start with a verb
    - GOOD: ["Create a free account at chat.openai.com", "Ask your first question or upload a file to analyze", "Build a Custom GPT to automate your recurring workflow"]

14. **getting_started_ko** (KO, array of exactly 3 strings):
    - Same 3 steps in natural Korean

15. **pricing_detail** (EN, markdown string):
    - A concise markdown table or bullet list of pricing plans
    - Include plan name, price, and key limits/features per plan
    - If pricing is not available on the page, use null
    - GOOD: "| Plan | Price | Includes |\n|---|---|---|\n| Free | $0 | 10 messages/day |\n| Plus | $20/mo | Unlimited, GPT-4o |"

16. **pricing_detail_ko** (KO, markdown string):
    - Same pricing info in Korean. Translate plan descriptions, keep $ prices as-is

## Examples

### ChatGPT (assistant)
```json
{
  "tagline": "Conversational AI for writing, analysis, and code in one chat",
  "tagline_ko": "대화 한 번으로 글쓰기·분석·코딩까지 — 가장 범용적인 AI 어시스턴트",
  "description_en": "Chat with GPT-4o to draft emails, debug code, summarize documents, and analyze data — all in a single conversation. Supports file uploads, image generation, and web browsing. The default starting point for anyone exploring what AI can do.",
  "description_ko": "GPT-4o와 대화하며 이메일 초안, 코드 디버깅, 문서 요약, 데이터 분석을 한 곳에서 처리합니다. 파일 업로드, 이미지 생성, 웹 검색까지 지원. AI를 처음 접하는 사람부터 파워 유저까지 가장 먼저 찾는 도구입니다.",
  "pricing": "freemium",
  "platform": ["web", "ios", "android", "api", "desktop"],
  "korean_support": true,
  "tags": ["llm", "chatbot", "productivity", "code-assistant", "writing"],
  "primary_category": "assistant",
  "secondary_categories": ["coding"],
  "features": ["Multi-modal input: text, images, files, and voice in one conversation", "Web browsing and real-time information retrieval", "Code Interpreter for data analysis and chart generation", "Image generation with DALL-E integration", "Custom GPTs for specialized workflows"],
  "features_ko": ["텍스트, 이미지, 파일, 음성을 하나의 대화에서 멀티모달 입력", "웹 브라우징과 실시간 정보 검색", "Code Interpreter로 데이터 분석과 차트 생성", "DALL-E 통합 이미지 생성", "맞춤형 GPTs로 전문 워크플로우 구성"],
  "use_cases": ["Knowledge workers drafting and refining documents with AI feedback", "Developers debugging code and generating boilerplate in conversation", "Students researching topics with cited sources and summaries"],
  "use_cases_ko": ["지식 노동자가 AI 피드백으로 문서를 작성·수정할 때", "개발자가 대화형으로 코드를 디버깅하고 보일러플레이트를 생성할 때", "학생이 출처가 달린 요약으로 주제를 리서치할 때"],
  "getting_started": ["Create a free account at chat.openai.com", "Ask your first question or upload a file to analyze", "Build a Custom GPT to automate your recurring workflow"],
  "getting_started_ko": ["chat.openai.com에서 무료 계정 생성", "첫 질문을 하거나 파일을 업로드해서 분석", "반복 작업을 자동화하는 Custom GPT 만들기"],
  "pricing_detail": "| Plan | Price | Includes |\n|---|---|---|\n| Free | $0 | GPT-4o mini, 제한적 GPT-4o |\n| Plus | $20/mo | GPT-4o 무제한, DALL-E, Advanced Voice |\n| Team | $30/mo/seat | 협업, 더 긴 컨텍스트, 관리자 콘솔 |",
  "pricing_detail_ko": "| 플랜 | 가격 | 포함 내용 |\n|---|---|---|\n| Free | $0 | GPT-4o mini, 제한적 GPT-4o |\n| Plus | $20/월 | GPT-4o 무제한, DALL-E, Advanced Voice |\n| Team | $30/월/인 | 협업, 더 긴 컨텍스트, 관리자 콘솔 |"
}
```

### Cursor (coding)
```json
{
  "tagline": "AI-native code editor that writes, refactors, and debugs with you",
  "tagline_ko": "코드 작성·리팩토링·디버깅을 AI와 함께 — VS Code 기반 AI 코딩 에디터",
  "description_en": "A VS Code fork with deep AI integration — highlight code and ask questions, generate functions from comments, refactor across files with a single prompt. Supports Claude, GPT-4o, and custom models. Replaces your IDE, not just your autocomplete.",
  "description_ko": "VS Code를 포크해 AI를 깊이 통합한 코딩 에디터입니다. 코드를 드래그해서 질문하고, 주석에서 함수를 생성하고, 한 줄 프롬프트로 파일 전체를 리팩토링합니다. Claude, GPT-4o, 커스텀 모델을 지원합니다.",
  "pricing": "freemium",
  "platform": ["desktop"],
  "korean_support": false,
  "tags": ["ide", "code-generation", "refactoring", "developer-tools"],
  "primary_category": "coding",
  "secondary_categories": [],
  "features": ["Inline code generation from natural language comments", "Multi-file refactoring with project-wide context", "Chat with your codebase using @-mentions for files and symbols", "Supports Claude, GPT-4o, and custom model endpoints", "Built on VS Code with full extension compatibility"],
  "features_ko": ["자연어 주석에서 인라인 코드 생성", "프로젝트 전체 컨텍스트를 활용한 멀티파일 리팩토링", "@멘션으로 파일과 심볼을 지정해 코드베이스와 대화", "Claude, GPT-4o, 커스텀 모델 엔드포인트 지원", "VS Code 기반으로 모든 확장 프로그램 호환"],
  "use_cases": ["Developers refactoring legacy codebases across multiple files", "Teams prototyping new features with AI-assisted code generation", "Solo developers who want IDE-level AI without switching editors"],
  "use_cases_ko": ["레거시 코드베이스를 멀티파일로 리팩토링하는 개발자", "AI 코드 생성으로 새 기능을 빠르게 프로토타이핑하는 팀", "에디터를 바꾸지 않고 IDE 수준 AI를 원하는 1인 개발자"],
  "getting_started": ["Download Cursor from cursor.com", "Open an existing project or create a new one", "Press Cmd+K to generate code from a natural language prompt"],
  "getting_started_ko": ["cursor.com에서 Cursor 다운로드", "기존 프로젝트를 열거나 새 프로젝트 생성", "Cmd+K를 눌러 자연어 프롬프트로 코드 생성"],
  "pricing_detail": "| Plan | Price | Includes |\n|---|---|---|\n| Hobby | $0 | 2000 completions/mo |\n| Pro | $20/mo | Unlimited, fast models |\n| Business | $40/mo/seat | Admin, SSO, audit logs |",
  "pricing_detail_ko": "| 플랜 | 가격 | 포함 내용 |\n|---|---|---|\n| Hobby | $0 | 월 2000 완성 |\n| Pro | $20/월 | 무제한, 빠른 모델 |\n| Business | $40/월/인 | 관리자, SSO, 감사 로그 |"
}
```

### Midjourney (image)
```json
{
  "tagline": "Generate stunning visual art and designs from text prompts",
  "tagline_ko": "텍스트 프롬프트만으로 고퀄리티 아트·디자인 생성 — 스타일 표현력 최강",
  "description_en": "Describe what you want and get publication-quality images in seconds. Excels at artistic styles, concept art, and photorealistic renders. Operates through Discord with a simple /imagine command. The go-to choice when visual quality matters most.",
  "description_ko": "원하는 이미지를 텍스트로 설명하면 출판 수준의 결과물을 수초 내에 생성합니다. 아트 스타일, 컨셉 아트, 포토리얼리스틱 렌더링에 특히 강합니다. Discord에서 /imagine 명령어로 간편하게 사용합니다.",
  "pricing": "paid",
  "platform": ["web"],
  "korean_support": false,
  "tags": ["image-generation", "art", "design", "text-to-image"],
  "primary_category": "image",
  "secondary_categories": [],
  "features": ["Text-to-image generation with industry-leading aesthetic quality", "Style tuning with --style, --stylize, and reference images", "Upscaling and variations from generated results", "Pan and zoom for extending image compositions", "Describe command to reverse-engineer prompts from images"],
  "features_ko": ["업계 최고 수준의 미적 품질로 텍스트→이미지 생성", "--style, --stylize, 참조 이미지로 스타일 튜닝", "생성된 결과물에서 업스케일링과 변형 생성", "팬/줌으로 이미지 구도 확장", "Describe 명령어로 이미지에서 프롬프트 역추출"],
  "use_cases": ["Designers creating concept art and mood boards for client pitches", "Content creators generating unique visuals for social media and blogs", "Game developers prototyping character and environment art"],
  "use_cases_ko": ["클라이언트 프레젠테이션용 컨셉 아트와 무드보드를 만드는 디자이너", "소셜 미디어와 블로그용 독창적 비주얼을 생성하는 콘텐츠 크리에이터", "캐릭터와 환경 아트를 프로토타이핑하는 게임 개발자"],
  "getting_started": ["Subscribe to a plan at midjourney.com", "Join the Discord server and use /imagine with a text prompt", "Experiment with --style and --stylize flags to refine your aesthetic"],
  "getting_started_ko": ["midjourney.com에서 플랜 구독", "Discord 서버에 가입하고 /imagine으로 텍스트 프롬프트 입력", "--style과 --stylize 플래그로 원하는 스타일 조정"],
  "pricing_detail": "| Plan | Price | Includes |\n|---|---|---|\n| Basic | $10/mo | ~200 images/mo |\n| Standard | $30/mo | 15h fast generation |\n| Pro | $60/mo | 30h fast, stealth mode |",
  "pricing_detail_ko": "| 플랜 | 가격 | 포함 내용 |\n|---|---|---|\n| Basic | $10/월 | 약 200장/월 |\n| Standard | $30/월 | 15시간 빠른 생성 |\n| Pro | $60/월 | 30시간 빠른 생성, 스텔스 모드 |"
}
```

### n8n (workflow)
```json
{
  "tagline": "Open-source workflow automation with 400+ app integrations",
  "tagline_ko": "400개 이상 앱 연동 — 셀프호스트 가능한 오픈소스 워크플로우 자동화",
  "description_en": "Connect apps, APIs, and AI models in visual workflows — no code for simple automations, full JavaScript for complex logic. Self-hostable with fair-code license. A developer-friendly alternative to Zapier with complete data ownership.",
  "description_ko": "앱, API, AI 모델을 비주얼 워크플로우로 연결합니다. 간단한 자동화는 노코드로, 복잡한 로직은 JavaScript로 처리합니다. 셀프호스트 가능하고 데이터를 직접 관리할 수 있어 Zapier의 개발자 친화적 대안입니다.",
  "pricing": "freemium",
  "platform": ["web", "api", "desktop"],
  "korean_support": false,
  "tags": ["automation", "workflow", "no-code", "open-source", "integrations"],
  "primary_category": "workflow",
  "secondary_categories": ["builder"],
  "features": ["Visual workflow builder with 400+ pre-built app integrations", "JavaScript/Python code nodes for custom logic", "Self-hostable with Docker or native installation", "AI agent nodes for LLM-powered decision making", "Webhook triggers and cron scheduling for event-driven automation"],
  "features_ko": ["400개 이상의 앱 연동이 내장된 비주얼 워크플로우 빌더", "커스텀 로직을 위한 JavaScript/Python 코드 노드", "Docker 또는 네이티브 설치로 셀프호스트 가능", "LLM 기반 의사결정을 위한 AI 에이전트 노드", "이벤트 기반 자동화를 위한 웹훅 트리거와 크론 스케줄링"],
  "use_cases": ["DevOps teams automating deployment pipelines and monitoring alerts", "Marketers connecting CRM, email, and analytics tools without engineering help", "AI builders chaining LLM calls with data sources and external APIs"],
  "use_cases_ko": ["배포 파이프라인과 모니터링 알림을 자동화하는 DevOps 팀", "엔지니어 도움 없이 CRM, 이메일, 분석 도구를 연결하는 마케터", "LLM 호출을 데이터 소스 및 외부 API와 체이닝하는 AI 빌더"],
  "getting_started": ["Sign up at n8n.io or self-host with Docker", "Create your first workflow by connecting two apps with a trigger", "Add an AI Agent node to make LLM-powered decisions in your flow"],
  "getting_started_ko": ["n8n.io에서 가입하거나 Docker로 셀프호스트", "트리거로 두 앱을 연결하는 첫 워크플로우 생성", "AI Agent 노드를 추가해 LLM 기반 의사결정 구현"],
  "pricing_detail": "| Plan | Price | Includes |\n|---|---|---|\n| Community | $0 | Self-host, unlimited workflows |\n| Starter | $20/mo | Cloud, 2500 executions |\n| Pro | $50/mo | 10K executions, advanced features |",
  "pricing_detail_ko": "| 플랜 | 가격 | 포함 내용 |\n|---|---|---|\n| Community | $0 | 셀프호스트, 무제한 워크플로우 |\n| Starter | $20/월 | 클라우드, 2500 실행 |\n| Pro | $50/월 | 10K 실행, 고급 기능 |"
}
```

## Self-Verification Checklist

Before returning, verify your output:
- tagline is ≤12 words and starts with a verb or specific noun
- tagline does NOT contain: "AI-powered", "revolutionary", "cutting-edge", "innovative", "game-changing"
- description_en sentence 1 describes a concrete action, not a category label
- features are specific capabilities (verb-first), not vague benefits
- use_cases describe real scenarios with specific user types
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
