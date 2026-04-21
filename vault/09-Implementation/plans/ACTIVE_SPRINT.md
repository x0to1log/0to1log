# ACTIVE SPRINT — Handbook Quality & Content Migration (HB-QM)

> **스프린트 기간:** 2026-04-10 ~ 진행 중
> **마지막 업데이트:** 2026-04-21 (뉴스 파이프라인 **v11** mid-sprint ship: Rubric v2 + Quality Gates + URL Plumbing + rerun_from=quality)
> **목표:** 핸드북 콘텐츠 품질 및 규모 확장 — 138개 전량 재생성 + P0 품질 수정 + SEO 구조화 데이터
> **이전 스프린트:** [[2026-04-10-np4q-sprint-close|NP4-Q]] (클로즈 2026-04-10)
> **설계 참조:** [[2026-03-31-handbook-quality-audit]], [[2026-04-09-handbook-section-redesign]], [[2026-04-16-handbook-quality-measurement-plan]], [[2026-04-21-news-pipeline-v11]]

---

## 스프린트 완료 게이트

### 핵심 목표 (전부 통과해야 HB-QM 종료)

- [ ] **HB-MIGRATE-138** — 138개 published 용어 v4 7섹션 구조 + redesign 필드로 전량 regenerate
- [ ] **HB-SEED-800** — 800개 신규 시드 생성·퍼블리시 (Phase 0~4 전부 통과) — [[2026-04-19-handbook-seed-800]]
- [ ] **HQ-01** — Hallucination 즉시 수정 (stereo matching 정의, ecosystem integration adv)
- [ ] **HQ-02** — 비기술 용어 archived 처리 (actionable intelligence, AI-driven efficiencies, warping operation 등)
- [ ] **HQ-11** — SEO 구조화 데이터 (DefinedTerm + FAQPage + BreadcrumbList JSON-LD)
- [ ] **최종 검증** — `ruff check .` + `pytest tests/ -v` 통과

### 선택 목표 (여유 있으면)

- [ ] HQ-03 — 구세대 핵심 용어 재생성 (HB-MEASURE 베이스라인 결과 기반으로 재우선순위화)
- [x] ~~HQ-05 — quality_scores 저장 버그 수정~~ — 저장 경로 정상 확인됨 (2026-04-20 CoT 테스트). 상세는 HQ 섹션 참조
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
| HB-MIGRATE-138 | 138개 published 용어 v4 구조로 전량 regenerate (병렬 시간·비용 추정치 재검토 필요 — HB-SEED-41 warmup 실측 후 적용) | todo | — | — |
| HB-SEED-01 | 800개 시드 용어 큐레이션 (Amy + Codex, 9 카테고리 JSONL) — [[plans/2026-04-19-handbook-seed-800]] | doing | 2026-04-20 | — |
| HB-SEED-02 | 기존 138 슬러그 export (`export_handbook_slugs.py`, 1회 실행) | todo | — | — |
| NP-OBSERVE-* | 하드닝 후 4개 long-tail metric 관찰 (~2026-04-30) — v11 rubric 엄격도 반영하여 threshold 재평가 병행 | doing | 2026-04-16 | 2026-04-30 |
| NQ-30 | Auto-publish threshold 재조정 — v11 rubric v2 적용 후 기존 85 기준은 너무 엄격. 1주 관찰 후 80 검토 | todo | 2026-04-21 | 2026-04-28 |
| NQ-31 | rerun_from=quality post-deploy E2E — Apr 22 fresh run에서 `smoke_cp_citations.py 2026-04-22` 실행하여 `with hn_url > 0`, `raw == 0` 확인 | todo | — | 2026-04-22 |
| NQ-32 | Weekly quality score 실측 — v11 rubric 적용 후 평균 점수대 파악 (3 weeks backlog 기준) | todo | — | — |
| NQ-33 | CommunityInsight HN+Reddit 동시 URL 저장 시 linkify 매칭 정합성 검증 — body block label prefix(`Hacker News` / `r/*`)로 자동 분리되는지 실데이터로 확인 | todo | — | — |
| NQ-34 | Rubric v2 evidence 필드를 admin UI에 노출 — quality_score sub-score drill-down UX | todo | — | — |
| NQ-35 | Few-shot 데이터 축적 후 rubric 재교정 — 4주 데이터 확보 시 | todo (4주 후) | — | 2026-05-21 |
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

### News Pipeline v11 — Rubric v2 + Quality Gates + URL Plumbing — 2026-04-18 ~ 2026-04-21

> **Journal:** [[2026-04-21-news-pipeline-v11]]
> **Plans:** [[2026-04-20-rerun-from-quality-plan]], [[2026-04-21-cp-thread-url-plumbing]]
> **commits:** 60+ (4일) — 결정 A-F 6개 구조적 변경
> **도화선:** Apr 19 draft 사고 (KO 영어 블록쿼트 + LLM judge 96점 — `locale_integrity`가 severity marker에 묻힘)

**완료:**

**결정 A — Rubric v2 (evidence-anchored sub-scores + code aggregation)**
- [x] **NP-QUALITY-06** — Daily news QC 루브릭 재설계 (handbook 패턴 이식): 10 sub-score + 각각 evidence 필수, 코드가 aggregate, `locale_integrity` explicit 승격. `a7b9cd3` + `1a6df5b` + `e93360b` + `e4c317a`
- [x] **WEEKLY-RUBRIC-V2** — Weekly 파이프라인에 동일 rubric 이식 (3-pipeline parity: handbook ↔ news ↔ weekly). `c5ebc35` + `70867bb` + `a7e2121` + `4994884` + `c7d02b2`
- [x] **HANDBOOK-RUBRIC-V2** — Handbook에서 먼저 검증된 원본 (sub-score + evidence + 4-anchor 스케일). `8249e9d`
- [x] **NQ-37** — Frontload QC도 v11 rubric으로 통일 (4×25 single-score → 10 sub-score + evidence). body/frontload/weekly/handbook 4 경로 완전 parity. `a08f382`

**결정 B — Multi-layer quality gates**
- [x] **NP-QUALITY-01** — Enrich stage source quality gate (`_classify_source_meta` mirror, spam/analysis-low/exa_enrich-github 3개 drop). Apr 19 13개 문제 URL 전량 차단. `aa70ee4` + 관대화 `5796df1`
- [x] **NP-QUALITY-02** — Classify 프롬프트 GitHub repo authority rule + CoT + few-shot. `79a90b9` + `019424a`
- [x] **NP-QUALITY-03** — URL liveness HEAD check (3s timeout, Semaphore(20) 병렬, fail-open). `48a5cdd` + brand TLD 사후 수정 `4618e9a`

**결정 C — Thread URL plumbing** (CP 인용 신뢰도)
- [x] Model 확장: `CommunityInsight` optional `hn_url`/`reddit_url`. `9547eb4`
- [x] Collection URL embed: `[Hacker News|url=...]` / `[Reddit r/<sub>|url=...]`. `971c6d3` + `5985c3e`
- [x] Parsing: `_parse_source_meta` optional URL capture. `0fa85dd`
- [x] Summarize wiring: `summarize_community`가 URL을 CommunityInsight로 전달. `4a8ba6e` + annotation fix `275a859`
- [x] Post-processor 재작성: upvote count 매칭 (positional 버그 해결). `fa565b4`
- [x] Smoke script + Apr 21 retrofit: `822cc3d` + HN Algolia 재조회로 과거 데이터 12개 attribution linkify

**결정 D — `rerun_from=quality` (저비용 QC 재평가)**
- [x] STAGE_CASCADE + loader helper + quality-only branch + defensive handling. `a9fd8de` + `286f79a` + `0f4fb72` + `37ec1a3` + `112d790`
- [x] API + Admin UI + E2E validation script: `71a3e85` + `3c80055` + `5ef93d7` + schema fix `74afcc2`
- [x] **비용 효과:** rerun_from=write ~$0.54 → rerun_from=quality ~$0.05 (10x 절감)

**결정 E — Writer prompt hardening**
- [x] Forward-looking verb 금지 (영어) + `focus_items_ko` REQUIRED. `7014058`
- [x] `focus_items_ko` 방어적 fallback (gpt-5-mini 번역 콜, ~$0.001). `cad1d87`
- [x] CP `quotes_ko == quotes` 길이 강제. `aee61a8`

**결정 F — Cross-pipeline parity**
- [x] Handbook scope/naming/grounding gates (code-side + pipeline_logs rejection). `eb1f446` + `99dad16` + `5732eb9` + wire commits
- [x] Weekly excerpt/focus_items/quiz/source metadata daily parity. `ea1dcf6` + `d8d658f` + `95f9183` + `d11c6ef` + `6bd99dd` + `bf24d02` + `38b1ab4`

**비용 영향 요약:**
- Per-run +8% (~$0.50 → ~$0.54, evidence 필드 max_tokens 500→1800)
- rerun_from=quality ~10배 절감
- URL liveness / enrich gate / focus_items_ko fallback 추가 비용 0 또는 조건부

**v10 → v11 마이그레이션 포인트:**
- LLM single score → 10 sub-score + evidence + 코드 aggregation
- 단일 감점 → issue-based penalty + cap 레이어
- URL 구조 검증만 → HEAD liveness gate 추가
- Collect만 quality gate → collect + enrich 양쪽 mirror
- CP attribution 텍스트만 → thread URL linkify (HN + Reddit)
- rerun_from 4-stage → 5-stage (quality 추가)

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
| HQ-05 | investigated | 점수 저장 경로 **정상 동작 확인** (2026-04-20 CoT 테스트, adv=78 basic=92 hybrid manual). 누락 17개 원인: 레거시 16개(초기 수동 생성, advisor 미경유) + NLP 1건 slug 파생 불일치. 레거시는 HB-MIGRATE-138에서 자연 해소. slug 불일치는 HB-SEED-12로 이관 | ~~P1~~ resolved |
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

### HIGH PRIORITY — 핸드북 시드 800 파이프라인 (HB-SEED)

> **설계 문서:** [[2026-04-19-handbook-seed-800]]
> **목표:** 현재 57 published → +800 신규 = ~857개로 SEO·커버리지·최신성 확보
> **접근:** Amy + Codex 큐레이션(E) → 병렬 3개 생성 → 2-tier 품질 게이트 → auto-publish or draft
> **검증 완료 (2026-04-20):** 점수 저장 경로 정상, manual/0-100/hybrid 스케일, slug 파생은 `req.term` 기반(term_id 조인 권장)
> **실측 (CoT 테스트):** 1개 용어당 **~8분 / ~150k 토큰** — 기존 "~$15/138개" 추정은 **실제 $400~800/800개** 수준으로 상향 필요

#### Phase 0 — Curation (진행 중)

| Task | 상태 | 목표 |
|------|------|------|
| HB-SEED-01 | doing | 9개 카테고리 JSONL에 총 800 용어 수집 (Amy + Codex) — target: llm-genai 180, dl 130, products 110, ml-fund 90, infra 90, de 70, cs-fund 50, math 40, safety 40 |
| HB-SEED-02 | todo | `export_handbook_slugs.py` 1회 실행 → `_existing.jsonl` 채움 (중복 체크 레퍼런스) |

#### Phase 1 — Validation

| Task | 상태 | 목표 |
|------|------|------|
| HB-SEED-10 | todo | 9 JSONL 통합 + validator: 스키마(term_type ∈ TERM_TYPES), 정확·**퍼지** 중복 체크 (`_existing.jsonl` + 교차 카테고리 + aliases cross-match), target 대비 count 리포트 → `queue.jsonl` |

#### Phase 2 — Orchestrator

| Task | 상태 | 목표 |
|------|------|------|
| HB-SEED-20 | todo | `_config.yaml` 스키마 + 로더 (concurrency, threshold, retry, publish mode) |
| HB-SEED-21 | todo | State 관리 (`state.jsonl`, resume-safe, 중복 insert 방지) |
| HB-SEED-22 | todo | Parallel runner (asyncio concurrency=3) — `run_handbook_advise()` 호출로 기존 advisor 재활용 |
| HB-SEED-23 | todo | 2-tier 품질 게이트: (1) 객관 5-check 전부 통과 (hard, type-aware), (2) `advanced ≥ 80` 보조 |
| HB-SEED-24 | todo | 분기: auto_publish / draft / retry (2회까지 재시도, 실패 이유 프롬프트 피드백 옵션) |
| HB-SEED-25 | todo | CLI `scripts/run_handbook_seed.py` (`--dry-run`, `--resume`, `--limit`, `--warmup`) |

#### Phase 3 — Admin UX

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| HB-SEED-30 | todo | Admin Draft 리스트에 quality score + 실패 체크 배지 표시 — warmup 전제 조건 | P0 |
| HB-SEED-31 | todo | 편집 페이지에 full 5-check 결과 + "재생성" 버튼 | P1 |

#### Phase 4 — Execution

| Task | 상태 | 목표 |
|------|------|------|
| HB-SEED-40 | todo | Warmup 배치: 첫 30개 전부 draft 강제 → Amy 검수 → 점수와 체감 품질 일치 확인 |
| HB-SEED-41 | todo | Threshold + 비용 calibration — warmup 실측치로 80/75 조정 + 800개 완주 비용 재추정 |
| HB-SEED-42 | todo | Full run (나머지 770) + failures 재시도 스위프 |

#### 부수 태스크

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| HB-SEED-12 | todo | `handbook_quality_scores.term_slug` 파생 로직 정리 — `req.term` 기반 파생 대신 DB의 official slug 사용. 기존 orphan/mismatch 레코드 cleanup (NLP 1건 등) | P2 |
| HB-SEED-50 | todo | 토큰 다이어트 프로파일링 — CoT 150k 토큰 분석, retrieval/prompt 단계별 비용 절감 포인트 탐색 (warmup 결과에 따라 발동) | P2 |

#### 게이트·의존성

- **HB-SEED-40 (Warmup)** blocks by: **HB-SEED-30 (점수 배지 UI)** — 없으면 검수 시 점수 확인 불가
- **HB-SEED-42 (Full run)** blocks by: HB-SEED-40 + HB-SEED-41 — warmup calibration 반영 전 실행 금지
- **HB-SEED-10** blocks by: HB-SEED-01 완료 (800 수집 완료)

### HIGH PRIORITY — 핸드북 UX 남은 것

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| HB-UX-06 | todo | §4 Tradeoffs 2-column grid — heading pair 감지 rehype 플러그인 + 2-col CSS | P2 |

### 뉴스 파이프라인 — 관찰 및 rolling 개선

> **관찰 대상:** NP-HARDEN + v11 후 long-tail metric (~2026-04-30까지). 관찰 결과에 따라 튜닝 결정.

| Task | 상태 | 목표 |
|------|------|------|
| NP-OBSERVE-01 | doing | Option B Exa 복원 후 business candidate pool 회복 추적 |
| NP-OBSERVE-02 | doing | `measure_token_usage.py --days 3` runtime token 감소 확인 |
| NP-OBSERVE-03 | doing | Measurement v2 (2주 후) — frontload+overclaim/ko-locale issue 감소 검증 |
| NP-OBSERVE-04 | doing | Business digest 길이 패턴 Amy 체감 지속 여부 |
| NP-OBSERVE-05 | doing | v11 rubric threshold calibration — 85→80 적절성 판단 (1주 관찰, NQ-30와 연동) |
| NP-OBSERVE-06 | doing | CP linkify coverage — Apr 22+ fresh runs에서 `with hn_url > 0` 꾸준히 나오는지 |
| NQ-09 | todo | 랭킹에 "어제 발행 뉴스 제목" 전달 — 같은 이벤트 다른 URL 반복 방지 |
| NQ-15 | todo | Learner 콘텐츠 재설계 — "Expert의 쉬운 버전" 아닌 학습자 관점 재구성 |
| NQ-21 | todo | GitHub Trending 축소 + 급부상 오픈소스 별도 제공 |
| NQ-23 | ~~todo~~ done | ~~CP 안정화~~ — v11 URL plumbing에서 해결 (thread URL 보존 + upvote 매칭). canonicalization은 HN Algolia가 정규화 URL 반환으로 자연 해결 |
| NQ-24 | todo | 파이프라인 테스트 전면 재작성 — 현재 계약 기반 mock 테스트 (MagicMock 덫 교훈 반영) |
| NQ-36 | todo | CLASSIFY 프롬프트 토큰 축약 (Phase 3에서 drop된 scope, v12 트리거 전 정리) | — | — |
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

- **HB-QM** (2026-04-10 ~) — **현재** (mid-sprint ship: NP-HARDEN + HB-MEASURE Phase 1 + **뉴스 파이프라인 v11**)
- [[2026-04-10-np4q-sprint-close|NP4-Q]] (2026-03-15 ~ 2026-04-10) — 게이트 전부 통과, 100+ commits
- Phase 3B-SHARE (2026-03-08 ~ 2026-03-13) — 게이트 전체 통과
- Phase 3A-SEC (2026-03-08 ~ 2026-03-09) — 12개 태스크 완료

## Related

- [[Phase-Flow]] — Phase 진입/완료 기준 + Phase 3-Intelligence G3i Gate
- [[Implementation-Plan]] — 실행 계약 + Hard Gates + 상태 규칙
- [[Checklists-&-DoD]] — 완료 기준 체크리스트
- [[2026-04-21-news-pipeline-v11]] — **v11 journal** (Rubric v2 + Quality Gates + URL Plumbing + rerun_from=quality)
- [[2026-04-17-news-pipeline-hardening-retro]] — NP-HARDEN 회고
- [[2026-04-16-handbook-quality-measurement-plan]] — HB-MEASURE 실행 계획
- [[2026-04-20-rerun-from-quality-plan]] — rerun=quality 구현 플랜
- [[2026-04-21-cp-thread-url-plumbing]] — CP thread URL plumbing 구현 플랜
