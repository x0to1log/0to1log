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
Return JSON: {{"type": "one_of_the_10_types"}}
Only the type field. Nothing else."""


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


def get_type_depth_guide(term_type: str) -> str:
    """Return type-specific depth instructions for advanced prompt injection."""
    return TYPE_DEPTH_GUIDES.get(term_type, TYPE_DEPTH_GUIDES["concept_theory"])


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

If score >= 75, set needs_improvement to false."""


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
