# rerun_from=quality Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `rerun_from=quality` option so QC prompts can be rescored against an existing daily digest without re-running the expensive gpt-5 writer stage (~$0.54 → ~$0.05, 10x cost reduction).

**Architecture:** Add `"quality"` key to STAGE_CASCADE (only deletes quality/save/summary logs). In `rerun_pipeline_stage()`, when `from_stage="quality"`, load `PersonaOutput` (EN+KO content) and frontload directly from the existing `news_posts` rows instead of re-running `_generate_digest`. Call `_check_digest_quality` on the loaded content and update the same rows with fresh `quality_score`, `quality_flags`, and `content_analysis`. Admin endpoint accepts the new stage; admin UI exposes a new button.

**Tech Stack:** Python 3.11, FastAPI, Supabase, Astro v5 (admin UI).

**Spec:** None — this is a small, well-scoped optimization following an observed pain point (Apr 19 had 2 reruns × $0.55 each = $1.10 wasted on unchanged content).

**Prerequisite context for implementer:**
- `_check_digest_quality()` signature (in `services/pipeline_quality.py`): takes `personas: dict[str, PersonaOutput]`, `digest_type`, `classified`, `community_summary_map`, `supabase`, `run_id`, `cumulative_usage`, `frontload`. Returns a dict with `score`/`quality_score`/`quality_flags`/`quality_issues`/`quality_breakdown` keys.
- `PersonaOutput` (in `models/news_pipeline.py`): simple `{en: str, ko: str}` pydantic model.
- `_load_checkpoint(supabase, run_id, stage)` (in `services/pipeline.py`): returns the `data` dict stored under that stage, or `None`.
- `ClassifiedGroup` (in `models/news_pipeline.py`): reconstructible from checkpoint via `ClassifiedGroup(**g)` — see existing usage at pipeline.py:1762.
- `CommunityInsight` (in `models/news_pipeline.py`): reconstructible via `CommunityInsight(**ins_data)` from `community_summarize` checkpoint `summaries` dict.
- News posts have columns: `slug`, `locale`, `content_expert`, `content_learner`, `title`, `excerpt`, `focus_items`, `guide_items` (JSONB), `quality_score`, `quality_flags`, `content_analysis`.
- The EN and KO versions of one digest share the same `quality_score` in production — updating both rows keeps them consistent.

---

## File Structure

**Files to modify:**

| File | Responsibility | Changes |
|------|----------------|---------|
| `backend/services/pipeline.py` | Pipeline orchestration + STAGE_CASCADE | Add `"quality"` key to STAGE_CASCADE; add quality-only branch in `rerun_pipeline_stage` |
| `backend/services/pipeline.py` | New helper | Add `_load_personas_and_frontload_from_db(supabase, batch_id)` to reconstruct inputs for `_check_digest_quality` from existing news_posts rows |
| `backend/routers/cron.py` | API validation | Add `"quality"` to `valid_stages` set in `rerun_pipeline` endpoint |
| `frontend/src/pages/admin/pipeline-runs/[runId].astro` | Admin UI | Add "Quality only" button to rerun dropdown |
| `backend/tests/test_pipeline_rerun.py` | Test coverage | Add test for quality-only rerun path |

**Files NOT to touch:**
- `services/pipeline_quality.py` — already has `_check_digest_quality` that we call as-is
- `services/pipeline_digest.py` — we're bypassing `_generate_digest`, not modifying it

---

## Chunk 1: Backend — STAGE_CASCADE + loader helper

### Task 1: Add `"quality"` to STAGE_CASCADE

**Files:**
- Modify: `backend/services/pipeline.py` lines 1558-1578 (the `STAGE_CASCADE` dict inside `rerun_pipeline_stage`)

**Context:**
`STAGE_CASCADE` maps a `from_stage` key to the list of `pipeline_type` values whose logs should be deleted before re-execution. A new `"quality"` key should delete only quality/save/summary stages — everything upstream (classify/merge/community/community_summarize/ranking/enrich/digest:*) is preserved.

- [ ] **Step 1: Add the dict entry**

In `services/pipeline.py`, edit the `STAGE_CASCADE` dict (inside `rerun_pipeline_stage`, starting at line 1558). Add a new key `"quality"` AFTER the existing `"write"` entry:

```python
        "write": ["digest:research:expert", "digest:research:learner",
                  "digest:business:expert", "digest:business:learner",
                  "quality:research", "quality:business",
                  "save:research", "save:business", "summary"],
        "quality": ["quality:research", "quality:business",
                    "save:research", "save:business", "summary"],
    }
```

- [ ] **Step 2: Verify dict syntax**

Run:
```
cd backend && .venv/Scripts/python.exe -c "from services.pipeline import rerun_pipeline_stage; print('ok')"
```
Expected output: `ok` (no SyntaxError).

- [ ] **Step 3: Commit**

```bash
git add backend/services/pipeline.py
git commit -m "feat(rerun): add 'quality' to STAGE_CASCADE — skip log deletion upstream

Enables quality-only rerun that preserves collect/classify/merge/community/
enrich/digest checkpoints and only re-runs quality + save + summary."
```

---

### Task 2: Helper to rebuild QC inputs from `news_posts`

**Files:**
- Modify: `backend/services/pipeline.py` (add new helper function before `rerun_pipeline_stage`, roughly around line 1530)

**Context:**
The digest stage writes PersonaOutput (EN+KO content) directly to `news_posts` — there is NO digest checkpoint. So to re-run quality without writer regeneration, we load content straight from the DB. This helper returns `(personas_by_type, frontload_by_type)` where each is a dict keyed by `digest_type` ("research"|"business").

- [ ] **Step 1: Write the failing test**

Create or open `backend/tests/test_pipeline_rerun.py` and add:

```python
import pytest
from unittest.mock import MagicMock

from services.pipeline import _load_personas_and_frontload_from_db


def test_load_personas_and_frontload_from_db_builds_two_types():
    """Loader reconstructs PersonaOutput (EN+KO) and frontload for both digest_types from existing news_posts rows."""
    supabase = MagicMock()

    # Four expected rows: research-EN, research-KO, business-EN, business-KO
    rows = [
        {
            "slug": "2026-04-19-research-digest",
            "locale": "en",
            "post_type": "research",
            "content_expert": "EN expert body",
            "content_learner": "EN learner body",
            "title": "Research headline",
            "excerpt": "Research excerpt",
            "focus_items": ["a", "b", "c"],
            "guide_items": {"title_learner": "Research learner title", "excerpt_learner": "Research learner excerpt"},
        },
        {
            "slug": "2026-04-19-research-digest-ko",
            "locale": "ko",
            "post_type": "research",
            "content_expert": "KO expert body",
            "content_learner": "KO learner body",
            "title": "Research headline KO",
            "excerpt": "Research excerpt KO",
            "focus_items": ["ㄱ", "ㄴ", "ㄷ"],
            "guide_items": {},
        },
        {
            "slug": "2026-04-19-business-digest",
            "locale": "en",
            "post_type": "business",
            "content_expert": "B-EN expert",
            "content_learner": "B-EN learner",
            "title": "Business headline",
            "excerpt": "Business excerpt",
            "focus_items": ["x", "y", "z"],
            "guide_items": {},
        },
        {
            "slug": "2026-04-19-business-digest-ko",
            "locale": "ko",
            "post_type": "business",
            "content_expert": "B-KO expert",
            "content_learner": "B-KO learner",
            "title": "Business headline KO",
            "excerpt": "Business excerpt KO",
            "focus_items": [],
            "guide_items": {},
        },
    ]
    supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value.data = rows

    personas_by_type, frontload_by_type = _load_personas_and_frontload_from_db(supabase, "2026-04-19")

    # Two digest types reconstructed
    assert set(personas_by_type.keys()) == {"research", "business"}
    assert set(frontload_by_type.keys()) == {"research", "business"}

    # Research personas merged EN + KO
    research_personas = personas_by_type["research"]
    assert research_personas["expert"].en == "EN expert body"
    assert research_personas["expert"].ko == "KO expert body"
    assert research_personas["learner"].en == "EN learner body"
    assert research_personas["learner"].ko == "KO learner body"

    # Business personas
    assert personas_by_type["business"]["expert"].en == "B-EN expert"
    assert personas_by_type["business"]["expert"].ko == "B-KO expert"

    # Frontload from EN row, with focus_items_ko from KO row's focus_items
    research_front = frontload_by_type["research"]
    assert research_front["headline"] == "Research headline"
    assert research_front["headline_ko"] == "Research headline KO"
    assert research_front["excerpt"] == "Research excerpt"
    assert research_front["excerpt_ko"] == "Research excerpt KO"
    assert research_front["focus_items"] == ["a", "b", "c"]
    assert research_front["focus_items_ko"] == ["ㄱ", "ㄴ", "ㄷ"]


def test_load_personas_and_frontload_returns_empty_on_missing_rows():
    """When no news_posts match the batch, the loader returns empty dicts (caller handles)."""
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value.data = []

    personas_by_type, frontload_by_type = _load_personas_and_frontload_from_db(supabase, "2026-04-19")
    assert personas_by_type == {}
    assert frontload_by_type == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_pipeline_rerun.py::test_load_personas_and_frontload_from_db_builds_two_types -v
```
Expected: FAIL with `ImportError: cannot import name '_load_personas_and_frontload_from_db'` (or similar — function doesn't exist yet).

- [ ] **Step 3: Implement the helper**

In `services/pipeline.py`, add this function just above `async def rerun_pipeline_stage(` (around line 1530). Required imports should already be present (`PersonaOutput` from models.news_pipeline — add to existing imports if missing).

```python
def _load_personas_and_frontload_from_db(
    supabase, batch_id: str,
) -> tuple[dict[str, dict[str, "PersonaOutput"]], dict[str, dict[str, Any]]]:
    """Reconstruct per-digest-type PersonaOutput + frontload from existing news_posts rows.

    Used by rerun_from='quality' to re-run QC without regenerating content.
    Returns:
        personas_by_type: {"research": {"expert": PersonaOutput, "learner": PersonaOutput}, "business": {...}}
        frontload_by_type: {"research": {headline, headline_ko, excerpt, excerpt_ko, focus_items, focus_items_ko}, "business": {...}}
    """
    from models.news_pipeline import PersonaOutput

    slugs = [
        f"{batch_id.lower()}-research-digest",
        f"{batch_id.lower()}-research-digest-ko",
        f"{batch_id.lower()}-business-digest",
        f"{batch_id.lower()}-business-digest-ko",
    ]
    resp = (
        supabase.table("news_posts")
        .select("slug,locale,post_type,content_expert,content_learner,title,excerpt,focus_items,guide_items")
        .eq("category", "ai-news")
        .in_("slug", slugs)
        .execute()
    )
    rows = resp.data or []

    # Group rows by digest_type
    by_type: dict[str, dict[str, dict]] = {}  # {type: {locale: row}}
    for row in rows:
        dtype = row.get("post_type")
        loc = row.get("locale")
        if dtype in ("research", "business") and loc in ("en", "ko"):
            by_type.setdefault(dtype, {})[loc] = row

    personas_by_type: dict[str, dict[str, PersonaOutput]] = {}
    frontload_by_type: dict[str, dict[str, Any]] = {}

    for dtype, by_loc in by_type.items():
        en_row = by_loc.get("en") or {}
        ko_row = by_loc.get("ko") or {}

        personas_by_type[dtype] = {
            "expert": PersonaOutput(
                en=en_row.get("content_expert") or "",
                ko=ko_row.get("content_expert") or "",
            ),
            "learner": PersonaOutput(
                en=en_row.get("content_learner") or "",
                ko=ko_row.get("content_learner") or "",
            ),
        }

        # Frontload: EN fields from EN row, KO from KO row, focus_items_ko from KO row's focus_items
        guide = en_row.get("guide_items") or {}
        frontload_by_type[dtype] = {
            "headline": en_row.get("title") or "",
            "headline_ko": ko_row.get("title") or guide.get("title_learner") or "",
            "excerpt": en_row.get("excerpt") or "",
            "excerpt_ko": ko_row.get("excerpt") or guide.get("excerpt_learner") or "",
            "focus_items": en_row.get("focus_items") or [],
            "focus_items_ko": ko_row.get("focus_items") or [],
        }

    return personas_by_type, frontload_by_type
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_pipeline_rerun.py::test_load_personas_and_frontload_from_db_builds_two_types tests/test_pipeline_rerun.py::test_load_personas_and_frontload_returns_empty_on_missing_rows -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_pipeline_rerun.py
git commit -m "feat(rerun): add _load_personas_and_frontload_from_db helper

Rebuilds PersonaOutput (EN+KO) and frontload dict from existing
news_posts rows. Enables rerun_from='quality' to skip writer regen."
```

---

## Chunk 2: Backend — quality-only branch in rerun_pipeline_stage

### Task 3: Wire the `quality` branch into `rerun_pipeline_stage`

**Files:**
- Modify: `backend/services/pipeline.py` (inside `rerun_pipeline_stage`, around the existing `--- Always run write (digest generation) ---` block at line 1770)

**Context:**
When `from_stage == "quality"`, the function must:
1. Skip checkpoint loading logic that feeds writer (no need for raw_content_map, enriched_map, etc.)
2. Load classified from `merge` checkpoint (so `_check_digest_quality` gets `classified` for structural checks)
3. Load `community_summary_map` from `community_summarize` checkpoint (for CP structural check)
4. Call `_load_personas_and_frontload_from_db` to get content + frontload
5. Call `_check_digest_quality(personas, digest_type, classified, community_summary_map, supabase, run_id, cumulative_usage, frontload)` for each digest_type
6. Update the 2 locale rows for that digest_type in news_posts with `quality_score`, `quality_flags`, `content_analysis`
7. Log summary stage

- [ ] **Step 1: Add the quality-only branch**

In `services/pipeline.py`, inside `rerun_pipeline_stage`, find the existing `# --- Always run write (digest generation) ---` section (around line 1770). REPLACE that section with a branch that handles quality separately. The full edit:

```python
        # --- Branch: quality-only rerun (skip writer) ---
        if from_stage == "quality":
            from services.pipeline_quality import _check_digest_quality
            from datetime import datetime, timezone

            # Need classification (for structural checks) + community summaries
            merge_data = _load_checkpoint(supabase, source_run_id, "merge")
            classification = ClassificationResult()
            if merge_data:
                classification.research = [ClassifiedGroup(**g) for g in merge_data.get("research", [])]
                classification.business = [ClassifiedGroup(**g) for g in merge_data.get("business", [])]

            cs_data = _load_checkpoint(supabase, source_run_id, "community_summarize")
            community_summary_map: dict[str, CommunityInsight] = {}
            if cs_data and cs_data.get("summaries"):
                community_summary_map = {
                    url: CommunityInsight(**ins_data)
                    for url, ins_data in cs_data["summaries"].items()
                }

            personas_by_type, frontload_by_type = _load_personas_and_frontload_from_db(supabase, batch_id)
            if not personas_by_type:
                all_errors.append(f"No news_posts found for batch {batch_id} — cannot rescore")

            for digest_type in ("research", "business"):
                if category and digest_type != category:
                    continue
                if digest_type not in personas_by_type:
                    continue

                classified_items = getattr(classification, digest_type, []) or []
                personas = personas_by_type[digest_type]
                frontload = frontload_by_type.get(digest_type, {})

                try:
                    qc_result = await _check_digest_quality(
                        personas=personas,
                        digest_type=digest_type,
                        classified=classified_items,
                        community_summary_map=community_summary_map,
                        supabase=supabase,
                        run_id=run_id,
                        cumulative_usage=cumulative_usage,
                        frontload=frontload,
                    )
                except Exception as e:
                    all_errors.append(f"Quality rescore failed for {digest_type}: {e}")
                    continue

                score_int = int(qc_result.get("score") or qc_result.get("quality_score") or 0)
                flags = qc_result.get("quality_flags") or []
                content_analysis = {
                    "scores_breakdown": qc_result.get("quality_breakdown"),
                    "issues": qc_result.get("quality_issues") or [],
                }
                analyzed_at = datetime.now(timezone.utc).isoformat()

                # Update BOTH locale rows for this digest_type.
                # total_posts counts rows updated (EN + KO = 2 per digest_type). This differs
                # from _generate_digest's return semantics (which counts digests generated),
                # but is the honest metric here: we touched 2 rows.
                for slug in (
                    f"{batch_id.lower()}-{digest_type}-digest",
                    f"{batch_id.lower()}-{digest_type}-digest-ko",
                ):
                    try:
                        supabase.table("news_posts").update({
                            "quality_score": score_int,
                            "quality_flags": flags,
                            "content_analysis": content_analysis,
                            "analyzed_at": analyzed_at,
                        }).eq("slug", slug).execute()
                        total_posts += 1
                    except Exception as e:
                        all_errors.append(f"Failed to update {slug}: {e}")

            # Skip the digest-generation block below
        else:
            # --- Always run write (digest generation) ---
            digest_tasks = []
            for digest_type, classified_items in [
                ("research", classification.research),
                ("business", classification.business),
            ]:
                if not classified_items:
                    continue
                if category and digest_type != category:
                    continue  # Skip if category filter is set
                digest_tasks.append(
                    _generate_digest(
                        classified=classified_items,
                        digest_type=digest_type,
                        batch_id=batch_id,
                        handbook_slugs=handbook_slugs,
                        raw_content_map=raw_content_map,
                        community_summary_map=community_summary_map,
                        supabase=supabase,
                        run_id=run_id,
                        enriched_map=enriched_map,
                        auto_publish=False,
                    )
                )

            digest_results = await asyncio.gather(*digest_tasks, return_exceptions=True)
            for result in digest_results:
                if isinstance(result, Exception):
                    all_errors.append(f"Digest generation failed: {result}")
                else:
                    posts, errors, usage = result
                    total_posts += posts
                    all_errors.extend(errors)
                    cumulative_usage = merge_usage_metrics(cumulative_usage, usage)
```

Note: the existing checkpoint-loading block above (research/business/etc.) runs BEFORE this branch. For `quality`, we only need `merge` + `community_summarize` — but the existing block loads them already for lower stages. If `from_stage == "quality"`, the upstream loading block's conditions (`if from_stage == "classify"`, `if from_stage in ("classify", "merge")`, etc.) will all be false, so those branches skip. That's correct — we only need the two specific checkpoints, which are loaded fresh inside our branch.

- [ ] **Step 2: Write the integration tests**

Add two tests to `backend/tests/test_pipeline_rerun.py` — one asserts the quality branch skips regeneration AND writes the correct payload; the other asserts the checkpoint-hydration path actually reconstructs ClassifiedGroup + CommunityInsight (so a regression there ships red, not green):

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


def _build_supabase_mock_for_quality_rerun(news_rows: list, checkpoint_returns=None):
    """Small helper shared by the two tests below.

    news_rows: list of news_posts rows returned by the persona loader.
    checkpoint_returns: optional dict[str, dict] keyed by stage name
        (e.g. {"merge": {...}, "community_summarize": {...}}).
    """
    supabase = MagicMock()
    # pipeline_runs claim-lock + pipeline_logs delete always succeed
    supabase.table.return_value.update.return_value.eq.return_value.neq.return_value.execute.return_value.data = [{"id": "run-1"}]
    supabase.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
    supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    # news_posts loader
    supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value.data = news_rows
    return supabase


@pytest.mark.asyncio
async def test_rerun_from_quality_skips_digest_generation_and_writes_payload():
    """rerun_from='quality' must:
      1. call _check_digest_quality (not _generate_digest)
      2. update BOTH locale rows with quality_score, quality_flags, content_analysis, analyzed_at
      3. return status=success
    """
    from services.pipeline import rerun_pipeline_stage

    news_rows = [
        {"slug": "2026-04-19-research-digest", "locale": "en", "post_type": "research",
         "content_expert": "E", "content_learner": "L", "title": "t", "excerpt": "x",
         "focus_items": [], "guide_items": {}},
        {"slug": "2026-04-19-research-digest-ko", "locale": "ko", "post_type": "research",
         "content_expert": "E-ko", "content_learner": "L-ko", "title": "t-ko", "excerpt": "x-ko",
         "focus_items": [], "guide_items": {}},
    ]
    supabase = _build_supabase_mock_for_quality_rerun(news_rows)

    with patch("services.pipeline.get_supabase_client", return_value=supabase), \
         patch("services.pipeline._load_checkpoint", return_value=None), \
         patch("services.pipeline._check_digest_quality", new_callable=AsyncMock) as qc_mock, \
         patch("services.pipeline._generate_digest", new_callable=AsyncMock) as gen_mock:
        qc_mock.return_value = {
            "score": 84,
            "quality_score": 84,
            "quality_flags": [],
            "quality_issues": [],
            "quality_breakdown": {"total_score": 84},
        }

        result = await rerun_pipeline_stage(
            source_run_id="run-1",
            from_stage="quality",
            batch_id="2026-04-19",
            category="research",
        )

        # Cost saving: writer skipped
        assert qc_mock.await_count == 1
        assert gen_mock.await_count == 0
        assert result.status == "success"

        # Payload assertion: both locale rows updated with expected shape.
        # Collect all .update(...) calls on news_posts (the first positional arg is the payload dict).
        update_calls = [
            c for c in supabase.table.return_value.update.call_args_list
            if c.args and isinstance(c.args[0], dict) and "quality_score" in c.args[0]
        ]
        assert len(update_calls) == 2, f"expected 2 locale updates, got {len(update_calls)}"
        for c in update_calls:
            payload = c.args[0]
            assert payload["quality_score"] == 84
            assert payload["quality_flags"] == []
            assert "scores_breakdown" in payload["content_analysis"]
            assert "analyzed_at" in payload and payload["analyzed_at"]  # non-empty ISO string


@pytest.mark.asyncio
async def test_rerun_from_quality_hydrates_classified_and_community_from_checkpoints():
    """When merge + community_summarize checkpoints are present, the quality branch
    must hydrate them into ClassifiedGroup / CommunityInsight objects and pass them
    into _check_digest_quality (not empty lists). Covers the else-branch inside the
    checkpoint-loading block."""
    from services.pipeline import rerun_pipeline_stage
    from models.news_pipeline import ClassifiedGroup, CommunityInsight

    news_rows = [
        {"slug": "2026-04-19-research-digest", "locale": "en", "post_type": "research",
         "content_expert": "E", "content_learner": "L", "title": "t", "excerpt": "x",
         "focus_items": [], "guide_items": {}},
        {"slug": "2026-04-19-research-digest-ko", "locale": "ko", "post_type": "research",
         "content_expert": "E-ko", "content_learner": "L-ko", "title": "t-ko", "excerpt": "x-ko",
         "focus_items": [], "guide_items": {}},
    ]
    supabase = _build_supabase_mock_for_quality_rerun(news_rows)

    # Realistic checkpoint payloads.
    # Use the minimum field set required by ClassifiedGroup / CommunityInsight constructors —
    # if model fields change, update this fixture and the test will keep covering the path.
    merge_ckpt = {
        "research": [{
            "topic": "Anthropic releases Claude 4.7",
            "items": [],
            "category": "ai-news",
        }],
        "business": [],
    }
    community_ckpt = {
        "summaries": {
            "https://example.com/a": {
                "url": "https://example.com/a",
                "summary_en": "Hot take",
                "summary_ko": "핫한 의견",
                "source": "reddit",
                "quotes_en": [],
                "quotes_ko": [],
            }
        }
    }

    def load_ckpt_side_effect(sb, run_id, stage):
        return {"merge": merge_ckpt, "community_summarize": community_ckpt}.get(stage)

    with patch("services.pipeline.get_supabase_client", return_value=supabase), \
         patch("services.pipeline._load_checkpoint", side_effect=load_ckpt_side_effect), \
         patch("services.pipeline._check_digest_quality", new_callable=AsyncMock) as qc_mock, \
         patch("services.pipeline._generate_digest", new_callable=AsyncMock) as gen_mock:
        qc_mock.return_value = {
            "score": 80, "quality_score": 80,
            "quality_flags": [], "quality_issues": [],
            "quality_breakdown": {"total_score": 80},
        }

        await rerun_pipeline_stage(
            source_run_id="run-1",
            from_stage="quality",
            batch_id="2026-04-19",
            category="research",
        )

        assert gen_mock.await_count == 0
        assert qc_mock.await_count == 1
        # Inspect the kwargs passed to _check_digest_quality — classified and
        # community_summary_map must have been HYDRATED, not left empty.
        kwargs = qc_mock.await_args.kwargs
        assert len(kwargs["classified"]) == 1
        assert isinstance(kwargs["classified"][0], ClassifiedGroup)
        assert "https://example.com/a" in kwargs["community_summary_map"]
        assert isinstance(kwargs["community_summary_map"]["https://example.com/a"], CommunityInsight)
```

**Why two tests:**
- Test 1 proves: writer is skipped, both locale rows get the expected payload (including `analyzed_at`).
- Test 2 proves: the checkpoint-hydration branches run correctly — without it, a regression in the `ClassifiedGroup(**g)` / `CommunityInsight(**ins_data)` construction would slip through the first test (which passes `None` checkpoints).

- [ ] **Step 3: Run tests**

Run:
```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_pipeline_rerun.py -v
```
Expected: all 4 tests pass — 2 helper tests from Chunk 1 + 2 integration tests above (payload + hydration).

- [ ] **Step 4: Lint**

Run:
```
cd backend && .venv/Scripts/python.exe -m ruff check services/pipeline.py
```
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_pipeline_rerun.py
git commit -m "feat(rerun): add quality-only branch to rerun_pipeline_stage

Skip expensive gpt-5 writer when only QC prompts changed. Loads persona
outputs from news_posts (EN+KO content_expert/content_learner + title/
excerpt/focus_items/guide_items) and classified from merge checkpoint,
calls _check_digest_quality, writes fresh quality_score/flags/analysis
back to both locale rows.

Expected cost per rerun: ~\$0.05 (vs ~\$0.55 for rerun_from=write).
Apr 19 case: 2 reruns × \$0.55 = \$1.10 wasted — this fixes that class
of spend for QC tuning cycles."
```

---

## Chunk 3: API + UI exposure

### Task 4: Admin endpoint validation

**Files:**
- Modify: `backend/routers/cron.py` line 257 (`valid_stages` set in `rerun_pipeline` endpoint)

- [ ] **Step 1: Update the valid stages set**

In `routers/cron.py`, find the existing line 257:

```python
    valid_stages = {"classify", "merge", "community", "write"}
```

Change to:

```python
    valid_stages = {"classify", "merge", "community", "write", "quality"}
```

Also update the field docstring comment on line 243:

```python
    from_stage: str  # "classify"|"merge"|"community"|"write"|"quality"
```

- [ ] **Step 2: Smoke check — endpoint still imports**

Run:
```
cd backend && .venv/Scripts/python.exe -c "from routers.cron import rerun_pipeline; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/routers/cron.py
git commit -m "feat(api): accept 'quality' as rerun_from value"
```

---

### Task 5: Admin UI — add "Quality only" button

**Files:**
- Modify: `frontend/src/pages/admin/pipeline-runs/[runId].astro` around line 262-267 (the rerun dropdown buttons)

- [ ] **Step 1: Add the button**

In `frontend/src/pages/admin/pipeline-runs/[runId].astro`, find the existing block around line 262:

```html
<button class="pipeline-rerun-option" data-stage="write" data-category="research">Write: Research only</button>
<button class="pipeline-rerun-option" data-stage="write" data-category="business">Write: Business only</button>
<button class="pipeline-rerun-option" data-stage="write">Write: Both</button>
<button class="pipeline-rerun-option" data-stage="community">From Community</button>
<button class="pipeline-rerun-option" data-stage="merge">From Merge</button>
<button class="pipeline-rerun-option" data-stage="classify">From Classify</button>
```

ADD 3 new buttons at the top (quality is the cheapest so list it first):

```html
<button class="pipeline-rerun-option" data-stage="quality" data-category="research">Quality only: Research</button>
<button class="pipeline-rerun-option" data-stage="quality" data-category="business">Quality only: Business</button>
<button class="pipeline-rerun-option" data-stage="quality">Quality only: Both</button>
<button class="pipeline-rerun-option" data-stage="write" data-category="research">Write: Research only</button>
<button class="pipeline-rerun-option" data-stage="write" data-category="business">Write: Business only</button>
<button class="pipeline-rerun-option" data-stage="write">Write: Both</button>
<button class="pipeline-rerun-option" data-stage="community">From Community</button>
<button class="pipeline-rerun-option" data-stage="merge">From Merge</button>
<button class="pipeline-rerun-option" data-stage="classify">From Classify</button>
```

- [ ] **Step 2: Build check**

Run:
```
cd frontend && npm run build
```
Expected: build succeeds with 0 errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/admin/pipeline-runs/[runId].astro
git commit -m "feat(admin-ui): add Quality-only rerun buttons

Adds 3 new buttons (research/business/both) that hit the backend with
from_stage='quality' — skips expensive gpt-5 writer regen and only
re-runs QC scoring + save against existing content."
```

---

## Chunk 4: End-to-end validation

### Task 6: Manual smoke test on Apr 19

All validation queries below are consolidated into one script (`backend/scripts/validate_quality_rerun.py`, created in Step 0) so Step 5 runs as a single pass/fail output rather than 3 separate eyeball queries.

- [ ] **Step 0: Create baseline + preflight script**

Create `backend/scripts/validate_quality_rerun.py`. It has two modes:
- `baseline` — captures pre-rerun state: body hashes for all 4 slugs, `pipeline_logs` max `created_at` (cutoff for cost filter), and asserts all 4 slugs exist.
- `verify` — compares post-rerun state to the baseline file and prints a pass/fail summary across all 6 criteria.

```python
"""Validate that a quality-only rerun preserved content + hit the cost budget.

Usage:
    python scripts/validate_quality_rerun.py baseline 2026-04-19
    # ... trigger rerun via admin UI ...
    python scripts/validate_quality_rerun.py verify 2026-04-19

Writes baseline to scripts/.quality_rerun_baseline_<batch_id>.json (git-ignored).
Exit code 0 = all criteria pass, 1 = any failure.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SB = create_client(
    os.environ["SUPABASE_URL"],
    os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY"),
)

COST_BUDGET_USD = 0.10


def slugs_for(batch_id: str) -> list[str]:
    return [
        f"{batch_id}-research-digest",
        f"{batch_id}-research-digest-ko",
        f"{batch_id}-business-digest",
        f"{batch_id}-business-digest-ko",
    ]


def _sha(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def baseline(batch_id: str, out_path: Path) -> int:
    # Preflight: all 4 slugs must exist
    rows = SB.table("news_posts").select(
        "slug,content_expert,content_learner,analyzed_at,quality_score"
    ).in_("slug", slugs_for(batch_id)).execute().data
    by_slug = {r["slug"]: r for r in rows}
    missing = [s for s in slugs_for(batch_id) if s not in by_slug]
    if missing:
        print(f"FAIL preflight: missing slugs {missing}")
        return 1

    # pipeline_logs cutoff — any row created AFTER this timestamp is from the rerun
    run = SB.table("pipeline_runs").select("id").eq(
        "run_key", f"news-{batch_id}"
    ).single().execute().data
    logs = SB.table("pipeline_logs").select("created_at").eq(
        "run_id", run["id"]
    ).order("created_at", desc=True).limit(1).execute().data
    cutoff = logs[0]["created_at"] if logs else "1970-01-01T00:00:00+00:00"

    snapshot = {
        "batch_id": batch_id,
        "run_id": run["id"],
        "cutoff_created_at": cutoff,
        "slugs": {
            slug: {
                "content_expert_hash": _sha(by_slug[slug].get("content_expert")),
                "content_learner_hash": _sha(by_slug[slug].get("content_learner")),
                "analyzed_at": by_slug[slug].get("analyzed_at"),
                "quality_score": by_slug[slug].get("quality_score"),
            }
            for slug in slugs_for(batch_id)
        },
    }
    out_path.write_text(json.dumps(snapshot, indent=2))
    print(f"OK baseline written: {out_path}")
    print(f"   run_id={run['id']}  cutoff={cutoff}")
    return 0


def verify(batch_id: str, in_path: Path) -> int:
    if not in_path.exists():
        print(f"FAIL: baseline file not found: {in_path}")
        return 1
    base = json.loads(in_path.read_text())

    run_id = base["run_id"]
    cutoff = base["cutoff_created_at"]

    fails: list[str] = []

    # Criterion 1: cost — sum pipeline_logs.cost_usd for rows created AFTER cutoff
    new_logs = SB.table("pipeline_logs").select(
        "pipeline_type,cost_usd,created_at"
    ).eq("run_id", run_id).gt("created_at", cutoff).execute().data
    total_cost = sum((log.get("cost_usd") or 0) for log in new_logs)
    print(f"[cost] rerun logs: {len(new_logs)}  total_cost=${total_cost:.4f}")
    for log in new_logs:
        print(f"   ${log.get('cost_usd') or 0:.4f}  {log['pipeline_type']}  {log['created_at'][-14:-4]}")
    if total_cost > COST_BUDGET_USD:
        fails.append(f"cost ${total_cost:.4f} > budget ${COST_BUDGET_USD}")

    # Criterion 2: no digest:* stages ran in the rerun window (proof writer skipped)
    digest_runs = [log for log in new_logs if str(log["pipeline_type"]).startswith("digest:")]
    if digest_runs:
        fails.append(f"digest stages re-ran: {[l['pipeline_type'] for l in digest_runs]}")

    # Criterion 3: each slug's quality_score + analyzed_at refreshed, both locales
    rows = SB.table("news_posts").select(
        "slug,quality_score,quality_flags,content_analysis,analyzed_at,"
        "content_expert,content_learner"
    ).in_("slug", slugs_for(batch_id)).execute().data
    by_slug = {r["slug"]: r for r in rows}

    for slug in slugs_for(batch_id):
        row = by_slug.get(slug)
        if not row:
            fails.append(f"{slug}: row missing")
            continue
        base_slug = base["slugs"][slug]

        # 3a: quality_score is an int
        qs = row.get("quality_score")
        if not isinstance(qs, int):
            fails.append(f"{slug}: quality_score not int ({qs!r})")

        # 3b: content_analysis has the expected shape
        ca = row.get("content_analysis")
        if not (isinstance(ca, dict) and "scores_breakdown" in ca):
            fails.append(f"{slug}: content_analysis missing scores_breakdown")

        # 3c: analyzed_at refreshed (strictly newer than baseline)
        if not row.get("analyzed_at"):
            fails.append(f"{slug}: analyzed_at missing after rerun")
        elif base_slug["analyzed_at"] and row["analyzed_at"] <= base_slug["analyzed_at"]:
            fails.append(f"{slug}: analyzed_at not refreshed "
                         f"(was {base_slug['analyzed_at']}, is {row['analyzed_at']})")

        # 3d: content_expert / content_learner UNCHANGED (writer skipped)
        now_e = _sha(row.get("content_expert"))
        now_l = _sha(row.get("content_learner"))
        if now_e != base_slug["content_expert_hash"]:
            fails.append(f"{slug}: content_expert CHANGED — writer must have re-run")
        if now_l != base_slug["content_learner_hash"]:
            fails.append(f"{slug}: content_learner CHANGED — writer must have re-run")

    if fails:
        print("\nFAIL — criteria violated:")
        for f in fails:
            print(f"   - {f}")
        return 1
    print("\nOK all criteria passed.")
    return 0


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("baseline", "verify"):
        print("usage: python scripts/validate_quality_rerun.py {baseline|verify} <batch_id>")
        return 2
    mode, batch_id = sys.argv[1], sys.argv[2]
    path = Path(__file__).parent / f".quality_rerun_baseline_{batch_id}.json"
    return baseline(batch_id, path) if mode == "baseline" else verify(batch_id, path)


if __name__ == "__main__":
    sys.exit(main())
```

Also append this line to `backend/.gitignore` if not already covered by a broader pattern:
```
scripts/.quality_rerun_baseline_*.json
```
Check first with `grep quality_rerun backend/.gitignore` — if no match, append the line and commit it alongside the script in Step 2. If already covered, skip the gitignore edit (Step 2's `git add backend/.gitignore` becomes a no-op; drop it from the `git add` list).

- [ ] **Step 1: Capture baseline**

```
cd backend && .venv/Scripts/python.exe scripts/validate_quality_rerun.py baseline 2026-04-19
```
Expected: `OK baseline written: ...` with a printed run_id + cutoff timestamp. If this fails with a missing-slug error, stop — the Apr 19 batch doesn't have both locales for both digest_types and this plan can't be validated on it. Pick a different batch or investigate.

- [ ] **Step 2: Push branch**

```bash
git add backend/scripts/validate_quality_rerun.py backend/.gitignore
git commit -m "chore(scripts): add quality-rerun E2E validation script"
git push origin main
```

- [ ] **Step 3: Wait for Railway deploy**

Check Railway dashboard or wait ~2-3 minutes for the new code to go live.

- [ ] **Step 4: Trigger quality-only rerun via admin UI**

1. Open admin → Pipeline Runs → `news-2026-04-19`.
2. Click **"Quality only: Both"**.
3. Wait for completion (expected ~30–60 seconds).

- [ ] **Step 5: Verify everything**

```
cd backend && .venv/Scripts/python.exe scripts/validate_quality_rerun.py verify 2026-04-19
```
Expected final line: `OK all criteria passed.` and exit code 0.

The script asserts all 6 criteria in one pass:
1. Total cost since cutoff ≤ $0.10.
2. No `digest:*` stages ran after cutoff (proves writer skipped).
3. `quality_score` is an int on all 4 slugs.
4. `content_analysis.scores_breakdown` present on all 4 slugs.
5. `analyzed_at` strictly newer than baseline on all 4 slugs.
6. `content_expert` + `content_learner` hashes UNCHANGED on all 4 slugs (writer didn't run).

- [ ] **Step 6: If verification fails — rollback + debug**

The rerun wrote `quality_score`/`quality_flags`/`content_analysis`/`analyzed_at` over the pre-rerun values. Those columns are safe to overwrite (we overwrite them on every normal run). So "rollback" means: fix the bug, re-run, and the next success overwrites the bad values — no data restoration needed.

If `content_expert` / `content_learner` CHANGED (criterion 6 failed), that's the only serious case: the writer somehow ran during a quality rerun. Stop, do NOT retry, and investigate:
- Check `rerun_pipeline_stage` logs — did the quality branch execute?
- Did `_generate_digest` get called? (Test 1 in Chunk 2 asserts it shouldn't.)
- If body text was overwritten with new-but-wrong content, restore from the most recent `published` or `final` state before the rerun (check Supabase row history / a previous Railway log / prior day's backup if one exists).

For other criteria failures, check `pipeline_logs` for the run_id + recent rows, check `all_errors` in the RerunResult, and iterate on Chunk 2. Each retry is itself a quality rerun so costs stay bounded.

- [ ] **Step 7: Optional commit (only if script needs tweaks)**

If Step 5 reveals that the script itself has a bug (false negative, wrong filter), fix the script and commit with `fix(scripts): ...`. Don't commit the `.quality_rerun_baseline_*.json` file.

---

## Done criteria (full plan)

- [ ] `rerun_from=quality` is a valid value in both the API endpoint and the admin UI.
- [ ] Quality-only rerun does NOT call `_generate_digest` and does NOT incur gpt-5 writer cost.
- [ ] `news_posts.quality_score`, `quality_flags`, `content_analysis`, `analyzed_at` are updated on both EN and KO rows for the targeted digest_type(s).
- [ ] `content_expert` and `content_learner` remain byte-identical after a quality rerun (writer skipped).
- [ ] All existing rerun paths (`classify`/`merge`/`community`/`write`) continue to behave identically.
- [ ] `pytest tests/test_pipeline_rerun.py` passes (4 tests: 2 helper from Chunk 1 + 2 integration from Chunk 2).
- [ ] `ruff check services/pipeline.py` clean.
- [ ] Apr 19 E2E: `validate_quality_rerun.py verify 2026-04-19` exits 0 (all 6 criteria pass, cost ≤ $0.10).
