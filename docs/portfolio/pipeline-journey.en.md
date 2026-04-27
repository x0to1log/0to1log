# AI News Pipeline Development Journey

> **Project:** [0to1log](https://0to1log.com) -- AI News Curation + AI Glossary + IT Blog Platform
> **Duration:** Mid-February to April 23, 2026 (2 weeks planning + 50 days development)
> **Role:** Solo full-stack developer (planning, design, frontend, backend, AI, infrastructure)
> **Stack:** Astro v5 - FastAPI - Supabase - OpenAI (gpt-5) - Tavily - Exa - Brave - Vercel - Railway

---

## At a Glance

A pipeline that collects 50-60 AI news articles daily from 7 sources, auto-groups same-event articles, classifies, ranks, enriches with multi-source context, and summarizes them into 2 digests (Research + Business) with Expert/Learner personas. Built over 50 days through 12 versions, with gpt-5 transition (v10), quality evaluation redesign (v11), and efficiency overhaul (v12).

| | Start (v2) | v8 | v10 | v11 | Current (v12) |
|---|---|---|---|---|---|
| **Cost per run** | $0.18 | $0.25 | $0.58 | $0.54 | **$0.41** |
| **Model** | gpt-4o | gpt-4.1 | gpt-5 | gpt-5 | gpt-5 (flex + cache) |
| **Quality eval** | none | 4x25 single score | 4x25 + code deductions | 10 sub-score + evidence | **14-15 sub-score + schema enum** |
| **URL hallucination guard** | none | prompt instruction | prompt instruction | URL liveness check | **API schema enum (100%)** |
| **Prompt cache** | -- | -- | -- | -- | **52% avg hit rate** |
| **QC rerun cost** | full $0.25 | full $0.25 | full $0.58 | QC only $0.05 (-90%) | QC only $0.02 (flex) |
| **Quality (R/B)** | 75.8 / 82.9 | 91.8 / 94.8 | 96 / 91 | 76 / 93 | **89-97 stable** |

Through v8, quality improved 9.3x while keeping cost at $0.18-$0.25/run. v9 cost exploded to $0.77 with multi-source enrichment, then merge brought it back to $0.43. v10 transitioned to gpt-5. v11 redesigned the rubric with 3-layer source gates and a QC rerun path. **v12 cut cost to $0.33-$0.41 (18-34% below baseline) while restoring citation density 3-6x** -- API schema enum blocks URL hallucination at the server level, flex tier and prompt cache cut the bill. All figures measured from production databases.

Key discoveries:
1. **Removing DON'Ts makes LLMs perform better.** Cutting the Research Expert Guide from 569 to 151 words and deleting all 9 DON'Ts increased per-item depth from 1 paragraph to 3.
2. **Give LLMs one role at a time.** Classification/ranking (v8), classify/merge (v9), Writer/Summarizer (v10) -- three rounds of validation. Accuracy improved immediately each time tasks were separated.
3. **Input quality determines output quality.** Instructing the Writer to "reflect diverse perspectives" doesn't work -- actually providing diverse sources does. Merge deduplicated input, cutting cost by 44% while maintaining quality.
4. **Reasoning models have a different parameter system.** Empty responses from gpt-5 aren't bugs -- reasoning tokens consume the output budget. reasoning_effort=low + 3x headroom solves it. **In practice 60-72% of output is reasoning tokens** -- only 30-40% is body.
5. **Good source filtering matters more than good generation prompts.** Spam, content farms, dead URLs, fork repos blocked at the enrich stage. All 13 problematic URLs from the Apr 19 incident blocked. Quality is built at the input gate, not Writer tuning.
6. **When you turn the quality knob, turn the cost knob too.** In v12, raising `reasoning_effort=low` to `high` alone added +72% ($0.50 to $0.86). Adding `flex tier (-50%)` and `prompt_cache_key (-30%)` together flipped it to -34% ($0.33). Tuning one axis blows up the cost.
7. **API schema enum beats prompts for compliance.** Prompts achieve 85-97% URL hallucination prevention; `json_schema` + `citations[].url: enum` enforced at the API level rejects hallucinated URLs server-side -> 100%. When prompts can't get there, escalate to the schema.

---

## Table of Contents

1. [Project Overview and Architecture](#1-project-overview-and-architecture)
2. [Quantitative Results](#2-quantitative-results)
3. [Key Decisions and Lessons](#3-key-decisions-and-lessons)
4. [News Pipeline Evolution](#4-news-pipeline-evolution)
5. [Handbook Pipeline](#5-handbook-pipeline)
6. [Tech Stack](#6-tech-stack)

---

## 1. Project Overview and Architecture

0to1log is an automated AI/IT news curation platform that collects, classifies, and summarizes the latest developments every day. It automatically extracts AI terms from news articles to build a glossary, and delivers content through two personas -- Expert and Learner -- tailored to different reader levels.

See actual daily digests at [0to1log.com](https://0to1log.com).

### Why I Built This

AI news floods in daily, but quality Korean-language technical briefings are scarce. News outlets often republish press releases verbatim or list headlines without technical context. I wanted to build a platform that automatically delivers two things: "a technical brief that a research engineer would read on their commute" and "an explanation accessible to someone new to AI."

### Current Pipeline Architecture

```
+-----------------------------------------------------------------------+
| Collect -- 7 sources in parallel                                       |
| Tavily | HuggingFace | arXiv | GitHub | Google RSS | Exa | Brave     |
+-----------------------------------------------------------------------+
    | 50-60 candidates/day
    v
Dedup + Filter (URL dedup, published exclusion 3d, category pages, filler)
    v
Classify (gpt-5-mini) --> Research 0-5 / Business 0-5 (individual items)
    v
Merge (gpt-5-mini) --> group same-event articles ($0.002)
    v
Community collect (HN Algolia + Brave Discussions, top 30/platform)
    v
Relevance filter (gpt-5-nano) -- 30 → 5-10 (drop off-topic flame wars)
    v
Community summarize (gpt-5-mini, per-platform) --> ThreadInfo[]
    sentiment + quotes(EN/KO) + key_point per platform
    v
Rank (gpt-5-mini) --> [LEAD] / [SUPPORTING] (per group)
    v
Conditional enrich (Exa find_similar -- only groups with 1 source)
    + source quality gate (drop spam / content farms, original repo > fork)
    v
+-- Research Digest -----------+   +-- Business Digest -----------+
|  Expert EN+KO (gpt-5 flex)  |   |  Expert EN+KO (gpt-5 flex)  |
|  Learner EN+KO (gpt-5 flex) |   |  Learner EN+KO (gpt-5 flex) |
|  + JSON schema: citations[] |   |  + JSON schema: citations[] |
|    url: enum [allowlist]    |   |    url: enum [allowlist]    |
|  + prompt_cache_key (52% ↑) |   |  + prompt_cache_key (52% ↑) |
+------------------------------+   +------------------------------+
    v
Post-process (bold fix + tag strip + [CITE_N] → [N](URL) substitution)
    v
Quality check (gpt-5 flex x 4: R/B x Expert/Learner)
    + 14-15 sub-score + evidence (LLM), total aggregated by code
    + Code deductions (CP missing -15, structural mismatch -5)
    + Health Check (0 classifications, over-grouping, collection failures)
    v
Save Draft --> Admin Review --> Publish
    |
    v (conditional)
Handbook Term Extraction
```

---

## 2. Quantitative Results

All numbers below are measured from production databases (`pipeline_logs` for costs, `news_posts` for quality metrics), not estimates.

### Cost per Run (pipeline_logs, failed runs excluded)

| Period | Runs | Avg cost/run | Range | Key change |
|--------|------|-------------|-------|-----------|
| v2-v4 | 13 | **$0.18** | $0.13-$0.21 | Single source, 4000 char limit |
| v5-v6 | 10 | **$0.20** | $0.11-$0.28 | 4 sources + skeleton maps |
| v7-v8 | 4 | **$0.25** | $0.20-$0.27 | Ranking separation + DON'T removal |
| v9 initial | 3 | **$0.62** | $0.46-$0.77 | Multi-source enrichment (input explosion) |
| v9 + merge | 4 | **$0.43** | $0.32-$0.52 | Merge deduplicates input (back to v8 level) |
| v10 (gpt-5) | 6 | **$0.58** | $0.51-$0.64 | gpt-5 transition + CP Summarizer + code deductions |
| v11 | measuring | **$0.54** | -- | Rubric v2 + source gates + rerun=quality ($0.05) |
| v12 initial (high only) | 1 | $0.86 | -- | reasoning_effort=high alone (+72%, lesson) |
| v12 (4/23 single) | 1 | $0.36 | -- | flex + cache + liveness removed (-28%) |
| v12 (4/23-27 avg) | 5 | **$0.41** | $0.36-0.47 | + CP per-platform + relevance filter (4/24-27 follow-up) |

### Quality Trend (news_posts, EN, Research/Business split)

| Metric | | v2-v4 | v5-v6 | v7-v8 | v9 | v10 | v11 | v12 |
|--------|---|-------|-------|-------|-----|-----|-----|-----|
| **Quality score** | Research | 75.8 | 92.2 | 91.8 | 94 | 96 | 76 | **90-97** |
| | Business | 82.9 | 94.1 | 94.8 | 95 | 91 | 93 | **89-95** |
| **Expert citations** | Research | 1.8 | 12.9 | 16.8 | 17.5 | 17.5 | 17.5 | **30** (peak) |
| | Business | 2.7 | 13.9 | 14.2 | 20.5 | 20.5 | 20.5 | 21 |
| **Avg cost/run** | All | $0.18 | $0.20 | $0.25 | $0.43 | $0.58 | $0.54 | **$0.41** |

*Quality scores are automated LLM evaluation (100-point scale). From v5 onward, evaluation switched to 4 persona-specific prompts -- a stricter standard -- yet scores improved. **v11 scores are not directly comparable to pre-v11 because the rubric architecture itself changed** -- the 10-sub-score + evidence redesign distributes scores differently. v12 extended v11's rubric to 14-15 sub-scores + schema enforcement, with a 3-day average of 92.7 (89-97 stable).*

**Summary:** Through v8, cost stayed at $0.18-$0.25 while citations grew 9.3x. v9 exploded to $0.77, merge brought it back to $0.43. v10 transitioned to gpt-5. v11 redesigned the rubric, added source gates, and introduced a QC rerun path. **v12 used schema enum to block URL hallucination at the API level, then flex tier + prompt cache brought cost down to $0.33 (-34%) with citation density restored 3-6x.** Quality and cost improved together.

### Prompt Iteration History (12 rounds)

| Iteration | Score | Key change | Keyword |
|-----------|-------|-----------|---------|
| v1 | **56** | 13 writing rules listed | Rules ignored |
| v2 | **48** | gpt-4o A/B test | Prompt, not model |
| v3 | **75** | 1 few-shot skeleton | Examples > rules |
| v4 | **84** | KO skeleton + structural parity | Structure over chars |
| v5 | **84** | 4 sources + quality framework | Source diversification |
| v6 | **90** | 4 per-persona skeletons | Style contamination fix |
| v7 | **85.3** | User-perspective eval + rollback | Stacked changes = regression |
| v8 | **90.0** | DON'T removal | Over-correction removed |
| v9 | **95** | Multi-source + merge + citation code | Cost explosion then recovery |
| v10 | **96** | gpt-5 transition + CP redesign + code deductions | Reasoning model migration |
| v11 | **rebaseline** | 10 sub-score + source gates + rerun=quality | LLM/code role re-separation |
| v11.1 | **95/100** | Writer-QC mirror + Phase 2a measurement | QC and Writer change in pairs |
| v12 | **89-97 stable** | Schema enum + flex + cache, liveness removed | Cost -34% + citation 3-6x recovery |

---

## 3. Key Decisions and Lessons

### Decisions

**4-Tier Model Structure (v10, post gpt-5 transition)**

| Tier | Model | Usage |
|------|-------|-------|
| Main | gpt-5 | Digest generation, Weekly Recap |
| Light | gpt-5-mini | Classification, merge, ranking, CP summary |
| Nano | gpt-5-nano | Handbook lightweight tasks |
| Reasoning | gpt-5-mini | Quality evaluation, fact-checking |

**Model transition history:** gpt-4o (v1-v4) to gpt-4.1 (v5-v9, IFEval +6%, cost -20%) to gpt-5 (v10, reasoning model transition). gpt-5 is a reasoning model with a different parameter system -- max_tokens becomes max_completion_tokens, temperature is not supported, and reasoning tokens consume the output budget causing empty responses. Solved with reasoning_effort=low + 3x headroom. Designed so changing model names in `.env` switches/rolls back without code changes.

**Draft-First Principle**

> "Never stop the pipeline for content quality. Only retry for infrastructure errors."

If quality is below threshold, save as draft and let admin review. The pipeline itself never stops. This was the biggest architectural shift from v1 to v2.

**Quality Evaluation Design -- 3 Layers**

Instead of stopping the pipeline, quality is tracked through 3 layers.

**Layer 1 -- LLM Auto-Evaluation (v12: 14-15 sub-score + evidence + schema enum)**

Started with 4 criteria x 25 points per persona, but v11 redesigned it as **10 sub-scores (each 0-10) + evidence per score**. v11.1 expanded to 14-15 by adding `claim_calibration`, `temporal_anchoring`, `internal_consistency`. LLM provides only sub-scores and evidence; **code aggregates the total**.

Each persona uses 14-15 sub-scores: shared dimensions (section_completeness, source_quality, locale_integrity, language_quality) plus persona-specific ones -- Expert gets technical/analysis depth, Learner gets accessibility, Business Expert adds claim_coverage (forbids press-release evaluative phrases in focus_items).

**Why LLM doesn't compute the total:** LLMs are strong at qualitative evaluation but weak at arithmetic. Mixing the two makes both unstable. Separation makes each more accurate. `locale_integrity` was promoted from severity marker to explicit sub-dimension in v11 -- preventing recurrence of the Apr 19 incident (KO digest with English-only quotes scoring 96).

**4 QC paths fully unified:** body / frontload / weekly / handbook all use the same rubric structure for parity.

**v12 schema enum enforcement:** Writer output is constrained by OpenAI strict `json_schema` -- `citations[].url` is an enum bounded by the fact_pack allowlist. **The API rejects bad URLs server-side**, blocking URL hallucination at the schema level (100%) instead of relying on prompts. v11's URL liveness HEAD check produced 70-85% false positives (dropping 90% of citations) and was removed -- schema enum is the more accurate solution.

**Layer 2 -- Code-Based Source Gates + Structural Verification + Deductions**

Code handles three things before and after LLM scoring.

**2a. Source quality gate (v11, collection stage):**
- **Source quality gate** -- drop spam tier / content farms (introl.com, neuraplus-ai.github.io, etc.); drop exa_enrich official_repo mismatches
- **Authority rule** -- GitHub original repo > fork/mirror (CoT + few-shot judgment)
- **URL liveness** -- HEAD request drops 404/410/DNS failures/wrong redirects

All 13 problematic URLs from the Apr 19 incident blocked. Good quality is built at the **input gate**, not Writer tuning.

**2b. Post-generation structural deductions:**

Final score = LLM aggregate score - code deductions (max -30)

CP data exists but section missing: -15, EN/KO section mismatch: -5, empty citation: -5, Supporting under 3 paragraphs: -5/item.

**2c. Health Check:** 0 classifications, merge over-grouping (5+ items), 0 community results, enrich failures. Logs warnings without blocking the pipeline.

**Layer 3 -- Human Final Judgment**

Auto-publish is intentionally not implemented. Scores and Health Check results are displayed on the admin dashboard; the final publish decision is made by a human.

**Why have LLMs evaluate LLMs:** The limitation is known -- in v7, automated score was 90 but user-perspective score was 76. But consistent daily measurement is valuable for **tracking trends**. The purpose is change detection, not absolute scoring.

The handbook pipeline follows the same philosophy: Self-Critique (score < 75 during generation triggers regeneration) + Quality Check (depth/accuracy/uniqueness/completeness, < 60 triggers warning). Both news and handbook follow the principle of "measure automatically, judge humanly."

**0-to-5 Rule**

If no news qualifies for Research, **allow an empty list**. The "select 3-5" forced quota degraded quality by pushing subpar articles into the digest.

**rerun_from=quality -- QC-only rerun path (v11)**

Re-running from Writer for every prompt iteration cost $0.54/run. By reusing Writer output from DB and only rerunning the QC, cost dropped to **$0.05/run (10x reduction).**

**Why it matters:** Prompt engineering accumulates iteration cost. Cutting iteration cost by 10x means 10x more experiments. Without a low-cost rescore path, large prompt redesigns like rubric v2 would have been economically unviable.

**Cost savings considered but not adopted (v5-v8 period):** classification model downgrade ($0.03/day savings), quality checks removal ($0.004/day), handbook Self-Critique removal ($0.02/term) -- all rejected. Protecting the quality floor mattered more than cutting cost.

### Lessons

**When quality thresholds go down, the architecture is wrong.** In v1, quality bar went from 5,000 chars to 3,500 to 2,500. That was the signal to stop patching and redesign. v2's architecture change made v1's 400 lines of defensive code unnecessary.

**Removing DON'Ts makes LLMs perform better.** Deleting all 9 DON'Ts from the Research Expert Guide improved per-item depth from 1 paragraph to 3. Business Expert Guide was already scoring 90 with 201 words and zero DON'Ts -- applying the same pattern confirmed it.

**Prompt changes must be verified one at a time.** In v7, stacking 3 changes in one commit crashed the score from 86.5 to 66.5. "Rollback + selective re-apply" is safer than "patch the patches."

**Prompt examples are not neutral.** An empty-bracket `[](URL)` in the prompt caused 3 of 4 personas to omit citations entirely. `[1](URL)` fixed it immediately. LLMs follow example patterns literally.

**Accept LLM limitations, compensate with code.** Handbook term linking: prompt 70%, code 100%. Citation renumbering: LLM resets per section, code handles it perfectly.

**Reasoning models have a different parameter system.** Empty responses from gpt-5 aren't bugs -- reasoning tokens consume the output budget. reasoning_effort=low + 3x headroom solves it. Data in system prompts gets ignored, so system=rules, user=data separation is required.

**Changing the scoring system breaks score trends.** Same content scored 85 by gpt-4.1-mini and 36 by gpt-5-mini, and v10 85 isn't directly comparable to v11 85 (rubric architecture changed). When trend tracking is the goal, recognize that scoring model or rubric structure changes create discontinuities and pair them with calibration + threshold rebaselining.

**Don't make the LLM do arithmetic.** Rubric v2 moves the 10 sub-score aggregation to code. LLMs are strong at qualitative evaluation, code is precise at arithmetic -- mixing them makes the LLM stack arithmetic on top of qualitative judgment, destabilizing both.

**Structural validation isn't reachability validation.** A URL with the right string format isn't necessarily reachable. A HEAD-request gate is needed to verify actual liveness. Many of the 13 problematic URLs from the Apr 19 incident were structurally normal.

**API schema enum beats prompts for compliance.** Prompts achieve 85-97% URL hallucination prevention; OpenAI strict `json_schema` + `citations[].url: enum` enforced at the API level rejects hallucinated URLs server-side -> 100%. When prompts can't get there, escalate to the schema -- a third layer beyond "what the LLM should do vs what code should do": "what the API should enforce."

**False positives can cost more than accuracy.** v11's URL liveness HEAD check had 70-85% false positives, dropping 90% of citations. Removing it in v12 was the fix. A validation system's **false positive rate** matters as much as its detection rate -- adding isn't always the answer.

**When you turn the quality knob, turn the cost knob too.** In v12, raising `reasoning_effort=low` to `high` alone added +72% ($0.50 to $0.86). Adding `flex tier (-50%)` and `prompt_cache_key (-30%)` together flipped it to -34% ($0.33). Quality and cost changes must be packaged in the same release -- if the intermediate state ships, the billing spike forces a rollback that drags the quality gains back too.

**Put structural enforcement in front of rubric increases.** Rubric bar was raised continuously over a month while scores stayed stable at 89-97. Reason: schema + code validation locked in the bottom line first. Reverse order (raise rubric first) produces a score roller coaster.

---

## 4. News Pipeline Evolution

### Version History at a Glance

```
v1 ████████████████████████████████████████ 5 days (root cause discovery)
v2 ████████                                 1 day  (working)
v3 ████                                     half day (working)
v4 ██                                       half day (working)
v5 ████████████████                         8 days (stabilization)
v6 ██                                       1 day  (optimization)
v7 ████████                                 2 days (quality overhaul + rollback)
v8 ████████                                 2 days (structural separation)
v9 ████                                     1 day  (multi-source + merge)
v10 ██████████████████████████               7 days (gpt-5 transition + CP redesign)
v11 ████████████████████████████████████████████████████  15 days (rubric v2 + source gates)
v11.1 ████                                                1 day (Writer-QC mirror)
v12  ████                                                 1 day (schema enum + flex + cache)
```

| | v1 | v2-v4 | v5-v6 | v7-v8 | v9 | v10 | v11 | v12 |
|---|---|---|---|---|---|---|---|---|
| **Period** | 3/10-14 | 3/15-17 | 3/18-26 | 3/28-30 | 3/30 | 3/31-4/6 | 4/7-4/22 | 4/23 |
| **Outcome** | Root cause discovery | Working → stable | Stabilized + optimized | Quality + separation | Multi-source + merge | gpt-5 + code deductions | Rubric v2 + source gates | schema enum + flex + cache |
| **Model** | gpt-4o | gpt-4o | gpt-4.1 | gpt-4.1 | gpt-4.1 | gpt-5 | gpt-5 | gpt-5 flex |
| **Cost/run** | N/A | $0.13-0.17 | $0.20 | $0.25 | $0.43 | $0.58 | $0.54 | **$0.41** |
| **Quality eval** | none | none | 4x25 | 4x25 + code deductions | 4x25 + code deductions | 4x25 + code deductions | 10 sub-score + evidence | 14-15 sub-score + schema enum |

---

### v1: Finding the Root Causes (3/10-14, 5 days)

The first five days produced no publishable output -- but they identified three architectural flaws that would have been invisible without building and testing end to end. Each flaw directly informed v2's design.

Five days of accumulated patches:

**Days 1-3:** LLM couldn't reliably generate 5,000+ character articles → retry logic. EN→KO translation lost 30-50% of content → translation prompt strengthening had no effect → quality bar lowered from 5,000 to 3,500 chars.

**Days 4-5:** Intermittent JSON parsing failures → artifact/resume system. pipeline.py grew from 979 to 1,346 lines, 400+ defensive. On day 5, after lowering the bar to 2,500 chars (50% of the original target), I stopped and deleted everything.

**Root cause:** Patches were stacking on a broken architecture. Lowering quality thresholds, adding retry logic, building resume systems -- all symptom patches. The real causes were sequential translation, monolithic generation, and hard validation.

**Cost of discovery:** $15-25 (estimated), zero publishable output. But these three root causes became v2's exact design requirements. Without this phase, v2's "build it in one day" would not have been possible.

---

### v2: Fix the Root Cause, Code Shrinks (3/15, 1 day)

Attacked v1's three root causes directly: replaced sequential translation with **bilingual simultaneous generation**, split monolithic generation into **fact extraction then per-persona generation**, and switched hard validation to **draft-first saving**.

**Why this approach:** The alternative was improving the translation prompt. But translation inherently loses content. Generating both languages from the same FactPack eliminated the problem entirely.

**Result:** Code shrank to 1/3, working in one day. All defensive code from v1 became unnecessary.

---

### v3-v6: Stabilization and Optimization (3/16-26, 11 days)

Rapid iteration on content strategy, personas, collection, and prompt structure -- all on top of v2's infrastructure. Good infrastructure makes product changes exponentially faster.

**v3 (half day):** Single article to **daily digest** (3-5 articles). Pipeline skeleton unchanged, only prompts replaced.

**v4 (half day):** 3 personas to 2 (Expert + Learner). Intermediate overlapped 70%+ with Expert -- removal beat differentiation. LLM calls 6 to 4, cost -33%. Parallelization: 170s to 90s (47%).

**v5 (8 days):** Research digest had zero actual papers. Root cause: Tavily-only source bias. Added HuggingFace + arXiv + GitHub (4-source parallel), classification hardening (0-to-5 rule), 52-issue prompt audit, gpt-4o to gpt-4.1 switch (IFEval +6%, cost -20%), automated quality scoring.

**v6 (1 day):** 13 rules to 4 per-persona skeletons. Showing the desired output skeleton instead of listing rules raised scores from 56 to 75 to 90. **Key discovery: LLMs follow "do it like this" far better than "follow these rules."**

---

### v7: Quality Overhaul and Rollback (3/28-29, 2 days)

Automated score 90, user-perspective score 76. Five invisible problems (redirect URLs, filler articles, Expert/Learner overlap, flat depth, no community reactions).

**Changes:** Layered Reading, Weighted Depth, real-comment Community Pulse, 4 persona-aware quality checks.

**Rollback:** 3 stacked changes caused score to drop from 86.5 to 66.5. Rolled back, selectively re-applied 3 proven changes. Recovered to 85.3.

---

### v8: Structural Separation and DON'T Removal (3/29-30, 2 days)

Research Expert stuck at 1 paragraph/item. Three causes: coupled classification/ranking, 9 DON'Ts in 569-word guide, skeleton placeholders.

**Solutions:** `rank_classified()` for [LEAD]/[SUPPORTING] ($0.00014/run), Guide 569 to 151 words with 0 DON'Ts, skeleton 2nd item fully written, Exa promoted (5 to 6 sources), Community Pulse overhaul.

**Why remove rather than rewrite DON'Ts:** Business Expert already proved fewer words + zero DON'Ts = higher scores. Per-item depth: 1 to 3 paragraphs.

**Result:** All 4 personas at 90/100 -- first version with equal scores across all combinations.

---

### v9: Multi-Source Enrichment, Cost Explosion, and Recovery (3/30-31, 2 days)

**Phase 1 -- Multi-source introduction and cost explosion**

v8 backfill testing revealed two structural problems: Writer saw only 1 source (`raw_content[:4000]`), and citation numbers reset per section.

**Solutions:** Exa `find_similar` for up to 4 additional sources per article, and citation renumbering moved to code post-processing. **Why:** Writer cannot know what it wasn't given -- diversifying sources themselves is the root-cause fix.

**Problem:** Cost exploded from $0.25 to $0.77. 5 items x 4 sources x full text = Writer input went from 57K to 318K tokens.

**Phase 2 -- Recovery via merge**

Same-event articles were classified as separate items. This duplication was the root cause of input explosion.

**Solution:** Added a separate merge step after classify to group same-event articles. Merged groups already have multiple sources, so Exa calls are skipped (conditional enrich).

**merge v1 failure then v2:** Initially tried classify and merge in one call -- LLM grouped all articles with the same subcategory. Same lesson as v8 -- **combining two tasks in one call reduces accuracy for both.** Separating classify and merge solved it. Additional cost: $0.002.

**Result:**

| Stage | Writer tokens | Run cost |
|-------|-------------|---------|
| v8 (single source) | 57K | $0.27 |
| v9 enrich only | 318K | $0.77 (3x explosion) |
| **v9 + merge (4 runs avg)** | **73-203K** | **$0.43** (back to v8 level) |

Merge deduplicated input, reducing cost by 44% ($0.77 to $0.43 avg) while maintaining multi-source quality.

---

### v10: gpt-5 Transition and Code-Based Quality Management (3/31-4/6, 7 days)

**gpt-5 Migration**

gpt-5 is a reasoning model where existing parameters don't work -- `max_tokens` becomes `max_completion_tokens`, `temperature` is not supported, reasoning tokens consume output tokens causing empty responses. Learned from previous all-at-once failures and validated step by step:

1. `_apply_gpt5_compat()` function handles parameter compatibility in one place (28 call sites)
2. `reasoning_effort: "low"` + `max_completion_tokens` 3x headroom solves empty responses
3. Data in system prompts gets ignored by gpt-5 -- separated to system=rules, user=data

**Community Pulse Pipeline Redesign**

Separated the Summarizer stage from Writer. Third application of "role separation" after classification/ranking (v8) and classify/merge (v9).

**Why:** Asking the Writer to do "comment selection + summarization + formatting + KO translation" all at once meant one of the four always failed. Summarizer handles selection + summarization + KO translation, Writer just formats the refined data. Replaced Reddit keyword search with Brave Discussions, and improved HN search accuracy with Entity-First Search.

**Code-Based Quality Management**

Introduced a system combining LLM scoring (subjective quality) with code deductions (structural rule violations). Final score = LLM score - code deductions (max -30). CP missing, empty sections, EN/KO mismatch detected with 100% accuracy by code.

**Quality trend:**

| Stage | Research | Business | Notes |
|-------|----------|----------|-------|
| v10 initial (gpt-5) | 61 | 59 | Scoring model calibration absent |
| v10 stabilized | 89 | 87 | Calibration + 0 structural deductions |
| v10 final (4/6) | **96** | **91** | [BODY] marker + event dedup scoring |

---

### v11: Rubric Redesign and Source Quality Gates (4/7-4/21, 15 days)

Started with the Apr 19 incident. KO Research digest scored **96** automatically but actually had only English quotes in Community Pulse. The single-total rubric was hiding the locale problem -- a high score concealing content defects.

**1. Rubric v2 -- 10 sub-score + evidence + code aggregate**

Old 4x25 single score → 10 sub-scores each 0-10 + evidence per score. LLM no longer computes the total; **code aggregates**. `locale_integrity` promoted from severity marker to explicit sub-dimension.

**Why:** LLMs are strong at qualitative evaluation but weak at arithmetic. Mixing makes the LLM pile arithmetic on top of qualitative judgment, destabilizing both. Separating roles makes each more accurate. body/frontload/weekly/handbook 4 QC paths unified to the same rubric for parity.

**2. 3-Layer Source Quality Gates**

The Apr 19 incident's root cause was low-quality sources reaching the Writer. Three gates added between collection and Writer.

**A. Source quality gate** -- drop spam tier, content farms (introl.com, neuraplus-ai.github.io, etc.). Drop exa_enrich official_repo mismatches.

**B. Authority rule** -- GitHub original repo > fork/mirror. Previously LLM treated forks as originals. CoT + few-shot improved authority judgment.

**C. URL liveness gate** -- HEAD requests drop 404/410/DNS failures/wrong redirects. Correct string format and actual reachability are different validations.

All 13 problematic URLs from the Apr 19 incident blocked.

**3. Pipeline Hardening (Phase 1-3)**

3-day large refactor:
- `pipeline.py` **3,794 → 2,149 lines (-43%)**. 4-file split + shim re-export keeps 20+ import sites unbroken
- Paid API queries **24 → 11 (-46%)**. Brave entirely removed, Exa 12→5, Tavily 2 duplicates removed
- SEO-spam domains **47% → 0%**
- QUALITY_CHECK shared block shortened → **-1,956 tokens** (156% of target)

**4. `rerun_from=quality` -- Prompt experiment cost innovation**

Added a path that reruns only QC. $0.54 → $0.05 (10x reduction). Reuses Writer output from DB and only reruns quality evaluation. The precondition that made large redesigns like rubric v2 economically possible.

**5. CP Thread URL preservation -- structural-key matching** -- HN `story_id`/Reddit `permalink` embedded at collection time, matched by upvote count. Positional matching breaks when LLM rearranges, so structural keys are required.

**v11 quality:** Research 76 / Business 93 (v11 rubric). **v10 85 and v11 85 are not directly comparable** -- changing rubric architecture breaks score continuity.

---

### v11.1: Writer-QC Mirror Sync (4/22, 1 day)

In v11, new sub-scores (`claim_calibration`, `temporal_anchoring`, `internal_consistency`) were added to QC but **the corresponding rules weren't mirrored to the Writer side**, causing inconsistency. Apr 21 actual incident: Business digest translated `$8.3 billion` as `8.3억 달러` (actually `83억 달러`, **100x mistranslation**).

**Solution:** Added `BODY_LOCALE_PARITY` block to Writer side, expanded HALLUCINATION_GUARD, added 3 FINAL CHECKLIST items. Established the principle that QC and Writer rules **change in pairs in the same commit**.

**NQ-40 Phase 2a -- 3 Community Pulse-specific sub-scores** (`cp_relevance`, `cp_substance`, `translation_fidelity`) added. **weight=0 for 2-week measurement only** -- observe variance and decide weights in Phase 2b (incremental introduction with hypothesis verification first).

**Result:** Apr 21 rerun -- Research 76→**95**, Business 93→**100**. Mistranslation root cause eliminated.

---

### v12: GPT-5 Efficiency Overhaul (4/23, 1 day)

By v11 the structural problems were solved, exposing the next gate: **$0.50 cost and URL hallucination**. v12 solved both at once.

**4 problems:**
1. URL hallucination -- Writer fabricated URLs like `liner.com`, `axiomlogica.com`
2. Massive citation loss -- v11's `_validate_urls_live` HEAD check had 70-85% false positives → 90% of citations dropped
3. EN/KO asymmetry -- different allowlist per locale → body mismatch
4. Inaccurate cost tracking -- DB-stored cost was standard tier rate, didn't reflect flex discount

**Solution A: Schema enum blocks URL hallucination at the API level**

New Writer output contract:
```
body: "... [CITE_1] ... [CITE_2] ..."
citations: [
  {n: 1, url: "https://...allowlist_url_1..."},
  {n: 2, url: "https://...allowlist_url_2..."}
]
```

OpenAI strict `json_schema` + `citations[].url: enum [fact_pack.source_urls]` → **API rejects URLs outside the allowlist server-side**. Prompt compliance 85-97% → **schema 100%**. `apply_citations()` post-processor substitutes placeholders with `[N](URL)`.

**Why:** Repeating "don't hallucinate URLs" in prompts can't fully prevent it. **Structurally remove** the possibility of LLM non-compliance -- make the bad response impossible at the API level.

**Solution B: Removed v11's URL liveness check**

The HEAD-request validation introduced in v11 had 70-85% false positives, dropping 90% of citations. With schema enum guaranteeing URL validity, liveness check became unnecessary → fully removed. Result: paragraph coverage 29% → **94%**, URLs 5 → 14 (2.8x), citations 5 → 16 (3.2x).

**Lesson: adding isn't always the answer.** The validation added in v11 created a bigger problem via false positives, and the fix in v12 was removal.

**Solution C: GPT-5 Flex Tier + Prompt Caching**

- `service_tier="flex"` (50% discount) + `with_flex_retry` helper (429 exponential backoff)
- `prompt_cache_key` per persona -- 3-day average **52% cache hit** (4/23: 183K of 350K input tokens cached)
- `reasoning_effort="high"` applied uniformly

**reasoning_effort A/B (4/23, high vs medium, 1 run each):** Research expert was decisive -- high `30 cites / 15 unique URLs` vs medium `17 / 9`. The multi-paper cross-reference synthesis paragraph (positioning μLM → Latent-Guided → SLM-MUX on the abstract "latency-centric vs accuracy-centric" axis) showed 2x density. Business was nearly tied at medium 96 vs high 91 -- 1-sample variance. **Mixed (research expert only high) was rejected in favor of uniform high**: code simplicity + mental model consistency + only $2/month difference.

**Solution D: Single source of truth for cost tracking**

- `extract_usage_metrics` reads `response.service_tier` automatically → flex auto-applied
- `reasoning_tokens` extraction + admin UI display

**3-stage cost progression (most important lesson):**

| Stage | Config | Daily cost | vs baseline |
|-------|--------|-----------|-------------|
| (1) Baseline | low reasoning, standard, liveness ON | $0.50 | -- |
| (2) High-only blip | high reasoning, standard, no flex | **$0.86** | **+72%** |
| (3) Final | high + flex + cache + liveness off | **$0.33** | **-34%** |

Monthly $15 → $26 (naive) → **$10** (final). $192/year saved vs naive.

**Reality of reasoning tokens (4/23 measured):** all 4 personas spent **60-72% of output as internal reasoning** (business expert 67%, learner 72%, research expert 65%, learner 60%). Only 30-40% is actual body. Reasoning tokens are billed at output rate ($8/M) -- a hidden cost structure. Exposed `completion_tokens_details.reasoning_tokens` in admin UI to ground reasoning_effort tuning decisions.

**v12 follow-up (4/24-27):** Moved Community Pulse rendering from Writer prompt to **code post-processing** (`_linkify_cp_section`, about 150 LOC). After 3 prompt reruns all failed, conceded that forcing fancy markdown on the Writer was the wrong layer. Redesigned data model from single `CommunityInsight` to per-platform `ThreadInfo[]` to preserve quote provenance -- eliminated false corroboration in the Apr 24 case where the same quote was duplicated across both HN and Reddit blocks. Added **gpt-5-nano relevance filter** to select 5-10 from top-voted 30 comments, dropping off-topic top-voted comments (the political flame war on Apr 25 DeepSeek thread). **Mirror domain blocklist 8 → 26** (based on 14-day audit). Quiz `answer: str` → `answer_index: int 0-3` contract change to enforce cross-field invariants in schema. **Average $0.41/day after follow-up changes (4/23-27)** ($0.36-0.47, 18-28% below the $0.50 baseline). All applications of the same principle -- "structural enforcement at the code/schema layer, LLM focuses on content."

---

### Rubric Evolution × Stable Scores -- A Cross-Observation

Over the past month, the QC rubric was tightened continuously (9 → 14-15 sub-scores, schema enforcement, CP-specific dimensions added), yet writer quality scores stayed stable at **89-97**. The typical pattern -- new check added → temporary drop → prompt adjustment → recovery -- did not occur.

**5 reasons:**

1. **Schema enforcement preempts structural failure** -- URL hallucination blocked at the API level results in `url_validation_failed=0`. No score loss in that rubric quadrant.

2. **Prompt strengthening internalizes writer behavior** -- Concrete examples in HALLUCINATION_GUARD (forbidden verb lists, date absolutization worked example, `$X million` conversion examples) make the writer's "attention targets" explicit, leading to automatic avoidance in self-check.

3. **`reasoning_effort=high` thoroughly executes self-check loops** -- The 11-item FINAL CHECKLIST is skimmed at low effort, actually verified at high before submission.

4. **BODY_LOCALE_PARITY + schema enum → automatic EN/KO symmetry** -- Citations are substituted from a shared `citations[]` array, so counts auto-match.

5. **Code-level validation replaces LLM-level validation** -- Code validators like `_renumber_citations` and `apply_citations` guarantee structure, freeing the LLM to spend reasoning tokens on **content quality**.

**Rubric drift problem:** Apr 21's 94 and Mar 10's 94 aren't the same 94. The bar has been raised, so **today's 94 is higher quality**. Absolute scores can't measure "the bar has been raised" -- considering rescoring the same articles with old/new rubrics to derive an offset.

---

## 5. Handbook Pipeline

The Handbook (AI glossary) auto-extracts AI terms from news articles and generates explanations at two levels: Basic (accessible to beginners) and Advanced (senior engineer reference).

### 4-Call Split

Single call for 16 fields caused later fields to be shallow. Split into 4 calls with Call 2/3 in parallel.

### 10 Term Types

gpt-5-mini classifies into Algorithm/Model, Infrastructure/Tool, Business/Industry, Concept/Theory, Product/Brand, Metric/Measure, Technique/Method, Data Structure/Format, Protocol/Standard, or Architecture Pattern. Each type has a dedicated depth prompt. Cost: $0.001/term.

### Tavily + Self-Critique

Web search for latest context then inject into all 4 calls. Self-critique: score < 75 triggers regeneration. Quality check: 4 criteria x 25 points.

### Confidence Routing

Suffix pattern matching (free) + LLM filtering ($0.01). High confidence auto-generates, low confidence queued for human review.

```
Term input (auto-extracted from news or admin manual)
    v
+-- Tavily web search (5 results)  --+
|                                     |  parallel
+-- Type classify (gpt-5-mini)     --+
    v
Select type-specific depth prompt (10 types)
    v
+-----------------------------------+
| Generate (gpt-5 x 4-Call)         |
|   Call 1: Meta + Basic KO         |
|   Call 2: Basic EN     --+  par.  |
|   Call 3: Advanced KO  --+        |
|   Call 4: Advanced EN             |
+-----------------------------------+
    v
Self-Critique (gpt-5-mini, < 75 --> regenerate)
    v
Quality Check (4 criteria x 25 pts, < 60 --> warning)
    v
Save (High confidence --> draft, Low --> queued)
```

---

## 6. Tech Stack

| Layer | Technology | Hosting |
|-------|-----------|---------|
| Frontend | Astro v5 + Tailwind CSS v4 + TypeScript | Vercel |
| Backend | FastAPI + PydanticAI | Railway |
| AI | OpenAI (gpt-5 / gpt-5-mini / gpt-5-nano) + Tavily + Exa + Brave | - |
| Database | Supabase (PostgreSQL + Auth + RLS) | Supabase |

---

> This document chronicles the AI pipeline development journey of 0to1log.
> 12 pipeline versions, model and infra transition from gpt-4o to gpt-5 flex,
> cost explosion → merge recovery → reasoning model migration → rubric redesign
> → schema enum + flex + cache, a journey of innovating quality and cost together.
> Built a quality management system spanning LLM/code/API across 3 layers
> with 14-15 sub-score rubric + 3-layer source gates + API schema enforcement.
> As a solo project, I handled every stage from planning to deployment.
