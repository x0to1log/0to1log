# CP Citation Pattern — 2026-04-25

## Problem

Apr 24 news Community Pulse section showed broken markdown — `**[Hacker News]** (URL)` (with a space between `]**` and `(URL)`) and empty `> — ` attributions. Block headers and attributions didn't render as clickable links. The earlier 2026-04-24 plan (`cp-writer-url-plumbing.md`) tried to fix it by having the writer emit `**[Label](URL)**` directly. That failed because the LLM doesn't reliably produce mixed bold-link inline markdown.

## What we tried first — extending body's `[CITE_N]` pattern to CP (failed)

The 2026-04-24 follow-up plan (`cp-citation-pattern.md`, 8 tasks) extended the news body's proven `[CITE_N]` placeholder pattern to CP: writer prompt rule 9 told the writer to emit `[CITE_N]` at the end of CP block headers and attributions; thread URLs were added to the strict json_schema enum; `apply_citations` would substitute. Same contract as body paragraphs that work flawlessly hundreds of times per run.

Three reruns (with different prompt wordings — angle-bracket metavariables, natural-language phrasing, and post-revert) all produced the same outcome: writer emitted bare `**Label** (N↑) — summary` and `> — Label` for CP, never `[CITE_N]`. Body had 18 `[N](url)` substitutions; CP had 0. The writer non-deterministically chose between three broken/incomplete shapes across reruns: bare bold, broken bold-link split, and (rarely) the desired linked form.

## Decision — code-side linkifier post-processor

The user pointed out that asking the writer to emit different markdown shapes is the wrong layer — instead, let the writer emit whatever it naturally produces (the writer DOES reliably emit some recognizable bold-label shape) and have code post-process it into the bold-link form.

`_linkify_cp_section(body, community_summary_map) → body`:
- Locates CP section (`## Community Pulse` or `## 커뮤니티 반응`)
- Normalizes the writer's broken bold-link split shape (`**[Label]** (URL) (N↑)`) into the canonical linked form (`**[Label](URL)** (N↑)`)
- For bare bold headers (`**Label** (N↑) — summary`), looks up thread URL from `CommunityInsight.hn_url` / `reddit_url` matched by upvote count, rewrites in-place to `**[Label](url)** (N↑) — summary`
- For bare attributions (`> — Hacker News`), rewrites to `> — [Hacker News](url)` using the enclosing block's URL
- Idempotent on already-linked content
- Falls back to bare output when no matching insight exists

Implementation: `backend/services/pipeline_digest.py` — `_linkify_cp_section` (~150 LOC), called after `_clean_writer_output` in `_generate_digest`. Re-exported from `pipeline.py`.

This is essentially what the deleted `_inject_cp_citations` did before Task 6 of the prior plan deleted it. The difference now: writer output is more standardized (after rule 9 + skeleton rewrites), so the linkifier handles fewer shapes and is simpler to reason about.

## Verification

Local test with the current Apr 24 broken body + checkpoint insight map: 3/3 linked headers, 6/6 linked attributions, 0 bare attributions remaining.

Live verification skipped a fourth rerun ($0.50 + 9 min cost) — instead, applied `_linkify_cp_section` directly to the existing Apr 24 broken DB rows. All 4 posts (research/business × en/ko) now show `linked_hdrs > 0`, `bare_attrs == 0`, `broken_old_form == 0`.

## What's still NOT fixed

- **Per-quote provenance.** When an insight has both HN + Reddit quotes mixed, the writer chooses which block to place each quote under. A misattribution sends the quote to the wrong-platform block. Resulting link points to a real-but-not-the-source thread. Acceptable degradation; full fix requires `CommunityInsight.threads[]` restructure (Path Y, deferred).
- **External P1-2** (provenance collapse) and **P2 bundle** (target_date search window, summarizer JSON mode, KO quote count alignment) — separate small plan.
- **Writer output is non-deterministic across reruns.** Three different broken shapes observed. The linkifier covers the three observed shapes; future reruns might produce a 4th shape. Tomorrow's cron output should be monitored.

## Lessons

1. **Writer compliance for fancy markdown is unreliable; code post-processing is the right layer.** Mirrors the broader "LLM mixed bold-link markdown unreliable" lesson from 2026-04-24 (saved to memory).
2. **The `_inject_cp_citations` function deleted in the prior plan's Task 6 was actually doing the right thing.** The premature deletion was based on the assumption that the writer would emit `[CITE_N]` for CP — that assumption was wrong. The new linkifier resurrects the same approach with simpler regex (writer output is more standardized now).
3. **In-place DB updates can substitute for live reruns when the change is purely post-processing.** Saved $0.50 + 9 min vs triggering another rerun.

## Plan documents (archive)

- `vault/09-Implementation/plans/2026-04-24-cp-pipeline-redesign-design.md` (design)
- `vault/09-Implementation/plans/2026-04-24-cp-citation-pattern.md` (implementation plan; tasks 1-2 + 6 still valid; tasks 3-5 + 7 partially obsoleted; task 8 superseded by linkifier addition)

The linkifier addition is committed at `797741b` (normalization fix on top of `5ea7c2c`).
