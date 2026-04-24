# CP Citation Pattern Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Community Pulse links clickable and reliable by extending the news writer's proven `[CITE_N]` citation pattern to the CP section, eliminating the fragile bold-inline-link markdown and the `_inject_cp_citations` post-processor.

**Architecture:** Writer treats CP identically to body paragraphs. Each CP block header and each blockquote attribution carries a trailing `[CITE_N]` token; the `citations[]` sidecar carries entries whose `url` values come from the CP Data input (`HackerNewsURL` / `RedditURL`). The strict JSON schema's `citations[].url` enum is extended to include those thread URLs, so the writer cannot emit an unknown URL. After the call, `apply_citations` substitutes `[CITE_N]` → `[N](URL)` uniformly for body and CP — same contract. The post-processor and its regex infrastructure are deleted. This plan also fixes the P1-1 ranking issue by filtering `community_map` through `community_summary_map` before ranking, so irrelevant threads (summarizer-marked `sentiment=null`) cannot influence Lead/Supporting scoring.

**Tech Stack:** Python 3.11, Pydantic v2, pytest. Backend is FastAPI + Supabase on Railway. No new dependencies.

---

## Prerequisite context

- **Repo:** `c:\Users\amy\Desktop\0to1log` on `main` (main-only workflow per CLAUDE.md — no feature branches)
- **Python venv:** `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe` (never `backend/venv`)
- **Design doc:** `vault/09-Implementation/plans/2026-04-24-cp-pipeline-redesign-design.md` — read this first for architectural rationale
- **Prior session context (kept, not rolled back):** commits `13afc76` (helper extraction — kept), `f0ab746` (URL plumbing into CP Data — kept), `f501c38` `5c84fd4` (bold-link rule 9 + skeletons — REPLACED by Tasks 3+4 here), `6397274` (QC EXEMPT — REPLACED by Task 5), `3d950fc` `0c9f01d` (post-processor + Case 1 validation — DELETED by Task 6), `0dafd8a` (revert of I-1)
- **Commit policy:** `feat:/fix:/chore:/refactor:/docs:` prefix, no `Co-Authored-By`. One commit per task.
- **Date convention:** Today is 2026-04-24; use absolute dates in comments and journal notes.

---

## File structure

| File | Responsibility | Task |
|---|---|---|
| `backend/services/pipeline_digest.py` | URL allowlist builder, remove `_inject_cp_citations` | 1, 6 |
| `backend/services/pipeline.py` | Ranking call site, remove re-export of `_inject_cp_citations` | 2, 6 |
| `backend/services/agents/prompts_news_pipeline.py` | Rule 9, 8 skeletons, 4 QC rubrics | 3, 4, 5 |
| `backend/tests/test_cp_allowlist.py` | NEW — allowlist includes thread URLs | 1 |
| `backend/tests/test_ranking_filtered_community.py` | NEW — ranking ignores irrelevant threads | 2 |
| `backend/tests/test_cp_skeleton_cite_pattern.py` | NEW — skeletons use `[CITE_N]` shape | 4 |
| `backend/tests/test_cp_integration.py` | NEW — end-to-end `[CITE_N]` → `[N](url)` in CP | 7 |
| `backend/tests/test_cp_citation_injection.py` | DELETED | 6 |
| `backend/tests/test_cp_skeleton_format.py` | DELETED | 4 |
| `backend/scripts/smoke_cp_citations.py` | DELETED | 6 |

---

## Task 1: Extend URL allowlist with thread URLs

**Why:** The writer's strict json_schema uses `citations[].url` as an enum to prevent URL hallucination. Today the allowlist is built from classified items + enriched URLs. For the writer to emit `[CITE_N]` with a thread URL in CP, that URL must be in the enum. Add thread URLs from the `community_summary_map` to the allowlist.

**Files:**
- Modify: `backend/services/pipeline_digest.py` — find the `allowlist_urls: list[str] = []` build (inside `_generate_digest`, currently around line 620 after Tasks 1-2 of the prior plan landed)
- Create: `backend/tests/test_cp_allowlist.py`

**Step 1: Write the failing test**

Create `backend/tests/test_cp_allowlist.py`:

```python
"""Tests for the writer URL allowlist — it must include thread URLs
(hn_url / reddit_url) from community_summary_map so the writer can emit
[CITE_N] entries pointing at them without schema rejection."""

from models.news_pipeline import ClassifiedGroup, CommunityInsight, GroupedItem


def _make_group(primary_url: str, items_urls: list[str]) -> ClassifiedGroup:
    return ClassifiedGroup(
        group_title="X",
        items=[GroupedItem(url=u, title="x", subcategory="news") for u in items_urls],
        category="research",
        subcategory="news",
        reason="[LEAD] x",
        primary_url=primary_url,
    )


def test_allowlist_includes_hn_url_from_insight():
    from services.pipeline_digest import _build_writer_url_allowlist

    groups = [_make_group("https://example.com/story", ["https://example.com/story"])]
    community_summary_map = {
        "https://example.com/story": CommunityInsight(
            source_label="Hacker News 79↑",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    allowlist = _build_writer_url_allowlist(groups, community_summary_map, {})
    assert "https://news.ycombinator.com/item?id=42" in allowlist


def test_allowlist_includes_reddit_url_from_insight():
    from services.pipeline_digest import _build_writer_url_allowlist

    groups = [_make_group("https://example.com/story", ["https://example.com/story"])]
    community_summary_map = {
        "https://example.com/story": CommunityInsight(
            source_label="r/AI (500↑)",
            reddit_url="https://www.reddit.com/r/AI/comments/abc/t/",
        ),
    }
    allowlist = _build_writer_url_allowlist(groups, community_summary_map, {})
    assert "https://www.reddit.com/r/AI/comments/abc/t/" in allowlist


def test_allowlist_includes_both_urls_when_present():
    from services.pipeline_digest import _build_writer_url_allowlist

    groups = [_make_group("https://example.com/story", ["https://example.com/story"])]
    community_summary_map = {
        "https://example.com/story": CommunityInsight(
            source_label="Hacker News 1041↑ · r/OpenAI (642↑)",
            hn_url="https://news.ycombinator.com/item?id=1",
            reddit_url="https://www.reddit.com/r/OpenAI/comments/x/t/",
        ),
    }
    allowlist = _build_writer_url_allowlist(groups, community_summary_map, {})
    assert "https://news.ycombinator.com/item?id=1" in allowlist
    assert "https://www.reddit.com/r/OpenAI/comments/x/t/" in allowlist


def test_allowlist_still_includes_group_items_and_enriched():
    from services.pipeline_digest import _build_writer_url_allowlist

    groups = [_make_group("https://example.com/story", [
        "https://example.com/story",
        "https://example.com/item2",
    ])]
    enriched_map = {
        "https://example.com/story": [
            {"url": "https://example.com/related1"},
            {"url": "https://example.com/related2"},
        ],
    }
    allowlist = _build_writer_url_allowlist(groups, {}, enriched_map)
    assert "https://example.com/story" in allowlist
    assert "https://example.com/item2" in allowlist
    assert "https://example.com/related1" in allowlist
    assert "https://example.com/related2" in allowlist


def test_allowlist_handles_missing_insight_gracefully():
    from services.pipeline_digest import _build_writer_url_allowlist

    groups = [_make_group("https://example.com/story", ["https://example.com/story"])]
    # Insight with no URLs (old checkpoint)
    community_summary_map = {
        "https://example.com/story": CommunityInsight(source_label="Hacker News 5↑"),
    }
    allowlist = _build_writer_url_allowlist(groups, community_summary_map, {})
    assert allowlist == ["https://example.com/story"]
```

**Step 2: Run test to verify it fails**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_allowlist.py -v`

Expected: FAIL with `ImportError: cannot import name '_build_writer_url_allowlist'`

**Step 3: Extract and extend the allowlist builder**

In `backend/services/pipeline_digest.py`, find the allowlist construction inside `_generate_digest`. It currently looks like:

```python
# Build URL allowlist matching pipeline_quality._check_digest_quality (line 588+):
# every group.items[].url + every enriched_map anchor/related URL. The strict
# json_schema uses this as an enum, so the API rejects any URL the writer
# emits that isn't in the allowlist — writer hallucination is blocked at the
# API layer, not after the fact.
allowlist_urls: list[str] = []
for group in classified:
    for item in (group.items or []):
        if getattr(item, "url", None):
            allowlist_urls.append(item.url)
for anchor_url, enriched_list in (_enriched or {}).items():
    if anchor_url:
        allowlist_urls.append(anchor_url)
    for entry in (enriched_list or []):
        url = entry.get("url") if isinstance(entry, dict) else None
        if url:
            allowlist_urls.append(url)
```

Extract this block into a module-level helper near `_build_cp_data_entry` (around line 275):

```python
def _build_writer_url_allowlist(
    classified: "list[ClassifiedGroup]",
    community_summary_map: "dict[str, CommunityInsight] | None",
    enriched_map: "dict[str, list[dict]] | None",
) -> list[str]:
    """Build the URL allowlist used by the writer's strict json_schema enum.

    Includes:
    - Every classified group's item URLs (primary articles)
    - Every enriched_map anchor + related URL (post-classify expanded sources)
    - Every CommunityInsight's hn_url / reddit_url (so CP [CITE_N] citations
      point at thread URLs the writer was given in CP Data — prevents
      schema rejection on valid CP references)
    """
    allowlist: list[str] = []
    for group in classified:
        for item in (group.items or []):
            if getattr(item, "url", None):
                allowlist.append(item.url)
    for anchor_url, enriched_list in (enriched_map or {}).items():
        if anchor_url:
            allowlist.append(anchor_url)
        for entry in (enriched_list or []):
            url = entry.get("url") if isinstance(entry, dict) else None
            if url:
                allowlist.append(url)
    for insight in (community_summary_map or {}).values():
        if getattr(insight, "hn_url", None):
            allowlist.append(insight.hn_url)
        if getattr(insight, "reddit_url", None):
            allowlist.append(insight.reddit_url)
    return allowlist
```

Then replace the inline block inside `_generate_digest` with:

```python
allowlist_urls = _build_writer_url_allowlist(classified, community_summary_map, _enriched)
```

**Step 4: Run tests to verify they pass**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_allowlist.py -v`

Expected: 5 passed.

Full regression:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ --tb=short -q`

Expected: same baseline pass count as before.

Lint:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/services/pipeline_digest.py backend/tests/test_cp_allowlist.py`

Expected: `All checks passed!`

**Step 5: Commit**

```bash
git add backend/services/pipeline_digest.py backend/tests/test_cp_allowlist.py
git commit -m "feat(cp-allowlist): extend writer URL enum with thread URLs

Extract the allowlist builder into _build_writer_url_allowlist and
include hn_url/reddit_url from community_summary_map. The writer can
now legally emit [CITE_N] citations whose URL is an HN or Reddit thread
— the strict json_schema will accept them (and continue to reject any
hallucinated URL). Prep for Task 3+4 that instruct the writer to use
[CITE_N] for CP block headers and attributions."
```

---

## Task 2: Ranking uses filtered community map (P1-1 fix)

**Why:** External review (2026-04-24) flagged that ranking calls `rank_classified(..., community_map)` with the RAW community blobs. `summarize_community` runs before ranking and produces insights marked `sentiment=null` for off-topic threads, but ranking ignores that signal — so an irrelevant high-upvote HN thread still boosts the Lead/Supporting score of its group. Pre-filter `community_map` by the insights that summarizer accepted.

**Files:**
- Modify: `backend/services/pipeline.py` — the two `rank_classified(...)` call sites (currently around `pipeline.py:1488-1492`)
- Create: `backend/tests/test_ranking_filtered_community.py`

**Step 1: Write the failing test**

Create `backend/tests/test_ranking_filtered_community.py`:

```python
"""Tests for the pre-ranking filter that drops community_map entries
whose summarizer marked the thread as irrelevant (sentiment=null).
Without this filter, irrelevant high-upvote threads influence Lead/Supporting
ranking via their upvote counts."""

from models.news_pipeline import CommunityInsight


def test_filter_drops_null_sentiment_entries():
    from services.pipeline import _filter_community_map_by_summary

    community_map = {
        "https://a.example.com/story": "HN thread blob A with 500 upvotes",
        "https://b.example.com/story": "HN thread blob B with 1000 upvotes",
        "https://c.example.com/story": "HN thread blob C with 50 upvotes",
    }
    community_summary_map = {
        "https://a.example.com/story": CommunityInsight(sentiment="mixed", source_label="HN 500↑"),
        "https://b.example.com/story": CommunityInsight(sentiment=None, source_label="HN 1000↑"),  # off-topic
        "https://c.example.com/story": CommunityInsight(sentiment="negative", source_label="HN 50↑"),
    }
    filtered = _filter_community_map_by_summary(community_map, community_summary_map)
    assert "https://a.example.com/story" in filtered
    assert "https://c.example.com/story" in filtered
    # Irrelevant thread excluded
    assert "https://b.example.com/story" not in filtered


def test_filter_drops_entries_with_no_insight():
    """If the summarizer produced no insight for a URL (mapping missing),
    treat it as unclassified and exclude — same as sentiment=null."""
    from services.pipeline import _filter_community_map_by_summary

    community_map = {
        "https://a.example.com/story": "blob A",
        "https://missing.example.com/story": "blob without insight",
    }
    community_summary_map = {
        "https://a.example.com/story": CommunityInsight(sentiment="positive", source_label="HN 10↑"),
    }
    filtered = _filter_community_map_by_summary(community_map, community_summary_map)
    assert "https://a.example.com/story" in filtered
    assert "https://missing.example.com/story" not in filtered


def test_filter_handles_empty_summary_map():
    """Defensive: if summarizer failed entirely, pass through unchanged
    (don't break ranking by filtering everything out)."""
    from services.pipeline import _filter_community_map_by_summary

    community_map = {
        "https://a.example.com/story": "blob A",
    }
    filtered = _filter_community_map_by_summary(community_map, {})
    # Empty summary map → pass through (graceful degradation)
    assert filtered == community_map


def test_filter_handles_empty_community_map():
    from services.pipeline import _filter_community_map_by_summary

    community_summary_map = {
        "https://a.example.com/story": CommunityInsight(sentiment="mixed", source_label="HN 1↑"),
    }
    filtered = _filter_community_map_by_summary({}, community_summary_map)
    assert filtered == {}
```

**Step 2: Run test to verify it fails**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_ranking_filtered_community.py -v`

Expected: FAIL with `ImportError: cannot import name '_filter_community_map_by_summary'`

**Step 3: Implement the filter + use it at ranking call sites**

In `backend/services/pipeline.py`, add a module-level helper near the other `_*` helpers at the top of the file (or above `run_daily_pipeline`):

```python
def _filter_community_map_by_summary(
    community_map: dict[str, str],
    community_summary_map: dict[str, "CommunityInsight"],
) -> dict[str, str]:
    """Drop community_map entries whose summarizer marked the thread as
    irrelevant to the source article (sentiment=null). Without this filter,
    irrelevant high-upvote threads still influence ranking via their upvote
    counts. Graceful degradation: if summary_map is empty (summarizer
    failed entirely), pass community_map through unchanged — ranking
    operates on best-available data rather than nothing.
    """
    if not community_summary_map:
        return community_map
    return {
        url: raw
        for url, raw in community_map.items()
        if (ins := community_summary_map.get(url)) is not None
        and ins.sentiment is not None
    }
```

Then modify the ranking call sites at `pipeline.py:1488-1492` (find them by grep `rank_classified`):

Before:
```python
research_ranked, research_rank_usage = await rank_classified(
    classification.research, "research", community_map,
)
business_ranked, business_rank_usage = await rank_classified(
    classification.business, "business", community_map,
)
```

After:
```python
filtered_community_map = _filter_community_map_by_summary(
    community_map, community_summary_map,
)
research_ranked, research_rank_usage = await rank_classified(
    classification.research, "research", filtered_community_map,
)
business_ranked, business_rank_usage = await rank_classified(
    classification.business, "business", filtered_community_map,
)
```

**Step 4: Run tests**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_ranking_filtered_community.py -v`

Expected: 4 passed.

Full regression:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ --tb=short -q`

Lint:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/services/pipeline.py backend/tests/test_ranking_filtered_community.py`

**Step 5: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_ranking_filtered_community.py
git commit -m "fix(ranking): filter community_map by summary before ranking

External review finding (2026-04-24 P1-1): ranking called
rank_classified with the raw community_map, bypassing the summarizer's
relevance filter. Off-topic threads (sentiment=null) still influenced
Lead/Supporting ranking via their upvote counts. Pre-filter via
_filter_community_map_by_summary — drop entries whose insight is
sentiment=null or missing entirely.

Graceful degradation: if summary_map is empty (summarizer failed),
pass through unchanged so ranking runs on best-available data."
```

---

## Task 3: Rewrite writer rule 9 for `[CITE_N]` CP pattern

**Why:** Tasks 1-2 laid the plumbing. Now instruct the writer to USE the new pattern. Rule 9 becomes a short rule whose only novelty vs. body citations is WHICH URL goes in the citation for each CP block. The bold-inline-link instruction is deleted entirely.

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` — rule 9 (currently around line 346-355)

**No unit test** — prompt wording changes are verified by inspection + Task 4's skeleton snapshot test + Task 8's end-to-end smoke.

**Step 1: Read current rule 9**

Run:

```
cd c:/Users/amy/Desktop/0to1log && c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -c "
import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'backend')
from services.agents.prompts_news_pipeline import get_digest_prompt
p = get_digest_prompt('expert', 'business', ['sample'])
m = re.search(r'9\.\s*COMMUNITY PULSE[\s\S]*?(?=\n\{handbook|\n10\.|\n\n##)', p)
print(m.group(0) if m else 'NOT FOUND')
"
```

Expected output: the current rule 9 (post-revert, with `<url>` angle-bracket metavariables and bold-link `**[...](url)**` format).

**Step 2: Replace rule 9 with the CITE_N version**

In `backend/services/agents/prompts_news_pipeline.py`, locate the numbered rule 9 block. Replace it in full with:

```
9. COMMUNITY PULSE: write a single `## Community Pulse` (ko: `## 커뮤니티 반응`) section — see skeleton for exact format. For each topic in the Community Pulse Data input:
   - **Block header format (REQUIRED):** `**Hacker News** (N↑) — one-sentence sentiment summary [CITE_X]` where X is a citation number and `citations[X].url` equals the `HackerNewsURL` value from CP Data. For Reddit blocks: `**r/<subreddit>** (N↑) — sentiment summary [CITE_Y]` with `citations[Y].url = RedditURL`. The `[CITE_X]` token appears at the END of the block header line — same position as citations at the end of body paragraphs.
   - **Multi-platform topics:** if `Platform:` lists BOTH Hacker News AND r/<sub> (e.g. "Hacker News 1041↑ · 689 comments · r/OpenAI (642↑)"), emit TWO separate blocks — one per platform — each with its own `[CITE_N]` token whose URL matches that platform. Never combine them into one block.
   - `HasQuotes: yes` → emit blockquote(s) using the exact "English quote N" text in en and matching "Korean quote N" in ko. Each blockquote attribution: `> — Hacker News [CITE_X]` or `> — Reddit [CITE_Y]` where X/Y is the SAME citation number as the enclosing block header. Never put a Reddit quote under a Hacker News block (or vice versa) — if the quote clearly belongs to the OTHER platform, place it under that block.
   - `HasQuotes: no` → write ONE short paragraph based on Sentiment + Key Discussion, ending with `[CITE_X]`. Do NOT emit any blockquote. Do NOT invent quotes.
   - NEVER write literal `[EN quote]`, `[KO quote]`, `Quote (EN)`, or `Quote (KO)` in the output — these are input labels, not output text.
   - Omit the entire Community Pulse section only when no Community Pulse Data was provided.
```

Key points when editing:
- Keep the indentation style of surrounding text (probably `   - ` / `     - ` for nested lists)
- Keep the em-dash `—` (U+2014) consistent with the rest of the prompt
- Rules 1-8 and 10+ are untouched

**Step 3: Verify the new rule 9 lands in the rendered prompt**

Run:

```
cd c:/Users/amy/Desktop/0to1log && c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, 'backend')
from services.agents.prompts_news_pipeline import get_digest_prompt
p = get_digest_prompt('expert', 'business', ['sample'])
assert '**Hacker News** (N↑) — one-sentence sentiment summary [CITE_X]' in p, 'CITE_X block header format missing'
assert '> — Hacker News [CITE_X]' in p or '\`> — Hacker News [CITE_X]\`' in p, 'CITE_X attribution format missing'
assert 'Multi-platform topics' in p, 'multi-platform rule missing'
assert '**[Hacker News](' not in p.split('COMMUNITY PULSE')[1].split('handbook_section')[0].split('Output JSON format')[0], 'old bold-link format leaked into rule 9'
print('OK rule 9 CITE_N format landed')
"
```

Expected: `OK rule 9 CITE_N format landed`

**Step 4: Regression**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ --tb=short -q`

Expected: same baseline (the `test_cp_skeleton_format.py` tests WILL fail at this point — that's expected; they're replaced in Task 4).

Lint:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/services/agents/prompts_news_pipeline.py`

Expected: `All checks passed!`

**Step 5: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "feat(cp-prompt): rewrite rule 9 to use [CITE_N] pattern

Replace the failed bold-inline-link instruction (\`**[Label](URL)**\`)
with the same [CITE_N] pattern body paragraphs use: trailing [CITE_X]
token at the end of each block header and each attribution line; the
citations[] sidecar carries the URL value (HackerNewsURL or RedditURL
from CP Data). Multi-platform topics split into separate blocks, each
with its own [CITE_N].

The \`test_cp_skeleton_format.py\` assertions will fail at this commit
— skeletons still show the old bold-link format. Task 4 replaces the
skeletons and the test file together so the final state is coherent."
```

---

## Task 4: Rewrite 8 skeleton CP sections for `[CITE_N]` format

**Why:** Rule 9 instructs the writer; skeletons show it. Writers rely heavily on Show-Don't-Tell, so skeleton CP sections must demonstrate the new `[CITE_N]` pattern. Also replace the existing `test_cp_skeleton_format.py` (which asserts on the old bold-link format) with a new test file that asserts on the new `[CITE_N]` format.

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` — 8 CP sections inside the 4 skeleton constants (BUSINESS_EXPERT_SKELETON, BUSINESS_LEARNER_SKELETON, RESEARCH_EXPERT_SKELETON, RESEARCH_LEARNER_SKELETON) × 2 locales each (en + ko)
- Delete: `backend/tests/test_cp_skeleton_format.py`
- Create: `backend/tests/test_cp_skeleton_cite_pattern.py`

**Step 1: Write the failing test**

Create `backend/tests/test_cp_skeleton_cite_pattern.py`:

```python
"""Guards that every skeleton's Community Pulse section demonstrates the
new [CITE_N] citation pattern (not the old bold-inline-link format)."""

import re
import pytest


@pytest.mark.parametrize("constant_name", [
    "BUSINESS_EXPERT_SKELETON",
    "BUSINESS_LEARNER_SKELETON",
    "RESEARCH_EXPERT_SKELETON",
    "RESEARCH_LEARNER_SKELETON",
])
def test_skeleton_block_header_ends_with_cite_token(constant_name):
    import services.agents.prompts_news_pipeline as prompts

    skeleton = getattr(prompts, constant_name)
    # At least one block header line ending with [CITE_N]
    assert re.search(r"\*\*(?:Hacker News|r/[^*]+?)\*\*\s*\([^)]+?↑\)\s*—[^\n]+\[CITE_\d+\]", skeleton), (
        f"{constant_name} CP section must show block header ending with [CITE_N] "
        "(pattern: **Label** (N↑) — summary [CITE_N])"
    )


@pytest.mark.parametrize("constant_name", [
    "BUSINESS_EXPERT_SKELETON",
    "BUSINESS_LEARNER_SKELETON",
    "RESEARCH_EXPERT_SKELETON",
    "RESEARCH_LEARNER_SKELETON",
])
def test_skeleton_attribution_ends_with_cite_token(constant_name):
    import services.agents.prompts_news_pipeline as prompts

    skeleton = getattr(prompts, constant_name)
    # At least one attribution line ending with [CITE_N]
    assert re.search(r">\s*—\s*(?:Hacker News|Reddit|r/[^\[\n]+?)\s*\[CITE_\d+\]", skeleton), (
        f"{constant_name} must show attribution ending with [CITE_N] "
        "(pattern: > — Label [CITE_N])"
    )


@pytest.mark.parametrize("constant_name", [
    "BUSINESS_EXPERT_SKELETON",
    "BUSINESS_LEARNER_SKELETON",
    "RESEARCH_EXPERT_SKELETON",
    "RESEARCH_LEARNER_SKELETON",
])
def test_skeleton_has_no_bold_inline_link(constant_name):
    """After Task 4 lands, no skeleton should retain the failed
    `**[Label](URL)**` bold-inline-link format — that's the pattern
    the LLM cannot reliably produce."""
    import services.agents.prompts_news_pipeline as prompts

    skeleton = getattr(prompts, constant_name)
    # Scan only the CP section to avoid false positives from body example links
    cp_match = re.search(r"##\s*(?:Community Pulse|커뮤니티 반응)[\s\S]*?(?=\n##\s|\Z)", skeleton)
    assert cp_match, f"{constant_name} has no CP section"
    cp_body = cp_match.group(0)
    assert "**[Hacker News]" not in cp_body, (
        f"{constant_name} CP still contains old **[Hacker News](url)** pattern"
    )
    assert "**[r/" not in cp_body, (
        f"{constant_name} CP still contains old **[r/subreddit](url)** pattern"
    )


@pytest.mark.parametrize("constant_name", [
    "BUSINESS_EXPERT_SKELETON",
    "BUSINESS_LEARNER_SKELETON",
    "RESEARCH_EXPERT_SKELETON",
    "RESEARCH_LEARNER_SKELETON",
])
def test_skeleton_has_no_bare_attribution(constant_name):
    """Attribution must end with [CITE_N] — bare `> — Hacker News` without
    a citation token would signal pre-plan format. Guard against regression."""
    import re
    import services.agents.prompts_news_pipeline as prompts

    skeleton = getattr(prompts, constant_name)
    cp_match = re.search(r"##\s*(?:Community Pulse|커뮤니티 반응)[\s\S]*?(?=\n##\s|\Z)", skeleton)
    assert cp_match, f"{constant_name} has no CP section"
    cp_body = cp_match.group(0)
    bare = re.search(r"^>\s*—\s*(?:Hacker News|Reddit|r/\S+?)\s*$", cp_body, re.MULTILINE)
    assert bare is None, (
        f"{constant_name} CP still contains bare attribution '{bare.group(0) if bare else ''}' "
        "— must end with [CITE_N]"
    )
```

**Step 2: Run tests to verify they fail**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_skeleton_cite_pattern.py -v`

Expected: 16 FAIL — current skeletons still have `**[Label](URL)**` and no `[CITE_N]`.

**Step 3: Delete the old skeleton test file**

Delete: `backend/tests/test_cp_skeleton_format.py`

```bash
rm backend/tests/test_cp_skeleton_format.py
```

**Step 4: Rewrite each of the 8 CP sections**

Open `backend/services/agents/prompts_news_pipeline.py`. For each skeleton constant (`BUSINESS_EXPERT_SKELETON`, `BUSINESS_LEARNER_SKELETON`, `RESEARCH_EXPERT_SKELETON`, `RESEARCH_LEARNER_SKELETON`), locate its `## Community Pulse` (en) and `## 커뮤니티 반응` (ko) subsections — 8 total. Apply the transformation:

**Before (example from `BUSINESS_EXPERT_SKELETON` en):**

```
## Community Pulse

**[r/OpenAI](https://www.reddit.com/r/OpenAI/comments/ab12xy/openai_hiring_push/)** (2.1K↑) — OpenAI's hiring push is seen as accelerating industry consolidation, sparking concern over startup talent pipelines.

> "If OpenAI hoovers up 3,500 more engineers, every Series A startup just lost their candidate pipeline."
> — [r/OpenAI](https://www.reddit.com/r/OpenAI/comments/ab12xy/openai_hiring_push/)

**[Hacker News](https://news.ycombinator.com/item?id=3941872)** (890↑) — Debate centers on the strategic pivot away from consumer products toward enterprise margins.

> "The real story is the pivot away from consumer -- enterprise margins are where the IPO math works."
> — [Hacker News](https://news.ycombinator.com/item?id=3941872)
```

**After:**

```
## Community Pulse

**r/OpenAI** (2.1K↑) — OpenAI's hiring push is seen as accelerating industry consolidation, sparking concern over startup talent pipelines. [CITE_3]

> "If OpenAI hoovers up 3,500 more engineers, every Series A startup just lost their candidate pipeline."
> — Reddit [CITE_3]

**Hacker News** (890↑) — Debate centers on the strategic pivot away from consumer products toward enterprise margins. [CITE_4]

> "The real story is the pivot away from consumer -- enterprise margins are where the IPO math works."
> — Hacker News [CITE_4]
```

Rules for the rewrite:
1. Block header: strip `**[Label](URL)**` wrapping → plain `**Label**`. Keep upvote parens + em-dash + summary. Append ` [CITE_N]` at end of line (pick a sequential N — example uses 3, 4 since body examples typically occupy 1, 2).
2. Attribution: strip `— [Label](URL)` → plain `— Label` (Reddit for r/ blocks, Hacker News for HN blocks). Append ` [CITE_N]` matching the block header.
3. Reuse the SAME citation number between a block header and its attribution(s). That's the whole point — citation number ties them together.
4. Keep the Korean body text in `## 커뮤니티 반응` unchanged — translate only the markup, not the prose.
5. The EN skeleton and KO skeleton within a single constant should use the same CITE_N numbers for the same blocks (since the writer output has unified citations[] across both locales).

Apply to all 8 sections:
- `BUSINESS_EXPERT_SKELETON` en + ko
- `BUSINESS_LEARNER_SKELETON` en + ko
- `RESEARCH_EXPERT_SKELETON` en + ko
- `RESEARCH_LEARNER_SKELETON` en + ko

**Step 5: Run tests to verify they pass**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_skeleton_cite_pattern.py -v`

Expected: 16 passed.

Verify the old test file is gone:

Run: `ls backend/tests/test_cp_skeleton_format.py 2>&1 || echo "deleted"`

Expected: `deleted`.

Full regression:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ --tb=short -q`

Lint:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/services/agents/prompts_news_pipeline.py backend/tests/test_cp_skeleton_cite_pattern.py`

**Step 6: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py backend/tests/test_cp_skeleton_cite_pattern.py
git rm backend/tests/test_cp_skeleton_format.py
git commit -m "feat(cp-skeleton): rewrite 8 CP sections to [CITE_N] pattern

Replace bold-inline-link format (\`**[Label](URL)**\` + \`> — [Label](url)\`)
with the [CITE_N] pattern that matches body citations: \`**Label** (N↑) —
summary [CITE_X]\` block headers and \`> — Label [CITE_X]\` attributions.
Each block header and its attributions share the same X number.

Delete test_cp_skeleton_format.py (asserts on old bold-link format) and
replace with test_cp_skeleton_cite_pattern.py — 16 parametrized tests
covering block header CITE_N, attribution CITE_N, no bold-link leakage,
no bare attribution."
```

---

## Task 5: Remove CP EXEMPT from 4 QC rubrics

**Why:** CP now uses `[N](url)` citations at the end of block headers and attributions — the SAME format as body paragraphs. The `citation_coverage` QC sub-score can apply uniformly; the `EXEMPT: CP section uses a different format` bullet is obsolete. Removing it simplifies the rubric and prevents the scorer from under-crediting CP traceability.

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` — 4 locations where the EXEMPT sentence currently appears (one per quality rubric; they are character-identical since the 2026-04-24 prior Task 5 applied `replace_all`)

**Step 1: Verify current wording appears exactly 4 times**

Run:

```
cd c:/Users/amy/Desktop/0to1log && c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -c "
content = open('backend/services/agents/prompts_news_pipeline.py', encoding='utf-8').read()
marker = 'Do NOT penalize CP attributions for having a link'
print('occurrences:', content.count(marker))
"
```

Expected: `occurrences: 4`.

If not 4, STOP and report — the prior Task 5 wording may have drifted.

**Step 2: Remove the entire EXEMPT sentence**

Edit `backend/services/agents/prompts_news_pipeline.py`. Using `replace_all`, change this sentence:

```
 **EXEMPT**: the `## 커뮤니티 반응` (Community Pulse) section — its block headers use `**[Platform](URL)** (N↑)` and its quotes use `> — [Platform](URL)` attribution, NOT inline `[N](URL)` placeholders. Do NOT penalize CP blocks for missing inline citations. Do NOT penalize CP attributions for having a link — that IS the format.
```

To an empty string (remove it entirely). Keep a single space around the boundary so the surrounding bullet prose stays well-formed — if the EXEMPT sentence is the last part of a bullet's description, deletion leaves the bullet's primary rule intact (`citation_coverage: Every body paragraph ends with [N](URL) citation.`).

Verify the `citation_coverage` bullet's primary rule still exists and reads cleanly:

Run:

```
cd c:/Users/amy/Desktop/0to1log && c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -c "
content = open('backend/services/agents/prompts_news_pipeline.py', encoding='utf-8').read()
# Primary rule text must still appear 4×
print('primary rule occurrences:', content.count('Every body paragraph ends with'))
# EXEMPT text must be gone
print('EXEMPT occurrences:', content.count('**EXEMPT**: the \`## 커뮤니티 반응\`'))
print('link-format marker occurrences:', content.count('Do NOT penalize CP attributions'))
"
```

Expected: primary rule 4; EXEMPT 0; link-format marker 0.

**Step 3: Full regression**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ --tb=short -q`

Lint:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/services/agents/prompts_news_pipeline.py`

**Step 4: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "chore(cp-qc): remove CP exemption from citation_coverage rubric

CP section now uses [N](url) citations at the end of block headers and
attributions — same format as body paragraphs. The EXEMPT bullet that
told the scorer \"CP uses a different format, don't require inline
citations\" is obsolete. Citation coverage applies uniformly; CP
block headers and attributions meet the rule naturally via their
trailing [CITE_N] tokens."
```

---

## Task 6: Delete `_inject_cp_citations` and its infrastructure

**Why:** Tasks 1-5 make the writer produce clean CP markdown with `[CITE_N]` tokens that `apply_citations` substitutes into `[N](url)` — same path as body. The post-processor is no longer needed. Deleting it removes a whole category of subtle bugs (idempotency, URL validation, regex edge cases) and reduces pipeline_digest.py's surface area.

**Files:**
- Modify: `backend/services/pipeline_digest.py` — remove function, helpers, and 2 call sites
- Modify: `backend/services/pipeline.py` — remove `_inject_cp_citations` from the re-export block (currently line ~3288 per the Task 1 implementer's output)
- Delete: `backend/tests/test_cp_citation_injection.py` (16 tests — all relate to the deleted function)
- Delete: `backend/scripts/smoke_cp_citations.py` (counts linked-vs-raw attributions — no bare attributions exist after Task 3+4)

**Step 1: Identify and verify what to delete**

Run:

```
cd c:/Users/amy/Desktop/0to1log && c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m grep -n "_inject_cp_citations\|_CP_LINKED_HEADER_RE\|_CP_LINKED_ATTR_RE\|_CP_BLOCK_HEADER_RE\|_CP_ATTR_RE_TMPL\|_CP_HEADERS\|_INSIGHT_UPVOTE_RE\|_upvotes_to_int\|_insight_hn_upvotes\|_insight_reddit_upvotes" backend/services/pipeline_digest.py || true
```

(If that `-m grep` doesn't work in your shell, use `grep -n` directly.) Confirm the listed helpers all live in `pipeline_digest.py`. Expected: helper definitions clustered near the top of the file (around lines 55-210 per prior plan) and the `_inject_cp_citations` call sites around lines 1242-1243.

**Step 2: Remove the post-processor call sites in `pipeline_digest.py`**

Find the two call sites (they surround the writer output cleaning inside `_generate_digest`, roughly):

```python
expert_content = _inject_cp_citations(expert_content, community_summary_map)
learner_content = _inject_cp_citations(learner_content, community_summary_map)
```

Delete these two lines entirely. The lines before/after should already be the writer-output post-processing path; nothing else needs adjustment.

**Step 3: Remove all the helper definitions**

Still in `backend/services/pipeline_digest.py`, remove the entire block containing:

- `_CP_HEADERS` tuple
- `_CP_BLOCK_HEADER_RE`
- `_CP_ATTR_RE_TMPL`
- `_INSIGHT_UPVOTE_RE`
- `_upvotes_to_int`
- `_insight_hn_upvotes`
- `_insight_reddit_upvotes`
- `_CP_LINKED_HEADER_RE`
- `_CP_LINKED_ATTR_RE`
- `_inject_cp_citations` (the function itself)

These live in a contiguous block around lines 55-210. Delete the whole block. Keep `_build_cp_data_entry` (Task 1 prior, still in use) and `_build_writer_url_allowlist` (new, this plan's Task 1).

Leave the module's imports intact — `re` is still used elsewhere.

**Step 4: Remove from re-export block in `pipeline.py`**

Find `_inject_cp_citations` in the re-export list at the bottom of `backend/services/pipeline.py` (around line 3285-3290 after the prior plan). Delete that single line.

**Step 5: Delete the two obsolete files**

```bash
rm backend/tests/test_cp_citation_injection.py
rm backend/scripts/smoke_cp_citations.py
```

**Step 6: Run tests and lint**

Full regression:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ --tb=short -q`

Expected: same baseline — 16 tests from `test_cp_citation_injection.py` no longer present (deleted file), but no other failures. Any import error from leftover `_inject_cp_citations` references → fix by grepping and removing.

Lint:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/`

Expected: `All checks passed!`

**Step 7: Commit**

```bash
git add backend/services/pipeline_digest.py backend/services/pipeline.py
git rm backend/tests/test_cp_citation_injection.py backend/scripts/smoke_cp_citations.py
git commit -m "refactor(cp-postproc): delete _inject_cp_citations infrastructure

The post-processor's job — linkifying bare CP attributions and block
headers — is obsolete. Writer emits [CITE_N] directly (Tasks 3-4),
apply_citations substitutes into [N](url) (same path as body), schema
enum enforces URL correctness (Task 1). No separate CP post-processor
needed.

Deleted: _inject_cp_citations function, _CP_HEADERS, _CP_BLOCK_HEADER_RE,
_CP_ATTR_RE_TMPL, _CP_LINKED_HEADER_RE, _CP_LINKED_ATTR_RE,
_INSIGHT_UPVOTE_RE, _upvotes_to_int, _insight_hn_upvotes,
_insight_reddit_upvotes. Also deleted test_cp_citation_injection.py
(16 tests covering the removed function) and smoke_cp_citations.py
(counts linked-vs-raw — no bare attributions exist now)."
```

---

## Task 7: Integration test — end-to-end CP `[CITE_N]` substitution

**Why:** Tasks 1-6 land individual pieces. A single integration test verifies the end-to-end path: writer emits a realistic CP body with `[CITE_N]` tokens and a matching `citations[]` sidecar; `apply_citations` substitutes uniformly; final markdown has clickable `[N](url)` in block headers and attributions; no bare attributions; no post-processor involved.

**Files:**
- Create: `backend/tests/test_cp_integration.py`

**Step 1: Write the integration test**

Create `backend/tests/test_cp_integration.py`:

```python
"""End-to-end CP citation path: writer emits [CITE_N] tokens, apply_citations
substitutes into [N](url). Same infrastructure as body citations — proves the
CP section and body share the same contract."""

from services.agents.citation_substitution import apply_citations


def test_cp_body_cite_substitution_end_to_end():
    """Realistic writer output: body paragraphs + CP section, all with
    [CITE_N] tokens. apply_citations substitutes uniformly."""
    writer_body = """## One-Line Summary
OpenAI launched GPT-5.5 with expanded reasoning. [CITE_1]

## Big Tech
### GPT-5.5 launch

OpenAI announced GPT-5.5 today. [CITE_1]

The model targets enterprise. [CITE_2]

## Community Pulse

**Hacker News** (1041↑) — Mixed reactions center on guardrails and pricing. [CITE_3]

> "Laughed a little to this 'We are releasing GPT-5.5...'"
> — Hacker News [CITE_3]

**r/OpenAI** (642↑) — Pricing draws pushback from developers. [CITE_4]

> "$30 per million output? I thought we were democratising intelligence?!"
> — Reddit [CITE_4]
"""
    citations = [
        {"n": 1, "url": "https://openai.com/index/introducing-gpt-5-5/"},
        {"n": 2, "url": "https://techcrunch.com/2026/04/24/gpt55/"},
        {"n": 3, "url": "https://news.ycombinator.com/item?id=47879092"},
        {"n": 4, "url": "https://www.reddit.com/r/OpenAI/comments/1stqlnh/introducing_gpt55_openai/"},
    ]

    result = apply_citations(writer_body, citations)

    # Body paragraphs substituted
    assert "[1](https://openai.com/index/introducing-gpt-5-5/)" in result
    assert "[2](https://techcrunch.com/2026/04/24/gpt55/)" in result

    # CP block headers substituted
    assert (
        "**Hacker News** (1041↑) — Mixed reactions center on guardrails and pricing. "
        "[3](https://news.ycombinator.com/item?id=47879092)"
    ) in result
    assert (
        "**r/OpenAI** (642↑) — Pricing draws pushback from developers. "
        "[4](https://www.reddit.com/r/OpenAI/comments/1stqlnh/introducing_gpt55_openai/)"
    ) in result

    # CP attributions substituted
    assert "> — Hacker News [3](https://news.ycombinator.com/item?id=47879092)" in result
    assert (
        "> — Reddit [4](https://www.reddit.com/r/OpenAI/comments/1stqlnh/introducing_gpt55_openai/)"
    ) in result

    # No unreplaced [CITE_N] tokens
    assert "[CITE_" not in result

    # No bare attributions
    import re
    bare = re.search(r"^>\s*—\s*(?:Hacker News|Reddit|r/\S+?)\s*$", result, re.MULTILINE)
    assert bare is None, f"Found bare attribution: {bare.group(0) if bare else ''}"


def test_cp_multi_platform_topic_uses_two_cite_numbers():
    """A group with both HN + Reddit threads → writer emits TWO blocks,
    each with its own [CITE_N]. Substitution produces distinct URLs for each."""
    writer_body = """## Community Pulse

**Hacker News** (1041↑) — HN discussion focuses on guardrails. [CITE_3]

> "guardrails quote"
> — Hacker News [CITE_3]

**r/OpenAI** (642↑) — Reddit discussion focuses on pricing. [CITE_4]

> "pricing quote"
> — Reddit [CITE_4]
"""
    citations = [
        {"n": 3, "url": "https://news.ycombinator.com/item?id=47879092"},
        {"n": 4, "url": "https://www.reddit.com/r/OpenAI/comments/1stqlnh/x/"},
    ]

    result = apply_citations(writer_body, citations)

    # Two distinct URLs land in two distinct blocks
    assert "[3](https://news.ycombinator.com/item?id=47879092)" in result
    assert "[4](https://www.reddit.com/r/OpenAI/comments/1stqlnh/x/)" in result
    # Count occurrences — each CITE_N appears exactly twice (header + attribution)
    assert result.count("[3](https://news.ycombinator.com/item?id=47879092)") == 2
    assert result.count("[4](https://www.reddit.com/r/OpenAI/comments/1stqlnh/x/)") == 2


def test_cp_has_no_quotes_block_substitutes_cite_in_paragraph():
    """HasQuotes: no → writer emits paragraph ending with [CITE_N],
    no blockquote. Substitution still works."""
    writer_body = """## Community Pulse

**r/OpenAI** (642↑) — Discussion is muted despite high upvote count; most comments are off-topic. [CITE_3]
"""
    citations = [
        {"n": 3, "url": "https://www.reddit.com/r/OpenAI/comments/xyz/t/"},
    ]

    result = apply_citations(writer_body, citations)

    assert "[3](https://www.reddit.com/r/OpenAI/comments/xyz/t/)" in result


def test_apply_citations_raises_on_missing_cite_target():
    """Safety: if the writer emits [CITE_N] but citations[] has no matching n,
    apply_citations raises loudly — same contract as body."""
    from services.agents.citation_substitution import CitationSubstitutionError

    writer_body = "**Hacker News** (79↑) — summary. [CITE_9]"
    citations = [{"n": 1, "url": "https://x.com/"}]

    import pytest
    with pytest.raises(CitationSubstitutionError):
        apply_citations(writer_body, citations)
```

**Step 2: Run the test**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_integration.py -v`

Expected: 4 passed.

Full regression:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ --tb=short -q`

Lint:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/tests/test_cp_integration.py`

**Step 3: Commit**

```bash
git add backend/tests/test_cp_integration.py
git commit -m "test(cp): integration — [CITE_N] substitution works end-to-end

Realistic writer output with CP block headers + attributions carrying
[CITE_N] tokens; apply_citations substitutes into [N](url) uniformly
with body citations. Covers multi-platform topic (two [CITE_N] in one
CP section), HasQuotes=no paragraph path, and the missing-citation
failure mode (raises CitationSubstitutionError)."
```

---

## Task 8: Apr 24 rerun-from-write validation

**Why:** Tasks 1-7 are verified in unit + integration tests. Task 8 proves the whole chain works on real cron data against the live Railway backend. Also records evidence in a journal note.

**Files:** no modifications — script-only validation + journal entry.

**Step 1: Wait for Railway deploy**

After pushing Task 7's commit, Railway auto-deploys `main`. Typical deploy time is 2-4 minutes. Verify by waiting ~3 minutes after push, or tailing Railway logs.

**Step 2: Trigger rerun from write on Apr 24**

```bash
CRON_SECRET=$(grep '^CRON_SECRET=' c:/Users/amy/Desktop/0to1log/backend/.env | cut -d= -f2-)
curl -sS -X POST https://0to1log-production.up.railway.app/api/cron/pipeline-rerun \
  -H "Content-Type: application/json" \
  -H "x-cron-secret: $CRON_SECRET" \
  -d '{"run_id":"a1ee1bec-8f18-415c-98c6-7d1a66e5482f","from_stage":"write","batch_id":"2026-04-24","category":null}'
```

Expected response: `{"status":"accepted", ...}`.

**Step 3: Poll for completion (8-15 minutes expected)**

Run this polling script in the background:

```python
# Save as /tmp/wait_apr24_rerun.py
import io, os, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"c:\Users\amy\Desktop\0to1log\backend")
from dotenv import load_dotenv
load_dotenv(r"c:\Users\amy\Desktop\0to1log\backend\.env")
from supabase import create_client

sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"],
)
RUN_ID = "a1ee1bec-8f18-415c-98c6-7d1a66e5482f"
start = time.monotonic()
for _ in range(40):
    r = sb.table("pipeline_runs").select("status,finished_at,last_error").eq("id", RUN_ID).execute().data[0]
    if r["status"] in ("success", "failed") and r.get("finished_at"):
        elapsed = time.monotonic() - start
        print(f"DONE after {elapsed:.0f}s status={r['status']} last_error={(r.get('last_error') or '')[:200]}")
        break
    time.sleep(30)
else:
    print("TIMEOUT after 20min")
```

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe /tmp/wait_apr24_rerun.py`

Expected: `DONE after <seconds> status=success`.

**Step 4: Verify CP section has clickable `[N](url)` citations**

Run an inline verification script:

```python
# Save as /tmp/verify_apr24_cp.py
import io, os, re, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(r"c:\Users\amy\Desktop\0to1log\backend\.env")
sb = create_client(os.environ["SUPABASE_URL"], os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"])

SLUGS = [
    "2026-04-24-research-digest", "2026-04-24-research-digest-ko",
    "2026-04-24-business-digest",  "2026-04-24-business-digest-ko",
]

CITE_RE = re.compile(r"\[\d+\]\(https?://[^\s)]+\)")
BARE_ATTR_RE = re.compile(r"^>\s*—\s*(?:Hacker News|Reddit|r/\S+?)\s*$", re.MULTILINE)
CP_RE = re.compile(r"##\s*(?:Community Pulse|커뮤니티 반응)[\s\S]*?(?=\n##\s|\Z)")

all_pass = True
for slug in SLUGS:
    row = sb.table("news_posts").select("content_expert,content_learner,quality_score,fact_pack").eq("slug", slug).execute().data
    if not row:
        print(f"FAIL {slug}: no row")
        all_pass = False
        continue
    r = row[0]
    for field in ("content_expert", "content_learner"):
        body = r.get(field) or ""
        cp = CP_RE.search(body)
        if not cp:
            print(f"WARN {slug}/{field}: no CP section")
            continue
        cp_body = cp.group(0)
        cites = CITE_RE.findall(cp_body)
        bare = BARE_ATTR_RE.findall(cp_body)
        status = "PASS" if (len(cites) > 0 and len(bare) == 0) else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"{status} {slug}/{field}: cp_cites={len(cites)}, bare_attrs={len(bare)}, score={r.get('quality_score')}")

print(f"\n{'ALL PASS' if all_pass else 'FAILURES DETECTED'}")
```

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe /tmp/verify_apr24_cp.py`

Expected output (all 8 fields across 4 slugs):
```
PASS 2026-04-24-research-digest/content_expert: cp_cites=3+, bare_attrs=0, score=85+
...
ALL PASS
```

Every post's CP section shows `cp_cites >= 1` and `bare_attrs == 0`. Any FAIL → inspect the body directly, report failure mode.

**Step 5: Spot-check one link resolves to the real thread**

Pick a `[N](url)` from one of the bodies — e.g. `[3](https://news.ycombinator.com/item?id=47879092)`. Open the URL in a browser and confirm it's a real HN thread (not a 404, not the arxiv paper).

**Step 6: Write journal evidence**

Create `vault/12-Journal-&-Decisions/2026-04-24-cp-citation-pattern.md`:

```markdown
# CP Citation Pattern — 2026-04-24

## Problem

The 2026-04-24 CP URL plumbing plan (7 commits) tried to make the writer
emit **[Label](URL)** bold-inline-link markdown for CP block headers and
attributions. Two reruns produced broken output — writer split the markdown
into **[Label]** (URL) with a space (not a clickable link) and emitted
empty `> — ` attributions. Root cause: LLM writers do not reliably emit
mixed bold-link markdown, no matter how the prompt is worded. The
`_inject_cp_citations` post-processor could not recover every case.

## Decision

Extend the news writer's proven `[CITE_N]` citation pattern to CP.
Writer emits `[CITE_N]` at the end of each block header and each
attribution; `apply_citations` substitutes into `[N](url)`; strict
json_schema enum enforces URL correctness. No CP post-processor.

Plan: vault/09-Implementation/plans/2026-04-24-cp-citation-pattern.md
Design: vault/09-Implementation/plans/2026-04-24-cp-pipeline-redesign-design.md

Also fixed ranking P1-1: `rank_classified` now receives a filtered
community_map that drops sentiment=null entries, so irrelevant high-upvote
threads no longer influence Lead/Supporting scoring.

## Verification

Post-deploy, rerun-from-write on Apr 24:
- verify_apr24_cp.py output: [paste actual output here]
- Spot-checked [paste one URL here] resolves to the real thread

## What's NOT fixed by this plan

- Per-quote provenance when a group has HN + Reddit quotes mixed in one
  insight. The writer picks which block to place each quote under; a
  misattribution results in a quote being under the wrong platform's
  block (linking to a real-but-not-the-source thread). Complete fix
  requires CommunityInsight.threads[] restructure — deferred.
- P2 bundle (target_date search window, summarizer JSON mode, KO quote
  count alignment) — separate small plan.
- Weekly pipeline — not touched.
```

**Step 7: Commit the journal**

```bash
git add vault/12-Journal-&-Decisions/2026-04-24-cp-citation-pattern.md
git commit -m "docs(journal): CP citation pattern — Apr 24 evidence

Records Apr 24 rerun-from-write validation after the [CITE_N] pivot:
every CP block header and attribution renders as a clickable [N](url)
citation, no bare attributions, ranking now ignores irrelevant
sentiment=null threads."
```

---

## Done criteria

- [ ] Task 1: `_build_writer_url_allowlist` includes thread URLs; 5 tests pass
- [ ] Task 2: `_filter_community_map_by_summary` drops sentiment=null; 4 tests pass; ranking call sites use filtered map
- [ ] Task 3: rule 9 renders with `[CITE_N]` block header + attribution instructions; no bold-inline-link in the CP rule text
- [ ] Task 4: 8 skeleton CP sections use `[CITE_N]`; 16 parametrized tests pass; old skeleton test file deleted
- [ ] Task 5: EXEMPT bullet removed from 4 QC rubrics; primary `citation_coverage` rule intact
- [ ] Task 6: `_inject_cp_citations` and its infrastructure deleted; `test_cp_citation_injection.py` deleted; `smoke_cp_citations.py` deleted; full suite green
- [ ] Task 7: integration test covers body + CP substitution end-to-end; 4 tests pass
- [ ] Task 8: Apr 24 rerun-from-write produces clickable CP citations; `verify_apr24_cp.py` shows ALL PASS; journal committed

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Writer emits `[CITE_N]` in CP but omits matching entry in `citations[]` | `apply_citations` raises `CitationSubstitutionError` loudly — same as body; run fails instead of shipping a broken body |
| Writer reuses a citation number between body and CP (e.g. both `[CITE_3]`) | Rule 9 instructs "CP uses unique numbers not colliding with body"; skeleton shows 1-2 for body and 3-4 for CP; schema `citations[].n` is 1-50 so plenty of room |
| Writer forgets `[CITE_N]` on a CP block header | QC citation_coverage sub-score drops (CP paragraph without citation); same traceability signal as body; degradation limited to one block |
| Thread URL not in allowlist → schema rejection on valid CP reference | Task 1 ensures insight.hn_url/reddit_url are in the allowlist; `build_news_writer_json_schema` deduplicates; enum has no length limit |
| Ranking filter is too aggressive (drops relevant threads) | `_filter_community_map_by_summary` only drops sentiment=null (summarizer explicitly marked as off-topic); falls back to raw map if summary_map is empty |
| Existing Apr 24 draft bodies (broken format) remain in DB | Task 8 rerun-from-write overwrites them; draft status means they never hit the frontend; no manual cleanup needed |
| Deleting `_inject_cp_citations` breaks pre-plan bodies already in DB | Those bodies are draft (never published); no frontend exposure; future reruns will overwrite |
