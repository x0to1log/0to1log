# Pipeline Analytics Dashboard

> 파이프라인 단계별 토큰/비용/품질을 트래킹하고 시계열로 비교하는 대시보드.

## 목표

- 각 파이프라인 실행의 단계별 비용 비율을 한눈에 파악
- 실행 간 추이를 시계열 차트로 비교 (프롬프트 변경 전후 효과 측정)
- quality_score를 기록해서 비용 대비 품질 판단 근거 확보

## 접근: 프론트엔드 중심 (DB 변경 없음)

기존 `pipeline_logs` 테이블에 이미 `tokens_used`, `cost_usd`, `model_used`, `duration_ms`, `debug_meta` (JSONB)가 기록되고 있음. 하루 1회 실행이라 데이터 양이 적으므로 프론트엔드에서 직접 쿼리.

---

## 1. 백엔드: debug_meta 강화

### 1-1. 에이전트에서 attempts 반환

각 에이전트 함수(`generate_business_expert`, `derive_business_personas`, `_translate_business`, `_translate_research`, `generate_research_post`, `rank_candidates`)가 usage와 함께 **attempts 횟수**를 반환하도록 변경.

변경 방식: 각 에이전트의 return에 `cumulative_usage`에 `"attempts": attempt + 1` 추가.

### 1-2. pipeline.py log_pipeline_stage 호출부 보강

각 단계의 `debug_meta`에 다음 필드 추가:

**research.generate.en / research.translate.ko:**
```python
debug_meta={
    "research_en_len": len(...),        # 기존
    "has_news": ...,                     # 기존
    "resumed_from_saved_en": ...,        # 기존
    "input_tokens": usage.get("input_tokens"),     # 신규
    "output_tokens": usage.get("output_tokens"),   # 신규
    "attempts": usage.get("attempts", 1),          # 신규
}
```

**business.generate.en:**
```python
debug_meta={
    "business_analysis_len": ...,        # 기존
    "persona_lengths": {...},            # 기존
    "input_tokens": usage.get("input_tokens"),     # 신규
    "output_tokens": usage.get("output_tokens"),   # 신규
    "expert_call_tokens": {                        # 신규
        "input": expert_usage.get("input_tokens"),
        "output": expert_usage.get("output_tokens"),
    },
    "derive_call_tokens": {                        # 신규
        "input": derive_usage.get("input_tokens"),
        "output": derive_usage.get("output_tokens"),
    },
    "attempts": {                                  # 신규
        "expert": expert_usage.get("attempts", 1),
        "derive": derive_usage.get("attempts", 1),
    },
}
```

**business.translate.ko:**
```python
debug_meta={
    "business_analysis_len": ...,        # 기존
    "persona_lengths": {...},            # 기존
    "input_tokens": usage.get("input_tokens"),     # 신규
    "output_tokens": usage.get("output_tokens"),   # 신규
    "attempts": usage.get("attempts", 1),          # 신규
}
```

### 1-3. quality_score 기록

research/business KO 저장 직후 `compute_quality()` 호출 → `debug_meta`에 추가:

```python
score, flags = compute_quality(post_dict)
# 해당 단계의 debug_meta에 추가:
"quality_score": score,
"quality_flags": flags,
```

### 1-4. business.py에서 expert/derive usage 분리 반환

현재 `generate_business_post()`가 `merge_usage_metrics(expert_usage, derive_usage)`로 합산만 반환.
pipeline.py에서 expert/derive 각각의 토큰을 기록하려면 **개별 usage도 반환**해야 함.

변경: `generate_business_post()` → `tuple[BusinessPost, dict, dict, dict]` (post, total_usage, expert_usage, derive_usage)

---

## 2. 프론트엔드: [runId] 상세 페이지 개선

### 2-1. Cost Breakdown 섹션 추가 (Stage Timeline 위)

Summary Grid와 Stage Timeline 사이에 **비용 비율 가로 막대** 섹션 삽입:

- AI 호출이 있는 단계만 표시 (rank, research.en, research.ko, business.en, business.ko, terms)
- 각 단계의 비용이 전체의 몇 %인지 가로 막대 + 라벨로 표시
- CSS-only 구현 (width 퍼센트)

### 2-2. Stage Card 칩 강화

기존 Tokens/Cost 칩에 **Input/Output 분리** 표시:
- `debug_meta.input_tokens` / `debug_meta.output_tokens` 있으면 `In: 3,200 / Out: 4,100` 형식
- `debug_meta.attempts` 있으면 Attempt 칩에 표시
- `debug_meta.quality_score` 있으면 Quality 칩 추가 (0-4 점수 + 색상)

---

## 3. 프론트엔드: Analytics 페이지 (신규)

### 경로: `/admin/pipeline-analytics`

### 3-1. 데이터 소스

```sql
-- 최근 30일 pipeline_logs (AI 호출 단계만)
SELECT pl.*, pr.run_key, pr.started_at as run_started_at
FROM pipeline_logs pl
JOIN pipeline_runs pr ON pl.run_id = pr.id
WHERE pr.started_at > now() - interval '30 days'
  AND pl.pipeline_type NOT IN ('pipeline', 'research.novelty_gate', 'candidates.save')
ORDER BY pr.started_at ASC, pl.created_at ASC
```

### 3-2. 차트 라이브러리

Chart.js CDN (`<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js">`).
어드민 전용이므로 번들 크기 무관.

### 3-3. 차트 구성

**Chart 1: 실행별 총 비용 추이** (Line chart)
- X축: run_key (날짜)
- Y축: 총 cost_usd
- 성공/실패 색상 구분

**Chart 2: 단계별 비용 분포** (Stacked bar chart)
- X축: run_key
- Y축: cost_usd
- 스택: rank, research.en, research.ko, business.en, business.ko, terms

**Chart 3: 단계별 토큰 추이** (Grouped bar chart)
- Input vs Output 토큰 비교
- 단계별 그룹

**Chart 4: Quality Score 추이** (Line chart)
- X축: run_key
- Y축: quality_score (0-4)
- research/business 별도 라인

### 3-4. 통계 테이블

각 pipeline_type별 평균:
| Stage | Avg Tokens | Avg Cost | Avg Duration | Success Rate | Avg Attempts |
|-------|-----------|---------|-------------|-------------|-------------|

### 3-5. 레이아웃

기존 어드민 패턴 (AdminSidebar + admin-main).
`pipeline-runs` 옆에 `pipeline-analytics` 사이드바 항목 추가.

---

## 변경 파일 목록

### 백엔드
- `backend/services/agents/business.py` — expert/derive usage 분리 반환, attempts 추가
- `backend/services/agents/research.py` — attempts 추가
- `backend/services/agents/ranking.py` — attempts 추가
- `backend/services/agents/translate.py` — attempts 추가
- `backend/services/pipeline.py` — debug_meta 강화, quality_score 기록

### 프론트엔드
- `frontend/src/pages/admin/pipeline-runs/[runId].astro` — Cost Breakdown 섹션 + 칩 강화
- `frontend/src/pages/admin/pipeline-analytics.astro` — 신규 페이지
- `frontend/src/components/admin/AdminSidebar.astro` — Analytics 링크 추가

### DB
- 변경 없음 (기존 `pipeline_logs.debug_meta` JSONB 활용)
