# CP Per-Platform Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure the Community Pulse pipeline so each HN/Reddit thread is processed independently per-platform, with a gpt-5-nano relevance filter pre-selecting on-topic comments, eliminating cross-platform quote ambiguity (P1-2) and off-topic comment noise (Apr 25 DeepSeek case) in one coherent change.

**Architecture:** Today: HN + Reddit blobs are concatenated per group, summarizer LLM ingests mixed input, outputs flat `quotes: list[str]` with no platform tags — writer must guess which quote came from which platform. New: split before summarizer. For each thread (HN, Reddit, or both), run a gpt-5-nano relevance filter (top voted 30 → most relevant 5-10 for the article), then call the summarizer per-platform. Aggregate results into `CommunityInsight.threads: list[ThreadInfo]` — a structured per-platform record. Downstream (CP Data builder, writer prompt, linkifier) consumes the structured shape, so quote provenance is preserved by design and the writer never needs to "split into 2 blocks" — the data is already split.

**Tech Stack:** Python 3.11, Pydantic v2, OpenAI Python SDK (gpt-5-mini for summarizer, gpt-5-nano for relevance filter), pytest. No new external dependencies.

---

## Plan Revisions (2026-04-26 review feedback)

Five design errors found in the v1 plan during review. **Implementer must apply these revisions to the affected tasks below — they override the original task text.**

### R1 — Task 1 hydration over-attributed legacy quotes (FIXED)
v1 placed all multi-platform legacy quotes under the higher-upvote thread. That invents per-quote provenance the legacy data never had. **Already fixed in commit `f19ec05`** — multi-platform legacy hydration now returns both threads with EMPTY quotes; downstream renders key_point only via the HasQuotes:no path. Single-platform legacy still keeps quotes (provenance unambiguous).

### R2 — Task 2 has hidden behavior change; merge into Task 4
v1 Task 2 alone expands top_n from 5-10 to 30. That's NOT "no behavior change" — until Task 4 plugs in the relevance filter, the summarizer receives 30 raw comments per platform → 6× larger blob → token budget pressure + noise. **Drop Task 2 as a standalone task. Move the top-N expansion into Task 4** (combined with the relevance filter wire-up so it ships atomically).

### R3 — Task 3 fallback semantics are inverted
v1 Task 3 has the relevance filter return top-3 voted when the LLM returns `selected_indexes: []`. That defeats the whole purpose: Apr 25 DeepSeek = LLM correctly judging "everything is off-topic" — falling back to top-3 re-introduces the political flame wars we want to filter out.

**Correct semantics:**
- **API failure** (network, parse error, retry exhausted) → fail-OPEN: return `candidates[:max_pick]` (preserve top-N voted ordering — better degraded data than no data when the LLM is unreachable)
- **Valid LLM response with `selected_indexes: []`** → fail-CLOSED: return `[]` (LLM judged correctly that nothing is on-topic; let the summarizer's sentiment=null path drop the section, which is the intended behavior)

Update `_filter_relevant_comments` accordingly. Update tests to cover both branches separately. Specifically: the v1 test `test_filter_falls_back_when_zero_selected` must FLIP — assert `result == []`, not `result == candidates[:3]`.

### R4 — Task 5 ranking still receives raw blob with off-topic platform text
v1 Task 5 only updates the per-entry filter (`_filter_community_map_by_summary`) to recognize "any thread relevant → keep entry". But when a multi-platform group has one relevant + one off-topic platform, the WHOLE raw blob (containing both) is still passed to ranking. Ranking parses upvote signal from raw text and counts upvotes from the off-topic platform too — undermining the relevance filter.

**Correct fix (add to Task 5):** when a multi-platform insight has one off-topic thread, strip that platform's section from the blob before passing to ranking. Implementation:
- New helper `_redact_offtopic_sections(raw_blob, insight) -> str` that removes `[Hacker News|url=...]` and `[Reddit r/sub|url=...]` sections whose platform's thread has `sentiment=None`
- Apply in `_filter_community_map_by_summary` (or in caller before ranking)
- Tests: blob with HN sentiment=mixed + Reddit sentiment=None → output blob has only HN section

### R5 — Task 6 missing consumer updates (allowlist + linkifier + QC)
v1 Task 6 only updates `_build_cp_data_entries`. But three other consumers also read flat `hn_url`/`reddit_url` and depend on upvote-matching logic:
- `_build_writer_url_allowlist` (pipeline_digest.py:135) — must read URLs from `insight.synthesized_threads()`
- `_linkify_cp_section` (pipeline_digest.py:264) — must build hn_index / reddit_index from threads, not flat fields
- `_check_digest_quality` URL allowlist (pipeline_quality.py:591) — same pattern

**Add subtasks 6b, 6c, 6d** (or split into Tasks 6, 7, 8, 9). Each is small (~20-30 LOC) but missing them means the CP section won't actually render correctly even after Task 6 ships.

### R6 — Already-resolved items confirmed
P1-1 ranking filter (pipeline.py:1508), summarizer JSON mode (ranking.py:541), EN/KO quote pair alignment (pipeline_digest.py:140), thread URL in QC allowlist (pipeline_quality.py:591) — all present in code. v1 plan correctly accounts for these. No action.

---

### Renumbered task ordering (post-revision)

| # | Task | Status |
|---|---|---|
| 1 | ThreadInfo + CommunityInsight.threads + hydration | DONE (`dbd8942` + `f19ec05`) |
| 2 | (was top-N expansion) | DROPPED — folded into Task 4 |
| 3 | filter_relevant_comments helper (gpt-5-nano) — with R3 fallback fix | pending |
| 4 | summarize_community per-platform + top-N expansion (R2) | pending |
| 5 | _filter_community_map_by_summary uses synthesized_threads + R4 redaction | pending |
| 6 | _build_cp_data_entries (per-thread) | pending |
| 6b | _build_writer_url_allowlist reads from threads (R5) | pending |
| 6c | _linkify_cp_section reads URLs from threads (R5) | pending |
| 6d | _check_digest_quality allowlist reads from threads (R5) | pending |
| 7 | Drop multi-platform split rule from prompt rule 9 | pending |
| 8 | Apr 26+ cron verification + journal | pending |

The original Task 2-8 sections below remain as reference but apply the revisions above before implementation.

---

## Prerequisite context

- **Repo:** `c:\Users\amy\Desktop\0to1log` on `main` (main-only workflow per CLAUDE.md — no feature branches)
- **Python venv:** `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe`
- **Brainstorming context:** documented in this conversation. Key research findings:
  - Most existing HN summarizer tools dump full threads to LLM (Simon Willison, FastDigest); we can't do that because gpt-5-mini summarizer has ~2k token budget
  - HN Companion uses engagement scoring + hierarchy preservation
  - Academic standard is MMR (relevance + diversity) but requires embeddings infra we don't have
  - LLM-as-judge for relevance scoring is widely used in Reddit monitoring tools
- **Why this design:** 6 problems collapse into one architectural fix:
  1. P1-2 per-quote platform tag (external review)
  2. Off-topic top voted comments (Apr 25 DeepSeek)
  3. Quote duplication across platforms (Apr 24 research personas)
  4. Writer non-deterministic quote distribution
  5. Multi-platform split rule complexity in writer prompt
  6. Comment selection strategy
- **Already shipped this week:** linkifier (`_linkify_cp_section`), Option 1 attribution, hallucination guard, min upvote threshold, JSON mode for summarizer, EN/KO pair alignment, QC allowlist for thread URLs, P1-1 ranking filter. This plan does NOT undo any of those — it builds on top.
- **Backward compatibility:** old CommunityInsight checkpoints have flat `quotes/quotes_ko/source_label/hn_url/reddit_url` (no `threads`). Loading must work — Pydantic model includes a hydration adapter.
- **Cost budget:** new gpt-5-nano filter call per platform per group. ~6 groups × 1-2 platforms/day = 8-12 calls × ~$0.001 = **$0.008-0.012/day extra**. Summarizer cost roughly doubles when both platforms exist (was 1 call per group, now up to 2). Total CP-related cost increase: ~$0.01-0.02/day. Negligible.
- **Commit policy (CLAUDE.md):** `feat:/fix:/refactor:/chore:` prefix, NO `Co-Authored-By`. One commit per task.

---

## File structure

| File | Responsibility | Task |
|---|---|---|
| `backend/models/news_pipeline.py` | `CommunityInsight` schema + new `ThreadInfo` + hydration adapter | 1 |
| `backend/services/news_collection.py` | Top voted N expansion (5-10 → 30) | 2 |
| `backend/services/agents/comment_relevance.py` | NEW — `filter_relevant_comments` helper (gpt-5-nano) | 3 |
| `backend/services/agents/ranking.py` | `summarize_community` per-platform restructure + aggregate to threads | 4 |
| `backend/services/pipeline.py` | `_filter_community_map_by_summary` updated for threads structure | 5 |
| `backend/services/pipeline_digest.py` | `_build_cp_data_entry` per-thread output, `_has_strong_community_signal` per-thread | 6 |
| `backend/services/agents/prompts_news_pipeline.py` | Rule 9 simplification (drop multi-platform split rule) | 7 |
| `backend/tests/test_community_insight_threads.py` | NEW — Pydantic model + hydration tests | 1 |
| `backend/tests/test_comment_relevance.py` | NEW — relevance filter tests | 3 |
| `backend/tests/test_summarize_community_per_platform.py` | NEW — per-platform summarizer tests | 4 |
| `backend/tests/test_cp_data_builder.py` | Extend — per-thread entry tests | 6 |

---

## Task 1: Add `ThreadInfo` + extend `CommunityInsight` with threads field

**Why:** Foundation for the redesign. New `threads: list[ThreadInfo]` carries per-platform records. Old field shape (`quotes`, `quotes_ko`, `source_label`, `hn_url`, `reddit_url`) stays for backward compat — old checkpoints continue to deserialize. Hydration helper synthesizes a single-element `threads` list when only the legacy fields are present, so downstream consumers see a uniform shape.

**Files:**
- Modify: `backend/models/news_pipeline.py` — `CommunityInsight` class
- Create: `backend/tests/test_community_insight_threads.py`

**Step 1: Write the failing test**

Create `backend/tests/test_community_insight_threads.py`:

```python
"""Tests for CommunityInsight.threads structure + backward-compat hydration."""

from models.news_pipeline import CommunityInsight, ThreadInfo


def test_thread_info_basic_fields():
    t = ThreadInfo(
        platform="hackernews",
        url="https://news.ycombinator.com/item?id=42",
        upvotes=1041,
        comments=689,
        sentiment="mixed",
        quotes=["a real quote with substance over ten chars"],
        quotes_ko=["충분히 긴 한국어 인용"],
        key_point="Discussion about pricing",
    )
    assert t.platform == "hackernews"
    assert t.upvotes == 1041
    assert t.subreddit is None  # only set for reddit


def test_thread_info_reddit_has_subreddit():
    t = ThreadInfo(
        platform="reddit",
        url="https://www.reddit.com/r/OpenAI/comments/abc/t/",
        subreddit="OpenAI",
        upvotes=642,
        comments=230,
        sentiment="negative",
        quotes=["a real quote"],
        quotes_ko=["인용"],
        key_point="Pricing critique",
    )
    assert t.subreddit == "OpenAI"


def test_community_insight_with_threads():
    insight = CommunityInsight(
        threads=[
            ThreadInfo(
                platform="hackernews",
                url="https://news.ycombinator.com/item?id=42",
                upvotes=1041,
                comments=689,
                sentiment="mixed",
                quotes=["hn quote with substance over ten chars"],
                quotes_ko=["에이치엔 인용 충분히 긴 텍스트"],
                key_point="HN discussion",
            ),
            ThreadInfo(
                platform="reddit",
                url="https://www.reddit.com/r/OpenAI/comments/abc/t/",
                subreddit="OpenAI",
                upvotes=642,
                comments=230,
                sentiment="negative",
                quotes=["reddit quote with substance over ten chars"],
                quotes_ko=["레딧 인용 충분히 긴 텍스트"],
                key_point="Reddit pricing critique",
            ),
        ],
    )
    assert len(insight.threads) == 2
    assert insight.threads[0].platform == "hackernews"
    assert insight.threads[1].platform == "reddit"


def test_community_insight_legacy_hydration_hn_only():
    """Old checkpoint shape (flat fields, no threads) hydrates to a single-thread
    structure so downstream code sees a uniform shape."""
    insight = CommunityInsight(
        source_label="Hacker News 79↑ · 116 comments",
        sentiment="mixed",
        quotes=["legacy hn quote with substance over ten chars"],
        quotes_ko=["레거시 인용 충분히 긴 텍스트"],
        key_point="Legacy discussion",
        hn_url="https://news.ycombinator.com/item?id=42",
    )
    threads = insight.synthesized_threads()
    assert len(threads) == 1
    assert threads[0].platform == "hackernews"
    assert threads[0].url == "https://news.ycombinator.com/item?id=42"
    assert threads[0].upvotes == 79
    assert threads[0].comments == 116
    assert threads[0].sentiment == "mixed"
    assert threads[0].quotes == ["legacy hn quote with substance over ten chars"]


def test_community_insight_legacy_hydration_both_platforms():
    """Multi-platform legacy insight (HN + Reddit URLs both present) hydrates to
    TWO threads. Quotes are placed under the higher-upvote thread by default
    since legacy data has no per-quote provenance."""
    insight = CommunityInsight(
        source_label="Hacker News 1041↑ · 689 comments · r/OpenAI (642↑)",
        sentiment="mixed",
        quotes=["q1 with substance over ten chars", "q2 with substance over ten chars"],
        quotes_ko=["인용 1 충분히 긴", "인용 2 충분히 긴"],
        key_point="Multi-platform discussion",
        hn_url="https://news.ycombinator.com/item?id=47879092",
        reddit_url="https://www.reddit.com/r/OpenAI/comments/1stqlnh/x/",
    )
    threads = insight.synthesized_threads()
    assert len(threads) == 2
    # HN comes first (higher upvotes)
    assert threads[0].platform == "hackernews"
    assert threads[0].upvotes == 1041
    # Quotes go to the dominant thread (HN); secondary thread gets empty quotes
    assert threads[0].quotes == ["q1 with substance over ten chars", "q2 with substance over ten chars"]
    assert threads[1].platform == "reddit"
    assert threads[1].upvotes == 642
    assert threads[1].quotes == []


def test_community_insight_synthesized_threads_returns_existing_when_present():
    """When threads is already populated (new format), synthesized_threads
    returns it as-is — no re-derivation from flat fields."""
    explicit = ThreadInfo(
        platform="hackernews",
        url="https://news.ycombinator.com/item?id=42",
        upvotes=1041,
        comments=689,
        sentiment="positive",
        quotes=["new format"],
        quotes_ko=["신규 형식"],
        key_point="New format",
    )
    insight = CommunityInsight(threads=[explicit])
    result = insight.synthesized_threads()
    assert len(result) == 1
    assert result[0] is explicit
```

**Step 2: Run test to verify it fails**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_community_insight_threads.py -v`

Expected: FAIL with `ImportError: cannot import name 'ThreadInfo'`.

**Step 3: Add `ThreadInfo` + extend `CommunityInsight`**

In `backend/models/news_pipeline.py`, add `ThreadInfo` Pydantic model + extend `CommunityInsight`. Find the existing `CommunityInsight` class and update:

```python
from pydantic import BaseModel, Field


class ThreadInfo(BaseModel):
    """Per-platform community thread record. Each ThreadInfo represents one
    discussion thread (HN OR Reddit) — quotes and sentiment scoped to that
    thread alone, no cross-platform mixing."""
    platform: str  # "hackernews" or "reddit"
    url: str       # thread URL (item?id=... or /r/sub/comments/...)
    subreddit: str | None = None  # only for platform="reddit"
    upvotes: int
    comments: int
    sentiment: str | None = "mixed"  # positive / mixed / negative / neutral / None (off-topic)
    quotes: list[str] = []           # English quotes from THIS thread only
    quotes_ko: list[str] = []        # KO translations, 1:1 with quotes
    key_point: str | None = None     # one-line discussion summary


class CommunityInsight(BaseModel):
    """Summarized community reaction for a news group. Two shapes coexist:
    - NEW: threads (list[ThreadInfo]) carries per-platform records with provenance
    - LEGACY: flat fields (quotes/quotes_ko/source_label/hn_url/reddit_url) for
      backward compatibility with checkpoints from before 2026-04-26
    Use synthesized_threads() to get a uniform list[ThreadInfo] regardless of shape.
    """
    threads: list[ThreadInfo] = []

    # Legacy fields — DO NOT remove; old checkpoint loading depends on them.
    source_label: str = ""
    sentiment: str | None = None
    quotes: list[str] = []
    quotes_ko: list[str] = []
    key_point: str | None = None
    hn_url: str | None = None
    reddit_url: str | None = None

    def synthesized_threads(self) -> list[ThreadInfo]:
        """Return per-platform threads, synthesizing from legacy fields if needed.
        New checkpoints set `threads` directly; old ones derive from the flat
        fields. Quotes from legacy data are placed under the dominant (higher-
        upvote) thread since legacy data has no per-quote provenance."""
        if self.threads:
            return self.threads

        derived: list[ThreadInfo] = []
        # Parse upvotes/comments from source_label
        import re as _re
        hn_match = _re.search(r"Hacker News\s+(\d[\d,]*)↑(?:\s*·\s*(\d[\d,]*)\s*comments?)?", self.source_label or "")
        reddit_match = _re.search(r"r/(\S+?)\s*\(\s*(\d[\d,.]*)([Kk])?↑\)", self.source_label or "")

        if self.hn_url and hn_match:
            hn_upvotes = int(hn_match.group(1).replace(",", ""))
            hn_comments = int(hn_match.group(2).replace(",", "")) if hn_match.group(2) else 0
            derived.append(ThreadInfo(
                platform="hackernews",
                url=self.hn_url,
                upvotes=hn_upvotes,
                comments=hn_comments,
                sentiment=self.sentiment,
                quotes=[],     # placeholder; quotes assigned to dominant below
                quotes_ko=[],
                key_point=self.key_point,
            ))

        if self.reddit_url and reddit_match:
            sub = reddit_match.group(1).rstrip(")")
            digits = reddit_match.group(2).replace(",", "")
            kmult = (reddit_match.group(3) or "").upper() == "K"
            r_upvotes = int(float(digits) * (1000 if kmult else 1))
            derived.append(ThreadInfo(
                platform="reddit",
                url=self.reddit_url,
                subreddit=sub,
                upvotes=r_upvotes,
                comments=0,  # legacy source_label rarely has Reddit comment count
                sentiment=self.sentiment,
                quotes=[],
                quotes_ko=[],
                key_point=self.key_point,
            ))

        # Place all legacy quotes under the dominant (highest-upvote) thread
        if derived and (self.quotes or self.quotes_ko):
            derived.sort(key=lambda t: t.upvotes, reverse=True)
            derived[0].quotes = list(self.quotes or [])
            derived[0].quotes_ko = list(self.quotes_ko or [])

        return derived
```

**Important:** if `pydantic` is v2 (it is per CLAUDE.md backend stack), `BaseModel` ignores extra fields by default. Make sure any current usages of `CommunityInsight(**checkpoint_dict)` still work — they will because all new fields have defaults.

**Step 4: Run tests to verify they pass**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_community_insight_threads.py -v`

Expected: 6 passed.

Run full regression to ensure existing CommunityInsight callers still work:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ --tb=short -q`

Expected: same baseline + 6 new passing. No regressions in `test_cp_*`, `test_community_*`, `test_pipeline*`.

Lint:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/models/news_pipeline.py backend/tests/test_community_insight_threads.py`

Expected: `All checks passed!`

**Step 5: Commit**

```bash
git add backend/models/news_pipeline.py backend/tests/test_community_insight_threads.py
git commit -m "feat(model): add ThreadInfo + extend CommunityInsight with threads

ThreadInfo carries per-platform provenance for community discussion
records (one HN or Reddit thread = one ThreadInfo). CommunityInsight
gains a threads list field while keeping legacy flat fields
(quotes/quotes_ko/source_label/hn_url/reddit_url) for backward compat
with checkpoints from before this redesign.

synthesized_threads() helper returns a uniform list[ThreadInfo]
regardless of shape — new checkpoints use threads directly, old ones
derive from the flat fields with quotes placed under the dominant
(higher-upvote) thread (legacy data has no per-quote provenance).

Foundation for the per-platform summarizer redesign — no behavior
change yet, just the data shape."
```

---

## Task 2: Expand top-voted N from 5-10 to 30 in `news_collection.py`

**Why:** The new gpt-5-nano relevance filter (Task 3) needs a candidate pool to filter from. Today HN/Reddit collection grabs only 5-10 top voted comments. Filtering 5 down to 5 doesn't help. Expand to 30 so the filter has signal to work with. Not yet plugging in the filter — just expanding the pool. No behavior change downstream (summarizer just sees more raw text; its 2k token budget will still cap usable input).

**Files:**
- Modify: `backend/services/news_collection.py` — find the `top_n` parameter / slice on HN comment fetch and Reddit comment fetch

**Step 1: Locate the comment count limits**

Run:

```
c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m grep -n "top_n\|comments_text\|top.*comments\|.comments\[:" backend/services/news_collection.py | head -20
```

Or use Grep tool. Find any `[:5]`, `[:10]`, `top_n=`, or similar slice/parameter in the HN and Reddit fetch paths. Expected: ~2-4 locations (one per platform, possibly one for max_comments_to_fetch and one for top_n_to_render).

**Step 2: Write a regression test**

Create `backend/tests/test_news_collection_top_n.py`:

```python
"""Guard that HN + Reddit comment fetch returns up to TOP_N (now 30) raw
comments, providing enough candidate pool for the gpt-5-nano relevance
filter (Task 3). Prior limit was 5-10 — too small to filter."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.parametrize("module_attr,expected_min", [
    ("HN_COMMENTS_TOP_N", 30),
    ("REDDIT_COMMENTS_TOP_N", 30),
])
def test_collection_top_n_constants_at_least_30(module_attr, expected_min):
    """The collection module must export named constants for top-N comments
    per platform, and they must be >= 30 after this change."""
    import services.news_collection as nc
    n = getattr(nc, module_attr, None)
    assert n is not None, f"{module_attr} must be defined as a module constant"
    assert n >= expected_min, f"{module_attr} = {n}, expected >= {expected_min}"
```

**Step 3: Run test — expect FAIL**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_news_collection_top_n.py -v`

Expected: FAIL on missing `HN_COMMENTS_TOP_N` constant.

**Step 4: Add module constants + update slice sites**

In `backend/services/news_collection.py`, near the top of the file (after imports), add:

```python
# Comment fetch limits per platform. Expanded from 5-10 → 30 on 2026-04-26 to
# provide a candidate pool for the gpt-5-nano relevance filter
# (services.agents.comment_relevance). The summarizer's token budget still caps
# what's actually used downstream — these are upper bounds for collection.
HN_COMMENTS_TOP_N = 30
REDDIT_COMMENTS_TOP_N = 30
```

Then find the HN and Reddit comment slicing in the file and replace hard-coded numbers (`[:5]`, `[:10]`) with the constants:

```python
# HN: e.g.
comments_text = [c["text"] for c in hits[:HN_COMMENTS_TOP_N]]

# Reddit: e.g.
comments_text = [c["body"] for c in top_comments[:REDDIT_COMMENTS_TOP_N]]
```

If the existing code uses `top_n` as a function parameter, change the default value or pass the constant from the call site.

**Step 5: Run tests — expect PASS**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_news_collection_top_n.py -v`

Expected: 2 passed.

Full regression:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ --tb=short -q`

Expected: same baseline. No new failures.

Lint:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/services/news_collection.py backend/tests/test_news_collection_top_n.py`

**Step 6: Commit**

```bash
git add backend/services/news_collection.py backend/tests/test_news_collection_top_n.py
git commit -m "feat(collection): expand HN/Reddit comment fetch top-N to 30

Pre-work for the gpt-5-nano relevance filter (Task 3 of CP per-platform
redesign): the filter needs a candidate pool of ~30 to work with,
versus today's 5-10 which would yield trivial filtering.

Add named module constants HN_COMMENTS_TOP_N and REDDIT_COMMENTS_TOP_N
so the limit lives in one place and the relevance filter knows the
upper bound of what it's filtering. No behavior change to summarizer
yet — its token budget caps usable input independently."
```

---

## Task 3: Add `filter_relevant_comments` helper (gpt-5-nano LLM-as-judge)

**Why:** The Apr 25 DeepSeek case: HN thread had 1357 comments; top voted were political flame wars (Tiananmen, Mexico cartels, Iran-Israel) because big threads attract politically charged voting. Real DeepSeek tech discussion was buried. Summarizer correctly flagged the top voted as off-topic and dropped the entire CP map (sentiment=null). The right fix is to filter BEFORE summarizer — give it 5-10 article-relevant comments instead of 30 mixed-bag top voted.

LLM-as-judge with gpt-5-nano (cheapest model, ~$0.0001/call) is the right tool. Article title + excerpt provides query context. 30 comments → 5-10 relevant ones.

**Files:**
- Create: `backend/services/agents/comment_relevance.py`
- Create: `backend/tests/test_comment_relevance.py`

**Step 1: Write the failing test**

Create `backend/tests/test_comment_relevance.py`:

```python
"""Tests for filter_relevant_comments — gpt-5-nano LLM-as-judge that picks
on-topic comments from a candidate pool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_filter_returns_subset_of_input():
    from services.agents.comment_relevance import filter_relevant_comments

    candidates = [
        "DeepSeek v4 has 1.6T params — interesting MoE arch",
        "USA is descending into totalitarianism, but...",  # off-topic
        "Apache 2.0 license is huge for adoption",
        "Tiananmen Square...",  # off-topic
        "1M context window with cost-efficient inference",
    ]
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = '{"selected_indexes": [0, 2, 4]}'
    fake_response.usage = MagicMock(prompt_tokens=200, completion_tokens=20, total_tokens=220)

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.comment_relevance.get_openai_client", return_value=fake_client):
        result, usage = await filter_relevant_comments(
            candidates,
            article_title="DeepSeek v4 released — open-source 1.6T MoE",
            article_excerpt="Apache 2.0 license, 1M context",
            max_pick=10,
        )

    assert len(result) == 3
    assert "DeepSeek v4" in result[0]
    assert "Apache 2.0" in result[1]
    assert "1M context" in result[2]
    # Off-topic dropped
    assert all("Tiananmen" not in r and "totalitarianism" not in r for r in result)


@pytest.mark.asyncio
async def test_filter_falls_back_to_top_voted_on_llm_failure():
    """If gpt-5-nano fails (network, parse error, retry exhausted), return
    the input as-is (preserving order = top voted) up to max_pick. Graceful
    degradation: better to send raw top voted than no comments."""
    from services.agents.comment_relevance import filter_relevant_comments

    candidates = [f"comment {i}" for i in range(20)]
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("API down"))

    with patch("services.agents.comment_relevance.get_openai_client", return_value=fake_client):
        result, usage = await filter_relevant_comments(
            candidates,
            article_title="X",
            article_excerpt="Y",
            max_pick=5,
        )

    assert result == candidates[:5]


@pytest.mark.asyncio
async def test_filter_falls_back_when_zero_selected():
    """If LLM returns selected_indexes=[] (everything off-topic per its judgment),
    don't drop the section entirely — fall back to top-3 voted as a polite
    minimum. The summarizer's own relevance check catches truly off-topic
    later as a second line of defense."""
    from services.agents.comment_relevance import filter_relevant_comments

    candidates = ["c1", "c2", "c3", "c4", "c5"]
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = '{"selected_indexes": []}'
    fake_response.usage = MagicMock(prompt_tokens=100, completion_tokens=10, total_tokens=110)
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.comment_relevance.get_openai_client", return_value=fake_client):
        result, usage = await filter_relevant_comments(
            candidates,
            article_title="X",
            article_excerpt="Y",
            max_pick=10,
        )

    # Polite fallback: top-3 voted preserved
    assert result == candidates[:3]


@pytest.mark.asyncio
async def test_filter_caps_result_at_max_pick():
    """If LLM returns more than max_pick, truncate to max_pick (preserves
    LLM's ordering — which is presumably most relevant first)."""
    from services.agents.comment_relevance import filter_relevant_comments

    candidates = [f"c{i}" for i in range(20)]
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = '{"selected_indexes": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}'
    fake_response.usage = MagicMock(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.comment_relevance.get_openai_client", return_value=fake_client):
        result, usage = await filter_relevant_comments(
            candidates,
            article_title="X",
            article_excerpt="Y",
            max_pick=5,
        )

    assert len(result) == 5
    assert result == ["c0", "c1", "c2", "c3", "c4"]


@pytest.mark.asyncio
async def test_filter_handles_empty_candidates():
    from services.agents.comment_relevance import filter_relevant_comments

    result, usage = await filter_relevant_comments(
        [],
        article_title="X",
        article_excerpt="Y",
        max_pick=10,
    )
    assert result == []
    assert usage == {}


@pytest.mark.asyncio
async def test_filter_handles_invalid_index_gracefully():
    """LLM might return out-of-range indexes; skip them silently."""
    from services.agents.comment_relevance import filter_relevant_comments

    candidates = ["c0", "c1", "c2"]
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = '{"selected_indexes": [0, 99, 1, -1, 2]}'
    fake_response.usage = MagicMock(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.comment_relevance.get_openai_client", return_value=fake_client):
        result, usage = await filter_relevant_comments(
            candidates,
            article_title="X",
            article_excerpt="Y",
            max_pick=10,
        )

    # Only valid indexes 0, 1, 2 used
    assert result == ["c0", "c1", "c2"]
```

**Step 2: Run tests — expect FAIL**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_comment_relevance.py -v`

Expected: 6 FAIL with `ImportError: cannot import name 'filter_relevant_comments'`.

**Step 3: Implement the helper**

Create `backend/services/agents/comment_relevance.py`:

```python
"""LLM-as-judge relevance filter for community comments.

Given a candidate pool of HN/Reddit comments (typically top voted 30) and
the article context, ask gpt-5-nano which comments are actually about the
article topic. Filter out tangential rants, political flame wars, off-topic
discussions that happen to be top-voted in big threads.

Apr 25 DeepSeek case: HN thread had 1357 comments; top voted were political
(Tiananmen, Iran-Israel, Mexico cartels) not technical. Sending those to the
summarizer triggered sentiment=null drop and lost the entire CP section.

Cost: ~$0.001 per call (gpt-5-nano). At 6 groups × 1-2 platforms/day,
~$0.008-0.012/day extra. Negligible.
"""
import json
import logging
from typing import Any

from core.config import settings
from services.agents.client import (
    build_completion_kwargs,
    extract_usage_metrics,
    get_openai_client,
    parse_ai_json,
    with_flex_retry,
)

logger = logging.getLogger(__name__)


_RELEVANCE_FILTER_PROMPT = """You are filtering community comments for an AI news digest.

Given:
- An article (title + excerpt)
- A list of candidate comments from a discussion thread (HN or Reddit), top-voted first

Your job: pick the comments that are SUBSTANTIVELY ABOUT the article's topic. Drop:
- Off-topic political/social rants (mentions of Tiananmen, Iran, USA politics, racial issues, etc. when the article is about a tech/AI release)
- Pure emotional reactions with no information
- Generic comments that could apply to any article ("Wow, this is huge")
- Meta-comments about HN/Reddit itself
- Comments that admit to not reading the article

Keep:
- Technical critique with specifics (architecture, benchmarks, performance numbers)
- Deployment / production concerns (cost, integration, edge cases)
- Comparisons to alternatives (named tools, methods, prior work)
- Substantive disagreement or supporting evidence
- Personal experience reports relevant to the article topic

Output JSON only:
{"selected_indexes": [<comment indexes you picked, 0-based, max 10>]}

Pick the smallest set that captures the substantive discussion. If a comment is borderline, drop it."""


async def filter_relevant_comments(
    candidates: list[str],
    article_title: str,
    article_excerpt: str,
    max_pick: int = 10,
) -> tuple[list[str], dict[str, Any]]:
    """Filter candidates down to article-relevant comments via gpt-5-nano.

    Returns (filtered_comments, usage_dict).

    Graceful degradation:
    - Empty input → return ([], {})
    - LLM call fails → return top-N voted as-is (preserves input order)
    - LLM returns 0 selected → polite fallback to top-3 voted (don't drop CP entirely)
    - LLM returns out-of-range indexes → skip silently
    - More than max_pick selected → truncate to max_pick
    """
    if not candidates:
        return [], {}

    client = get_openai_client()
    model = settings.openai_model_nano  # gpt-5-nano

    numbered = "\n\n".join(f"[{i}] {c}" for i, c in enumerate(candidates))
    user_content = (
        f"## Article\nTitle: {article_title}\nExcerpt: {article_excerpt}\n\n"
        f"## Candidate comments (top-voted first)\n\n{numbered}"
    )

    kwargs = build_completion_kwargs(
        model=model,
        messages=[
            {"role": "system", "content": _RELEVANCE_FILTER_PROMPT},
            {"role": "user", "content": user_content},
        ],
        max_tokens=200,
        response_format={"type": "json_object"},
        service_tier="flex",
        prompt_cache_key="cp-comment-relevance",
    )

    try:
        response = await with_flex_retry(
            lambda: client.chat.completions.create(**kwargs),
        )
        raw_output = response.choices[0].message.content or ""
        data = parse_ai_json(raw_output, "comment_relevance_filter")
        usage = extract_usage_metrics(response, model, requested_service_tier="flex")
    except Exception as e:
        logger.warning(
            "Comment relevance filter failed (%s) — falling back to top-%d voted",
            e, max_pick,
        )
        return candidates[:max_pick], {}

    selected_indexes = data.get("selected_indexes") if isinstance(data, dict) else None
    if not isinstance(selected_indexes, list):
        logger.warning(
            "Comment relevance filter returned malformed shape — falling back to top-%d voted",
            max_pick,
        )
        return candidates[:max_pick], usage

    # Validate + truncate
    valid: list[str] = []
    for idx in selected_indexes:
        if not isinstance(idx, int):
            continue
        if 0 <= idx < len(candidates):
            valid.append(candidates[idx])
        if len(valid) >= max_pick:
            break

    if not valid:
        # LLM said "everything is off-topic" — polite fallback to top-3
        # (the summarizer's own relevance check catches truly off-topic later).
        logger.info(
            "Comment relevance filter selected 0 — falling back to top-3 voted",
        )
        return candidates[:3], usage

    return valid, usage
```

**Important:** the function imports `settings.openai_model_nano`. Confirm this setting exists in `backend/core/config.py`. If it doesn't, add it:

```python
openai_model_nano: str = "gpt-5-nano"
```

Or use an existing equivalent like `openai_model_light`. Check first; don't add unnecessary settings.

**Step 4: Run tests — expect PASS**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_comment_relevance.py -v`

Expected: 6 passed.

Lint:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/services/agents/comment_relevance.py backend/tests/test_comment_relevance.py`

**Step 5: Commit**

```bash
git add backend/services/agents/comment_relevance.py backend/tests/test_comment_relevance.py
# (only add config.py if you had to add openai_model_nano setting)
git commit -m "feat(cp): add gpt-5-nano LLM-as-judge comment relevance filter

Solves the Apr 25 DeepSeek case: HN thread had 1357 comments; top voted
were political flame wars (Tiananmen, Iran, USA politics) because big
threads attract politically charged voting. Real tech discussion was
buried. Summarizer correctly dropped them all as off-topic, losing the
entire CP section.

filter_relevant_comments takes the candidate pool (top voted N from
collection) + article title/excerpt, asks gpt-5-nano which comments are
substantively about the article topic, returns up to max_pick (default
10). gpt-5-nano costs ~$0.001/call; ~6-12 calls/day = ~\$0.01/day
extra.

Graceful degradation throughout: empty input → empty output; LLM call
fails → top-N voted fallback; LLM returns 0 → polite top-3 fallback
(don't drop CP entirely); out-of-range indexes silently skipped;
oversize selections truncated.

Not yet wired into ranking.summarize_community — Task 4 plugs it in."
```

---

## Task 4: Restructure `summarize_community` to per-platform calls

**Why:** This is the load-bearing change. Today `summarize_community` receives the concatenated HN+Reddit blob per group and runs ONE LLM call producing flat `quotes: list[str]` with no platform tags. New: split the blob by platform headers, run the relevance filter (Task 3) on each platform's comments separately, call the summarizer per platform, aggregate results into `CommunityInsight.threads`.

**Files:**
- Modify: `backend/services/agents/ranking.py` — `summarize_community` function
- Create: `backend/tests/test_summarize_community_per_platform.py`

**Step 1: Understand current code**

Read `backend/services/agents/ranking.py` `summarize_community` function (search `def summarize_community`). Note:
- Current input: `community_map: dict[str, str]` (primary_url → concatenated blob)
- Current output: `(dict[str, CommunityInsight], usage_dict)`
- Current LLM input: groups concatenated, summarizer returns `{"groups": {"group_0": {...}}}`
- Current `_parse_source_meta` extracts `(label, hn_url, reddit_url)` from concatenated blob

**Step 2: Write failing tests for the new shape**

Create `backend/tests/test_summarize_community_per_platform.py`:

```python
"""Tests for summarize_community per-platform restructure: each platform in
the input blob gets its own filter + summarizer call; results aggregated
into CommunityInsight.threads."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from models.news_pipeline import ClassifiedGroup, GroupedItem, ThreadInfo


def _make_group(primary_url="https://example.com/x", title="Topic A") -> ClassifiedGroup:
    return ClassifiedGroup(
        group_title=title,
        items=[GroupedItem(url=primary_url, title=title, subcategory="news")],
        category="research",
        subcategory="news",
        reason="[LEAD] x",
        primary_url=primary_url,
    )


@pytest.mark.asyncio
async def test_summarize_community_calls_filter_then_summarizer_per_platform():
    """Multi-platform group → filter called twice (once per platform), summarizer
    called twice (once per platform), result has 2 threads in CommunityInsight."""
    from services.agents.ranking import summarize_community

    primary_url = "https://example.com/gpt55"
    blob = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=42] GPT-5.5 | 1041 points | 689 comments\n"
        "Top comments:\n"
        '> "guardrails complaint"\n'
        '> "30 dollar pricing critique"\n\n'
        "[Reddit r/OpenAI|url=https://www.reddit.com/r/OpenAI/comments/abc/t/] GPT-5.5 thread | 642 upvotes | 230 comments\n"
        "Top comments:\n"
        '> "reddit pricing complaint"\n'
        '> "reddit accessibility concern"\n'
    )
    community_map = {primary_url: blob}
    group = _make_group(primary_url, "GPT-5.5 release")

    # Mock filter: passthrough (return all candidates as-is)
    async def fake_filter(candidates, article_title, article_excerpt, max_pick=10):
        return candidates[:max_pick], {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110}

    # Mock summarizer LLM: return one quote per call
    call_count = {"n": 0}

    def make_response():
        call_count["n"] += 1
        n = call_count["n"]
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = (
            '{"groups": {"group_0": {"sentiment": "mixed", '
            f'"quotes": ["quote from platform {n}"], '
            f'"quotes_ko": ["인용 플랫폼 {n}"], '
            f'"key_point": "Discussion about platform {n}"}}}}'
        )
        resp.usage = MagicMock(prompt_tokens=200, completion_tokens=50, total_tokens=250)
        return resp

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=lambda **kw: make_response())

    with patch("services.agents.ranking.filter_relevant_comments", new=fake_filter), \
         patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        result, usage = await summarize_community(community_map, [group])

    insight = result[primary_url]
    assert len(insight.threads) == 2

    hn = next(t for t in insight.threads if t.platform == "hackernews")
    assert hn.upvotes == 1041
    assert hn.comments == 689
    assert hn.url == "https://news.ycombinator.com/item?id=42"
    assert len(hn.quotes) == 1

    reddit = next(t for t in insight.threads if t.platform == "reddit")
    assert reddit.upvotes == 642
    assert reddit.subreddit == "OpenAI"
    assert reddit.url == "https://www.reddit.com/r/OpenAI/comments/abc/t/"
    assert len(reddit.quotes) == 1


@pytest.mark.asyncio
async def test_summarize_community_single_platform_creates_one_thread():
    """HN-only group → 1 thread in result."""
    from services.agents.ranking import summarize_community

    primary_url = "https://example.com/y"
    blob = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=99] HN thread | 200 points | 50 comments\n"
        "Top comments:\n"
        '> "single quote"\n'
    )
    community_map = {primary_url: blob}
    group = _make_group(primary_url, "Single platform")

    async def fake_filter(candidates, article_title, article_excerpt, max_pick=10):
        return candidates[:max_pick], {}

    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = (
        '{"groups": {"group_0": {"sentiment": "positive", '
        '"quotes": ["q"], "quotes_ko": ["인용"], "key_point": "kp"}}}'
    )
    fake_response.usage = MagicMock(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.ranking.filter_relevant_comments", new=fake_filter), \
         patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        result, usage = await summarize_community(community_map, [group])

    insight = result[primary_url]
    assert len(insight.threads) == 1
    assert insight.threads[0].platform == "hackernews"


@pytest.mark.asyncio
async def test_summarize_community_skips_irrelevant_per_platform():
    """If summarizer returns sentiment=null for a platform, that thread is
    still recorded (with sentiment=None) so downstream knows it was processed
    and judged off-topic — the relevance filter at the start of the pipeline
    is the FIRST line of defense; this is the SECOND."""
    from services.agents.ranking import summarize_community

    primary_url = "https://example.com/z"
    blob = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=1] DeepSeek | 1700 points | 1357 comments\n"
        "Top comments:\n"
        '> "off-topic political rant"\n'
    )
    community_map = {primary_url: blob}
    group = _make_group(primary_url, "DeepSeek v4")

    async def fake_filter(candidates, article_title, article_excerpt, max_pick=10):
        return candidates[:max_pick], {}

    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = (
        '{"groups": {"group_0": {"sentiment": null, '
        '"quotes": [], "quotes_ko": [], "key_point": null}}}'
    )
    fake_response.usage = MagicMock(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("services.agents.ranking.filter_relevant_comments", new=fake_filter), \
         patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        result, usage = await summarize_community(community_map, [group])

    insight = result[primary_url]
    assert len(insight.threads) == 1
    assert insight.threads[0].sentiment is None
    assert insight.threads[0].quotes == []


@pytest.mark.asyncio
async def test_summarize_community_handles_empty_community_map():
    from services.agents.ranking import summarize_community

    result, usage = await summarize_community({}, [_make_group()])
    assert result == {}
```

**Step 3: Run tests — expect FAIL**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_summarize_community_per_platform.py -v`

Expected: 4 FAIL — current `summarize_community` doesn't call `filter_relevant_comments`, doesn't return `threads` structure.

**Step 4: Restructure `summarize_community`**

In `backend/services/agents/ranking.py`, modify the `summarize_community` function. High-level shape:

```python
import re
from models.news_pipeline import CommunityInsight, ThreadInfo
from services.agents.comment_relevance import filter_relevant_comments


# Header regex (already exists; verify)
_HN_HEADER_RE = re.compile(
    r"\[Hacker News\|url=(?P<url>[^\]]+)\]\s+[^|]*?\|\s*(?P<upvotes>\d[\d,]*)\s*points?\s*\|\s*(?P<comments>\d[\d,]*)\s*comments?",
)
_REDDIT_HEADER_RE = re.compile(
    r"\[Reddit\s+r/(?P<sub>[^\|\]]+)\|url=(?P<url>[^\]]+)\]\s+[^|]*?\|\s*(?P<upvotes>\d[\d,]*)\s*upvotes?\s*\|\s*(?P<comments>\d[\d,]*)\s*comments?",
)
_COMMENT_LINE_RE = re.compile(r'^>\s*"(.*)"$', re.MULTILINE)


def _split_blob_by_platform(blob: str) -> list[dict]:
    """Split a community_map blob into per-platform sections.
    Returns list of dicts: [{platform, url, upvotes, comments, comments_text: list[str], subreddit?}].
    """
    sections: list[dict] = []
    for m in _HN_HEADER_RE.finditer(blob):
        end = blob.find("[", m.end())
        block = blob[m.start():end if end > 0 else len(blob)]
        comments_text = _COMMENT_LINE_RE.findall(block)
        sections.append({
            "platform": "hackernews",
            "url": m.group("url"),
            "upvotes": int(m.group("upvotes").replace(",", "")),
            "comments": int(m.group("comments").replace(",", "")),
            "comments_text": comments_text,
        })
    for m in _REDDIT_HEADER_RE.finditer(blob):
        end = blob.find("[", m.end())
        block = blob[m.start():end if end > 0 else len(blob)]
        comments_text = _COMMENT_LINE_RE.findall(block)
        sections.append({
            "platform": "reddit",
            "url": m.group("url"),
            "subreddit": m.group("sub"),
            "upvotes": int(m.group("upvotes").replace(",", "")),
            "comments": int(m.group("comments").replace(",", "")),
            "comments_text": comments_text,
        })
    return sections


async def summarize_community(
    community_map: dict[str, str],
    groups: list,
) -> tuple[dict[str, CommunityInsight], dict[str, Any]]:
    """Per-platform community summarization.

    For each group's blob, split into platform sections (HN, Reddit, both).
    For each section: filter comments via gpt-5-nano relevance filter, call
    summarizer LLM per platform with filtered comments, build a ThreadInfo.
    Aggregate ThreadInfo records into CommunityInsight.threads.
    """
    result: dict[str, CommunityInsight] = {}
    cumulative_usage: dict[str, Any] = {}

    if not community_map:
        return result, cumulative_usage

    client = get_openai_client()
    model = settings.openai_model_light

    for group in groups:
        primary_url = group.primary_url
        blob = community_map.get(primary_url)
        if not blob:
            continue

        sections = _split_blob_by_platform(blob)
        if not sections:
            continue

        threads: list[ThreadInfo] = []
        article_title = group.group_title
        # Prefer first item's metadata for article context if available
        article_excerpt = ""

        for section in sections:
            # Stage 1: relevance filter
            filtered_comments, filter_usage = await filter_relevant_comments(
                section["comments_text"],
                article_title=article_title,
                article_excerpt=article_excerpt,
                max_pick=10,
            )
            cumulative_usage = merge_usage_metrics(cumulative_usage, filter_usage)

            if not filtered_comments:
                # Nothing relevant from this platform; record empty thread (sentiment=None)
                threads.append(ThreadInfo(
                    platform=section["platform"],
                    url=section["url"],
                    subreddit=section.get("subreddit"),
                    upvotes=section["upvotes"],
                    comments=section["comments"],
                    sentiment=None,
                    quotes=[],
                    quotes_ko=[],
                    key_point=None,
                ))
                continue

            # Stage 2: per-platform summarizer call
            comments_blob = "\n".join(f'> "{c}"' for c in filtered_comments)
            user_content = COMMUNITY_SUMMARIZER_USER_TEMPLATE.format(
                groups_text=(
                    f"### Group 0 — {article_title}\n"
                    f"Original article: {article_title}\n"
                    f"Platform: {section['platform']}\n"
                    f"{comments_blob}"
                ),
            )

            kwargs = build_completion_kwargs(
                model=model,
                messages=[
                    {"role": "system", "content": COMMUNITY_SUMMARIZER_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=2000,
                response_format={"type": "json_object"},
                service_tier="flex",
                prompt_cache_key=f"community-summarize-{section['platform']}",
            )

            try:
                response = await with_flex_retry(
                    lambda: client.chat.completions.create(**kwargs),
                )
                raw_output = response.choices[0].message.content or ""
                data = parse_ai_json(raw_output, f"summarize-{section['platform']}")
                usage = extract_usage_metrics(response, model, requested_service_tier="flex")
                cumulative_usage = merge_usage_metrics(cumulative_usage, usage)
            except Exception as e:
                logger.warning("Summarizer failed for %s: %s", section["platform"], e)
                threads.append(ThreadInfo(
                    platform=section["platform"],
                    url=section["url"],
                    subreddit=section.get("subreddit"),
                    upvotes=section["upvotes"],
                    comments=section["comments"],
                    sentiment=None,
                    quotes=[],
                    quotes_ko=[],
                    key_point=None,
                ))
                continue

            # Parse summarizer output (single-group shape)
            llm_groups = (data or {}).get("groups", {})
            llm_data = llm_groups.get("group_0", {})

            threads.append(ThreadInfo(
                platform=section["platform"],
                url=section["url"],
                subreddit=section.get("subreddit"),
                upvotes=section["upvotes"],
                comments=section["comments"],
                sentiment=llm_data.get("sentiment"),
                quotes=list(llm_data.get("quotes") or []),
                quotes_ko=list(llm_data.get("quotes_ko") or []),
                key_point=llm_data.get("key_point"),
            ))

        if threads:
            result[primary_url] = CommunityInsight(threads=threads)

    return result, cumulative_usage
```

**Important — preserve old re-exports:** the old `_parse_source_meta`, `_parse_source_label` etc. may be imported from this file by other code. Search:

```
c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m grep -rn "from services.agents.ranking import" backend/
```

If anything imports the legacy parsers, KEEP them as-is (they're used by `_inject_cp_citations` history — though we deleted that — but other code may also depend on them).

**Step 5: Run tests — expect PASS**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_summarize_community_per_platform.py -v`

Expected: 4 passed.

Full regression:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ --tb=short -q`

Expected: same baseline + 4 new passing. Watch carefully for `test_pipeline.py`, `test_pipeline_rerun.py` (they may mock `summarize_community` — verify mocks still match the new shape).

If existing tests break: read each failure. If the test asserted on flat `quotes` field, update it to use `synthesized_threads()[0].quotes` (which works for both shapes via the hydration helper). Don't bypass the helper.

Lint:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/services/agents/ranking.py backend/tests/test_summarize_community_per_platform.py`

**Step 6: Commit**

```bash
git add backend/services/agents/ranking.py backend/tests/test_summarize_community_per_platform.py
git commit -m "refactor(ranking): per-platform summarize_community + relevance filter

Each blob in community_map is split into per-platform sections (HN,
Reddit, or both). Each section runs through gpt-5-nano relevance filter
(Task 3) then a dedicated summarizer LLM call. Results aggregate into
CommunityInsight.threads — quote provenance preserved by construction
since cross-platform never mixes.

Changes:
- _split_blob_by_platform: parse the [Hacker News|url=...] and
  [Reddit r/sub|url=...] header markers (already embedded by
  news_collection per the 2026-04-21 plumbing) to extract per-platform
  sections + their comments
- summarize_community: iterate sections, filter+summarize per section,
  build ThreadInfo records, package as CommunityInsight(threads=[...])
- Single-platform groups produce 1-thread insights; multi-platform
  produce 2-thread insights; sections that the summarizer judges
  off-topic (sentiment=null) are still recorded with empty quotes so
  downstream knows the platform was processed
- Cost: 2x summarizer calls when both platforms exist (~+\$0.005/day
  total)"
```

---

## Task 5: Update `_filter_community_map_by_summary` for threads structure

**Why:** The P1-1 ranking filter (added 2026-04-25) checks `insight.sentiment is not None` to decide if a community thread is relevant for ranking. With the new threads structure, this single field is gone — relevance lives per-thread. New rule: keep an entry if ANY thread has non-null sentiment.

**Files:**
- Modify: `backend/services/pipeline.py` — `_filter_community_map_by_summary`
- Modify: `backend/tests/test_ranking_filtered_community.py` — extend with threads-structure tests

**Step 1: Write failing tests**

Append to `backend/tests/test_ranking_filtered_community.py`:

```python
from models.news_pipeline import ThreadInfo


def test_filter_keeps_when_any_thread_has_sentiment():
    """New: if at least one thread in insight.threads has non-null sentiment,
    the community_map entry is kept (the dominant thread carries usable signal)."""
    from services.pipeline import _filter_community_map_by_summary

    community_map = {
        "https://example.com/x": "blob",
    }
    community_summary_map = {
        "https://example.com/x": CommunityInsight(threads=[
            ThreadInfo(platform="hackernews", url="https://news.ycombinator.com/item?id=1",
                       upvotes=100, comments=10, sentiment="mixed",
                       quotes=["q"], quotes_ko=["인용"], key_point="kp"),
            ThreadInfo(platform="reddit", url="https://www.reddit.com/r/x/comments/y/z/",
                       subreddit="x", upvotes=50, comments=5, sentiment=None,
                       quotes=[], quotes_ko=[], key_point=None),
        ]),
    }
    filtered = _filter_community_map_by_summary(community_map, community_summary_map)
    assert "https://example.com/x" in filtered


def test_filter_drops_when_all_threads_off_topic():
    """If every thread has sentiment=None, drop the entry — same as the
    legacy single-sentiment=null case."""
    from services.pipeline import _filter_community_map_by_summary

    community_map = {
        "https://example.com/x": "blob",
    }
    community_summary_map = {
        "https://example.com/x": CommunityInsight(threads=[
            ThreadInfo(platform="hackernews", url="https://x", upvotes=100, comments=10,
                       sentiment=None, quotes=[], quotes_ko=[], key_point=None),
            ThreadInfo(platform="reddit", url="https://y", subreddit="x", upvotes=50,
                       comments=5, sentiment=None, quotes=[], quotes_ko=[], key_point=None),
        ]),
    }
    filtered = _filter_community_map_by_summary(community_map, community_summary_map)
    assert "https://example.com/x" not in filtered


def test_filter_legacy_insight_still_works_via_synthesized_threads():
    """Old checkpoints with flat sentiment field hydrate to single-thread
    via synthesized_threads(); the filter must use that uniform shape."""
    from services.pipeline import _filter_community_map_by_summary

    community_map = {
        "https://example.com/x": "blob",
    }
    community_summary_map = {
        # Legacy format: no threads, flat sentiment
        "https://example.com/x": CommunityInsight(
            source_label="Hacker News 100↑ · 10 comments",
            sentiment="mixed",
            quotes=["legacy q"],
            hn_url="https://news.ycombinator.com/item?id=1",
        ),
    }
    filtered = _filter_community_map_by_summary(community_map, community_summary_map)
    assert "https://example.com/x" in filtered
```

**Step 2: Run tests — expect FAIL or partial pass**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_ranking_filtered_community.py -v`

Expected: existing tests still pass (legacy behavior); 3 new tests fail because the filter checks `ins.sentiment` directly (only legacy field) without hydrating threads.

**Step 3: Update `_filter_community_map_by_summary`**

In `backend/services/pipeline.py`, find the function and replace its body:

```python
def _filter_community_map_by_summary(
    community_map: dict[str, str],
    community_summary_map: dict[str, "CommunityInsight"],
) -> dict[str, str]:
    """Drop community_map entries whose summarizer marked the discussion as
    irrelevant (every thread sentiment=None) to the source article.

    Works uniformly across legacy flat-shape insights and new threads-shape:
    uses synthesized_threads() to get a uniform list[ThreadInfo] and keeps the
    entry if ANY thread has non-null sentiment. Graceful degradation: if
    summary_map is empty (summarizer failed entirely), pass community_map
    through unchanged."""
    if not community_summary_map:
        return community_map

    def _has_signal(insight) -> bool:
        threads = insight.synthesized_threads()
        return any(t.sentiment is not None for t in threads) if threads else False

    return {
        url: raw
        for url, raw in community_map.items()
        if (ins := community_summary_map.get(url)) is not None and _has_signal(ins)
    }
```

**Step 4: Run tests — expect PASS**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_ranking_filtered_community.py -v`

Expected: 7 passed (4 original + 3 new).

Full regression:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ --tb=short -q`

Lint:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/services/pipeline.py backend/tests/test_ranking_filtered_community.py`

**Step 5: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_ranking_filtered_community.py
git commit -m "fix(ranking): filter handles per-thread sentiment in new shape

_filter_community_map_by_summary previously checked insight.sentiment
(single field); new CommunityInsight has per-thread sentiment in
threads[N].sentiment. Use synthesized_threads() for a uniform view that
works for both legacy flat-shape and new threads-shape, then keep the
community_map entry if ANY thread has non-null sentiment.

Apr 25 DeepSeek case (single platform, single sentiment=null) still
drops correctly. New: a multi-platform group where one platform has
substantive discussion and the other is off-topic still keeps the
entry — the dominant platform's signal is enough."
```

---

## Task 6: Update `_build_cp_data_entry` to emit per-thread entries

**Why:** Today `_build_cp_data_entry` returns ONE entry per insight (with concatenated platform info in source_label). With threads structure, each insight can produce MULTIPLE entries — one per thread. Each entry feeds the writer with single-platform context: writer sees `Topic: ... Platform: hackernews ... HackerNewsURL: ...` and produces a single `**Hacker News** (N↑)` block per entry. No more "split into 2 blocks if Platform: lists both" gymnastics.

**Files:**
- Modify: `backend/services/pipeline_digest.py` — `_build_cp_data_entry` + caller loop
- Modify: `backend/tests/test_cp_data_builder.py` — extend with threads-structure tests

**Step 1: Write failing tests**

Append to `backend/tests/test_cp_data_builder.py`:

```python
from models.news_pipeline import ThreadInfo


def test_cp_entries_threads_produce_one_per_thread():
    """New: insight with 2 threads (HN + Reddit) produces 2 separate CP Data
    entries. Each entry is single-platform — Platform field has only one
    platform name, only one URL line (HackerNewsURL OR RedditURL)."""
    from services.pipeline import _build_cp_data_entries

    insight = CommunityInsight(threads=[
        ThreadInfo(
            platform="hackernews",
            url="https://news.ycombinator.com/item?id=42",
            upvotes=1041,
            comments=689,
            sentiment="mixed",
            quotes=["hn quote with substance over ten chars"],
            quotes_ko=["에이치엔 인용 충분히 긴 한국어"],
            key_point="HN discussion",
        ),
        ThreadInfo(
            platform="reddit",
            url="https://www.reddit.com/r/OpenAI/comments/abc/t/",
            subreddit="OpenAI",
            upvotes=642,
            comments=230,
            sentiment="negative",
            quotes=["reddit quote with substance over ten chars"],
            quotes_ko=["레딧 인용 충분히 긴 한국어"],
            key_point="Reddit critique",
        ),
    ])
    group = _make_group()
    entries = _build_cp_data_entries(group, insight)

    assert len(entries) == 2

    hn_entry = next(e for e in entries if "Platform: Hacker News" in e)
    assert "HackerNewsURL: https://news.ycombinator.com/item?id=42" in hn_entry
    assert "RedditURL:" not in hn_entry
    assert 'English quote 1: "hn quote with substance over ten chars"' in hn_entry

    r_entry = next(e for e in entries if "Platform: r/OpenAI" in e)
    assert "RedditURL: https://www.reddit.com/r/OpenAI/comments/abc/t/" in r_entry
    assert "HackerNewsURL:" not in r_entry
    assert 'English quote 1: "reddit quote with substance over ten chars"' in r_entry


def test_cp_entries_skip_off_topic_thread():
    """Threads with sentiment=None are skipped (no CP entry for them) even if
    other threads in the same insight produce entries."""
    from services.pipeline import _build_cp_data_entries

    insight = CommunityInsight(threads=[
        ThreadInfo(
            platform="hackernews", url="https://x", upvotes=100, comments=10,
            sentiment="mixed",
            quotes=["good quote with substance over ten chars"],
            quotes_ko=["좋은 인용 충분히 긴 한국어 텍스트"],
            key_point="ok",
        ),
        ThreadInfo(
            platform="reddit", url="https://y", subreddit="x", upvotes=50, comments=5,
            sentiment=None,
            quotes=[], quotes_ko=[], key_point=None,
        ),
    ])
    entries = _build_cp_data_entries(_make_group(), insight)
    assert len(entries) == 1
    assert "Platform: Hacker News" in entries[0]


def test_cp_entries_apply_per_thread_signal_threshold():
    """Each thread checks the upvote/comment threshold independently. A weak
    HN thread (6↑, 1 comment) drops even if the Reddit thread is strong."""
    from services.pipeline import _build_cp_data_entries

    insight = CommunityInsight(threads=[
        ThreadInfo(
            platform="hackernews", url="https://hn", upvotes=6, comments=1,
            sentiment="negative",
            quotes=["a quote with substance over ten chars"],
            quotes_ko=["인용 충분히 긴 한국어"],
            key_point="weak",
        ),
        ThreadInfo(
            platform="reddit", url="https://r", subreddit="x", upvotes=500, comments=50,
            sentiment="mixed",
            quotes=["a quote with substance over ten chars"],
            quotes_ko=["인용 충분히 긴 한국어"],
            key_point="strong",
        ),
    ])
    entries = _build_cp_data_entries(_make_group(), insight)
    # Only Reddit (strong signal) survives
    assert len(entries) == 1
    assert "Platform: r/x" in entries[0]


def test_cp_entries_legacy_insight_via_hydration():
    """Legacy CommunityInsight with flat fields hydrates to single thread →
    one CP entry."""
    from services.pipeline import _build_cp_data_entries

    insight = CommunityInsight(
        source_label="Hacker News 79↑ · 25 comments",
        sentiment="mixed",
        quotes=["legacy quote with substance over ten chars"],
        quotes_ko=["레거시 인용 충분히 긴 한국어"],
        key_point="legacy",
        hn_url="https://news.ycombinator.com/item?id=1",
    )
    entries = _build_cp_data_entries(_make_group(), insight)
    assert len(entries) == 1
    assert "Platform: Hacker News" in entries[0]


def test_cp_entries_returns_empty_when_insight_none():
    from services.pipeline import _build_cp_data_entries

    assert _build_cp_data_entries(_make_group(), None) == []
```

**Step 2: Run tests — expect FAIL**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_data_builder.py -v -k "threads or legacy_insight or empty_when_insight_none"`

Expected: FAIL on missing `_build_cp_data_entries` (note plural — new function returning a list).

**Step 3: Add `_build_cp_data_entries` (plural) + adapter for old callers**

In `backend/services/pipeline_digest.py`, near `_build_cp_data_entry` (singular), add the new plural version:

```python
def _build_cp_data_entries(
    group: "ClassifiedGroup",
    insight: "CommunityInsight | None",
) -> list[str]:
    """Build per-thread CP Data entries for a single topic. Returns 0..N
    entries (one per thread that passes the signal threshold + has quotes
    or key_point). Each entry is single-platform — writer sees one platform
    per entry and produces one block per entry (no multi-platform split rule).
    """
    if insight is None:
        return []

    entries: list[str] = []
    for thread in insight.synthesized_threads():
        # Per-thread signal threshold — weak threads (HN 6↑, 1 comment) drop
        if not _thread_has_strong_signal(thread):
            continue
        # Need quotes or key_point to render usefully
        if not (thread.quotes or thread.key_point):
            continue
        # Skip off-topic threads (summarizer marked sentiment=None)
        if thread.sentiment is None:
            continue

        entry = _build_single_thread_entry(group, thread)
        if entry is not None:
            entries.append(entry)
    return entries


def _thread_has_strong_signal(thread: "ThreadInfo") -> bool:
    """Per-thread version of the upvote/comment threshold check."""
    return thread.upvotes >= _CP_MIN_UPVOTES or thread.comments >= _CP_MIN_COMMENTS


def _build_single_thread_entry(
    group: "ClassifiedGroup",
    thread: "ThreadInfo",
) -> str | None:
    """Build the CP Data block for a single thread (one platform).

    Output shape:
        Topic: <group title>
        Platform: <Hacker News N↑ · M comments | r/sub (N↑)>
        HackerNewsURL: <url>          # OR
        RedditURL: <url>
        Sentiment: <mixed/positive/...>
        HasQuotes: yes — emit N blockquote(s) below
        English quote 1: "..."
        Korean quote 1 (translation of English quote 1): "..."
        ...
        Key Discussion: <key_point>
    """
    # Pair-aligned quote sanitization (preserve the strict 1:1 rule from
    # the 2026-04-25 fix)
    raw_en = list(thread.quotes or [])
    raw_ko = list(thread.quotes_ko or [])
    clean_quotes: list[str] = []
    clean_quotes_ko: list[str] = []
    for i in range(min(len(raw_en), len(raw_ko))):
        en = _sanitize_cp_quote(raw_en[i])
        ko = _sanitize_cp_quote(raw_ko[i])
        if en and ko:
            clean_quotes.append(en)
            clean_quotes_ko.append(ko)
    has_quotes = bool(clean_quotes)

    # Build platform label string in the legacy format the writer expects
    if thread.platform == "hackernews":
        platform_label = f"Hacker News {thread.upvotes}↑ · {thread.comments} comments"
    else:
        platform_label = f"r/{thread.subreddit} ({thread.upvotes}↑)"

    parts = [f"Topic: {group.group_title}"]
    parts.append(f"Platform: {platform_label}")
    if thread.platform == "hackernews":
        parts.append(f"HackerNewsURL: {thread.url}")
    else:
        parts.append(f"RedditURL: {thread.url}")
    parts.append(f"Sentiment: {thread.sentiment}")
    if has_quotes:
        parts.append(f"HasQuotes: yes — emit {len(clean_quotes)} blockquote(s) below")
        for i, q in enumerate(clean_quotes, start=1):
            parts.append(f'English quote {i}: "{q}"')
        for i, q in enumerate(clean_quotes_ko, start=1):
            parts.append(f'Korean quote {i} (translation of English quote {i}): "{q}"')
    else:
        parts.append("HasQuotes: no — DO NOT emit any blockquote for this topic, write key point as a regular paragraph only")
    if thread.key_point:
        parts.append(f"Key Discussion: {thread.key_point}")
    return "\n".join(parts)
```

Then update the loop in `_generate_digest` that builds `cp_entries`:

```python
# OLD:
# cp_entries: list[str] = []
# for group in classified:
#     insight = community_summary_map.get(group.primary_url)
#     entry = _build_cp_data_entry(group, insight)
#     if entry is not None:
#         cp_entries.append(entry)

# NEW:
cp_entries: list[str] = []
for group in classified:
    insight = community_summary_map.get(group.primary_url)
    entries = _build_cp_data_entries(group, insight)
    cp_entries.extend(entries)
```

KEEP the old `_build_cp_data_entry` (singular) as a deprecated wrapper for any external callers — return the first entry from the plural version, or None:

```python
def _build_cp_data_entry(
    group: "ClassifiedGroup",
    insight: "CommunityInsight | None",
) -> str | None:
    """DEPRECATED: returns the first per-thread entry (or None). Use
    _build_cp_data_entries (plural) for the new per-thread shape."""
    entries = _build_cp_data_entries(group, insight)
    return entries[0] if entries else None
```

Re-export from `pipeline.py` (add `_build_cp_data_entries` next to existing `_build_cp_data_entry`).

**Step 4: Run tests**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_data_builder.py -v`

Expected: existing 20 tests still pass (now via the deprecated wrapper that calls the plural) + 5 new tests pass.

Full regression:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ --tb=short -q`

Lint:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/services/pipeline_digest.py backend/services/pipeline.py backend/tests/test_cp_data_builder.py`

**Step 5: Commit**

```bash
git add backend/services/pipeline_digest.py backend/services/pipeline.py backend/tests/test_cp_data_builder.py
git commit -m "feat(cp-data): per-thread CP Data entries

_build_cp_data_entries (plural) returns 0..N CP Data blocks per insight,
one per thread that passes the signal threshold + has quotes or
key_point + has non-null sentiment. Each entry is single-platform: the
writer sees one Platform line, one URL line (HackerNewsURL OR
RedditURL), one set of quotes — no need to 'split into 2 blocks' as the
data is already split.

Per-thread signal threshold: a weak HN thread (6↑, 1 comment) drops
even when paired with a strong Reddit thread (was previously: whole
insight survived if EITHER platform was strong). Cleaner — each block
shown to readers passes the threshold on its own.

Per-thread quote sanitization preserves the 2026-04-25 strict 1:1 EN/KO
pairing rule per thread.

Old _build_cp_data_entry (singular) kept as deprecated wrapper that
returns the first entry; existing tests pass through unchanged."
```

---

## Task 7: Simplify writer prompt rule 9 (drop multi-platform split rule)

**Why:** With per-thread CP Data entries (Task 6), each block the writer renders is single-platform from the start. The "Multi-platform topics: split into 2 blocks" instruction in rule 9 becomes obsolete and confusing. Remove it. Skeleton stays mostly the same (already single-platform examples).

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` — rule 9

**No unit test** — prompt wording change. Verified via rendered prompt check.

**Step 1: Locate current rule 9**

Run:

```
cd c:/Users/amy/Desktop/0to1log && c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -c "
import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'backend')
from services.agents.prompts_news_pipeline import get_digest_prompt
p = get_digest_prompt('expert', 'business', ['sample'])
m = re.search(r'9\.\s*COMMUNITY PULSE[\s\S]*?(?=\n\{handbook|\n10\.|\n\n##)', p)
print(m.group(0))
"
```

Find the `Multi-platform topics:` bullet inside rule 9.

**Step 2: Remove the multi-platform bullet**

In `backend/services/agents/prompts_news_pipeline.py`, find this exact bullet inside rule 9:

```
   - **Multi-platform topics:** if `Platform:` lists BOTH Hacker News AND r/<sub> (e.g. "Hacker News 1041↑ · 689 comments · r/OpenAI (642↑)"), emit TWO separate blocks — one per platform — each with its own `[CITE_N]` token whose URL matches that platform. Never combine them into one block.
```

Delete the entire bullet (full line including the leading newline). The remaining bullets (block header format, attribution format, HasQuotes:yes/no, etc.) stay.

**Step 3: Verify rule 9 no longer mentions multi-platform**

Run:

```
cd c:/Users/amy/Desktop/0to1log && c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, 'backend')
from services.agents.prompts_news_pipeline import get_digest_prompt
p = get_digest_prompt('expert', 'business', ['sample'])
assert 'Multi-platform topics' not in p, 'multi-platform rule still present'
# Other bullets must still exist
assert 'Block header format (REQUIRED)' in p, 'block header rule missing'
assert 'Sentiment summary must derive from quotes only' in p, 'hallucination guard missing'
print('OK rule 9 simplified')
"
```

Expected: `OK rule 9 simplified`.

**Step 4: Regression + lint**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ --tb=short -q`

Expected: same baseline. Note `test_cp_skeleton_cite_pattern.py` may have assertions referencing the multi-platform behavior — review but skeletons themselves are single-platform examples so should pass.

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/services/agents/prompts_news_pipeline.py`

**Step 5: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "chore(cp-prompt): drop multi-platform split rule from rule 9

With per-thread CP Data entries (Task 6 of cp-per-platform redesign),
each block the writer renders is already single-platform — the data
arrives split. The 'Multi-platform topics: emit TWO separate blocks'
instruction is obsolete and adds noise to the prompt.

Other rule 9 bullets (block header format, attribution, HasQuotes
yes/no, sentiment-derives-from-quotes guard) all remain — only the
multi-platform sub-bullet removed."
```

---

## Task 8: Apr 26 cron verification

**Why:** Tasks 1-7 are unit + integration tested. Task 8 verifies the redesign in production: real cron run produces per-platform CP, off-topic comments filtered out, no quote duplication across platforms.

**Files:** no modifications — script-only validation + journal entry.

**Step 1: Wait for next daily cron**

Apr 26 daily cron fires at 07:00 KST (22:00 UTC Apr 25). Wait for completion (~30 min) OR manually trigger if needed:

```bash
CRON_SECRET=$(grep '^CRON_SECRET=' c:/Users/amy/Desktop/0to1log/backend/.env | cut -d= -f2-)
curl -sS -X POST https://0to1log-production.up.railway.app/api/cron/news \
  -H "x-cron-secret: $CRON_SECRET"
```

Wait for `pipeline_runs.status=success` for `news-2026-04-26`.

**Step 2: Verify checkpoints have new threads structure**

```python
# /tmp/verify_apr26_threads.py
import io, os, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(r"c:\Users\amy\Desktop\0to1log\backend\.env")
sb = create_client(os.environ["SUPABASE_URL"], os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"])

run = sb.table("pipeline_runs").select("id").eq("run_key", "news-2026-04-26").execute().data
if not run:
    print("No Apr 26 run yet")
    sys.exit(1)
run_id = run[0]["id"]

ckpt = sb.table("pipeline_checkpoints").select("data").eq("run_id", run_id).eq("stage", "community_summarize").execute().data
if not ckpt:
    print("No community_summarize checkpoint")
    sys.exit(1)

summaries = ckpt[0]["data"].get("summaries") or {}
print(f"=== community_summarize: {len(summaries)} insights ===\n")
for url, ins in summaries.items():
    threads = ins.get("threads") or []
    print(f"[{url[:70]}]")
    if threads:
        print(f"  NEW shape: {len(threads)} thread(s)")
        for t in threads:
            print(f"    - {t.get('platform')} ({t.get('upvotes')}↑, {t.get('comments')} comments) "
                  f"sentiment={t.get('sentiment')} quotes={len(t.get('quotes') or [])}")
    else:
        print(f"  LEGACY shape (no threads field)")
        print(f"  source_label: {ins.get('source_label')}")
```

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe /tmp/verify_apr26_threads.py`

Expected: every insight uses NEW shape with `threads` populated. Each thread has its own sentiment, quotes, upvotes.

**Step 3: Verify CP rendering**

Re-use `verify_apr24_v2.py` style script for Apr 26. Expected:
- Each block in CP body is single-platform
- No quote text duplicated across HN and Reddit blocks
- No off-topic comment quotes (the relevance filter caught them)
- Hallucination guard, threshold, linkifier all still working from prior fixes

**Step 4: Spot-check a busy thread**

Pick the day's biggest HN thread. Inspect what comments survived the filter:

```python
# /tmp/spotcheck_relevance.py — picks one insight and dumps the filtered comments
# (would need to log them; alternatively, look at the actual quotes that ended up in the CP block)
```

Confirm: filtered comments are about the article topic, not political tangents.

**Step 5: Write journal entry**

Create `vault/12-Journal-&-Decisions/2026-04-26-cp-per-platform-redesign.md`:

```markdown
# CP Per-Platform Redesign — 2026-04-26

## Problem

Two coupled CP issues:
1. (External P1-2) Quote provenance lost — summarizer received concatenated
   HN+Reddit blob, output flat quotes list with no platform tags. Writer
   guessed platform attribution non-deterministically — Apr 24 research
   personas duplicated quotes across blocks; business split correctly.
2. (Apr 25 DeepSeek) HN thread top voted comments were political flame
   wars (Tiananmen, Iran-Israel). Summarizer correctly judged as off-topic
   and dropped the entire CP map → no CP section in either digest.

## Decision

Per-platform processing throughout the pipeline:
- Collection: top voted 30 per platform (was 5-10)
- gpt-5-nano relevance filter per platform (~$0.001/call)
- Summarizer called per platform (no cross-platform mixing)
- New CommunityInsight.threads structure with per-thread sentiment, quotes,
  url, upvotes — provenance preserved by construction
- CP Data builder emits 1 entry per thread (writer sees single-platform input)
- Writer prompt rule 9 simplified — multi-platform split rule removed

Plan: vault/09-Implementation/plans/2026-04-26-cp-per-platform-redesign.md

## Verification

[paste verify_apr26_threads.py output]

[paste CP rendering check output]

Spot-checked DeepSeek-style busy thread: filtered comments include
[<comment 1 substance>], [<comment 2>], ... — no political tangents.

## What's NOT addressed by this redesign

- target_date search window in news_collection (separate small plan,
  external review P2)
- Persona differentiation in CP (structural limit of short CP format)
- Linkifier auto-apply timing (operational, monitoring)

## Backward compat

- Old CommunityInsight checkpoints (flat shape) hydrate via
  synthesized_threads() helper — new code never crashes on old data
- _build_cp_data_entry singular kept as deprecated wrapper for any
  external import; returns first entry from the plural version
```

**Step 6: Commit journal**

```bash
git add vault/12-Journal-&-Decisions/2026-04-26-cp-per-platform-redesign.md
git commit -m "docs(journal): CP per-platform redesign — Apr 26 evidence

Records the redesign rationale (P1-2 quote provenance + Apr 25 DeepSeek
off-topic case), the decision (per-platform processing throughout), and
the post-deploy verification (Apr 26 cron output: per-thread structure
in checkpoints, no cross-platform quote duplication, filtered comments
on-topic)."
```

---

## Done criteria

- [ ] Task 1: ThreadInfo + CommunityInsight.threads + synthesized_threads(); 6 tests pass
- [ ] Task 2: Top-voted N expanded to 30; constants exported; 2 tests pass
- [ ] Task 3: filter_relevant_comments helper + gpt-5-nano LLM-as-judge; 6 tests pass; graceful fallbacks covered
- [ ] Task 4: summarize_community calls filter + summarizer per platform; aggregates into threads; 4 tests pass
- [ ] Task 5: _filter_community_map_by_summary uses synthesized_threads; 7 tests pass (4 existing + 3 new)
- [ ] Task 6: _build_cp_data_entries (plural) emits per-thread entries; per-thread threshold + sentiment check; 25 tests pass (20 existing + 5 new)
- [ ] Task 7: Rule 9 multi-platform bullet removed; rendered prompt verification passes
- [ ] Task 8: Apr 26 cron uses new shape; CP body has per-platform blocks with no cross-platform quote duplication; journal committed

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Old checkpoints break on load (Pydantic schema mismatch) | All new fields have defaults; legacy fields kept; `synthesized_threads()` provides uniform shape regardless of source. Tested in Task 1. |
| 2x summarizer cost when both platforms exist | ~+$0.005/day. Negligible. Documented. |
| Relevance filter too aggressive (drops on-topic) | Multi-layer fallback: empty input → empty output; LLM fail → top-N voted; LLM zero-select → top-3 polite fallback. Tested in Task 3. |
| Relevance filter too lenient (lets noise through) | Summarizer's own judgment is the second line of defense (sentiment=null on bad input). Two-stage filter. |
| Existing tests in `test_pipeline*` mock summarize_community with old shape | Update mocks during Task 4 regression. Use `synthesized_threads()` to bridge if tests assert on old quotes field. |
| Per-thread threshold too strict (drops legit secondary platforms) | Threshold is 50 upvotes OR 10 comments — same as before. Per-platform application is more honest (each block must justify itself). |
| Prompt cache invalidation on summarizer per-platform calls | New cache_key includes platform suffix (`community-summarize-hackernews` / `community-summarize-reddit`). Each platform builds its own cache entry. |
| Writer still emits broken bold-link markdown sometimes | Linkifier (already deployed) normalizes. Unrelated to this redesign. |
| News collection regex parsing of blob fails on edge cases | Regex tested on real Apr 24 blobs (have known shape). Defensive: empty match list → no sections → no threads → empty insight (no CP for that group). Same as today's "summarizer returned nothing" graceful path. |
| target_date window bug (P2) still affects collection | Separate plan. Not in scope. |
