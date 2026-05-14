# CP Writer URL Plumbing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move CP link generation from the fragile post-processor (`_inject_cp_citations`) into the writer itself — the writer receives thread URLs as part of the CP Data input and emits `**[Hacker News](hn_url)** (N↑)` block headers and `> — [Hacker News](hn_url)` attributions directly. The post-processor becomes a safety net that linkifies any remaining bare attributions or block headers.

**Architecture:** Three layers of defense. (1) CP Data input — the CP entry given to the writer already contains `HackerNewsURL:` / `RedditURL:` lines when the corresponding `CommunityInsight` has them. (2) Writer prompt — rule 9 and all 4 persona skeletons show `**[Platform](URL)** (N↑)` block headers and `> — [Platform](URL)` attributions as the REQUIRED format (no more bare text). (3) Post-processor — `_inject_cp_citations` becomes idempotent (skip already-linked lines) and picks up any remaining bare block headers/attributions the writer missed.

**Tech Stack:** Python 3.11, Pydantic v2, pytest. No new dependencies. Applies only to daily news pipeline (weekly writer has a different CP structure and is out of scope).

---

## Prerequisite context for implementer

- **Project:** 0to1log — AI news curation platform. Solo project (Amy). Backend: FastAPI + Supabase. Pipeline: `collect → classify → merge → community → community_summarize → ranking → enrich → write → quality → save`.
- **Why this exists:** Apr 24 news showed partial CP linkification (2/6 attributions linked in business digest; 4/8 in research). Root cause: writer emits `> — Hacker News` (bare text) per the current prompt contract; the `_inject_cp_citations` post-processor tries to linkify later by matching body blocks to checkpoint insights by upvote count. It misses (a) unbold block headers (writer inconsistency — emits `Hacker News (1041↑)` without `**`), (b) mixed-platform attribution inside a single block (writer puts "— Reddit" under an HN block because the underlying insight has quotes from both), and (c) `HasQuotes: no` blocks which have no attribution line at all to linkify. See `vault/09-Implementation/plans/2026-04-21-cp-thread-url-plumbing.md` for the upstream URL-plumbing work (collection → CommunityInsight.hn_url / reddit_url) that this plan builds on.
- **Key architectural contrast:** The rest of the body uses strict schema + `[CITE_N]` placeholders (`backend/services/agents/schemas/news_writer.py` → `citations[].url` as enum). CP has historically emitted bare attribution and relied on post-processing for links. This plan does NOT fold CP into the `[CITE_N]` system (CP URLs are block/attribution markdown, not paragraph-end citations) — instead the writer emits inline `[Label](URL)` markdown directly, using URLs it's given in the input. There's no schema enforcement for these inline URLs (they're inside the `en`/`ko` string fields), but the writer has explicit source-of-truth data (CP Data), so hallucination risk is low, and the post-processor safety net catches any drift.
- **File locations:**
  - CP Data builder: [pipeline_digest.py:577-613](backend/services/pipeline_digest.py#L577-L613) (inline inside `_generate_digest`, no helper function yet — Task 1 extracts it for testability)
  - Writer prompt rule 9: [prompts_news_pipeline.py:346-350](backend/services/agents/prompts_news_pipeline.py#L346-L350)
  - Skeletons (8 CP section locations across 4 constants × 2 locales): [prompts_news_pipeline.py:745, 787, 831, 874, 925, 966, 1006, 1036](backend/services/agents/prompts_news_pipeline.py)
  - QC EXEMPT wording (4 quality prompts): [prompts_news_pipeline.py:1765, 1830, 1895, 1960](backend/services/agents/prompts_news_pipeline.py)
  - Post-processor: [pipeline_digest.py:112-210](backend/services/pipeline_digest.py#L112-L210)
  - Existing tests: `backend/tests/test_cp_citation_injection.py` (9 tests), `backend/tests/test_community_source_meta.py`, `backend/scripts/smoke_cp_citations.py`
- **Date convention:** Today is 2026-04-24. Use absolute dates in commit messages and comments.
- **Virtualenv:** `backend/.venv` (Python 3.11). All commands below assume `c:\Users\amy\Desktop\0to1log` as cwd.
- **Commit policy (CLAUDE.md):** Commit by feature unit. Messages: `feat:`, `fix:`, `chore:`, `refactor:`. NEVER add `Co-Authored-By`. Frequent commits — one per task.

---

## File Structure

**Files to modify:**

| File | Responsibility | Changes |
|------|----------------|---------|
| `backend/services/pipeline_digest.py` | CP Data input builder | Extract `_build_cp_data_entry` helper (Task 1); include `HackerNewsURL` / `RedditURL` lines (Task 2) |
| `backend/services/pipeline_digest.py` | Post-processor `_inject_cp_citations` | Linkify block headers too; make idempotent on already-linked content (Task 6) |
| `backend/services/agents/prompts_news_pipeline.py` | Writer prompt rule 9 | Require `**[Platform](URL)** (N↑)` block header and `> — [Platform](URL)` attribution (Task 3) |
| `backend/services/agents/prompts_news_pipeline.py` | 4 skeletons × 2 locales = 8 CP sections | Replace bare attribution with URL-linked format (Task 4) |
| `backend/services/agents/prompts_news_pipeline.py` | QC EXEMPT wording × 4 | Update "separate `> — [Source](URL)` format" description so QC prompts match new writer contract (Task 5) |

**New test files:**

| File | Covers |
|------|--------|
| `backend/tests/test_cp_data_builder.py` | New — tests `_build_cp_data_entry` helper includes URLs |
| `backend/tests/test_cp_citation_injection.py` | Extended — new tests for block-header linkification + idempotency |

**Files NOT to touch:**
- `backend/services/news_collection.py` — URL collection already works (Apr 21 plan complete)
- `backend/services/agents/ranking.py` — `CommunityInsight.hn_url`/`reddit_url` already populated by `summarize_community`
- `backend/services/agents/schemas/news_writer.py` — CP URLs live inside the `en`/`ko` string fields, not in `citations[]`; strict schema unchanged
- `backend/models/news_pipeline.py` — `CommunityInsight` already has URL fields
- Weekly pipeline (`run_weekly_pipeline` / `pipeline.py:2709+`) — weekly uses a different CP structure; out of scope

---

## Task 1: Extract CP Data builder into a helper function

**Why:** The CP entry build loop at [pipeline_digest.py:577-601](backend/services/pipeline_digest.py#L577-L601) is inline inside a 300-line function. Extracting to a helper gives us a unit-testable seam for Task 2's URL plumbing without touching the calling code's flow.

**Files:**
- Modify: `backend/services/pipeline_digest.py:577-601` (extract helper)
- Create: `backend/tests/test_cp_data_builder.py`

**Step 1: Write the failing test**

Create `backend/tests/test_cp_data_builder.py`:

```python
"""Tests for _build_cp_data_entry — builds the per-topic CP Data block
passed to the writer prompt."""

from models.news_pipeline import ClassifiedGroup, CommunityInsight, GroupedItem


def _make_group(primary_url: str = "https://example.com/story", title: str = "Topic A") -> ClassifiedGroup:
    return ClassifiedGroup(
        group_title=title,
        items=[GroupedItem(url=primary_url, title=title, subcategory="news")],
        category="research",
        subcategory="news",
        reason="[LEAD] test",
        primary_url=primary_url,
    )


def test_cp_entry_with_quotes():
    from services.pipeline_digest import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 79↑ · 116 comments",
        sentiment="mixed",
        quotes=["first real quote over ten chars"],
        quotes_ko=["열 글자 이상의 실제 인용"],
        key_point="Community is debating the approach",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    assert "Topic: Topic A" in entry
    assert "Platform: Hacker News 79↑ · 116 comments" in entry
    assert "Sentiment: mixed" in entry
    assert "HasQuotes: yes — emit 1 blockquote(s) below" in entry
    assert 'English quote 1: "first real quote over ten chars"' in entry
    assert 'Korean quote 1 (translation of English quote 1): "열 글자 이상의 실제 인용"' in entry
    assert "Key Discussion: Community is debating the approach" in entry


def test_cp_entry_without_quotes():
    from services.pipeline_digest import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="r/OpenAI (500↑)",
        sentiment="negative",
        quotes=[],
        quotes_ko=[],
        key_point="Users unhappy with pricing",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    assert "HasQuotes: no — DO NOT emit any blockquote" in entry
    assert "Key Discussion: Users unhappy with pricing" in entry
    assert "English quote" not in entry


def test_cp_entry_returns_none_when_no_content():
    """Insight with no quotes AND no key_point produces nothing useful for CP."""
    from services.pipeline_digest import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 5↑",
        sentiment="neutral",
        quotes=[],
        quotes_ko=[],
        key_point=None,
    )
    assert _build_cp_data_entry(_make_group(), insight) is None


def test_cp_entry_returns_none_when_insight_is_none():
    from services.pipeline_digest import _build_cp_data_entry

    assert _build_cp_data_entry(_make_group(), None) is None


def test_cp_entry_sanitizes_surrounding_quote_marks():
    """Quotes wrapped in extra quote marks (from old checkpoints) are unwrapped."""
    from services.pipeline_digest import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 5↑",
        quotes=['"real quote with wrapping"'],
        quotes_ko=['"실제 인용 감쌈"'],
        key_point="k",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    assert 'English quote 1: "real quote with wrapping"' in entry
    # Unwrapped (no extra outer quotes)
    assert 'English quote 1: ""real quote with wrapping""' not in entry


def test_cp_entry_rejects_quote_containing_url():
    """Quote with a URL is suspicious (likely summarizer leaked a link) — drop it."""
    from services.pipeline_digest import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 5↑",
        quotes=["Check out https://example.com for details"],
        quotes_ko=["자세한 내용은 https://example.com 참조"],
        key_point="discussion",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    # URL-containing quote dropped, so HasQuotes becomes no (since clean_quotes is empty)
    assert "HasQuotes: no" in entry
```

**Step 2: Run test to verify it fails**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_data_builder.py -v`

Expected: FAIL — `ImportError: cannot import name '_build_cp_data_entry'`.

**Step 3: Extract the helper**

In `backend/services/pipeline_digest.py`, add this helper above `_generate_digest` (before line 440 — near the existing `_inject_cp_citations` block):

```python
# ---------------------------------------------------------------------------
# CP Data input builder (per-topic entry passed to writer prompt)
# ---------------------------------------------------------------------------

_CP_QUOTE_MARKS = '"“”‘’\''
_CP_URL_PAT = re.compile(
    r"(?:https?://|\b(?:github|arxiv|twitter|x|youtu|youtube|medium|reddit|huggingface|paperswithcode|openai|anthropic|deepmind)\.(?:com|org|be)/)",
    re.IGNORECASE,
)


def _sanitize_cp_quote(q: str) -> str | None:
    """Strip surrounding quote marks up to 3 layers; reject quotes containing URLs
    or shorter than 10 chars (likely garbage or link-only comments)."""
    if not isinstance(q, str):
        return None
    s = q.strip()
    for _ in range(3):
        if len(s) >= 2 and s[0] in _CP_QUOTE_MARKS and s[-1] in _CP_QUOTE_MARKS:
            s = s[1:-1].strip()
        else:
            break
    if len(s) < 10 or _CP_URL_PAT.search(s):
        return None
    return s


def _build_cp_data_entry(
    group: "ClassifiedGroup",
    insight: "CommunityInsight | None",
) -> str | None:
    """Build the CP Data block for a single topic (primary_url → insight).

    Returns None when the insight is missing or has neither quotes nor key_point
    (nothing meaningful to render in CP).
    """
    if insight is None:
        return None
    if not (insight.quotes or insight.key_point):
        return None

    clean_quotes = [s for q in (insight.quotes or []) if (s := _sanitize_cp_quote(q))]
    clean_quotes_ko = [s for q in (insight.quotes_ko or []) if (s := _sanitize_cp_quote(q))]
    # Align lengths: quotes_ko should match quotes count (writer expects 1:1 mapping)
    clean_quotes_ko = clean_quotes_ko[:len(clean_quotes)]
    has_quotes = bool(clean_quotes)

    parts = [f"Topic: {group.group_title}"]
    parts.append(f"Platform: {insight.source_label}")
    parts.append(f"Sentiment: {insight.sentiment}")
    if has_quotes:
        parts.append(f"HasQuotes: yes — emit {len(clean_quotes)} blockquote(s) below")
        for i, q in enumerate(clean_quotes, start=1):
            parts.append(f'English quote {i}: "{q}"')
        for i, q in enumerate(clean_quotes_ko, start=1):
            parts.append(f'Korean quote {i} (translation of English quote {i}): "{q}"')
    else:
        parts.append("HasQuotes: no — DO NOT emit any blockquote for this topic, write key point as a regular paragraph only")
    if insight.key_point:
        parts.append(f"Key Discussion: {insight.key_point}")
    return "\n".join(parts)
```

Then replace the inline build at [pipeline_digest.py:556-601](backend/services/pipeline_digest.py#L556-L601) — delete the local `_quote_marks`, `_url_pat`, `_sanitize_quote`, and the `cp_entries` loop — replace with:

```python
    cp_entries: list[str] = []
    for group in classified:
        insight = community_summary_map.get(group.primary_url)
        entry = _build_cp_data_entry(group, insight)
        if entry is not None:
            cp_entries.append(entry)
```

**Step 4: Run tests to verify they pass**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_data_builder.py -v`

Expected: 6 passed.

Regression sweep:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ -v --tb=short`

Expected: all pass.

**Step 5: Commit**

```bash
git add backend/services/pipeline_digest.py backend/tests/test_cp_data_builder.py
git commit -m "refactor(cp-data): extract _build_cp_data_entry helper

Moves the per-topic CP Data block build from inline code inside
_generate_digest into a module-level helper so it becomes unit-testable.
Behavior-preserving — same output format, same sanitization rules."
```

---

## Task 2: Include thread URLs in CP Data entry

**Why:** This is the load-bearing data change. Once the helper emits `HackerNewsURL:` / `RedditURL:` lines, the writer prompt can reference those fields to emit inline markdown links. Without this step, writer has no URL data to work with.

**Files:**
- Modify: `backend/services/pipeline_digest.py` — extend `_build_cp_data_entry`
- Modify: `backend/tests/test_cp_data_builder.py` — new URL-plumbing tests

**Step 1: Write the failing tests**

Append to `backend/tests/test_cp_data_builder.py`:

```python
def test_cp_entry_includes_hn_url_when_present():
    from services.pipeline_digest import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 79↑ · 116 comments",
        quotes=["a real quote over ten chars"],
        quotes_ko=["열 글자 이상 실제 인용"],
        key_point="discussion",
        hn_url="https://news.ycombinator.com/item?id=42",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    assert "HackerNewsURL: https://news.ycombinator.com/item?id=42" in entry
    # No RedditURL line when reddit_url is None
    assert "RedditURL:" not in entry


def test_cp_entry_includes_reddit_url_when_present():
    from services.pipeline_digest import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="r/OpenAI (500↑)",
        quotes=["a real quote over ten chars"],
        quotes_ko=["열 글자 이상 실제 인용"],
        key_point="discussion",
        reddit_url="https://www.reddit.com/r/OpenAI/comments/abc/t/",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    assert "RedditURL: https://www.reddit.com/r/OpenAI/comments/abc/t/" in entry
    assert "HackerNewsURL:" not in entry


def test_cp_entry_includes_both_urls_when_present():
    """Multi-platform insight (e.g. GPT-5.5 story had both HN + r/OpenAI)."""
    from services.pipeline_digest import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 1041↑ · 689 comments · r/OpenAI (642↑)",
        quotes=["guardrails quote over ten chars", "pricing quote over ten chars"],
        quotes_ko=["안전장치 인용", "가격 인용"],
        key_point="discussion",
        hn_url="https://news.ycombinator.com/item?id=47879092",
        reddit_url="https://www.reddit.com/r/OpenAI/comments/1stqlnh/x/",
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    assert "HackerNewsURL: https://news.ycombinator.com/item?id=47879092" in entry
    assert "RedditURL: https://www.reddit.com/r/OpenAI/comments/1stqlnh/x/" in entry


def test_cp_entry_without_urls_works_for_old_checkpoints():
    """Insights hydrated from pre-plumbing checkpoints (Apr 21 and before) have
    no hn_url / reddit_url — entry should still build, just without URL lines."""
    from services.pipeline_digest import _build_cp_data_entry

    insight = CommunityInsight(
        source_label="Hacker News 5↑",
        quotes=["an old-checkpoint quote"],
        quotes_ko=["구 체크포인트 인용"],
        key_point="discussion",
        # hn_url and reddit_url default to None
    )
    entry = _build_cp_data_entry(_make_group(), insight)
    assert entry is not None
    assert "HackerNewsURL:" not in entry
    assert "RedditURL:" not in entry
```

**Step 2: Run tests to verify they fail**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_data_builder.py -v -k "url"`

Expected: 4 FAIL — assertions `"HackerNewsURL: ..."` / `"RedditURL: ..."` not found in entry.

**Step 3: Add URL lines to the entry build**

In `backend/services/pipeline_digest.py`, modify `_build_cp_data_entry` — insert after the `Platform:` line and before `Sentiment:`:

```python
    parts = [f"Topic: {group.group_title}"]
    parts.append(f"Platform: {insight.source_label}")
    # URL plumbing: writer uses these to emit **[Platform](URL)** block headers
    # and > — [Platform](URL) attributions directly. Lines omitted when insight
    # predates the URL-plumbing feature (Apr 21 plan) — writer then falls back
    # to bare text and the post-processor linkifies later.
    if getattr(insight, "hn_url", None):
        parts.append(f"HackerNewsURL: {insight.hn_url}")
    if getattr(insight, "reddit_url", None):
        parts.append(f"RedditURL: {insight.reddit_url}")
    parts.append(f"Sentiment: {insight.sentiment}")
```

**Step 4: Run tests to verify they pass**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_data_builder.py -v`

Expected: 10 passed (6 from Task 1 + 4 new).

Full regression:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ -v --tb=short`

Expected: all pass.

**Step 5: Commit**

```bash
git add backend/services/pipeline_digest.py backend/tests/test_cp_data_builder.py
git commit -m "feat(cp-data): thread hn_url/reddit_url into writer input

CP Data entries now carry HackerNewsURL: / RedditURL: lines when the
underlying CommunityInsight has them. Writer prompt (next commit) will
use these to emit **[Platform](URL)** block headers and
> — [Platform](URL) attributions directly — ending the bare-text +
post-processor matching pattern that missed unbold headers, mingled
quotes, and HasQuotes=no blocks on Apr 24. Old checkpoints without
hn_url/reddit_url degrade safely (lines omitted, writer emits bare
text, post-processor safety-net linkifies)."
```

---

## Task 3: Update writer prompt rule 9 — require linked attribution format

**Why:** The CP Data now carries URLs, but rule 9 at [prompts_news_pipeline.py:346-350](backend/services/agents/prompts_news_pipeline.py#L346-L350) still tells the writer to emit bare `> — Reddit` or `> — Hacker News`. Without updating rule 9, the writer ignores the new `HackerNewsURL:` / `RedditURL:` fields and keeps the old behavior. This is the behavior-change commit.

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py:346-350` (rule 9)

**Note:** No unit test — prompt rule changes are verified manually via the skeleton snapshot check in Task 4 and the end-to-end smoke in Task 7.

**Step 1: Read the current rule**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -c "from services.agents.prompts_news_pipeline import get_business_expert_prompt; import re; p = get_business_expert_prompt([]); m = re.search(r'9\. COMMUNITY PULSE[\s\S]*?(?=\n{handbook|\{handbook|\n\n##|\n10\.)', p); print(m.group(0) if m else 'not found')"`

Expected output: the current rule 9 text (3 bullets for HasQuotes yes/no + NEVER labels + Omit rule).

**Step 2: Update rule 9**

In `backend/services/agents/prompts_news_pipeline.py`, replace lines 346-350 with:

```python
9. COMMUNITY PULSE: write a single `## Community Pulse` (ko: `## 커뮤니티 반응`) section — see skeleton for exact format. For each topic in the Community Pulse Data input:
   - **Block header format (REQUIRED — must be bold):**
     - When `HackerNewsURL: <url>` is given: `**[Hacker News](<url>)** (N↑)` — use the full URL verbatim
     - When `RedditURL: <url>` is given: `**[r/<subreddit>](<url>)** (N↑)` — infer subreddit from the `Platform:` label
     - When neither URL is given (legacy CP Data without URL plumbing): fall back to `**Hacker News** (N↑)` / `**r/<subreddit>** (N↑)` bare — downstream post-processor will link if possible
   - **Multi-platform topics:** if `Platform:` lists BOTH Hacker News AND r/<sub> (e.g. "Hacker News 1041↑ · 689 comments · r/OpenAI (642↑)"), emit TWO separate blocks — one per platform — each with its own linked block header. Never combine them into one block.
   - `HasQuotes: yes` → emit blockquote(s) using the exact "English quote N" text in en and matching "Korean quote N" in ko. **Attribution format (REQUIRED):** `> — [Hacker News](<HackerNewsURL>)` or `> — [r/<subreddit>](<RedditURL>)` — use the same URL as the block header above. Bare `> — Hacker News` is a fallback for legacy CP Data only. Every blockquote's attribution URL MUST match its enclosing block's platform — never put a Reddit quote under an HN block or vice versa. If the quote clearly belongs to the OTHER platform, move it under that block instead.
   - `HasQuotes: no` → write ONE short paragraph based on Sentiment + Key Discussion. Do NOT emit any blockquote. Do NOT invent quotes.
   - NEVER write literal `[EN quote]`, `[KO quote]`, `Quote (EN)`, or `Quote (KO)` in the output — these are input labels, not output text.
   - Omit the entire Community Pulse section only when no Community Pulse Data was provided.
```

**Step 3: Verify the rule actually lands in the rendered prompt**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -c "from services.agents.prompts_news_pipeline import get_business_expert_prompt; p = get_business_expert_prompt([]); assert '**[Hacker News](<url>)** (N↑)' in p, 'rule 9 update did not land'; assert 'Attribution format (REQUIRED)' in p; print('OK')"`

Expected: `OK`.

**Step 4: Run existing tests to ensure nothing else broke**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ -v --tb=short`

Expected: all pass (prompt tests in `test_prompts_*` snapshot against content that may need updating — review any failures).

**Step 5: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "feat(cp-prompt): require linked block headers + attributions

Writer now reads HackerNewsURL / RedditURL from CP Data and emits
**[Hacker News](url)** block headers and > — [Hacker News](url)
attributions directly. Multi-platform topics (GPT-5.5 had HN 1041↑ +
r/OpenAI 642↑) must split into two blocks, each linked to its own
thread. Attribution URL must match its block's platform — fixes Apr 24
mingled-quote pattern where a Reddit quote sat under an HN block."
```

---

## Task 4: Update all 4 skeletons to show linked CP format

**Why:** The writer relies heavily on the skeleton for output shape (rule 9 describes the format abstractly; the skeleton makes it concrete). Eight CP section instances exist across the 4 skeleton constants × 2 locales. Without updating them, the writer sees an ambiguous signal: rule 9 says "link required" but the skeleton shows bare attribution — Show-Don't-Tell conflict.

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py` — 8 CP sections inside 4 skeleton constants:
  - `BUSINESS_EXPERT_SKELETON` (en @ line ~745, ko @ line ~787)
  - `BUSINESS_LEARNER_SKELETON` (en @ line ~831, ko @ line ~874)
  - `RESEARCH_EXPERT_SKELETON` (en @ line ~925, ko @ line ~966)
  - `RESEARCH_LEARNER_SKELETON` (en @ line ~1006, ko @ line ~1036)

**Note:** Prompts are plain string constants — line numbers will drift as the file is edited. Find each skeleton's CP section by searching for `## Community Pulse` or `## 커뮤니티 반응` inside each constant.

**Step 1: Write a format-check snapshot test**

Create `backend/tests/test_cp_skeleton_format.py`:

```python
"""Guards that every skeleton's Community Pulse section demonstrates the
new linked block-header + linked attribution format."""

import pytest


@pytest.mark.parametrize("constant_name", [
    "BUSINESS_EXPERT_SKELETON",
    "BUSINESS_LEARNER_SKELETON",
    "RESEARCH_EXPERT_SKELETON",
    "RESEARCH_LEARNER_SKELETON",
])
def test_skeleton_cp_section_uses_linked_block_header(constant_name):
    import services.agents.prompts_news_pipeline as prompts

    skeleton = getattr(prompts, constant_name)
    # At least one linked block header in EITHER locale (en or ko section)
    assert "**[Hacker News](https://news.ycombinator.com/" in skeleton, (
        f"{constant_name} CP section must show "
        "**[Hacker News](https://news.ycombinator.com/...)** as the block header example"
    )


@pytest.mark.parametrize("constant_name", [
    "BUSINESS_EXPERT_SKELETON",
    "BUSINESS_LEARNER_SKELETON",
    "RESEARCH_EXPERT_SKELETON",
    "RESEARCH_LEARNER_SKELETON",
])
def test_skeleton_cp_section_uses_linked_attribution(constant_name):
    import services.agents.prompts_news_pipeline as prompts

    skeleton = getattr(prompts, constant_name)
    # At least one linked attribution
    assert "> — [Hacker News](https://news.ycombinator.com/" in skeleton, (
        f"{constant_name} must show > — [Hacker News](url) attribution example"
    )


@pytest.mark.parametrize("constant_name", [
    "BUSINESS_EXPERT_SKELETON",
    "BUSINESS_LEARNER_SKELETON",
    "RESEARCH_EXPERT_SKELETON",
    "RESEARCH_LEARNER_SKELETON",
])
def test_skeleton_has_no_bare_cp_attribution(constant_name):
    """After Task 4 lands, no skeleton should have the old bare
    `> — Hacker News` or `> — Reddit` pattern as a demonstration —
    that pattern is a last-resort fallback, not the target format."""
    import re
    import services.agents.prompts_news_pipeline as prompts

    skeleton = getattr(prompts, constant_name)
    # Bare attribution = `> — Hacker News` at end of a line (no bracket/paren after)
    bare_hn = re.search(r"^>\s+—\s+Hacker News\s*$", skeleton, re.MULTILINE)
    bare_reddit = re.search(r"^>\s+—\s+Reddit\s*$", skeleton, re.MULTILINE)
    assert bare_hn is None, f"{constant_name} still contains bare `> — Hacker News` attribution"
    assert bare_reddit is None, f"{constant_name} still contains bare `> — Reddit` attribution"
```

**Step 2: Run tests to verify they fail**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_skeleton_format.py -v`

Expected: 12 FAIL — all 3 parametrized tests × 4 skeletons fail because current skeletons show bare attributions.

**Step 3: Update each of the 8 CP sections**

Open `backend/services/agents/prompts_news_pipeline.py` and locate each `## Community Pulse` / `## 커뮤니티 반응` block (8 total). Pattern to apply to each:

**Before (example from `BUSINESS_EXPERT_SKELETON` en):**
```
## Community Pulse

**r/OpenAI** (2.1K↑) — OpenAI's hiring push is seen as accelerating industry consolidation, sparking concern over startup talent pipelines.

> "If OpenAI hoovers up 3,500 more engineers, every Series A startup just lost their candidate pipeline."
> — Reddit

**Hacker News** (890↑) — Debate centers on the strategic pivot away from consumer products toward enterprise margins.

> "The real story is the pivot away from consumer -- enterprise margins are where the IPO math works."
> — Hacker News
```

**After:**
```
## Community Pulse

**[r/OpenAI](https://www.reddit.com/r/OpenAI/comments/example123/openai_hiring/)** (2.1K↑) — OpenAI's hiring push is seen as accelerating industry consolidation, sparking concern over startup talent pipelines.

> "If OpenAI hoovers up 3,500 more engineers, every Series A startup just lost their candidate pipeline."
> — [r/OpenAI](https://www.reddit.com/r/OpenAI/comments/example123/openai_hiring/)

**[Hacker News](https://news.ycombinator.com/item?id=example890)** (890↑) — Debate centers on the strategic pivot away from consumer products toward enterprise margins.

> "The real story is the pivot away from consumer -- enterprise margins are where the IPO math works."
> — [Hacker News](https://news.ycombinator.com/item?id=example890)
```

Apply the same pattern (bold label becomes linked bold label; attribution label becomes linked attribution) to all 8 CP sections:
- `BUSINESS_EXPERT_SKELETON` en (around line 745)
- `BUSINESS_EXPERT_SKELETON` ko (around line 787) — keep Korean text, update the link format; `커뮤니티 반응` heading stays unchanged
- `BUSINESS_LEARNER_SKELETON` en (around line 831)
- `BUSINESS_LEARNER_SKELETON` ko (around line 874)
- `RESEARCH_EXPERT_SKELETON` en (around line 925)
- `RESEARCH_EXPERT_SKELETON` ko (around line 966)
- `RESEARCH_LEARNER_SKELETON` en (around line 1006)
- `RESEARCH_LEARNER_SKELETON` ko (around line 1036)

Use `https://news.ycombinator.com/item?id=<short_id>` for HN example URLs and `https://www.reddit.com/r/<sub>/comments/<id>/<slug>/` for Reddit. The example URLs are illustrative only — writer will substitute with real URLs from the CP Data input.

**Step 4: Run tests to verify they pass**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_skeleton_format.py -v`

Expected: 12 passed.

Full regression:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ -v --tb=short`

Expected: all pass.

**Step 5: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py backend/tests/test_cp_skeleton_format.py
git commit -m "feat(cp-skeleton): show linked block-header + attribution format

All 4 skeletons × 2 locales = 8 CP sections now demonstrate the new
format: **[Hacker News](https://news.ycombinator.com/...)** (N↑) block
headers with > — [Hacker News](url) attributions. Test guards that no
skeleton falls back to bare > — Hacker News — that's a legacy-only
fallback for old checkpoints, not a target format."
```

---

## Task 5: Update QC rubric EXEMPT wording to match new contract

**Why:** Four quality rubrics (`QUALITY_CHECK_RESEARCH_EXPERT`, `..._LEARNER`, `QUALITY_CHECK_BUSINESS_EXPERT`, `..._LEARNER`) each have a `citation_coverage` sub-score bullet that says the CP section uses "a separate `> — [Source](URL)` attribution format" as an EXEMPT case. With the new writer contract, the linked attribution is no longer a separate-exempt case — it's the PRIMARY expected format. The wording should reflect that so the QC scorer doesn't flag it as an anomaly.

**Files:**
- Modify: `backend/services/agents/prompts_news_pipeline.py:1765, 1830, 1895, 1960`

**Step 1: Read the current EXEMPT wording**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m grep "separate.*attribution format" backend/services/agents/prompts_news_pipeline.py`

(Or use Grep tool directly.) Expected: 4 matching lines, all identical `EXEMPT` bullet.

**Step 2: Update the EXEMPT language at each of the 4 locations**

For each of the 4 occurrences, change:

```
**EXEMPT**: the `## 커뮤니티 반응` (Community Pulse) section — its quotes use a separate `> — [Source](URL)` attribution format at the end of the blockquote, NOT inline `[N](URL)`. Do NOT penalize CP blockquotes for missing inline citations.
```

to:

```
**EXEMPT**: the `## 커뮤니티 반응` (Community Pulse) section — its block headers use `**[Platform](URL)** (N↑)` and its quotes use `> — [Platform](URL)` attribution, NOT inline `[N](URL)` placeholders. Do NOT penalize CP blocks for missing inline citations. Do NOT penalize CP attributions for having a link — that IS the format.
```

Because the 4 occurrences are character-identical, use `replace_all=true`.

**Step 3: Verify the replacement landed**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -c "content = open('backend/services/agents/prompts_news_pipeline.py', encoding='utf-8').read(); assert content.count('Do NOT penalize CP attributions for having a link') == 4, 'expected 4 occurrences'; assert 'separate \`> — [Source](URL)\` attribution format' not in content, 'old wording still present'; print('OK')"`

Expected: `OK`.

**Step 4: Full regression**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ -v --tb=short`

Expected: all pass.

Also verify ruff:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/services/agents/prompts_news_pipeline.py`

Expected: `All checks passed!`

**Step 5: Commit**

```bash
git add backend/services/agents/prompts_news_pipeline.py
git commit -m "chore(cp-qc): update EXEMPT wording to match new writer contract

Linked CP attributions are now the PRIMARY format (per Task 3 writer
prompt), not a separate-exempt case. Update the EXEMPT bullet in all
4 quality rubrics so the scorer knows that > — [Platform](URL) is
expected, not anomalous."
```

---

## Task 6: Make `_inject_cp_citations` idempotent + linkify bare block headers

**Why:** The post-processor now plays a different role — it's a safety net for writer output that didn't fully follow the new contract (e.g., old cached prompt behavior, legacy checkpoints without `hn_url`, or writer drift). Two specific fixes: (a) when the writer already emitted `**[Hacker News](url)** (N↑)` or `> — [Hacker News](url)`, the post-processor must NOT double-link or corrupt the line (idempotency); (b) when the writer emitted a bare `**Hacker News** (N↑)` block header, the post-processor should linkify it too — not just the attribution lines below it.

**Files:**
- Modify: `backend/services/pipeline_digest.py` — `_inject_cp_citations` at [line 112-210](backend/services/pipeline_digest.py#L112-L210)
- Modify: `backend/tests/test_cp_citation_injection.py` — new tests for idempotency + block header linkification

**Step 1: Write failing tests**

Append to `backend/tests/test_cp_citation_injection.py`:

```python
def test_inject_linkifies_bare_block_header():
    """When writer emits a bare `**Hacker News** (79↑)` header (didn't follow
    the new contract), post-processor should linkify the header using the
    matched insight's hn_url."""
    from services.pipeline import _inject_cp_citations
    from models.news_pipeline import CommunityInsight

    body = """## Community Pulse

**Hacker News** (79↑) — discussion summary.

> "quote"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/X": CommunityInsight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "**[Hacker News](https://news.ycombinator.com/item?id=42)** (79↑)" in out
    assert "> — [Hacker News](https://news.ycombinator.com/item?id=42)" in out


def test_inject_linkifies_bare_reddit_block_header():
    from services.pipeline import _inject_cp_citations
    from models.news_pipeline import CommunityInsight

    body = """## Community Pulse

**r/OpenAI** (500↑) — sentiment.

> "quote"
> — r/OpenAI
"""
    cmap = {
        "https://example.com/X": CommunityInsight(
            source_label="r/OpenAI (500↑)",
            reddit_url="https://www.reddit.com/r/OpenAI/comments/abc/t/",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "**[r/OpenAI](https://www.reddit.com/r/OpenAI/comments/abc/t/)** (500↑)" in out


def test_inject_is_idempotent_on_already_linked_block_header():
    """Writer followed the new contract — block header already has
    [Label](URL). Post-processor must NOT double-link or otherwise
    corrupt the output."""
    from services.pipeline import _inject_cp_citations
    from models.news_pipeline import CommunityInsight

    original = """## Community Pulse

**[Hacker News](https://news.ycombinator.com/item?id=42)** (79↑) — discussion.

> "quote"
> — [Hacker News](https://news.ycombinator.com/item?id=42)
"""
    cmap = {
        "https://arxiv.org/abs/X": CommunityInsight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(original, cmap)
    # Output unchanged — post-processor detected the line was already linked
    assert out == original
    # Specifically: no double link like [[Hacker News](...)](...)
    assert "[[" not in out
    assert "]]" not in out


def test_inject_is_idempotent_on_already_linked_attribution():
    """Attribution already linked — post-processor must not touch it."""
    from services.pipeline import _inject_cp_citations
    from models.news_pipeline import CommunityInsight

    original = """## Community Pulse

**Hacker News** (79↑) — discussion.

> "quote A"
> — [Hacker News](https://news.ycombinator.com/item?id=42)

> "quote B"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/X": CommunityInsight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(original, cmap)
    # Already-linked "quote A" attribution unchanged
    assert out.count("> — [Hacker News](https://news.ycombinator.com/item?id=42)") == 3
    # "quote B" (bare) was linkified (attribution #1)
    # Block header was bare (unbold linkified) — attribution #2
    # "quote A" stayed (attribution #3)
    # Wait: block header linkify doesn't use `> — ` prefix — let me re-count:
    # attribution #1: quote A (was already linked, 1 count)
    # attribution #2: quote B (linkified now, 1 count)
    # That's 2 attribution lines with `> — [Hacker News](...)` total.
    # The block header `**[Hacker News](...)**` does NOT have `> — ` prefix.


def test_inject_handles_partial_writer_compliance():
    """Writer linked attribution but forgot block header — post-processor
    should still linkify the block header."""
    from services.pipeline import _inject_cp_citations
    from models.news_pipeline import CommunityInsight

    body = """## Community Pulse

**Hacker News** (79↑) — discussion.

> "quote"
> — [Hacker News](https://news.ycombinator.com/item?id=42)
"""
    cmap = {
        "https://arxiv.org/abs/X": CommunityInsight(
            source_label="Hacker News 79↑",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "**[Hacker News](https://news.ycombinator.com/item?id=42)** (79↑)" in out
    # Attribution stays linked (not double-linked)
    assert out.count("> — [Hacker News](https://news.ycombinator.com/item?id=42)") == 1
```

**Note:** `test_inject_is_idempotent_on_already_linked_attribution` has a correction — rewrite that test body as:

```python
def test_inject_is_idempotent_on_already_linked_attribution():
    """Attribution already linked — post-processor must not touch it."""
    from services.pipeline import _inject_cp_citations
    from models.news_pipeline import CommunityInsight

    body = """## Community Pulse

**[Hacker News](https://news.ycombinator.com/item?id=42)** (79↑) — discussion.

> "quote A"
> — [Hacker News](https://news.ycombinator.com/item?id=42)

> "quote B"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/X": CommunityInsight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    # Already-linked attribution (quote A) unchanged — exactly one occurrence expected in that position
    # Bare attribution (quote B) gets linkified — another occurrence
    # Total linked attribution count in output: 2
    linked_attr_count = out.count("> — [Hacker News](https://news.ycombinator.com/item?id=42)")
    assert linked_attr_count == 2, f"expected 2 linked attributions, got {linked_attr_count}"
    # No double-linking
    assert "[[" not in out
```

**Step 2: Run tests to verify they fail**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_citation_injection.py -v`

Expected: 5 new tests FAIL (existing 9 pass — already covers current behavior).

**Step 3: Update `_inject_cp_citations` in `backend/services/pipeline_digest.py`**

Replace the `_process_section` inner function inside `_inject_cp_citations` (around [line 174](backend/services/pipeline_digest.py#L174)) with:

```python
    # Already-linked block header: **[Label](url)** (N↑) — must match BEFORE
    # plain header regex, otherwise we'd re-process it and create **[[Label](url)](url)**.
    _CP_LINKED_HEADER_RE = re.compile(
        r"^\s*(?:-\s+)?\*\*\[(?P<label>[^\]]+)\]\((?P<url>https?://[^)]+)\)\*\*\s*\(\s*(?P<upvotes>[\d,.]+)(?P<kmult>[Kk]?)\s*↑",
    )
    # Already-linked attribution: > — [Label](url)
    _CP_LINKED_ATTR_RE = re.compile(r"^>\s+[—\-]+\s+\[[^\]]+\]\(https?://[^)]+\)\s*$")

    def _process_section(section_body: str) -> str:
        out_lines: list[str] = []
        current_label: str | None = None
        current_url: str | None = None

        for line in section_body.split("\n"):
            # Case 1: already-linked block header — leave alone, use its URL for
            # any bare attributions that follow.
            linked_hdr = _CP_LINKED_HEADER_RE.match(line)
            if linked_hdr:
                current_label = linked_hdr.group("label").strip()
                current_url = linked_hdr.group("url").strip()
                out_lines.append(line)
                continue

            # Case 2: bare block header — try to linkify it AND use URL for attributions.
            hdr = _CP_BLOCK_HEADER_RE.match(line)
            if hdr:
                label = hdr.group("label").strip()
                upvotes = _upvotes_to_int(hdr.group("upvotes"), hdr.group("kmult"))
                url = _lookup_url(label, upvotes) if upvotes >= 0 else None
                if url:
                    # Linkify the bold label in place, preserve the rest of the line
                    # (upvote parens, dash, summary text).
                    line = re.sub(
                        r"\*\*" + re.escape(label) + r"\*\*",
                        f"**[{label}]({url})**",
                        line,
                        count=1,
                    )
                    current_label = label
                    current_url = url
                else:
                    current_label = None
                    current_url = None
                out_lines.append(line)
                continue

            # Case 3: already-linked attribution — leave alone (idempotent).
            if _CP_LINKED_ATTR_RE.match(line):
                out_lines.append(line)
                continue

            # Case 4: bare attribution line under a known block — linkify it.
            if current_label and current_url:
                attr_pat = re.compile(
                    _CP_ATTR_RE_TMPL.format(label=re.escape(current_label))
                )
                if attr_pat.match(line):
                    line = f"> — [{current_label}]({current_url})"

            out_lines.append(line)
        return "\n".join(out_lines)
```

**Step 4: Run tests to verify they pass**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/test_cp_citation_injection.py -v`

Expected: 14 passed (9 existing + 5 new).

Full regression:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m pytest backend/tests/ -v --tb=short`

Expected: all pass.

Ruff:

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe -m ruff check backend/services/pipeline_digest.py`

Expected: `All checks passed!`

**Step 5: Commit**

```bash
git add backend/services/pipeline_digest.py backend/tests/test_cp_citation_injection.py
git commit -m "feat(cp-postproc): safety net for partial writer compliance

_inject_cp_citations is no longer the primary link source (that's now
the writer itself). Its job becomes: (1) linkify block headers AND
attributions when the writer emitted bare text (old prompt cache, no
CP URLs in checkpoint, writer drift); (2) leave already-linked content
alone — idempotency prevents **[[Label](url)](url)** corruption on
re-run or double-processing.

Covers 5 new cases: bare HN/Reddit block header linkify, idempotent
on linked header, idempotent on linked attribution, partial compliance
(header bare + attribution linked or vice versa)."
```

---

## Task 7: End-to-end validation on Apr 24 — rerun-from-write

**Why:** After Tasks 1-6 land, the fix covers the next fresh cron run. To verify on Apr 24 (which triggered this plan), we need to rerun from the `write` stage — QC-only rerun wouldn't regenerate the body. Post-deploy, we re-run, then smoke-check with `scripts/smoke_cp_citations.py` to confirm `linked > 0, raw == 0` for CP attributions.

**Files:** no modifications — script-only validation. But we capture evidence in a committed journal.

**Step 1: Wait for Railway deploy**

After pushing Tasks 1-6, wait for Railway to deploy (usually 2-4 min). Verify by looking at Railway logs or by calling the backend `/health` endpoint twice and comparing `git_sha` (if exposed) — or just wait 5 min.

**Step 2: Trigger a from-write rerun for Apr 24**

From the admin UI at `/admin/pipeline-runs/<run_id>`, click the "Write: Both" rerun option. This regenerates the writer output (both research + business, both personas, both locales) using the NEW prompt, then re-runs quality.

Alternatively (if clicking is not practical), post to the cron endpoint:

```bash
curl -X POST http://localhost:8000/api/cron/pipeline-rerun \
  -H "Content-Type: application/json" \
  -H "x-cron-secret: $CRON_SECRET" \
  -d '{"run_id":"a1ee1bec-8f18-415c-98c6-7d1a66e5482f","from_stage":"write","batch_id":"2026-04-24","category":null}'
```

Wait for completion (~8-15 min for write + QC × 2 digests).

**Step 3: Run the smoke script**

Run: `c:/Users/amy/Desktop/0to1log/backend/.venv/Scripts/python.exe backend/scripts/smoke_cp_citations.py 2026-04-24`

Expected output:
```
Loaded 3 insights
  with hn_url: 3, with reddit_url: 1
  2026-04-24-research-digest: linked=<N>, raw=0
  2026-04-24-research-digest-ko: linked=<N>, raw=0
  2026-04-24-business-digest: linked=<N>, raw=0
  2026-04-24-business-digest-ko: linked=<N>, raw=0
```

Success criteria: every digest shows `raw=0` (no bare attributions remaining) and `linked > 0`.

If any `raw > 0` persists, inspect the body to see what the writer emitted. The post-processor safety net (Task 6) should catch most writer drift; if it didn't, the remaining gap is a writer prompt issue — iterate on rule 9 (Task 3) wording.

**Step 4: Record evidence in a journal note**

Create `vault/12-Journal-&-Decisions/2026-04-24-cp-writer-url-plumbing.md`:

```markdown
# CP Writer URL Plumbing — 2026-04-24

## Problem

Apr 24 news posts showed partial CP linkification:
- research en+ko: linked=4, raw=4 (50%)
- business en+ko: linked=2, raw=4 (33%)

Root causes: (1) writer sometimes dropped `**bold**` on block headers
(business expert both locales), breaking `_inject_cp_citations` regex
matching; (2) writer mingled quotes from different platforms under a
single block header, so "— Reddit" ended up inside an HN block and
didn't linkify; (3) HasQuotes=no blocks had no attribution line to
linkify — entire block unclickable.

## Decision

Move CP link generation from post-processor (data→code matching) to
writer (writer emits links directly). The writer receives
`HackerNewsURL:` / `RedditURL:` fields in CP Data and produces
`**[Platform](URL)** (N↑)` block headers and
`> — [Platform](URL)` attributions inline. Post-processor becomes an
idempotent safety net.

Plan: vault/09-Implementation/plans/2026-04-24-cp-writer-url-plumbing.md

## Verification

Post-deploy, rerun-from-write on Apr 24:
- smoke_cp_citations output: [paste actual output here]
- Spot-checked one HN link resolves to the thread (not 404)
- Spot-checked one Reddit link resolves to the r/sub/comments/... page

## What's NOT fixed by this plan

- Quote-to-platform disambiguation inside a single CommunityInsight
  (a single insight with quotes from both HN + Reddit still has no
  per-quote platform tag). Writer now has an instruction to move
  cross-platform quotes to the correct block, but compliance is
  LLM-dependent. Safety net: post-processor detects the mismatch and
  leaves the attribution raw rather than incorrectly linking to the
  wrong platform's URL.
- Weekly pipeline — out of scope; different CP structure.
```

**Step 5: Commit the journal**

```bash
git add vault/12-Journal-&-Decisions/2026-04-24-cp-writer-url-plumbing.md
git commit -m "docs(journal): CP writer URL plumbing — Apr 24 evidence

Records the Apr 24 partial-linkification problem, the architectural
decision to move link generation to the writer, and the post-deploy
smoke verification output."
```

---

## Done criteria (full plan)

- [ ] `_build_cp_data_entry` extracted as a testable helper; 6 tests pass.
- [ ] CP Data includes `HackerNewsURL:` / `RedditURL:` lines when insight has them; 10 total builder tests pass.
- [ ] Writer prompt rule 9 requires `**[Platform](URL)** (N↑)` block headers + `> — [Platform](URL)` attributions; multi-platform split rule documented.
- [ ] All 4 × 2 = 8 skeleton CP sections demonstrate linked format; 12 skeleton tests pass.
- [ ] 4 QC rubric EXEMPT bullets updated to describe linked CP format as PRIMARY (not separate-exempt).
- [ ] `_inject_cp_citations` linkifies bare block headers, is idempotent on already-linked content, and preserves partial compliance; 14 total injection tests pass.
- [ ] Full `pytest backend/tests/` clean; `ruff check` clean.
- [ ] Apr 24 rerun-from-write shows `smoke_cp_citations` output with `raw=0` on all 4 digests.
- [ ] Journal note committed with evidence.

---

## Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| Writer hallucinates a URL not in CP Data (emits a wrong HN thread URL) | Low-probability — writer has explicit `HackerNewsURL:` / `RedditURL:` to copy verbatim. No observed pattern of LLM inventing HN/Reddit URLs from whole cloth. Safety net: post-processor doesn't validate writer-emitted URLs against any allowlist, so a hallucinated URL would ship — acceptable risk given the rare frequency and the clear input signal. If this becomes a problem, add a post-processor URL sanity check (strip inline CP links whose URL doesn't appear in `community_summary_map`). |
| Writer continues emitting bare text (prompt cache stale, model ignores new rule) | Post-processor safety net (Task 6) linkifies bare block headers AND attributions. Existing 9 tests guarantee the safety net still works on fully-bare output (the Apr 24 baseline). `prompt_cache_key` changes when prompt content changes, invalidating stale cache automatically. |
| Writer splits multi-platform insight incorrectly (puts Reddit quote under HN block) | Rule 9 now explicitly instructs: "Attribution URL must match block's platform — move cross-platform quotes to the correct block." Safety net: post-processor's bare-attribution linkify keys off BLOCK header URL, so a misplaced attribution stays raw (not incorrectly linked). This is a degradation, not a corruption. |
| Existing `test_cp_citation_injection.py` tests break because behavior subtly shifted | Task 6's updated `_process_section` handles bare headers by editing in place (not replacing the line), preserving upvote text and summary. The 9 existing tests assert specific output strings — review each after Task 6 implementation and update only where the new behavior is intentional. |
| Post-processor double-linkifies on rerun (regenerated body re-processed through `_inject_cp_citations`) | Task 6 explicitly tests idempotency. Already-linked header and attribution patterns are matched FIRST and passed through unchanged. |
| Old checkpoints lack `hn_url` / `reddit_url` — writer gets bare CP Data, emits bare text | Backward-compatible path: rule 9 explicitly allows `**Hacker News** (N↑)` bare fallback when URL isn't in input. Post-processor catches up when it has the insight's URL (new-format checkpoints) OR leaves raw (pre-plumbing checkpoints — safe degradation). |
| Weekly pipeline affected | Out of scope. Weekly uses `run_weekly_pipeline` with a different prompt path (`get_weekly_prompt` / `get_weekly_ko_prompt`). If the weekly CP section exists and has the same issue, file a follow-up plan. |
