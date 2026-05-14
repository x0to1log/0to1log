# CP Thread URL Plumbing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Thread the HN/Reddit discussion URL from collection through summarization into the daily digest body, so `## Community Pulse` blockquote attributions can link to the actual forum discussion (not the arxiv/primary URL the map is currently keyed by).

**Architecture:** Embed the thread URL inside the scraped text blob as a structured header (`[Hacker News|url=https://...]`), so checkpoint format stays a plain `dict[str, str]`. A deterministic regex parser in `ranking.py` extracts the URL into new `CommunityInsight.hn_url` / `CommunityInsight.reddit_url` fields. The existing `_inject_cp_citations` post-processor is rewritten to use these fields and match blocks by upvote count (fixing the positional-cursor bug).

**Tech Stack:** Python 3.11, Pydantic v2, pytest. No new dependencies.

**Prerequisite context for implementer:**
- `news_collection.py:1335` defines `collect_community_reactions(title, url, target_date) -> str` — already scrapes HN (via Algolia) and Reddit (via JSON API + Brave Discussions fallback). It has `story_id` and `permalink` in scope but throws them away.
- `pipeline.py:1389-1400` calls it and stores results in `community_map: dict[primary_url, str]` which gets checkpointed.
- `ranking.py:413 summarize_community(community_map, groups)` reads the blobs, extracts `source_label` via deterministic regex (`_parse_source_label`), then calls LLM for sentiment/quotes and returns `dict[primary_url, CommunityInsight]`.
- `models/news_pipeline.py:52 CommunityInsight` is a Pydantic model with 5 fields today. Adding optional `hn_url` / `reddit_url` is backward-compatible for stored checkpoints (missing fields default to None).
- `pipeline_digest.py:_inject_cp_citations` (the post-processor) currently reads URL from `community_summary_map.items()` keys (arxiv URLs). This plan replaces that with per-insight thread URLs.
- Writer-generated CP body looks like:
  ```
  **Hacker News** (79↑) — sentiment summary
  > "quote"
  > — Hacker News
  ```
- `community_summary_map` dict iteration order is NOT writer block order — that was the source of the positional-matching bug in commit `6a2d7dc`. This plan matches blocks to insights by upvote count (e.g. `(79↑)` → insight whose `source_label` contains "79↑").

---

## File Structure

**Files to modify:**

| File | Responsibility | Changes |
|------|----------------|---------|
| `backend/services/news_collection.py` | Community scraping | Embed thread URL in HN + Reddit thread_block header |
| `backend/services/agents/ranking.py` | Community summarization | Replace `_parse_source_label` with `_parse_source_meta` that also extracts URLs; pass into `CommunityInsight` |
| `backend/models/news_pipeline.py` | Data model | Add `hn_url` and `reddit_url` optional fields to `CommunityInsight` |
| `backend/services/pipeline_digest.py` | Digest post-processor | Rewrite `_inject_cp_citations` to use per-insight URLs matched by upvote count |
| `backend/tests/test_cp_citation_injection.py` | Post-processor tests | Replace existing tests to use new matching logic (upvote-count-based) |
| `backend/tests/test_community_source_meta.py` | Parser tests | NEW — covers `_parse_source_meta` extraction from embedded-URL text blob |
| `backend/tests/test_news_collection_community_urls.py` | Collection tests | NEW — covers URL embedding in thread_block strings |

**Files NOT to touch:**
- `ranking.py` summarizer LLM prompt (URLs never touch the LLM — prompt unchanged)
- `models/news_pipeline.py` other classes (ClassifiedGroup, ClassificationResult, etc.)
- Any digest prompt (writer body format stays `> — Hacker News`)

---

## Task 1: Add optional URL fields to CommunityInsight

**Files:**
- Modify: `backend/models/news_pipeline.py:52-58`
- Test: `backend/tests/test_community_insight_model.py` (NEW)

**Context:** Pydantic v2, `BaseModel`. Adding optional fields with `None` defaults is backward compatible — old checkpoints deserialize fine because missing fields just fall back to None.

**Step 1: Write the failing test**

Create `backend/tests/test_community_insight_model.py`:

```python
"""CommunityInsight model — URL fields are optional and default to None."""

from models.news_pipeline import CommunityInsight


def test_community_insight_defaults_urls_to_none():
    insight = CommunityInsight(source_label="Hacker News 79↑ · 116 comments")
    assert insight.hn_url is None
    assert insight.reddit_url is None


def test_community_insight_accepts_urls():
    insight = CommunityInsight(
        source_label="Hacker News 79↑ · 116 comments",
        hn_url="https://news.ycombinator.com/item?id=12345",
        reddit_url="https://www.reddit.com/r/OpenAI/comments/abc",
    )
    assert insight.hn_url == "https://news.ycombinator.com/item?id=12345"
    assert insight.reddit_url == "https://www.reddit.com/r/OpenAI/comments/abc"


def test_community_insight_hydrates_from_checkpoint_without_urls():
    """Existing checkpoints (pre-this-feature) don't carry url fields.
    Hydration must succeed — missing fields default to None."""
    old_checkpoint_data = {
        "sentiment": "mixed",
        "quotes": ["first quote"],
        "quotes_ko": ["첫 인용"],
        "key_point": "Discussion about X",
        "source_label": "Hacker News 79↑ · 116 comments",
    }
    insight = CommunityInsight(**old_checkpoint_data)
    assert insight.hn_url is None
    assert insight.reddit_url is None
    assert insight.sentiment == "mixed"
```

**Step 2: Run test — expect FAIL**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_community_insight_model.py -v
```
Expected: FAIL on `assert insight.hn_url is None` with AttributeError (field doesn't exist yet).

**Step 3: Add the fields**

In `backend/models/news_pipeline.py`, modify `CommunityInsight`:

```python
class CommunityInsight(BaseModel):
    """Summarized community reaction for a news group."""
    sentiment: str = "neutral"  # positive / mixed / negative / neutral
    quotes: list[str] = []  # 0-2 representative quotes (English original)
    quotes_ko: list[str] = []  # 0-2 Korean translations of quotes
    key_point: str | None = None  # 1-line discussion summary (English)
    source_label: str = ""  # e.g. "Hacker News 342↑ · 89 comments"
    hn_url: str | None = None  # Hacker News thread URL (if HN discussion found)
    reddit_url: str | None = None  # Reddit thread URL (if Reddit discussion found)
```

**Step 4: Run tests — expect PASS**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_community_insight_model.py -v
```
Expected: 3 passed.

**Step 5: Commit**

```bash
git add backend/models/news_pipeline.py backend/tests/test_community_insight_model.py
git commit -m "feat(models): add optional hn_url/reddit_url to CommunityInsight

Backward-compatible — old checkpoints hydrate fine with missing fields
defaulting to None. Enables CP citation linkification in pipeline_digest
with thread URLs plumbed from news_collection."
```

---

## Task 2: Embed thread URL in HN thread_block

**Files:**
- Modify: `backend/services/news_collection.py:1425` (HN thread_block)
- Test: `backend/tests/test_news_collection_community_urls.py` (NEW)

**Context:** `news_collection.py:1404` has `story_id = best_hit.get("objectID", "")`. HN thread URL format is `https://news.ycombinator.com/item?id={story_id}`. We need to embed it in the `thread_block` header so downstream parsers can recover it deterministically.

**Step 1: Write the failing test**

Create `backend/tests/test_news_collection_community_urls.py`:

```python
"""news_collection community thread_block — embeds HN/Reddit thread URLs
in the header line so ranking._parse_source_meta can recover them."""

import re


def test_hn_thread_block_embeds_thread_url():
    from services.news_collection import _format_hn_thread_block

    block = _format_hn_thread_block(
        story_id="12345",
        hn_title="Language Model Contains Personality Subnetworks",
        points=58,
        num_comments=34,
        comments_text=['"first comment"', '"second comment"'],
    )
    # Header line includes structured URL token
    assert block.startswith(
        "[Hacker News|url=https://news.ycombinator.com/item?id=12345] "
        "Language Model Contains Personality Subnetworks | 58 points | 34 comments"
    )
    # Comments preserved
    assert "first comment" in block


def test_hn_thread_block_with_no_story_id_omits_url_token():
    """Defensive: if story_id is missing we keep the old header format so
    downstream parsing doesn't break on empty ids."""
    from services.news_collection import _format_hn_thread_block

    block = _format_hn_thread_block(
        story_id="",
        hn_title="Title",
        points=5,
        num_comments=0,
        comments_text=[],
    )
    assert block.startswith("[Hacker News] Title | 5 points | 0 comments")
    assert "url=" not in block.split("\n")[0]
```

**Step 2: Run test — expect FAIL**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_news_collection_community_urls.py::test_hn_thread_block_embeds_thread_url -v
```
Expected: FAIL with `ImportError: cannot import name '_format_hn_thread_block'`.

**Step 3: Extract thread_block builder + embed URL**

In `backend/services/news_collection.py`, add near the top of the community-reaction section (before `collect_community_reactions`):

```python
def _format_hn_thread_block(
    story_id: str,
    hn_title: str,
    points: int,
    num_comments: int,
    comments_text: list[str],
) -> str:
    """Build the HN thread_block string with embedded thread URL.

    URL token format: [Hacker News|url=https://...]
    When story_id is empty we omit the url= token so downstream regexes
    cleanly see a plain `[Hacker News]` header.
    """
    if story_id:
        header = (
            f"[Hacker News|url=https://news.ycombinator.com/item?id={story_id}] "
            f"{hn_title} | {points} points | {num_comments} comments\n"
        )
    else:
        header = f"[Hacker News] {hn_title} | {points} points | {num_comments} comments\n"
    block = header
    if comments_text:
        block += "Top comments:\n"
        block += "\n".join(f'> "{ct}"' for ct in comments_text)
    return block
```

Then replace the existing inline construction around `news_collection.py:1425-1429`:

```python
# BEFORE (lines ~1425-1429):
thread_block = f"[Hacker News] {hn_title} | {points} points | {num_comments} comments\n"
if comments_text:
    thread_block += "Top comments:\n"
    thread_block += "\n".join(f'> "{ct}"' for ct in comments_text)
parts.append(thread_block)

# AFTER:
thread_block = _format_hn_thread_block(story_id, hn_title, points, num_comments, comments_text)
parts.append(thread_block)
```

**Step 4: Run tests — expect PASS**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_news_collection_community_urls.py -v
```
Expected: 2 passed.

**Step 5: Commit**

```bash
git add backend/services/news_collection.py backend/tests/test_news_collection_community_urls.py
git commit -m "feat(news-collection): embed HN thread URL in thread_block header

Extracts _format_hn_thread_block helper and embeds story_id-derived
thread URL as [Hacker News|url=...]. Downstream ranking._parse_source_meta
will recover this URL so CP attributions can linkify to the actual
discussion instead of the primary article URL."
```

---

## Task 3: Embed thread URL in Reddit thread_block

**Files:**
- Modify: `backend/services/news_collection.py:1559-1563` (Reddit thread_block)
- Test: extend `backend/tests/test_news_collection_community_urls.py`

**Context:** `news_collection.py:1532` has `permalink = best_thread.get("permalink", "")` (from Reddit API). Reddit thread URL is `https://www.reddit.com{permalink}` (permalink already starts with `/r/...`).

**Step 1: Write the failing test**

Append to `backend/tests/test_news_collection_community_urls.py`:

```python
def test_reddit_thread_block_embeds_thread_url():
    from services.news_collection import _format_reddit_thread_block

    block = _format_reddit_thread_block(
        permalink="/r/OpenAI/comments/abc123/new_gpt_release/",
        rd_title="New GPT release",
        subreddit="OpenAI",
        score=500,
        num_comments=120,
        comments_text=['"hot take"'],
    )
    assert block.startswith(
        "[Reddit r/OpenAI|url=https://www.reddit.com/r/OpenAI/comments/abc123/new_gpt_release/] "
        "New GPT release | 500 upvotes | 120 comments"
    )
    assert "hot take" in block


def test_reddit_thread_block_with_no_permalink_omits_url_token():
    from services.news_collection import _format_reddit_thread_block

    block = _format_reddit_thread_block(
        permalink="",
        rd_title="Title",
        subreddit="AI",
        score=10,
        num_comments=0,
        comments_text=[],
    )
    assert block.startswith("[Reddit r/AI] Title | 10 upvotes | 0 comments")
    assert "url=" not in block.split("\n")[0]
```

**Step 2: Run — expect FAIL**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_news_collection_community_urls.py::test_reddit_thread_block_embeds_thread_url -v
```
Expected: FAIL with ImportError.

**Step 3: Add helper + update call site**

In `backend/services/news_collection.py`, add next to `_format_hn_thread_block`:

```python
def _format_reddit_thread_block(
    permalink: str,
    rd_title: str,
    subreddit: str,
    score: int,
    num_comments: int,
    comments_text: list[str],
) -> str:
    """Build the Reddit thread_block string with embedded thread URL.

    URL token format: [Reddit r/<sub>|url=https://www.reddit.com<permalink>]
    When permalink is empty we omit the url= token.
    """
    if permalink:
        header = (
            f"[Reddit r/{subreddit}|url=https://www.reddit.com{permalink}] "
            f"{rd_title} | {score} upvotes | {num_comments} comments\n"
        )
    else:
        header = f"[Reddit r/{subreddit}] {rd_title} | {score} upvotes | {num_comments} comments\n"
    block = header
    if comments_text:
        block += "Top comments:\n"
        block += "\n".join(f'> "{ct}"' for ct in comments_text)
    return block
```

Then replace the existing inline block at `news_collection.py:1559-1563`:

```python
# BEFORE:
thread_block = f"[Reddit r/{subreddit}] {rd_title} | {score} upvotes | {num_comments} comments\n"
if comments_text:
    thread_block += "Top comments:\n"
    thread_block += "\n".join(f'> "{ct}"' for ct in comments_text)
parts.append(thread_block)

# AFTER:
thread_block = _format_reddit_thread_block(
    permalink, rd_title, subreddit, score, num_comments, comments_text,
)
parts.append(thread_block)
```

**Step 4: Run — expect PASS**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_news_collection_community_urls.py -v
```
Expected: 4 passed.

**Step 5: Commit**

```bash
git add backend/services/news_collection.py backend/tests/test_news_collection_community_urls.py
git commit -m "feat(news-collection): embed Reddit thread URL in thread_block header

Mirrors the HN change (Task 2) — Reddit permalink is now plumbed into
the thread_block as [Reddit r/<sub>|url=https://www.reddit.com<permalink>],
ready for parsing in ranking._parse_source_meta."
```

---

## Task 4: Parse embedded URLs into (label, hn_url, reddit_url) tuple

**Files:**
- Modify: `backend/services/agents/ranking.py:397-410` (`_parse_source_label` → `_parse_source_meta`)
- Test: `backend/tests/test_community_source_meta.py` (NEW)

**Context:** Existing regex `_HN_HEADER_RE` matches `\[Hacker News\]`. We need to extend it to optionally capture `|url=<thread_url>` and return it alongside the label. Same for Reddit. Old blobs (no URL token) must still work — the URL captures are optional groups.

**Step 1: Write the failing test**

Create `backend/tests/test_community_source_meta.py`:

```python
"""Tests for _parse_source_meta — extracts source_label + thread URLs
from community text blobs (both new-format with url= tokens and old-format
without, for backward compatibility)."""


def test_parse_hn_only_with_url():
    from services.agents.ranking import _parse_source_meta

    raw = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=12345] "
        "Title | 79 points | 116 comments\n"
        "Top comments:\n"
        '> "first"\n'
    )
    label, hn_url, reddit_url = _parse_source_meta(raw)
    assert label == "Hacker News 79↑ · 116 comments"
    assert hn_url == "https://news.ycombinator.com/item?id=12345"
    assert reddit_url is None


def test_parse_reddit_only_with_url():
    from services.agents.ranking import _parse_source_meta

    raw = (
        "[Reddit r/OpenAI|url=https://www.reddit.com/r/OpenAI/comments/abc/t/] "
        "Title | 500 upvotes | 120 comments\n"
    )
    label, hn_url, reddit_url = _parse_source_meta(raw)
    assert label == "r/OpenAI (500↑)"
    assert hn_url is None
    assert reddit_url == "https://www.reddit.com/r/OpenAI/comments/abc/t/"


def test_parse_both_hn_and_reddit_with_urls():
    from services.agents.ranking import _parse_source_meta

    raw = (
        "[Hacker News|url=https://news.ycombinator.com/item?id=1] HNTitle | 50 points | 10 comments\n"
        "Top comments:\n> \"hn\"\n\n"
        "[Reddit r/AI|url=https://www.reddit.com/r/AI/comments/x/t/] RdTitle | 100 upvotes | 20 comments\n"
    )
    label, hn_url, reddit_url = _parse_source_meta(raw)
    assert label == "Hacker News 50↑ · 10 comments · r/AI (100↑)"
    assert hn_url == "https://news.ycombinator.com/item?id=1"
    assert reddit_url == "https://www.reddit.com/r/AI/comments/x/t/"


def test_parse_backcompat_no_url_tokens():
    """Old blobs without url= still produce the label and return None for URLs."""
    from services.agents.ranking import _parse_source_meta

    raw = "[Hacker News] Title | 79 points | 116 comments\nTop comments:\n"
    label, hn_url, reddit_url = _parse_source_meta(raw)
    assert label == "Hacker News 79↑ · 116 comments"
    assert hn_url is None
    assert reddit_url is None


def test_parse_empty_blob():
    from services.agents.ranking import _parse_source_meta

    label, hn_url, reddit_url = _parse_source_meta("")
    assert label == ""
    assert hn_url is None
    assert reddit_url is None
```

**Step 2: Run — expect FAIL**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_community_source_meta.py -v
```
Expected: FAIL with ImportError.

**Step 3: Extend regex + add `_parse_source_meta`**

In `backend/services/agents/ranking.py`, modify lines 389-410:

```python
# --- Community source header regexes ---
# The `|url=<thread_url>` token is optional for back-compat with checkpoints
# predating the URL-plumbing change. `\S+?` keeps the URL tight (no spaces).
_HN_HEADER_RE = re.compile(
    r"\[Hacker News(?:\|url=(\S+?))?\]\s*.*?\|\s*([\d,]+)\s*points?\s*\|\s*([\d,]+)\s*comments?"
)
_REDDIT_HEADER_RE = re.compile(
    r"\[Reddit\s+r/(\S+?)(?:\|url=(\S+?))?\]\s*.*?\|\s*([\d,]+)\s*upvotes?\s*\|\s*([\d,]+)\s*comments?"
)


def _parse_source_meta(raw_text: str) -> tuple[str, str | None, str | None]:
    """Extract (source_label, hn_url, reddit_url) from raw community text.

    Deterministic — no LLM. URL captures are optional (None when the blob
    predates the URL-plumbing change in news_collection).
    """
    parts: list[str] = []
    hn_url: str | None = None
    reddit_url: str | None = None

    hn = _HN_HEADER_RE.search(raw_text)
    if hn:
        hn_url = hn.group(1) or None  # group 1 is the URL (optional)
        points = hn.group(2).replace(",", "")
        comments = hn.group(3).replace(",", "")
        parts.append(f"Hacker News {points}↑ · {comments} comments")

    rd = _REDDIT_HEADER_RE.search(raw_text)
    if rd:
        sub = rd.group(1)
        reddit_url = rd.group(2) or None  # group 2 is the URL (optional)
        upvotes = rd.group(3).replace(",", "")
        parts.append(f"r/{sub} ({upvotes}↑)")

    label = " · ".join(parts) if parts else ""
    return label, hn_url, reddit_url


def _parse_source_label(raw_text: str) -> str:
    """Back-compat wrapper — returns just the label for callers not yet
    migrated to _parse_source_meta. Delete after Task 5."""
    label, _hn, _rd = _parse_source_meta(raw_text)
    return label
```

**Step 4: Run — expect PASS**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_community_source_meta.py -v
```
Expected: 5 passed.

Also verify no regression in existing callers:

```
cd backend && .venv/Scripts/python.exe -m pytest tests/ -k community -v
```
Expected: all pass (existing `_parse_source_label` callers still work via wrapper).

**Step 5: Commit**

```bash
git add backend/services/agents/ranking.py backend/tests/test_community_source_meta.py
git commit -m "feat(ranking): add _parse_source_meta for URL extraction

Extends _HN_HEADER_RE / _REDDIT_HEADER_RE with optional |url=<thread_url>
capture and exposes _parse_source_meta returning (label, hn_url, reddit_url).
Keeps _parse_source_label as a back-compat wrapper; will be removed after
summarize_community migrates in Task 5."
```

---

## Task 5: Wire hn_url/reddit_url into CommunityInsight construction

**Files:**
- Modify: `backend/services/agents/ranking.py:413-567` (`summarize_community`)

**Context:** `summarize_community` currently calls `_parse_source_label(raw)` and stores the string in `group_entries[key] = (raw, _label, group.group_title)`. We need to call `_parse_source_meta` instead, unpack 3 values, and pass `hn_url`/`reddit_url` into the `CommunityInsight` constructor at the bottom of the function.

**Step 1: Write the failing integration test**

Append to `backend/tests/test_community_source_meta.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_summarize_community_populates_urls_from_parsed_blob():
    """summarize_community must extract hn_url/reddit_url from embedded
    url= tokens in community_map blobs and populate CommunityInsight."""
    from services.agents.ranking import summarize_community
    from models.news_pipeline import ClassifiedGroup, GroupedItem

    group = ClassifiedGroup(
        group_title="Test paper",
        items=[GroupedItem(url="https://arxiv.org/abs/2604.05716", title="Test", subcategory="paper")],
        category="research",
        subcategory="paper",
        reason="test",
        primary_url="https://arxiv.org/abs/2604.05716",
    )

    community_map = {
        "https://arxiv.org/abs/2604.05716": (
            "[Hacker News|url=https://news.ycombinator.com/item?id=42] "
            "Paper Title | 79 points | 116 comments\n"
            "Top comments:\n"
            '> "interesting"\n'
        )
    }

    fake_llm_response = MagicMock()
    fake_llm_response.choices = [MagicMock()]
    fake_llm_response.choices[0].message.content = (
        '{"groups": {"group_0": {"sentiment": "mixed", "quotes": ["interesting"], '
        '"quotes_ko": ["흥미로움"], "key_point": "discussion"}}}'
    )
    fake_llm_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_llm_response)

    with patch("services.agents.ranking.get_openai_client", return_value=fake_client):
        result, _usage = await summarize_community(community_map, [group])

    insight = result["https://arxiv.org/abs/2604.05716"]
    assert insight.source_label == "Hacker News 79↑ · 116 comments"
    assert insight.hn_url == "https://news.ycombinator.com/item?id=42"
    assert insight.reddit_url is None
```

**Step 2: Run — expect FAIL**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_community_source_meta.py::test_summarize_community_populates_urls_from_parsed_blob -v
```
Expected: FAIL (CommunityInsight's hn_url stays None because summarize_community doesn't pass it yet).

**Step 3: Migrate `summarize_community` to use `_parse_source_meta`**

In `backend/services/agents/ranking.py`, change the `group_entries` build at line ~434:

```python
# BEFORE:
group_entries[key] = (raw, _parse_source_label(raw), group.group_title)

# AFTER:
label, hn_url, reddit_url = _parse_source_meta(raw)
group_entries[key] = (raw, label, group.group_title, hn_url, reddit_url)
```

Then update unpacking at line ~443:

```python
# BEFORE:
for key, (raw, _label, gtitle) in group_entries.items():

# AFTER:
for key, (raw, _label, gtitle, _hn, _rd) in group_entries.items():
```

Then at line ~486 (inside the per-group loop after LLM):

```python
# BEFORE:
_raw, source_label, _gtitle = group_entries[key]

# AFTER:
_raw, source_label, _gtitle, hn_url, reddit_url = group_entries[key]
```

Finally, the `CommunityInsight(...)` constructor at line ~555:

```python
# BEFORE:
result[primary_url] = CommunityInsight(
    sentiment=sentiment,
    quotes=quotes,
    quotes_ko=quotes_ko,
    key_point=key_point,
    source_label=source_label,
)

# AFTER:
result[primary_url] = CommunityInsight(
    sentiment=sentiment,
    quotes=quotes,
    quotes_ko=quotes_ko,
    key_point=key_point,
    source_label=source_label,
    hn_url=hn_url,
    reddit_url=reddit_url,
)
```

Then delete the temporary `_parse_source_label` back-compat wrapper at the top of the function module.

**Step 4: Run tests — expect PASS**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_community_source_meta.py -v
```
Expected: 6 passed.

Regression sweep:

```
cd backend && .venv/Scripts/python.exe -m pytest tests/ -k "community or rerun or digest" -v
```
Expected: all pass (no `_parse_source_label` caller left).

**Step 5: Commit**

```bash
git add backend/services/agents/ranking.py backend/tests/test_community_source_meta.py
git commit -m "feat(ranking): plumb hn_url/reddit_url into CommunityInsight

summarize_community now calls _parse_source_meta instead of
_parse_source_label, unpacks (label, hn_url, reddit_url), and passes
the URLs into the CommunityInsight constructor. Drops the _parse_source_label
back-compat wrapper — no remaining callers."
```

---

## Task 6: Rewrite _inject_cp_citations to use per-insight URLs

**Files:**
- Modify: `backend/services/pipeline_digest.py:55-138` (entire CP citation section)
- Modify: `backend/tests/test_cp_citation_injection.py` (replace tests)

**Context:** Current implementation matches by source_label → positional URL from dict iteration. This breaks when writer reorders blocks (observed in Apr 21 bug). New approach: each CommunityInsight now carries its OWN `hn_url` / `reddit_url`. We match body blocks to insights by **upvote count** extracted from both the block header `(79↑)` and the insight's `source_label` ("Hacker News 79↑ · 116 comments"). No more positional guessing.

**Step 1: Write the failing test**

Replace the ENTIRE content of `backend/tests/test_cp_citation_injection.py` (delete all existing tests, they match the old helper signature):

```python
"""Tests for _inject_cp_citations — post-processing that linkifies
`> — Hacker News` / `> — r/xxx` attribution lines in the Community Pulse
section using per-insight thread URLs matched by upvote count."""

from models.news_pipeline import CommunityInsight


def _make_insight(*, source_label: str, hn_url: str | None = None, reddit_url: str | None = None):
    return CommunityInsight(
        source_label=source_label,
        hn_url=hn_url,
        reddit_url=reddit_url,
    )


def test_inject_linkifies_hn_block_using_insight_hn_url():
    from services.pipeline import _inject_cp_citations

    body = """## Community Pulse

**Hacker News** (79↑) — Skeptical.

> "first"
> — Hacker News

> "second"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/ANY": _make_insight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    # Both attributions linkify to the THREAD URL (not arxiv)
    link = "> — [Hacker News](https://news.ycombinator.com/item?id=42)"
    assert out.count(link) == 2
    assert "> — Hacker News\n" not in out


def test_inject_matches_multiple_hn_blocks_by_upvote_count():
    """Regression for Apr 21 positional bug: two HN blocks at different upvote
    counts must each get their OWN thread URL, regardless of dict order."""
    from services.pipeline import _inject_cp_citations

    # Deliberately insert the 58-upvote insight FIRST in the dict —
    # writer put the 79 block first in body. Matching by upvote count should
    # still pair (79 block, insight with "Hacker News 79↑...") correctly.
    cmap = {
        "https://arxiv.org/abs/LOWER": _make_insight(
            source_label="Hacker News 58↑ · 34 comments",
            hn_url="https://news.ycombinator.com/item?id=58",
        ),
        "https://arxiv.org/abs/HIGHER": _make_insight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=79",
        ),
    }
    body = """## Community Pulse

**Hacker News** (79↑) — High-upvote discussion.

> "popular"
> — Hacker News

**Hacker News** (58↑) — Smaller discussion.

> "niche"
> — Hacker News
"""
    out = _inject_cp_citations(body, cmap)
    # 79 block → id=79 URL; 58 block → id=58 URL
    assert "> — [Hacker News](https://news.ycombinator.com/item?id=79)" in out
    assert "> — [Hacker News](https://news.ycombinator.com/item?id=58)" in out


def test_inject_linkifies_reddit_block_using_insight_reddit_url():
    from services.pipeline import _inject_cp_citations

    body = """## Community Pulse

**r/OpenAI** (500↑) — sentiment.

> "reaction"
> — r/OpenAI
"""
    cmap = {
        "https://example.com/PRIMARY": _make_insight(
            source_label="r/OpenAI (500↑)",
            reddit_url="https://www.reddit.com/r/OpenAI/comments/abc/t/",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "> — [r/OpenAI](https://www.reddit.com/r/OpenAI/comments/abc/t/)" in out


def test_inject_handles_ko_header():
    from services.pipeline import _inject_cp_citations

    body = """## 커뮤니티 반응

**Hacker News** (79↑) — 혼재된 반응.

> "간단한 질문"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/X": _make_insight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "> — [Hacker News](https://news.ycombinator.com/item?id=42)" in out


def test_inject_unmatched_upvote_count_leaves_attribution_untouched():
    """If no insight has matching upvote count, the attribution stays raw."""
    from services.pipeline import _inject_cp_citations

    body = """## Community Pulse

**Hacker News** (999↑) — orphan block.

> "quote"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/X": _make_insight(
            source_label="Hacker News 50↑ · 10 comments",
            hn_url="https://news.ycombinator.com/item?id=50",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "> — Hacker News\n" in out
    assert "[Hacker News]" not in out


def test_inject_missing_hn_url_leaves_attribution_untouched():
    """If insight matches by upvote count but has no hn_url, leave alone."""
    from services.pipeline import _inject_cp_citations

    body = """## Community Pulse

**Hacker News** (79↑) — old checkpoint.

> "quote"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/X": _make_insight(
            source_label="Hacker News 79↑ · 116 comments",
            hn_url=None,  # old checkpoint pre-URL-plumbing
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert "> — Hacker News\n" in out


def test_inject_empty_map_returns_unchanged():
    from services.pipeline import _inject_cp_citations

    body = "## Community Pulse\n\n**Hacker News** (79↑) — foo.\n\n> q\n> — Hacker News\n"
    out = _inject_cp_citations(body, {})
    assert out == body


def test_inject_no_cp_section_returns_unchanged():
    from services.pipeline import _inject_cp_citations

    body = "## Big Tech\n\nStory without CP.\n"
    cmap = {
        "https://arxiv.org/abs/X": _make_insight(
            source_label="Hacker News 79↑",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    assert out == body


def test_inject_preserves_non_cp_blockquotes():
    """Blockquotes outside the CP section (e.g., direct primary-source quotes
    in Big Tech) must not be touched even if they use `> — Label`."""
    from services.pipeline import _inject_cp_citations

    body = """## Big Tech

### OpenAI ships model

> "primary-source quote"
> — Hacker News

## Community Pulse

**Hacker News** (79↑) — community.

> "community quote"
> — Hacker News
"""
    cmap = {
        "https://arxiv.org/abs/X": _make_insight(
            source_label="Hacker News 79↑",
            hn_url="https://news.ycombinator.com/item?id=42",
        ),
    }
    out = _inject_cp_citations(body, cmap)
    # Pre-CP blockquote unchanged
    assert "> — Hacker News\n\n## Community Pulse" in out
    # CP blockquote linkified
    assert "> — [Hacker News](https://news.ycombinator.com/item?id=42)\n" in out
```

**Step 2: Run — expect FAIL on most tests (old impl doesn't read hn_url)**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_cp_citation_injection.py -v
```
Expected: most tests fail (old impl reads `.url` attribute that doesn't exist or positional-matches).

**Step 3: Rewrite `_inject_cp_citations`**

Replace the section in `backend/services/pipeline_digest.py:55-138` (keep the comment header and `_CP_HEADERS`; replace `_normalize_platform_label` and `_inject_cp_citations`):

```python
# ---------------------------------------------------------------------------
# Community Pulse citation injection
# ---------------------------------------------------------------------------

_CP_HEADERS = ("## Community Pulse", "## 커뮤니티 반응")

# Block header like `**Hacker News** (79↑)` or `**r/OpenAI** (1.2K↑)`.
# Captures the label text and the upvote count (digits only; we normalize K suffixes).
_CP_BLOCK_HEADER_RE = re.compile(
    r"^\s*(?:-\s+)?\*\*(?P<label>[^*\n]+?)\*\*\s*\(\s*(?P<upvotes>[\d,.]+)(?P<kmult>[Kk]?)\s*↑",
)

# Attribution line `> — <label>` (em-dash OR double hyphen).
_CP_ATTR_RE_TMPL = r"^> [—\-]+ {label}\s*$"

# Upvote count inside CommunityInsight.source_label, e.g. "Hacker News 79↑ · 116 comments"
# or "r/OpenAI (500↑)". Captures the digits/K preceding the ↑ arrow.
_INSIGHT_UPVOTE_RE = re.compile(r"(\d[\d,.]*)(K)?↑", re.IGNORECASE)


def _upvotes_to_int(digits: str, kmult: str) -> int:
    """'1,203' + '' → 1203;   '1.2' + 'K' → 1200."""
    try:
        base = float(digits.replace(",", ""))
    except ValueError:
        return -1
    if kmult and kmult.upper() == "K":
        base *= 1000
    return int(round(base))


def _insight_hn_upvotes(source_label: str) -> int:
    """Extract upvote count of the HN thread from an insight's source_label.
    Returns -1 if not found. Used to match body blocks to insights by count."""
    # We look at the FIRST ↑ in the label (HN comes before Reddit per _parse_source_meta).
    if "Hacker News" not in source_label:
        return -1
    m = _INSIGHT_UPVOTE_RE.search(source_label)
    if not m:
        return -1
    return _upvotes_to_int(m.group(1), m.group(2) or "")


def _insight_reddit_upvotes(source_label: str) -> int:
    """Extract upvote count of the Reddit thread from an insight's source_label.
    Returns -1 if not found."""
    # Look for upvote count AFTER "r/xxx" in the label.
    m = re.search(r"r/\S+?\s*\(\s*(\d[\d,.]*)(K)?↑", source_label, re.IGNORECASE)
    if not m:
        return -1
    return _upvotes_to_int(m.group(1), m.group(2) or "")


def _inject_cp_citations(
    content: str,
    community_summary_map: dict[str, "CommunityInsight"],
) -> str:
    """Linkify `> — <Label>` attribution lines in the Community Pulse section
    using thread URLs from each CommunityInsight (hn_url / reddit_url).

    Matching strategy — by upvote count:
      Body block header `**Hacker News** (79↑)` is paired with the insight
      whose source_label contains "79↑" and has hn_url populated. This avoids
      the positional bug (writer can reorder blocks; dict iteration order
      is independent of body order).

    Degrades safely:
      - No CP section → return content unchanged.
      - Insight has no hn_url/reddit_url (old checkpoint) → attribution stays raw.
      - Block upvote count doesn't match any insight → attribution stays raw.
      - Non-CP blockquotes → never touched (only section-scoped).
    """
    if not community_summary_map or not content:
        return content

    # Build per-platform index of (upvote_count, thread_url). First match wins
    # if two insights happen to share an upvote count (rare; HN/Reddit APIs
    # return integers in different ranges).
    hn_index: list[tuple[int, str]] = []       # (upvotes, hn_url)
    reddit_index: list[tuple[str, int, str]] = []  # (subreddit, upvotes, reddit_url)

    for insight in community_summary_map.values():
        src = getattr(insight, "source_label", "") or ""
        hn_url = getattr(insight, "hn_url", None)
        reddit_url = getattr(insight, "reddit_url", None)

        if hn_url:
            upv = _insight_hn_upvotes(src)
            if upv >= 0:
                hn_index.append((upv, hn_url))

        if reddit_url:
            m_sub = re.search(r"r/(\S+?)(?:\s|\(|$)", src)
            upv = _insight_reddit_upvotes(src)
            if m_sub and upv >= 0:
                reddit_index.append((m_sub.group(1).rstrip(")"), upv, reddit_url))

    if not hn_index and not reddit_index:
        return content

    def _lookup_url(label: str, upvotes: int) -> str | None:
        if label == "Hacker News":
            for upv, url in hn_index:
                if upv == upvotes:
                    return url
            return None
        # r/<subreddit>
        m = re.match(r"r/(\S+)", label)
        if m:
            sub = m.group(1)
            for isub, upv, url in reddit_index:
                if isub == sub and upv == upvotes:
                    return url
        return None

    def _process_section(section_body: str) -> str:
        out_lines: list[str] = []
        current_label: str | None = None
        current_url: str | None = None

        for line in section_body.split("\n"):
            hdr = _CP_BLOCK_HEADER_RE.match(line)
            if hdr:
                label = hdr.group("label").strip()
                upvotes = _upvotes_to_int(hdr.group("upvotes"), hdr.group("kmult"))
                url = _lookup_url(label, upvotes) if upvotes >= 0 else None
                if url:
                    current_label = label
                    current_url = url
                else:
                    current_label = None
                    current_url = None
            elif current_label and current_url:
                attr_pat = re.compile(
                    _CP_ATTR_RE_TMPL.format(label=re.escape(current_label))
                )
                if attr_pat.match(line):
                    line = f"> — [{current_label}]({current_url})"
            out_lines.append(line)
        return "\n".join(out_lines)

    result = content
    for header_text in _CP_HEADERS:
        section_re = re.compile(
            rf"^({re.escape(header_text)}\s*\n)(.*?)(?=^## |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        result = section_re.sub(
            lambda m: m.group(1) + _process_section(m.group(2)),
            result,
        )
    return result
```

Also remove the stale `_normalize_platform_label` function (no longer used).

**Step 4: Run tests — expect PASS**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_cp_citation_injection.py -v
```
Expected: 9 passed.

Regression sweep:

```
cd backend && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```
Expected: all pass; no test references `_normalize_platform_label`.

Ruff:

```
cd backend && .venv/Scripts/python.exe -m ruff check services/pipeline_digest.py
```
Expected: `All checks passed!`

**Step 5: Commit**

```bash
git add backend/services/pipeline_digest.py backend/tests/test_cp_citation_injection.py
git commit -m "refactor(cp-citations): match blocks to insights by upvote count

Replaces positional-cursor matching (which swapped URLs when writer
reordered blocks — Apr 21 bug) with upvote-count matching. Each
insight now carries its OWN hn_url/reddit_url (Tasks 1-5), so we pair
body block \`**Hacker News** (79↑)\` with the insight whose source_label
contains \"79↑\" and has hn_url populated. Old checkpoints lacking
hn_url degrade safely to raw attributions.

Drops the _normalize_platform_label helper (no longer needed — block
label matching is now exact by upvote count)."
```

---

## Task 7: End-to-end validation on Apr 21 data

**Files:** none modified (script-only validation)

**Context:** After all changes land, re-run the existing Apr 21 post-processor path with a REAL `CommunityInsight` reconstructed from the `community_summarize` checkpoint — verifies the entire chain (checkpoint deserialization → parse URLs → inject into body).

But: Apr 21's checkpoint was generated BEFORE this feature, so it has no embedded URLs. To truly validate, we need a fresh run (Apr 22) OR we can **synthetically rebuild the community_map** from the `community` checkpoint + retroactively embed URLs using the HN search API.

Decision: **skip retroactive validation for Apr 21** (pre-plumbing data). Mark Task 7 as "verify on next fresh run (Apr 22)" and add a smoke script.

**Step 1: Add a smoke validation script**

Create `backend/scripts/smoke_cp_citations.py`:

```python
"""Smoke test: pull the latest news-* run's checkpoints, run
_inject_cp_citations on its digest bodies, and report linkify coverage.

Usage:
    python scripts/smoke_cp_citations.py YYYY-MM-DD
"""

import os
import re
import sys

from dotenv import load_dotenv
from supabase import create_client


def main(batch_id: str) -> int:
    load_dotenv()
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY"),
    )

    import services.pipeline  # noqa: populate re-exports
    from models.news_pipeline import CommunityInsight
    from services.pipeline import _inject_cp_citations

    run = sb.table("pipeline_runs").select("id").eq("run_key", f"news-{batch_id}").single().execute().data
    if not run:
        print(f"FAIL: no pipeline_run for news-{batch_id}")
        return 1
    run_id = run["id"]

    ckpt = sb.table("pipeline_checkpoints").select("data").eq(
        "run_id", run_id
    ).eq("stage", "community_summarize").execute().data
    if not ckpt:
        print(f"FAIL: no community_summarize checkpoint for {batch_id}")
        return 1
    cmap = {url: CommunityInsight(**ins) for url, ins in (ckpt[0]["data"].get("summaries") or {}).items()}
    print(f"Loaded {len(cmap)} insights")

    # Count insights with URLs (proves the plumbing worked)
    with_hn = sum(1 for i in cmap.values() if i.hn_url)
    with_rd = sum(1 for i in cmap.values() if i.reddit_url)
    print(f"  with hn_url: {with_hn}, with reddit_url: {with_rd}")
    if with_hn == 0 and with_rd == 0:
        print("WARN: no URLs plumbed — is this a pre-plumbing run?")

    # Apply post-processor to each digest body, count linkification
    slugs = [
        f"{batch_id}-research-digest", f"{batch_id}-research-digest-ko",
        f"{batch_id}-business-digest", f"{batch_id}-business-digest-ko",
    ]
    for slug in slugs:
        row = sb.table("news_posts").select("content_expert,content_learner").eq("slug", slug).execute().data
        if not row:
            print(f"  {slug}: no row")
            continue
        body = (row[0]["content_expert"] or "") + "\n" + (row[0]["content_learner"] or "")
        linked = len(re.findall(r">\s*—\s*\[(Hacker News|Reddit|r/\S+?)\]\(http", body))
        raw = len(re.findall(r"^>\s*—\s*(Hacker News|Reddit|r/\S+?)\s*$", body, re.MULTILINE))
        print(f"  {slug}: linked={linked}, raw={raw}")

    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python scripts/smoke_cp_citations.py YYYY-MM-DD")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
```

**Step 2: Manual smoke on Apr 21 (pre-plumbing — expect 0 plumbed URLs)**

```
cd backend && .venv/Scripts/python.exe scripts/smoke_cp_citations.py 2026-04-21
```
Expected output includes:
- `Loaded 2 insights`
- `with hn_url: 0, with reddit_url: 0` (pre-plumbing — expected zero)
- `WARN: no URLs plumbed — is this a pre-plumbing run?`
- body counts: `linked=0, raw=6` (writer still emits raw attributions, post-processor has no URLs to inject)

This confirms safe degradation on old data.

**Step 3: Document Apr 22 validation steps**

Append to the plan file (below) a checklist to run the morning after Apr 22 cron fires:

```markdown
## Post-deploy validation (Apr 22+)

After the first fresh run lands on `main` + Railway deploys:

- [ ] `python scripts/smoke_cp_citations.py 2026-04-22` shows `with hn_url > 0`
- [ ] Each Research/Business digest body shows `linked > 0, raw == 0` for CP attributions
- [ ] Spot-check one `[Hacker News](https://news.ycombinator.com/...)` link actually
      resolves to the HN thread (not 404, not the arxiv paper)
- [ ] Spot-check one Reddit link resolves to the r/<subreddit>/comments/... thread
```

**Step 4: Commit the smoke script**

```bash
git add backend/scripts/smoke_cp_citations.py
git commit -m "chore(scripts): add smoke_cp_citations for post-deploy CP linkify check

Counts insights with plumbed hn_url/reddit_url and reports linkified vs
raw CP attributions per digest body. Old runs (pre-plumbing) show 0
plumbed URLs — expected; proves safe degradation. Fresh runs after
Task 2/3/5 deploy should show non-zero plumbed URLs and 0 raw attributions."
```

---

## Done criteria (full plan)

- [ ] `CommunityInsight` has optional `hn_url` and `reddit_url` fields; old checkpoints hydrate.
- [ ] `news_collection.py` embeds thread URLs in both HN and Reddit `thread_block` headers.
- [ ] `ranking._parse_source_meta` returns `(label, hn_url, reddit_url)`; old-format blobs still work.
- [ ] `summarize_community` passes both URLs into the `CommunityInsight` constructor.
- [ ] `_inject_cp_citations` matches body blocks to insights by upvote count and uses `insight.hn_url` / `insight.reddit_url`.
- [ ] `pytest tests/` clean (existing + new).
- [ ] `ruff check` clean on all modified files.
- [ ] `smoke_cp_citations.py` shows safe degradation on Apr 21 (pre-plumbing) data.
- [ ] Apr 22 fresh run verification passes (see Post-deploy checklist above).

---

## Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| `|` char inside future URLs breaks the `\S+?` URL capture | URLs from HN/Reddit APIs don't contain `\|`; regex uses non-greedy `\S+?` which stops at `]`. |
| Two HN threads share the same upvote count (rare) | First match wins; given the same count, either URL points to a discussion of the same topic — acceptable. |
| Writer changes block header format in future | `_CP_BLOCK_HEADER_RE` is tolerant of `- ` prefix and both em-dash/hyphen; any further format change would be flagged by existing snapshot tests. |
| Old checkpoint hydration fails due to Pydantic strict validation | Optional fields with `None` default — Pydantic v2 accepts missing fields gracefully. Covered by `test_community_insight_hydrates_from_checkpoint_without_urls`. |
