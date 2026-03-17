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

### 28. Weekly Digest 구현 `[WEEKLY-01]`
- **체크:** [ ]
- **상태:** todo (선행: Daily Digest 안정화)
- **설계 참조:** [[2026-03-16-weekly-digest-design]]

### 29. 자동 발행 Phase 2: 퀄리티 기준 자동 발행 `[AUTOPUB-01]`
- **체크:** [ ]
- **상태:** todo (선행: 퀄리티 점수 데이터 축적)
- **설계 참조:** [[2026-03-16-auto-publish-roadmap]]

### 30. 파이프라인 최적화: 다이제스트 병렬화 `[OPT-01]`
- **체크:** [ ]
- **상태:** todo
- **목적:** Research + Business 다이제스트를 `asyncio.gather`로 동시 생성 (~25s 절감)
- **설계 참조:** [[2026-03-17-pipeline-optimization]]

### 31. 파이프라인 최적화: 핸드북 call 병렬화 `[OPT-02]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 핸드북 4-call 중 Call 2(EN Basic) + Call 3(KO Advanced) 병렬 실행 (용어당 ~5s 절감)
- **의존성:** OPT-01

### 32. 파이프라인 최적화: 핸드북 용어 동시 생성 `[OPT-03]`
- **체크:** [ ]
- **상태:** todo
- **목적:** 핸드북 용어 2개씩 동시 생성 (세마포어 제한, ~30s 절감)
- **의존성:** OPT-02

### 33. 데드 코드 정리 `[OPT-04]`
- **체크:** [ ]
- **상태:** todo
- **목적:** `_generate_post()`, `_filter_terms_with_llm()` 제거
- **의존성:** OPT-03

### 34. 페르소나 완전성 강제 `[BUG-PERSONA-01]`
- **체크:** [x]
- **상태:** done
- **목적:** 3개 페르소나 모두 성공해야만 포스트 저장 (부분 실패 시 저장 안 함)
- **수정:** `_generate_digest()`, `_generate_post()` — `len(personas) < 3` 체크

---

## 의존성 순서

```
[완료] Pipeline v2 → Infra → Handbook → Digest v3 → Quality → BUG-PERSONA-01

[다음]
OPT-01 → OPT-02 → OPT-03 → OPT-04 (파이프라인 최적화)
COMMUNITY-01 → DIGEST-04 (검증)
                  ↓
             WEEKLY-01 (주간 다이제스트)
                  ↓
             AUTOPUB-01 (자동 발행)
```

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
