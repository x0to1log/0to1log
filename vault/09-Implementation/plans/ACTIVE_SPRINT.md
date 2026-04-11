# ACTIVE SPRINT — Handbook Quality & Content Migration (HB-QM)

> **스프린트 기간:** 2026-04-10 ~ 진행 중
> **마지막 업데이트:** 2026-04-10 (NP4-Q 클로즈 + HB-QM 선언, sprint/phase 문서 재정비)
> **목표:** 핸드북 콘텐츠 품질 및 규모 확장 — 138개 전량 재생성 + P0 품질 수정 + SEO 구조화 데이터
> **이전 스프린트:** NP4-Q (News Pipeline v4 Quality Stabilization) — 2026-04-10 명시적 클로즈, 요약 아래 섹션 참조
> **설계 참조:** [[plans/2026-03-31-handbook-quality-audit]], [[plans/2026-04-09-handbook-section-redesign]]

---

## 스프린트 완료 게이트

### 핵심 목표 (전부 통과해야 HB-QM 종료)

- [ ] **HB-MIGRATE-138** — 138개 published 용어 v4 7섹션 구조 + redesign 필드로 전량 regenerate
- [ ] **HQ-01** — Hallucination 즉시 수정 (stereo matching 정의, ecosystem integration adv)
- [ ] **HQ-02** — 비기술 용어 archived 처리 (actionable intelligence, AI-driven efficiencies, warping operation 등)
- [ ] **HQ-11** — SEO 구조화 데이터 (DefinedTerm + FAQPage + BreadcrumbList JSON-LD)
- [ ] **최종 검증** — `ruff check .` + `pytest tests/ -v` 통과

### 선택 목표 (여유 있으면)

- [ ] HQ-03 — 구세대 핵심 용어 재생성
- [ ] HQ-05 — quality_scores 저장 버그 수정
- [ ] HQ-12 — 콘텐츠 톤 재설계 (위키 → 기술 블로그)
- [ ] HQ-13 — term type 재설계 + facet 시스템
- [ ] GPT5-01~05 — gpt-5 단계별 마이그레이션 완료

---

## Current Doing (active work only)

> **운영 규칙:** Current Doing은 **active work만** 추적. done은 자동으로 제거 (commit hash가 provenance). todo는 Current Doing이 아닌 "남은 태스크" 섹션에. 1주 이상 commit 없는 in_progress는 stale 표시.

| Task ID | 제목 | 상태 | 시작 | 예상 완료 |
|---|---|---|---|---|
| HB-MIGRATE-138 | 138개 published 용어 v4 구조로 전량 regenerate (병렬 ~2시간, 비용 ~$15) | todo | — | — |
| GPT5-01 | gpt-5 마이그레이션 — classify/merge/ranking (gpt-5-mini) | in_progress (⚠️ stale: last commit `ff8a081` 9일 전) | 2026-04-01 | — |
| GPT5-01-FIX | merge 프롬프트 gpt-5 호환 — system→user 데이터 이동 | in_progress (⚠️ stale: 매칭 commit 없음) | 2026-04-01 | — |
| WEBHOOK-USER-01 | 유저 Webhook 구독 셀프서비스 | todo | — | — |
| README-01 | 프로젝트 README 작성 | ⚠️ ghost (시작 14일 전, 매칭 commit 0건 — drop or restart 결정 필요) | 2026-03-26 | — |
| UA-02~05 | User Analytics 차트 추가 | ⚠️ stale (시작 14일 전, 매칭 commit 0건 — 상태 확인 필요) | 2026-03-27 | — |

---

## HB-QM 남은 태스크

### BLOCKING — 게이트 통과 필수

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| HB-MIGRATE-138 | todo | 138개 published 용어 v4 구조로 전량 regenerate (병렬 ~2시간, ~$15) | P0 |
| HQ-01 | todo | Hallucination 즉시 수정 — stereo matching, ecosystem integration adv | P0 |
| HQ-02 | todo | 비기술 용어 archived 처리 | P0 |
| HQ-11 | todo | SEO 구조화 데이터 — DefinedTerm + FAQPage + BreadcrumbList JSON-LD | P0 |

### HIGH PRIORITY — 핸드북 콘텐츠 품질 (HQ)

> **설계 문서:** [[plans/2026-03-31-handbook-quality-audit]]
> **배경:** 2026-03-31 published 138개 중 24개 샘플링 심층 분석에서 도출.

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| HQ-03 | todo | 구세대 핵심 용어 재생성 — embedding, reinforcement learning 등 | P1 |
| HQ-05 | todo | quality_scores 저장 버그 수정 — 최근 용어에 점수 미기록 원인 파악 | P1 |
| HQ-12 | todo | 콘텐츠 톤 재설계 — "AI 위키" → "기술 블로그" 전환 | P1 |
| HQ-13 | todo | term type 재설계 + facet 시스템 — type 8개 + intent/volatility facet | P1 |
| HQ-06 | todo | 콘텐츠 최소 기준 코드화 — basic ≥2500자, adv ≥7000자, 비교표/수식 체크 | P2 |
| HQ-07 | todo | 레퍼런스 다양성 제어 — 같은 batch 동일 URL 인용 비율 제한 | P2 |
| HQ-08 | todo | 중복 용어 병합 — variation operator → evolutionary search 등 | P2 |

**완료된 HQ (NP4-Q 기간):**
- HQ-04 — 5-point self-check + 코드 blocklist/suffix 필터
- HQ-09 — 카테고리 재설계 11→9, 212개 마이그레이션
- HQ-10 — 9 CATEGORY_CONTEXT + Basic TYPE_GUIDE 10개
- HQ-14 — LLM gate 추출 필터 (nano pre-gen 검증)

### HIGH PRIORITY — 핸드북 심화 품질 (HB-QUALITY)

| Task | 상태 | 목표 |
|------|------|------|
| HB-QUALITY-01 | todo | Advanced 콘텐츠 깊이 강화 — 벤치마크 수치 필수, 아키텍처 상세, 논문 참조 |
| HB-QUALITY-02 | todo | 비교표 정확성 — 현재 경쟁 모델과 비교 (2세대 전 모델 금지) |
| HB-QUALITY-03 | todo | Exa deep context 트리거 검증 — 최신 용어에서 실제로 작동하는지 확인 |
| HB-QUALITY-04 | todo | Basic/Advanced 깊이 차이 명확화 — Basic은 비유+사례, Advanced는 수치+코드+논문 |

> **배경 (3/27 gemini-31 기준):** 비교표가 GPT-4o/Gemini 1.0 (현재 경쟁은 GPT-5.2/Claude Opus 4.6), 벤치마크 수치 없음, 정보 "2024 baseline" (현재 2026).

### HIGH PRIORITY — 핸드북 UX 개선 (HB-UX)

> **설계 문서:** [[plans/2026-04-10-handbook-ux-improvements]]
> **배경:** 2026-04-10 Advanced 페이지 시각 리듬 부족 + 코드 섹션 스크롤 부담 관찰. Basic은 HB-REDESIGN으로 정돈됐지만 Advanced는 단조로움.

| Task | 상태 | 목표 | 우선도 | Commit |
|------|------|------|--------|--------|
| HB-UX-01 | done | Advanced §3 code block collapsed by default — macOS window 헤더 유지, 펼치기 버튼 (rehypeCodeWindow 옵션 확장, handbook advanced processor에만 scoping) | P1 | `a744824` |
| HB-UX-02 | done | §5 Production pitfalls callout 스타일링 — rehypeHandbookSectionMarkers 플러그인으로 ul 태그 + 좌측 경고 bar + 연노란 배경 | P1 | `7571d36` + `0f7b707` (프롬프트 bullet 강제) |
| HB-UX-03 | done | §6 blockquote CSS — 단 effect는 news blockquote에만 (handbook §6는 ul/li 구조라 별도 처리 필요 → HB-UX-04로) | P2 | `7571d36` |
| HB-UX-04 | done | §6 Industry dialogue marker — rehypeHandbookSectionMarkers 확장 + accent border + italic + bold de-italic + Hero label semantic 수정 (h2→div role=heading) | P1 | `b64e789` |
| HB-UX-05 | **cancelled** | ~~Advanced 사이드바 체크리스트~~ — 사용자 거부 ("판단할 수 있나요?" 인위적, 콘텐츠 감 부족) | — | — |
| HB-UX-06 | todo | §4 Tradeoffs 2-column grid — "적합한 경우" / "피해야 할 경우" heading pair 감지 rehype 플러그인 + 2-col CSS | P2 | — |

**구현 전략:**
- **Phase 1 ✅ done (commits a744824 → 7571d36 → 0f7b707 → b64e789):** HB-UX-01/02/03/04 — CSS/renderer + 마커 플러그인 + 프롬프트 §5 bullet 강제. 효과 즉시.
- **Phase 2 (HB-MIGRATE-138과 통합, +1.5h):** HB-UX-06만 남음. 새 rehype plugin (`rehypeHandbookSectionCards`) + §4 프롬프트 heading pair 강제 + regen 필요. 별도 batch 비용 arbitrage 가능.

**HB-UX Phase 1 회고 (2026-04-11):**
- Playwright 시각 검수가 silent failure 잡음 — HB-UX-03이 commit 시점엔 작동하는 줄 알았으나 §6 콘텐츠가 ul/li 구조라 효과 0. HB-UX-04가 그 fix.
- §5 pitfalls 프롬프트 format이 free-form text였다가 callout 추가 후 bullet 강제 (`0f7b707`) — UI 변경이 backend prompt 수정을 trigger한 사례.
- 마커 플러그인 (`rehypeHandbookSectionMarkers`) 패턴이 §5/§6 모두 재사용. 새 추상화 안 만들어도 확장 가능 = 좋은 plugin 설계 신호.

### 뉴스 파이프라인 — rolling 개선

| Task | 상태 | 목표 |
|------|------|------|
| NQ-09 | todo | 랭킹에 "어제 발행 뉴스 제목" 전달 — 같은 이벤트 다른 URL 반복 방지 |
| NQ-15 | todo | Learner 콘텐츠 재설계 — "Expert의 쉬운 버전" 아닌 학습자 관점 재구성 |
| NQ-21 | todo | GitHub Trending 축소 + 급부상 오픈소스 별도 제공 |
| NQ-23 | todo | CP 안정화 — semaphore 동시성 제어 + URL canonicalization |
| NQ-24 | todo | 파이프라인 테스트 전면 재작성 — 현재 계약 기반 mock 테스트 |
| COLLECT-BRAVE-01 | todo | Brave Search API 수집기 추가 — 무료 티어, 뉴스 필터 |

### GPT-5 마이그레이션 (진행 중)

> **배경:** OpenAI gpt-4.1 deprecation 대비. Allowed: gpt-5, gpt-5-mini, gpt-5-nano.
> 2026-03-31 한번에 전부 교체 → gpt-5-mini classify 0 picks → revert. 단계별 마이그레이션 전략.

| Task | 상태 | 목표 |
|------|------|------|
| GPT5-01 | in_progress (⚠️ stale) | classify/merge/ranking → gpt-5-mini |
| GPT5-01-FIX | in_progress (⚠️ stale) | merge 프롬프트 gpt-5 호환 — system→user 데이터 이동 |
| GPT5-02 | todo | community_summarize → gpt-5-nano |
| GPT5-03 | todo | Writer digest → gpt-5 |
| GPT5-04 | todo | 전체 파이프라인 backfill 비교 검증 |
| GPT5-05 | todo | main 머지 + gpt-4.1 deprecation 대응 완료 |

### User Analytics — Site Analytics 차트

> **설계:** [[plans/2026-03-27-dau-mau-tracking]]

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| UA-01 | done | DAU/MAU 숫자 대시보드 표시 (profiles.last_seen_at) | P0 |
| UA-02 | ⚠️ stale | DAU/MAU 트렌드 차트 | P0 |
| UA-03 | ⚠️ stale | 유저 페르소나 분포 파이 차트 | P1 |
| UA-04 | ⚠️ stale | 학습 진행 상세 (read vs learned 비율) | P1 |
| UA-05 | ⚠️ stale | 댓글 활동량 일별 트렌드 | P1 |
| UA-06 | todo | 퀴즈 정답률 by 포스트 | P2 |
| UA-07 | todo | 가입→첫 활동 퍼널 | P2 |

### User Webhook Subscriptions (WEBHOOK-USER-01)

> **설계:** [[plans/2026-03-27-user-webhook-subscriptions]]

| Task | 상태 | 목표 |
|------|------|------|
| WEBHOOK-USER-01a | todo | DB: `user_webhooks` 테이블 + RLS (유저당 5개 상한) |
| WEBHOOK-USER-01b | todo | API: `/api/user/webhooks` CRUD + test 엔드포인트 |
| WEBHOOK-USER-01c | todo | 발송: `fireWebhooks()` 확장 — user_webhooks 동시 조회 |
| WEBHOOK-USER-01d | todo | 페이지: `/settings/webhooks/` UI (목록 + 추가 폼 + 가이드) |
| WEBHOOK-USER-01e | todo | 진입점: 편지지 모달 + 뉴스 스트립 Webhook 링크 연결 |

### OPTIONAL

| Task | 상태 | 목표 |
|------|------|------|
| README-01 | ⚠️ ghost | 프로젝트 README 작성 — 14일 방치, drop or restart 결정 필요 |
| COMMUNITY-01 | todo | Reddit/HN/X 반응 수집 (선택) |
| HANDBOOK-LEVEL-LINK-01 | todo | 페르소나별 핸드북 링크 깊이 |
| QUALITY-HYBRID-01 | todo | 규칙 기반 + LLM 하이브리드 품질체크 |
| PERF-TERMS-CACHE-01 | todo | 뉴스 상세 페이지 용어집 캐시 (200개 초과 시 착수) |

---

## 배경 노트 (HB-QM 관련)

### HB-REDESIGN 핵심 (2026-04-10 완료, 참조용)

**재설계 트리거:** Basic 13섹션 → 중복 3개, "함께 알면 좋은 용어" 30개 중 27개 orphan link, References level 토글 깜빡임, Basic vs Advanced 차별화 실종.

**재설계 결과:** Basic 7섹션 + Hero card + References footer + Sidebar checklist. KO/EN 양쪽 완료, Advanced는 Basic body를 context로 받아 verbatim overlap 0건. 어드민 에디터 redesign 필드 편집 + JSON live validation.

→ 상세: [[12-Journal-&-Decisions/2026-04-10-handbook-section-redesign-shipped]], [[plans/2026-04-09-handbook-section-redesign]]

### HQ-11 SEO 구조화 데이터

**문제:** 핸드북 용어 페이지에 JSON-LD 없음. "RAG란?" 검색에서 리치 스니펫(정의 박스, FAQ) 노출 불가. 검색 유입 경로(C) 차단.

**구현:** Head.astro에 `DefinedTerm` 스키마 + "주의할 점" 섹션을 `FAQPage`로 변환 + 카테고리 경로 `BreadcrumbList` 추가.

### HQ-12 콘텐츠 톤 재설계

**문제:** 품질 9/10이지만 "AI가 자동으로 만든 위키"처럼 읽힘. 기술 블로그 톤(누군가의 관점·경험)으로 전환 필요.

**방향:** 프롬프트 톤 변경(백과사전 → 시니어 엔지니어), "왜 알아야 하는지"를 먼저, "정의"는 나중에. HQ-03(구세대 재생성)과 동시 진행 가능.

### HQ-13 term type 재설계 (확정)

- **term type 8개:** concept, model_architecture, technique_method, product_platform, hardware_infra, workflow_pattern, metric_benchmark, protocol_format
- **facet 2개:** intent (understand/compare/build/debug/evaluate), volatility (stable/evolving/fast-changing)
- **evidence 규칙 기반:** type → evidence 자동 매핑 (LLM 분류 불필요)
- **구현 범위:** DB 컬럼 추가, 분류 프롬프트 확장, TYPE_SECTION_WEIGHTS 정의, 프론트엔드 섹션 차별화, 225개 기존 용어 마이그레이션

---

## NP4-Q 스프린트 클로즈 요약 (2026-03-15 ~ 2026-04-10)

**기간:** 27일 | **commits:** 100+ | **완료율:** 100% (핵심 게이트 전부 통과)

### 주요 달성

**Pipeline Architecture (v4):**
- v4 Pydantic 모델 (2 personas: Expert + Learner, Beginner 제거)
- Skeleton-map 라우팅 (Research/Business × Expert/Learner = 4 skeleton)
- Cron 자동화 + E2E 검증 + Backfill 지원
- News Run + Handbook Run 분리, pipeline_logs 로깅, handbook_quality_scores 테이블

**퀄리티 v2:**
- 0~100 스코어링, Research/Business 기준 분리
- LLM 2차 용어 필터링 (gpt-4o-mini)
- Expert/Learner 양쪽 평가, gpt-4.1-mini, 12000자 truncation (`QUALITY-CHECK-02` ✅ `b1fcf46`, `3661fd6`)

**직접 FastAPI 호출 (`FASTAPI-DIRECT-01` ✅ `c63a5e3`):**
- AdminAiConfig 컴포넌트 + 4개 에디터 직접 FastAPI 호출 전환
- Vercel 60s proxy timeout 완전 제거

**뉴스 품질 v7 (NQ-*):**
- **Done (17):** NQ-02 baseline, NQ-03/05/07 KO skeleton + 페르소나 톤 + Action Items, NQ-05b Expert 약어, NQ-06/06b CP 전면 재설계, NQ-08 랭킹 분리, NQ-10 citation 중복, NQ-11 CP MANDATORY, NQ-12 citation 포맷, NQ-13 multi-source enrichment, NQ-14 citation 번호, NQ-16 classify/merge 분리, NQ-17 health check, NQ-18 CP 스팸 필터, NQ-19 체크포인트, NQ-20 Writer 다중 소스, NQ-22 CP 전면 재설계 (Summarizer + Entity Search + Brave Discussions)
- **Remaining (5):** NQ-09, NQ-15, NQ-21, NQ-23, NQ-24 → HB-QM으로 이월

**핸드북 재설계 (HB-REDESIGN):**
- KO/EN Basic 7섹션 + Advanced 7섹션 (11→7 재작성)
- Hero card + References footer + Sidebar checklist 3개 컴포넌트
- HB-EDITOR-V2: 어드민 에디터 redesign 필드 편집 + JSON live validation
- 8개 샘플 용어 차별화 매트릭스 전부 통과

**자동화:**
- `AUTOPUB-01` ✅ — Quality ≥85 자동 발행 + 2h 리뷰 윈도우 (07:00→09:00 KST) + draft 이메일 알림 + 어드민 dot (`76e3f51`, `74b13b5`, `711c05b`, `6b22647`)

**Weekly Recap:** 백엔드 완료, 프론트 통합만 남음 (→ HB-QM OPTIONAL)

**PROMPT-AUDIT (52개):**
- **P0 2개:** citation-소스 매핑 해결, URL hallucination 방지
- **P1 9개:** 섹션 구조 싱크, 토큰 효율, few-shot 개선
- **P2 40개:** rolling 프롬프트 개선 작업에 자연스럽게 흡수 → **별도 track 종료** (2026-04-10)

### 설계 참조 (NP4-Q 기간)

- [[2026-03-16-daily-digest-design]] — Daily Digest v3/v4 설계
- [[2026-03-16-weekly-digest-design]] — Weekly Digest 설계
- [[2026-03-17-news-pipeline-v4-design]] — v4 전환
- [[2026-03-18-prompt-audit-fixes]] — 프롬프트 감사 52개
- [[plans/2026-03-25-direct-fastapi-ai-calls]] — FASTAPI-DIRECT
- [[plans/2026-03-26-news-quality-check-overhaul]] — QUALITY-CHECK
- [[plans/2026-03-30-merge-classify-design]] — NQ-16
- [[plans/2026-03-30-multi-source-enrichment]] — NQ-13
- [[plans/2026-03-31-handbook-quality-audit]] — HQ source
- [[plans/2026-04-09-handbook-section-redesign]] — HB-REDESIGN master
- [[12-Journal-&-Decisions/2026-04-10-handbook-section-redesign-shipped]] — 회고

---

## 이전 스프린트 체인

- **HB-QM** (2026-04-10 ~) — **현재**
- NP4-Q (2026-03-15 ~ 2026-04-10) — 게이트 전부 통과, 100+ commits
- Phase 3B-SHARE (2026-03-08 ~ 2026-03-13) — 게이트 전체 통과
- Phase 3A-SEC (2026-03-08 ~ 2026-03-09) — 12개 태스크 완료

## Related

- [[Phase-Flow]] — Phase 진입/완료 기준 상세
- [[Phases-Roadmap]] — 5단계 전략 로드맵
- [[Implementation-Plan]] — 실행 계약 + 운영 원칙
- [[Checklists-&-DoD]] — 완료 기준 체크리스트
