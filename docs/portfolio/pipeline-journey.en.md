# AI News Pipeline Development Journey

> **Project:** [0to1log](https://0to1log.com) — AI News Curation + AI Glossary + IT Blog Platform
> **Duration:** Mid-February to March 30, 2026 (2 weeks planning + 26 days development)
> **Role:** Solo full-stack developer (planning, design, frontend, backend, AI, infrastructure)
> **Stack:** Astro v5 · FastAPI · Supabase · OpenAI (gpt-4.1) · Tavily · HN/Reddit APIs · Vercel · Railway

---

## At a Glance

A pipeline that collects 50–60 AI news articles daily from 6 sources, auto-classifies, ranks, enriches with multi-source context, and summarizes them into 2 digests (Research + Business) with Expert/Learner personas. Built over 26 days through 9 versions.

| | Start (v2) | v8 | Current (v9) |
|---|---|---|---|
| **Cost per run** | $0.18 | $0.25 | $0.42–0.77 |
| **Citations per digest** | 1.8 | 16.8 | 16.8 |
| **Sources per article** | 1 (original only) | 1 | up to 5 (Exa find_similar) |
| **Writer input tokens** | 14K | 57K | 132–318K |
| **News items covered** | 1.3 | 5.0 | 5.0 |
| **Collection sources** | 1 (Tavily) | 6 | 6 |
| **Quality score (Research)** | 75.8 | 91.8 | 91.8 |
| **Quality score (Business)** | 82.9 | 94.8 | 94.8 |

Through v8, quality improved 9.3x while keeping cost at $0.25/run. v9 introduced multi-source synthesis, raising cost to $0.42–0.77 because the Writer now processes full text from up to 5 sources per article — single-perspective summaries and multi-source synthesis produce fundamentally different quality. All figures measured from production databases.

Key discoveries:
1. Removing negative instructions ("don't do X") from LLM prompts improves output. Cutting the Research Expert Guide from 569 to 151 words and deleting all 9 DON'Ts increased per-item depth from 1 paragraph to 3.
2. Prompt examples determine LLM behavior. An empty-bracket citation format `[](URL)` in the prompt caused 3 of 4 personas to omit citations entirely.

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

0to1log is an automated AI/IT news curation platform that collects, classifies, and summarizes the latest developments every day. It automatically extracts AI terms from news articles to build a glossary, and delivers content through two personas — Expert and Learner — tailored to different reader levels.

See actual daily digests at [0to1log.com](https://0to1log.com).

### Why I Built This

AI news floods in daily, but quality Korean-language technical briefings are scarce. News outlets often republish press releases verbatim or list headlines without technical context. I wanted to build a platform that automatically delivers two things: "a technical brief that a research engineer would read on their commute" and "an explanation accessible to someone new to AI."

### Current Pipeline Architecture

```
+-----------------------------------------------------------------------+
| Collect — 6 sources in parallel                                        |
| Tavily | HuggingFace | arXiv | GitHub | Google RSS | Exa             |
+-----------------------------------------------------------------------+
    | 50-60 candidates/day
    v
Dedup + Filter (URL dedup, published exclusion 3d, filler)
    v
Classify (gpt-4.1-mini) --> Research 0-5 / Business 0-5
    v
Community (HN Algolia + Reddit JSON, 38 subreddits)
    v
Rank (gpt-4.1-mini) --> [LEAD] / [SUPPORTING]
    v
Enrich (Exa find_similar, up to 4 additional sources per article)
    v
+-- Research Digest -----------+   +-- Business Digest -----------+
|  Expert EN+KO (gpt-4.1)     |   |  Expert EN+KO (gpt-4.1)     |
|  Learner EN+KO (gpt-4.1)    |   |  Learner EN+KO (gpt-4.1)    |
+------------------------------+   +------------------------------+
    v
Post-process (bold fix + tag strip + citation renumber)
    v
Quality Check (o4-mini x 4: R/B x Expert/Learner)
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
| v2–v4 | 13 | **$0.18** | $0.13–$0.21 | Single source, 4000 char limit |
| v5–v6 | 10 | **$0.20** | $0.11–$0.28 | 4 sources + skeleton maps |
| v7–v8 | 4 | **$0.25** | $0.20–$0.27 | Ranking separation + DON'T removal |
| v9 | 3 | **$0.55** | $0.42–$0.77 | Multi-source enrichment (Writer 5.6x) |

### Quality Trend (news_posts, EN, Research/Business split)

| Metric | | v2–v4 | v5–v6 | v7–v8 | v9 |
|--------|---|-------|-------|-------|-----|
| **Quality score** | Research | 75.8 | 92.2 | **91.8** | 91.8 |
| | Business | 82.9 | 94.1 | **94.8** | 94.8 |
| **Expert citations** | Research | 1.8 | 12.9 | **16.8** | 16.8 |
| | Business | 2.7 | 13.9 | **14.2** | 14.2 |
| **News items covered** | Research | 1.3 | 4.6 | **5.0** | 5.0 |
| | Business | 2.7 | 3.6 | **4.5** | 4.5 |
| **Avg cost/run** | All | $0.18 | $0.20 | $0.25 | **$0.55** |

*Quality scores are automated LLM evaluation (100-point scale). From v5 onward, evaluation switched to 4 persona-specific prompts — a stricter standard — yet scores improved.*

**Summary:** Through v8, cost stayed at $0.18–$0.25 while citations grew 9.3x and coverage 3.8x. v9 added $0.30/run (about $9/month) to introduce multi-source synthesis — the Writer now processes full text from up to 5 sources per article, producing fundamentally different depth than single-perspective summaries.

### Prompt Iteration History (9 rounds)

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
| v9 | **90.0** | Multi-source + citation code | Examples determine behavior |

---

## 3. Key Decisions and Lessons

### Decisions

**3-Tier Model Structure**

| Tier | Model | Usage | Price (input/output per 1M) |
|------|-------|-------|---------------------------|
| Main | gpt-4.1 | Digest generation, handbook content | $2.00 / $8.00 |
| Light | gpt-4.1-mini | Classification, SEO, review, quality eval | $0.40 / $1.60 |
| Reasoning | o4-mini | News ranking, fact-checking | $1.10 / $4.40 |

**Alternatives considered:** gpt-4o (existing, familiar), Claude 3.5 Sonnet (strong instruction following), gpt-4.1-mini (cheaper). A/B tested gpt-4o vs gpt-4.1 — same prompts, same failure patterns, but gpt-4.1 scored 6% higher on IFEval and cost 20% less on input tokens. Claude was not tested due to SDK switching cost and existing PydanticAI + OpenAI integration.

**Draft-First Principle**

> "Never stop the pipeline for content quality. Only retry for infrastructure errors."

If quality is below threshold, save as draft and let admin review. The pipeline itself never stops. This was the biggest architectural shift from v1 to v2.

**0-to-5 Rule**

If no news qualifies for Research, **allow an empty list**. The "select 3–5" forced quota degraded quality by pushing subpar articles into the digest.

**What I Chose NOT to Do**

| Considered | Decision | Reason |
|-----------|----------|--------|
| Use gpt-4.1-mini for classification | Rejected | $0.03/day savings but classification quality risk |
| Remove quality checks | Rejected | $0.004/day savings but prerequisite for auto-publish |
| Remove handbook self-critique | Rejected | $0.02/term savings but needed to guarantee quality floor |

### Lessons

**When quality thresholds go down, the architecture is wrong.** In v1, quality bar went from 5,000 chars to 3,500 to 2,500. That was the signal to stop patching and redesign. v2's architecture change made v1's 400 lines of defensive code unnecessary.

**Removing DON'Ts makes LLMs perform better.** Deleting all 9 DON'Ts from the Research Expert Guide improved per-item depth from 1 paragraph to 3. Business Expert Guide was already scoring 90 with 201 words and zero DON'Ts — applying the same pattern confirmed it.

**Skeletons beat rules when they conflict.** Even with "minimum 3 paragraphs" stated in 6 places, if the skeleton shows `[2-3 paragraphs]`, the LLM picks 2. Rules, skeletons, and quality checks must be consistent.

**Prompt changes must be verified one at a time.** In v7, stacking 3 changes in one commit crashed the score from 86.5 to 66.5. "Rollback + selective re-apply" is safer than "patch the patches."

**Prompt examples are not neutral.** An empty-bracket `[](URL)` in the prompt caused 3 of 4 personas to omit citations entirely. `[1](URL)` fixed it immediately. LLMs follow example patterns literally — examples are stronger instructions than rules.

**Accept LLM limitations, compensate with code.** Handbook term linking: prompt 70%, code 100%. Citation renumbering: LLM resets per section, code handles it perfectly.

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
v9 ████                                     1 day  (multi-source enrichment)
```

| | v1 | v2 | v3 | v4 | v5 | v6 | v7 | v8 | v9 |
|---|---|---|---|---|---|---|---|---|---|
| **Period** | 3/10–14 (5d) | 3/15 (1d) | 3/16 (½d) | 3/17 (½d) | 3/18–25 (8d) | 3/26 (1d) | 3/28–29 (2d) | 3/29–30 (2d) | 3/30 (1d) |
| **Outcome** | Root cause discovery | Working | Working | Working | Stabilized | Optimized | Quality overhaul | Structural separation | Multi-source enrichment |
| **Content** | Single article deep-dive | Single article, 3 personas | Digest of 3–5 articles | Digest, 2 personas | 4 sources + quality | Skeleton maps | Layered reading + CP | Ranking + Guide refactor | Exa find_similar + citation automation |
| **Daily cost** | N/A | $0.13 | $0.17–0.21 | $0.17–0.21 | $0.20 | $0.20 | $0.25 | $0.25 | $0.42–0.77 |
| **LLM calls** | 6 | 4 | 6 | 4 | 10 | 10 | 12 | 14 | 14 |

---

### v1: Finding the Root Causes (3/10–14, 5 days)

The first five days produced no publishable output — but they identified three architectural flaws that would have been invisible without building and testing end to end. Each flaw directly informed v2's design.

**Days 1–2:** LLM couldn't reliably generate 5,000+ character articles. Added retry logic.
**Day 3:** EN→KO translation lost 30–50% of content. Lowered threshold from 5,000 to 3,500 chars.
**Day 4:** JSON parsing failures. Built artifact/resume system. pipeline.py grew from 979 to 1,346 lines — 400+ defensive.
**Day 5:** Threshold down to 2,500 chars. Stopped and deleted everything.

| Symptom | Patch applied | Root cause |
|---------|--------------|------------|
| KO too short | Lowered quality bar | Sequential translation was the problem |
| Long text fails | Retry logic | Monolithic generation was the problem |
| Mid-pipeline crash | Artifact/resume | Tight coupling was the problem |

**Cost of discovery:** $15–25 (estimated), zero publishable output. But these three root causes became v2's exact design requirements.

---

### v2: Fix the Root Cause, Code Shrinks (3/15, 1 day)

| v1 Root Cause | v2 Solution |
|---|---|
| EN→KO translation (length loss) | **Bilingual simultaneous generation** |
| Single call (unstable length) | **Fact extraction → per-persona generation** |
| Hard validation (pipeline crash) | **Draft-first** (save, let admin review) |

**Why this approach:** The alternative was improving the translation prompt. But translation inherently loses content. Generating both languages from the same FactPack eliminated the problem entirely.

**Result:** Code shrank to 1/3, working in one day. All defensive code from v1 became unnecessary.

---

### v3–v6: Stabilization and Optimization (3/16–26, 11 days)

Rapid iteration on content strategy, personas, collection, and prompt structure — all on top of v2's infrastructure. Good infrastructure makes product changes exponentially faster.

**v3 (half day):** Single article → **Daily digest** (3–5 articles). Pipeline skeleton unchanged, only prompts replaced.

**v4 (half day):** 3 personas → 2 (Expert + Learner). Intermediate overlapped 70%+ with Expert — removal beat differentiation. LLM calls 6→4, cost -33%. Parallelization: 170s → 90s (47%).

**v5 (8 days):** Research digest had zero actual papers. Root cause: Tavily-only source bias. Added HuggingFace + arXiv + GitHub (4-source parallel), classification hardening (0-to-5 rule), 52-issue prompt audit, gpt-4o → gpt-4.1 switch (IFEval +6%, cost -20%), automated quality scoring.

**v6 (1 day):** 13 rules → 4 per-persona skeletons. Showing the desired output skeleton instead of listing rules raised scores from 56 → 75 → 90. **Key discovery: LLMs follow "do it like this" far better than "follow these rules."**

---

### v7: Quality Overhaul and Rollback (3/28–29, 2 days)

Automated score 90, user-perspective score 76. Five invisible problems (redirect URLs, filler articles, Expert/Learner overlap, flat depth, no community reactions).

**Changes:** Layered Reading, Weighted Depth, real-comment Community Pulse, 4 persona-aware quality checks.

**Rollback:** 3 stacked changes → 86.5 to 66.5. Rolled back, selectively re-applied 3 proven changes → 85.3.

---

### v8: Structural Separation and DON'T Removal (3/29–30, 2 days)

Research Expert stuck at 1 paragraph/item. Three causes: coupled classification/ranking, 9 DON'Ts in 569-word guide, skeleton placeholders.

**Solutions:** `rank_classified()` for [LEAD]/[SUPPORTING] ($0.00014/run), Guide 569→151 words with 0 DON'Ts, skeleton 2nd item fully written, Exa promoted (5→6 sources), Community Pulse overhaul.

**Why remove rather than rewrite DON'Ts:** Business Expert already proved fewer words + zero DON'Ts = higher scores. Per-item depth: 1→3 paragraphs.

**Result:** All 4 personas at 90/100 — first version with equal scores across all combinations.

---

### v9: Multi-Source Enrichment and Citation Automation (3/30, 1 day)

**1. Writer saw only 1 source.** 4000-char limit meant single perspective only.
**2. Citations reset per section.** 19 source_cards but body only used [1]–[4] repeatedly.

**A. Multi-Source Enrichment** — `enrich_sources()` uses Exa `find_similar_and_contents()`, up to 4 additional sources per article, no char limit. **Why:** Writer can't know what it wasn't given — diversify sources, not instructions.

**B. Citation renumbering via code** — `_renumber_citations()` reassigns sequential numbers by URL first-appearance. source_cards extracted by code, LLM's JSON ignored.

**Cost:** $0.30/run additional investment (about $9/month) expanded sources per article from 1 to 5, shifting from single-perspective summaries to multi-source synthesis.

| Date | Version | Writer tokens | Run cost |
|------|---------|-------------|---------|
| 3/28 | v8 | 57K | $0.27 |
| 3/20 | v9 early | 153K | $0.46 |
| 3/21 | v9 | 236K | $0.62 |
| 3/22 | v9 peak | 318K | $0.77 |

---

## 5. Handbook Pipeline

The Handbook (AI glossary) auto-extracts AI terms from news articles and generates explanations at two levels: Basic (accessible to beginners) and Advanced (senior engineer reference).

**4-Call split:** Single call for 16 fields caused later fields to be shallow. Split into 4 calls with Call 2/3 in parallel.

**10 term types:** gpt-4.1-mini classifies into Algorithm/Model, Infrastructure/Tool, Business/Industry, Concept/Theory, Product/Brand, Metric/Measure, Technique/Method, Data Structure/Format, Protocol/Standard, or Architecture Pattern. Each type has a dedicated depth prompt. Cost: $0.001/term.

**Tavily + Self-Critique:** Web search for latest context → inject into all 4 calls → self-critique (score < 75 → regenerate) → quality check (4 criteria x 25 points).

**Confidence routing:** Suffix pattern matching (free) + LLM filtering ($0.01). High → auto-generate, Low → queued for human review.

```
Term input (auto-extracted from news or admin manual)
    v
+-- Tavily web search (5 results)  --+
|                                     |  parallel
+-- Type classify (gpt-4.1-mini)   --+
    v
Select type-specific depth prompt (10 types)
    v
+-----------------------------------+
| Generate (gpt-4.1 x 4-Call)       |
|   Call 1: Meta + Basic KO         |
|   Call 2: Basic EN     --+  par.  |
|   Call 3: Advanced KO  --+        |
|   Call 4: Advanced EN             |
+-----------------------------------+
    v
Self-Critique (gpt-4.1-mini, < 75 --> regenerate)
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
| AI | OpenAI (gpt-4.1 / gpt-4.1-mini / o4-mini) + Tavily + Exa | - |
| Database | Supabase (PostgreSQL + Auth + RLS) | Supabase |

---

> This document chronicles the AI pipeline development journey of 0to1log.
> 9 pipeline versions, evolving from single-source summaries to multi-source synthesis,
> and the discoveries that removing instructions improves output,
> and that a single prompt example can determine the entire output.
> As a solo project, I handled every stage from planning to deployment.
