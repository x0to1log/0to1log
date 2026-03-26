# Building AI News Pipelines: 5 Redesigns, 6 Prompt Iterations, and What I Learned

> **Project:** 0to1log — AI News Curation + AI Glossary + IT Blog Platform
> **Duration:** Mid-February to March 26, 2026 (2 weeks planning + 22 days development)
> **Role:** Solo full-stack developer (planning, design, frontend, backend, AI, infrastructure)
> **Stack:** Astro v5 · FastAPI · Supabase · OpenAI (gpt-4.1) · Tavily · Vercel · Railway

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [News Pipeline Evolution](#2-news-pipeline-evolution)
3. [Handbook Pipeline Evolution](#3-handbook-pipeline-evolution)
4. [Prompt Engineering: From 56 to 90 Points](#4-prompt-engineering-from-56-to-90-points)
5. [Key Technical Decisions](#5-key-technical-decisions)
6. [Quantitative Results](#6-quantitative-results)
7. [What I Learned from Failure](#7-what-i-learned-from-failure)
8. [Current Architecture](#8-current-architecture)

---

## 1. Project Overview

0to1log is an automated AI/IT news curation platform that collects, classifies, and summarizes the latest developments every day. It automatically extracts AI terms from news articles to build a glossary (Handbook), and delivers content through two personas — Expert and Learner — tailored to different reader levels.

### Why I Built This

AI news floods in daily, but quality Korean-language technical briefings are scarce. News outlets often republish press releases verbatim or list headlines without technical context. I wanted to build a platform that automatically delivers two things: "a technical brief that a research engineer would read on their commute" and "an explanation accessible to someone new to AI."

### The Project in Numbers

| Metric | Value |
|--------|-------|
| Total commits | 907 (over 22 days) |
| Avg. daily commits | 41 |
| Frontend code | 54,000 lines (Astro + TypeScript) |
| Backend code | 11,000 lines (Python) |
| AI agent code | 5,700 lines (52% of backend) |
| Tests | 64, all passing |
| Vault documents | 204 .md files |

---

## 2. News Pipeline Evolution

### Version History at a Glance

```
v1 ████████████████████████████████████████ 5 days (FAILED, deleted entirely)
v2 ████████                                 1 day  (working)
v3 ████                                     half day (working)
v4 ██                                       half day (working)
v5 ████████████████                         8 days (stabilization)
v6 ██                                       1 day  (optimization)
```

| | v1 | v2 | v3 | v4 | v5 | v6 |
|---|---|---|---|---|---|---|
| **Period** | 3/10–14 (5d) | 3/15 (1d) | 3/16 (½d) | 3/17 (½d) | 3/18–25 (8d) | 3/26 (1d) |
| **Outcome** | Failed → deleted | Working | Working | Working | Stabilized | Optimized |
| **Content** | Single article deep-dive | Single article, 3 personas | Digest of 3–5 articles | Digest, 2 personas | 4 sources + quality | Skeleton maps |
| **Code** | 3,444 lines | 1,127 lines | 1,127 lines | Refactored | Extended | Prompts only |
| **Daily cost** | N/A (broken) | $0.43 | $0.59 | $0.39 | $0.50–0.80 | $0.50–0.80 |
| **LLM calls** | 6 | 4 | 6 | 4 | 10 | 10 |
| **Dev cost** | $15–25 | $2 | $1 | $1 | $5 | $2 |

---

### v1: The "Try Harder" Trap (3/10–14, 5 days, FAILED)

The initial strategy was straightforward: pick one news article, write an in-depth analysis in English, translate to Korean, then convert into three personas (Expert/Intermediate/Beginner).

Here's what happened over five days:

**Days 1–2:** Built the basic pipeline. Discovered that LLMs couldn't reliably generate 5,000+ character articles in a single call. Added retry logic.

**Day 3:** EN→KO translation reduced content length to 50–70% of the original. Added "maintain equal length" instructions to the translation prompt — no effect. Lowered the quality threshold from 5,000 to 3,500 characters.

**Day 4:** Intermittent JSON parsing failures. Built an artifact/resume system for mid-pipeline recovery. `pipeline.py` grew from 979 lines to 1,346 lines. Over 400 lines were purely defensive code.

**Day 5:** Lowered the quality threshold to 2,500 characters — 50% of the original target. "It works, but poorly." I stopped and deleted everything.

```
pipeline.py growth:
Day 1  ████████████████████  979 lines
Day 3  ██████████████████████████  1,200 lines
Day 5  ██████████████████████████████  1,346 lines (400+ defensive)
v2     ████████████  1,127 lines (rewritten from scratch)
```

**Root cause:** I was stacking patches on a broken architecture.

| Symptom | What I did (patch) | Root cause |
|---------|-------------------|------------|
| KO translation too short | Lowered quality bar | EN→KO sequential translation was the problem |
| LLM can't generate long text | Added retry logic | Single-call full generation was the problem |
| Mid-pipeline failures | Built artifact/resume | Pipeline was too tightly coupled |

**Wasted cost:** Dozens of debugging LLM calls = $15–25. Zero usable output.

---

### v2: Fix the Root Cause, Code Shrinks (3/15, 1 day)

I attacked v1's three root causes directly.

| v1 Root Cause | v2 Solution |
|---|---|
| EN generation → KO translation (length loss) | **Bilingual simultaneous generation** (no translation step) |
| Single call for entire article (unstable length) | **Fact extraction → per-persona generation** |
| Hard validation (pipeline crashes on quality) | **Draft-first** (save, let admin review) |

The key architectural change:

```
v1: Collect → Pick 1 → Generate EN → Translate KO → 3 persona variants
v2: Collect → Pick 1 → Extract facts → Per-persona EN+KO simultaneous generation
```

The **fact extraction step** was the breakthrough. Instead of asking the LLM to "understand + write" in one call, I separated the two: first extract key facts, figures, and quotes into a structured JSON (FactPack), then have each persona write their version based on that FactPack.

**Result:** Code shrank to 1/3, and it worked in a single day. Every line of defensive code from v1 became unnecessary.

---

### v3: Good Infrastructure Makes Product Changes Fast (3/16, half day)

With v2 working reliably, the content strategy's limitations became obvious: covering only one article per day was low-value. AI news produces dozens of stories daily; picking just one meant missing everything else.

**Decision:** Single article deep-dive → **Daily digest** (curating 3–5 articles)

Because v2 had solid infrastructure, very little needed to change:
- `rank_candidates()` → `classify_candidates()` (picking 1 → categorized classification)
- Two categories: Research (papers/models/open-source) and Business (big-tech/industry/new-tools)
- Prompt rewrite (single article analysis → digest format)

Pipeline skeleton, logging, error handling, DB schema — all unchanged. **Good infrastructure accelerates product iteration.**

---

### v4: 2-Persona Transition and Parallelization (3/17, half day)

Two major changes:

**1. Three personas → Two (Expert + Learner)**

Running three personas (Expert/Intermediate/Beginner) revealed that Intermediate and Expert were too similar. From the reader's perspective, it was also hard to self-identify: "I kind of know this stuff" fits neither Expert nor Beginner.

Expert (in-depth) and Learner (accessible) — two clear axes. "Do I want depth, or do I want understanding?"

- LLM calls: 6 → 4 (2 categories × 2 personas)
- Cost: -33%
- UX: Fewer choices, more intuitive

**2. Pipeline Parallelization — 170s → 90s (47% reduction)**

All LLM calls were running sequentially. Analysis revealed three parallelization opportunities:

| Optimization | Time saved |
|-------------|-----------|
| Research + Business digests concurrently | 25s |
| Handbook Call 2 and Call 3 | 5s per term |
| 2 handbook terms simultaneously | 30s |
| **Total** | **80s (170s to 90s)** |

Same token usage, same cost — just eliminated wait time.

---

### v5: Source Diversification and Quality Framework (3/18–25, 8 days)

Through v4, the pipeline relied solely on **Tavily news search**. This created a critical bias.

**Problem discovered (3/24):** The Research digest contained zero actual research papers. Articles like "Arm AI chip announcement" and "LG Display low-power LCD" were classified as research.

**Three root causes:**
1. **Source bias** — Only Tavily (news search). No direct collection of papers, code, or models, so the candidate pool itself lacked research material
2. **Vague classification criteria** — Broad definitions like "papers: breakthrough results." No negative examples
3. **Forced quotas** — "Select 3–5 articles" rule forced subpar articles into research

**Solutions:**

**A. Four-source parallel collection**

| Source | Target | Daily candidates |
|--------|--------|-----------------|
| Tavily | General AI news | 15 |
| HuggingFace Daily Papers | Community-curated papers | 10 |
| arXiv API | Latest papers (cs.AI/cs.CL/cs.LG) | 10 |
| GitHub Trending | ML open-source repos | 10 |

Candidate pool: 30 to **45/day**. Collected via `asyncio.gather()`.

**B. Classification prompt hardening**
- Research entry criteria: must be based on technical artifacts (model weights/code/papers)
- Litmus test: "Is this article primarily about a model, code, or paper?"
- **0-to-5 rule**: empty list is allowed if nothing qualifies. No forced filling

**C. Prompt audit (52 issues)**
Full audit of all prompt files, classified into three priority levels:
- **P0 (Critical, 6):** URL hallucination prevention, citation mapping, factual error prevention
- **P1 (Important, 18):** Token efficiency, few-shot examples, score definitions
- **P2 (Nice-to-have, 28):** Code standards, structural clarity, naming

**D. Model switch: gpt-4o → gpt-4.1**
- IFEval (instruction following): 87.4% vs 81%
- Cost: input $2.00/M vs $2.50/M (20% cheaper)
- A/B test result: gpt-4.1 more consistent with identical prompts

**E. Automated quality scoring**
- 4 criteria × 25 points = 100 total
- Section Completeness, Source Citations, Technical Depth, Language Quality
- Evaluated by gpt-4.1-mini ($0.004/check)

---

### v6: Skeleton Maps — The Decisive Prompt Structure Change (3/26, 1 day)

Through v5, the prompt listed 13 writing rules. The LLM only partially followed them — especially KO content, which was consistently shorter than EN with missing sections.

**Key discovery:** Switching models (gpt-4o ↔ gpt-4.1) produced the same failure patterns. It wasn't the model — it was the prompt.

**Solution: Per-persona skeletons (complete output examples)**

Instead of listing rules, I showed the LLM the exact skeleton of the desired output. Four separate skeletons for each combination:

```
SKELETON_MAP = {
    ("research", "expert"):  RESEARCH_EXPERT_SKELETON,
    ("research", "learner"): RESEARCH_LEARNER_SKELETON,
    ("business", "expert"):  BUSINESS_EXPERT_SKELETON,
    ("business", "learner"): BUSINESS_LEARNER_SKELETON,
}
```

**Results:**

| Version | EN Biz | EN Res | KO Biz | KO Res | Avg |
|---------|--------|--------|--------|--------|-----|
| v1 (rules only) | 50 | 75 | 60 | 40 | **56** |
| v3 (1 skeleton) | 85 | 90 | 65 | 60 | **75** |
| v6 (4 skeletons) | 95 | 93 | 85 | 88 | **90** |

Automated quality scores (gpt-4.1-mini):
- **Business: 99** (Expert 100, Learner 98)
- **Research: 95** (Expert 95, Learner 95)

---

## 3. Handbook Pipeline Evolution

The Handbook (AI glossary) is tightly coupled with the news pipeline. It automatically extracts AI terms from news articles and generates explanations at two levels: Basic (accessible to beginners) and Advanced (senior engineer reference material).

### Initial → 4-Call Split (3/15–17)

**Problem:** Generating all 16 fields (KO/EN × basic/advanced × 4 sections) in a single LLM call caused later fields to be shallow or missing entirely. LLM token limits in action.

**Solution:** Split into 4 sequential calls:

```
Call 1: Metadata + Basic KO
Call 2: Basic EN        --+  parallel
Call 3: Advanced KO     --+
Call 4: Advanced EN
```

Calls 2 and 3 are independent — run in parallel. 5s saved per term.

### 10 Term Types (3/18)

**Problem:** Using the same prompt for every term meant "BERT," "Kubernetes," and "Funding Round" all got similar-depth explanations. Algorithms need formulas; infrastructure tools need architecture diagrams; business terms need case studies.

**Solution:** Classify each term into one of 10 types using gpt-4.1-mini, then apply type-specific depth prompts:

| Type | Examples | Depth comes from |
|------|----------|-----------------|
| Algorithm/Model | BERT, Transformer | Formula derivation, complexity analysis, code |
| Infrastructure/Tool | Docker, CUDA | Architecture diagrams, configs, troubleshooting |
| Business/Industry | Funding Round | Market data, decision frameworks |
| Concept/Theory | Overfitting | Mathematical intuition, trade-offs |
| Product/Brand | GPT-4, Claude | Competitive comparison, API specs, benchmarks |
| Metric/Measure | F1, BLEU | Formula derivation, selection criteria, misuse cases |
| Technique/Method | Prompt Engineering | Variant comparison, failure patterns |
| Data Structure/Format | Parquet, ONNX | Internal structure, benchmarks |
| Protocol/Standard | OAuth 2.0, gRPC | Handshake flows, security models |
| Architecture Pattern | Microservices, RAG | Trade-off analysis, migration strategies |

Classification cost: $0.001/term (single gpt-4.1-mini call).

### Tavily Integration + Self-Critique (3/18)

**Problem:** LLMs don't know information beyond their knowledge cutoff. Terms about "a new model released in March 2026" would lack the latest details.

**Solution:**
1. **Tavily search**: Fetch 5 web results for context before generation
2. **Reference injection**: Feed Tavily results as context to all 4 generation calls
3. **Self-critique**: gpt-4.1-mini evaluates "what would a senior engineer find lacking?" Score below 75 → regenerate
4. **Quality scoring**: 4 criteria (depth/accuracy/uniqueness/completeness) × 25 points

### Confidence-Based Routing (3/23–25)

Some auto-extracted terms were common nouns, not technical terms. Marketing phrases with suffixes like "-powered" and "-driven" slipped through.

**Dual defense:**
1. **Suffix pattern matching** (first pass): Hardcoded patterns for fast filtering. Zero cost
2. **LLM second-pass filtering**: gpt-4.1-mini picks "real technical terms only." $0.01

**Confidence routing:**
- High confidence → automatic generation (4-call + quality check)
- Low confidence → `status: queued` (human reviews before generation)

---

## 4. Prompt Engineering: From 56 to 90 Points

The news prompt file (`prompts_news_pipeline.py`) accumulated **50 commits**. Prompt engineering was the most iterative — and most educational — part of this project.

### Record of 6 Iterations

| Iteration | Score | Key change | Lesson |
|-----------|-------|-----------|--------|
| v1 | **56** | 13 writing rules listed | Rules alone don't make LLMs comply |
| v2 | **48** | gpt-4o rollback (A/B test) | Same failure patterns with different model → it's the prompt, not the model |
| v3 | **75** | Added 1 few-shot skeleton | LLMs follow **complete examples** far more accurately than rules |
| v4 | **84** | Added KO skeleton + structural parity | "80% of EN length" is wrong for Korean — same content is naturally shorter |
| v5 | **84** | Structural equivalence (section/item/paragraph count) | Verify by **structure** (section count, item count), not character count |
| v6 | **90** | 4 per-persona skeletons | Sharing one skeleton across 4 personas causes style contamination |

### Key Lessons

**1. "It's the prompt, not the model"**

In v2, I ran an A/B test: gpt-4o vs gpt-4.1. Both failed identically — ignored section headers, dropped citations, abbreviated KO content. Before switching models, restructure the prompt.

**2. Few-shot skeletons >> rule lists**

13 rules (v1, 56 points) vs. same rules + 1 skeleton (v3, 75 points). LLMs understand "do it like this" far better than "follow these rules."

**3. Per-persona skeletons are essential**

In v3–v5, one Business Expert skeleton was shared across all 4 combinations. Research Learner wrote like Business Expert — jargon instead of analogies, dense analysis instead of accessible explanation. After splitting skeletons, Research Learner began producing: "Instead of reading one character at a time, it processes the entire page at once — this is called parallel diffusion decoding."

**4. Korean quality requires structural parity, not character counting**

"At least 80% of EN length" is the wrong metric for Korean. Korean expresses the same content more concisely than English. Switching to "same number of ## sections, ### items, and paragraphs" equalized KO/EN coverage.

**5. Sandwich pattern: checklist at the end of the prompt**

Placing a FINAL CHECKLIST (8 verification items) at the bottom of the prompt improved compliance with citation format, section presence, and KO=EN parity. The LLM reads it just before finishing output.

**6. Code post-processing > prompt instructions**

Asking the LLM to link handbook terms in-text: 70% accuracy. Doing it in code post-processing: 100%. Knowing the boundary between "what LLMs do well" and "what code should handle" is critical.

---

## 5. Key Technical Decisions

### 3-Tier Model Structure

| Tier | Model | Usage | Price (input/output per 1M tokens) |
|------|-------|-------|-------------------------------------|
| Main | gpt-4.1 | Digest generation, handbook content | $2.00 / $8.00 |
| Light | gpt-4.1-mini | Classification, SEO, review, quality eval | $0.40 / $1.60 |
| Reasoning | o4-mini | News ranking, fact-checking | $1.10 / $4.40 |

Why gpt-4.1: IFEval (instruction following) 87.4% — 6 points higher than gpt-4o, and 20% cheaper on input tokens.

### Draft-First Principle

> "Never stop the pipeline for content quality. Only retry for infrastructure errors."

If quality is below threshold, save as draft and let admin review. The pipeline itself never stops. This was the biggest architectural shift from v1 to v2.

### The 0-to-5 Rule

If no news article qualifies for the Research category, **allow an empty list**. The "select 3–5 articles" forced quota actually degraded quality — it pushed subpar articles into the digest.

### Cost Optimization: What I Chose NOT to Do

| Considered | Decision | Reason |
|-----------|----------|--------|
| Use gpt-4.1-mini for classification | Rejected | $0.03/day savings but classification quality risk |
| Remove quality checks | Rejected | $0.004/day savings but prerequisite for auto-publish |
| Remove handbook self-critique | Rejected | $0.02/term savings but needed to guarantee quality floor |

---

## 6. Quantitative Results

### Cost Efficiency

| Version | Dev time | Dev cost (LLM) | Daily ops cost | Content output |
|---------|---------|----------------|---------------|----------------|
| v1 | 5 days | $15–25 | N/A (broken) | None |
| v2 | 1 day | $2 | $0.43 | 2 articles/day |
| v3 | half day | $1 | $0.59 | 6–10 articles/day |
| v4 | half day | $1 | $0.39 | 6–10 articles/day (2 personas) |
| v5–v6 | 9 days | $7 | $0.50–0.80 | 6–10 articles + handbook |

**v1 burned $15–25 with zero output. From v3 onward, under $1 produces 6–10 curated digest articles.** Over 10x cost efficiency improvement.

Total daily cost including handbook: **$1.00–$1.50/day**.
Monthly estimate: **$30–$45/month**.

### Quality Improvement

| Metric | Start | Current | Improvement |
|--------|-------|---------|-------------|
| Prompt quality score | 56/100 | 90/100 | +61% |
| Automated Business score | — | 99/100 | — |
| Automated Research score | — | 95/100 | — |
| Execution time | 170s | 90s | -47% |
| Collection sources | 1 | 4 | +300% |
| Daily news candidates | 30 | 45 | +50% |

### Codebase Scale

| Component | Lines |
|-----------|-------|
| Frontend (Astro + TS) | 54,000 |
| Backend (Python) | 11,000 |
| AI agent code | 5,700 (52% of backend) |
| Tests | 64, all passing |
| Design/plan documents (Vault) | 204 .md files |

---

## 7. What I Learned from Failure

### "Work differently, not harder"

In v1, I spent five days stacking patches and felt productive the entire time. The moment I started lowering quality thresholds was the moment I should have stopped. If I had abandoned v1 on day 3, I would have reached v3 two days earlier.

### Good architecture eliminates defensive code

v1's 400 lines of defensive code became entirely unnecessary in v2. When you fix the root cause, the symptom-handling code disappears.

### Fast failure = fast progress

```
v1 → v2: Architecture redesign. 5 days → 1 day.
v2 → v3: Content strategy change. Infrastructure reused.
v3 → v4: Optimization. Existing structure maintained.
```

Each iteration built on the previous foundation, making the next version exponentially faster.

### Prompt engineering is software engineering

Prompts need version control, testing, auditing, and refactoring — just like code. 50 commits on a single prompt file isn't an exaggeration; it's reality. "Write one prompt and you're done" is a myth. It requires a structured, iterative improvement process.

### Accept LLM limitations, compensate with code

- Handbook term linking: prompt accuracy 70% → code post-processing 100%
- Tag normalization: LLM mixed in Korean tags → code filters English only
- Date/format: LLM hallucinated metadata like "Vol.01 No.10" → code strips it

Developing intuition for the boundary between "what LLMs are good at" (writing, summarizing, classifying) and "what code is good at" (exact matching, format enforcement, post-processing) was one of the most valuable outcomes of this project.

---

## 8. Current Architecture

### News Pipeline Flow

```
4 sources in parallel (Tavily + HuggingFace + arXiv + GitHub)
    | 45 candidates/day
    v
URL deduplication + published URL exclusion (3-day lookback)
    |
    v
o4-mini classification --> Research / Business (0-to-5 rule)
    |
    v
Community reactions for top 3 articles (Reddit/HN via Tavily)
    |
    v
+-- Research Digest -------+   +-- Business Digest -------+
|  Expert EN+KO (gpt-4.1)  |   |  Expert EN+KO (gpt-4.1)  |  <-- parallel
|  Learner EN+KO (gpt-4.1) |   |  Learner EN+KO (gpt-4.1) |
+---------------------------+   +---------------------------+
    |
    v
Quality scoring (gpt-4.1-mini, 4 criteria x 25 points)
    |
    v
Save as draft --> Admin review --> Publish
    |
    v
Handbook term auto-extraction (conditional)
```

### Handbook Term Generation Flow

```
Term input
    |
    +-- Tavily search (5 results)        --+  parallel
    +-- gpt-4.1-mini type classification --+
                |
                v
    Select type-specific depth prompt
                |
    +-------------------------------+
    | Call 1: Meta + Basic KO       |
    | Call 2+3: Basic EN // Adv KO  |  <-- parallel
    | Call 4: Advanced EN           |
    +-------------------------------+
                |
    Self-Critique (gpt-4.1-mini)
    score < 75 --> regenerate
                |
    Quality Check (4 criteria x 25 points)
    score < 60 --> warning flag
                |
                v
    Save (draft / queued)
```

### Tech Stack Overview

| Layer | Technology | Hosting |
|-------|-----------|---------|
| Frontend | Astro v5 + Tailwind CSS v4 + TypeScript | Vercel |
| Backend | FastAPI + PydanticAI | Railway |
| AI | OpenAI (gpt-4.1 / gpt-4.1-mini / o4-mini) + Tavily | - |
| Database | Supabase (PostgreSQL + Auth + RLS) | Supabase |

---

> This document chronicles the AI pipeline development journey of 0to1log.
> 907 commits, 52 prompt issues, 6 prompt iterations, and 5 pipeline redesigns
> brought the system to its current state.
> As a solo project, I handled every stage from planning to deployment.
