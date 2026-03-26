# 0to1log

**한국인을 위한 AI 뉴스 큐레이션 + 용어집 + IT 블로그 플랫폼**

## 왜 만들었나?

AI 뉴스는 **영어가 제일 빠르고 다양**한데, 한국어로만 접하면 정보 격차가 커진다.
그리고 네 가지 문제가 있다:

- **뉴스가 너무 많다** → 영어 소식 중 정말 중요한 건 무엇인가?
- **영문 기술 용어가 어렵다** → "Agent", "RAG", "Fine-tuning"... 정확히 뭐고 왜 중요한가?
- **뉴스와 학습이 분리돼 있다** → 오늘의 AI 뉴스 속 개념을 체계적으로 배우고 싶다면?
- **배운 후 도구를 못 찾는다** → AI 제품이 너무 많은데, 어디서 찾고 어떤 게 나한테 맞는가?

**0to1log는 이 네 가지를 한 곳에서 해결한다.**

## 0to1log의 세 기둥

### 🔍 Daily News Digest

영어 AI 뉴스를 **LLM으로 자동 큐레이션**한다.
스팸이 아닌, 진짜 중요한 소식만.

- **Research 페르소나**: 논문·기술 트렌드 중심
- **Business 페르소나**: 비즈니스·업계 영향 중심
- **한국어 + 영어 동시 제공**

**해결하는 것:** "뉴스가 너무 많다" + "영어 소식을 놓친다"

### 📚 AI Handbook

**핵심 AI 용어를 체계적으로 설명**한다.
뉴스 속 나온 개념을 깊이 있게 이해하고 싶을 때.

- **기초**: 입문자를 위한 쉬운 설명
- **심화**: 개발자/실무자를 위한 기술적 깊이
- **자동 인라인 연결**: 뉴스 속 용어를 클릭하면 용어집으로

**해결하는 것:** "용어가 어렵다" + "뉴스와 학습의 분리"

### ✍️ Blog & AI Product Guides

**AI 도구 선택 가이드**와 **IT 인사이트 글**을 모은다.
새로운 AI 제품이 나왔을 때, 어디서 찾고, 뭐가 다른지, 어떻게 쓰는지.

- **제품 비교 가이드** (ChatGPT vs Claude vs Gemini...)
- **사용 사례** (이 도구로 뭘 할 수 있나)
- **심화 기술 블로그**

**해결하는 것:** "배운 후 도구를 못 찾는다" + "실제 적용이 어렵다"

## 기술 스택

**프론트엔드**
- [Astro](https://astro.build) v5: 빠르고 가벼운 정적 사이트 생성
- [Tailwind CSS](https://tailwindcss.com) v4: 현대적인 디자인 시스템
- 배포: [Vercel](https://vercel.com)

**백엔드**
- [FastAPI](https://fastapi.tiangolo.com): 고성능 Python API 프레임워크
- [PydanticAI](https://ai.pydantic.dev/): 타입 안전한 AI 에이전트 개발
- 배포: [Railway](https://railway.app)

**데이터베이스 & 인증**
- [Supabase](https://supabase.com): PostgreSQL 기반, 내장 Auth & RLS

**AI & 검색**
- [OpenAI](https://openai.com): gpt-4.1, gpt-4.1-mini (뉴스 큐레이션, 용어 설명)
- [Tavily API](https://tavily.com): 의미론적 뉴스 검색 (최신 소식 수집)

**자동화**
- Cron jobs: 매일 뉴스 파이프라인 자동 실행
- GitHub Actions: 배포 자동화

## 현재 상태 & 로드맵

### ✅ 안정적으로 작동 중
- Daily News Digest (매일 자동 생성)
- AI Handbook (1000+ 용어)
- Blog (기술 글 발행)

### 🔄 진행 중
- Weekly Recap (주간 요약 파이프라인 완성, 뉴스 퀄리티 안정화 대기)
- 뉴스 퀄리티 개선 (프롬프트 감사 및 인용 형식 정규화)
- AI Product Guides (상세 가이드 확대)

**로드맵 보기:**
- 현재 스프린트: [ACTIVE_SPRINT](./vault/09-Implementation/plans/ACTIVE_SPRINT.md)
- 전체 Phase 계획: [Phase-Flow](./vault/09-Implementation/plans/Phase-Flow.md)

## 시작하기

### 📖 사용자로서

0to1log 웹사이트에서 뉴스, 용어, 블로그를 브라우징하세요.

→ [0to1log.vercel.app](https://0to1log.vercel.app)

### 👨‍💻 개발자로서

코드와 아키텍처를 이해하고 싶다면:

- **백엔드 아키텍처**: [ARCHITECTURE.md](./ARCHITECTURE.md) — 파이프라인 상세 (Mermaid 다이어그램 포함)
- **백엔드 설정**: [backend/CLAUDE.md](./backend/CLAUDE.md) — FastAPI + AI 파이프라인
- **프론트엔드 설정**: [frontend/CLAUDE.md](./frontend/CLAUDE.md) — Astro v5 + Tailwind CSS
- **설계 & 계획**: [vault/](./vault/) — 시스템 설계 & 의사결정 이력

## 함께하기 & 연락

궁금하거나 함께하고 싶으신 분들은:

- 📧 **Email**: [x0to1log@gmail.com](mailto:x0to1log@gmail.com)
- 𝕏 **Twitter/X**: [@x0to1log](https://x.com/x0to1log)
