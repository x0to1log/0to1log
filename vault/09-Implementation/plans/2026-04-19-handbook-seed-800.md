# Handbook Seed 800 — Curation & Generation Plan

> **작성일:** 2026-04-19 · **갱신:** 2026-04-20
> **목표:** 57 published → +800 신규 = ~857개 (SEO·커버리지·최신성)
> **연관 태스크:** ACTIVE_SPRINT `HB-SEED-*`, HB-MIGRATE-138
> **작업 디렉토리:** [[2026-04-19-handbook-seed-800/README|2026-04-19-handbook-seed-800/]]

## 배경

현재 핸드북 published가 **57개** (어제 초안에 "138개"로 적었던 것은 archived 포함 오인). 이 규모로는 SEO 노출·내부 링크 밀도·발견성 부족. 추가 생성은 admin 수동 입력밖에 없어 속도가 부족.

병렬 batch 생성 인프라(`advisor.py`에 `batch-regen-xxx` term_id 패턴 + `run_handbook_advise()` 엔드포인트)가 이미 일부 존재 → 시드 800개 일괄 생성 파이프라인으로 확장.

## 결정

- **규모:** +800 신규 (최종 ~857 published)
- **대상 프로파일:** **(A)** 절대 숫자 확장 + **(C)** 2024~2026 최신 용어 우선
- **큐레이션 방식:** E — Amy 직접 큐레이션. Codex는 **후보 제안만** 돕고, 선택/제거/수정은 Amy가 결정
- **카테고리 분배:** 비대칭

| Category | Target | 근거 |
|----------|--------|------|
| llm-genai | 180 | 최다 — 핵심 관심, 최신성 높음 |
| deep-learning | 130 | 아키텍처·학습 기법 |
| products-platforms | 110 | 최신 제품·API (volatility fast-changing) |
| ml-fundamentals | 90 | 전통 ML 기초 |
| infra-hardware | 90 | GPU·서빙·최적화 |
| data-engineering | 70 | 파이프라인·스토리지 |
| cs-fundamentals | 50 | AI 인접만 |
| math-statistics | 40 | AI 맥락 |
| safety-ethics | 40 | 안전·정렬 |
| **합계** | **800** | |

## 파일 포맷: JSONL

- **한 줄 = 한 용어 객체** — Codex append 안전, 들여쓰기·escape 없음
- Python `json.loads()` per line — 한 줄 깨져도 복구
- `wc -l`로 진행 상황 즉시 확인
- 각 카테고리 파일 첫 줄 `_meta` 객체 (target, vocab hint) — 파서 스킵

## 검증된 사실 (2026-04-20)

### 점수 저장 시스템 정상 동작

CoT 재생성 테스트(`scripts/test_advisor_score_save.py CoT`):
- 소요: **485초 (8분 5초)**
- 토큰: **150,543**
- 저장 결과: adv=78, basic=92, **method=hybrid, source=manual, 0-100 스케일**
- 2개 row 정상 insert (adv + basic)

즉 `run_handbook_advise()` → `handbook_quality_scores` 저장 경로는 신뢰 가능. **HQ-05 "점수 저장 버그"는 실제로는 레거시 데이터 이슈**(초기 수동 생성 16개 + slug 파생 1건)로 재해석 완료.

### Slug 파생 불일치 (경미)

`advisor.py:2732`가 `handbook_quality_scores.term_slug`를 `req.term` 기반으로 재계산:
```python
term_slug = re.sub(r'[^a-z0-9]+', '-', req.term.lower().strip()).strip('-')
```

→ `req.term="CoT"` 입력 시 `slug="cot"` 저장, 실제 `handbook_terms.slug="chain-of-thought"`. join 불일치. **workaround:** `term_id`(UUID)로 조인. **근본 수정:** HB-SEED-12로 이관.

### 실측 비용·시간

| 항목 | 초기 추정 | **실측 기반 재계산** |
|------|---------|-------------------|
| 시간 (3-parallel, 800개) | ~12h | **~35h** |
| 비용 (gpt-5 토큰가 기준) | ~$90 | **~$400~800** |

ACTIVE_SPRINT의 HB-MIGRATE-138 "~$15" 추정치도 실제 대비 낮음. **warmup 30개 실측 후 확정.**

## 품질 게이트 설계 (수정판)

### 설계 원칙

1. **객관 5-check = 메인 게이트** (regex/날짜, 신뢰도 높음)
2. **LLM quality_score = 보조 필터** (그라디언트 용)
3. 누락 점수는 fail-close(draft) — auto-publish 절대 금지

### Config 초안 (`_config.yaml`)

```yaml
generation:
  concurrency: 3                    # 동시 3개
  retry_limit: 2                    # 최대 2회 재시도
  retry_feedback_to_prompt: true    # 2차 retry 시 실패 이유를 프롬프트에 주입
  model: gpt-5

quality_gate:
  # Hard blockers: 객관 5-check (type-aware 적용)
  objective_checks:
    require_all_pass: true
    checks:
      - stale_model_comparison
      - missing_architecture_detail   # type-aware
      - missing_paper_reference       # type-aware
      - dated_claim
      - stale_age
    type_aware_rules:
      missing_paper_reference:
        applies_to: [model_algorithm_family, foundational_concept, training_optimization_method]
      missing_architecture_detail:
        applies_to: [model_algorithm_family]

  # Soft: LLM 점수 2-tier
  auto_publish:
    advanced_score: 80
    basic_score: 75                 # bimodal이라 ≥55 또는 ≥85 둘 중 하나에 몰림. 75는 하한 안전선
    require_method: hybrid          # "unknown" method 제외
    require_both_scores: true       # adv, basic 둘 다 저장되어야 함 (누락 시 draft)

  draft:
    advanced_score: 55              # 55~80
    basic_score: null               # bimodal로 변별 없음 → 조건 제외

  fail_retry:
    objective_any_fail: true
    OR_advanced_score_below: 55

calibration:
  warmup_count: 30                  # 첫 30개는 auto_publish 비활성, 전부 draft
  warmup_policy: force_draft

publish:
  mode: auto                        # auto | review_queue
  warmup_override: review_queue     # warmup 중에는 강제로 수동 승인 모드

paths:
  seed_dir: vault/09-Implementation/plans/2026-04-19-handbook-seed-800/
  queue: queue.jsonl
  state: state.jsonl
  failures: failures.jsonl
  source_of_truth_module: services.agents.prompts_handbook_types  # TERM_TYPES, CATEGORY_CONTEXT
```

### 동작 흐름

```
┌──────────┐   ┌──────────┐   ┌──────────┐
│ queue    │──▶│ worker 1 │──▶│ advisor  │──▶ handbook_terms (draft/published)
│ .jsonl   │   │ worker 2 │   │ +HB-MEAS │──▶ handbook_quality_scores
│ (800개)   │   │ worker 3 │   │ +5-check │
└──────────┘   └──────────┘   └──────────┘
                      │
                      ▼
              ┌─────────────────┐
              │  게이트 분기     │
              ├─────────────────┤
              │ 5-check 전부 OK │
              │ + adv≥80        │──▶ published
              │ + basic≥75      │
              │ + hybrid method │
              │ + 양쪽 저장됨   │
              │─────────────────│
              │ 5-check 1개 실패 │──▶ draft (Amy 검수)
              │ OR adv 55~80    │
              │ OR 점수 누락     │
              │─────────────────│
              │ 5-check 2개+ 실패 │──▶ retry (최대 2회)
              │ OR adv<55       │  실패시 failures.jsonl
              └─────────────────┘
```

## 워크플로 Phase

### Phase 0 — Curation (진행 중)
- HB-SEED-01: Amy + Codex가 9 카테고리 JSONL에 800 용어 수집
- HB-SEED-02: `export_handbook_slugs.py` 1회 실행 → `_existing.jsonl` 채움

### Phase 1 — Validation
- HB-SEED-10: 9 JSONL 통합 + validator:
  - 스키마 체크 (term_type ∈ TERM_TYPES, 필수 필드)
  - **정확 중복** (`_existing.jsonl` slug 기준)
  - **퍼지 중복** (Levenshtein + aliases cross-match + `term_to_slug` 정규화 결과 매칭)
  - Target vs 실제 count 리포트
  - 출력: `queue.jsonl`

### Phase 2 — Orchestrator
- HB-SEED-20: `_config.yaml` 스키마 + 로더
- HB-SEED-21: State 관리 (`state.jsonl`, resume-safe, idempotent insert)
- HB-SEED-22: Parallel runner (asyncio semaphore=3, 기존 `run_handbook_advise()` 재활용)
- HB-SEED-23: 2-tier 품질 게이트 구현
- HB-SEED-24: 분기 로직 (auto_publish / draft / retry)
- HB-SEED-25: CLI `scripts/run_handbook_seed.py`
  - `--dry-run`: queue만 검증하고 실제 호출 안 함
  - `--resume`: state.jsonl 기준 이어서 실행
  - `--limit N`: 앞 N개만
  - `--warmup`: warmup 모드 (전부 draft 강제)

### Phase 3 — Admin UX
- HB-SEED-30 (P0): Admin Draft 리스트에 `adv/basic` score + 실패 체크 배지 (warmup 선행 조건)
- HB-SEED-31 (P1): 편집 페이지에 full 5-check 결과 + "재생성" 버튼

### Phase 4 — Execution
- HB-SEED-40: Warmup 30개 → 전부 draft → Amy 수동 검수 → 점수 vs 체감 품질 일치 확인
- HB-SEED-41: Threshold + 비용 calibration (warmup 결과 반영)
- HB-SEED-42: Full run (나머지 770) + failures 재시도 스위프

## Codex 경계 (큐레이션 철학 유지)

Amy가 E(직접 큐레이션) 선택한 취지를 지키기 위한 룰:

> **Codex는 후보를 제안만 한다. 선택·제거·수정·최종 승인은 Amy 본인이 한다.**

구체 운영:
- Codex가 한 라운드에 최대 50개 후보 → Amy가 리뷰 후 승인/수정/거절
- Codex가 제안한 용어 중 **Amy가 명시적으로 채택**한 것만 `.jsonl`에 기록
- 후보는 GitHub 스타일 일회용 제안 (구조화된 대화 로그 유지 불필요)

> ⚠️ **안티 패턴:** "Codex가 제안 → Amy 전량 OK" — E 선택 무효화. Amy가 최소 20~30%는 거르거나 수정해야 큐레이션 의미 유효.

## 부수 태스크

- **HB-SEED-12 (P2):** `handbook_quality_scores.term_slug` 파생 로직 정리 — `req.term` 기반 대신 DB official slug 사용. NLP 등 mismatch 레코드 cleanup.
- **HB-SEED-50 (P2):** 토큰 다이어트 프로파일링 — CoT 150k 토큰 중 retrieval/prompt 단계별 비용 분석. 800개 비용을 $400→$200로 낮출 수 있는지 탐색. Warmup 실측 후 발동.

## 알려진 리스크·완화

| 리스크 | 완화 |
|--------|------|
| **비용 폭주** (추정 $400~800) | warmup 30개로 실측 후 GO/NO-GO. 한도 초과 시 HB-SEED-50 먼저 |
| **Auto-publish 오판** | 2-tier 게이트 + warmup calibration + Amy가 `fail-close` 선호 |
| **Stale score** (편집 후 점수 미갱신) | seed 800은 신규라 초기엔 문제 없음. 장기 과제(rescore-on-edit)로 별도 분리 |
| **Pipeline 소스 0-10 스케일 버그** | seed는 `source=manual` path만 쓰므로 무관. pipeline 버그는 별도 이슈 |
| **Transient API failure** (12h 롱런 중 429/timeout) | State file + `--resume` + idempotent insert로 복구 가능 |
| **Codex 편향** (E 무효화) | 위 "Codex 경계" 룰로 완화. Amy가 실제로 필터링했는지 커밋 히스토리로 검증 가능 |

## 관련 문서

- [[2026-03-31-handbook-quality-audit]] — 품질 감사 (규모 확장 배경)
- [[2026-04-16-handbook-quality-measurement-plan]] — HB-MEASURE 5-check (품질 게이트 근거)
- [[ACTIVE_SPRINT]] — HB-SEED-* 태스크 추적
