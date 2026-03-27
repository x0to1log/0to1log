# README Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a comprehensive, multi-audience README.md that explains 0to1log's value (AI news + terminology + product guides), technology stack, and how to get started.

**Architecture:**
Write a 7-section README following the design spec. Sections progress from problem definition → solutions → technology → current state → getting started. Each section balances clarity (for non-technical users) with depth (for technical users). Links point to vault documentation and external resources.

**Tech Stack:** Markdown, relative links to vault/, external URLs (Vercel, GitHub, etc.)

---

## File Structure

**Files to create:**
- `README.md` — Project root. Main entry point for all audiences.

**Files to reference:**
- `vault/09-Implementation/plans/2026-03-26-README-design.md` — Design spec
- `vault/09-Implementation/plans/ACTIVE_SPRINT.md` — Current sprint status
- `vault/09-Implementation/plans/Phase-Flow.md` — Long-term roadmap
- `backend/CLAUDE.md`, `frontend/CLAUDE.md` — Developer docs
- Project URLs: Vercel deployment, social channels

**No tests needed** — This is documentation, not code. Verification is manual review.

---

## Chunk 1: Basic Structure + Sections 1-2 (Intro + Problem Definition)

### Task 1: Create README.md skeleton with sections 1-2

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write the basic structure and fill sections 1-2**

Create `README.md` at project root with the following content (sections 1-2 only; others will be stubs for now):

```markdown
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
- [PydanticAI](https://docs.pydantic.dev/latest/concepts/agents/): 타입 안전한 AI 에이전트 개발
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

- **아키텍처 개요**: [vault/](./vault/) — 시스템 설계 & 의사결정 이력
- **백엔드 설정**: [backend/CLAUDE.md](./backend/CLAUDE.md) — FastAPI + AI 파이프라인
- **프론트엔드 설정**: [frontend/CLAUDE.md](./frontend/CLAUDE.md) — Astro v5 + Tailwind CSS

## 함께하기 & 연락

궁금하거나 함께하고 싶으신 분들은:

- 📧 **Email**: [x0to1log@gmail.com](mailto:x0to1log@gmail.com)
- 𝕏 **Twitter/X**: [@x0to1log](https://x.com/x0to1log)

**배포 채널:**
- 𝕏 X: 최신 소식 & 커뮤니티 논의
```

- [ ] **Step 2: Verify the file was created correctly**

Run: `cat README.md | head -50`
Expected: Shows the first 50 lines of README.md with proper structure

- [ ] **Step 3: Check Markdown formatting (optional but good)**

Visually skim the file to ensure:
- Headers are properly formatted (`#`, `##`, `###`)
- Bullet points are clear
- Links use correct format: `[text](url)`
- No typos in key terms (AI, Handbook, etc.)

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: create README with core sections (intro, problems, solutions, stack, status, getting-started)"
```

---

## Chunk 2: Link Verification & Final Review

### Task 2: Verify all links and ensure X URL is correct

**Files:**
- Modify: `README.md` (verify X channel link)

- [ ] **Step 1: Check all internal links are relative and correct**

Verify these paths work from project root:
- `./vault/09-Implementation/plans/ACTIVE_SPRINT.md` ✓
- `./vault/09-Implementation/plans/Phase-Flow.md` ✓
- `./backend/CLAUDE.md` ✓
- `./frontend/CLAUDE.md` ✓

Run: `ls -la vault/09-Implementation/plans/ | grep -E "(ACTIVE|Phase)"`
Expected: Both files exist

- [ ] **Step 2: Verify external URLs are correct**

Check:
- Vercel deployment: `https://0to1log.vercel.app` (test in browser if possible)
- X channel: `https://x.com/x0to1log` (should redirect to Amy's X profile)
- OpenAI, Tavily, etc.: Links are canonical and correct

- [ ] **Step 3: Final Markdown syntax check**

Run a quick lint (if available) or manual check:
```bash
grep -E "^\[.*\]\(.*\)" README.md | head -10
```
Expected: All markdown links formatted correctly (no broken syntax)

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: verify links and finalize README"
```

---

## Execution Notes

**Relative Paths:** All internal links use `./` prefix (e.g., `./vault/...`) to be explicit and relative from project root.

**Link Strategy:**
- Internal docs: Relative paths (vault/, backend/, frontend/)
- External: Full URLs (Vercel, X, etc.)
- Email: `mailto:` link

**Review Criteria (before final commit):**
- [ ] Markdown renders cleanly (no syntax errors)
- [ ] All links are clickable and correct
- [ ] Tone is balanced: accessible + technical
- [ ] No placeholder text remains
- [ ] Follows design spec exactly

---

## Success Criteria

✅ **README.md is complete when:**
1. All 7 sections are written per spec
2. All links are verified (internal relative, external absolute)
3. X channel link is `https://x.com/x0to1log`
4. No placeholder or incomplete text
5. Markdown syntax is correct
6. Changes are committed with clear message

---

## Next Steps (Post-Implementation)

After README is complete and committed:
- Verify rendering on GitHub/web
- Optionally: Add to project's main documentation index
- Monitor for user feedback on clarity and usefulness
