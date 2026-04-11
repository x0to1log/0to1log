---
title: Handbook term disambiguation design
status: design
created: 2026-04-12
owner: Amy
related: [2026-03-16-handbook-redesign-design.md]
---

# Handbook Term Disambiguation Design

## Problem

Some handbook terms share their **surface name** with a separate,
equally-valid concept. The classic case:

| Surface name | Concept A (classical) | Concept B (product/entity) |
|---|---|---|
| **Perplexity** | Info-theory metric | Perplexity AI (search product) |
| **Mistral** | (general word) | Mistral AI (company) + Mistral-7B model family |
| **Claude** | (no classical CS term) | Anthropic's LLM assistant |
| **Gemini** | (no classical CS term) | Google's LLM family |
| **Mamba** | State space model architecture | Mamba (conda alternative package manager) |
| **LLaMA / Llama** | Meta's open model family | Animal / generic noun |
| **Transformer** | Attention-based architecture | (Electric device — out of domain, no conflict) |

The handbook pipeline (extraction → gate → generation → auto-linkify
→ popup) needs to handle these gracefully without silently collapsing
two distinct concepts into one entry or polluting the glossary with
ambiguous definitions.

## Current architecture (as of 2026-04-12)

1. **Extraction** (`prompts_advisor.py:EXTRACT_TERMS_PROMPT`):
   takes news articles, emits candidate terms with `{term, korean_name,
   category, confidence, reason}`. Outputs are filtered by category +
   a 5-point self-check.
2. **Gate** (`prompts_advisor.py:TERM_GATE_PROMPT`): receives
   candidates + the list of existing handbook term names, accepts or
   rejects each. Rejection reasons include DUPLICATE, TOO SPECIFIC,
   NOT ESTABLISHED, TOO GENERIC, OVERLAPS EXISTING.
3. **Pipeline dedup** (`services/pipeline.py:_extract_and_create_
   handbook_terms`, ~line 615): 3-layer DB dedup before insert — slug
   match, ilike term match, abbreviation match (bracket form + reverse
   initials).
4. **Generation** (`advisor.py:_run_generate_term`): called per accepted
   term, produces definition + basic body + advanced body + references.
5. **Auto-linkify** (`rehypeHandbookTerms.ts`): builds a regex from the
   `termsMap` keys sorted by length descending, wraps matches in
   `<span class="handbook-term" data-slug="...">`. Longest match wins.
6. **Popup** (`handbook-popup.ts`): reads `data-slug`, fetches the term
   data from an embedded JSON map, renders the popup.

## Gaps identified

### Gap 1 — Gate's DUPLICATE rule conflates "same surface name" with "same concept"

The old rule only cited `abbreviation ↔ full name` as an example. The
LLM could apply this liberally and reject "Perplexity AI" as a duplicate
of existing "Perplexity" (metric) even though they are distinct
concepts. Fixed 2026-04-12 by adding an explicit **"Name overlap"**
acceptance note in `TERM_GATE_PROMPT` that distinguishes surface-name
collision from concept identity.

### Gap 2 — Extraction produced bare names for products that collide

When a news article said "Perplexity raised $500M", the extractor would
output `term: "Perplexity"`. The downstream pipeline then slug-collided
with the existing metric entry and silently dropped the candidate.
Fixed 2026-04-12 by adding a **name-clash rule** to `EXTRACT_TERMS_
PROMPT` requiring products/companies that share a name with a classical
concept to be extracted in their fully-qualified form
(`"Perplexity AI"`, `"Mistral AI"`, etc.) or dropped to low-confidence
review if the full form cannot be determined.

### Gap 3 — Pipeline dedup had a latent indentation bug

`_extract_and_create_handbook_terms`'s reverse-abbreviation check had
its `continue` statement at the wrong indentation level: any term with
≥3 capitalized-initial words (e.g., "Large Language Model",
"Convolutional Neural Network") was unconditionally skipped regardless
of whether a matching abbreviation existed in DB. Fixed 2026-04-12 by
moving `continue` inside the `if exists_by_initials.data:` block.

### Gap 4 — No `aliases` field in `handbook_terms`

The auto-linkify `termsMap` is currently built from `{term, korean_name}`.
If a single concept has multiple surface forms (plurals, hyphenation
variants, abbreviation + full name, Korean + English), they all need
entries in the map. There is no per-term alias list in the schema —
every alias requires a separate handbook_terms row (wasteful) or a
manual map build step (fragile).

**Decision**: defer. Add `aliases: text[]` column only when:
- We observe ≥3 real concept collisions in production, OR
- A common term has ≥3 surface variants that need to link to the same
  entry (e.g., "RAG" / "Retrieval-Augmented Generation" / "검색 증강 생성"
  all needing to auto-link to the same slug).

The fix is small (Supabase migration + map-build adjustment + admin UI
field), but the problem must be real, not hypothetical.

### Gap 5 — News context can't disambiguate bare mentions

When a news article writes "Perplexity" bare (no "AI" suffix) meaning
the company, auto-linkify currently links to whichever entry holds the
`"perplexity"` key in the termsMap. Case-insensitive matching means
`"Perplexity"` and `"perplexity"` cannot be differentiated at the regex
level.

**Convention in place of code**: the news pipeline prompt should require
authors (the LLM writing the digest) to use the fully-qualified form
when the referent is the product — "Perplexity AI" always, never bare
"Perplexity" for the company. Bare "perplexity" in news prose is
reserved for the metric. This is a **style rule**, not a runtime check.

TODO: add this convention to `prompts_news_pipeline.py` as an explicit
rule when the two-slug Perplexity case actually ships.

## Implemented fixes (2026-04-12)

- `EXTRACT_TERMS_PROMPT`: new "Name-clash rule" section with BAD/GOOD
  examples for Perplexity / Mistral / Claude / Mamba.
- `TERM_GATE_PROMPT`: clarified DUPLICATE rule + new "Name overlap"
  acceptance section with ACCEPT and REJECT examples.
- `services/pipeline.py`: fixed reverse-abbreviation `continue`
  indentation.

## Deferred — implement when real cases accumulate

1. **`aliases` field on handbook_terms**: adds a first-class place to
   record surface-form variants that should auto-link to a single slug.
   Triggered by: observing the first concrete same-concept-multiple-
   surfaces case that the current single-term-name field can't handle.
2. **Disambiguation clause in generation prompt**: when generating a
   term that has a known name-clash peer (e.g., generating `perplexity`
   and `perplexity-ai` both exist), the prompt should require a 1-
   sentence "Not to be confused with X" clause in the definition.
3. **News pipeline style rule**: explicit "use full product name when
   the bare name would collide with a classical term" rule in the news
   digest prompt.
4. **Context-aware entity linking at news indexing**: an LLM call per
   article to resolve ambiguous name references to the correct slug.
   Expensive; deferred until convention-based approaches prove
   insufficient.

## First real test case: Perplexity pilot

Procedure to validate the gap-1 / gap-2 fixes end-to-end:

1. Add `perplexity` (metric) + `perplexity-ai` (product) to
   `c:/tmp/regen_handbook.py:TERM_META`.
2. Run regen for both terms.
3. Verify:
   - Both rows exist in `handbook_terms` with distinct slugs.
   - Each definition mentions the other (disambiguation clause).
   - `handbookTermsJson` includes both slugs with distinct term names.
   - A synthetic news article containing "Perplexity AI launched a
     feature" auto-links to `perplexity-ai`.
   - A synthetic news article containing "perplexity score dropped to
     3.2" auto-links to `perplexity`.
4. Document what works and what doesn't in a follow-up journal entry.

If the pilot reveals that the disambiguation clause isn't being
generated consistently, that's a signal to add deferred fix #2 (clause
requirement in the generation prompt).
