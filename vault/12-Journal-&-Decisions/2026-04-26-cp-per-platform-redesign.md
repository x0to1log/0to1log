# CP Per-Platform Redesign — 2026-04-26

## Problem

Two coupled issues that were treated as separate items but turned out to share a single root cause:

1. **Per-quote provenance loss (external review P1-2)** — `summarize_community` received the concatenated HN+Reddit blob per group, output flat `quotes: list[str]` with no platform tag. Writer guessed which quote came from which platform non-deterministically. Apr 24 evidence: research-persona writer duplicated the same 2 quotes across both blocks (HN + Reddit) implying false multi-source corroboration; business-persona writer split quotes correctly. Same input, same prompt, different output.

2. **Off-topic top-voted comments (Apr 25 DeepSeek case)** — Apr 25 DeepSeek v4 thread had 1357 comments. Top voted were political flame wars (Tiananmen, Iran-Israel, Mexico cartels) because big threads attract politically charged voting. Real DeepSeek tech discussion was buried. Summarizer correctly judged top-voted as off-topic and dropped the entire CP map → no CP section in either digest.

Common root: data flowed through a layer (concatenated blob, top-voted-only collection) that erased the structure downstream needed.

## Decision

Per-platform processing throughout the pipeline:

```
Collection (top voted 30 per platform — was 5-10)
    ↓
gpt-5-nano relevance filter per platform (NEW)
    ↓
Summarizer per platform (was: mixed concat → single call)
    ↓
CommunityInsight.threads: list[ThreadInfo] (NEW shape)
    ↓
CP Data builder emits one entry per thread (NEW plural)
    ↓
Writer prompt: each block is single-platform — no "split into 2 blocks" rule
    ↓
Linkifier reads URLs from threads structure
```

Plan: `vault/09-Implementation/plans/2026-04-26-cp-per-platform-redesign.md`

## Plan Revisions Mid-Stream (R1-R5)

External review of v1 plan caught 5 design errors before execution. All addressed before/during implementation:

- **R1** — Legacy hydration over-attributed quotes to "dominant thread" (invents provenance). Conservative fix: multi-platform legacy hydration returns both threads with empty quotes; downstream renders key_point only. (Single-platform legacy keeps quotes — provenance unambiguous.)
- **R2** — v1 Task 2 (top-N expansion) had hidden behavior change if shipped alone. Merged into Task 4 (atomic with relevance filter wire-up).
- **R3** — Relevance filter fallback semantics were inverted. Fixed: API failure → fail-OPEN (top-N fallback); valid LLM `selected_indexes: []` → fail-CLOSED (return [] so summarizer's sentiment=null path drops the section honestly — Apr 25 DeepSeek case).
- **R4** — Ranking still received raw blobs containing off-topic platform sections (with their upvote counts). Added `_redact_offtopic_sections` that strips off-topic platform's text before passing to ranking.
- **R5** — Task 6 only updated `_build_cp_data_entries`; missed 3 sibling consumers (`_build_writer_url_allowlist`, `_linkify_cp_section`, `_check_digest_quality` allowlist). Bundled into one atomic task — all 4 read from `synthesized_threads()`.

Plan revisions documented in commit `1c6ddf2`.

## Verification

End-to-end local smoke test on synthetic multi-platform `CommunityInsight`:

| Stage | Result |
|---|---|
| `_build_cp_data_entries` | 2 entries (one per thread), single-platform each |
| `_build_writer_url_allowlist` | Includes both thread URLs |
| `_filter_community_map_by_summary` (both relevant) | Blob unchanged |
| `_redact_offtopic_sections` (Reddit off-topic) | HN section preserved, Reddit section + upvotes gone |
| `_linkify_cp_section` | 2 linked headers from threads structure |

Live Apr 27 cron output (next morning's automatic cron) will be the definitive test.

## Commit log

| Commit | Task |
|---|---|
| `dbd8942` | Task 1: ThreadInfo + CommunityInsight.threads + initial hydration |
| `f19ec05` | R1 fix: conservative multi-platform legacy hydration |
| `1c6ddf2` | Plan revisions R1-R5 documented |
| `c0898f6` | Task 3: filter_relevant_comments helper (R3 fail-open vs fail-closed) |
| `4fd094d` | Task 4: per-platform summarize_community + top-N expansion (absorbed Task 2 per R2) |
| `1498735` | Task 5: filter + offtopic redaction (R4) |
| `872d090` | Task 6 (bundled per R5): 4 consumers migrated to threads |
| `74545e2` | Task 7: dropped multi-platform split rule from writer prompt |

Total: 8 commits (7 task commits + 1 plan revision doc + 1 R1 follow-up).

## What's NOT addressed

- **target_date search window** (external review P2) — separate small plan. HN/Reddit/Brave search uses "now-relative" freshness instead of batch_date ±7 days. Affects backfill rerun accuracy.
- **Persona differentiation in CP** — structural limit (CP is short; per-thread sentiment is per-platform, not per-persona). Acceptable.
- **Linkifier auto-apply timing on cron** — operational concern observed Apr 24-25 where linkifier didn't auto-apply on freshly written rows; `apply_linkifier_to_db.py` script run manually. May resolve naturally with the new flow since CP data shape is more uniform.

## Backward compat

- Old `CommunityInsight` checkpoints (flat shape: `quotes`, `quotes_ko`, `source_label`, `hn_url`, `reddit_url`) hydrate via `synthesized_threads()` — single-platform legacy keeps quotes (unambiguous provenance), multi-platform legacy returns empty quotes with key_point preserved.
- Old `_build_cp_data_entry` (singular) kept as deprecated wrapper returning first entry from the plural version.
- All existing tests pass — they go through `synthesized_threads()` automatically.

## Cost impact

| Change | Per-day cost delta |
|---|---|
| Top-N expansion (5-10 → 30 raw comments collected) | $0 (collection layer; no extra API calls) |
| gpt-5-nano relevance filter (~$0.001/call × 8-12 calls/day) | +$0.008-0.012 |
| Summarizer 2x calls when both platforms exist (~3-4 multi-platform groups/day) | +$0.005 |
| **Total** | **~$0.015/day** (negligible) |
