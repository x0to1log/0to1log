# ACTIVE SPRINT — AI News Pipeline v3 + Quality

> **스프린트 시작:** 2026-03-15
> **목표:** AI News Pipeline v3 (다이제스트 큐레이션) + 핸드북/뉴스 퀄리티 안정화
> **설계 참조:** `vault/04-AI-System/AI-News-Pipeline-Design.md`, [[2026-03-16-daily-digest-design]]
> **이전 스프린트:** Phase 3A-SEC — 2026-03-09 게이트 전체 통과

---

## 스프린트 완료 게이트

- [x] 파이프라인 v3 다이제스트 형태로 전환 (research + business)
- [x] 3 페르소나 × 2 언어 다이제스트가 news_posts에 저장됨
- [x] 핸드북 4-call 분리로 KO/EN 누락 해소
- [x] 퀄리티 스코어링 구현
- [ ] 커뮤니티 반응 수집 구현
- [ ] 파이프라인 1회 실행 → 다이제스트 + 핸드북 전체 정상 확인
- [ ] `ruff check .` + `pytest tests/ -v` 통과

---

## Current Doing (1개 고정)

| Task ID | 상태 | 시작 시점 | Owner |
|---|---|---|---|
| - | - | - | - |

---

## 완료된 태스크

### News Pipeline v2 기반 — 모두 완료
- [x] `NP2-MODEL-01` — Pydantic 모델 정의
- [x] `NP2-COLLECT-01` — 뉴스 수집 모듈 (Tavily)
- [x] `NP2-RANK-01` — LLM 랭킹
- [x] `NP2-FACTS-01` — 팩트 추출
- [x] `NP2-PERSONA-01` — 페르소나 생성
- [x] `NP2-PIPE-01` — 파이프라인 오케스트레이터
- [x] `NP2-CRON-01` — Cron 엔드포인트
- [x] `NP2-E2E-01` — E2E 검증
- [x] `NP2-DEPLOY-01` — 배포 + cron 실행
- [x] `NP2-BACKFILL-01` — 과거 날짜 백필

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

### Daily Digest v3 전환 — 모두 완료
- [x] `DIGEST-01` — 랭킹 → 분류 (카테고리별 3~5건)
- [x] `DIGEST-02` — 다이제스트 프롬프트 (6 페르소나 × R/B)
- [x] `DIGEST-03` — 파이프라인 오케스트레이터 전환

### 퀄리티 개선 — 완료
- [x] `QUALITY-01` — 다이제스트 퀄리티 스코어링 (Research/Business 기준 분리)
- [x] `QUALITY-02` — LLM 2차 용어 필터링 (gpt-4o-mini)
- [x] `QUALITY-03` — headline_ko 생성 (LLM이 한국어 제목 생성)
- [x] `QUALITY-04` — 핸드북 4-call 분리 (KO Basic / EN Basic / KO Advanced / EN Advanced)
- [x] `QUALITY-05` — 비즈니스 다이제스트 깊이 개선 (2-3단락, CTO 브리핑 톤)
- [x] `QUALITY-06` — 빈 섹션 생략 + 입력 본문 확대 (2000→4000자)

---

## 남은 태스크

### 26. 커뮤니티 반응 수집 `[COMMUNITY-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 선정된 뉴스에 대한 Reddit/HN/X 커뮤니티 반응을 수집하여 다이제스트에 반영
- **배경:** v2 설계에 있었으나 v3 전환 시 누락됨. 원본 설계: [[AI-News-Pipeline-Design]] (커뮤니티 반응 수집 섹션)
- **접근:** 주요 뉴스 2-3건만 반응 수집 (전체 뉴스별 수집은 비용 과다)
- **산출물:** `news_collection.py`에 커뮤니티 반응 수집 함수, 다이제스트 프롬프트에 반응 컨텍스트 주입
- **완료 기준:** 다이제스트에 커뮤니티 반응 요약 포함 + 비용 기록
- **의존성:** DIGEST-03 (완료)

### 27. Daily Digest 프론트엔드 검증 `[DIGEST-04]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 다이제스트가 기존 페르소나 탭 + 마크다운 렌더러로 정상 표시되는지 검증
- **의존성:** COMMUNITY-01 (반영 후 검증)

### 28. Weekly Recap 파이프라인 + 뉴스레터 `[WEEKLY-01]` — NEXT SPRINT 최우선
- **체크:** [ ]
- **상태:** todo — **다음 스프린트 1순위**
- **설계 참조:** [[2026-03-16-weekly-digest-design]]
- **변경 (2026-03-25):** 비즈니스 분석 결과 배포 채널 구축이 최우선. Weekly Recap은 웹사이트 콘텐츠 + 이메일 뉴스레터 + 커뮤니티 공유의 기반이 됨.
- **범위 확장:**
  - 7일간 뉴스 베스트 3-5개 요약
  - 이번 주 핸드북 용어 1-2개 소개
  - 뉴스 속 AI 도구 추천 1개
  - 동일 콘텐츠를 웹(/weekly) + 이메일(Buttondown) 동시 발행
- **참조:** [[2026-03-25-Business-Reality-Check]], [[2026-03-25-business-pivot-decision]]

### 29. 자동 발행 Phase 2: 퀄리티 기준 자동 발행 `[AUTOPUB-01]`
- **체크:** [ ]
- **상태:** todo (선행: 퀄리티 점수 데이터 축적)
- **설계 참조:** [[2026-03-16-auto-publish-roadmap]]

### 30. 파이프라인 최적화: 다이제스트 병렬화 `[OPT-01]`
- **체크:** [x]
- **상태:** done
- **수정:** `pipeline.py` — `asyncio.gather`로 Research + Business 동시 생성

### 31. 파이프라인 최적화: 핸드북 call 병렬화 `[OPT-02]`
- **체크:** [x]
- **상태:** done
- **수정:** `advisor.py` — Call 2(EN Basic) + Call 3(KO Advanced) `asyncio.gather` 병렬

### 32. 파이프라인 최적화: 핸드북 용어 동시 생성 `[OPT-03]`
- **체크:** [x]
- **상태:** done
- **수정:** `pipeline.py` — `Semaphore(2)` + `asyncio.gather`

### 33. 데드 코드 정리 `[OPT-04]`
- **체크:** [x]
- **상태:** done
- **수정:** `_generate_post()`, `_filter_terms_with_llm()` 삭제, 미사용 import 정리

### 34. 페르소나 완전성 강제 `[BUG-PERSONA-01]`
- **체크:** [x]
- **상태:** done
- **수정:** `_generate_digest()` — `len(personas) < 3` 시 포스트 저장 안 함

### 35. Retry attempt 횟수 pipeline_logs 기록 `[OBSERVE-02]`
- **체크:** [x]
- **상태:** done
- **수정:** `pipeline.py` — 다이제스트 페르소나 루프에 MAX_DIGEST_RETRIES=1 + attempt 기록

### 36. 퀄리티 점수 Phase 2 완성 `[QUALITY-07]`
- **체크:** [x]
- **상태:** done
- **수정:** `pipeline.py` quality_score 독립 컬럼 저장, `index.astro` 배지 표시, `pipeline-analytics.astro` 차트 호환

### 37. KO 누락 자동 복구 `[RECOVERY-01]`
- **체크:** [x]
- **상태:** done
- **수정:** `pipeline.py` — 다이제스트 EN 있고 KO 없으면 KO만 재호출. `advisor.py` — 핸드북 Call 1 KO basic 없으면 재시도.

### 38. 페르소나 정체성 재설계 `[PERSONA-REDESIGN-01]`
- **체크:** [x]
- **상태:** done
- **수정:** `prompts_news_pipeline.py` — 6개 GUIDE + SECTIONS를 "읽은 후 행동" 축으로 재작성. Expert 3-4단락, Learner 2-3단락, Beginner 1-2단락.
- **설계 참조:** [[2026-03-17-persona-identity-redesign]]

### 39. 핸드북 링크 레벨 연결 `[HANDBOOK-LEVEL-LINK-01]`
- **체크:** [ ]
- **상태:** todo (v4 안정화 후 재검토)
- **목적:** 뉴스 본문의 핸드북 링크를 페르소나에 따라 기초/심화 레벨로 연결

### 40. Pipeline v4 — 2 페르소나 전환 `[V4-01]`
- **체크:** [x]
- **상태:** done
- **수정:** 프롬프트 재설계, 파이프라인 3→2, 프론트엔드 2탭, Beginner 완전 삭제, auto-fill(excerpt/tags/focus_items/reading_time)
- **설계 참조:** [[2026-03-17-news-pipeline-v4-design]]

### 41. 뉴스 본문 핸드북 용어 인라인 팝업 `[INLINE-POPUP-01]`
- **체크:** [x]
- **상태:** done
- **수정:** `rehypeHandbookTerms.ts` — `\b` → lookbehind `(?<![a-zA-Z\uAC00-\uD7AF])` + lookahead `(?![a-zA-Z])` 적용 완료. Node.js regex 검증으로 한국어 용어(에이전트가, 딥러닝은 등) 및 English(AI) 매칭 확인.

### 42. 핸드북 퀄리티 개선 `[HANDBOOK-QUALITY-01]`
- **체크:** [x]
- **상태:** done
- **수정:** 프롬프트 강화 (마크다운 포맷, 불릿 리스트, BAD/GOOD 예시, 반복 방지), article_context 전달, 자기 링크 방지

### 43. 핸드북 심화 퀄리티 시스템 `[HANDBOOK-ADV-01]`
- **체크:** [x]
- **상태:** done
- **수정:** Tavily 검색 + gpt-4o-mini 유형 분류 (10 types) + 유형별 심화 프롬프트 + Self-critique + 퀄리티 체크 (점수 매기기). Tavily context를 기초+심화 모든 Call에 적용.
- **설계 참조:** [[2026-03-18-handbook-advanced-quality-design]]

### 44a. 에디터 Delete 버튼 Danger Zone 분리 `[EDITOR-DANGER-01]`
- **체크:** [x]
- **상태:** done
- **수정:** 3개 에디터(blog/news/handbook) topbar에서 Delete 버튼 제거 → 에디터 하단 `.admin-danger-zone` 섹션으로 이동. `global.css` danger zone 스타일 추가.

### 44. 프롬프트 감사 수정 `[PROMPT-AUDIT-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 전체 프롬프트 감사 결과 52개 이슈 수정 (신뢰도/일관성/토큰 효율)
- **설계 참조:** [[2026-03-18-prompt-audit-fixes]]
- **구현 범위:**
  - P0 (CRITICAL): URL hallucination 방지, citation-소스 매핑, 사실 오류 방지
  - P1 (HIGH): 토큰 비효율 제거, few-shot 예시 추가, score 해석 정의, 유형 분류 모호성 해소
  - P2 (MEDIUM): 일관성 개선, 코드 기준 명확화, 구조 정리, 반복 제거 리팩토링
- **대상 파일:** `prompts_advisor.py`, `prompts_news_pipeline.py`, `prompts_handbook_types.py`

---

## 의존성 순서

```
[완료] Pipeline v2 → v3 → v4
       → OPT-01~04 → OBSERVE-02 → QUALITY-07 → RECOVERY-01
       → PERSONA-REDESIGN-01 → V4-01

[완료]
INLINE-POPUP-01 (한국어 매칭 수정 + 조상 체인 체크)
HANDBOOK-QUALITY-01 (핸드북 프롬프트 강화)

[완료]
HANDBOOK-ADV-01 (심화 퀄리티 시스템 — Tavily+유형분류+Self-critique)

[완료 — 2026-03-24 세션]
- 뉴스 파이프라인 백엔드 용어 링크 제거 (프론트엔드 전담)
- gpt-4o → gpt-4.1 / gpt-4o-mini → gpt-4.1-mini 모델 전환
- self-critique mini 전환 + confidence 기반 용어 큐 (비용 최적화)
- Quality Score Trend 차트 스케일 수정 (/4 → /100)
- 핸드북 Quality Score 차트 추가
- strikethrough/dollar 마크다운 렌더링 버그 수정
- 뉴스 퀴즈 기능 구현 (페르소나별 4지선다)
- quiz_responses 테이블 생성 (포인트 시스템 대비)
- headline/tags 언어 혼동 방지 + EN recovery 로직
- upsert null 덮어쓰기 방지
- definition bold 렌더링 수정
- 수식 $$ 프롬프트 지시 + 표 안 수식 금지

[완료 — 2026-03-25 세션 2] SEO + Admin Analytics 개선
- SEO: 전체 페이지 meta description + OG tags + canonical + Twitter card 추가
- Site Analytics: 탭 순서 Traffic→News→Handbook→Blog, News 탭 추가, Brief 3-column
- GA4 Data API: 백엔드 라우터 + 프론트 proxy 작성 (배포 대기)

[완료 — 2026-03-25 세션 1] 뉴스 퀄리티 개선
- 수집: HuggingFace Daily Papers + arXiv API + GitHub Trending 3개 소스 추가
- 수집: Tavily 쿼리에 research 지향 2개 추가, GitHub topic 태그 필터링
- 수집: GitHub README excerpt 병렬 fetch (raw_content 보강)
- 분류: research 서브카테고리 강화 (litmus test, NOT-Research 리스트)
- 분류: 3-5 → 0-5 룰 (빈 리스트 허용, 억지 채움 방지)
- 분류: open_source 기준 강화 (AI/ML 필수, awesome-* 제외)
- 글쓰기: 출처 인용 형식 변경 (Perplexity 번호 → Source URL 명시)
- 품질체크: research 섹션명 싱크 (Technical Outlook → Why It Matters)
- 품질체크: business 섹션명 싱크 (Action Items → Strategic Decisions)
- 기타: prompt-audit 스킬 파일 경로 수정, focus_items 길이 가이드
- PROMPT-AUDIT-01 P0 C2 (citation 매핑) 해결됨

[다음 Phase]
WEEKLY-01 (주간 다이제스트)
PROMPT-AUDIT-01 (프롬프트 감사)
COMMUNITY-01 (커뮤니티 반응 수집)
AUTOPUB-01 (자동 발행)
```

---

## 다음 Phase 계획 — Weekly Digest + 안정화

> **예상 시작:** 현재 스프린트 게이트 통과 후
> **목표:** Weekly Recap 탭 구현 + 프롬프트 품질 안정화 + 자동 발행 기반

### Phase 목표
1. **Weekly Digest** — 주간 요약 자동 생성 + 프론트엔드 탭
2. **프롬프트 감사** — 52개 이슈 중 P0/P1 우선 수정
3. **커뮤니티 반응** — Reddit/HN/X 반응 수집 (선택)
4. **자동 발행** — quality_score 기반 auto-publish 기초

### 태스크 순서

```
Phase A: Weekly Digest (핵심) — 구현 완료, 비활성화 상태
  [x] WEEKLY-PROMPT-01 → 주간 프롬프트 (expert/learner)
  [x] WEEKLY-PIPE-01   → run_weekly_pipeline() 파이프라인
  [x] WEEKLY-CRON-01   → 일요일 cron + 어드민 수동 버튼 + backfill (week picker)
  [x] WEEKLY-FE-01     → 뉴스 리스트 Weekly 탭 + 배지 + 하단 카드 (용어+도구)
  [x] WEEKLY-ADMIN-01  → 대시보드/Pipeline Runs 통합 UI (Daily+Weekly 카드 레이아웃)
  [ ] WEEKLY-TEST-01   → E2E 검증 (뉴스 퀄리티 안정 후 활성화)

Phase B: 뉴스 퀄리티 안정화 (진행 중)
  [x] PROMPT-FIX-01    → KO 제목 영어 문제 — fallback 체인 + prefix
  [x] PROMPT-FIX-02    → 섹션 구조 미준수 — 분석 섹션 MANDATORY 규칙
  [x] PROMPT-FIX-03    → 뉴스 분량 부족 — EQUAL COVERAGE 규칙
  [x] PROMPT-FIX-04    → Bullet format 미적용 — 구체적 예시 포함
  [x] PROMPT-FIX-05    → Citation 형식 — [N](URL) Perplexity 스타일
  [x] PROMPT-FIX-06    → Few-shot skeleton (EN+KO full 예시)
  [x] PROMPT-FIX-07    → KO 분량 가드레일 (80% 규칙 + KO 전용 skeleton)
  [x] PROMPT-FIX-08    → 수식 $$ 강제 (KaTeX 렌더링 깨짐 방지)
  [x] PROMPT-FIX-09    → sources 배열 (제목 포함) + 빈 URL 필터
  [x] PROMPT-FIX-10    → Quality check 프롬프트를 현재 형식에 맞게 업데이트
  [x] MODEL-EVAL-01    → gpt-4o vs gpt-4.1 A/B 테스트 → 프롬프트가 원인, 4.1 유지
  [ ] PROMPT-FIX-11    → Citation이 본문 단락 끝이 아닌 하단에 묶이는 문제 (고질적)
  [ ] PROMPT-FIX-12    → KO 섹션 헤더가 자유 형식으로 나오는 문제 (WebFetch 번역 가능성 확인 필요)
  [ ] QUALITY-HYBRID-01 → 규칙 기반 체크(코드) + LLM 평가 하이브리드 품질 시스템

Phase C: 확장 (선택)
  [ ] COMMUNITY-01     → 커뮤니티 반응 수집
  [ ] AUTOPUB-01       → quality_score ≥ 80 자동 발행
```

### 게이트 조건
- [x] Weekly Digest 구현 완료 (비활성화 상태, 뉴스 퀄리티 안정 후 활성화)
- [ ] 뉴스 quality_score 평균 ≥ 75 (현재 하락 추세 — 프롬프트 수정 효과 확인 필요)
- [ ] Citation이 본문 단락 끝에 정상 삽입
- [ ] KO/EN 커버리지 동등 + KO 섹션 헤더 정상
- [ ] `ruff check .` + `pytest tests/ -v` 통과

### 설계 참조
- [[2026-03-16-weekly-digest-design]] — Weekly Digest 설계 (v4 업데이트 완료)
- [[2026-03-18-prompt-audit-fixes]] — 프롬프트 감사 이슈 목록

---

## 이전 스프린트 요약

> Phase 3A-SEC (2026-03-08~09) — 게이트 전체 통과, 12개 태스크 완료.
> AI News Pipeline v1 (2026-03-10~14) — 삭제됨. v2 재설계.

## Related Plans

- [[2026-03-16-daily-digest-design|Daily Digest 재설계]]
- [[2026-03-16-weekly-digest-design|Weekly Digest 설계]]
- [[2026-03-16-auto-publish-roadmap|자동 발행 로드맵]]
- [[2026-03-15-handbook-quality-design|Handbook 퀄리티 시스템 설계]]
- [[Handbook-Prompt-Redesign|Handbook 프롬프트 재설계]]
- [[2026-03-17-pipeline-optimization|파이프라인 최적화 계획]]
- [[2026-03-18-handbook-advanced-quality-design|Handbook 심화 퀄리티 시스템]]
- [[2026-03-18-prompt-audit-fixes|프롬프트 감사 52개 이슈 수정]]
