# ACTIVE SPRINT — News Pipeline v4 Quality Stabilization (NP4-Q)

> **스프린트 기간:** 2026-03-15~진행 중 (NP4-Q phase)
> **마지막 업데이트:** 2026-03-26 17:45 (+27 commits since 2026-03-19, 48+/50 tasks complete)
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
| NQ-10 | Business Expert citation 중복 — 같은 URL에 매번 새 번호 부여 (18개 → 5개) | — | — | todo |
| NQ-11 | CP MANDATORY 4곳 통일 (Business Expert CP 누락 반복) | — | — | todo |
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
