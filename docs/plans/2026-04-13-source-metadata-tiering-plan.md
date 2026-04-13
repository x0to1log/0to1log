# Source Metadata Tiering Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add source metadata classification (`source_kind`, `source_confidence`, `source_tier`) to the daily news pipeline so prompts, saved source cards, and future QA/scoring can distinguish official sources from secondary coverage.

**Architecture:** Classify sources in code before digest generation, not inside the LLM prompt. Attach normalized source metadata during collection and enrichment, surface it in the writer input as structured source labels, and persist the same metadata into `fact_pack.sources` and `source_cards` so later validation and scoring can reuse it.

**Tech Stack:** FastAPI backend, Pydantic models, Supabase JSON payloads, pytest

---

### Task 1: Extend Source Models For Metadata

**Files:**
- Modify: `backend/models/news_pipeline.py`
- Test: `backend/tests/test_news_pipeline_models.py`

**Step 1: Write the failing test**

Add model coverage for the new fields on both `NewsCandidate` and `FactSource`.

```python
def test_news_candidate_accepts_source_metadata():
    candidate = NewsCandidate(
        title="Official launch",
        url="https://openai.com/index/launch",
        source="tavily",
        source_kind="official_site",
        source_confidence="high",
        source_tier="primary",
    )

    assert candidate.source_kind == "official_site"
    assert candidate.source_confidence == "high"
    assert candidate.source_tier == "primary"


def test_fact_source_accepts_source_metadata():
    source = FactSource(
        id="s1",
        title="Launch post",
        url="https://openai.com/index/launch",
        source_kind="official_site",
        source_confidence="high",
        source_tier="primary",
    )

    assert source.source_kind == "official_site"
    assert source.source_confidence == "high"
    assert source.source_tier == "primary"
```

**Step 2: Run test to verify it fails**

Run: `backend\.venv\Scripts\python -m pytest backend\tests\test_news_pipeline_models.py -k source_metadata -v`

Expected: FAIL because the new fields do not exist yet.

**Step 3: Write minimal implementation**

Add string fields with safe defaults to the models:

```python
class NewsCandidate(BaseModel):
    ...
    source_kind: str = ""
    source_confidence: str = ""
    source_tier: str = ""


class FactSource(BaseModel):
    ...
    source_kind: str = ""
    source_confidence: str = ""
    source_tier: str = ""
```

**Step 4: Run test to verify it passes**

Run: `backend\.venv\Scripts\python -m pytest backend\tests\test_news_pipeline_models.py -k source_metadata -v`

Expected: PASS

**Step 5: Commit**

```bash
git add backend/models/news_pipeline.py backend/tests/test_news_pipeline_models.py
git commit -m "feat: add source metadata fields"
```


### Task 2: Add A Central Source Classifier In Collection

**Files:**
- Modify: `backend/services/news_collection.py`
- Test: `backend/tests/test_news_collection.py`

**Step 1: Write the failing test**

Add focused classifier tests for representative URLs.

```python
def test_classify_source_meta_marks_official_site_primary():
    meta = _classify_source_meta(
        url="https://openai.com/index/introducing-gpt-5-4/",
        source="tavily",
        title="Introducing GPT-5.4",
    )
    assert meta == {
        "source_kind": "official_site",
        "source_confidence": "high",
        "source_tier": "primary",
    }


def test_classify_source_meta_marks_hf_blog_as_official_platform_asset():
    meta = _classify_source_meta(
        url="https://huggingface.co/blog/Hcompany/holo3",
        source="tavily",
        title="Holo3",
    )
    assert meta["source_kind"] == "official_platform_asset"
    assert meta["source_confidence"] == "medium"
    assert meta["source_tier"] == "primary"


def test_classify_source_meta_marks_media_as_secondary():
    meta = _classify_source_meta(
        url="https://venturebeat.com/ai/story",
        source="tavily",
        title="VentureBeat coverage",
    )
    assert meta["source_kind"] == "media"
    assert meta["source_tier"] == "secondary"
```

**Step 2: Run test to verify it fails**

Run: `backend\.venv\Scripts\python -m pytest backend\tests\test_news_collection.py -k classify_source_meta -v`

Expected: FAIL because `_classify_source_meta` does not exist.

**Step 3: Write minimal implementation**

Add one helper in `backend/services/news_collection.py` and keep it rule-based only:

```python
def _classify_source_meta(url: str, source: str = "", title: str = "") -> dict[str, str]:
    ...
    return {
        "source_kind": "...",
        "source_confidence": "...",
        "source_tier": "...",
    }
```

Initial mapping:
- `arxiv.org` -> `paper/high/primary`
- official company domains (`openai.com`, `anthropic.com`, `techcommunity.microsoft.com`, `blogs.nvidia.com`, etc.) -> `official_site/high/primary`
- `huggingface.co/blog/...` -> `official_platform_asset/medium/primary`
- `huggingface.co/<org>/<repo>` model card / LICENSE / file pages -> `official_platform_asset/high/primary`
- `github.com/.../pull/...`, `/releases`, repo root -> `official_repo/medium/primary`
- `registry.npmjs.org`, `npmjs.com/package/...` -> `registry/medium/primary`
- known media domains -> `media/high/secondary`
- Medium/Substack/personal-style domains -> `analysis/medium/secondary`
- Reddit / Hacker News / X -> `community/medium/secondary`
- default fallback -> `analysis/low/secondary`

**Step 4: Run test to verify it passes**

Run: `backend\.venv\Scripts\python -m pytest backend\tests\test_news_collection.py -k classify_source_meta -v`

Expected: PASS

**Step 5: Commit**

```bash
git add backend/services/news_collection.py backend/tests/test_news_collection.py
git commit -m "feat: classify source metadata in collection"
```


### Task 3: Attach Source Metadata During Collection And Enrichment

**Files:**
- Modify: `backend/services/news_collection.py`
- Test: `backend/tests/test_news_collection.py`

**Step 1: Write the failing test**

Add integration-level tests to ensure `collect_news()` and `enrich_sources()` emit tagged sources.

```python
async def test_collect_news_attaches_source_metadata():
    candidates, _meta = await collect_news()

    assert candidates[0].source_kind
    assert candidates[0].source_confidence
    assert candidates[0].source_tier


async def test_enrich_sources_preserves_source_metadata():
    enriched = await enrich_sources(groups, raw_content_map)

    first = enriched[group.primary_url][0]
    assert first["source_kind"]
    assert first["source_confidence"]
    assert first["source_tier"]
```

**Step 2: Run test to verify it fails**

Run: `backend\.venv\Scripts\python -m pytest backend\tests\test_news_collection.py -k "source_metadata and (collect_news or enrich_sources)" -v`

Expected: FAIL because the emitted payloads do not include metadata yet.

**Step 3: Write minimal implementation**

Update both flows:

```python
meta = _classify_source_meta(url=url, source="tavily", title=title)
NewsCandidate(..., **meta)
```

```python
meta = _classify_source_meta(url=item.url, source="merge", title=item.title)
sources = [{"url": item.url, "title": item.title, "content": ..., **meta}]
```

Rules:
- preserve existing `source` field for collector provenance
- add metadata without changing dedup logic
- reuse the same classifier helper in both collection and enrichment

**Step 4: Run test to verify it passes**

Run: `backend\.venv\Scripts\python -m pytest backend\tests\test_news_collection.py -k "source_metadata and (collect_news or enrich_sources)" -v`

Expected: PASS

**Step 5: Commit**

```bash
git add backend/services/news_collection.py backend/tests/test_news_collection.py
git commit -m "feat: attach source metadata to collected sources"
```


### Task 4: Surface Source Metadata In Digest Writer Input

**Files:**
- Modify: `backend/services/pipeline.py`
- Test: `backend/tests/test_pipeline_digest_validation.py`

**Step 1: Write the failing test**

Add a focused test around `_generate_digest()` input formatting.

```python
async def test_generate_digest_includes_source_metadata_labels_in_writer_prompt():
    ...
    assert "Source 1 [PRIMARY / official_site / high]:" in captured_user_prompt
    assert "Source 2 [SECONDARY / media / high]:" in captured_user_prompt
```

**Step 2: Run test to verify it fails**

Run: `backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_digest_validation.py -k source_metadata_labels -v`

Expected: FAIL because the prompt currently emits plain `Source N: URL`.

**Step 3: Write minimal implementation**

Change the source block rendering inside `_generate_digest()` to include metadata:

```python
label = f"{src.get('source_tier', '').upper()} / {src.get('source_kind', '')} / {src.get('source_confidence', '')}"
source_blocks.append(f"Source {i} [{label}]: {src['url']}\n{content[:12000]}")
```

If metadata is missing, fall back to current output shape instead of crashing.

**Step 4: Run test to verify it passes**

Run: `backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_digest_validation.py -k source_metadata_labels -v`

Expected: PASS

**Step 5: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_pipeline_digest_validation.py
git commit -m "feat: pass source metadata into digest prompts"
```


### Task 5: Persist Source Metadata In Saved Post Payloads

**Files:**
- Modify: `backend/services/pipeline.py`
- Modify: `backend/models/news_pipeline.py`
- Test: `backend/tests/test_pipeline_digest_validation.py`
- Test: `backend/tests/test_fact_pack_models.py`

**Step 1: Write the failing test**

Add assertions that saved `source_cards` and `guide_items` source payloads retain metadata.

```python
async def test_generate_digest_saves_source_cards_with_source_metadata():
    ...
    assert payload["source_cards"][0]["source_kind"] == "official_site"
    assert payload["source_cards"][0]["source_confidence"] == "high"
    assert payload["source_cards"][0]["source_tier"] == "primary"
```

If `FactSource` is used in typed validation for fact packs, add a model-level test there too.

**Step 2: Run test to verify it fails**

Run: `backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_digest_validation.py -k source_cards_with_source_metadata -v`

Expected: FAIL because metadata is currently dropped when citations are renumbered and titles are merged.

**Step 3: Write minimal implementation**

Update the source-card merge helpers to preserve metadata:

```python
source_cards.append({
    "id": num,
    "url": url,
    "title": "",
    "source_kind": source_meta.get(url, {}).get("source_kind", ""),
    "source_confidence": source_meta.get(url, {}).get("source_confidence", ""),
    "source_tier": source_meta.get(url, {}).get("source_tier", ""),
})
```

Also ensure `_fill_source_titles()` keeps the metadata keys intact.

**Step 4: Run test to verify it passes**

Run: `backend\.venv\Scripts\python -m pytest backend\tests\test_pipeline_digest_validation.py -k source_cards_with_source_metadata -v`

Expected: PASS

**Step 5: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_pipeline_digest_validation.py backend/tests/test_fact_pack_models.py
git commit -m "feat: persist source metadata in digest payloads"
```


### Task 6: Add Prompt Guidance That Uses The Metadata

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py`
- Test: `backend/tests/test_news_digest_prompts.py`

**Step 1: Write the failing test**

Add prompt assertions for metadata-aware wording.

```python
def test_business_prompt_uses_source_metadata_for_front_load_calibration():
    prompt = get_digest_prompt("business", "expert", [])
    assert "PRIMARY sources can support direct factual statements in the headline, excerpt, and first paragraph." in prompt
    assert "SECONDARY or analysis sources should be framed more cautiously in those front-loaded positions." in prompt
```

**Step 2: Run test to verify it fails**

Run: `backend\.venv\Scripts\python -m pytest backend\tests\test_news_digest_prompts.py -k source_metadata_for_front_load_calibration -v`

Expected: FAIL because the prompt does not mention source metadata yet.

**Step 3: Write minimal implementation**

Add one short rule block to the business prompt only:

```text
SOURCE METADATA CALIBRATION:
- PRIMARY sources can support direct factual statements in the headline, excerpt, and first paragraph.
- SECONDARY, analysis, or community-derived claims should be framed more cautiously in those front-loaded positions.
```

Keep this scoped to business prompt behavior only for now.

**Step 4: Run test to verify it passes**

Run: `backend\.venv\Scripts\python -m pytest backend\tests\test_news_digest_prompts.py -k source_metadata_for_front_load_calibration -v`

Expected: PASS

**Step 5: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py backend/tests/test_news_digest_prompts.py
git commit -m "fix: calibrate business prompt with source metadata"
```


### Task 7: Run Cross-File Regression Tests

**Files:**
- Test: `backend/tests/test_news_pipeline_models.py`
- Test: `backend/tests/test_news_collection.py`
- Test: `backend/tests/test_pipeline_digest_validation.py`
- Test: `backend/tests/test_news_digest_prompts.py`
- Test: `backend/tests/test_pipeline.py`
- Test: `backend/tests/test_pipeline_rerun.py`

**Step 1: Run the focused regression suite**

Run:

```bash
backend\.venv\Scripts\python -m pytest ^
  backend\tests\test_news_pipeline_models.py ^
  backend\tests\test_news_collection.py ^
  backend\tests\test_pipeline_digest_validation.py ^
  backend\tests\test_news_digest_prompts.py ^
  backend\tests\test_pipeline.py ^
  backend\tests\test_pipeline_rerun.py
```

Expected: PASS

**Step 2: Manual verification**

Run one `2026-04-13` rewrite and inspect:
- `source_cards` contain metadata
- prompt input shows `[PRIMARY / ...]` labels
- business title/excerpt tone becomes more fact-led when only secondary coverage exists

**Step 3: Commit final integration checkpoint**

```bash
git add backend
git commit -m "feat: add source metadata tiering to news pipeline"
```


### Notes

- Do not add LLM-based source classification in this pass.
- Do not change scoring logic in this pass.
- Do not modify research prompt behavior in this pass except where metadata must flow through shared code.
- Preserve current citation renumbering and source URL dedup behavior.
