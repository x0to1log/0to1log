# ACTIVE SPRINT — Handbook Quality & Content Migration (HB-QM)

> **스프린트 기간:** 2026-04-10 ~ 진행 중
> **마지막 업데이트:** 2026-04-16 (NP-HARDEN mid-sprint ship + HB-MEASURE Phase 1 완료)
> **목표:** 핸드북 콘텐츠 품질 및 규모 확장 — 138개 전량 재생성 + P0 품질 수정 + SEO 구조화 데이터
> **이전 스프린트:** [[2026-04-10-np4q-sprint-close|NP4-Q]] (클로즈 2026-04-10)
> **설계 참조:** [[2026-03-31-handbook-quality-audit]], [[2026-04-09-handbook-section-redesign]], [[2026-04-16-handbook-quality-measurement-plan]]

---

## 스프린트 완료 게이트

### 핵심 목표 (전부 통과해야 HB-QM 종료)

- [ ] **HB-MIGRATE-138** — 138개 published 용어 v4 7섹션 구조 + redesign 필드로 전량 regenerate
- [ ] **HQ-01** — Hallucination 즉시 수정 (stereo matching 정의, ecosystem integration adv)
- [ ] **HQ-02** — 비기술 용어 archived 처리 (actionable intelligence, AI-driven efficiencies, warping operation 등)
- [ ] **HQ-11** — SEO 구조화 데이터 (DefinedTerm + FAQPage + BreadcrumbList JSON-LD)
- [ ] **최종 검증** — `ruff check .` + `pytest tests/ -v` 통과

### 선택 목표 (여유 있으면)

- [ ] HQ-03 — 구세대 핵심 용어 재생성 (HB-MEASURE 베이스라인 결과 기반으로 재우선순위화)
- [ ] HQ-05 — quality_scores 저장 버그 수정
- [ ] HQ-12 — 콘텐츠 톤 재설계 (위키 → 기술 블로그)
- [ ] HQ-13 — term type 재설계 + facet 시스템
- [ ] GPT5-01~05 — gpt-5 단계별 마이그레이션 완료

---

## Current Doing (active work only)

> **운영 규칙:** Current Doing은 **active work만** 추적. done은 자동으로 제거.
>
> **2차 상태 (자동 판정):**
> - `⚠️ stale` — 마지막 매칭 commit 7일+ 경과
> - `⚠️ ghost` — 시작 후 14일 + 매칭 commit 0건 (drop or restart 결정 필요)

| Task ID | 제목 | 상태 | 시작 | 예상 완료 |
|---|---|---|---|---|
| HB-MEASURE-02 | Measurement CLI + baseline report (`measure_handbook_quality.py`) | doing | 2026-04-16 | 2026-04-17 |
| HB-MIGRATE-138 | 138개 published 용어 v4 구조로 전량 regenerate (병렬 ~2시간, ~$15) | todo | — | — |
| NP-OBSERVE-* | 하드닝 후 4개 long-tail metric 관찰 (~2026-04-30) | doing | 2026-04-16 | 2026-04-30 |
| NP-QUALITY-01 | Enrich 단계 source quality gate — `enrich_sources` / `_lookup_official_sources`의 Exa 결과에 `_classify_source_meta` 기반 필터 적용 (spam drop + analysis/low drop + exa_enrich의 github.com drop). Apr 19 draft 13개 문제 URL 전부 enrich 주입분이었고, collect 단계 필터가 enrich에 복제 안 된 DRY 위반. (원래 scope: Tavily 쿼리 정제 — 효과 제한적이라 drop) | todo | — | — |
| NP-QUALITY-02 | Classify 프롬프트 quality gate — 무명 1인 GitHub repo 제외 규칙, source authority 기준 명시. Apr 19 draft에 `poseljacob/agentic-video-editor`, 3개의 `*/superpowers` repo 통과 | todo | — | — |
| NP-QUALITY-03 | URL 유효성 사후 검증 — 생성된 source_cards URL의 HTTPS 여부, 404/redirect 체크. Apr 19 draft의 `http://openai.com/index/introducing-gpt-5-4/` (http 스킴, 정식 여부 의심) 같은 케이스 방지 | todo | — | — |
| WEBHOOK-USER-01 | 유저 Webhook 구독 셀프서비스 | todo | — | — |
| WEEKLY-V2-PROMPT-01 | Weekly 프롬프트에 `weekly_quiz` JSON 출력 추가 (Expert/Learner + KO adapt) — [[plans/2026-04-19-weekly-content-v2]] — commit `00c8d90` | done | 2026-04-19 | 2026-04-19 |
| WEEKLY-V2-PIPE-01 | `run_weekly_pipeline`에서 guide_items에 weekly_quiz_expert/learner 저장 (locale별 EN/KO 분기) — commit `91b9f84` | done | 2026-04-19 | 2026-04-19 |
| WEEKLY-V2-GUARD-01 | 퀴즈 검증 가드 + 옵션 셔플 (문제별 독립) — `_validate_and_shuffle_weekly_quiz`, commit `91b9f84` | done | 2026-04-19 | 2026-04-19 |
| WEEKLY-V2-FE-01 | 본문 하단 퀴즈 3문제 렌더 + 페르소나 탭 연동 — commit `83b7a87` | done | 2026-04-19 | 2026-04-19 |
| WEEKLY-V2-TEST-01 | 백필 1회 + 셔플 단위 테스트 (1000회 분포 검증) — unit tests `ded105a`, W15 백필 2회 (KO adapter bug fix `1e9fa78`), 12/12 answer∈options | done | 2026-04-19 | 2026-04-19 |
| CONSOL-A | Dead code 제거 — PromptGuideItems 클래스, advisor 4필드 suggestion, openapi 스키마, NewsprintArticleLayout render 블록, vault docs — [[plans/2026-04-19-weekly-consolidation]] — commits `2a6a5ca` `02c9148` `bd1a8b7` `bb043f0` `1d8ebba` `e848085` | done | 2026-04-19 | 2026-04-19 |
| CONSOL-B | Admin post_type 드롭다운 'weekly' 옵션 (corruption 방지) — commit `1e47ce3` | done | 2026-04-19 | 2026-04-19 |
| CONSOL-C | Weekly excerpt + focus_items 자동 생성 (daily 패턴 일치 + TOP 5-7로 축소) — prompt/pipeline/helper + 20 tests — commits `ea1dcf6` `358ff8a` `e052c45` `d8d658f` `d11c6ef` `95f9183` | done | 2026-04-19 | 2026-04-19 |
| CONSOL-D | W13/W14/W15 백필 실행 — 3 weeks × 2 locale = 6 rows all OK. excerpt/focus_items/weekly_quiz_* 전부 채움. quality 86-90. | done | 2026-04-19 | 2026-04-19 |
| CONSOL-E | JSONB dead key 정리 — **no-op**. Preflight scan 결과 194 rows 중 dead key 보유 row 0개 (pipeline이 처음부터 해당 키를 DB에 쓰지 않았음). | done | 2026-04-19 | 2026-04-19 |
| README-01 | 프로젝트 README 작성 | ⚠️ ghost (시작 20일+ 전, 매칭 commit 0건 — drop or restart 결정 필요) | 2026-03-26 | — |
| UA-02~05 | User Analytics 차트 추가 | ⚠️ ghost (시작 20일+ 전, 매칭 commit 0건) | 2026-03-27 | — |

---

## 🏆 스프린트 중 완료 (mid-sprint ship)

### News Pipeline Hardening (NP-HARDEN) — 2026-04-15 ~ 2026-04-16

> **설계:** [[2026-04-15-news-pipeline-hardening-design]] + Phase 1/2/3 plans + [[2026-04-15-news-pipeline-failure-measurement]]
> **회고:** [[2026-04-17-news-pipeline-hardening-retro]]
> **commits:** 34개 (2일)

**완료:**
- [x] **NP-HARDEN-01** (Phase 1 Engineering) — `pipeline.py` 3794→2149줄 (-43%), 4-file split, shim re-export로 20+ import 지점 무중단
- [x] **NP-HARDEN-02** (Phase 2 Reliability) — URL 검증 (3번 revision, `enriched_map` allowlist까지 포함), SEO-spam 도메인 blocklist (47% → 0%), few-shot 예시 Top 2 failure mode (`frontload+overclaim/clarity`, `ko+locale`)
- [x] **NP-HARDEN-03** (Phase 3 Token Diet) — QUALITY_CHECK 공유 블록 단축 `replace_all` 3블록 → **-1956 tokens** (목표 -1250의 156%)
- [x] **NP-DIET-01** (API Diet) — 유료 쿼리 24→11, Brave 전량 제거, Exa 12→5, Tavily 중복 2개 제거. 46% API 비용 절감
- [x] **NP-AUDIT-01** (Post-Phase-3 cleanup) — dead GUIDE 제거 + JSON footer 정리 + citation guard

**드롭된 범위 (재검토 조건 문서화):**
- PydanticAI 마이그레이션 — JSON 파싱 실패 이슈화 시 재검토
- 프롬프트 캐싱 — cron 빈도 시간당 1회↑시 재검토
- Silent failure 로깅 강화 — 빈 배열 발행 시 재검토
- 7-파일 분리 — 팀/오픈소스화 시 재검토

### Handbook Quality Measurement Phase 1 (HB-MEASURE-01) — 2026-04-16

> **설계:** [[2026-04-16-handbook-quality-measurement-plan]]
> **패턴:** NP-HARDEN의 measurement-first 접근을 HB에 적용 (30-50% scope 축소 효과 관찰됨)

- [x] **HB-MEASURE-01a** — Config (`handbook_quality_config.py`) — stale/current model list, 8-type architecture/paper requirements, STALE_AGE_DAYS=90, 다국어 regex patterns (`0d9856e`)
- [x] **HB-MEASURE-01b** — `check_stale_model_comparison` + 테스트 (`746b912`)
- [x] **HB-MEASURE-01c** — `check_missing_architecture_detail` + 테스트 (`9869c42`)
- [x] **HB-MEASURE-01d** — `check_missing_paper_reference` + 테스트 (`02c0a6d`)
- [x] **HB-MEASURE-01e** — `check_dated_claim` + 테스트 (`b2accc6`, 한국어 `년` 정규식 포함)
- [x] **HB-MEASURE-01f** — `check_stale_age` + 테스트 — check layer 완료 (`117a747`)
- [x] regex 정교화 — 한국어 `년` 접미사 + architecture keyword 범위 축소 (`ad98092`)

### 핸드북 UX Phase 1 (HB-UX-01~04, 07) — 이전 기간 완료

| Task | Commit | 효과 |
|------|--------|------|
| HB-UX-01 | `a744824` | Advanced §3 code block collapsed by default |
| HB-UX-02 | `7571d36` + `0f7b707` | §5 Production pitfalls callout |
| HB-UX-03 | `7571d36` | §6 blockquote CSS |
| HB-UX-04 | `b64e789` | §6 Industry dialogue marker |
| HB-UX-07 | `42b7ee7` | Math/currency `$` classifier |

> **상세 회고:** [[2026-04-10-handbook-section-redesign-shipped]]

---

## HB-QM 남은 태스크

### BLOCKING — 게이트 통과 필수

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| HB-MIGRATE-138 | todo | 138개 published 용어 v4 구조로 전량 regenerate (병렬 ~2시간, ~$15) | P0 |
| HQ-01 | todo | Hallucination 즉시 수정 — stereo matching, ecosystem integration adv | P0 |
| HQ-02 | todo | 비기술 용어 archived 처리 | P0 |
| HQ-11 | todo | SEO 구조화 데이터 — DefinedTerm + FAQPage + BreadcrumbList JSON-LD | P0 |

### HIGH PRIORITY — HB-MEASURE Phase 2 (진행 중)

> **설계:** [[2026-04-16-handbook-quality-measurement-plan]] Task 3~5

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| HB-MEASURE-02 | doing | `measure_handbook_quality.py` CLI — production DB 돌려 5-check 집계 출력 | P0 |
| HB-MEASURE-03 | todo | Baseline 저장 — `vault/09-Implementation/plans/measurements/2026-04-16-handbook-baseline.md` | P0 |
| HB-MEASURE-04 | todo | HB-QUALITY-01 scope 재평가 — baseline 데이터 기준으로 prompt/rubric 작업 우선순위 조정 | P1 |

### HIGH PRIORITY — 핸드북 콘텐츠 품질 (HQ)

> **설계 문서:** [[2026-03-31-handbook-quality-audit]]
> **배경:** 2026-03-31 published 138개 중 24개 샘플링 심층 분석에서 도출. **HB-MEASURE baseline 결과 수령 후 우선순위 재평가**.

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| HQ-03 | todo | 구세대 핵심 용어 재생성 — embedding, reinforcement learning 등 | P1 (measure 후) |
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

> **의존성:** HB-MEASURE baseline 완료 후 scope/우선순위 재평가. 추측 대신 데이터 기반 scope 결정.

| Task | 상태 | 목표 |
|------|------|------|
| HB-QUALITY-01 | todo (measure 후) | Advanced 콘텐츠 깊이 강화 — 벤치마크 수치 필수, 아키텍처 상세, 논문 참조 |
| HB-QUALITY-02 | todo (measure 후) | 비교표 정확성 — 현재 경쟁 모델과 비교 (2세대 전 모델 금지) |
| HB-QUALITY-03 | todo | Exa deep context 트리거 검증 — 최신 용어에서 실제로 작동하는지 확인 |
| HB-QUALITY-04 | todo | Basic/Advanced 깊이 차이 명확화 — Basic은 비유+사례, Advanced는 수치+코드+논문 |

### HIGH PRIORITY — 핸드북 UX 남은 것

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| HB-UX-06 | todo | §4 Tradeoffs 2-column grid — heading pair 감지 rehype 플러그인 + 2-col CSS | P2 |

### 뉴스 파이프라인 — 관찰 및 rolling 개선

> **관찰 대상:** NP-HARDEN 후 4개 long-tail metric (~2026-04-30까지). 관찰 결과에 따라 튜닝 결정.

| Task | 상태 | 목표 |
|------|------|------|
| NP-OBSERVE-01 | doing | Option B Exa 복원 후 business candidate pool 회복 추적 |
| NP-OBSERVE-02 | doing | `measure_token_usage.py --days 3` runtime token 감소 확인 |
| NP-OBSERVE-03 | doing | Measurement v2 (2주 후) — frontload+overclaim/ko-locale issue 감소 검증 |
| NP-OBSERVE-04 | doing | Business digest 길이 패턴 Amy 체감 지속 여부 |
| NQ-09 | todo | 랭킹에 "어제 발행 뉴스 제목" 전달 — 같은 이벤트 다른 URL 반복 방지 |
| NQ-15 | todo | Learner 콘텐츠 재설계 — "Expert의 쉬운 버전" 아닌 학습자 관점 재구성 |
| NQ-21 | todo | GitHub Trending 축소 + 급부상 오픈소스 별도 제공 |
| NQ-23 | todo | CP 안정화 — semaphore 동시성 제어 + URL canonicalization |
| NQ-24 | todo | 파이프라인 테스트 전면 재작성 — 현재 계약 기반 mock 테스트 |
| COLLECT-BRAVE-01 | ~~todo~~ cancelled | ~~Brave Search API 수집기 추가~~ — NP-DIET-01에서 Brave 전량 제거하며 의미 상실 |

### GPT-5 마이그레이션 (완료 — 2026-04-19)

> **배경:** OpenAI gpt-4.1 deprecation 대비. Allowed: gpt-5, gpt-5-mini, gpt-5-nano.
> 2026-03-31 한번에 전부 교체 → gpt-5-mini classify 0 picks → revert. 단계별 마이그레이션 전략.
> **결과:** 2026-04-19 기준 전체 마이그레이션 완료. 정확한 종료일/커밋 추후 git log로 보강 필요.

| Task | 상태 | 목표 |
|------|------|------|
| GPT5-01 | done | classify/merge/ranking → gpt-5-mini |
| GPT5-01-FIX | done | merge 프롬프트 gpt-5 호환 — system→user 데이터 이동 |
| GPT5-02 | done | community_summarize → gpt-5-nano |
| GPT5-03 | done | Writer digest → gpt-5 |
| GPT5-04 | done | 전체 파이프라인 backfill 비교 검증 |
| GPT5-05 | done | main 머지 + gpt-4.1 deprecation 대응 완료 |

### User Analytics — Site Analytics 차트 (ghost)

> **설계:** [[2026-03-27-dau-mau-tracking]]
> **상태:** 3주+ 진전 없음 — **drop or restart 결정 필요**

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| UA-01 | done | DAU/MAU 숫자 대시보드 표시 (profiles.last_seen_at) | P0 |
| UA-02 | ⚠️ ghost | DAU/MAU 트렌드 차트 | P0 |
| UA-03 | ⚠️ ghost | 유저 페르소나 분포 파이 차트 | P1 |
| UA-04 | ⚠️ ghost | 학습 진행 상세 (read vs learned 비율) | P1 |
| UA-05 | ⚠️ ghost | 댓글 활동량 일별 트렌드 | P1 |
| UA-06 | todo | 퀴즈 정답률 by 포스트 | P2 |
| UA-07 | todo | 가입→첫 활동 퍼널 | P2 |

### User Webhook Subscriptions (WEBHOOK-USER-01)

> **설계:** [[2026-03-27-user-webhook-subscriptions]]

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
| README-01 | ⚠️ ghost | 프로젝트 README 작성 — 3주+ 방치, **drop 권장** |
| COMMUNITY-01 | todo | Reddit/HN/X 반응 수집 (선택) |
| HANDBOOK-LEVEL-LINK-01 | todo | 페르소나별 핸드북 링크 깊이 |
| QUALITY-HYBRID-01 | todo | 규칙 기반 + LLM 하이브리드 품질체크 |
| PERF-TERMS-CACHE-01 | todo | 뉴스 상세 페이지 용어집 캐시 (200개 초과 시 착수) |

---

## 배경 노트 (HB-QM 관련)

### HB-MEASURE 도입 배경 (2026-04-16)

**패턴 차용:** NP-HARDEN 2일 동안 **원래 계획의 30-50%가 이미 해결됐거나 필요 없는 것**으로 드러남 (measurement-first 효과). 같은 pattern을 핸드북 품질에 적용. "체감상 stale"을 **숫자로** 측정한 뒤 HQ/HB-QUALITY 스코프 재평가.

**비목표:**
- 프롬프트/루브릭 수정 아님 (측정만)
- LLM-judge 레이어 아님 (생성자와 평가자 분리 원칙)
- 콘텐츠 backfill 아님 (측정만)

**5개 check:** stale_model_comparison, missing_architecture_detail, missing_paper_reference, dated_claim, stale_age

### HQ-11 SEO 구조화 데이터

**문제:** 핸드북 용어 페이지에 JSON-LD 없음. "RAG란?" 검색에서 리치 스니펫(정의 박스, FAQ) 노출 불가.

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

## 이전 스프린트 체인

- **HB-QM** (2026-04-10 ~) — **현재** (mid-sprint ship: NP-HARDEN + HB-MEASURE Phase 1)
- [[2026-04-10-np4q-sprint-close|NP4-Q]] (2026-03-15 ~ 2026-04-10) — 게이트 전부 통과, 100+ commits
- Phase 3B-SHARE (2026-03-08 ~ 2026-03-13) — 게이트 전체 통과
- Phase 3A-SEC (2026-03-08 ~ 2026-03-09) — 12개 태스크 완료

## Related

- [[Phase-Flow]] — Phase 진입/완료 기준 + Phase 3-Intelligence G3i Gate
- [[Implementation-Plan]] — 실행 계약 + Hard Gates + 상태 규칙
- [[Checklists-&-DoD]] — 완료 기준 체크리스트
- [[2026-04-17-news-pipeline-hardening-retro]] — NP-HARDEN 회고
- [[2026-04-16-handbook-quality-measurement-plan]] — HB-MEASURE 실행 계획
