"""Handbook term taxonomy and type-specific prompt helpers."""

from __future__ import annotations

import re

TERM_TYPES = [
    "foundational_concept",
    "problem_failure_mode",
    "model_algorithm_family",
    "training_optimization_method",
    "retrieval_knowledge_system",
    "system_workflow_pattern",
    "data_storage_indexing_system",
    "protocol_format_data_structure",
    "capability_feature_spec",
    "metric_benchmark",
    "product_platform_service",
    "library_framework_sdk",
    "hardware_runtime_infra",
]

INTENT_VALUES = ["understand", "compare", "build", "debug", "evaluate"]
VOLATILITY_VALUES = ["stable", "evolving", "fast-changing"]

TYPE_SUBTYPE_VALUES: dict[str, list[str]] = {
    "foundational_concept": [
        "reasoning_method",
        "policy_discourse",
        "standard_regulation",
    ],
    "product_platform_service": [
        "ecosystem_platform",
        "model_api_service",
        "managed_ai_cloud_platform",
        "managed_ai_infra_service",
        "developer_tool_platform",
    ],
    "hardware_runtime_infra": [
        "accelerator_hardware",
        "compute_runtime",
        "serving_engine",
    ],
    "metric_benchmark": [
        "scalar_metric",
        "benchmark_suite",
    ],
    "protocol_format_data_structure": [
        "wire_protocol",
        "data_format",
        "core_data_structure",
    ],
}

DEFAULT_INTENT_BY_TYPE: dict[str, list[str]] = {
    "foundational_concept": ["understand"],
    "problem_failure_mode": ["debug", "understand"],
    "model_algorithm_family": ["understand", "compare"],
    "training_optimization_method": ["build", "compare"],
    "retrieval_knowledge_system": ["build", "understand"],
    "system_workflow_pattern": ["build", "compare"],
    "data_storage_indexing_system": ["build", "compare"],
    "protocol_format_data_structure": ["build", "understand"],
    "capability_feature_spec": ["compare", "evaluate"],
    "metric_benchmark": ["evaluate", "understand"],
    "product_platform_service": ["compare", "build"],
    "library_framework_sdk": ["build", "compare"],
    "hardware_runtime_infra": ["compare", "build"],
}

DEFAULT_VOLATILITY_BY_TYPE: dict[str, str] = {
    "foundational_concept": "stable",
    "problem_failure_mode": "evolving",
    "model_algorithm_family": "stable",
    "training_optimization_method": "evolving",
    "retrieval_knowledge_system": "evolving",
    "system_workflow_pattern": "fast-changing",
    "data_storage_indexing_system": "evolving",
    "protocol_format_data_structure": "stable",
    "capability_feature_spec": "fast-changing",
    "metric_benchmark": "evolving",
    "product_platform_service": "fast-changing",
    "library_framework_sdk": "evolving",
    "hardware_runtime_infra": "fast-changing",
}


def normalize_term_key(term: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", (term or "").lower()).strip()
    return re.sub(r"\s+", " ", cleaned)


def normalize_term_subtype(term_type: str, subtype: object | None) -> str | None:
    if not subtype:
        return None
    allowed = TYPE_SUBTYPE_VALUES.get(term_type, [])
    if not allowed:
        return None
    normalized = normalize_term_key(str(subtype)).replace(" ", "_")
    return normalized if normalized in allowed else None


def format_term_type_label(term_type: str, subtype: str | None = None) -> str:
    return f"{term_type} / {subtype}" if subtype else term_type


TERM_PLANNER_OVERRIDES: dict[str, dict[str, object]] = {
    "rag": {"type": "retrieval_knowledge_system", "intent": ["build", "understand"], "volatility": "evolving"},
    "retrieval augmented generation": {"type": "retrieval_knowledge_system", "intent": ["build", "understand"], "volatility": "evolving"},
    "hugging face": {"type": "product_platform_service", "subtype": "ecosystem_platform", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "huggingface": {"type": "product_platform_service", "subtype": "ecosystem_platform", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "pytorch": {"type": "library_framework_sdk", "intent": ["build", "compare"], "volatility": "evolving"},
    "attention": {"type": "model_algorithm_family", "intent": ["understand", "compare"], "volatility": "stable"},
    "transformer": {"type": "model_algorithm_family", "intent": ["understand", "compare"], "volatility": "stable"},
    "chain of thought": {"type": "foundational_concept", "subtype": "reasoning_method", "intent": ["understand", "compare"], "volatility": "evolving"},
    "cot": {"type": "foundational_concept", "subtype": "reasoning_method", "intent": ["understand", "compare"], "volatility": "evolving"},
    "frontier model": {"type": "foundational_concept", "subtype": "policy_discourse", "intent": ["understand", "evaluate"], "volatility": "fast-changing"},
    "iso 42001": {"type": "foundational_concept", "subtype": "standard_regulation", "intent": ["understand", "evaluate"], "volatility": "stable"},
    "lora": {"type": "training_optimization_method", "intent": ["build", "compare"], "volatility": "evolving"},
    "qlora": {"type": "training_optimization_method", "intent": ["build", "compare"], "volatility": "evolving"},
    "fine tuning": {"type": "training_optimization_method", "intent": ["build", "compare"], "volatility": "evolving"},
    "agentic workflow": {"type": "system_workflow_pattern", "intent": ["build", "compare"], "volatility": "fast-changing"},
    "agentic workflows": {"type": "system_workflow_pattern", "intent": ["build", "compare"], "volatility": "fast-changing"},
    "edge deployment": {"type": "system_workflow_pattern", "intent": ["build", "compare"], "volatility": "evolving"},
    "vector database": {"type": "data_storage_indexing_system", "intent": ["build", "compare"], "volatility": "evolving"},
    "feature store": {"type": "data_storage_indexing_system", "intent": ["build", "compare"], "volatility": "evolving"},
    "parquet": {"type": "protocol_format_data_structure", "subtype": "data_format", "intent": ["build", "understand"], "volatility": "stable"},
    "apache arrow": {"type": "protocol_format_data_structure", "subtype": "data_format", "intent": ["build", "understand"], "volatility": "stable"},
    "jsonl": {"type": "protocol_format_data_structure", "subtype": "data_format", "intent": ["build", "understand"], "volatility": "stable"},
    "oauth 2 0": {"type": "protocol_format_data_structure", "subtype": "wire_protocol", "intent": ["build", "understand"], "volatility": "stable"},
    "grpc": {"type": "protocol_format_data_structure", "subtype": "wire_protocol", "intent": ["build", "understand"], "volatility": "stable"},
    "websocket": {"type": "protocol_format_data_structure", "subtype": "wire_protocol", "intent": ["build", "understand"], "volatility": "stable"},
    "b tree": {"type": "protocol_format_data_structure", "subtype": "core_data_structure", "intent": ["build", "understand"], "volatility": "stable"},
    "1m context": {"type": "capability_feature_spec", "intent": ["compare", "evaluate"], "volatility": "fast-changing"},
    "function calling": {"type": "capability_feature_spec", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "multimodal": {"type": "capability_feature_spec", "intent": ["compare", "understand"], "volatility": "fast-changing"},
    "f1 score": {"type": "metric_benchmark", "subtype": "scalar_metric", "intent": ["evaluate", "understand"], "volatility": "stable"},
    "perplexity": {"type": "metric_benchmark", "subtype": "scalar_metric", "intent": ["evaluate", "understand"], "volatility": "stable"},
    "mmlu": {"type": "metric_benchmark", "subtype": "benchmark_suite", "intent": ["evaluate", "compare"], "volatility": "evolving"},
    "humaneval": {"type": "metric_benchmark", "subtype": "benchmark_suite", "intent": ["evaluate", "compare"], "volatility": "evolving"},
    "hallucination": {"type": "problem_failure_mode", "intent": ["debug", "understand"], "volatility": "evolving"},
    "prompt injection": {"type": "problem_failure_mode", "intent": ["debug", "build"], "volatility": "fast-changing"},
    "openai api": {"type": "product_platform_service", "subtype": "model_api_service", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "anthropic api": {"type": "product_platform_service", "subtype": "model_api_service", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "gemini api": {"type": "product_platform_service", "subtype": "model_api_service", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "bedrock": {"type": "product_platform_service", "subtype": "managed_ai_cloud_platform", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "vertex ai": {"type": "product_platform_service", "subtype": "managed_ai_cloud_platform", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "azure ai foundry": {"type": "product_platform_service", "subtype": "managed_ai_cloud_platform", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "pinecone": {"type": "product_platform_service", "subtype": "managed_ai_infra_service", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "qdrant cloud": {"type": "product_platform_service", "subtype": "managed_ai_infra_service", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "langsmith": {"type": "product_platform_service", "subtype": "developer_tool_platform", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "weights and biases": {"type": "product_platform_service", "subtype": "developer_tool_platform", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "w b": {"type": "product_platform_service", "subtype": "developer_tool_platform", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "trainium": {"type": "hardware_runtime_infra", "subtype": "accelerator_hardware", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "h100": {"type": "hardware_runtime_infra", "subtype": "accelerator_hardware", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "cuda": {"type": "hardware_runtime_infra", "subtype": "compute_runtime", "intent": ["build", "compare"], "volatility": "fast-changing"},
    "tensorrt": {"type": "hardware_runtime_infra", "subtype": "compute_runtime", "intent": ["build", "compare"], "volatility": "fast-changing"},
    "vllm": {"type": "hardware_runtime_infra", "subtype": "serving_engine", "intent": ["build", "compare"], "volatility": "fast-changing"},
    "text generation inference": {"type": "hardware_runtime_infra", "subtype": "serving_engine", "intent": ["build", "compare"], "volatility": "fast-changing"},
}


def get_term_planner_override(term: str) -> dict[str, object] | None:
    return TERM_PLANNER_OVERRIDES.get(normalize_term_key(term))


TERM_GENERATION_OVERRIDES: dict[str, dict[str, object]] = {
    "function calling": {
        "preferred_code_mode": "real-code",
        "basic_ko_focus_guide": (
            "## Function Calling KO Basic Compression Guide\n"
            "- Keep '쉽게 이해하기' to 3 short paragraphs max.\n"
            "- Keep '비유와 예시' to exactly 3 bullets.\n"
            "- Keep '한눈에 비교' to a table plus at most 2 short follow-up sentences.\n"
            "- Keep '어디서 왜 중요한가' to exactly 3 bullets.\n"
            "- Keep '자주 하는 오해' to exactly 3 misconception -> correction pairs.\n"
            "- Keep '대화에서는 이렇게' to exactly 4 short team-style lines."
        ),
        "advanced_ko_focus_guide": (
            "## Function Calling KO Advanced Readability Guide\n"
            "- Use design-review tone, not paper-summary tone.\n"
            "- Prefer bullets over long dense paragraphs.\n"
            "- Keep one claim per sentence whenever possible.\n"
            "- Prefer execution flow and runtime boundaries over abstract formalism.\n"
            "- Keep formulas minimal unless they directly clarify validation or control flow."
        ),
        "code_contract_guide": (
            "## Function Calling Code Contract\n"
            "- KO and EN code sections must implement the same system model and same logical steps.\n"
            "- Include a tool registry, schema validation, unknown tool handling, bad args handling, "
            "network or timeout failure handling, retry or backoff logic, and a no-call case.\n"
            "- Keep the code vendor-neutral. Do not rely on provider-specific SDK behavior.\n"
            "- Locale differences belong in the explanatory prose, not in the core code path."
        ),
        "advanced_focus_guide": (
            "## Function Calling Recovery Guide\n"
            "- Center the advanced explanation on the real runtime loop: tool schema definition -> model tool selection "
            "-> argument emission -> host-side validation -> execution boundary -> tool result handoff.\n"
            "- Explicitly distinguish model proposal from host execution. The model suggests a call; the application "
            "owns validation, authorization, retries, and failure handling.\n"
            "- In tradeoffs, compare function calling against RAG, generic tool-use prompts, and hardcoded routing.\n"
            "- In pitfalls, prioritize wrong tool choice, malformed arguments, unsafe defaults, relevance misses, "
            "unknown function handling, and runtime failure handling over benchmark commentary.\n"
            "- In code, include schema validation, unknown function handling, bad args, and network failure paths.\n"
            "- Avoid drifting into benchmark summaries unless they directly support an engineering decision."
        ),
        "reference_context": (
            "## Curated Function Calling Reference Materials\n\n"
            "### [1] Function calling - OpenAI API\n"
            "URL: https://platform.openai.com/docs/guides/function-calling/how-do-i-ensure-the-model-calls-the-correct-function\n"
            "Official guide describing the tool calling flow, JSON schema-based function definitions, strict mode, "
            "parallel tool calls, and the requirement that the application executes tool calls and returns outputs.\n\n"
            "### [2] Structured model outputs - OpenAI API\n"
            "URL: https://platform.openai.com/docs/guides/structured-outputs/supported-types\n"
            "Official guide distinguishing structured outputs from function calling and clarifying when JSON schema "
            "should constrain tool arguments versus final assistant responses.\n\n"
            "### [3] Tool use with Claude - Anthropic\n"
            "URL: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview\n"
            "Official overview of tool use, tool_use blocks, and the client-side responsibility to implement tools.\n\n"
            "### [4] How to implement tool use - Anthropic\n"
            "URL: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use\n"
            "Implementation guide covering tool definitions, message structure, execution handoff, and practical tool "
            "result loops.\n\n"
            "### [5] Function calling with the Gemini API - Google AI for Developers\n"
            "URL: https://ai.google.dev/gemini-api/docs/function-calling\n"
            "Official guide covering function declarations, OpenAPI-compatible schemas, application-side execution, "
            "modes, validation, and error handling recommendations."
        ),
        "references_en": [
            {
                "title": "Function calling",
                "authors": "OpenAI",
                "venue": "OpenAI API Docs",
                "type": "docs",
                "url": "https://platform.openai.com/docs/guides/function-calling/how-do-i-ensure-the-model-calls-the-correct-function",
                "tier": "primary",
                "annotation": "Official tool-calling flow, schema design, strict mode, and host execution loop.",
            },
            {
                "title": "Structured model outputs",
                "authors": "OpenAI",
                "venue": "OpenAI API Docs",
                "type": "docs",
                "url": "https://platform.openai.com/docs/guides/structured-outputs/supported-types",
                "tier": "primary",
                "annotation": "Clarifies when to use function calling versus schema-constrained final responses.",
            },
            {
                "title": "Tool use with Claude",
                "authors": "Anthropic",
                "venue": "Anthropic Docs",
                "type": "docs",
                "url": "https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview",
                "tier": "primary",
                "annotation": "Official overview of tool_use blocks and client-owned execution boundaries.",
            },
            {
                "title": "How to implement tool use",
                "authors": "Anthropic",
                "venue": "Anthropic Docs",
                "type": "docs",
                "url": "https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use",
                "tier": "primary",
                "annotation": "Concrete implementation guidance for tool schemas, execution loops, and tool results.",
            },
            {
                "title": "Function calling with the Gemini API",
                "authors": "Google",
                "venue": "Google AI for Developers",
                "type": "docs",
                "url": "https://ai.google.dev/gemini-api/docs/function-calling",
                "tier": "primary",
                "annotation": "Official function declaration, mode, validation, and error-handling guidance.",
            },
        ],
        "references_ko": [
            {
                "title": "Function calling",
                "authors": "OpenAI",
                "venue": "OpenAI API Docs",
                "type": "docs",
                "url": "https://platform.openai.com/docs/guides/function-calling/how-do-i-ensure-the-model-calls-the-correct-function",
                "tier": "primary",
                "annotation": "공식 툴 호출 흐름, JSON 스키마 정의, strict mode, 호스트 실행 책임을 정리한 문서.",
            },
            {
                "title": "Structured model outputs",
                "authors": "OpenAI",
                "venue": "OpenAI API Docs",
                "type": "docs",
                "url": "https://platform.openai.com/docs/guides/structured-outputs/supported-types",
                "tier": "primary",
                "annotation": "함수 호출과 구조화 응답의 경계를 설명해 언제 어떤 방식을 써야 하는지 구분해 준다.",
            },
            {
                "title": "Tool use with Claude",
                "authors": "Anthropic",
                "venue": "Anthropic Docs",
                "type": "docs",
                "url": "https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview",
                "tier": "primary",
                "annotation": "tool_use 블록 구조와 모델 제안 대 클라이언트 실행 경계를 공식적으로 설명한다.",
            },
            {
                "title": "How to implement tool use",
                "authors": "Anthropic",
                "venue": "Anthropic Docs",
                "type": "docs",
                "url": "https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use",
                "tier": "primary",
                "annotation": "툴 스키마 정의, 실행 루프, tool result 전달 패턴을 구현 관점에서 정리한 문서.",
            },
            {
                "title": "Function calling with the Gemini API",
                "authors": "Google",
                "venue": "Google AI for Developers",
                "type": "docs",
                "url": "https://ai.google.dev/gemini-api/docs/function-calling",
                "tier": "primary",
                "annotation": "함수 선언, 모드 설정, 검증, 에러 처리까지 포함한 공식 함수 호출 가이드.",
            },
        ],
    },
    "rag": {
        "preferred_code_mode": "pseudocode",
        "advanced_focus_guide": "",
    },
    "prompt injection": {
        "preferred_code_mode": "no-code",
        "advanced_focus_guide": "",
    },
    "vector database": {
        "preferred_code_mode": "real-code",
        "advanced_focus_guide": "",
    },
    "quantization": {
        "preferred_code_mode": "pseudocode",
        "advanced_focus_guide": "",
    },
    "context window": {
        "preferred_code_mode": "no-code",
        "advanced_focus_guide": "",
    },
}


def get_term_generation_override(term: str) -> dict[str, object] | None:
    return TERM_GENERATION_OVERRIDES.get(normalize_term_key(term))


SOURCE_FIELDS = ("definition", "hero", "basic", "advanced", "references")
SOURCE_CANDIDATES = ("curated", "brave", "exa", "tavily")

FIELD_SOURCE_PRIORITY: dict[str, list[str]] = {
    "definition": ["curated", "brave", "exa", "tavily"],
    "hero": ["tavily", "curated", "brave", "exa"],
    "basic": ["brave", "tavily", "curated", "exa"],
    "advanced": ["brave", "exa", "curated", "tavily"],
    "references": ["curated", "brave", "exa", "tavily"],
}

TYPE_SOURCE_PRIORITY: dict[str, dict[str, list[str]]] = {
    "capability_feature_spec": dict(FIELD_SOURCE_PRIORITY),
    "product_platform_service": {
        "definition": ["brave", "curated", "tavily", "exa"],
        "hero": ["tavily", "brave", "curated", "exa"],
        "basic": ["brave", "tavily", "curated", "exa"],
        "advanced": ["brave", "exa", "tavily", "curated"],
        "references": ["brave", "curated", "exa", "tavily"],
    },
    "model_algorithm_family": {
        "definition": ["exa", "brave", "curated", "tavily"],
        "hero": ["tavily", "brave", "exa", "curated"],
        "basic": ["exa", "brave", "tavily", "curated"],
        "advanced": ["exa", "brave", "curated", "tavily"],
        "references": ["exa", "brave", "curated", "tavily"],
    },
    "training_optimization_method": {
        "definition": ["exa", "brave", "curated", "tavily"],
        "hero": ["tavily", "brave", "exa", "curated"],
        "basic": ["exa", "brave", "tavily", "curated"],
        "advanced": ["exa", "brave", "curated", "tavily"],
        "references": ["exa", "brave", "curated", "tavily"],
    },
    "problem_failure_mode": {
        "definition": ["brave", "exa", "curated", "tavily"],
        "hero": ["tavily", "brave", "exa", "curated"],
        "basic": ["brave", "exa", "tavily", "curated"],
        "advanced": ["brave", "exa", "curated", "tavily"],
        "references": ["brave", "exa", "curated", "tavily"],
    },
}

SUBTYPE_SOURCE_PRIORITY: dict[tuple[str, str], dict[str, list[str]]] = {
    ("foundational_concept", "reasoning_method"): {
        "definition": ["exa", "brave", "curated", "tavily"],
        "hero": ["tavily", "exa", "brave", "curated"],
        "basic": ["exa", "brave", "curated", "tavily"],
        "advanced": ["exa", "brave", "curated", "tavily"],
        "references": ["exa", "brave", "curated", "tavily"],
    },
    ("foundational_concept", "policy_discourse"): {
        "definition": ["brave", "curated", "exa", "tavily"],
        "hero": ["tavily", "brave", "curated", "exa"],
        "basic": ["brave", "exa", "curated", "tavily"],
        "advanced": ["brave", "exa", "curated", "tavily"],
        "references": ["brave", "curated", "exa", "tavily"],
    },
    ("foundational_concept", "standard_regulation"): {
        "definition": ["brave", "curated", "exa", "tavily"],
        "hero": ["tavily", "brave", "curated", "exa"],
        "basic": ["brave", "curated", "exa", "tavily"],
        "advanced": ["brave", "curated", "exa", "tavily"],
        "references": ["brave", "curated", "exa", "tavily"],
    },
}

TYPE_AWARE_REFERENCE_BLOCKLISTS: dict[str, list[str]] = {
    "capability_feature_spec": [
        "datacamp.com",
        "mlsysbook.ai",
        "pmc.ncbi.nlm.nih.gov",
        "substack.com",
    ]
}

SUBTYPE_AWARE_REFERENCE_BLOCKLISTS: dict[tuple[str, str], list[str]] = {
    ("foundational_concept", "reasoning_method"): [
        "datacamp.com",
        "mlsysbook.ai",
        "pmc.ncbi.nlm.nih.gov",
        "substack.com",
    ],
}


def get_field_source_priority(term_type: str, field: str, subtype: str | None = None) -> list[str]:
    subtype_priority = SUBTYPE_SOURCE_PRIORITY.get((term_type, subtype or ""), {}).get(field)
    if subtype_priority:
        return list(subtype_priority)
    priority = TYPE_SOURCE_PRIORITY.get(term_type, {}).get(field)
    if priority:
        return list(priority)
    return list(FIELD_SOURCE_PRIORITY.get(field, list(SOURCE_CANDIDATES)))


def get_reference_blocklist(term_type: str, subtype: str | None = None) -> list[str]:
    merged: list[str] = []
    for host in TYPE_AWARE_REFERENCE_BLOCKLISTS.get(term_type, []):
        if host not in merged:
            merged.append(host)
    for host in SUBTYPE_AWARE_REFERENCE_BLOCKLISTS.get((term_type, subtype or ""), []):
        if host not in merged:
            merged.append(host)
    return merged


CLASSIFY_TERM_PROMPT = """You are a planner for an AI handbook pipeline.

Classify the term into exactly one type:
- foundational_concept
- problem_failure_mode
- model_algorithm_family
- training_optimization_method
- retrieval_knowledge_system
- system_workflow_pattern
- data_storage_indexing_system
- protocol_format_data_structure
- capability_feature_spec
- metric_benchmark
- product_platform_service
- library_framework_sdk
- hardware_runtime_infra

Guidance:
- hosted platform/service/model surface => product_platform_service
- importable framework/sdk => library_framework_sdk
- retrieval/indexing/reranking/grounding system => retrieval_knowledge_system
- orchestration across components => system_workflow_pattern
- feature/spec claim like context length/function calling => capability_feature_spec
- failure or security issue => problem_failure_mode
- architecture/mechanism => model_algorithm_family
- if type=foundational_concept, also choose one subtype when it materially sharpens retrieval and framing:
  - reasoning_method: prompting or reasoning scaffold such as Chain-of-Thought, scratchpad prompting, or deliberate reasoning traces
  - policy_discourse: umbrella governance/safety/capability term such as frontier model where technical meaning and policy meaning must be separated
  - standard_regulation: named standard, certification, or management-system concept such as ISO 42001
- if type=product_platform_service, also choose one subtype:
  - ecosystem_platform: hub/repository/distribution surface for models, datasets, apps
  - model_api_service: hosted model API endpoint and pricing surface
  - managed_ai_cloud_platform: cloud control plane with IAM/region/enterprise integration
  - managed_ai_infra_service: managed vector/runtime/inference infrastructure service
  - developer_tool_platform: eval, tracing, experiments, observability, prompt workflow tooling
- if type=hardware_runtime_infra, also choose one subtype:
  - accelerator_hardware: chips/accelerators such as Trainium or H100
  - compute_runtime: driver/compiler/runtime stack such as CUDA or TensorRT
  - serving_engine: serving stack such as vLLM or TGI
- if type=metric_benchmark, also choose one subtype:
  - scalar_metric: single-number metric such as F1 score or perplexity
  - benchmark_suite: multi-task benchmark or leaderboard such as MMLU
- if type=protocol_format_data_structure, also choose one subtype:
  - wire_protocol: network/auth/protocol flow such as OAuth 2.0 or gRPC
  - data_format: serialization/storage format such as Parquet or Arrow
  - core_data_structure: abstract data structure such as B-tree

Return JSON:
{
  "type": "one_of_13_types",
  "subtype": "optional_subtype_or_null",
  "intent": ["primary_intent", "optional_secondary"],
  "volatility": "stable_or_evolving_or_fast-changing",
  "confidence": 0.0
}
"""


TYPE_DEPTH_GUIDES: dict[str, str] = {
    "foundational_concept": "Explain the concept precisely, then its intuition, then where it matters.",
    "problem_failure_mode": "Lead with symptoms, root causes, detection, and mitigation.",
    "model_algorithm_family": "Explain data flow, complexity, bottlenecks, and what problem the design solves.",
    "training_optimization_method": "Explain when the method is applied, major variants, and configuration tradeoffs.",
    "retrieval_knowledge_system": "Organize around ingestion, chunking, indexing, retrieval, reranking, grounding, and evaluation.",
    "system_workflow_pattern": "Describe components, request flow, failure handling, and observability.",
    "data_storage_indexing_system": "Explain storage model, indexing path, read path, and scaling constraints.",
    "protocol_format_data_structure": "Explain structure, flow, compatibility, and safety.",
    "capability_feature_spec": "Explain what the feature label means operationally and where people over-interpret it.",
    "metric_benchmark": "Explain what the number means before formulas, then misuse cases and alternatives.",
    "product_platform_service": "Explain who it is for, what surface it exposes, pricing/lock-in, and migration cost.",
    "library_framework_sdk": "Explain developer abstractions, idiomatic usage, and integration constraints.",
    "hardware_runtime_infra": "Explain workload fit, throughput/latency tradeoffs, memory model, and deployment cost.",
}

SUBTYPE_DEPTH_GUIDES: dict[tuple[str, str], str] = {
    ("foundational_concept", "reasoning_method"): "Emphasize the direct method definition, what the reasoning trace is doing, and where adjacent reasoning discourse should be excluded.",
    ("foundational_concept", "policy_discourse"): "Separate the technical definition from the policy meaning. Do not collapse governance framing, safety framing, and capability framing into one blurry explanation.",
    ("foundational_concept", "standard_regulation"): "Emphasize scope, management system requirements, audit boundaries, and what teams must operationalize to comply.",
    ("product_platform_service", "ecosystem_platform"): "Emphasize hub surface, repository workflow, ecosystem gravity, and how models, datasets, and apps connect.",
    ("product_platform_service", "model_api_service"): "Emphasize endpoint surface, model lineup, rate limits, pricing semantics, and migration cost.",
    ("product_platform_service", "managed_ai_cloud_platform"): "Emphasize cloud control plane, IAM and region model, enterprise guardrails, and provider abstraction.",
    ("product_platform_service", "managed_ai_infra_service"): "Emphasize managed index/runtime topology, latency and scaling model, and operational constraints.",
    ("product_platform_service", "developer_tool_platform"): "Emphasize evals, traces, experiment tracking, prompt workflow, and team collaboration surface.",
    ("hardware_runtime_infra", "accelerator_hardware"): "Emphasize chip role, workload fit, memory/interconnect constraints, and cost or region availability.",
    ("hardware_runtime_infra", "compute_runtime"): "Emphasize the software stack around drivers, kernels, compilers, configuration flags, and compatibility constraints.",
    ("hardware_runtime_infra", "serving_engine"): "Emphasize batching, KV cache behavior, scheduler design, latency-throughput tradeoffs, and deployment patterns.",
    ("metric_benchmark", "scalar_metric"): "Emphasize formula meaning, threshold effects, and common misuse in imbalanced or noisy settings.",
    ("metric_benchmark", "benchmark_suite"): "Emphasize task composition, scoring methodology, contamination risk, and leaderboard caveats.",
    ("protocol_format_data_structure", "wire_protocol"): "Emphasize handshake or auth flow, actor responsibilities, interoperability, and security boundaries.",
    ("protocol_format_data_structure", "data_format"): "Emphasize schema layout, serialization model, compatibility, compression, and read/write tradeoffs.",
    ("protocol_format_data_structure", "core_data_structure"): "Emphasize invariants, supported operations, asymptotic behavior, and implementation tradeoffs.",
}

_SECTION_MINIMUM = """
## Section Quality Minimums
- Each advanced section must be substantive.
- adv_*_1_mechanism should be the deepest section.
- adv_*_3_code should show real usage or implementation patterns when code is relevant.
- Omit non-applicable sections instead of using placeholders.
"""


def get_type_depth_guide(term_type: str, subtype: str | None = None) -> str:
    guide = TYPE_DEPTH_GUIDES.get(term_type, TYPE_DEPTH_GUIDES["foundational_concept"])
    subtype_guide = SUBTYPE_DEPTH_GUIDES.get((term_type, subtype))
    label = format_term_type_label(term_type, subtype)
    if subtype_guide:
        guide = f"{guide} {subtype_guide}"
    return f"## Type-Specific Depth ({label})\n{guide}\n\n{_SECTION_MINIMUM}"


EVIDENCE_RULES: dict[str, list[str]] = {
    "foundational_concept": ["paper", "docs"],
    "problem_failure_mode": ["docs", "paper", "community"],
    "model_algorithm_family": ["paper", "docs", "community"],
    "training_optimization_method": ["paper", "docs", "community"],
    "retrieval_knowledge_system": ["paper", "docs", "community"],
    "system_workflow_pattern": ["docs", "community", "paper"],
    "data_storage_indexing_system": ["docs", "benchmark", "community"],
    "protocol_format_data_structure": ["docs", "paper"],
    "capability_feature_spec": ["docs", "benchmark", "community"],
    "metric_benchmark": ["paper", "docs", "benchmark"],
    "product_platform_service": ["docs", "benchmark", "community"],
    "library_framework_sdk": ["docs", "community", "code"],
    "hardware_runtime_infra": ["benchmark", "docs", "community"],
}

SUBTYPE_EVIDENCE_RULES: dict[tuple[str, str], list[str]] = {
    ("foundational_concept", "reasoning_method"): ["paper", "docs", "community"],
    ("foundational_concept", "policy_discourse"): ["docs", "paper", "community"],
    ("foundational_concept", "standard_regulation"): ["docs", "paper"],
    ("product_platform_service", "ecosystem_platform"): ["docs", "community", "code"],
    ("product_platform_service", "model_api_service"): ["docs", "benchmark", "community"],
    ("product_platform_service", "managed_ai_cloud_platform"): ["docs", "benchmark", "community"],
    ("product_platform_service", "managed_ai_infra_service"): ["docs", "benchmark", "community"],
    ("product_platform_service", "developer_tool_platform"): ["docs", "community", "benchmark"],
    ("hardware_runtime_infra", "accelerator_hardware"): ["benchmark", "docs", "community"],
    ("hardware_runtime_infra", "compute_runtime"): ["docs", "benchmark", "community"],
    ("hardware_runtime_infra", "serving_engine"): ["benchmark", "docs", "community"],
    ("metric_benchmark", "scalar_metric"): ["paper", "docs", "benchmark"],
    ("metric_benchmark", "benchmark_suite"): ["paper", "benchmark", "docs"],
    ("protocol_format_data_structure", "wire_protocol"): ["docs", "paper"],
    ("protocol_format_data_structure", "data_format"): ["docs", "code", "community"],
    ("protocol_format_data_structure", "core_data_structure"): ["docs", "paper"],
}

TYPE_QUERY_FOCUS: dict[str, str] = {
    "foundational_concept": "definition intuition mechanism examples",
    "problem_failure_mode": "symptoms root cause detection mitigation",
    "model_algorithm_family": "architecture mechanism complexity comparison",
    "training_optimization_method": "implementation variants hyperparameters tradeoffs",
    "retrieval_knowledge_system": "chunking indexing retrieval reranking grounding evaluation",
    "system_workflow_pattern": "orchestration components request flow observability",
    "data_storage_indexing_system": "storage index retrieval consistency scaling",
    "protocol_format_data_structure": "spec format handshake schema interoperability",
    "capability_feature_spec": "capability limits benchmarking usage constraints",
    "metric_benchmark": "formula interpretation pitfalls comparison",
    "product_platform_service": "official docs pricing release notes comparison",
    "library_framework_sdk": "official docs api usage examples integration",
    "hardware_runtime_infra": "benchmark deployment configuration workload fit",
}

SUBTYPE_QUERY_FOCUS: dict[tuple[str, str], str] = {
    ("foundational_concept", "reasoning_method"): "reasoning method explicit reasoning traces scratchpad prompting direct definition",
    ("foundational_concept", "policy_discourse"): "technical definition policy meaning governance safety capability framing official definition",
    ("foundational_concept", "standard_regulation"): "standard requirements controls certification audit scope management system",
    ("product_platform_service", "ecosystem_platform"): "hub datasets spaces model cards repository workflow ecosystem",
    ("product_platform_service", "model_api_service"): "api endpoints pricing rate limits responses migration",
    ("product_platform_service", "managed_ai_cloud_platform"): "iam regions guardrails knowledge bases agents governance",
    ("product_platform_service", "managed_ai_infra_service"): "index cluster namespaces replicas latency scaling operations",
    ("product_platform_service", "developer_tool_platform"): "traces evals experiments observability prompt management workflow",
    ("hardware_runtime_infra", "accelerator_hardware"): "accelerator chip memory bandwidth interconnect throughput training inference",
    ("hardware_runtime_infra", "compute_runtime"): "runtime kernels compiler driver configuration compatibility performance",
    ("hardware_runtime_infra", "serving_engine"): "batching kv cache scheduler serving throughput latency deployment",
    ("metric_benchmark", "scalar_metric"): "formula threshold interpretation misuse class imbalance",
    ("metric_benchmark", "benchmark_suite"): "tasks scoring coverage contamination leaderboard comparison",
    ("protocol_format_data_structure", "wire_protocol"): "handshake authorization flow tokens interoperability spec",
    ("protocol_format_data_structure", "data_format"): "schema serialization columnar compression compatibility read write",
    ("protocol_format_data_structure", "core_data_structure"): "insert lookup traversal complexity invariants balancing",
}


def get_evidence_priorities(term_type: str, subtype: str | None = None) -> list[str]:
    return SUBTYPE_EVIDENCE_RULES.get((term_type, subtype), EVIDENCE_RULES.get(term_type, ["docs", "paper"]))


def get_type_query_focus(term_type: str, subtype: str | None = None) -> str:
    return SUBTYPE_QUERY_FOCUS.get((term_type, subtype), TYPE_QUERY_FOCUS.get(term_type, TYPE_QUERY_FOCUS["foundational_concept"]))


TYPE_SECTION_WEIGHTS: dict[tuple[str, str], str] = {
    ("foundational_concept", "understand"): "Lead with intuition, then mechanism. Do not rush into implementation.",
    ("problem_failure_mode", "debug"): "Lead with symptoms, then root cause, then detection and mitigation.",
    ("model_algorithm_family", "compare"): "Lead with what problem the design solves relative to nearby alternatives.",
    ("training_optimization_method", "build"): "Lead with when to apply the method and what configuration choices matter.",
    ("retrieval_knowledge_system", "build"): "Lead with pipeline stages and evaluation criteria. Do not let code outrun system design.",
    ("system_workflow_pattern", "build"): "Lead with component responsibilities, execution flow, guardrails, and observability.",
    ("data_storage_indexing_system", "build"): "Lead with data model, index strategy, read/write path, and scaling tradeoffs.",
    ("protocol_format_data_structure", "build"): "Lead with structure or flow before API details.",
    ("capability_feature_spec", "compare"): "Lead with what the feature means operationally and where the label is misleading.",
    ("metric_benchmark", "evaluate"): "Lead with interpretation and misuse risk before formulas or leaderboards.",
    ("product_platform_service", "compare"): "Lead with adoption criteria, alternatives, pricing, lock-in, and migration cost.",
    ("library_framework_sdk", "build"): "Lead with core abstractions, installation context, and integration ergonomics.",
    ("hardware_runtime_infra", "compare"): "Lead with workload fit, throughput/latency, memory limits, and deployment cost.",
}

SUBTYPE_SECTION_WEIGHTS: dict[tuple[str, str, str], str] = {
    ("foundational_concept", "reasoning_method", "understand"): "Lead with the direct method definition and what the reasoning trace contributes. Keep adjacent benchmark or general reasoning discourse secondary.",
    ("foundational_concept", "reasoning_method", "compare"): "Compare the reasoning method against nearby prompting or reasoning scaffolds without drifting into unrelated evaluation trends.",
    ("foundational_concept", "policy_discourse", "understand"): "Separate the technical definition from the policy meaning. Explain why the label is contested before discussing examples.",
    ("foundational_concept", "policy_discourse", "evaluate"): "Evaluate the discourse term by separating technical scope, governance scope, and safety claims. Do not collapse them.",
    ("foundational_concept", "standard_regulation", "understand"): "Lead with scope, control objectives, and what an adopting organization must operationalize.",
    ("foundational_concept", "standard_regulation", "evaluate"): "Lead with applicability, auditability, evidence requirements, and implementation burden.",
    ("product_platform_service", "ecosystem_platform", "compare"): "Lead with what the hub/ecosystem contains, how teams publish or consume assets, and where switching cost comes from.",
    ("product_platform_service", "ecosystem_platform", "build"): "Lead with repository workflow, model and dataset distribution, and how SDKs connect to the ecosystem surface.",
    ("product_platform_service", "model_api_service", "compare"): "Lead with endpoint surface, pricing units, rate limits, model coverage, and migration friction.",
    ("product_platform_service", "managed_ai_cloud_platform", "compare"): "Lead with enterprise controls, region and IAM model, managed integrations, and provider coverage.",
    ("product_platform_service", "managed_ai_infra_service", "compare"): "Lead with managed runtime or index topology, latency envelope, scaling knobs, and operational fit.",
    ("product_platform_service", "developer_tool_platform", "compare"): "Lead with eval, traces, experiment workflow, and how the tool changes team operating habits.",
    ("hardware_runtime_infra", "accelerator_hardware", "compare"): "Lead with workload fit, memory and interconnect constraints, and cost-performance tradeoffs against nearby accelerators.",
    ("hardware_runtime_infra", "compute_runtime", "build"): "Lead with software stack role, compatibility prerequisites, and the configuration knobs developers actually touch.",
    ("hardware_runtime_infra", "serving_engine", "build"): "Lead with batching, scheduler design, KV cache handling, and deployment tradeoffs before generic serving claims.",
    ("metric_benchmark", "scalar_metric", "evaluate"): "Lead with what the scalar means, when it misleads, and how thresholding or class imbalance changes interpretation.",
    ("metric_benchmark", "benchmark_suite", "evaluate"): "Lead with what tasks are inside the suite, what the score aggregates, and why leaderboard comparisons can be brittle.",
    ("protocol_format_data_structure", "wire_protocol", "build"): "Lead with request or auth flow, participant roles, and interoperability or security constraints.",
    ("protocol_format_data_structure", "data_format", "build"): "Lead with schema and storage layout, then compatibility and performance tradeoffs.",
    ("protocol_format_data_structure", "core_data_structure", "build"): "Lead with supported operations, invariants, and complexity before implementation detail.",
}


def get_section_weight_guide(term_type: str, intent: str, subtype: str | None = None) -> str:
    label = format_term_type_label(term_type, subtype)
    guide = SUBTYPE_SECTION_WEIGHTS.get((term_type, subtype or "", intent))
    if guide:
        return f"## Content Priority Guide ({label} x {intent})\n{guide}"
    guide = TYPE_SECTION_WEIGHTS.get((term_type, intent))
    if guide:
        return f"## Content Priority Guide ({label} x {intent})\n{guide}"
    fallback_intent = DEFAULT_INTENT_BY_TYPE.get(term_type, ["understand"])[0]
    fallback = SUBTYPE_SECTION_WEIGHTS.get((term_type, subtype or "", fallback_intent))
    if fallback:
        return f"## Content Priority Guide ({label} x {fallback_intent})\n{fallback}"
    fallback = TYPE_SECTION_WEIGHTS.get((term_type, fallback_intent))
    if fallback:
        return f"## Content Priority Guide ({label} x {fallback_intent})\n{fallback}"
    return ""


CATEGORY_CONTEXT: dict[str, dict[str, str]] = {
    "cs-fundamentals": {
        "vocabulary": "data structure, algorithm, protocol, runtime, API, compiler, interpreter, hash table, HTTP, thread, process, stack, heap",
        "quality_signals": "Use concrete programming scenarios and official specs where relevant.",
        "anti_patterns": "Do not force AI framing when the concept is fundamentally general CS.",
        "reference_style": "Prefer MDN, RFCs, W3C, language specifications, and official docs.",
        "code_guide": "Use standard library or mainstream framework examples before niche tools.",
    },
    "math-statistics": {
        "vocabulary": "proof, theorem, estimator, variance, convergence, expectation, likelihood, posterior, prior",
        "quality_signals": "Lead with intuition before formulas. Use concrete numerical examples.",
        "anti_patterns": "Do not reduce the concept to only AI usage.",
        "reference_style": "Use textbook notation and foundational sources when available.",
        "code_guide": "Pair math explanation with numpy/scipy examples when code helps.",
    },
    "ml-fundamentals": {
        "vocabulary": "feature, label, overfitting, regularization, cross-validation, hyperparameter, precision, recall, ROC-AUC",
        "quality_signals": "Show full train/evaluate context and compare credible alternatives.",
        "anti_patterns": "Do not treat classical ML as obsolete by default.",
        "reference_style": "Use official library docs and foundational algorithm references.",
        "code_guide": "Prefer scikit-learn style examples for baseline implementations.",
    },
    "deep-learning": {
        "vocabulary": "tensor, gradient, backpropagation, layer, activation, learning rate, convolution, attention",
        "quality_signals": "Make tensor flow and compute tradeoffs explicit.",
        "anti_patterns": "Do not ignore memory, latency, or training-vs-inference differences.",
        "reference_style": "Use original papers and official implementation/docs when possible.",
        "code_guide": "Prefer PyTorch examples with clear shapes and data flow.",
    },
    "llm-genai": {
        "vocabulary": "token, prompt, context window, alignment, agent, tool use, embedding, retrieval, fine-tuning",
        "quality_signals": "Use developer workflows, cost awareness, and limitations.",
        "anti_patterns": "Avoid marketing language and vague capability claims.",
        "reference_style": "Prefer official API docs, benchmark references, and current platform docs.",
        "code_guide": "Show practical API or orchestration patterns, then what happens under the hood.",
    },
    "data-engineering": {
        "vocabulary": "pipeline, schema, partitioning, checkpoint, idempotency, lineage, throughput, latency, backfill",
        "quality_signals": "Discuss scaling, failure recovery, and maintenance cost.",
        "anti_patterns": "Do not treat all storage or indexing approaches as interchangeable.",
        "reference_style": "Prefer official architecture docs and versioned product documentation.",
        "code_guide": "Show data flow, then real integration snippets or configuration.",
    },
    "infra-hardware": {
        "vocabulary": "GPU, CUDA, kernel, throughput, latency, quantization, cluster, container, shard, replica",
        "quality_signals": "Use operational constraints, workload fit, and cost-aware comparisons.",
        "anti_patterns": "Do not explain only theory and skip deployment constraints.",
        "reference_style": "Use vendor docs, benchmarks, and deployment docs.",
        "code_guide": "Prefer deployment config, runtime flags, or profiling examples.",
    },
    "safety-ethics": {
        "vocabulary": "alignment, adversarial, bias, red teaming, audit, data poisoning, jailbreak, guardrail",
        "quality_signals": "Ground discussion in incidents, detection, and defenses.",
        "anti_patterns": "Avoid purely philosophical discussion when the term has technical mitigations.",
        "reference_style": "Use safety research, standards, and official guidance.",
        "code_guide": "Prefer concrete mitigation patterns, evaluators, and guardrail examples.",
    },
    "products-platforms": {
        "vocabulary": "API, SDK, release, pricing, benchmark, migration, deprecation, rate limit, quota, SLA",
        "quality_signals": "Include version/date sensitivity, pricing, and alternatives.",
        "anti_patterns": "Do not repeat marketing claims without tradeoffs.",
        "reference_style": "Prefer official docs, changelogs, and pricing pages.",
        "code_guide": "Show real integration or API usage with version awareness.",
    },
}


def build_category_block(category: str) -> str:
    ctx = CATEGORY_CONTEXT.get(category)
    if not ctx:
        return ""
    return (
        f"## Domain Context: {category}\n"
        f"<vocabulary>{ctx['vocabulary']}</vocabulary>\n"
        f"<quality_signals>{ctx['quality_signals']}</quality_signals>\n"
        f"<anti_patterns>{ctx['anti_patterns']}</anti_patterns>\n"
        f"<reference_style>{ctx['reference_style']}</reference_style>\n"
        f"<code_guide>{ctx['code_guide']}</code_guide>"
    )


BASIC_TYPE_GUIDES: dict[str, str] = {
    "foundational_concept": "Start with plain intuition, then explain the concrete mechanism.",
    "problem_failure_mode": "Start with what breaks and what it looks like in practice.",
    "model_algorithm_family": "Explain what the family does differently and what problem it solves before formulas or code.",
    "training_optimization_method": "Describe the problem first, then the method as a practical lever.",
    "retrieval_knowledge_system": "Frame the explanation around ingestion, indexing, retrieval, and grounding stages.",
    "system_workflow_pattern": "Describe the overall flow and roles of the components.",
    "data_storage_indexing_system": "Explain what gets stored, how it is organized, and how it gets read back.",
    "protocol_format_data_structure": "Use a visual metaphor for structure or flow, then show a tiny practical example.",
    "capability_feature_spec": "Explain what the feature label really means in practice and where people over-interpret it.",
    "metric_benchmark": "Explain what the number tells you in plain language before any math.",
    "product_platform_service": "Lead with what it is, who it is for, and how people usually adopt it.",
    "library_framework_sdk": "Lead with what a developer installs and what abstractions they work with.",
    "hardware_runtime_infra": "Start with what workload problem this solves and what it costs operationally.",
}

SUBTYPE_BASIC_GUIDES: dict[tuple[str, str], str] = {
    ("foundational_concept", "reasoning_method"): "Lead with the direct reasoning method first: what the trace is, why it helps, and how it differs from broader reasoning discourse.",
    ("foundational_concept", "policy_discourse"): "Lead with the plain-language definition, then separate the technical meaning from the governance or policy meaning.",
    ("foundational_concept", "standard_regulation"): "Lead with what the standard applies to, who uses it, and what adopting it changes operationally.",
    ("product_platform_service", "ecosystem_platform"): "Lead with the hub or ecosystem surface first: what assets live there, who publishes them, and how teams usually use the platform.",
    ("product_platform_service", "model_api_service"): "Lead with the hosted API surface: what developers call, what models they get, and what pricing or limits matter first.",
    ("product_platform_service", "managed_ai_cloud_platform"): "Lead with the managed cloud surface: what the provider manages, how enterprise teams adopt it, and where governance shows up.",
    ("product_platform_service", "managed_ai_infra_service"): "Lead with the managed infrastructure service: what gets operated for the user and what scaling or latency problem it solves.",
    ("product_platform_service", "developer_tool_platform"): "Lead with the developer workflow: what teams observe, evaluate, or coordinate through the platform.",
    ("hardware_runtime_infra", "accelerator_hardware"): "Lead with what kind of chip or accelerator it is, what workload it is built for, and what practical constraints teams hit first.",
    ("hardware_runtime_infra", "compute_runtime"): "Lead with the runtime layer developers install or depend on, then explain what that layer unlocks and what it constrains.",
    ("hardware_runtime_infra", "serving_engine"): "Lead with how it serves models in practice: batching, memory reuse, and deployment behavior.",
    ("metric_benchmark", "scalar_metric"): "Lead with what the single number means in plain language and when it can be misleading.",
    ("metric_benchmark", "benchmark_suite"): "Lead with what kinds of tasks are bundled together and what a higher score actually does and does not prove.",
    ("protocol_format_data_structure", "wire_protocol"): "Lead with who talks to whom and what the handshake or auth flow looks like.",
    ("protocol_format_data_structure", "data_format"): "Lead with what the bytes or columns represent and why teams choose this format over nearby alternatives.",
    ("protocol_format_data_structure", "core_data_structure"): "Lead with what operations the structure makes fast or slow before discussing internals.",
}


def get_type_basic_guide(term_type: str, subtype: str | None = None) -> str:
    guide = SUBTYPE_BASIC_GUIDES.get((term_type, subtype), BASIC_TYPE_GUIDES.get(term_type, BASIC_TYPE_GUIDES["foundational_concept"]))
    label = format_term_type_label(term_type, subtype)
    return f"## Basic Content Guide ({label})\n{guide}"


COVE_CRITIQUE_PROMPT = """You are a senior ML engineer performing Chain-of-Verification on a handbook entry.

The term "{term}" is classified as type: {term_type}.

Use only the supplied reference materials to:
1. identify factual claims
2. verify or flag them
3. note shallow sections or weak code

## Reference Materials
{reference_context}

## Output JSON
{{
  "claims_checked": 0,
  "claims_supported": 0,
  "claims_unverifiable": 0,
  "needs_improvement": true,
  "flagged_claims": [
    {{"claim": "exact claim", "section": "adv_ko_1_mechanism", "issue": "why weak", "suggestion": "how to fix"}}
  ],
  "improvements": [
    {{"section": "adv_*_3_code", "issue": "issue", "suggestion": "fix"}}
  ],
  "score": 0
}}

If score >= 75, set needs_improvement to false."""


SELF_CRITIQUE_PROMPT = """You are a senior ML engineer reviewing a handbook advanced section.

The term "{term}" is classified as type: {term_type}.

Find shallow sections, missing data, weak code, or places where advanced content repeats basic content.

## Output JSON
{{
  "needs_improvement": true,
  "weak_sections": ["adv_ko_1_mechanism"],
  "improvements": [
    {{"section": "adv_*_3_code", "issue": "issue", "suggestion": "fix"}}
  ],
  "score": 0
}}

If score >= 75, set needs_improvement to false."""


HANDBOOK_QUALITY_CHECK_PROMPT = """You are evaluating a handbook term's advanced section quality.

Term: "{term}" | Type: {term_type}

## Scoring Scale (applies to EVERY sub-score)

Use this 4-anchor scale on a 0-10 continuous range:
- **10**: Exemplary — criterion fully met with concrete evidence cited.
- **7**: Solid — criterion met with minor gaps.
- **4**: Weak — partial or surface-level adherence; notable gaps.
- **0**: Missing, contradicts the criterion, or fabricated.

## Required Output Format (per sub-score)

For EVERY sub-score you MUST provide BOTH:
1. `evidence`: Quote or describe SPECIFIC content observed (cite section heading or exact phrase). Empty evidence is not acceptable — if you find nothing, say so explicitly.
2. `score`: 0-10 integer using the scale above, grounded in the evidence you just cited.

Do NOT output any total or subtotal — code computes aggregates from sub-scores.
Do NOT hedge ("probably", "seems", "might") — anchor each score to concrete evidence.
Do NOT invent sections that aren't in the content.

## Sub-dimensions (10 sub-scores)

### Technical Depth
- **mechanism_clarity**: HOW the system works internally (data flow, algorithm steps, not just WHAT it does)
- **concrete_specifics**: Real numbers (parameter counts, FLOPs, benchmark results, latency figures) rather than qualitative handwaves
- **code_or_formula**: Working code or mathematical formulas are present, correct, and relevant to the term

### Accuracy
- **factual_correctness**: Claims verifiable against official docs or common technical knowledge
- **hallucination_absence**: No fabricated benchmarks, product names, paper titles, RFC numbers, or entities

### Uniqueness
- **term_differentiation**: Content clearly distinguishes this concept from similar handbook terms
- **internal_non_redundancy**: Each section adds new information; no paraphrasing the same idea across sections

### Structural Completeness
- **required_sections_present**: All expected sections are present with substantive content (not placeholder stubs)
- **format_compliance**: `❌ Mistake:`/`✅ Fix:` markers in pitfalls, `(prerequisite)`/`(alternative)`/`(extension)` tags in relations, references as structured array

## Output JSON

{{
  "technical_depth": {{
    "mechanism_clarity":   {{ "evidence": "...", "score": 0 }},
    "concrete_specifics":  {{ "evidence": "...", "score": 0 }},
    "code_or_formula":     {{ "evidence": "...", "score": 0 }}
  }},
  "accuracy": {{
    "factual_correctness":   {{ "evidence": "...", "score": 0 }},
    "hallucination_absence": {{ "evidence": "...", "score": 0 }}
  }},
  "uniqueness": {{
    "term_differentiation":   {{ "evidence": "...", "score": 0 }},
    "internal_non_redundancy": {{ "evidence": "...", "score": 0 }}
  }},
  "structural_completeness": {{
    "required_sections_present": {{ "evidence": "...", "score": 0 }},
    "format_compliance":         {{ "evidence": "...", "score": 0 }}
  }}
}}"""


BASIC_SELF_CRITIQUE_PROMPT = """You are reviewing a handbook basic section for quality.

The term "{term}" is classified as type: {term_type}.

Review both KO and EN basic content for:
- missing mechanism after analogy
- cliche examples
- weak comparisons
- article-like tone in communication sections
- fabricated product claims
- cross-section repetition

## Output JSON
{{
  "ko_needs_improvement": true,
  "en_needs_improvement": true,
  "ko_improvements": [
    {{"section": "basic_ko_1_plain", "issue": "issue", "suggestion": "fix"}}
  ],
  "en_improvements": [
    {{"section": "basic_en_1_plain", "issue": "issue", "suggestion": "fix"}}
  ],
  "ko_score": 0,
  "en_score": 0
}}

If score >= 75, mark that language as not needing improvement."""


BASIC_QUALITY_CHECK_PROMPT = """You are evaluating a handbook term's basic section quality.

Term: "{term}" | Type: {term_type}

## Scoring Scale (applies to EVERY sub-score)

Use this 4-anchor scale on a 0-10 continuous range:
- **10**: Exemplary — criterion fully met with concrete evidence cited.
- **7**: Solid — criterion met with minor gaps.
- **4**: Weak — partial or surface-level adherence; notable gaps.
- **0**: Missing, contradicts the criterion, or fabricated.

## Required Output Format (per sub-score)

For EVERY sub-score you MUST provide BOTH:
1. `evidence`: Quote or describe SPECIFIC content observed (cite section heading or exact phrase). Empty evidence is not acceptable — if you find nothing, say so explicitly.
2. `score`: 0-10 integer using the scale above, grounded in the evidence you just cited.

Do NOT output any total or subtotal — code computes aggregates from sub-scores.
Do NOT hedge ("probably", "seems", "might") — anchor each score to concrete evidence.
Do NOT invent sections that aren't in the content.

## Sub-dimensions (10 sub-scores)

### Engagement
- **plain_language_clarity**: Jargon is explained on first use; no unexplained acronyms; reader-friendly phrasing
- **analogy_effectiveness**: Analogies clarify the mechanism (not just decorate); they map to the actual concept
- **reader_hook**: "Why you should care" is concrete and compelling, not generic ("this is important in AI")

### Accuracy
- **factual_correctness**: Claims verifiable against official docs or common technical knowledge
- **hallucination_absence**: No fabricated products, benchmarks, or entities (especially in "Examples & Analogies" section)
- **product_claim_accuracy**: Real products cited match their actual 2026 capabilities; no stale or fabricated product features

### Uniqueness
- **concept_clarity**: Reader leaves understanding THIS specific concept, not a generic AI summary
- **non_redundancy**: Sections add distinct information; no paraphrasing the same idea across sections

### Structural Completeness
- **required_sections_present**: All expected Basic sections present with substantive content
- **misconceptions_and_conversation**: `❌ Myth:`/`✅ Reality:` in misconceptions, conversation examples feel authentic (not generic)

## Output JSON

{{
  "engagement": {{
    "plain_language_clarity": {{ "evidence": "...", "score": 0 }},
    "analogy_effectiveness":  {{ "evidence": "...", "score": 0 }},
    "reader_hook":            {{ "evidence": "...", "score": 0 }}
  }},
  "accuracy": {{
    "factual_correctness":    {{ "evidence": "...", "score": 0 }},
    "hallucination_absence":  {{ "evidence": "...", "score": 0 }},
    "product_claim_accuracy": {{ "evidence": "...", "score": 0 }}
  }},
  "uniqueness": {{
    "concept_clarity":  {{ "evidence": "...", "score": 0 }},
    "non_redundancy":   {{ "evidence": "...", "score": 0 }}
  }},
  "structural_completeness": {{
    "required_sections_present":       {{ "evidence": "...", "score": 0 }},
    "misconceptions_and_conversation": {{ "evidence": "...", "score": 0 }}
  }}
}}"""
