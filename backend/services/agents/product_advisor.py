"""Product AI Advisor service — generates taglines and descriptions from product URL."""

import asyncio
import logging
from urllib.parse import urlparse

from core.config import settings
from models.product_advisor import ProductGenerateRequest
from services.agents.client import get_openai_client, extract_usage_metrics, parse_ai_json, compat_create_kwargs

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

1. **name** (EN): The official product name as used on the product's own website.
   - Use the exact casing from the official site (e.g. "ChatGPT", "n8n", "DALL-E 3")
   - Do NOT add descriptors like "AI" or "Tool" unless it's part of the official name

2. **name_ko** (KO, string or null):
   - Korean name or transliteration ONLY if commonly used in Korean context
   - null if the English name is used as-is in Korea (most AI tools)
   - GOOD: "미드저니" (for Midjourney — Korean transliteration is common)
   - GOOD: null (for ChatGPT — Koreans say "ChatGPT" not "챗지피티")

3. **tagline** (EN): A sharp, specific tagline (max 12 words).
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
  "name": "ChatGPT",
  "name_ko": null,
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
  "name": "Cursor",
  "name_ko": null,
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

### Midjourney (image)
```json
{
  "name": "Midjourney",
  "name_ko": "미드저니",
  "tagline": "Generate stunning visual art and designs from text prompts",
  "tagline_ko": "텍스트 프롬프트만으로 고퀄리티 아트·디자인 생성 — 스타일 표현력 최강",
  "description_en": "Describe what you want and get publication-quality images in seconds. Excels at artistic styles, concept art, and photorealistic renders. Operates through Discord with a simple /imagine command.",
  "description_ko": "원하는 이미지를 텍스트로 설명하면 출판 수준의 결과물을 수초 내에 생성합니다. 아트 스타일, 컨셉 아트, 포토리얼리스틱 렌더링에 특히 강합니다.",
  "pricing": "paid",
  "platform": ["web"],
  "korean_support": false,
  "tags": ["image-generation", "art", "design", "text-to-image"],
  "primary_category": "image",
  "secondary_categories": [],
  "features": ["Describe a scene in words → get a publication-quality image in under 60 seconds", "Add --style or --stylize flags → fine-tune the aesthetic from photorealistic to abstract", "Click 'Upscale' on a result → get a print-ready high-resolution version", "Use pan and zoom → extend an image beyond its original frame", "Upload a reference image → generate variations that match its mood and composition"],
  "features_ko": ["장면을 글로 설명 → 60초 이내에 출판 수준 이미지 생성", "--style, --stylize 플래그 → 포토리얼부터 추상화까지 스타일 미세 조정", "'Upscale' 클릭 → 인쇄 가능한 고해상도 버전 제공", "팬/줌 사용 → 원래 프레임 너머로 이미지 확장", "참조 이미지 업로드 → 분위기와 구도를 맞춘 변형 생성"],
  "use_cases": ["A freelance designer creating 10 concept art variations for a client pitch in one afternoon", "A content creator generating unique blog header images without hiring an illustrator", "A game developer prototyping character designs by describing them in natural language"],
  "use_cases_ko": ["하루 오후에 클라이언트 피칭용 컨셉 아트 변형 10개를 만드는 프리랜서 디자이너", "일러스트레이터 없이 블로그 헤더 이미지를 직접 생성하는 콘텐츠 크리에이터", "자연어로 캐릭터를 설명해서 디자인을 프로토타이핑하는 게임 개발자"],
  "getting_started": ["Subscribe to a plan at midjourney.com", "Join the Discord server and type /imagine followed by your text prompt", "See your first AI-generated artwork appear in under a minute — experiment with styles from there"],
  "getting_started_ko": ["midjourney.com에서 플랜 구독", "Discord 서버에 가입하고 /imagine 뒤에 프롬프트 입력", "1분 이내에 첫 AI 아트가 생성되는 걸 확인 — 거기서부터 스타일 실험 시작"],
  "pricing_detail": "| Plan | Price | Includes |\\n|---|---|---|\\n| Basic | $10/mo | ~200 images/mo |\\n| Standard | $30/mo | 15h fast generation |\\n| Pro | $60/mo | 30h fast, stealth mode |",
  "pricing_detail_ko": "| 플랜 | 가격 | 포함 내용 |\\n|---|---|---|\\n| Basic | $10/월 | 약 200장/월 |\\n| Standard | $30/월 | 15시간 빠른 생성 |\\n| Pro | $60/월 | 30시간 빠른 생성, 스텔스 모드 |"
}
```

### n8n (workflow)
```json
{
  "name": "n8n",
  "name_ko": null,
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
  "features": ["Drag two app nodes onto the canvas → connect them with a line → data flows automatically", "Add a JavaScript node → write custom logic for anything the built-in nodes can't handle", "Set a cron trigger → your workflow runs on schedule without you touching it", "Drop in an AI Agent node → let an LLM make decisions inside your automation", "Self-host with Docker → keep all your data on your own servers"],
  "features_ko": ["두 앱 노드를 캔버스에 드래그 → 선으로 연결 → 데이터가 자동으로 흐름", "JavaScript 노드 추가 → 내장 노드로 안 되는 커스텀 로직 작성", "크론 트리거 설정 → 스케줄에 맞춰 워크플로우가 알아서 실행", "AI Agent 노드 추가 → LLM이 자동화 흐름 안에서 의사결정", "Docker로 셀프호스트 → 모든 데이터를 내 서버에 보관"],
  "use_cases": ["A marketer connecting HubSpot leads to Slack notifications and Google Sheets tracking without writing code", "A DevOps engineer automating deployment alerts from GitHub to Discord with custom severity filtering", "An AI builder chaining GPT-4o calls with a database lookup and Slack notification in one workflow"],
  "use_cases_ko": ["코드 없이 HubSpot 리드를 Slack 알림 + Google Sheets 기록으로 연결하는 마케터", "GitHub에서 Discord로 배포 알림을 자동화하며 심각도 필터링을 추가하는 DevOps 엔지니어", "하나의 워크플로우에서 GPT-4o 호출 + DB 조회 + Slack 알림을 체이닝하는 AI 빌더"],
  "getting_started": ["Sign up at n8n.io or self-host with a single Docker command", "Create your first workflow by dragging a trigger and an action node onto the canvas", "Watch your first automation run end-to-end — data flowing between two apps without you writing a line of code"],
  "getting_started_ko": ["n8n.io에서 가입하거나 Docker 명령어 하나로 셀프호스트", "트리거 노드와 액션 노드를 캔버스에 드래그해서 첫 워크플로우 생성", "코드 한 줄 없이 두 앱 사이에 데이터가 흐르는 첫 자동화를 확인"],
  "pricing_detail": "| Plan | Price | Includes |\\n|---|---|---|\\n| Community | $0 | Self-host, unlimited workflows |\\n| Starter | $20/mo | Cloud, 2500 executions |\\n| Pro | $50/mo | 10K executions, advanced features |",
  "pricing_detail_ko": "| 플랜 | 가격 | 포함 내용 |\\n|---|---|---|\\n| Community | $0 | 셀프호스트, 무제한 워크플로우 |\\n| Starter | $20/월 | 클라우드, 2500 실행 |\\n| Pro | $50/월 | 10K 실행, 고급 기능 |"
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
  "name": "ProductName",
  "name_ko": null,
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

## Important

If review data is not available or says "(not available)", base ALL fields on the product's own page content and observable features. Do NOT fabricate user opinions, quotes, or experiences. Do NOT guess at user experience issues you cannot verify from the product page.

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
   {"pros": [string, string, string], "cons": [1-3 strings]}
   - Each: one factual observation in one sentence, based on actual evidence
   - pros: exactly 3 specific strengths backed by features or reviews
     - BAD: "Great AI technology" (vague marketing)
     - GOOD: "Free tier includes GPT-4o mini with no daily message limit"
   - cons: 1-3 honest limitations, NOT attacks or comparisons. Only include what you can support with evidence.
     - BAD: "Worse than competitors" (subjective)
     - GOOD: "Korean language responses are noticeably less fluent than English"
   - Base on actual user reviews and page content, not assumptions
   - If reviews are not available, include at most 1 con based on observable limitations (e.g., pricing, language support, platform availability). Do not guess at user experience issues.

4. **pros_cons_ko** (KO, object):
   - Same structure, naturally written in Korean
   - Must have the same number of pros and cons as the EN version

5. **difficulty** (one of: "beginner", "intermediate", "advanced"):
   - beginner: sign up and use immediately, no technical knowledge needed (e.g., ChatGPT, Midjourney)
   - intermediate: some setup or learning curve, but no coding required (e.g., n8n cloud, Notion AI)
   - advanced: requires API keys, coding, or significant technical configuration (e.g., LangChain, self-hosted tools)

6. **editor_note** (EN, 1-2 sentences):
   - Draft an editorial recommendation the editor will review and personalize
   - Use third-person editorial voice ("we recommend", "worth trying if", "best suited for")
   - Do NOT claim personal experience with the product ("I use this", "my go-to")
   - Tone: honest, conversational, like a trusted review site
   - Include WHEN to use it or WHO it's best for
   - BAD: "This is a great AI tool" (generic)
   - BAD: "I use this every day" (fabricated personal experience)
   - GOOD: "Worth trying if you draft emails, blog posts, or code regularly — the fastest starting point for AI beginners."

7. **editor_note_ko** (KO, 1-2 sentences):
   - Same editorial recommendation, naturally written in Korean — NOT a translation
   - Use editorial voice: "추천합니다", "적합합니다", "시작하기 좋습니다"
   - Do NOT use first-person claims ("매일 쓰는", "내가 제일 좋아하는")
   - Tone: 신뢰할 수 있는 리뷰처럼 솔직하게

8. **korean_quality_note** (string or null):
   - If the product supports Korean: describe the actual quality of Korean support
   - "Full Korean UI with natural translations" or "Korean UI exists but feels machine-translated" or "No Korean UI but understands Korean input well"
   - null if the product has no Korean support at all

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
  "difficulty": "beginner",
  "editor_note": "Worth trying if you draft emails, blog posts, or code regularly — the fastest starting point for anyone new to AI.",
  "editor_note_ko": "이메일, 블로그, 코드 초안을 자주 작성한다면 써볼 만합니다. AI 입문자에게 가장 추천하는 시작점입니다.",
  "korean_quality_note": "Full Korean UI available. Responses in Korean are usable but noticeably less fluent than English."
}
```

## Self-Verification

- scenarios cover 5 DIFFERENT situations (not all work-related)
- Each scenario title is a concrete task, not a category
- Each scenario steps use → arrows and are actionable
- pros_cons are factual observations, not marketing language
- cons are honest but not hostile
- difficulty accurately reflects the signup-to-first-use experience
- editor_note uses editorial "we" voice — no first-person claims of product usage
- korean_quality_note is null if no Korean support, otherwise describes actual quality

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
                    {"role": "system", "content": GENERATE_FROM_URL_SYSTEM},
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
