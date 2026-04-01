# ACTIVE SPRINT — News Pipeline v4 Quality Stabilization (NP4-Q)

> **스프린트 기간:** 2026-03-15~진행 중 (NP4-Q phase)
> **마지막 업데이트:** 2026-03-31 (핸드북 품질 감사 HQ-01~08 추가)
> **목표:** AI News Pipeline v4 (2 페르소나 × 2 언어) 품질 안정화 + 프롬프트 감사 + 뉴스레터/대시보드 구축
> **설계 참조:** [[AI-News-Pipeline-Design]], [[plans/2026-03-16-daily-digest-design]], [[plans/2026-03-25-direct-fastapi-ai-calls]], [[plans/2026-03-26-news-quality-check-overhaul]]
> **이전 스프린트:** Phase 3B-SHARE — 2026-03-13 게이트 전체 통과

---

## 스프린트 완료 게이트

### 핵심 완료
- [x] 파이프라인 v4 전환 (2 페르소나: Expert + Learner, Beginner 제거)
- [x] Skeleton-map 기반 라우팅 (Research/Business × Expert/Learner = 4개 skeleton)
- [x] 핸드북 4-call 분리로 KO/EN 누락 해소
- [x] 퀄리티 스코어링 v2 (0~100, Research/Business 기준 분리)
- [x] 프롬프트 감사 P0 이슈 11개 배포 (40+ 이슈 중)
- [x] 프론트엔드 페르소나 탭 2개 (Expert/Learner) 전환
- [x] Weekly Recap 백엔드 구현 완료 (활성화 대기)

### 진행 중
- [ ] 프롬프트 감사 P1 이슈 배포 (PROMPT-AUDIT-01 진행 중)
- [x] 직접 FastAPI AI 호출 (Vercel 60s timeout 회피) — [[plans/2026-03-25-direct-fastapi-ai-calls]]
- [ ] User Analytics — Site Analytics 차트 (DAU/MAU 트렌드, 페르소나, 학습, 댓글)
- [ ] 뉴스 품질 체크 전면 재작성 (Expert/Learner 양쪽 평가) — [[plans/2026-03-26-news-quality-check-overhaul]]
- [ ] README 작성 (프로젝트 소개) — [[plans/2026-03-26-README-design]]

### 최종 검증
- [ ] `ruff check .` + `pytest tests/ -v` 통과
- [ ] 파이프라인 1회 run → 다이제스트 + 핸드북 정상 확인

---

## Current Doing (병렬 진행 중)

| Task ID | 제목 | 상태 | 시작 | 예상 완료 |
|---|---|---|---|---|
| FASTAPI-DIRECT-01 | 직접 FastAPI AI 호출 (Vercel timeout 회피) | done | 2026-03-25 | 2026-03-27 |
| README-01 | 프로젝트 README 작성 | in_progress | 2026-03-26 | 2026-03-27 |
| UA-02~05 | User Analytics — Site Analytics 차트 추가 | in_progress | 2026-03-27 | 2026-03-28 |
| WEBHOOK-USER-01 | 유저 Webhook 구독 셀프서비스 | todo | 2026-03-27 | 2026-03-29 |
| HQ-01~02 | 핸드북 Hallucination 수정 + 비기술 용어 정리 | todo | 2026-03-31 | — |
| GPT5-01 | gpt-5 모델 마이그레이션 — classify/merge/ranking (gpt-5-mini) | in_progress | 2026-04-01 | — |
| GPT5-01-FIX | merge 프롬프트 gpt-5 호환 — system→user 데이터 이동 | in_progress | 2026-04-01 | — |
| GPT5-02 | gpt-5 모델 마이그레이션 — community_summarize (gpt-5-nano) | todo | — | — |
| GPT5-03 | gpt-5 모델 마이그레이션 — Writer digest (gpt-5) | todo | — | — |
| GPT5-04 | gpt-5 전체 파이프라인 backfill 비교 검증 | todo | — | — |
| GPT5-05 | gpt-5 main 머지 + gpt-4.1 deprecation 대응 완료 | todo | — | — |

---

## 완료된 태스크 (v4 기반)

> **NP4-Q Sprint Progress:** 48+/50 tasks (96% complete)
> **주요 마일스톤:**
> - v4 전환 (3→2 페르소나): 2026-03-17
> - Skeleton-map 라우팅: 2026-03-26
> - 27개 커밋, 11개 P0/P1 프롬프트 감사 배포
> - Weekly Recap 백엔드 완성, 프론트엔드 통합 대기

### Pipeline Architecture (v4) — 모두 완료
- [x] `V4-MODEL-01` — v4 Pydantic 모델 (2 persona)
- [x] `V4-CLASSIFY-01` — 분류 에이전트 (research/business, 서브카테고리)
- [x] `V4-COLLECT-01` — 다중 소스 수집 (Tavily + HF + arXiv + GitHub, 3~5건씩)
- [x] `V4-PERSONA-01` — 2 페르소나 독립 생성 (Expert/Learner, EN+KO 동시)
- [x] `V4-SKELETON-01` — Skeleton-map 라우팅 (R/B × Expert/Learner)
- [x] `V4-PIPE-01` — 파이프라인 오케스트레이터 (분류 → 2페르소나 → 품질체크)
- [x] `V4-CRON-01` — Cron 엔드포인트 (매일 자동 실행)
- [x] `V4-E2E-01` — E2E 검증 (전체 파이프라인 1회 실행)
- [x] `V4-DEPLOY-01` — 배포 + cron 자동화
- [x] `V4-BACKFILL-01` — 과거 날짜 백필

### Pipeline Infra — 모두 완료
- [x] `NP2-OBSERVE-01` — 스테이지별 로깅 + 백필 검증 UI
- [x] `PIPE-SPLIT-01` — News Run + Handbook Run 분리
- [x] `BUG-LOGS-01` — pipeline_logs 기록 안 되는 버그
- [x] `DB-MIGRATE-01` — term_full, korean_full 마이그레이션
- [x] `RUNS-TAB-01` — Pipeline Runs News/Handbook 탭 분리
- [x] `PIPE-CTRL-01` — Cancel, Stuck 타임아웃, Include Handbook

### Handbook Quality — 모두 완료
- [x] `HB-SPLIT-01` — 프롬프트 2회 호출 분리
- [x] `HB-MODEL-01` — DB 모델 확장 (term_full, korean_full)
- [x] `HB-COST-01` — 비용/토큰 추적
- [x] `HB-ANALYTICS-01` — Pipeline Analytics Handbook 탭

### v4 Persona 전환 — 모두 완료
- [x] `V4-PERSONAS-01` — 3→2 페르소나 (Beginner 제거, Expert/Learner 독립 생성)
- [x] `V4-FE-TABS-01` — 프론트엔드 2 탭 (Expert/Learner)
- [x] `V4-AUTOFILL-01` — 자동 필드 채우기 (excerpt, tags, focus_items, reading_time)

### 퀄리티 개선 — 완료
- [x] `QUALITY-01` — 다이제스트 퀄리티 스코어링 (Research/Business 기준 분리)
- [x] `QUALITY-02` — LLM 2차 용어 필터링 (gpt-4o-mini)
- [x] `QUALITY-03` — headline_ko 생성 (LLM이 한국어 제목 생성)
- [x] `QUALITY-04` — 핸드북 4-call 분리 (KO Basic / EN Basic / KO Advanced / EN Advanced)
- [x] `QUALITY-05` — 비즈니스 다이제스트 깊이 개선 (2-3단락, CTO 브리핑 톤)
- [x] `QUALITY-06` — 빈 섹션 생략 + 입력 본문 확대 (2000→4000자)

---

## 남은 태스크 (BLOCKING + HIGH PRIORITY)

### BLOCKING — 게이트 통과 필수

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| PROMPT-AUDIT-01 | in_progress | P1/P2 이슈 배포 (40+ 남음) | HIGH |

### 완료된 BLOCKING

| Task | 완료일 | 결과 |
|------|--------|------|
| FASTAPI-DIRECT-01 | 2026-03-27 | AdminAiConfig 컴포넌트 + 4개 에디터 직접 FastAPI 호출 전환, proxy timeout 제거 |
| QUALITY-CHECK-02 | 2026-03-26 | 품질 체크 Expert/Learner 분리 평가, gpt-4.1-mini, 12000자 truncation |

### HIGH PRIORITY — 스프린트 게이트

| Task | 상태 | 목표 | 의존성 |
|------|------|------|--------|
| WEEKLY-FE-01 | todo | Weekly 탭 프론트 통합 | 백엔드 완료 ✅ |
| AUTOPUB-01 | monitoring | Quality ≥80 자동 발행 + 어드민 토글 | 3일 연속 90+ 확인 후 구현 |
| COMMUNITY-01 | todo | Reddit/HN/X 반응 수집 (선택) | 선택사항 |

### HIGH PRIORITY — 핸드북 콘텐츠 품질 (HQ)

> **설계 문서:** [[plans/2026-03-31-handbook-quality-audit]]
> **배경:** 3/31 published 138개 중 24개 샘플링 심층 분석에서 도출. 3/25 전후 품질 격차 심각.

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| HQ-01 | todo | Hallucination 즉시 수정 — stereo matching 정의, ecosystem integration adv | P0 |
| HQ-02 | todo | 비기술 용어 archived 처리 — actionable intelligence, AI-driven efficiencies, warping operation 등 | P0 |
| HQ-03 | todo | 구세대 핵심 용어 재생성 — embedding, reinforcement learning 등 현재 파이프라인으로 regenerate | P1 |
| HQ-04 | done | 용어 적합성 필터 추가 — 프롬프트 5-point self-check + 코드 blocklist/suffix 필터 | P1 |
| HQ-05 | todo | quality_scores 저장 버그 수정 — 최근 용어에 점수 미기록 원인 파악 | P1 |
| HQ-06 | todo | 콘텐츠 최소 기준 코드화 — basic ≥2500자, adv ≥7000자, 비교표/수식 체크 | P2 |
| HQ-07 | todo | 레퍼런스 다양성 제어 — 같은 batch 동일 URL 인용 비율 제한 | P2 |
| HQ-08 | todo | 중복 용어 병합 — variation operator → evolutionary search 등 | P2 |
| HQ-09 | done | 카테고리 재설계 — 11개→9개, 프롬프트+파이프라인+프론트엔드+DB 212개 마이그레이션 완료 | P1 |
| HQ-10 | done | 카테고리별 프롬프트 컨텍스트 — 9개 CATEGORY_CONTEXT(5필드) + Basic TYPE_GUIDE 10개 + 3-layer 코드 패턴 | P1 |

#### HQ-09 카테고리 재설계 — 배경 노트

**현재 문제:** ai-ml에 172/212개(81%) 집중, os-core/web3/network 사문, CS 기초 29개 미분류.
**목표:** "CS 기초 → AI 최전선" 학습 경로를 카테고리로 표현.

**새 카테고리 (9개, 다중 태깅 허용):**

| # | ID | 커버 | 예시 |
|---|-----|------|------|
| 1 | cs-fundamentals | 프로그래밍, 자료구조, 네트워크, OS, 웹 | API, SQL, OAuth, DOM, async, B-Tree |
| 2 | math-statistics | ML 뒤의 수학, 확률, 정보이론 | PCA, entropy, gradient, Bayes, ARIMA |
| 3 | ml-fundamentals | 전통 ML, 학습 이론, 평가 | SVM, KNN, overfitting, cross-validation |
| 4 | deep-learning | 신경망 아키텍처, 학습 기법, 비전 | CNN, RNN, Transformer, GAN, diffusion model |
| 5 | llm-genai | LLM, 생성AI, 에이전트, RLHF | RAG, hallucination, fine-tuning, MoE, prompt engineering |
| 6 | data-engineering | 파이프라인, 저장소, 포맷 | ETL, vector DB, Spark, Parquet, Kafka |
| 7 | infra-hardware | GPU, 클라우드, MLOps, 배포 | CUDA, FlashAttention, K8s, quantization, inference cost |
| 8 | safety-ethics | 보안, 정렬, 규제, 공정성 | adversarial attack, AI alignment, data poisoning |
| 9 | products-platforms | 특정 모델, 기업, 프레임워크 | GPT-4o, Anthropic, PyTorch, NVIDIA Blackwell |

**주의:** math-statistics는 뉴스 파이프라인에서 잘 안 채워짐 (수동 추가 필요). products-platforms는 유통기한 짧아 주기적 정리 필요.

**구현 범위:**
- 프롬프트: EXTRACT_TERMS_PROMPT의 allowed domains + category enum 변경
- 파이프라인: VALID_CATEGORIES 상수 변경
- DB: 기존 212개 용어 categories 배열 마이그레이션 스크립트
- 프론트엔드: 핸드북 필터 UI 카테고리 목록 변경
- 경계 용어 다중 태깅: Transformer→[deep-learning, llm-genai], fine-tuning→[ml-fundamentals, llm-genai] 등

#### HQ-10 카테고리별 프롬프트 컨텍스트 — 배경 노트

**현재 문제:** 4개 생성 프롬프트가 모든 카테고리에 동일한 DOMAIN CONTEXT ("AI/IT meaning에 집중")를 사용. SQL(cs-fundamentals)도, PCA(math-statistics)도, GPT-4o(products-platforms)도 같은 지시를 받아 도메인 맥락이 부자연스러움.

**리서치 결론:** 프로덕션 시스템들은 "Modular Prompt Composability" 패턴 사용 (Langfuse, LLMpedia, Slide2Text). 36개 전체 프롬프트(Approach B)는 보편적으로 reject. term type과 category는 독립 축으로 유지 (구조 vs 도메인).

**아키텍처:**
```
FINAL_PROMPT = BASE_PROMPT (4개, 공통 구조)
             + CATEGORY_CONTEXT[category] (9개, 도메인 프레이밍)
             + TYPE_DEPTH_GUIDE[term_type] (10개, 섹션 구조 — Advanced only → Basic에도 확장)
             + GROUNDING_RULES (1개, 팩트 체크)
```

**CATEGORY_CONTEXT 구조 (카테고리당 4개 필드):**
- vocabulary: 도메인에서 자연스러운 용어
- quality_signals: 좋은 콘텐츠의 특징
- anti_patterns: 피해야 할 패턴
- reference_style: 레퍼런스 인용 방식

**구현 범위:**
- `prompts_handbook_types.py`: CATEGORY_CONTEXT 9개 + `build_category_block()` 함수 + Basic TYPE_GUIDES 10개
- `advisor.py`: `_run_generate_term`에서 카테고리 블록 주입 (Basic + Advanced 모든 call)
- 비용 영향: $0 (프롬프트 토큰만 ~300 추가)

### 품질 점수 모니터링 (AUTOPUB-01 전제조건)

| 날짜 | Business | Research | 비고 |
|------|----------|----------|------|
| 3/26 | 99 (E:100/L:98) | 95 (E:95/L:95) | 최신 프롬프트 v6 + 12000자 truncation |
| 3/25 | 88 (E:88/L:88) | 69 (E:68/L:70) | 4000자 truncation 오탐 포함 |
| 3/24 | 85 | 65 | o4-mini (변별력 부족) |
| 3/24 (재생성) | 95 | 94 | 최종 파이프라인 |

목표: 3일 연속 Business ≥ 85, Research ≥ 80 → AUTOPUB-01 구현 착수.
현재: 3/24(95/94), 3/26(99/95) = 2일 달성. **3/27 결과 확인 후 구현 예정.**

#### AUTOPUB-01 구현 범위
- quality_score ≥ 설정값 → draft → published 자동 전환
- 어드민 대시보드에 **자동 발행 토글** (Weekly Recap 토글과 동일 패턴)
- 어드민에서 **기준 점수 설정** 가능 (기본값 80)
- admin_settings에 `auto_publish_enabled` + `auto_publish_threshold` 저장

목표: 3일 연속 Business ≥ 85, Research ≥ 80 → AUTOPUB-01 구현 착수.

### HIGH PRIORITY — 뉴스 v7 품질 체크리스트

> 3/29 콘텐츠 심층 평가에서 도출. 점수/10 기준.

| Task | 기준 | 현재 | 목표 | 상태 |
|------|------|------|------|------|
| NQ-02 | 정보 밀도 — baseline 맥락 (priority 2 수정) | 7.5 | 8.5+ | done |
| NQ-03+05+07 | KO skeleton 4개 + persona 톤 + 음차 + Action Items | 7~7.5 | 8+ | done |
| NQ-05b | Expert 약어 풀네임 규칙 | 7.5 | 8.5+ | done |
| NQ-06 | Community Pulse — 분위기 요약 중심 전환 (수집 + Rule 15 + skeleton) | 6.5 | 8+ | done |
| NQ-06b | Learner 숫자 생략 금지 + 최소 3p 통일 | — | 8+ | done |
| NQ-07 | Action Items — "팔로우/주시" 금지, 구체적 action만 | 7.5 | 8.5+ | done |
| NQ-08 | 분류/랭킹 분리 — gpt-4.1-mini 랭킹 + [LEAD]/[SUPPORTING] 태그 | 7.5 | 9+ | done |
| NQ-09 | 랭킹에 "어제 발행 뉴스 제목" 전달 — 같은 이벤트 다른 URL 반복 방지 | — | — | todo |
| NQ-10 | Business Expert citation 중복 — 같은 URL에 매번 새 번호 부여 (18개 → 5개) | — | — | done |
| NQ-11 | CP MANDATORY 4곳 통일 (Business Expert CP 누락 반복) | — | — | done |
| NQ-12 | Citation 포맷 변경 — 뉴스 아이템은 소제목 옆 1회, 분석 섹션만 문단별 | — | — | done |
| NQ-13 | 같은 이벤트 다중 소스 수집 (Multi-Source Enrichment) — rank 후 Exa find_similar 2차 수집 + Writer 다중 소스 입력 | — | — | done |
| NQ-14 | Citation 번호 전체 기사 순차 (섹션별 리셋 방지) — per-paragraph citation + 후처리 heading 집계 | — | — | done |
| NQ-15 | Learner 콘텐츠 재설계 — "Expert의 쉬운 버전"이 아닌 학습자 관점 재구성 | — | — | todo |
| NQ-16 | Classify/Merge 분리 — classify(개별 7-8개) → merge(전체 50개에서 같은 이벤트 매칭) → 외부 enrich(보충) | — | — | done |
| NQ-17 | 파이프라인 Health Check — classify/merge/enrich 과정의 코드 기반 이상 탐지 + 로그 경고 | — | — | done |
| NQ-18 | CP 스팸 필터 — 코멘트 최소 품질 체크(upvote, 패턴) + 소스 도메인 필터(HN/Reddit만) | — | — | done |
| NQ-22 | CP 전면 재설계 — Summarizer + Entity Search + Brave Discussions | — | — | done (Phase 1-2), 검증 대기 |
| NQ-23 | CP 안정화 — semaphore 동시성 제어 + URL canonicalization | — | — | todo |
| NQ-24 | 파이프라인 테스트 전면 재작성 — 현재 계약 기반 mock 테스트 | — | — | todo |
| NQ-19 | 파이프라인 체크포인트 — 각 단계 결과 DB 저장 + 임의 지점 재실행 + 어드민 UI | — | — | done |
| NQ-20 | Writer 다중 소스 활용 개선 — 여러 소스의 다른 관점/정보를 반영해서 작성하도록 Guide 수정 | — | — | done |
| NQ-21 | GitHub Trending 축소 + 급부상 오픈소스 별도 제공 | — | — | todo |

#### NQ-13 설계 참조
- **설계 문서:** [[plans/2026-03-30-multi-source-enrichment]]
- **결정 확정 (2026-03-30):**
  - 글자 제한: 제한 없음 (전문 전달)
  - 2차 수집: Exa `find_similar(url)` + 48시간 날짜 필터
  - 소스 상한: 최대 4개 (원본 + 3)
  - 이벤트 판별: 날짜 필터만 (LLM 판별 불필요)
  - 대상: 전체 (LEAD + SUPPORTING)
- **구현 태스크:** 6개 (enrich 함수 → Writer 포맷 → 파이프라인 삽입 → 프롬프트 → 어드민 → 검증)
- **비용 영향:** +$0.03-0.04/run (현재 $0.25 → $0.28-0.29)

#### NQ-16 설계 참조
- **설계 문서:** [[plans/2026-03-30-merge-classify-design]]

#### NQ-16 배경 노트
**v1 실패 (classify+merge 동시):** 3/16 Research papers 10개 한 그룹, 3/30 papers 5개 한 그룹. subcategory 기준 과묶기 반복. 예시 추가해도 해결 안 됨.

**v2 설계 (classify/merge 분리):**
- classify: 개별 아이템 7-8개 선별 (v8 방식 복원, 검증된 로직)
- merge: 선별 기준으로 전체 50개에서 같은 이벤트 매칭 → ClassifiedGroup 생성
- 외부 enrich: 소스 1개뿐인 그룹만 Exa 보충
- 추가 비용: ~$0.002 (merge LLM 1회)
- **핵심**: classify가 "뭐가 중요한가"만 판단, merge가 "같은 이벤트인가"만 판단 → 각자 단순한 작업

#### NQ-15 배경 노트
3/30 3월 21일 backfill 평가에서 도출. 현재 Learner는 Expert 내용을 쉬운 단어로 바꾼 수준이지 학습자 관점으로 재구성한 것이 아님.
- Transformers v5.4.0 breaking changes 같은 개발자 전용 내용이 Learner에도 그대로 포함
- "나한테 무슨 의미?" 가 약함 — 아키텍처 설명 대신 실용적 시나리오가 필요
- Expert/Learner가 동일 뉴스를 동일 비중으로 다룸 — 학습자에게 더 의미 있는 뉴스에 비중 조절 필요
- 방향: Learner Guide를 "Expert를 쉽게" → "학습자가 알고 싶은 관점으로 재구성"으로 전환

#### NQ-17 배경 노트
현재 quality check는 Writer 출력물만 평가. 과정(classify/merge/enrich)에서 발생하는 문제는 결과물에서 안 잡히는 경우가 있음:
- 카테고리 페이지가 classify 통과 → Writer가 어떻게든 글을 씀 (코드 필터 추가로 일부 해결됨)
- merge가 관련 없는 기사 묶음 → 소제목이 이상하지만 LLM quality check에서 감점 안 될 수 있음
- enrich가 소스 0개 반환 → Writer가 원본만 인용, 다중 소스 효과 없음
- community 0건 → CP 없어도 정당화됨
- **방향:** LLM 호출 아닌 코드 기반 규칙 체크 (비용 0). 파이프라인 로그에 warning 기록 + 어드민 표시

#### NQ-22 배경 노트 — CP 전면 재설계

**구현 완료 (2026-03-31, 6 커밋):**

1. **Community Summarizer 단계 추가** (`7745367`)
   - community → community_summarize → rank 흐름
   - gpt-4.1-mini 배치 1회, {sentiment, quotes 0-2, key_point} 추출
   - Writer는 정제된 데이터만 받아서 포맷+번역 (선별 책임 제거)

2. **Entity-First Search** (`062026a`)
   - 타이틀에서 고유명사/버전 패턴 추출 → 짧은 쿼리로 HN 검색
   - 선택적 부스트 (버전 +40, 긴 고유명사 +20) + foreign entity 패널티 (-8/entity, max -30)
   - target_date 기준 7일 시간 필터

3. **Brave Discussions 교체** (`87db4d7`, `ccb9ba1`)
   - Reddit 키워드 검색 → Brave Web Search discussions로 교체
   - Brave가 Reddit URL 발견 → permalink 추출 → 코멘트 1회 fetch
   - ALLOWED_SUBREDDITS 확장 (ai_agents, aiwars, fintech, legaltech, europe)

4. **코드리뷰 수정 6건** (`6d6a1f7`, `a67c538`)
   - 즉시: Brave freshness=pw, HN html.unescape(), entity 최소 2개
   - 곧: Brave 로그 warning + 카운트, Summarizer 다중 thread 합치기, insert 실패 구분

**미구현 → NQ-23, NQ-24로 분리:**
- semaphore 동시성 제어 (현재 URL ~10개라 급하지 않음)
- URL canonicalization (실제 발생 빈도 데이터 필요)
- 테스트 전면 재작성 (코드 안정화 후)

#### NQ-23 배경 노트 — CP 안정화
코드리뷰에서 도출된 아키텍처 개선:
- **semaphore 동시성 제어**: gather()로 URL 10+개 동시 호출 + 내부 sleep → 상위에서 asyncio.Semaphore(3-5)로 제한
- **URL canonicalization**: tracking param, mobile URL, redirect URL 정규화 → URL 검색 false negative 감소
- 파이프라인 안정화 + 데이터 확보 후 진행

#### NQ-24 배경 노트 — 테스트 전면 재작성
현재 test_news_collection.py, test_pipeline.py, test_ranking.py가 모두 예전 계약 기반:
- community reactions는 Tavily 방식 가정
- ClassificationResult가 old 구조 기대
- pipeline 모델 구조 변경 때문에 수집 단계에서 깨짐
- 방향: httpx.AsyncClient mock 기반으로 HN URL hit, Reddit URL hit, Brave fallback, freshness 적용 각각 테스트

#### NQ-18 배경 노트
3/31 자동 파이프라인에서 Research CP에 봇 생성 스팸 텍스트가 실제 코멘트로 인용됨.
- "Microservices architecture locally automates DOM elements" — 무의미한 기술 용어 나열
- 소스: "jplopsoft.idv.tw IT TOP Blog" — 신뢰 불가 도메인
- **구현 방향:**
  - 코멘트 최소 품질: upvote 3 미만 스킵, 기술 용어 무의미 나열 패턴 탐지
  - 소스 도메인 필터: HN Algolia + Reddit JSON만 사용, 기타 소스 무시
  - 비용 0 (코드 필터)

#### NQ-19 배경 노트 — 파이프라인 체크포인트 시스템
현재 파이프라인은 모든 단계가 메모리에서만 흘러가서, 한 단계라도 문제 시 전체를 처음부터 다시 돌려야 함.
각 단계 결과를 DB에 저장하면 임의 지점부터 재실행 가능.

**5개 재시작 지점:**

| 문제 상황 | 재시작 지점 | 이전 단계 재활용 |
|----------|-----------|----------------|
| Writer 출력 불만족 / Research·Business 따로 재생성 | write | collect~enrich 전부 |
| CP 스팸/누락 | community | collect~merge |
| merge 과묶기 | merge | collect~classify |
| classify 잘못 선별 | classify | collect |
| 수집 자체 부족 | collect | 없음 (처음부터) |

**구현 방향:**
- 각 단계 결과를 `pipeline_checkpoints` 테이블(또는 pipeline_logs.debug_meta 확장)에 저장
  - collect: candidates 리스트 (URL + title + raw_content)
  - classify: research_picks + business_picks
  - merge: ClassifiedGroup 리스트
  - community: community_map
  - rank: ranked groups (LEAD/SUPPORTING)
  - enrich: enriched_map
- 어드민 UI: pipeline-runs 상세에서 "이 단계부터 재실행" 버튼
- 백엔드 API: `POST /api/admin/pipeline/rerun?run_id=xxx&from_stage=write&category=research`
- raw_content가 가장 큰 데이터 — 저장 전략 결정 필요 (전문 vs 요약 vs URL만)

#### NQ-20 배경 노트
3/31 퀄리티 리뷰에서 도출. enrich가 소스 3-4개를 전달하지만 Writer가 1-2개만 인용하는 경향.
- Anthropic $45B 동맹: 3개 소스 전달 → [1]만 반복 (aibusinessreview 하나에 의존)
- 원인: LLM이 가장 풍부한 소스 하나에 의존, 나머지 무시
- **방향:** "전부 인용해라" (억지) 대신 "여러 소스의 다른 관점/정보를 반영해서 작성" (자연스러운 유도)
- 예: "딜 구조 [1] + 경쟁 영향 [2] + Google 대응 [3]" — 다른 소스에서 다른 정보를 가져오기
- NQ-15(Learner 재설계)와 함께 Writer Guide 전체를 손볼 때 반영
- **관찰 (3/29):** NQ-20 다중 소스 활용이 잘 작동하지만 부작용 발견 — Expert/Learner에서 같은 딜의 숫자가 다름 (500억 vs 670억). 소스마다 집계 방식이 달라서 LLM이 다른 숫자를 골랐음. 발생 빈도 낮고, 완전히 틀린 정보는 아니므로 관찰 유지. 빈도 높아지면 CHECKLIST 또는 소스 입력 단계 대응 검토

#### NQ-21 배경 노트
GitHub Trending 수집기가 대형 프로젝트(tensorflow, langchain)만 반복 수집하는 문제.
GitHub API로는 "star 증가율"을 직접 구할 수 없어 진짜 trending을 잡기 어려움.

**방향 2가지:**
1. **Daily — GitHub 레포 별도 제공**: 뉴스 본문과 별도로 "오늘 언급된 GitHub 레포" 링크 모음 제공 (뉴스/커뮤니티에서 추출한 GitHub URL)
2. **Weekly — 급부상 오픈소스 섹션**: weekly recap에서 주간 단위로 HN/Reddit/뉴스에서 화제된 오픈소스 프로젝트를 모아서 보여주기

**핵심 인사이트**: GitHub API 직접 쿼리보다, 이미 수집된 HN/Reddit/뉴스에서 GitHub URL을 추출하는 게 더 정확한 "trending" 시그널. HN 200 upvote "Show HN: ML framework"가 stars:>100 쿼리보다 의미 있음.

**GitHub Trending 수집기**: 축소 또는 신규 프로젝트(created:>7일, stars:>50)로 전환. 기존 대형 프로젝트 반복 방지.

#### GPT-5 모델 마이그레이션 배경 노트
OpenAI gpt-4.1 deprecation 대비. Allowed models: gpt-5, gpt-5-mini, gpt-5-nano, text-embedding-3-small.

**이전 시도 (2026-03-31 실패):** 한번에 전부 교체 → gpt-5-mini classify가 0 picks 반환 → 즉시 revert.

**이번 전략: 단계별 마이그레이션 (gpt5-migration 브랜치)**
1. GPT5-01: classify/merge/ranking → gpt-5-mini (가벼운 LLM 호출부터)
2. GPT5-02: community_summarize → gpt-5-nano (가장 작은 모델)
3. GPT5-03: Writer digest → gpt-5 (가장 비싸고 출력 포맷 영향 큼 → 마지막)
4. GPT5-04: 전체 파이프라인 backfill → gpt-4.1 결과와 나란히 비교
5. GPT5-05: 품질 확인 후 main 머지

**핵심 원칙:**
- 각 단계마다 backfill 1회 돌려서 gpt-4.1 결과와 비교
- checkpoint 데이터로 같은 입력 → 다른 모델 출력 비교 가능
- 문제 발생 시 해당 단계만 revert, 나머지는 유지

| NQ-09 | max_tokens 16K→32K (Expert 짧음 근본 원인 해결) | — | — | done |

### HIGH PRIORITY — 핸드북 퀄리티

| Task | 상태 | 목표 |
|------|------|------|
| HB-QUALITY-01 | todo | Advanced 콘텐츠 깊이 강화 — 벤치마크 수치 필수, 아키텍처 상세, 논문 참조 |
| HB-QUALITY-02 | todo | 비교표 정확성 — "현재 경쟁 모델"과 비교 (2세대 전 모델 금지) |
| HB-QUALITY-03 | todo | Exa deep context 트리거 검증 — 최신 용어에서 실제로 작동하는지 확인 |
| HB-QUALITY-04 | todo | Basic/Advanced 깊이 차이 명확화 — Basic은 비유+사례, Advanced는 수치+코드+논문 |

#### 발견된 문제 (3/27 gemini-31 기준)
- 비교표: GPT-4o/Gemini 1.0 비교 (현재 경쟁 모델은 GPT-5.2/Claude Opus 4.6)
- 벤치마크 수치 없음 — "빠르다/정확하다"만 표기
- Advanced가 Basic과 깊이 차이 적음 — 아키텍처(MoE, attention) 상세 없음
- 정보 최신성 — "2024 baseline" (현재 2026)

### User Analytics — Site Analytics 강화

> **목표:** 이미 수집 중이지만 안 보여주는 유저 데이터를 Site Analytics에 시각화
> **설계 참조:** [[plans/2026-03-27-dau-mau-tracking]]

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| UA-01 | done | DAU/MAU 숫자 대시보드 표시 (profiles.last_seen_at) | P0 |
| UA-02 | todo | DAU/MAU 트렌드 차트 — Site Analytics에 일별 활성 유저 추이 | P0 |
| UA-03 | todo | 유저 페르소나 분포 — beginner/learner/expert 파이 차트 | P1 |
| UA-04 | todo | 학습 진행 상세 — read vs learned 비율 표시 | P1 |
| UA-05 | todo | 댓글 활동량 — 일별 댓글 수 트렌드 (news_comments + blog_comments) | P1 |
| UA-06 | todo | 퀴즈 정답률 by 포스트 — 어떤 콘텐츠가 이해하기 어려운지 | P2 |
| UA-07 | todo | 가입→첫 활동 퍼널 (signup → read → bookmark → quiz) | P2 |

### User Webhook Subscriptions (WEBHOOK-USER-01)

> **설계:** [[plans/2026-03-27-user-webhook-subscriptions]]

| Task | 상태 | 목표 |
|------|------|------|
| WEBHOOK-USER-01a | todo | DB: `user_webhooks` 테이블 + RLS (유저당 5개 상한) |
| WEBHOOK-USER-01b | todo | API: `/api/user/webhooks` CRUD + test 엔드포인트 |
| WEBHOOK-USER-01c | todo | 발송: `fireWebhooks()` 확장 — user_webhooks 동시 조회 |
| WEBHOOK-USER-01d | todo | 페이지: `/settings/webhooks/` UI (목록 + 추가 폼 + 가이드) |
| WEBHOOK-USER-01e | todo | 진입점: 편지지 모달 + 뉴스 스트립 Webhook 링크 연결 |

### 뉴스 수집 다변화

| Task | 상태 | 목표 | 우선도 |
|------|------|------|--------|
| COLLECT-BRAVE-01 | todo | Brave Search API 수집기 추가 — 무료 티어(2,000건/월), 뉴스 필터, 독립 인덱스 | P1 |

#### COLLECT-BRAVE-01 배경 노트
Tavily 용량이 backfill로 소진되는 문제 대비. Brave Search API는 무료 티어 + 뉴스 전용 freshness 파라미터 지원.
Exa와 병렬 수집기로 추가하면 소스 다양성 확보 + Tavily 의존도 감소.
- API: https://api.search.brave.com/
- 무료: 2,000 쿼리/월, 뉴스 검색 지원
- 우선순위: NQ-16(merge) 완료 후 착수

### OPTIONAL — 다음 Phase

| Task | 상태 | 목표 |
|------|------|------|
| HANDBOOK-LEVEL-LINK-01 | todo | 페르소나별 핸드북 링크 깊이 |
| QUALITY-HYBRID-01 | todo | 규칙 기반 + LLM 하이브리드 품질체크 |
| PERF-TERMS-CACHE-01 | todo | 뉴스 상세 페이지 용어집 캐시 (현재 매 요청 200개 fetch → 서버 메모리 캐시). 용어 200개 초과 시 착수. 1000개+ 시 Aho-Corasick 다중 패턴 매칭 검토 |
| PERF-HTML-SLIM-01 | done | 뉴스 상세 HTML 322KB → 306KB lazy load 축소. dom_complete 2.5초 → 1.9초 (d3fdb79) |
| PERF-AUTH-CDN-01 | done | 로그인 유저도 CDN 캐시 적용 (admin 제외). 북마크/좋아요 hydration + 페르소나 쿠키 스왑 (dd21ded) |

### 44. 프롬프트 감사 수정 `[PROMPT-AUDIT-01]` (진행 중)
- **체크:** [~] (11/52 배포됨)
- **상태:** in_progress (rolling fix)
- **목적:** 전체 프롬프트 감사 결과 52개 이슈 수정 (신뢰도/일관성/토큰 효율)
- **설계 참조:** [[2026-03-18-prompt-audit-fixes]]
- **배포 현황:**
  - P0 (CRITICAL) 2개 배포: citation 매핑 해결, URL hallucination 방지
  - P1 (HIGH) 9개 배포: 섹션 구조 싱크, 토큰 효율, few-shot 개선
  - P2 (MEDIUM) 40개 대기: 일관성, 반복 제거, 코드 기준 명확화
- **대상 파일:** `prompts_advisor.py`, `prompts_news_pipeline.py`, `prompts_handbook_types.py`

---

## 최근 완료 (2026-03-20~26, 27+ commits)

**주요 마일스톤:**
- [x] Per-persona skeleton refactor + Research Learner 접근성 개선 (fc517fa)
- [x] 프롬프트 구조 동등성 규칙 적용 (412ec85)
- [x] 페르소나별 출처 인용 형식 표준화 (3133567)
- [x] Weekly Recap 백엔드 병렬화 완료 (ceb295c)
- [x] 품질 점수 Y축 스케일 수정 (0~100) (63c7e9d)
- [x] 인용 형식 표준화 → Perplexity 스타일 (8af5625)
- [x] Analytics 탭 확장 (퀴즈 성능, 피드백, 트래픽) (80f2560)
- [x] 핸드북 admin override 토글 (e14aa7d)
- [x] KaTeX 수식 렌더링 보안 개선 (24aa89a)
- [x] 핸드북 advanced quality (Tavily + 유형분류 + Self-critique)
- [x] 5개 에디터 Danger Zone 분리 (DELETE 버튼 → 하단 섹션)
- [x] SEO + Admin Analytics 전면 개선
- [x] GA4 Data API 백엔드/프론트 통합

**프롬프트 감사 배포 현황:**
- P0 C2 (Citation-소스 매핑): ✅ 해결
- P0 C1 (URL hallucination): ✅ 배포
- P1 섹션 구조: ✅ 배포
- P1 토큰 효율: ✅ 배포
- P1 few-shot: ✅ 배포
- P2 (40개): 🔄 rolling fix

---

## NP4-Q 스프린트 게이트 (Phase-Flow 기준)

### 게이트 상태 (완료 조건)

| # | 게이트 | 상태 | 기한 | Phase-Flow |
|---|--------|------|------|-----------|
| 1 | News Pipeline v4 core (2 personas, skeleton-map) | ✅ | — | [[Phase-Flow#News Pipeline v4]] |
| 2 | Weekly Recap 백엔드 | ✅ | — | 프론트 통합 대기 |
| 3 | PROMPT-AUDIT 70% 배포 (41/52 이상) | 🔄 | 2026-03-28 | P0/P1 우선 |
| 4 | FastAPI Direct Calls (FASTAPI-DIRECT-01) | 🔄 | 2026-03-27 | Admin timeout 회피 |
| 5 | 품질 체크 Expert/Learner (QUALITY-CHECK-02) | 🔄 | 2026-03-28 | 양쪽 평가 |
| 6 | `ruff check .` + `pytest tests/` 통과 | ⏳ | PROMPT-AUDIT 후 | 최종 검증 |

### Phase 3-Intelligence 진입 기준

**목표 시작:** 2026-03-30

**선행 조건:**
- [x] News Pipeline v4 완료 (2026-03-17) — [[Phase-Flow#파이프라인 진화]]
- 🔄 PROMPT-AUDIT 70% 배포 (~2026-03-28)
- 🔄 FastAPI direct + quality check (~2026-03-28)
- ⏳ ruff + pytest 통과

**진입 후 Wave별 계획:**
```
Wave 1 (2026-03-30~04-10): 개인화 기초
├─ 개인 학습 프로필 (사용자 선호도)
├─ 뉴스 추천 알고리즘
└─ Weekly Recap 프론트엔드 통합

Wave 2 (2026-04-10~04-20): 커뮤니티 기반
├─ COMMUNITY-01: Reddit/HN/X 반응 수집
├─ 사용자 피드백 수집 (퀴즈, 북마크)
└─ 트렌드 분석 & 핫이슈

Wave 3 (2026-04-20~05-01): 자동화
├─ AUTOPUB-01: Quality ≥80 자동 발행
├─ 스마트 발행 스케줄
└─ A/B 테스트 자동화
```

→ 상세: [[Phase-Flow#Phase 3-Intelligence]]

---

## Phase 3-Intelligence 다음 Phases

### Phase 4 — Community (미래)
**커뮤니티 기반 학습** — Semantic Search, 포인트 시스템, Prediction Game
- AI Semantic Search (Cmd+K → pgvector)
- Dynamic OG Image
- Highlight to Share
- 포인트 시스템 UI
- Prediction Game UI

→ 상세: [[Phase-Flow#Phase 4]]

### Phase 5 — Native App (미래)
**PWA → iOS/Android** — 오프라인 지원, 푸시 알림, 원클릭 설치
- PWA 검증 → 네이티브 전환
- Go Gate: 설치율 4%+ (4주 연속) / 유지율 25%+

→ 상세: [[Phase-Flow#Phase 5]]

### 미래 기능 (설계 완료, 구현 대기)
- **AI Products**: 7개 카테고리 (LLM, Image Gen, Video Gen 등) — [[Phase-Flow#AI Products]]
- **Factcheck**: Quick Check + Deep Verify — [[Phase-Flow#Factcheck]]
- **Legal & Compliance**: Privacy, Terms, Cookie Consent (⚠️ 시급)
- **Monetization**: Affiliate → AdSense → Premium 구독

### Phase 3-Intelligence 핵심 태스크

**Wave 1: 개인화 기초 (2026-03-30~04-10)**
```
[x] Weekly Digest 프론트 통합 (WEEKLY-FE-01)
[x] PROMPT-AUDIT P1/P2 배포 (rolling)
[ ] 개인 학습 프로필 (사용자 선호도 저장)
[ ] 뉴스 추천 알고리즘 (관심 기반)
```

**Wave 2: 커뮤니티 기반 (2026-04-10~04-20)**
```
[ ] COMMUNITY-01 — Reddit/HN/X 반응 수집
[ ] 사용자 피드백 수집 (퀴즈, 북마크, 댓글)
[ ] 트렌드 분석 및 핫이슈 추천
```

**Wave 3: 자동화 (2026-04-20~05-01)**
```
[ ] AUTOPUB-01 — Quality ≥80 자동 발행
[ ] 스마트 발행 스케줄 (최적 시간)
[ ] A/B 테스트 자동화
```

### NP4-Q 스프린트 게이트 상태

- [x] News Pipeline v4 core (2 personas, skeleton-map) — **완료**
- [x] Weekly Digest 백엔드 구현 — **완료**
- 🔄 FastAPI Direct Calls (FASTAPI-DIRECT-01) — **2026-03-27 목표**
- 🔄 품질 체크 Expert/Learner (QUALITY-CHECK-02) — **2026-03-28 목표**
- 🔄 PROMPT-AUDIT P1/P2 배포 (41개 남음) — **2026-03-28 목표 70%**
- [ ] 뉴스 quality_score 평균 ≥75 — **데이터 축적 중**
- [ ] `ruff check .` + `pytest tests/ -v` 통과 — **PROMPT-AUDIT 완료 후**

### 설계 참조 (NP4-Q Sprint)
- [[2026-03-16-weekly-digest-design]] — Weekly Digest 설계 (v4 완료, 백엔드 active)
- [[2026-03-18-prompt-audit-fixes]] — 프롬프트 감사 52개 이슈 (11/52 배포)
- [[plans/2026-03-25-direct-fastapi-ai-calls]] — FastAPI direct AI calls (진행 중)
- [[plans/2026-03-26-news-quality-check-overhaul]] — 품질 체크 Expert/Learner (진행 중)
- [[plans/2026-03-26-README-design]] — README 작성 (진행 중)

---

## 이전 스프린트 요약

> Phase 3A-SEC (2026-03-08~09) — 게이트 전체 통과, 12개 태스크 완료.
> AI News Pipeline v1 (2026-03-10~14) — 삭제됨. v2 재설계.

## Related Plans

### Current Phase (NP4-Q)
- [[plans/2026-03-27-user-webhook-subscriptions|유저 Webhook 구독 셀프서비스]]
- [[plans/2026-03-25-direct-fastapi-ai-calls|FastAPI Direct AI Calls]]
- [[plans/2026-03-26-README-design|README 작성 계획]]
- [[plans/2026-03-26-news-quality-check-overhaul|뉴스 품질 체크 전면 재작성]]
- [[2026-03-18-prompt-audit-fixes|프롬프트 감사 52개 이슈 수정]]

### v4 Foundation (Completed)
- [[2026-03-16-daily-digest-design|Daily Digest v3/v4 설계]]
- [[2026-03-16-weekly-digest-design|Weekly Digest 설계]]
- [[2026-03-17-news-pipeline-v4-design|v4 파이프라인 전환]]

### Handbook (Stable)
- [[2026-03-15-handbook-quality-design|Handbook 퀄리티 기준]]
- [[2026-03-18-handbook-advanced-quality-design|Handbook 심화 퀄리티 시스템]]

### Next Phase (Planning)
- [[2026-03-16-auto-publish-roadmap|자동 발행 로드맵]]
- [[Implementation-Plan|전체 구현 계획]]
- [[Phase-Flow|전체 Phase 진행 현황]]
