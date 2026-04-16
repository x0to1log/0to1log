# Phase 2 — Reliability Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** URL hallucination 구조적 차단 + 측정 기반 Few-shot 추가 + Research 도메인 품질 게이트(2026-04-16 추가). 뉴스 파이프라인의 신뢰도와 출처 품질을 동시에 끌어올림.

**Architecture:** 4가지 직교 방어선을 추가한다.
1. Retroactive 측정 → 어디가 약한지 데이터 기반 식별
2. URL strict allowlist → LLM이 fact_pack 밖 URL을 인용하면 quality_meta에 플래그 + draft 강제
3. Research 도메인 priority/blocklist → 수집 단계에서 저품질 출처 제외
4. Few-shot → 측정으로 식별한 Top 2 프롬프트에 한 쌍의 좋은/나쁜 예시

전부 기존 인프라(`pipeline_quality.py`, `news_domain_filters` 테이블, `prompts_news_pipeline.py`) 확장이며 새 모듈 없음.

**Tech Stack:** Python 3.11 / FastAPI / Supabase / pytest / ruff

**Spec reference:** [2026-04-15-news-pipeline-hardening-design.md](2026-04-15-news-pipeline-hardening-design.md) §5 (Phase 2)

---

## Critical Constraints (read before starting)

1. **Baseline (Phase 1 완료 후 2026-04-16)**: 9 pre-existing pytest 실패, 141 passing, 4 pre-existing ruff 에러 in `advisor.py`. **이 숫자가 늘어나면 회귀.**

2. **`fact_pack` 실제 구조** (2026-04-16 production 데이터 기준 검증):
   ```json
   {
     "news_items": [
       {"url": "https://...", "title": "...", "subcategory": "big_tech"}
     ],
     "digest_type": "business",
     "quality_score": 90,
     "quality_issues": [{"scope": "frontload", "category": "overclaim", "severity": "minor", "message": "..."}],
     "quality_version": "v2",
     "quality_breakdown": {
       "llm": {"frontload": 19, "expert_body": 18, "learner_body": 18},
       "raw_llm": {"frontload": 94, "expert_body": 92, "learner_body": 89},
       "deterministic": {"locale": 10, "structure": 15, "traceability": 14}
     },
     "structural_penalty": 0,
     "structural_warnings": [],
     "quality_caps_applied": [],
     "auto_publish_eligible": false
   }
   ```
   ⚠️ **Spec discrepancy**: spec §5.1 작업 2가 `fact_pack.sources[*].url`를 언급했지만 실제 필드는 `fact_pack.news_items[*].url`이다. 이 plan은 actual 필드명 사용.

3. **`source_urls`** (top-level text[] column) vs **`fact_pack.news_items[*].url`**:
   - `source_urls` = collect/enrich 단계에서 모은 모든 URL (가장 넓음)
   - `fact_pack.news_items[*].url` = ranking 후 디지스트에 실제로 들어간 큐레이션된 URL (좁음)
   - **URL 검증의 strict allowlist = `fact_pack.news_items[*].url`** (LLM에게 인용하라고 준 정확한 set)
   - 만약 false positive(엄격한 fail)가 운영에서 너무 많으면, `source_urls` union으로 완화 가능 — but start strict.

4. **검증 실패 시 동작 — 재생성 X**: `_check_digest_quality()` 재시도 루프에 통합하지 않는다. 대신 `quality_meta`에 `url_validation_failed: true` 플래그 + 실패 URL 리스트만 기록 → `auto_publish_eligible=false` 강제. 이미 있는 draft queue 인프라 재사용.

5. **Branch policy**: main 직접 (CLAUDE.md), 작은 commit 자주.

6. **NO `Co-Authored-By`** 트레일러 commit message에 포함 금지.

---

## File Structure (target after Phase 2)

```
backend/
├── services/
│   ├── pipeline_quality.py     # MODIFY: add validate_citation_urls() + integrate into _check_digest_quality
│   ├── news_collection.py      # MODIFY: extend _classify_source_meta with research priority/blocklist
│   └── agents/
│       └── prompts_news_pipeline.py  # MODIFY: add Few-shot examples to Top 2 prompts
├── scripts/
│   └── measure_prompt_failures.py    # CREATE: retroactive measurement script
└── tests/
    └── test_pipeline_quality_scoring.py  # MODIFY: add URL validation unit + integration tests

supabase/migrations/
└── 00051_research_domain_filters.sql  # CREATE: extend news_domain_filters with new filter types

vault/09-Implementation/plans/
└── 2026-04-15-news-pipeline-failure-measurement.md  # CREATE: measurement output
```

**Estimated:** 5 files modified, 3 files created. Total LOC ~400.

---

## Chunk 1: Retroactive Measurement (Task 1)

**기간**: 반나절. **목적**: Few-shot의 타겟 프롬프트를 데이터로 결정.

### Task 1: Measurement script + analysis

**Files:**
- Create: `backend/scripts/measure_prompt_failures.py`
- Create: `vault/09-Implementation/plans/2026-04-15-news-pipeline-failure-measurement.md`

- [ ] **Step 1.1: Baseline test 실행**
```bash
cd c:/Users/amy/Desktop/0to1log/backend && ./.venv/Scripts/python.exe -m pytest tests/ --tb=no -q 2>&1 | tail -5
```
Expected: `9 failed, 141 passed`

- [ ] **Step 1.2: Measurement script 작성**

`backend/scripts/measure_prompt_failures.py`:
```python
"""Measure prompt failure distribution from past 14 days of news_posts.

Phase 2 Task 1 of 2026-04-15-news-pipeline-hardening.

Identifies which quality categories most frequently fall below threshold,
to target Few-shot example additions in prompts_news_pipeline.py.

Usage:
    cd backend && python scripts/measure_prompt_failures.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from core.database import get_supabase


def main() -> None:
    supabase = get_supabase()
    if supabase is None:
        print("ERROR: Supabase unavailable")
        sys.exit(1)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()

    # Pull last 14 days of digest news_posts (research + business)
    rows = (
        supabase.table("news_posts")
        .select("id, slug, post_type, locale, quality_score, fact_pack, pipeline_batch_id, created_at")
        .gte("created_at", cutoff)
        .in_("post_type", ["research", "business"])
        .execute()
        .data or []
    )

    print(f"\n=== Sample size: {len(rows)} digests over 14 days ===\n")

    # 1. Auto-publish eligibility distribution
    eligible_count = sum(1 for r in rows if (r.get("fact_pack") or {}).get("auto_publish_eligible"))
    print(f"auto_publish_eligible=true: {eligible_count} / {len(rows)} ({eligible_count/max(len(rows),1)*100:.1f}%)")

    # 2. Quality score distribution buckets
    score_buckets = Counter()
    for r in rows:
        s = r.get("quality_score") or 0
        if s >= 90: score_buckets["90+"] += 1
        elif s >= 80: score_buckets["80-89"] += 1
        elif s >= 70: score_buckets["70-79"] += 1
        else: score_buckets["<70"] += 1
    print(f"\nQuality score distribution: {dict(score_buckets)}")

    # 3. Per-category mean scores (using fact_pack.quality_breakdown)
    breakdown_sums: dict[str, list[int]] = defaultdict(list)
    issue_categories = Counter()
    issue_scopes = Counter()
    for r in rows:
        fp = r.get("fact_pack") or {}
        breakdown = fp.get("quality_breakdown") or {}
        for group in ("llm", "deterministic"):
            for cat, score in (breakdown.get(group) or {}).items():
                breakdown_sums[f"{group}.{cat}"].append(score)
        for issue in (fp.get("quality_issues") or []):
            issue_categories[issue.get("category", "unknown")] += 1
            issue_scopes[issue.get("scope", "unknown")] += 1

    print("\n=== Mean scores per category ===")
    for cat, scores in sorted(breakdown_sums.items()):
        if scores:
            print(f"  {cat}: mean={sum(scores)/len(scores):.1f}, min={min(scores)}, max={max(scores)}, n={len(scores)}")

    print("\n=== Most-flagged issue categories (Top 10) ===")
    for cat, cnt in issue_categories.most_common(10):
        print(f"  {cat}: {cnt}")

    print("\n=== Most-flagged scopes (Top 5) ===")
    for scope, cnt in issue_scopes.most_common(5):
        print(f"  {scope}: {cnt}")

    print("\n=== Recommendation ===")
    print("Look at the lowest-mean category AND the most-flagged issue category.")
    print("Top 2 results = candidates for Few-shot example additions in prompts_news_pipeline.py.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 1.3: Script 실행**
```bash
cd c:/Users/amy/Desktop/0to1log/backend && ./.venv/Scripts/python.exe scripts/measure_prompt_failures.py 2>&1 | tee /tmp/measurement_output.txt
```

Expected: 출력에 "Sample size: N", category별 mean score, issue category Top 10이 표시됨.

- [ ] **Step 1.4: 결과를 vault 문서로 기록**

`vault/09-Implementation/plans/2026-04-15-news-pipeline-failure-measurement.md` 생성:
```markdown
---
title: News Pipeline Prompt Failure Measurement
date: 2026-04-16
parent_spec: 2026-04-15-news-pipeline-hardening-design.md
parent_plan: 2026-04-15-news-pipeline-hardening-phase2-plan.md
---

# 측정 결과 (지난 14일)

## Sample
- 총 digest 수:
- auto_publish_eligible=true 비율:

## Score 분포
[script 출력 paste]

## Per-category 평균 점수
[script 출력 paste]

## 가장 자주 flagged된 issue category Top 10
[script 출력 paste]

## Few-shot 타겟 결정

기준: 평균 점수가 낮으면서(약점 영역) 동시에 issue 빈도가 높은 카테고리.

**Top 2 (Few-shot 추가 대상):**
1. [예: `frontload + overclaim` — mean 89, 12회 flag]
2. [예: `learner_body + accessibility` — mean 88, 8회 flag]

각 타겟의 prompts_news_pipeline.py 위치:
1. [어느 prompt에 추가할지]
2. [어느 prompt에 추가할지]
```

- [ ] **Step 1.5: Commit measurement**
```bash
cd c:/Users/amy/Desktop/0to1log
git add backend/scripts/measure_prompt_failures.py vault/09-Implementation/plans/2026-04-15-news-pipeline-failure-measurement.md
git commit -m "feat(scripts): add prompt failure measurement + record 14-day baseline"
```

---

## Chunk 2: URL Strict Allowlist (Task 2)

**기간**: 1일. **목적**: LLM이 fact_pack 밖 URL을 인용하지 못하게 구조적 차단.

### Task 2: validate_citation_urls function

**Files:**
- Modify: `backend/services/pipeline_quality.py` (add new function)
- Modify: `backend/tests/test_pipeline_quality_scoring.py` (add tests)

- [ ] **Step 2.1: 실패하는 unit test 작성 (TDD)**

`backend/tests/test_pipeline_quality_scoring.py` 끝에 추가:

```python
# ---------------------------------------------------------------------------
# Phase 2 — URL Strict Allowlist Validation
# ---------------------------------------------------------------------------

class TestValidateCitationUrls:
    """Verify URL strict allowlist validation against fact_pack.news_items."""

    def test_all_citations_in_fact_pack_passes(self):
        from services.pipeline_quality import validate_citation_urls
        body = "Some content. [1](https://example.com/a)\n\nMore. [2](https://example.com/b)"
        fact_pack = {"news_items": [
            {"url": "https://example.com/a", "title": "A"},
            {"url": "https://example.com/b", "title": "B"},
        ]}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is True
        assert result["unknown_urls"] == []

    def test_unknown_url_fails(self):
        from services.pipeline_quality import validate_citation_urls
        body = "Cited [1](https://hallucinated.example.com/fake)."
        fact_pack = {"news_items": [{"url": "https://example.com/real", "title": "R"}]}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is False
        assert "https://hallucinated.example.com/fake" in result["unknown_urls"]

    def test_zero_citations_passes(self):
        """Sections like One-Line Summary may have no citations — must pass."""
        from services.pipeline_quality import validate_citation_urls
        body = "Just a summary, no citations.\n\n## Section\n\nMore prose."
        fact_pack = {"news_items": [{"url": "https://example.com/a", "title": "A"}]}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is True
        assert result["unknown_urls"] == []
        assert result["citation_count"] == 0

    def test_url_normalization_strips_tracking_params(self):
        """utm_*, fbclid, ref params should normalize away before comparing."""
        from services.pipeline_quality import validate_citation_urls
        body = "Cited [1](https://example.com/a?utm_source=twitter&utm_medium=social)."
        fact_pack = {"news_items": [{"url": "https://example.com/a", "title": "A"}]}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is True

    def test_url_normalization_strips_trailing_slash(self):
        from services.pipeline_quality import validate_citation_urls
        body = "Cited [1](https://example.com/a/)."
        fact_pack = {"news_items": [{"url": "https://example.com/a", "title": "A"}]}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is True

    def test_url_normalization_strips_fragment(self):
        from services.pipeline_quality import validate_citation_urls
        body = "Cited [1](https://example.com/a#section-2)."
        fact_pack = {"news_items": [{"url": "https://example.com/a", "title": "A"}]}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is True

    def test_duplicate_citations_deduped(self):
        """Same URL cited multiple times = 1 unique URL to validate."""
        from services.pipeline_quality import validate_citation_urls
        body = "First [1](https://example.com/a). Second [1](https://example.com/a)."
        fact_pack = {"news_items": [{"url": "https://example.com/a", "title": "A"}]}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is True
        assert result["citation_count"] == 1

    def test_empty_fact_pack_with_citations_fails(self):
        from services.pipeline_quality import validate_citation_urls
        body = "Cited [1](https://example.com/a)."
        fact_pack = {"news_items": []}
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is False
        assert "https://example.com/a" in result["unknown_urls"]

    def test_missing_news_items_field_treated_as_empty(self):
        from services.pipeline_quality import validate_citation_urls
        body = "Cited [1](https://example.com/a)."
        fact_pack = {}  # no news_items key
        result = validate_citation_urls(body, fact_pack)
        assert result["valid"] is False
```

- [ ] **Step 2.2: Run tests — 모두 fail 확인**
```bash
cd c:/Users/amy/Desktop/0to1log/backend && ./.venv/Scripts/python.exe -m pytest tests/test_pipeline_quality_scoring.py::TestValidateCitationUrls -v
```
Expected: 9 FAILED with `ImportError: cannot import name 'validate_citation_urls'` 또는 `AttributeError`

- [ ] **Step 2.3: Implement validate_citation_urls**

**Imports — top-of-file**: `pipeline_quality.py` already has `import re` (around line 17). Add this to the top-of-file imports alongside it:
```python
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
```
**Do NOT use `re as _re` aliasing** (existing file uses `re` directly). Mid-file imports trigger ruff E402.

Then add this code section in `pipeline_quality.py` AFTER the existing functions (e.g., after `_check_structural_penalties`, near end of file before any module-level constants):

```python
# ---------------------------------------------------------------------------
# Phase 2 — URL Strict Allowlist Validation
# ---------------------------------------------------------------------------

# Citation pattern: [N](URL) where N is digits and URL starts with http
_CITATION_RE = re.compile(r"\[(\d+)\]\((https?://[^\s\)]+)\)")

# Tracking params to strip during URL normalization
_TRACKING_PARAM_PREFIXES = ("utm_",)
_TRACKING_PARAM_NAMES = frozenset({
    "fbclid", "gclid", "msclkid", "ref", "referrer", "source",
    "share", "share_id", "src", "feature", "campaign",
})


def _normalize_url(url: str) -> str:
    """Normalize URL for citation comparison: scheme, trailing slash, tracking params, fragment."""
    try:
        parsed = urlparse(url.strip())
    except (ValueError, AttributeError):
        return url
    # NOTE: re-imports for safety (no _re alias — file already imports `re`)

    # Force https for comparison (treat http and https as same)
    scheme = "https" if parsed.scheme in ("http", "https") else parsed.scheme

    # Strip trailing slash from path
    path = parsed.path.rstrip("/") or "/"

    # Filter query params: drop tracking
    query_params = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not k.lower().startswith(_TRACKING_PARAM_PREFIXES)
        and k.lower() not in _TRACKING_PARAM_NAMES
    ]
    query = urlencode(query_params)

    # Drop fragment
    fragment = ""

    return urlunparse((scheme, parsed.netloc.lower(), path, parsed.params, query, fragment))


def validate_citation_urls(body: str, fact_pack: dict) -> dict:
    """Verify all [N](URL) citations in body refer to URLs in fact_pack.news_items.

    Returns dict with:
      - valid: bool
      - unknown_urls: list[str] — citations that don't match any allowed URL
      - citation_count: int — number of unique URLs cited (after dedup)
      - allowed_count: int — number of URLs in fact_pack.news_items

    Bodies with zero citations always pass (e.g., One-Line Summary section).
    URL comparison is normalized: scheme/trailing-slash/tracking-params/fragment stripped.
    """
    if not body:
        return {"valid": True, "unknown_urls": [], "citation_count": 0, "allowed_count": 0}

    # Build allowed set from fact_pack.news_items[*].url
    news_items = (fact_pack or {}).get("news_items") or []
    allowed = {
        _normalize_url(item["url"])
        for item in news_items
        if isinstance(item, dict) and item.get("url")
    }

    # Extract all citations and dedup by normalized URL
    cited_raw = [m.group(2) for m in _CITATION_RE.finditer(body)]
    cited_norm = {_normalize_url(u) for u in cited_raw}

    if not cited_norm:
        return {"valid": True, "unknown_urls": [], "citation_count": 0, "allowed_count": len(allowed)}

    unknown = sorted(cited_norm - allowed)
    return {
        "valid": len(unknown) == 0,
        "unknown_urls": unknown,
        "citation_count": len(cited_norm),
        "allowed_count": len(allowed),
    }
```

**Note**: 위 코드는 `re`를 이미 모듈에서 import한 상태로 가정한다. 만약 어떤 이유로 `import re`가 빠져 있으면 추가 (Phase 1 작업으로 들어왔을 가능성 높음 — 검증).

- [ ] **Step 2.4: Run tests — 모두 pass 확인**
```bash
cd c:/Users/amy/Desktop/0to1log/backend && ./.venv/Scripts/python.exe -m pytest tests/test_pipeline_quality_scoring.py::TestValidateCitationUrls -v
```
Expected: 9 PASSED

- [ ] **Step 2.5: Full test suite**
```bash
cd c:/Users/amy/Desktop/0to1log/backend && ./.venv/Scripts/python.exe -m pytest tests/ --tb=no -q 2>&1 | tail -5
```
Expected: `9 failed, 150 passed` (141 baseline + 9 new — confirm 새 테스트가 9개 추가됐다)

- [ ] **Step 2.6: Commit unit tests + function**
```bash
git add backend/services/pipeline_quality.py backend/tests/test_pipeline_quality_scoring.py
git commit -m "feat(quality): add validate_citation_urls() with URL normalization (strict allowlist)"
```

### Task 3: Integrate validate_citation_urls into _check_digest_quality flow

**Files:**
- Modify: `backend/services/pipeline_quality.py` (modify `_check_digest_quality`)
- Modify: `backend/tests/test_pipeline_quality_scoring.py` (add integration test)

- [ ] **Step 3.1: Read current _check_digest_quality structure**

3개 명령어로 통합 지점을 정확히 파악:
```bash
cd c:/Users/amy/Desktop/0to1log/backend
# (a) 함수 시그니처 + 본문 첫 50줄
grep -n "async def _check_digest_quality" services/pipeline_quality.py
# (b) quality_meta dict 또는 return 객체가 어떻게 빌드되는지
grep -n "quality_meta\|quality_breakdown\|auto_publish_eligible" services/pipeline_quality.py
# (c) 함수 인자에서 personas/classified가 어떻게 들어오는지 (fact_pack 구성 데이터 source)
grep -n "personas\|classified\|primary_url" services/pipeline_quality.py | head -20
```
**판단 포인트:**
- `_check_digest_quality()`의 return값이 dict인지 PersonaOutput인지 확인 (fact_pack가 여기서 만들어지는지, caller에서 만들어지는지)
- personas 인자의 타입 (`dict[str, PersonaOutput]`로 추정 — Phase 1 분리 시 확인됨)
- fact_pack의 `news_items[*].url`은 `classified` 인자에서 group → group.primary_url 형태로 나올 가능성 높음 (ranking.py의 ClassifiedGroup 모델 확인)

- [ ] **Step 3.2: Integration test 작성**

`tests/test_pipeline_quality_scoring.py`의 기존 `test_check_digest_quality` 함수 (L131 근처) 패턴을 그대로 따라간다. 그 테스트가 어떻게 mock하는지(LLM 호출, supabase 호출 등)를 먼저 읽고 같은 패턴으로:

```python
@pytest.mark.asyncio
async def test_check_digest_quality_url_validation_failure_marks_ineligible(monkeypatch):
    """Integration: hallucinated URL in body causes auto_publish_eligible=False."""
    from services.pipeline_quality import _check_digest_quality
    from models.news_pipeline import PersonaOutput, ClassifiedGroup, ClassifiedCandidate
    from unittest.mock import AsyncMock, MagicMock

    # 1. ClassifiedGroup with KNOWN URL (this is what becomes fact_pack.news_items)
    known_url = "https://known-source.example.com/article"
    group = ClassifiedGroup(
        group_title="Test article",
        primary_url=known_url,
        items=[ClassifiedCandidate(url=known_url, title="Test", subcategory="big_tech", reason="test", score=80)],
        subcategory="big_tech",
        urls=[known_url],
    )

    # 2. PersonaOutput with body that cites an UNKNOWN (hallucinated) URL
    bad_url = "https://hallucinated.example.com/fake"
    body = f"## One-Line Summary\nThis is fake. [1]({bad_url})\n"
    personas = {
        "expert": PersonaOutput(en=body, ko=body),
        "learner": PersonaOutput(en=body, ko=body),
    }

    # 3. Mock LLM judge call (existing test pattern shows how — replicate)
    # Most likely: monkeypatch.setattr(<openai client method>, AsyncMock(return_value=...))
    # The existing test_check_digest_quality_* tests in this file have the exact pattern.

    # 4. Mock supabase + run_id + cumulative_usage as the existing test does

    # 5. Call _check_digest_quality and assert
    result = await _check_digest_quality(
        personas=personas,
        digest_type="business",
        classified=[group],
        community_summary_map={},
        supabase=MagicMock(),  # or AsyncMock as existing pattern dictates
        run_id="test-run",
        cumulative_usage={},
    )

    # quality_meta dict should have url_validation_failed=True, auto_publish_eligible=False
    if isinstance(result, dict):
        assert result.get("url_validation_failed") is True
        assert result.get("auto_publish_eligible") is False
        assert any(bad_url in str(f) for f in result.get("url_validation_failures", []))
```

⚠️ **Implementer**: 이 test는 기존 `test_check_digest_quality_*` 패턴을 정확히 카피해야 mock이 맞는다. **Step 3.1의 grep 결과를 보고 정확한 시그니처/mock 패턴 파악 후 위 outline을 채워라.** Skip 하지 말 것 — spec §5.2 Done criteria가 명시적으로 요구하는 음성 케이스 통합 테스트.

- [ ] **Step 3.3: 통합 지점 추가 — minimal version**

`_check_digest_quality()` 함수 내부에서 score 계산이 끝나고 `quality_meta` (또는 반환 dict) 만들 때, **personas의 각 본문에 대해 validate_citation_urls 호출 → 실패 시 `auto_publish_eligible=False` 강제 + 플래그 기록**.

Pseudo-patch:
```python
# _check_digest_quality() 내부, return 직전 어딘가에:

# Phase 2 — URL strict allowlist validation
url_validation_failures = []
fact_pack_for_validation = {"news_items": [...]}  # build from classified groups

for persona_name, persona_output in personas.items():
    for locale, content in (("en", persona_output.en), ("ko", persona_output.ko)):
        result = validate_citation_urls(content, fact_pack_for_validation)
        if not result["valid"]:
            url_validation_failures.append({
                "persona": persona_name,
                "locale": locale,
                "unknown_urls": result["unknown_urls"],
                "citation_count": result["citation_count"],
            })

if url_validation_failures:
    logger.warning(
        "URL validation failed for digest %s: %d persona/locale pairs with unknown URLs",
        digest_type, len(url_validation_failures),
    )
    # Force ineligible
    quality_meta["url_validation_failed"] = True
    quality_meta["url_validation_failures"] = url_validation_failures
    quality_meta["auto_publish_eligible"] = False
else:
    quality_meta["url_validation_failed"] = False
```

⚠️ **CAUTION**: Implementer subagent는 `_check_digest_quality`의 actual 시그니처 + return 구조를 먼저 읽고, fact_pack을 구성하는 정확한 데이터 소스(아마 `classified` 인자에서 group → group.primary_url 또는 비슷한 패턴)를 식별 후 patch 적용. 위 pseudo는 의도만.

- [ ] **Step 3.4: Run quality tests**
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/test_pipeline_quality_scoring.py -v 2>&1 | tail -20
```
Expected: 모든 기존 테스트 + 새 테스트 PASS

- [ ] **Step 3.5: Full suite**
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/ --tb=no -q 2>&1 | tail -5
```
Expected: `9 failed, 150 passed` (또는 +1 if integration test added beyond skip)

- [ ] **Step 3.6: Ruff**
```bash
cd backend && ./.venv/Scripts/ruff.exe check services/pipeline_quality.py
```

- [ ] **Step 3.7: Commit integration**
```bash
git add backend/services/pipeline_quality.py backend/tests/test_pipeline_quality_scoring.py
git commit -m "feat(quality): integrate URL validation into _check_digest_quality, force draft on failure"
```

---

## Chunk 3: Research Domain Priority/Blocklist (Task 2.5)

**기간**: 반나절. **목적**: 2026-04-16 발견 — research source의 47% SEO-spam 도메인 차단.

### Task 4: Migration + seed data

**Files:**
- Create: `supabase/migrations/00051_research_domain_filters.sql`

- [ ] **Step 4.1: Migration 파일 작성**

`supabase/migrations/00051_research_domain_filters.sql`:
```sql
-- 00051_research_domain_filters.sql
-- Extend news_domain_filters with research_priority + research_blocklist
-- (Phase 2 of news-pipeline-hardening, 2026-04-16)
-- Background: 2026-04-16 production digest had 8/17 research source_urls
-- in low-quality/SEO-spam domains. This migration adds two new filter_types
-- to address source quality at collection/ranking time.

-- 1. Drop the existing CHECK constraint, recreate with 5 allowed types
alter table public.news_domain_filters
  drop constraint if exists news_domain_filters_filter_type_check;

alter table public.news_domain_filters
  add constraint news_domain_filters_filter_type_check
  check (filter_type in (
    'block_non_en',
    'official_priority',
    'media_tier',
    'research_priority',
    'research_blocklist'
  ));

-- 2. Seed research_priority — high-quality research sources
insert into public.news_domain_filters (domain, filter_type, notes) values
  ('arxiv.org', 'research_priority', 'arXiv preprints'),
  ('huggingface.co', 'research_priority', 'Hugging Face models/papers'),
  ('openreview.net', 'research_priority', 'OpenReview peer review'),
  ('paperswithcode.com', 'research_priority', 'Papers with Code'),
  ('aclanthology.org', 'research_priority', 'ACL Anthology'),
  ('proceedings.mlr.press', 'research_priority', 'PMLR conference proceedings'),
  ('proceedings.neurips.cc', 'research_priority', 'NeurIPS proceedings'),
  ('distill.pub', 'research_priority', 'Distill ML research articles'),
  ('ai.googleblog.com', 'research_priority', 'Google AI blog'),
  ('research.googleblog.com', 'research_priority', 'Google Research blog'),
  ('deepmind.google', 'research_priority', 'DeepMind research'),
  ('ai.meta.com', 'research_priority', 'Meta AI research'),
  ('machinelearning.apple.com', 'research_priority', 'Apple ML research'),
  ('research.microsoft.com', 'research_priority', 'Microsoft Research'),
  ('arxiv-vanity.com', 'research_priority', 'arXiv reformatted')
on conflict (domain) do nothing;

-- 3. Seed research_blocklist — domains observed producing low-quality research source_urls
--    (from 2026-04-16 production digest analysis)
insert into public.news_domain_filters (domain, filter_type, notes) values
  ('agent-wars.com', 'research_blocklist', '2026-04-16: low-tier rewrite/aggregator'),
  ('lilting.ch', 'research_blocklist', '2026-04-16: low-tier blog'),
  ('geektak.com', 'research_blocklist', '2026-04-16: SEO content farm'),
  ('areeblog.com', 'research_blocklist', '2026-04-16: SEO blog'),
  ('gist.science', 'research_blocklist', '2026-04-16: paper summary aggregator'),
  ('inbriefly.in', 'research_blocklist', '2026-04-16: SEO content farm'),
  ('ranksquire.com', 'research_blocklist', '2026-04-16: SEO content farm'),
  ('hongqinlab.blogspot.com', 'research_blocklist', '2026-04-16: low-tier personal blog')
on conflict (domain) do nothing;
```

- [ ] **Step 4.2: Apply migration**

Use Supabase MCP `apply_migration` tool with the SQL above OR run via SQL editor. Verify with:
```sql
select filter_type, count(*)
from public.news_domain_filters
group by filter_type
order by filter_type;
```
Expected: block_non_en=12, media_tier=9, official_priority=8, research_blocklist=8, research_priority=15

- [ ] **Step 4.3: Cache invalidation note**

⚠️ **Important**: `_load_domain_filters()` uses `lru_cache` — Railway 재시작 전까지 새 도메인 안 보임. Production 적용 후 Railway re-deploy 필요. 로컬에선 프로세스 재시작.

- [ ] **Step 4.4: Commit migration**
```bash
git add supabase/migrations/00051_research_domain_filters.sql
git commit -m "feat(db): extend news_domain_filters with research_priority/research_blocklist"
```

### Task 5: Use research filters in _classify_source_meta

**Files:**
- Modify: `backend/services/news_collection.py` (modify `_classify_source_meta`)
- Modify: `backend/tests/test_news_collection.py` (add tests)

- [ ] **Step 5.1: Failing tests 작성**

`tests/test_news_collection.py` 끝에:
```python
def test_classify_source_meta_research_blocklist_returns_spam_tier():
    """Domains in research_blocklist should be marked source_kind='spam', source_tier='spam'."""
    from services.news_collection import _classify_source_meta, _load_domain_filters
    _load_domain_filters.cache_clear()
    # Pre-condition: agent-wars.com seeded in research_blocklist (migration 00051)
    result = _classify_source_meta("https://agent-wars.com/some/article", title="x")
    assert result["source_tier"] == "spam"
    assert result["source_kind"] == "spam"
    assert result["source_confidence"] == "low"


def test_classify_source_meta_research_priority_returns_primary_tier():
    """Research priority domains should be marked primary tier with high confidence."""
    from services.news_collection import _classify_source_meta, _load_domain_filters
    _load_domain_filters.cache_clear()
    # arxiv.org already returns primary in existing logic, so use a NEW priority domain
    result = _classify_source_meta("https://openreview.net/forum?id=abc123", title="paper")
    assert result["source_tier"] == "primary"
    assert result["source_confidence"] == "high"
```

- [ ] **Step 5.2: Run tests — fail expected**
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/test_news_collection.py::test_classify_source_meta_research_blocklist_returns_spam_tier tests/test_news_collection.py::test_classify_source_meta_research_priority_returns_primary_tier -v
```
Expected: FAIL (current logic doesn't handle these)

- [ ] **Step 5.3: Modify _classify_source_meta**

`backend/services/news_collection.py`의 `_classify_source_meta()` 함수.

**위치 — 명확히**: 두 새 분기는 **hostname 결정 직후 + 어떤 tier 체크보다도 앞**에 배치한다. 즉 현재 L118 `if not hostname:` 체크 직후, L125 `if "arxiv.org" in hostname:` 보다 먼저. 그렇지 않으면 blocklist 도메인이 다른 priority 분기에 매치되어 leak할 수 있다.

```python
# 함수 본문, "if not hostname:" 블록 바로 다음, 그러나 다른 모든 tier/priority 체크보다 먼저:

filters = _load_domain_filters()

# Phase 2 — research_blocklist HIGHEST priority (kill source before any other tier check)
if any(d in hostname for d in filters.get("research_blocklist", frozenset())):
    return {
        "source_kind": "spam",
        "source_confidence": "low",
        "source_tier": "spam",
    }

# Phase 2 — research_priority next, before existing tier classification
if any(d in hostname for d in filters.get("research_priority", frozenset())):
    return {
        "source_kind": "research_primary",
        "source_confidence": "high",
        "source_tier": "primary",
    }
```

- [ ] **Step 5.4: Run tests — pass expected**
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/test_news_collection.py -v 2>&1 | tail -20
```
Expected: New tests PASS, no regression in existing.

- [ ] **Step 5.5: Commit classify changes**
```bash
git add backend/services/news_collection.py backend/tests/test_news_collection.py
git commit -m "feat(news): classify research_blocklist as spam tier, research_priority as primary"
```

### Task 6: Filter out spam-tier sources from collect/rank

**Files:**
- Modify: `backend/services/news_collection.py` (filter in `collect_news` or `enrich_sources`)

- [ ] **Step 6.1: NewsCandidate 모델 확인 — source_tier 필드가 있는가?**

```bash
cd backend && grep -n "source_tier\|class NewsCandidate" models/news_pipeline.py
```

만약 `NewsCandidate` model에 `source_tier` 필드가 없다면, source_tier는 모델이 아닌 **classification meta dict** (`_classify_source_meta` 반환값)에서만 존재한다. 이 경우 Step 6.2의 패치 위치는 **enrichment 단계에서 NewsCandidate가 만들어지는 직후, classification meta를 받아서 dict로 들고 있는 곳**이 된다.

- [ ] **Step 6.2: 결정 — drop in collect or rank?**

옵션 A: `collect_news()` 또는 `_collect_tavily()`에서 spam tier 도메인을 결과에서 제외
- Pro: 가장 이른 단계, 모든 후속 단계가 깨끗한 데이터
- Con: 다른 카테고리(business)에는 영향 없을지 검증 필요

옵션 B: ranking.py의 `classify_candidates()` 또는 `merge_classified()`에서 spam을 제외
- Pro: 카테고리 인식
- Con: 늦은 단계, 더 많은 처리 비용

→ **추천: 옵션 A** — research_blocklist는 정의상 어느 카테고리에든 spam이므로 일찍 제외하는 게 맞음.

- [ ] **Step 6.3: Implement filter in collect path**

전제: Step 6.1에서 `NewsCandidate.source_tier` 존재 여부 확인됨.

**Case A** — `source_tier`가 NewsCandidate field로 존재:
```python
# 각 collector(_collect_tavily/_collect_hf_papers/등) 결과 처리에서:
filtered = []
for candidate in results:
    if candidate.source_tier == "spam":
        logger.info("Dropping spam-tier source: %s", candidate.url)
        continue
    filtered.append(candidate)
return filtered
```

**Case B** — `source_tier`는 별도 dict에서만 존재 (NewsCandidate field 아님):
```python
# enrich_sources 또는 _classify_source_meta 호출 직후에:
meta = _classify_source_meta(url, source=collector_name, title=title)
if meta.get("source_tier") == "spam":
    logger.info("Dropping spam-tier source: %s", url)
    continue
# 그 다음 NewsCandidate 만들기
```

⚠️ **Implementer**: Step 6.1 결과로 Case A vs B 결정. enrich_sources 함수(L852)가 가장 자연스러운 통합 지점일 가능성 높음.

- [ ] **Step 6.4: Verify no regression**
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/ --tb=no -q 2>&1 | tail -5
```
Expected: `9 failed, 152 passed` (141 baseline + 9 URL + 2 classify research)

- [ ] **Step 6.4: Commit filter**
```bash
git add backend/services/news_collection.py
git commit -m "feat(news): drop spam-tier candidates at collection time"
```

---

## Chunk 4: Few-shot additions (Task 3)

**기간**: 반나절. **목적**: Chunk 1 측정 결과 Top 2 프롬프트에 좋은/나쁜 예시 한 쌍씩.

### Task 7: Add Few-shot to Top 2 prompts

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` (add example strings to identified prompts)

- [ ] **Step 7.1: Read measurement results**

`vault/09-Implementation/plans/2026-04-15-news-pipeline-failure-measurement.md`에서 식별된 Top 2 프롬프트를 읽는다.

⚠️ **Implementer NOTE**: 이 step은 Chunk 1 결과에 의존한다. 측정 결과 없이 어떤 프롬프트에 추가할지 결정하지 말 것. 만약 측정 결과가 모호하면 (Top 1만 명확) 1개만 추가하고 마무리.

- [ ] **Step 7.2: 각 타겟 프롬프트에 Few-shot 한 쌍 추가**

원칙:
- "좋은 예 1개 + 나쁜 예 1개" 한 쌍만
- 각 30-50 토큰
- 프롬프트당 +80~100 토큰 이내
- 프롬프트 system 부분 끝에 배치 (정적/동적 분리 일관성)
- 명확한 헤더로 구분: `## Examples`

예시 패턴 (실제 측정 결과에 맞춰 조정):

만약 Top 1이 `headline_ko` (직역 문제):
```python
# In _build_persona_system_prompt or wherever headline_ko rule is:

prompt += """

## Examples — headline_ko

✅ Good (자연스러운 의역):
EN: "OpenAI commits $50B Trainium capacity in landmark Amazon deal"
KO: "OpenAI–Amazon, 트레이니움 500억 달러 약정으로 클라우드 동맹 강화"

❌ Bad (직역, 어색함):
EN: "OpenAI commits $50B Trainium capacity in landmark Amazon deal"
KO: "OpenAI는 획기적인 아마존 거래에서 500억 달러 트레이니움 용량을 약정합니다"
"""
```

만약 Top 1이 `frontload + overclaim` (과장 문제):
```python
prompt += """

## Examples — frontload phrasing

✅ Good (사실 기반):
"Meta가 1GW Broadcom 파트너십을 발표했다."
"이 협상은 Meta의 GPU 의존도를 낮추려는 시도로 보인다."

❌ Bad (과장):
"Meta가 GPU 시장의 판도를 바꿀 1GW 거래를 성사시켰다."
"이 발표는 NVIDIA 시대의 종말을 알린다."
"""
```

- [ ] **Step 7.3: 토큰 증가량 측정**

대략적 추정: 1 토큰 ≈ 4 영문자 ≈ 2 한글자. Few-shot 추가 후 프롬프트 문자열 길이를 grep + wc -c로 측정해 +100 토큰 이내 확인.

```bash
# Before/after diff에서 추가된 라인 수 확인
git diff backend/services/agents/prompts_news_pipeline.py | grep "^+" | wc -c
```

- [ ] **Step 7.4: Run tests**
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/test_news_digest_prompts.py -v 2>&1 | tail -20
```
Expected: 모든 prompt 테스트 PASS (Few-shot 추가만으로는 회귀 안 남)

- [ ] **Step 7.5: Commit Few-shot**
```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "feat(prompts): add Few-shot examples to Top 2 prompts (measurement-driven)"
```

---

## Chunk 5: Final Verification & Deployment

### Task 8: Full regression + ruff

- [ ] **Step 8.1: Full pytest**
```bash
cd c:/Users/amy/Desktop/0to1log/backend && ./.venv/Scripts/python.exe -m pytest tests/ --tb=no -q 2>&1 | tail -10
```
Expected: 9 baseline failures unchanged. Pass count = 141 + 9 (URL tests) + 2 (research filter tests) + any integration tests added = ~152.

- [ ] **Step 8.2: Ruff all touched files**
```bash
cd backend && ./.venv/Scripts/ruff.exe check services/pipeline_quality.py services/news_collection.py services/agents/prompts_news_pipeline.py scripts/measure_prompt_failures.py
```
Expected: clean

- [ ] **Step 8.3: Backward compat check**
```bash
cd backend && ./.venv/Scripts/python.exe -c "
from services.pipeline_quality import _check_digest_quality, validate_citation_urls
from services.news_collection import _classify_source_meta, _load_domain_filters
print('Phase 2 imports OK')
"
```

### Task 9: Push + Railway deploy

- [ ] **Step 9.1: Confirm clean tree**
```bash
cd c:/Users/amy/Desktop/0to1log && git status --short | grep -v "tmp-\|^??"
```
Expected: empty (or pre-existing M docs/08_Handbook.md only)

- [ ] **Step 9.2: List Phase 2 commits**
```bash
git log --oneline 083bc95..HEAD
```
Expected: ~7-9 commits from Chunks 1-4.

- [ ] **Step 9.3: Push**
```bash
git push origin main
```

- [ ] **Step 9.4: Wait for Railway redeploy** (3-5 min)
- Verify Railway dashboard build success
- Health check: `curl https://<railway-domain>/health`

### Task 10: Production verification

- [ ] **Step 10.1: Trigger rerun via admin or wait for cron**
```bash
# Option A: manual rerun via admin dashboard /admin/news/
# Option B: wait for daily cron (KST morning)
```

- [ ] **Step 10.1b: Find latest batch_id**
```sql
select distinct pipeline_batch_id, max(created_at) as latest
from news_posts
where created_at > now() - interval '24 hours'
group by pipeline_batch_id
order by latest desc limit 5;
```
→ pick the batch_id you just generated, substitute below as `<BATCH>`.

- [ ] **Step 10.2: Verify URL validation runs (look for new flag in fact_pack)**
```sql
select id, slug, post_type,
       (fact_pack->>'url_validation_failed')::boolean as url_failed,
       fact_pack->'url_validation_failures' as failures
from news_posts
where pipeline_batch_id = '<BATCH>'
order by post_type, locale;
```
Expected: `url_failed` 컬럼이 false (또는 true with failures recorded). Either is fine — we want to see the FIELD exist.

- [ ] **Step 10.3: Verify research blocklist works**
```sql
-- Are blocklisted domains absent from new research source_urls?
select unnest(source_urls) as url
from news_posts
where pipeline_batch_id = '<BATCH>' and post_type = 'research'
order by url;
```
Expected: 0 hits for `agent-wars.com`, `lilting.ch`, `geektak.com`, `areeblog.com`, `gist.science`, `inbriefly.in`, `ranksquire.com`, `hongqinlab.blogspot.com`

- [ ] **Step 10.4: Update design.md Evidence section**

`vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-design.md`의 Phase 2 Evidence 섹션에 commit hashes + cron run_id + measurement summary 기록.

- [ ] **Step 10.5: Final commit**
```bash
git add vault/09-Implementation/plans/2026-04-15-news-pipeline-hardening-design.md
git commit -m "docs(plans): record Phase 2 evidence — URL allowlist + research filters + Few-shot live"
git push origin main
```

---

## Done Criteria Checklist (spec §5.2 mapping)

- [ ] Retroactive 측정 결과 기록 (Task 1)
- [ ] `validate_citation_urls()` 함수 + 9개 unit tests (Task 2)
- [ ] 음성 통합 테스트: 가짜 URL → `auto_publish_eligible=false` (Task 3)
- [ ] Daily cron 1회에서 URL 검증 실행 + 통과 (Task 10.2)
- [ ] Few-shot Top 2 프롬프트 추가, 토큰 ≤100/프롬프트 증가 (Task 7)
- [ ] Few-shot 후 daily cron 1회 품질 점수 회귀 없음 (Task 10)
- [ ] `news_domain_filters`에 research_priority + research_blocklist seed (Task 4)
- [ ] `_classify_source_meta` 활용 + spam 제외 (Tasks 5-6)
- [ ] 다음 daily cron의 research source_urls에서 blocklist 0건 (Task 10.3)

---

## Risks & Pitfalls

1. **`fact_pack.news_items[*].url`이 spec와 다른 필드명**. Plan에서는 정확한 필드 사용했으나, implementer가 spec를 그대로 보고 `fact_pack.sources` 찾으면 fail. 이 plan의 Critical Constraints §2 강조.

2. **URL validation false positive 운영 폭주**. Strict allowlist가 너무 엄격해서 정당한 인용도 탈락하면 매일 모든 digest가 draft에 갇힘. **Mitigation**: 첫 production 배포 후 24시간 모니터링. 만약 실제 운영에서 false positive율 > 10%면 normalization 규칙 재검토.

3. **`lru_cache` 캐시 무효화** — 새 research_priority/blocklist 도메인 추가 시 Railway 재시작 필요. design.md §10 Risk #4와 동일.

4. **Few-shot이 토큰 한도 초과** — 측정 결과로 결정하지만, 예시가 너무 길어지면 Phase 3의 토큰 다이어트와 충돌. Step 7.3에서 +100 토큰 이내 확인 필수.

5. **Research blocklist의 over-block** — 8개 SEO-spam 외에도 비슷한 도메인이 더 있을 수 있음. Phase 2 후 1-2주 모니터링 필요. 새 spam 발견 시 SQL UPDATE로 즉시 추가 (코드 배포 불필요).

6. **classify_candidates와의 인터랙션** — research_blocklist를 collect 단계에서 drop하면 ranking은 깨끗한 데이터를 받지만, 만약 blocklist 도메인이 어떤 이유로 ranking까지 새어나가면 어떻게 처리되는가? 일관성을 위해 ranking에도 spam tier 무시 로직 가능. Phase 2 첫 배포 후 모니터링하고 필요 시 보강.

---

## Estimated Total Effort
- Chunk 1 (measurement): 반나절
- Chunk 2 (URL validation): 1일
- Chunk 3 (research filters): 반나절
- Chunk 4 (Few-shot): 반나절
- Chunk 5 (verification + deploy): 반나절

**Total: 2.5~3.5일**
