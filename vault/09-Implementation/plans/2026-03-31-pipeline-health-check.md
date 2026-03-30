# NQ-17: Pipeline Health Check Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 파이프라인 각 단계(classify, merge, enrich, community)에 코드 기반 이상 탐지를 추가하여, LLM quality check에서 잡히지 않는 과정 문제를 warning 로그로 기록.

**Architecture:** 기존 파이프라인 흐름을 변경하지 않고, 각 단계의 `_log_stage()` 호출 직전에 health check 로직을 삽입. warning이 발생해도 파이프라인은 계속 진행 (blocking 아님). warning은 `debug_meta.warnings` 배열에 저장되어 어드민 pipeline-runs 상세 페이지에서 확인 가능.

**Tech Stack:** Python, 기존 pipeline.py + _log_stage()

---

### Task 1: `_check_pipeline_health()` 헬퍼 함수 추가

**Files:**
- Modify: `backend/services/pipeline.py` (상단 헬퍼 함수 영역)

**Step 1: 함수 구현**

`_log_stage()` 근처에 추가:

```python
def _check_pipeline_health(
    stage: str,
    *,
    classify_picks: tuple[int, int] | None = None,  # (research, business)
    merge_groups: list | None = None,
    community_total: int | None = None,
    community_found: int | None = None,
    enrich_map: dict | None = None,
    all_groups: list | None = None,
) -> list[str]:
    """Run stage-specific health checks. Returns list of warning strings."""
    warnings: list[str] = []

    if stage == "classify" and classify_picks:
        r, b = classify_picks
        if r == 0 and b == 0:
            warnings.append("classify: 0 picks for both categories")
        if r == 0:
            warnings.append("classify: 0 research picks")
        if b == 0:
            warnings.append("classify: 0 business picks")

    if stage == "merge" and merge_groups is not None:
        for g in merge_groups:
            if len(g.items) >= 5:
                warnings.append(f"merge: group '{g.group_title[:50]}' has {len(g.items)} items (possible over-grouping)")
            if len(g.items) >= 2:
                urls = [i.url for i in g.items]
                if len(set(urls)) < len(urls):
                    warnings.append(f"merge: group '{g.group_title[:50]}' has duplicate URLs")

    if stage == "community" and community_total is not None:
        if community_found == 0 and community_total > 0:
            warnings.append(f"community: 0 reactions from {community_total} queries")

    if stage == "enrich" and enrich_map is not None and all_groups is not None:
        zero_source_groups = [
            g.group_title[:50] for g in all_groups
            if not enrich_map.get(g.primary_url)
        ]
        if zero_source_groups:
            warnings.append(f"enrich: {len(zero_source_groups)} groups with 0 sources: {zero_source_groups[:3]}")

    return warnings
```

**Step 2: ruff check**

Run: `backend/.venv/Scripts/python.exe -m ruff check services/pipeline.py`

**Step 3: Commit**

```
feat(news): NQ-17 step1 — _check_pipeline_health() 헬퍼 함수
```

---

### Task 2: classify 단계에 health check 삽입

**Files:**
- Modify: `backend/services/pipeline.py` (line ~1129, classify _log_stage 직전)

**Step 1: classify health check 추가**

기존 `_log_stage` 호출의 `debug_meta`에 warnings 추가:

```python
        classify_warnings = _check_pipeline_health(
            "classify",
            classify_picks=(len(classification.research_picks), len(classification.business_picks)),
        )

        await _log_stage(
            supabase, run_id, "classify", "success", t0,
            ...
            debug_meta={
                ...existing...,
                "warnings": classify_warnings,
            },
        )
        for w in classify_warnings:
            logger.warning("Health check: %s", w)
```

**Step 2: ruff check + commit**

```
feat(news): NQ-17 step2 — classify health check
```

---

### Task 3: merge 단계에 health check 삽입

**Files:**
- Modify: `backend/services/pipeline.py` (line ~1156, merge _log_stage 직전)

**Step 1: merge health check 추가**

```python
        all_merged = classification.research + classification.business
        merge_warnings = _check_pipeline_health("merge", merge_groups=all_merged)

        await _log_stage(
            supabase, run_id, "merge", "success", t0,
            ...
            debug_meta={"llm_output": merge_output, "warnings": merge_warnings},
        )
        for w in merge_warnings:
            logger.warning("Health check: %s", w)
```

**Step 2: ruff check + commit**

```
feat(news): NQ-17 step3 — merge health check (과묶기 + URL 중복 탐지)
```

---

### Task 4: community 단계에 health check 삽입

**Files:**
- Modify: `backend/services/pipeline.py` (line ~1188, community _log_stage 직전)

**Step 1: community health check 추가**

```python
        community_warnings = _check_pipeline_health(
            "community",
            community_total=len(community_lookup),
            community_found=len(community_map),
        )

        await _log_stage(
            supabase, run_id, "community", "success", t0,
            ...
            debug_meta={"warnings": community_warnings} if community_warnings else None,
        )
        for w in community_warnings:
            logger.warning("Health check: %s", w)
```

**Step 2: ruff check + commit**

```
feat(news): NQ-17 step4 — community health check (0건 수집 경고)
```

---

### Task 5: enrich 단계에 health check 삽입

**Files:**
- Modify: `backend/services/pipeline.py` (line ~1222, enrich _log_stage 직전)

**Step 1: enrich health check 추가**

```python
        enrich_warnings = _check_pipeline_health(
            "enrich",
            enrich_map=enriched_map,
            all_groups=all_ranked,
        )

        await _log_stage(
            supabase, run_id, "enrich", "success", t0,
            ...
            debug_meta={"warnings": enrich_warnings} if enrich_warnings else None,
        )
        for w in enrich_warnings:
            logger.warning("Health check: %s", w)
```

**Step 2: ruff check + commit**

```
feat(news): NQ-17 step5 — enrich health check (0소스 그룹 경고)
```

---

### Task 6: 전체 ruff check + 검증

**Files:** 전체 수정 파일

**Step 1: ruff check**

```bash
backend/.venv/Scripts/python.exe -m ruff check services/pipeline.py
```

**Step 2: 파이프라인 run 후 어드민에서 확인**

- pipeline-runs 상세 → 각 단계의 debug_meta에 `warnings` 배열 확인
- Railway 로그에서 `Health check:` 로그 확인
- warning이 없으면 빈 배열 또는 키 없음 → 정상
