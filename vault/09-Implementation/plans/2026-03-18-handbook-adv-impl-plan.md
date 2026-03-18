# Handbook Advanced Quality System — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve handbook advanced content to senior-engineer reference quality via Tavily search, type-specific prompts, self-critique, and quality scoring.

**Architecture:** gpt-4o-mini classifies term type (10 categories) → Tavily searches for real-world data → type-specific advanced prompt replaces generic one → self-critique catches shallow content → quality score gates output.

**Tech Stack:** OpenAI (gpt-4o, gpt-4o-mini), Tavily API, FastAPI, asyncio

**Design Reference:** `vault/09-Implementation/plans/2026-03-18-handbook-advanced-quality-design.md`

---

## Chunk 1: Tavily Search + Type Classification

### Task 1: Tavily Search Function for Handbook Terms

**Files:**
- Modify: `backend/services/agents/advisor.py`

- [ ] **Step 1: Add Tavily search function**

Add after `_fetch_handbook_term_map()` (line ~542):

```python
async def _search_term_context(term: str) -> str:
    """Search web for term context using Tavily. Returns formatted reference text."""
    try:
        tavily = TavilyClient(api_key=settings.tavily_api_key)
        results = tavily.search(
            query=f"{term} AI technology explained",
            search_depth="advanced",
            max_results=5,
            include_raw_content=False,
        )
        if not results.get("results"):
            return ""
        parts = []
        for i, r in enumerate(results["results"], 1):
            title = r.get("title", "")
            url = r.get("url", "")
            content = r.get("content", "")[:600]
            parts.append(f"### [{i}] {title}\nURL: {url}\n{content}")
        return "## Reference Materials (from web search)\n\n" + "\n\n".join(parts)
    except Exception as e:
        logger.warning("Tavily search failed for '%s': %s", term, e)
        return ""
```

- [ ] **Step 2: Add import for TavilyClient**

Add at top of `advisor.py`:
```python
from tavily import TavilyClient
```

- [ ] **Step 3: Run ruff + verify**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check services/agents/advisor.py`
Expected: All checks passed

- [ ] **Step 4: Commit**

```bash
git add backend/services/agents/advisor.py
git commit -m "feat(handbook): add Tavily search function for term context"
```

---

### Task 2: Type Classification with gpt-4o-mini

**Files:**
- Create: `backend/services/agents/prompts_handbook_types.py`
- Modify: `backend/services/agents/advisor.py`

- [ ] **Step 1: Create type classification prompt**

Create `backend/services/agents/prompts_handbook_types.py`:

```python
"""Handbook term type classification and type-specific advanced prompts."""

TERM_TYPES = [
    "algorithm_model",
    "infrastructure_tool",
    "business_industry",
    "concept_theory",
    "product_brand",
    "metric_measure",
    "technique_method",
    "data_structure_format",
    "protocol_standard",
    "architecture_pattern",
]

CLASSIFY_TERM_PROMPT = """You are a technical term classifier. Given a term name and its categories, classify it into exactly ONE type.

## Types

1. **algorithm_model** — Algorithms, ML models, neural network architectures
   Examples: BERT, Transformer, GAN, Random Forest, Gradient Descent

2. **infrastructure_tool** — DevOps tools, frameworks, runtime environments
   Examples: Docker, Kubernetes, CUDA, TensorFlow, PostgreSQL

3. **business_industry** — Business concepts, market terms, organizational patterns
   Examples: Funding Round, AI Ecosystem, SaaS, Product-Market Fit

4. **concept_theory** — Abstract CS/ML concepts, mathematical theories
   Examples: Overfitting, Bias-Variance Tradeoff, CAP Theorem, Big O Notation

5. **product_brand** — Specific commercial products, named AI models/services
   Examples: GPT-5.4, Claude, Midjourney, GitHub Copilot, AWS SageMaker

6. **metric_measure** — Evaluation metrics, scoring methods, benchmarks
   Examples: AUC, F1 Score, BLEU, Perplexity, FLOPS, Latency

7. **technique_method** — Repeatable practices, engineering methods
   Examples: Data Augmentation, Prompt Engineering, A/B Testing, Feature Engineering

8. **data_structure_format** — Data structures, file formats, serialization specs
   Examples: Parquet, B-Tree, Protocol Buffers, ONNX, JSON-LD, Arrow

9. **protocol_standard** — Communication protocols, technical standards
   Examples: OAuth 2.0, HTTP/3, gRPC, WebSocket, MQTT, TLS 1.3

10. **architecture_pattern** — System design patterns, architectural blueprints
    Examples: Microservices, Event Sourcing, CQRS, RAG, MapReduce, Pub/Sub

## Output
Return JSON: {"type": "one_of_the_10_types"}
Only the type field. Nothing else."""
```

- [ ] **Step 2: Add classification function to advisor.py**

Add after `_search_term_context()`:

```python
async def _classify_term_type(term: str, categories: list[str], client, model_light: str) -> str:
    """Classify term into one of 10 types using gpt-4o-mini."""
    from services.agents.prompts_handbook_types import CLASSIFY_TERM_PROMPT, TERM_TYPES

    user_msg = f"Term: {term}\nCategories: {', '.join(categories)}"
    try:
        resp = await client.chat.completions.create(
            model=model_light,
            messages=[
                {"role": "system", "content": CLASSIFY_TERM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=100,
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = parse_ai_json(resp.choices[0].message.content, "term-classify")
        term_type = data.get("type", "concept_theory")
        if term_type not in TERM_TYPES:
            term_type = "concept_theory"
        return term_type
    except Exception as e:
        logger.warning("Term classification failed for '%s': %s", term, e)
        return "concept_theory"
```

- [ ] **Step 3: Run ruff + verify**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check services/agents/advisor.py`

- [ ] **Step 4: Commit**

```bash
git add backend/services/agents/advisor.py backend/services/agents/prompts_handbook_types.py
git commit -m "feat(handbook): add term type classification with gpt-4o-mini"
```

---

### Task 3: Integrate Tavily + Classification into Generate Flow

**Files:**
- Modify: `backend/services/agents/advisor.py` — `_run_generate_term()` function

- [ ] **Step 1: Add parallel Tavily + classification before Call 3-4**

In `_run_generate_term()`, after Call 1 completes (around line ~828), add before Call 2+3:

```python
    # Parallel: Tavily search + type classification (for advanced prompts)
    tavily_context, term_type = await asyncio.gather(
        _search_term_context(req.term),
        _classify_term_type(
            req.term, req.categories or basic_data.get("categories", []),
            client, settings.openai_model_light,
        ),
    )
    # Merge article_context with Tavily results
    combined_context = article_context
    if tavily_context:
        combined_context = f"{article_context}\n\n{tavily_context}" if article_context else tavily_context

    # Log classification
    logger.info("Term '%s' classified as type: %s", req.term, term_type)
```

- [ ] **Step 2: Pass combined_context to Call 3 and Call 4 user prompts**

Update the user prompt construction for Call 3 (KO Advanced) and Call 4 (EN Advanced) to include `combined_context`:

Replace the existing user prompt lines for advanced calls to append:
```python
    adv_user_prompt = f"Term: {req.term}\nKorean: {req.korean_name or basic_data.get('korean_name', '')}\n"
    adv_user_prompt += f"Definition (KO): {basic_data.get('definition_ko', '')}\n"
    adv_user_prompt += f"Definition (EN): {basic_data.get('definition_en', '')}\n"
    adv_user_prompt += f"Term Type: {term_type}\n"
    if combined_context:
        adv_user_prompt += f"\n---\n{combined_context[:6000]}\n---\n"
        adv_user_prompt += "Use the above reference materials as factual sources. Cite specific numbers and URLs from them.\n"
```

- [ ] **Step 3: Add term_type + tavily to debug_meta logging**

In the stage logging, add:
```python
"term_type": term_type,
"tavily_results": len(tavily_context) if tavily_context else 0,
```

- [ ] **Step 4: Run ruff + tests**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check . && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short`

- [ ] **Step 5: Commit**

```bash
git add backend/services/agents/advisor.py
git commit -m "feat(handbook): integrate Tavily search + type classification into generate flow"
```

---

## Chunk 2: Type-Specific Advanced Prompts

### Task 4: Write 10 Type-Specific Advanced Prompt Guides

**Files:**
- Modify: `backend/services/agents/prompts_handbook_types.py`

- [ ] **Step 1: Add type-specific depth guides**

Add to `prompts_handbook_types.py` — a dict mapping type → additional instructions injected into the advanced prompt:

```python
TYPE_DEPTH_GUIDES: dict[str, str] = {
    "algorithm_model": """## Type-Specific Depth: Algorithm/Model
- adv_*_1_technical: Include time/space complexity (Big O). Reference the original paper if applicable.
- adv_*_2_formulas: Full mathematical formulation with derivation steps, not just final formula. Include loss function, gradient update rules.
- adv_*_3_howworks: Data flow diagram description. Input → layers/steps → output. Include tensor shapes if applicable.
- adv_*_4_code: Production-grade code (NOT hello world). Include error handling, type hints, real library usage (torch, sklearn). Min 15 lines.
- adv_*_5_practical: Include benchmark comparisons (accuracy, latency, memory) with specific numbers from reference materials.""",

    "infrastructure_tool": """## Type-Specific Depth: Infrastructure/Tool
- adv_*_1_technical: Architecture diagram description (components, data flow, control plane vs data plane).
- adv_*_2_formulas: Performance characteristics table (throughput, latency, scalability limits). No math formulas needed.
- adv_*_3_howworks: Internal architecture. How requests are processed, scheduling, resource management.
- adv_*_4_code: Real configuration examples (YAML, Dockerfile, CLI commands). Production deployment patterns. Min 15 lines.
- adv_*_5_practical: Troubleshooting guide — common failure modes, debugging commands, monitoring metrics.""",

    "business_industry": """## Type-Specific Depth: Business/Industry
- adv_*_1_technical: Precise business definition with industry-standard terminology.
- adv_*_2_formulas: Market data table — size, growth rate, key players. Decision framework (matrix/flowchart).
- adv_*_3_howworks: Process flow — how this concept operates in practice. Stakeholders, timeline, decision points.
- adv_*_4_code: No code needed. Replace with: case study analysis (2-3 real companies, with specific numbers).
- adv_*_5_practical: Strategic implications — when to use, when to avoid, risk factors, ROI considerations.""",

    "concept_theory": """## Type-Specific Depth: Concept/Theory
- adv_*_1_technical: Formal definition. Cite foundational paper/textbook.
- adv_*_2_formulas: Mathematical formulation with step-by-step derivation and intuitive interpretation of each term.
- adv_*_3_howworks: Visual/geometric interpretation. "Imagine a 2D plot where..."
- adv_*_4_code: Demonstration code showing the concept in action (visualization, simulation). Min 15 lines.
- adv_*_5_practical: Where this concept causes real bugs/failures in production. Anti-patterns.""",

    "product_brand": """## Type-Specific Depth: Product/Brand
- adv_*_1_technical: Product capabilities, supported features, API surface area.
- adv_*_2_formulas: Competitive comparison table — this product vs 3-4 alternatives. Columns: pricing, performance benchmarks, key differentiators, limitations.
- adv_*_3_howworks: Architecture overview — how the product works internally (if known). API request flow.
- adv_*_4_code: API usage examples — authentication, common operations, error handling. Use REAL API endpoints from reference materials.
- adv_*_5_practical: Version history highlights. Migration notes. Known limitations and workarounds.""",

    "metric_measure": """## Type-Specific Depth: Metric/Measure
- adv_*_1_technical: Formal mathematical definition. What does this metric actually measure?
- adv_*_2_formulas: Full formula with derivation. Why this formula (e.g., why harmonic mean for F1, not arithmetic)?
- adv_*_3_howworks: Step-by-step calculation example with real numbers. Edge cases where the metric is misleading.
- adv_*_4_code: Implementation from scratch + library usage (sklearn, torch). Visualization code (ROC curve, confusion matrix).
- adv_*_5_practical: When NOT to use this metric. Alternative metrics and when to prefer them. Micro vs macro averaging.""",

    "technique_method": """## Type-Specific Depth: Technique/Method
- adv_*_1_technical: Formal description of the technique. Variants and their differences.
- adv_*_2_formulas: Comparison table — variants of this technique (e.g., CutMix vs Mixup vs CutOut for augmentation).
- adv_*_3_howworks: Step-by-step procedure. When to apply, in what order, how it interacts with other techniques.
- adv_*_4_code: Implementation of 2+ variants. Show the difference in code. Min 15 lines.
- adv_*_5_practical: Failure modes — when this technique hurts instead of helps. Hyperparameter sensitivity.""",

    "data_structure_format": """## Type-Specific Depth: Data Structure/Format
- adv_*_1_technical: Internal structure description. How data is organized on disk/memory.
- adv_*_2_formulas: Complexity analysis table — read/write/delete/search (average + worst case). Space complexity.
- adv_*_3_howworks: Internal operations — e.g., B-Tree node splitting, Parquet column encoding, Bloom filter hashing.
- adv_*_4_code: Usage examples — read, write, query. Include serialization/deserialization. Performance comparison code.
- adv_*_5_practical: When to use vs alternatives. Migration strategies. Compatibility concerns.""",

    "protocol_standard": """## Type-Specific Depth: Protocol/Standard
- adv_*_1_technical: Protocol version history. What changed and why. RFC references.
- adv_*_2_formulas: Handshake/flow diagram (described in text). State transitions.
- adv_*_3_howworks: Message format breakdown. Header structure, payload encoding, error codes.
- adv_*_4_code: Client/server implementation examples. Configuration for common frameworks. Security setup.
- adv_*_5_practical: Security considerations. Known vulnerabilities in older versions. Proxy/firewall traversal issues.""",

    "architecture_pattern": """## Type-Specific Depth: Architecture Pattern
- adv_*_1_technical: Pattern structure — components, responsibilities, communication.
- adv_*_2_formulas: Trade-off analysis table — consistency vs availability, complexity vs flexibility, etc.
- adv_*_3_howworks: Component interaction flow. How a request passes through the system. Failure handling.
- adv_*_4_code: Skeleton implementation showing the pattern structure. Configuration examples. Min 15 lines.
- adv_*_5_practical: Migration strategy from monolith/alternative. Real failure stories. When NOT to use this pattern.""",
}
```

- [ ] **Step 2: Add function to get type-specific guide**

```python
def get_type_depth_guide(term_type: str) -> str:
    """Return type-specific depth instructions for advanced prompt injection."""
    return TYPE_DEPTH_GUIDES.get(term_type, TYPE_DEPTH_GUIDES["concept_theory"])
```

- [ ] **Step 3: Run ruff**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check services/agents/prompts_handbook_types.py`

- [ ] **Step 4: Commit**

```bash
git add backend/services/agents/prompts_handbook_types.py
git commit -m "feat(handbook): add 10 type-specific advanced depth guides"
```

---

### Task 5: Inject Type-Specific Guide into Advanced Prompts

**Files:**
- Modify: `backend/services/agents/advisor.py` — Call 3 and Call 4

- [ ] **Step 1: Import the type guide function**

Add to imports in `advisor.py`:
```python
from services.agents.prompts_handbook_types import get_type_depth_guide
```

- [ ] **Step 2: Inject type guide into advanced system prompts**

In `_run_generate_term()`, when constructing Call 3 (KO Advanced) system prompt, append the type guide:

```python
    type_guide = get_type_depth_guide(term_type)
    adv_ko_system = f"{GENERATE_ADVANCED_PROMPT}\n\n{type_guide}"
```

Same for Call 4 (EN Advanced):
```python
    adv_en_system = f"{GENERATE_ADVANCED_EN_PROMPT}\n\n{type_guide}"
```

- [ ] **Step 3: Run ruff + tests**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check . && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short`

- [ ] **Step 4: Commit**

```bash
git add backend/services/agents/advisor.py
git commit -m "feat(handbook): inject type-specific depth guide into advanced prompts"
```

---

## Chunk 3: Self-Critique + Quality Check

### Task 6: Self-Critique Step

**Files:**
- Modify: `backend/services/agents/advisor.py`
- Modify: `backend/services/agents/prompts_handbook_types.py`

- [ ] **Step 1: Add self-critique prompt to prompts_handbook_types.py**

```python
SELF_CRITIQUE_PROMPT = """You are a senior ML engineer reviewing a handbook advanced section.

The term "{term}" is classified as type: {term_type}.

## Your Task
Review the advanced content below and identify:
1. Sections that are too shallow (blog-post level instead of senior-engineer level)
2. Missing concrete data (numbers, benchmarks, comparisons)
3. Code that is too simplistic (hello-world level)
4. Sections that repeat basic-level content

## Output JSON
{{
  "needs_improvement": true/false,
  "weak_sections": ["adv_*_3_howworks", ...],
  "improvements": [
    {{"section": "adv_*_4_code", "issue": "Code is only 5 lines with no error handling", "suggestion": "Add production-grade example with type hints and error handling"}},
    ...
  ],
  "score": 0-100
}}

If score >= 75, set needs_improvement to false."""
```

- [ ] **Step 2: Add self-critique function to advisor.py**

Add after `_classify_term_type()`:

```python
async def _self_critique_advanced(
    term: str, term_type: str, advanced_content: str,
    client, model: str,
) -> tuple[bool, str, int]:
    """Self-critique advanced content. Returns (needs_improvement, feedback, score)."""
    from services.agents.prompts_handbook_types import SELF_CRITIQUE_PROMPT

    system = SELF_CRITIQUE_PROMPT.format(term=term, term_type=term_type)
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": advanced_content[:8000]},
            ],
            max_tokens=2000,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        data = parse_ai_json(resp.choices[0].message.content, "self-critique")
        needs = data.get("needs_improvement", False)
        score = data.get("score", 50)
        feedback = ""
        if needs and data.get("improvements"):
            feedback = "\n".join(
                f"- {imp['section']}: {imp['suggestion']}"
                for imp in data["improvements"]
            )
        usage = extract_usage_metrics(resp, model)
        return needs, feedback, score, usage
    except Exception as e:
        logger.warning("Self-critique failed for '%s': %s", term, e)
        return False, "", 50, {}
```

- [ ] **Step 3: Integrate into _run_generate_term() after Call 3-4**

After Call 4 completes and before section assembly, add:

```python
    # Self-critique advanced content (KO only — saves cost, KO is primary)
    adv_ko_preview = "\n\n".join(
        f"## {k}: {v[:300]}" for k, v in advanced_ko_data.items() if k.startswith("adv_ko_")
    )
    needs_improvement, critique_feedback, critique_score, critique_usage = await _self_critique_advanced(
        req.term, term_type, adv_ko_preview, client, settings.openai_model_main,
    )
    if critique_usage:
        merged_usage = merge_usage_metrics(merged_usage, critique_usage)

    # If needs improvement, regenerate advanced KO with feedback
    if needs_improvement and critique_feedback:
        logger.info("Self-critique: regenerating advanced KO for '%s' (score=%d)", req.term, critique_score)
        improved_system = f"{adv_ko_system}\n\n## Reviewer Feedback (MUST address these):\n{critique_feedback}"
        resp3b = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": improved_system},
                {"role": "user", "content": adv_user_prompt},
            ],
            max_tokens=16000, temperature=0.35,
            response_format={"type": "json_object"},
        )
        advanced_ko_data = parse_ai_json(resp3b.choices[0].message.content, "Handbook-adv-ko-improved")
        usage3b = extract_usage_metrics(resp3b, model)
        merged_usage = merge_usage_metrics(merged_usage, usage3b)
```

- [ ] **Step 4: Run ruff + tests**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check . && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short`

- [ ] **Step 5: Commit**

```bash
git add backend/services/agents/advisor.py backend/services/agents/prompts_handbook_types.py
git commit -m "feat(handbook): add self-critique step for advanced content"
```

---

### Task 7: Quality Check Scoring

**Files:**
- Modify: `backend/services/agents/prompts_handbook_types.py`
- Modify: `backend/services/agents/advisor.py`

- [ ] **Step 1: Add quality check prompt**

Add to `prompts_handbook_types.py`:

```python
HANDBOOK_QUALITY_CHECK_PROMPT = """You are evaluating a handbook term's advanced section quality.

Term: "{term}" | Type: {term_type}

Rate the advanced content (0-100) based on this term's type:

## Universal Criteria (all types)
- Depth: Is this senior-engineer level, not blog-post level? (0-25)
- Accuracy: Are claims specific and verifiable? (0-25)
- Uniqueness: Does advanced content differ from basic? (0-25)
- Completeness: Are all 9 sections substantive? (0-25)

## Output JSON
{{
  "score": 0-100,
  "breakdown": {{
    "depth": 0-25,
    "accuracy": 0-25,
    "uniqueness": 0-25,
    "completeness": 0-25
  }},
  "summary": "1-sentence assessment"
}}"""
```

- [ ] **Step 2: Add quality check function**

```python
async def _check_handbook_quality(
    term: str, term_type: str, advanced_content: str, client,
) -> tuple[int, dict]:
    """Score handbook advanced quality. Returns (score, breakdown)."""
    from services.agents.prompts_handbook_types import HANDBOOK_QUALITY_CHECK_PROMPT

    system = HANDBOOK_QUALITY_CHECK_PROMPT.format(term=term, term_type=term_type)
    try:
        resp = await client.chat.completions.create(
            model=settings.openai_model_light,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": advanced_content[:6000]},
            ],
            max_tokens=500,
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = parse_ai_json(resp.choices[0].message.content, "handbook-quality")
        score = data.get("score", 50)
        usage = extract_usage_metrics(resp, settings.openai_model_light)
        return score, data, usage
    except Exception as e:
        logger.warning("Handbook quality check failed for '%s': %s", term, e)
        return 50, {}, {}
```

- [ ] **Step 3: Integrate into _run_generate_term() after assembly**

After `_assemble_all_sections()` and before post-processing:

```python
    # Quality check on assembled advanced content
    adv_combined = f"{data.get('body_advanced_ko', '')}\n\n{data.get('body_advanced_en', '')}"
    if adv_combined.strip():
        quality_score, quality_breakdown, quality_usage = await _check_handbook_quality(
            req.term, term_type, adv_combined, client,
        )
        if quality_usage:
            merged_usage = merge_usage_metrics(merged_usage, quality_usage)
        data["quality_score"] = quality_score
        data["quality_breakdown"] = quality_breakdown
        if quality_score < 60:
            warnings.append(f"Advanced quality score: {quality_score}/100 — review recommended")
        logger.info("Handbook quality for '%s': %d/100 (type=%s)", req.term, quality_score, term_type)
```

- [ ] **Step 4: Run ruff + tests**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check . && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short`

- [ ] **Step 5: Build frontend**

Run: `cd frontend && npm run build`
Expected: Complete!

- [ ] **Step 6: Commit**

```bash
git add backend/services/agents/advisor.py backend/services/agents/prompts_handbook_types.py
git commit -m "feat(handbook): add quality scoring for advanced content"
```

---

## Chunk 4: Final Integration + Verification

### Task 8: Pipeline Integration + Logging

**Files:**
- Modify: `backend/services/agents/advisor.py` — logging

- [ ] **Step 1: Add classification + quality stages to logging**

Log the classification and quality check as separate pipeline stages:

```python
    # Log classification
    _log_handbook_stage(
        "handbook.classify", {"tokens_used": 0, "cost_usd": 0.001},
        req, source, run_id, supabase,
        extra_meta={"term_type": term_type},
    )

    # Log quality check
    if quality_score is not None:
        _log_handbook_stage(
            "handbook.quality_check", quality_usage,
            req, source, run_id, supabase,
            extra_meta={"quality_score": quality_score, "term_type": term_type},
        )
```

- [ ] **Step 2: Run full test suite**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check . && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short`
Expected: All passed

- [ ] **Step 3: Build frontend**

Run: `cd frontend && npm run build`
Expected: Complete!

- [ ] **Step 4: Final commit + push**

```bash
git add -A
git commit -m "feat(handbook): complete advanced quality system — Tavily + type classification + self-critique + scoring"
git push
```

---

## Verification

1. **Admin editor**: 핸드북 에디터에서 "Generate All Fields" → 심화 콘텐츠가 유형에 맞는 깊이로 생성되는지 확인
2. **Pipeline**: 파이프라인 실행 → 추출된 용어의 심화 콘텐츠 품질 확인
3. **Pipeline logs**: `handbook.classify`, `handbook.quality_check` 스테이지가 기록되는지 확인
4. **비용**: 용어당 추가 비용이 ~$0.07 범위인지 pipeline_logs cost_usd로 확인
5. **질 점수**: `quality_score`가 DB에 저장되고 어드민에서 확인 가능한지 확인
