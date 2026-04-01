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

## Disambiguation Rules
- Tool vs Product: free/open-source = infrastructure_tool, commercial/paid = product_brand
  - PyTorch = infrastructure_tool (free framework)
  - GitHub Copilot = product_brand (paid commercial service)
  - TensorFlow = infrastructure_tool (free framework)
  - AWS SageMaker = product_brand (paid cloud service)
- Algorithm vs Technique: algorithm has formal math specification, technique is a repeatable practice
  - Gradient Descent = algorithm_model (has convergence proof)
  - Data Augmentation = technique_method (family of practices, no single algorithm)
- Hybrid terms: choose the PRIMARY use case the reader would look up

## Output
Return JSON: {{"type": "one_of_the_10_types"}}
Only the type field. Nothing else."""


TYPE_DEPTH_GUIDES: dict[str, str] = {
    "algorithm_model": """## Type-Specific Depth: Algorithm/Model
- adv_*_1_technical: Include time/space complexity (Big O). Reference the original paper if applicable.
- adv_*_2_formulas: Full mathematical formulation with derivation steps, not just final formula. Include loss function, gradient update rules.
- adv_*_3_howworks: Data flow diagram description. Input → layers/steps → output. Include tensor shapes if applicable.
- adv_*_4_code: Production-grade code (NOT hello world). Include error handling, type hints, real library usage (torch, sklearn). Min 15 lines.
- adv_*_5_practical: Include benchmark comparisons (accuracy, latency, memory) with specific numbers from reference materials. If no benchmarks are available in references, state "Public benchmarks not yet available" rather than inventing numbers.
- CRITICAL: Do NOT fabricate paper titles, arXiv IDs, author names, or publication venues. Only cite papers from the Reference Materials provided. If no paper reference is available, write "See official documentation" instead.""",

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
- adv_*_5_practical: Where this concept causes real bugs/failures in production. Anti-patterns.
- CRITICAL: Do NOT fabricate paper citations or textbook references. Only cite sources from Reference Materials. If unavailable, omit the citation.""",

    "product_brand": """## Type-Specific Depth: Product/Brand
- adv_*_1_technical: Product capabilities, supported features, API surface area.
- adv_*_2_formulas: Competitive comparison table — this product vs 3-4 alternatives. Columns: pricing, performance benchmarks, key differentiators, limitations.
- adv_*_3_howworks: Architecture overview — how the product works internally (if known). API request flow.
- adv_*_4_code: API usage examples — authentication, common operations, error handling. Use REAL API endpoints from reference materials.
- adv_*_5_practical: Version history highlights. Migration notes. Known limitations and workarounds. If benchmarks are unavailable in references, state so rather than inventing numbers.""",

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


_SECTION_MINIMUM = """
## Section Quality Minimums
- Each advanced section: minimum 200 characters of substantive content
- adv_*_1_technical: minimum 400 characters (most important section)
- adv_*_4_code: minimum 15 lines of substantial code (if code applies to this type)
- Empty or placeholder sections ("TBD", "N/A") are NOT acceptable — omit the section key entirely if not applicable"""


def get_type_depth_guide(term_type: str) -> str:
    """Return type-specific depth instructions for advanced prompt injection."""
    guide = TYPE_DEPTH_GUIDES.get(term_type, TYPE_DEPTH_GUIDES["concept_theory"])
    return f"{guide}\n\n{_SECTION_MINIMUM}"


COVE_CRITIQUE_PROMPT = """You are a senior ML engineer performing Chain-of-Verification on a handbook entry.

The term "{term}" is classified as type: {term_type}.

## Your Task: Verify factual accuracy using ONLY the Reference Materials

### Step 1: Extract Factual Claims
Identify every specific factual claim in the content:
- Named entities (system names, protocol names, paper titles, product names)
- Numerical claims (benchmarks, dates, percentages, performance numbers)
- Product-technology mappings ("X uses Y", "X is built on Y")
- Disambiguation claims ("not to be confused with X")

### Step 2: Verify Against References
For each claim, check if it appears in or is supported by the Reference Materials below.
- SUPPORTED: claim matches information in references
- UNVERIFIABLE: claim is not covered by references (could be true but cannot confirm)
- CONTRADICTED: claim conflicts with references

### Step 3: Check for Depth and Quality
Also evaluate:
1. Sections that are too shallow (blog-post level instead of senior-engineer level)
2. Missing concrete data (numbers, benchmarks, comparisons)
3. Code that is too simplistic (hello-world level)
4. Sections that repeat basic-level content

## Reference Materials
{reference_context}

## Output JSON
{{
  "claims_checked": 0,
  "claims_supported": 0,
  "claims_unverifiable": 0,
  "needs_improvement": true/false,
  "flagged_claims": [
    {{"claim": "exact text from content", "section": "adv_ko_1_technical", "issue": "No reference supports this entity name", "suggestion": "Remove or replace with verified alternative"}}
  ],
  "improvements": [
    {{"section": "adv_*_4_code", "issue": "Code is only 5 lines", "suggestion": "Add production-grade example"}}
  ],
  "score": 0-100
}}

Scoring: 85+ (all claims verified, ready), 70-84 (minor unverifiable claims, flag for review), <70 (significant unverifiable content, regeneration needed).
If score >= 75, set needs_improvement to false."""


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
  "weak_sections": ["adv_*_3_howworks"],
  "improvements": [
    {{"section": "adv_*_4_code", "issue": "Code is only 5 lines with no error handling", "suggestion": "Add production-grade example with type hints and error handling"}}
  ],
  "score": 0-100
}}

If score >= 75, set needs_improvement to false.

## Examples

### Pass (score=82)
{{"needs_improvement": false, "weak_sections": [], "improvements": [], "score": 82}}

### Fail (score=55)
{{"needs_improvement": true, "weak_sections": ["adv_ko_4_code", "adv_ko_5_practical"], "improvements": [{{"section": "adv_ko_4_code", "issue": "Only 5 lines, no error handling", "suggestion": "Add production example with type hints, try/except, real library usage (15+ lines)"}}, {{"section": "adv_ko_5_practical", "issue": "No benchmark numbers", "suggestion": "Add specific performance comparison: latency, memory, accuracy vs alternatives"}}], "score": 55}}"""


HANDBOOK_QUALITY_CHECK_PROMPT = """You are evaluating a handbook term's advanced section quality.

Term: "{term}" | Type: {term_type}

Rate the advanced content (0-100) based on this term's type:

## Universal Criteria (all types)
- Depth: Is this senior-engineer level, not blog-post level? (0-25)
- Accuracy: Are claims specific and verifiable? (0-25)
- Uniqueness: Does advanced content differ from basic? (0-25)
- Completeness: Are all 9 sections substantive? (0-25)

## Score Interpretation
- score = depth + accuracy + uniqueness + completeness (each 0-25, sum = 0-100)
- 80+: Senior-engineer reference quality. Ready for publication.
- 60-79: Acceptable with minor improvements. Review recommended.
- 40-59: Blog-post level. Needs significant depth improvement.
- <40: Insufficient. Major revision needed.

## Scoring Rubric (5 tiers per criterion)

### Depth
- 23-25: Production code + architecture diagrams + math proofs + benchmark comparisons with cited sources
- 18-22: Production code + detailed explanations + some benchmarks
- 13-17: Working code + adequate explanations but lacking depth/benchmarks
- 8-12: Partial code or simplified explanations, blog-post level
- 0-7: Conceptual only, no implementation examples, Wikipedia-level

### Accuracy
- 23-25: All claims cite reference materials, verifiable numbers, no fabricated mappings
- 18-22: Most claims sourced, minor uncited statements
- 13-17: Mix of sourced and unsourced claims
- 8-12: Vague "widely used" statements, some fabricated product claims
- 0-7: Fabricated URLs, wrong product-technology mappings

### Uniqueness
- 23-25: Zero overlap with basic content, advanced-only insights and code
- 18-22: Minimal overlap, mostly new content
- 13-17: Some repeated analogies or examples from basic
- 8-12: Significant overlap, rephrased basic content
- 0-7: Essentially the same content as basic

### Completeness
- 23-25: All 9 sections substantive (min 200 chars each), no thin sections
- 18-22: 8-9 sections substantive, 1 thin
- 13-17: 6-7 sections substantive, 2-3 thin
- 8-12: 4-5 sections substantive, rest thin or empty
- 0-7: Multiple empty sections, incomplete coverage

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


BASIC_SELF_CRITIQUE_PROMPT = """You are reviewing a handbook basic section for quality.

The term "{term}" is classified as type: {term_type}.

## Your Task
Review the basic content (KO and EN) below and identify:
1. Sections where the analogy exists but the **concrete mechanism** is missing (1_plain must explain WHY it works, not just WHAT it is)
2. Examples that are cliche: smartphone face recognition, self-driving cars, voice assistants are BANNED
3. Comparison tables that are attribute tables ("high vs low", "good vs bad") instead of comparing 2+ real technologies
4. Communication examples (7_comm) that sound like news articles instead of team meeting/slack conversations
5. Product-technology claims (5_where) that seem fabricated or unverifiable
6. Cross-section repetition (same analogy/example reused across sections)

## Output JSON
{{
  "ko_needs_improvement": true/false,
  "en_needs_improvement": true/false,
  "ko_improvements": [
    {{"section": "basic_ko_2_example", "issue": "Uses banned smartphone example", "suggestion": "Replace with surprising, non-obvious application scenario"}}
  ],
  "en_improvements": [
    {{"section": "basic_en_7_comm", "issue": "Reads like a news article", "suggestion": "Rewrite in team conversation tone with specific metrics/context"}}
  ],
  "ko_score": 0-100,
  "en_score": 0-100
}}

If ko_score >= 75, set ko_needs_improvement to false.
If en_score >= 75, set en_needs_improvement to false.

## Examples

### Pass (score=82)
{{"ko_needs_improvement": false, "en_needs_improvement": false, "ko_improvements": [], "en_improvements": [], "ko_score": 82, "en_score": 80}}

### Fail (score=55)
{{"ko_needs_improvement": true, "en_needs_improvement": true, "ko_improvements": [{{"section": "basic_ko_1_plain", "issue": "Only analogy, no mechanism", "suggestion": "After the analogy, add 1-2 sentences explaining the concrete technical reason"}}, {{"section": "basic_ko_2_example", "issue": "Uses self-driving car example", "suggestion": "Replace with non-obvious scenario like Netflix subtitle generation"}}], "en_improvements": [{{"section": "basic_en_7_comm", "issue": "News article tone", "suggestion": "Rewrite as team slack message with metrics"}}], "ko_score": 55, "en_score": 60}}"""


BASIC_QUALITY_CHECK_PROMPT = """You are evaluating a handbook term's basic section quality.

Term: "{term}" | Type: {term_type}

Rate the basic content (0-100) on criteria relevant to beginner-oriented educational content:

## Criteria

### Engagement (0-25)
- 23-25: 1_plain has clear analogy AND concrete mechanism. 2_example uses surprising non-obvious scenarios. 8_related triggers curiosity with comparison points.
- 18-22: Analogy and mechanism present but one is weak. Examples are specific but not surprising. Related terms have some comparison points.
- 13-17: Analogy exists but mechanism missing. Examples are generic (smartphones, self-driving). Related terms are dictionary-style.
- 8-12: Shallow analogy only. Examples are cliche. Related terms just list names.
- 0-7: No analogy, no mechanism. Generic one-liners.

### Accuracy (0-25)
- 23-25: All product-technology mappings verified. 6_caution myths are concept-specific. No fabricated claims.
- 18-22: Most claims accurate, one minor unverifiable statement.
- 13-17: Mix of accurate and vague claims ("widely used in industry").
- 8-12: Some fabricated product claims or wrong technology mappings.
- 0-7: Multiple factual errors.

### Uniqueness (0-25)
- 23-25: Zero cross-section repetition. 3_glance compares 2+ specific technologies. Each section adds genuinely new information.
- 18-22: Minimal repetition. Table compares real concepts but lacks depth.
- 13-17: Some repeated analogies/examples across sections. Table is "high vs low" style.
- 8-12: Significant repetition. Table is a glossary.
- 0-7: Sections are essentially reworded versions of each other.

### Completeness (0-25)
- 23-25: All 8 sections substantive (min 150 chars each). 1_plain >= 300 chars. 7_comm has 4+ team conversation examples.
- 18-22: 7-8 sections substantive, one slightly thin.
- 13-17: 6-7 sections substantive, 1-2 thin.
- 8-12: 4-5 sections substantive, rest thin or empty.
- 0-7: Multiple empty sections.

## Score Interpretation
- score = engagement + accuracy + uniqueness + completeness (each 0-25, sum = 0-100)
- 80+: Publication ready. Engaging and accurate.
- 60-79: Acceptable with minor improvements.
- 40-59: Needs revision.
- <40: Major revision needed.

## Output JSON
{{
  "score": 0-100,
  "breakdown": {{
    "engagement": 0-25,
    "accuracy": 0-25,
    "uniqueness": 0-25,
    "completeness": 0-25
  }},
  "summary": "1-sentence assessment"
}}"""
