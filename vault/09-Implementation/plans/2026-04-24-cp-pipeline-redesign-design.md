# CP Pipeline Redesign — Design Document

**Date:** 2026-04-24
**Status:** Design approved, awaiting implementation plan

## Goal

Make Community Pulse links clickable and reliable by extending the news writer's proven `[CITE_N]` citation pattern to the CP section, eliminating the fragile bold-inline-link markdown that the writer cannot reliably produce.

## Why this design

The CP section was the only part of the daily digest that used a bespoke link mechanism: writer emits `**[Label](URL)** (N↑)` inline markdown, and a post-processor (`_inject_cp_citations`) repairs bare attributions via upvote-count matching. The body of the digest has used a simpler and proven mechanism for months — writer emits `[CITE_N]` placeholders and a `citations[]` sidecar; a strict JSON schema enum pins URL values; `apply_citations` substitutes placeholders into `[N](URL)` links after the call returns.

On 2026-04-24 the prior redesign tried to make the writer emit `**[Label](URL)** (N↑)` directly. Two reruns with different prompt wordings produced the same broken output (`**[Label]** (URL) (N↑)` with a space between `]**` and `(URL)`, rendering as plain text; attributions emitted as an empty `> — `). The failure mode is inherent to the LLM, not the prompt — LLMs do not reliably emit markdown shapes that combine bold wrapping and link syntax in a single inline element, no matter how the rule is worded or how the skeleton demonstrates it. The `[CITE_N]` pattern sidesteps this entirely: the writer emits a flat token, and the substitution is pure string replacement. Zero markdown-syntax judgment asked of the LLM.

## Existing patterns considered

| Pattern | Used where | Extends to CP? |
|---|---|---|
| `[CITE_N]` + `citations[]` sidecar + schema enum | Every body paragraph | **YES — this design** |
| `_inject_cp_citations` upvote-count matching | CP only | No — being removed |
| Bold-inline-link `**[Label](URL)**` | Attempted for CP, failed | No — not supported reliably by LLM |

The `[CITE_N]` pattern is battle-tested (hundreds of citations per run with zero compliance failures on the body), schema-enforced (URL hallucination is blocked at the API layer), and visually consistent with the rest of the digest.

## Architecture

CP uses the same writer contract as body paragraphs. Writer emits `## Community Pulse` with each block header and each blockquote attribution carrying a trailing `[CITE_N]` token. The `citations[]` sidecar carries entries whose `url` values come from the CP Data input (`HackerNewsURL: <url>` / `RedditURL: <url>`). The strict JSON schema's `citations[].url` enum is extended to include thread URLs from the insight map, so the writer cannot emit an unknown URL. After the call, `apply_citations` substitutes every `[CITE_N]` — body and CP alike — into `[N](URL)` markdown. No special CP post-processor; no inline bold-link markdown; no upvote-count matching.

Ranking changes in the same plan to use the relevance-filtered `community_summary_map` instead of raw `community_map`. This fixes the external P1-1 finding that irrelevant community threads (summarizer marked `sentiment=null`) still influenced Lead/Supporting ranking via their upvote counts.

## Data flow

1. `news_collection` scrapes HN + Reddit threads per group (unchanged)
2. `summarize_community` produces `CommunityInsight` with `hn_url` / `reddit_url` per group (unchanged)
3. `_build_cp_data_entry` emits `Platform:`, `HackerNewsURL:`, `RedditURL:`, `Sentiment:`, quotes, `Key Discussion:` (unchanged from Tasks 1-2 of the prior plan)
4. Writer receives CP Data + news body data + URL allowlist. Allowlist now includes `hn_url` / `reddit_url` values from the insight map alongside body URLs
5. Writer emits body + CP section. For CP, each block header and each attribution carries a `[CITE_N]` trailing token whose corresponding `citations[N]` entry has the thread URL
6. Strict schema rejects any response whose `citations[].url` is outside the allowlist
7. `apply_citations(body, citations)` substitutes `[CITE_N]` → `[N](URL)` uniformly
8. Final markdown: `## Community Pulse` section has numbered citations in block headers and attributions, visually consistent with body

## Example writer output (before and after substitution)

**Before substitution (writer emits):**

```markdown
## Community Pulse

**Hacker News** (1041↑) — Mixed reactions to GPT-5.5 center on guardrails and pricing. [CITE_3]

> "Laughed a little to this 'We are releasing GPT-5.5...'"
> — Hacker News [CITE_3]

**r/OpenAI** (642↑) — Pricing draws pushback from developers. [CITE_4]

> "$30 per million output? I thought we were..."
> — Reddit [CITE_4]
```

**After `apply_citations`:**

```markdown
## Community Pulse

**Hacker News** (1041↑) — Mixed reactions to GPT-5.5 center on guardrails and pricing. [3](https://news.ycombinator.com/item?id=47879092)

> "Laughed a little to this 'We are releasing GPT-5.5...'"
> — Hacker News [3](https://news.ycombinator.com/item?id=47879092)

**r/OpenAI** (642↑) — Pricing draws pushback from developers. [4](https://www.reddit.com/r/OpenAI/comments/1stqlnh/...)

> "$30 per million output? I thought we were..."
> — Reddit [4](https://www.reddit.com/r/OpenAI/comments/1stqlnh/...)
```

## Files

**Modified:**

- `backend/services/pipeline_digest.py` — extend URL allowlist with thread URLs from `community_summary_map`; remove the two `_inject_cp_citations(...)` call sites on the writer output (expert/learner); remove the function definition
- `backend/services/agents/prompts_news_pipeline.py` — rewrite rule 9 short (write `## Community Pulse`, each block header ends with `[CITE_N]`, each attribution ends with `[CITE_N]`, use `HackerNewsURL` / `RedditURL` values verbatim as the matching `citations[].url`); rewrite 8 skeleton CP sections with the new `[CITE_N]` pattern; restore QC EXEMPT wording (CP now shares `[N](url)` format with body, no special-case exemption needed)
- `backend/services/pipeline.py` — `rank_classified(..., community_map)` → `rank_classified(..., community_summary_map)` (P1-1 fix)

**Preserved from the prior plan:**

- `_build_cp_data_entry` helper (Task 1 refactor) — reused as-is
- `HackerNewsURL: <url>` / `RedditURL: <url>` lines in the CP Data input (Task 2) — reused; writer now consumes these to produce `citations[]` entries
- Existing tests for `_build_cp_data_entry` — unchanged

**Deleted:**

- `_inject_cp_citations`, `_CP_LINKED_HEADER_RE`, `_CP_LINKED_ATTR_RE`, `_CP_BLOCK_HEADER_RE`, `_CP_ATTR_RE_TMPL`, `_upvotes_to_int`, `_insight_hn_upvotes`, `_insight_reddit_upvotes`, `_CP_HEADERS` in `pipeline_digest.py`
- `backend/tests/test_cp_citation_injection.py` — entire file; no post-processor to test
- `backend/tests/test_cp_skeleton_format.py` — replaced with a simpler test asserting skeleton CP sections use `[CITE_N]` pattern, not bold-link
- `backend/scripts/smoke_cp_citations.py` — entire file; no `_inject_cp_citations` to smoke-test
- I-2 Case 1 URL validation logic (inside the above `_inject_cp_citations`) — obsolete

## Testing strategy

- Unit test: `apply_citations` on a CP-including body end-to-end. Assert that `[CITE_N]` tokens in block headers and attributions substitute correctly
- Unit test: `build_news_writer_json_schema` allowlist includes thread URLs when insights carry them
- Unit test: writer schema rejects a `citations[]` entry whose URL is outside the allowlist
- Unit test: new skeleton snapshot — every CP section example uses `[CITE_N]` tokens, contains no `**[Label](URL)**` bold-link shapes
- Integration test: ranking uses `community_summary_map`. Construct a `community_summary_map` with one insight `sentiment=null`; assert that insight's upvote count does not influence the ranking score of its group
- Smoke: Apr 24 rerun-from-write produces a CP section whose every block header ends with a `[N](URL)` citation. No empty `> — ` attributions

## Success criteria

1. Apr 24 rerun-from-write: every CP block header and every CP blockquote attribution renders as a clickable `[N](URL)` citation. No bare `> — Hacker News` attributions. No empty `> — ` lines
2. Apr 24 posts auto-publishable (score ≥ 85, `url_validation_failed=false`, no caps applied)
3. Writer prompt size shrinks (rule 9 is simpler; no bold-link templates in skeletons)
4. `pipeline_digest.py` line count decreases (post-processor gone)
5. Ranking no longer influenced by upvote counts of irrelevant community threads

## Out of scope

- **P1-2** per-quote provenance (writer decides which block a quote belongs to when a group has both HN + Reddit; a misattribution results in the quote being under the wrong platform block, linking to a real-but-wrong thread — acceptable degradation; complete fix requires `CommunityInsight.threads[]` restructure, deferred)
- **P2** bundle (CP search date window on HN/Reddit/Brave, JSON mode on summarizer, KO quote count alignment) — separate small plan
- Weekly pipeline CP handling — not touched by this plan

## Risks

| Risk | Mitigation |
|---|---|
| Writer emits `[CITE_N]` in CP but omits matching entry in `citations[]` | Same as body — `apply_citations` raises `CitationSubstitutionError` and the run fails loudly, not silently |
| Writer reuses a citation number between body and CP (e.g. body has `[CITE_3]` for article, CP also `[CITE_3]`) | Schema permits any `n` 1-50; rule 9 instructs "CP citations use unique numbers that do not conflict with body citations"; skeleton shows body 1-2 + CP 3-4 pattern |
| Writer forgets `[CITE_N]` on a CP block header | QC quality gate catches it (same traceability scoring as body paragraphs); degradation is that one block is bare, not the whole section |
| Thread URL contains characters that break the JSON enum | URLs from HN/Reddit APIs are plain alphanumeric + `/?=:&` — safe for JSON strings. Existing body URLs have same character set with no issues |
| Existing Apr 24 draft bodies (broken format) remain in DB | Rerun-from-write overwrites them with the new clean format; no manual cleanup needed |

## Decisions log

- **Path X chosen over Path Y (full `CommunityInsight.threads[]` redesign):** Path X is ~100 LOC vs ~500-800. Solves the clickability issue (user's original complaint) completely. Leaves per-quote provenance (P1-2) as known-acceptable degradation, reversible later
- **Ranking P1-1 fix bundled:** Single-line swap, CP-related category, cheaper to test together
- **No data model changes:** `CommunityInsight` stays as-is. No schema migration needed. No checkpoint back-compat concerns
- **Summarizer untouched:** Existing prompt and schema preserved. P2 JSON mode fix deferred
