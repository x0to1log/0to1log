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
        "ai_company_ecosystem_actor",
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
    "openai": {"type": "product_platform_service", "subtype": "ai_company_ecosystem_actor", "intent": ["compare", "understand"], "volatility": "fast-changing"},
    "anthropic": {"type": "product_platform_service", "subtype": "ai_company_ecosystem_actor", "intent": ["compare", "understand"], "volatility": "fast-changing"},
    "nvidia": {"type": "product_platform_service", "subtype": "ai_company_ecosystem_actor", "intent": ["compare", "understand"], "volatility": "fast-changing"},
    "mistral ai": {"type": "product_platform_service", "subtype": "ai_company_ecosystem_actor", "intent": ["compare", "understand"], "volatility": "fast-changing"},
    "xai": {"type": "product_platform_service", "subtype": "ai_company_ecosystem_actor", "intent": ["compare", "understand"], "volatility": "fast-changing"},
    "cohere": {"type": "product_platform_service", "subtype": "ai_company_ecosystem_actor", "intent": ["compare", "understand"], "volatility": "fast-changing"},
    "google deepmind": {"type": "product_platform_service", "subtype": "ai_company_ecosystem_actor", "intent": ["compare", "understand"], "volatility": "fast-changing"},
    "deepmind": {"type": "product_platform_service", "subtype": "ai_company_ecosystem_actor", "intent": ["compare", "understand"], "volatility": "fast-changing"},
    "pytorch": {"type": "library_framework_sdk", "intent": ["build", "compare"], "volatility": "evolving"},
    "gpu": {"type": "hardware_runtime_infra", "subtype": "accelerator_hardware", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "graphics processing unit": {"type": "hardware_runtime_infra", "subtype": "accelerator_hardware", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "llm": {"type": "model_algorithm_family", "intent": ["understand", "compare"], "volatility": "fast-changing"},
    "large language model": {"type": "model_algorithm_family", "intent": ["understand", "compare"], "volatility": "fast-changing"},
    "large language models": {"type": "model_algorithm_family", "intent": ["understand", "compare"], "volatility": "fast-changing"},
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
    "ai agent": {"type": "foundational_concept", "intent": ["understand", "compare"], "volatility": "fast-changing"},
    "ai agents": {"type": "foundational_concept", "intent": ["understand", "compare"], "volatility": "fast-changing"},
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
    "tool use": {"type": "capability_feature_spec", "intent": ["build", "compare"], "volatility": "fast-changing"},
    "multimodal": {"type": "capability_feature_spec", "intent": ["compare", "understand"], "volatility": "fast-changing"},
    "f1 score": {"type": "metric_benchmark", "subtype": "scalar_metric", "intent": ["evaluate", "understand"], "volatility": "stable"},
    "perplexity": {"type": "metric_benchmark", "subtype": "scalar_metric", "intent": ["evaluate", "understand"], "volatility": "stable"},
    "mmlu": {"type": "metric_benchmark", "subtype": "benchmark_suite", "intent": ["evaluate", "compare"], "volatility": "evolving"},
    "humaneval": {"type": "metric_benchmark", "subtype": "benchmark_suite", "intent": ["evaluate", "compare"], "volatility": "evolving"},
    "hallucination": {"type": "problem_failure_mode", "intent": ["debug", "understand"], "volatility": "evolving"},
    "prompt injection": {"type": "problem_failure_mode", "intent": ["debug", "build"], "volatility": "fast-changing"},
    "openai api": {"type": "product_platform_service", "subtype": "model_api_service", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "anthropic api": {"type": "product_platform_service", "subtype": "model_api_service", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "claude": {"type": "product_platform_service", "subtype": "model_api_service", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "gemini": {"type": "product_platform_service", "subtype": "model_api_service", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "gemini api": {"type": "product_platform_service", "subtype": "model_api_service", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "bedrock": {"type": "product_platform_service", "subtype": "managed_ai_cloud_platform", "intent": ["compare", "build"], "volatility": "fast-changing"},
    "amazon bedrock": {"type": "product_platform_service", "subtype": "managed_ai_cloud_platform", "intent": ["compare", "build"], "volatility": "fast-changing"},
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
    "ai agent": {
        "preferred_code_mode": "no-code",
        "advanced_focus_guide": (
            "## AI Agent Practical System Focus Guide\n"
            "- Center the advanced explanation on the runtime loop: goal intake -> planning or routing -> tool/action proposal "
            "-> host/runtime validation -> execution -> observation feedback -> stopping or escalation.\n"
            "- Distinguish workflow from agent: workflows follow predefined code paths; agents dynamically direct process "
            "and tool usage within host-imposed boundaries.\n"
            "- Treat the orchestrator, tool boundary, memory/state, permissions, sandbox, observability, and human approval "
            "as first-class engineering concerns.\n"
            "- Explain why agents cost more and fail differently than a single LLM call, RAG pipeline, or deterministic workflow.\n"
            "- Do not center POMDP, policy notation, reward functions, or academic taxonomy. Mention formalism only as a short aside "
            "if it improves an engineering decision.\n"
            "- In pitfalls, prioritize autonomy scope creep, missing stop conditions, unsafe tool permissions, weak evals, "
            "state drift, compounding tool errors, and poor audit trails."
        ),
        "code_contract_guide": (
            "## AI Agent Operational Review Procedure\n"
            "- Use adv_*_3_code as an operational review procedure, not fenced code.\n"
            "- KO and EN should describe the same review contract: scope, allowed tools, permission gates, sandbox boundary, "
            "state/memory rules, stop conditions, evaluation signals, and escalation path.\n"
            "- Do not output SDK snippets or a long runnable framework wrapper for this term."
        ),
        "reference_context": (
            "## Curated AI Agent Reference Materials\n\n"
            "### [1] Building effective agents - Anthropic\n"
            "URL: https://www.anthropic.com/engineering/building-effective-agents\n"
            "Practical engineering guide distinguishing workflows from agents, emphasizing simple composable patterns, "
            "tool use, environmental feedback, stopping conditions, guardrails, and cost/latency tradeoffs.\n\n"
            "### [2] A practical guide to building agents - OpenAI\n"
            "URL: https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/\n"
            "Practical agent-building guide focused on when to use agents, orchestration, tools, evaluation, handoffs, "
            "guardrails, and deployment concerns.\n\n"
            "### [3] What are AI agents? - Google Cloud\n"
            "URL: https://cloud.google.com/discover/what-are-ai-agents\n"
            "Provider documentation-style overview defining AI agents through goal pursuit, reasoning, actions, tool use, "
            "and autonomy levels, with examples and implementation considerations.\n\n"
            "### [4] Position Paper: Agent AI Towards a Holistic Intelligence - Microsoft Research\n"
            "URL: https://www.microsoft.com/en-us/research/wp-content/uploads/2024/02/Agent_AI_position.pdf\n"
            "Research position paper connecting agent AI to autonomy, planning, memory, tool use, interaction, and evaluation.\n\n"
            "### [5] Agentic Artificial Intelligence (AI): Architectures, Taxonomies, and Evaluation of Large Language Model Agents\n"
            "URL: https://arxiv.org/abs/2601.12560\n"
            "Survey-style taxonomy for LLM agents across perception, brain/planning, action, tool use, collaboration, "
            "and evaluation. Use as taxonomy support, not as the main writing style."
        ),
        "references_en": [
            {
                "title": "Building effective agents",
                "authors": "Anthropic",
                "venue": "Anthropic Engineering",
                "type": "blog",
                "url": "https://www.anthropic.com/engineering/building-effective-agents",
                "tier": "primary",
                "annotation": "Practical distinction between workflows and agents, with runtime loops, tools, guardrails, and stopping conditions.",
            },
            {
                "title": "A practical guide to building agents",
                "authors": "OpenAI",
                "venue": "OpenAI Guides",
                "type": "blog",
                "url": "https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/",
                "tier": "primary",
                "annotation": "Practical agent-building guidance covering orchestration, tools, evaluation, handoffs, and guardrails.",
            },
            {
                "title": "What are AI agents?",
                "authors": "Google Cloud",
                "venue": "Google Cloud Discover",
                "type": "docs",
                "url": "https://cloud.google.com/discover/what-are-ai-agents",
                "tier": "primary",
                "annotation": "Provider overview of agent goals, reasoning, action, tool use, autonomy, and implementation considerations.",
            },
            {
                "title": "Position Paper: Agent AI Towards a Holistic Intelligence",
                "authors": "Microsoft Research",
                "venue": "Microsoft Research",
                "type": "paper",
                "url": "https://www.microsoft.com/en-us/research/wp-content/uploads/2024/02/Agent_AI_position.pdf",
                "tier": "secondary",
                "annotation": "Research framing for agent autonomy, planning, interaction, memory, tool use, and evaluation.",
            },
            {
                "title": "Agentic Artificial Intelligence (AI): Architectures, Taxonomies, and Evaluation of Large Language Model Agents",
                "authors": "arXiv",
                "venue": "arXiv",
                "type": "paper",
                "url": "https://arxiv.org/abs/2601.12560",
                "tier": "secondary",
                "annotation": "Taxonomy support for LLM agent components, architectures, and evaluation dimensions.",
            },
        ],
        "references_ko": [
            {
                "title": "Building effective agents",
                "authors": "Anthropic",
                "venue": "Anthropic Engineering",
                "type": "blog",
                "url": "https://www.anthropic.com/engineering/building-effective-agents",
                "tier": "primary",
                "annotation": "워크플로우와 에이전트를 구분하고, 도구 사용·피드백 루프·가드레일·중단 조건을 실무 관점에서 설명한다.",
            },
            {
                "title": "A practical guide to building agents",
                "authors": "OpenAI",
                "venue": "OpenAI Guides",
                "type": "blog",
                "url": "https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/",
                "tier": "primary",
                "annotation": "오케스트레이션, 도구, 평가, 핸드오프, 가드레일을 포함한 에이전트 구축 실무 가이드.",
            },
            {
                "title": "What are AI agents?",
                "authors": "Google Cloud",
                "venue": "Google Cloud Discover",
                "type": "docs",
                "url": "https://cloud.google.com/discover/what-are-ai-agents",
                "tier": "primary",
                "annotation": "목표 추구, 추론, 행동, 도구 사용, 자율성 수준을 중심으로 AI 에이전트 개념을 설명한다.",
            },
            {
                "title": "Position Paper: Agent AI Towards a Holistic Intelligence",
                "authors": "Microsoft Research",
                "venue": "Microsoft Research",
                "type": "paper",
                "url": "https://www.microsoft.com/en-us/research/wp-content/uploads/2024/02/Agent_AI_position.pdf",
                "tier": "secondary",
                "annotation": "에이전트 자율성, 계획, 상호작용, 메모리, 도구 사용, 평가를 연구 관점에서 정리한다.",
            },
            {
                "title": "Agentic Artificial Intelligence (AI): Architectures, Taxonomies, and Evaluation of Large Language Model Agents",
                "authors": "arXiv",
                "venue": "arXiv",
                "type": "paper",
                "url": "https://arxiv.org/abs/2601.12560",
                "tier": "secondary",
                "annotation": "LLM 에이전트의 구성요소, 아키텍처, 평가 차원을 분류하는 taxonomy 보조 자료.",
            },
        ],
    },
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
    "tool use": {
        "preferred_code_mode": "pseudocode",
        "advanced_focus_guide": (
            "## Tool Use Execution Boundary Guide\n"
            "- Center the explanation on the runtime contract: tool registry -> schema exposure -> model proposes "
            "tool name and arguments -> host validates -> host executes -> tool result is handed back to the model.\n"
            "- State the responsibility split explicitly: the model proposes; the host executes. The application owns "
            "argument validation, authorization, sandboxing, retries, side-effect control, and failure handling.\n"
            "- Make the term boundary explicit: Function Calling is an API pattern for structured tool calls; Tool Use is "
            "the broader runtime capability and design contract across function calling, hosted tools, and MCP-style tools.\n"
            "- Keep the Advanced body glossary-level: explain concept boundaries, runtime responsibilities, failure modes, "
            "and decision criteria before implementation minutiae.\n"
            "- Do not make stop_reason, pause_turn, billing metadata, or provider-specific trace fields the backbone of "
            "the section; mention them only as examples when useful.\n"
            "- In tradeoffs, compare Tool Use against plain prompting, RAG, hardcoded workflows, and full AI agents.\n"
            "- In pitfalls, prioritize wrong tool choice, malformed arguments, unsafe side effects, stale tool catalogs, "
            "prompt-injected tool outputs, and missing result validation.\n"
            "- Avoid drifting into benchmark taxonomy. Benchmarks may be mentioned only as secondary evaluation context, "
            "not as the section structure."
        ),
        "code_contract_guide": (
            "## Tool Use Code Contract\n"
            "- KO and EN code sections must implement the same tool-use contract.\n"
            "- Use the same pseudocode steps in both locales; translate only surrounding explanation.\n"
            "- Use compact pseudocode or Python-like code showing: tool registry, schema/argument validation, permission check, "
            "host execution boundary, tool result handoff, unknown tool handling, bad argument handling, and execution failure handling.\n"
            "- Do not use provider SDK boilerplate. Locale differences belong in explanatory prose, not the core control flow."
        ),
        "reference_context": (
            "## Curated Tool Use Reference Materials\n\n"
            "### [1] Tool use with Claude - Anthropic\n"
            "URL: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview\n"
            "Official overview of Claude tool use, tool definitions, client-side tool implementation, and tool result loops.\n\n"
            "### [2] How to implement tool use - Anthropic\n"
            "URL: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use\n"
            "Implementation guide covering tool schemas, tool_use blocks, client execution, and returning tool results.\n\n"
            "### [3] Function calling - OpenAI API\n"
            "URL: https://platform.openai.com/docs/guides/function-calling\n"
            "Official guide describing function/tool calling, JSON-schema function tools, custom tools, and host-side execution.\n\n"
            "### [4] Function calling with the Gemini API - Google AI for Developers\n"
            "URL: https://ai.google.dev/gemini-api/docs/function-calling\n"
            "Official guide covering function declarations, model-returned function calls, automatic function calling, and OpenAPI-compatible schemas.\n\n"
            "### [5] Tools - Model Context Protocol\n"
            "URL: https://modelcontextprotocol.io/specification/draft/server/tools\n"
            "Official MCP specification page describing tools as executable functionality exposed by servers and invoked by clients."
        ),
        "references_en": [
            {
                "title": "Tool use with Claude",
                "authors": "Anthropic",
                "venue": "Anthropic Docs",
                "type": "docs",
                "url": "https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview",
                "tier": "primary",
                "annotation": "Official tool-use overview covering tool definitions, client execution, and result loops.",
            },
            {
                "title": "How to implement tool use",
                "authors": "Anthropic",
                "venue": "Anthropic Docs",
                "type": "docs",
                "url": "https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use",
                "tier": "primary",
                "annotation": "Implementation guidance for tool schemas, tool_use blocks, host execution, and returning results.",
            },
            {
                "title": "Function calling",
                "authors": "OpenAI",
                "venue": "OpenAI API Docs",
                "type": "docs",
                "url": "https://platform.openai.com/docs/guides/function-calling",
                "tier": "primary",
                "annotation": "Official function/tool calling guide for schema-defined tools and host-side execution.",
            },
            {
                "title": "Function calling with the Gemini API",
                "authors": "Google",
                "venue": "Google AI for Developers",
                "type": "docs",
                "url": "https://ai.google.dev/gemini-api/docs/function-calling",
                "tier": "primary",
                "annotation": "Official function declaration and model-returned function call guide for Gemini.",
            },
            {
                "title": "Tools",
                "authors": "Model Context Protocol",
                "venue": "MCP Specification",
                "type": "docs",
                "url": "https://modelcontextprotocol.io/specification/draft/server/tools",
                "tier": "primary",
                "annotation": "Official MCP specification for executable tools exposed by servers and invoked by clients.",
            },
        ],
        "references_ko": [
            {
                "title": "Tool use with Claude",
                "authors": "Anthropic",
                "venue": "Anthropic Docs",
                "type": "docs",
                "url": "https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview",
                "tier": "primary",
                "annotation": "도구 정의, 클라이언트 실행 책임, tool result 루프를 설명하는 Anthropic 공식 개요.",
            },
            {
                "title": "How to implement tool use",
                "authors": "Anthropic",
                "venue": "Anthropic Docs",
                "type": "docs",
                "url": "https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use",
                "tier": "primary",
                "annotation": "도구 스키마, tool_use 블록, 호스트 실행, 결과 반환을 다루는 구현 가이드.",
            },
            {
                "title": "Function calling",
                "authors": "OpenAI",
                "venue": "OpenAI API Docs",
                "type": "docs",
                "url": "https://platform.openai.com/docs/guides/function-calling",
                "tier": "primary",
                "annotation": "스키마 기반 함수/도구 호출과 애플리케이션 실행 경계를 설명하는 공식 문서.",
            },
            {
                "title": "Function calling with the Gemini API",
                "authors": "Google",
                "venue": "Google AI for Developers",
                "type": "docs",
                "url": "https://ai.google.dev/gemini-api/docs/function-calling",
                "tier": "primary",
                "annotation": "Gemini의 함수 선언, 모델 반환 functionCall, OpenAPI 호환 스키마를 다루는 공식 가이드.",
            },
            {
                "title": "Tools",
                "authors": "Model Context Protocol",
                "venue": "MCP Specification",
                "type": "docs",
                "url": "https://modelcontextprotocol.io/specification/draft/server/tools",
                "tier": "primary",
                "annotation": "서버가 노출하고 클라이언트가 호출하는 실행 가능한 도구를 정의하는 MCP 공식 스펙.",
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
        "preferred_code_mode": "pseudocode",
        "advanced_focus_guide": (
            "## Context Window Focus Guide\n"
            "- Center the advanced explanation on token budget, input/output accounting, overflow behavior, "
            "truncation, compaction, prompt layout, RAG tradeoff, and attention cost.\n"
            "- Explain that larger windows increase capacity but do not guarantee recall or answer quality.\n"
            "- Treat extended thinking, tool_result handling, and signed blocks as a minor provider-specific example only; "
            "never let them become the main mechanism, code path, or pitfall list.\n"
            "- Avoid named model versions, benchmark scores, or paper-specific numbers unless they appear in the final references.\n"
            "- In tradeoffs, compare long context with RAG, summarization, sliding-window processing, and deterministic pruning."
        ),
        "code_contract_guide": (
            "## Context Window Code Contract\n"
            "- KO and EN code sections must implement the same system model and same logical steps.\n"
            "- Use provider-neutral pseudocode or compact Python; do not use Claude-specific signed thinking blocks, "
            "Kimi strategies, or provider SDK boilerplate.\n"
            "- The code should expose these logical functions: preflight_budget, reserve_output_tokens, "
            "compact_history, and fail_fast.\n"
            "- Include exactly two failure paths: budget_overflow and compaction_loss_risk.\n"
            "- Locale differences belong in surrounding prose, not in the core code path."
        ),
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
    "foundational_concept": (
        "Explain the concept precisely, then decompose it into component responsibilities, "
        "runtime boundaries, and practical decision points. For AI/LLM concepts, Do not lead "
        "with research formalism; show how the idea changes system design, evaluation, or operations."
    ),
    "problem_failure_mode": "Lead with symptoms, root causes, detection, and mitigation.",
    "model_algorithm_family": "Explain data flow, complexity, bottlenecks, and what problem the design solves.",
    "training_optimization_method": "Explain when the method is applied, major variants, and configuration tradeoffs.",
    "retrieval_knowledge_system": "Organize around ingestion, chunking, indexing, retrieval, reranking, grounding, and evaluation.",
    "system_workflow_pattern": (
        "Describe components, request flow, failure handling, and observability as a glossary deep-dive, "
        "not a framework implementation runbook. Keep provider-specific traces, retries, and SDK fields as "
        "small examples unless they define the workflow."
    ),
    "data_storage_indexing_system": "Explain storage model, indexing path, read path, and scaling constraints.",
    "protocol_format_data_structure": "Explain structure, flow, compatibility, and safety.",
    "capability_feature_spec": (
        "Explain what the feature label means operationally and where people over-interpret it. "
        "Center advanced sections on the host/runtime boundary, validation responsibilities, execution limits, "
        "failure handling, and when the capability should be replaced by a simpler deterministic workflow. "
        "Frame the section as a glossary deep-dive, not a provider implementation runbook; clarify adjacent "
        "term boundaries before provider-specific details. "
        "Do not turn capability/spec terms into a provider documentation inventory; use at most two provider examples "
        "as evidence, not as the section structure. Do not include model-style parameter/FLOP/spec tables unless the "
        "term itself is a model, benchmark, product, or hardware system. Keep code to a concise code capsule that "
        "shows only the input/schema, validation, control loop, execution boundary, and failure path instead of a "
        "full framework wrapper."
    ),
    "metric_benchmark": "Explain what the number means before formulas, then misuse cases and alternatives.",
    "product_platform_service": "Explain who it is for, what surface it exposes, pricing/lock-in, and migration cost.",
    "library_framework_sdk": "Explain developer abstractions, idiomatic usage, and integration constraints.",
    "hardware_runtime_infra": "Explain workload fit, throughput/latency tradeoffs, memory model, and deployment cost.",
}

SUBTYPE_DEPTH_GUIDES: dict[tuple[str, str], str] = {
    ("foundational_concept", "reasoning_method"): "Emphasize the direct method definition, what the reasoning trace is doing, and where adjacent reasoning discourse should be excluded.",
    ("foundational_concept", "policy_discourse"): "Separate the technical definition from the policy meaning. Do not collapse governance framing, safety framing, and capability framing into one blurry explanation.",
    ("foundational_concept", "standard_regulation"): "Emphasize scope, management system requirements, audit boundaries, and what teams must operationalize to comply.",
    ("product_platform_service", "ai_company_ecosystem_actor"): "Treat the company as an ecosystem actor, not a generic company profile. Emphasize product/API surface, model or hardware portfolio, developer adoption path, ecosystem dependencies, governance posture, switching cost, and where news readers encounter the name.",
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
- For capability/spec terms, adv_*_3_code should be a concise code capsule, not a long tutorial or full production harness.
- Omit non-applicable sections instead of using placeholders.

## Advanced Practical Depth Direction
- Advanced means stronger engineering judgment, not academic formalism by default.
- Prefer design review depth: runtime boundaries, component responsibilities, data/control flow, validation gates, failure handling, evaluation, and observability.
- Use formulas only when the term is a metric, loss, math/statistics concept, or algorithm with a standard formula.
- For system/concept terms, prefer architecture diagrams, component tables, decision-boundary maps, failure-path maps, and review checklists.
- Research formalism such as POMDP, policy pi, or conditional distributions may appear only as a brief aside if directly useful; do not make it the section backbone.
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
    ("product_platform_service", "ai_company_ecosystem_actor"): ["docs", "community", "benchmark"],
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
    ("product_platform_service", "ai_company_ecosystem_actor"): "company official products models api ecosystem partnerships developer platform governance competitive position",
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
    ("foundational_concept", "understand"): (
        "Lead with intuition, then mechanism. Do not rush into implementation. For AI system concepts, "
        "move into runtime/component boundaries after the intuition instead of making academic formalism the main explanation."
    ),
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
    ("product_platform_service", "ai_company_ecosystem_actor", "compare"): "Lead with the company's role in the AI stack, product/model/API surface, adoption criteria, ecosystem dependencies, governance and regulatory risk, and switching cost. Do not write a corporate biography.",
    ("product_platform_service", "ai_company_ecosystem_actor", "understand"): "Lead with why this company appears in AI news, then connect its products, models, infrastructure, partnerships, and developer surface. Avoid founder-story filler.",
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


DEFAULT_ARTIFACT_POLICY: dict[str, str] = {
    "code_mode": "contextual",
    "specs_mode": "off",
    "artifact_kind": "architecture or workflow artifact",
    "adv2_guidance": (
        "Use the artifact that best explains the term: formula only for terms with a standard mathematical "
        "definition; otherwise use a control-flow diagram, architecture table, taxonomy, or decision matrix."
    ),
    "code_guidance": (
        "If code_mode is real-code or pseudocode, keep adv_*_3_code to one compact implementation capsule. "
        "If code_mode is no-code, use adv_*_3_code for an operational review procedure without fenced code."
    ),
    "specificity_guidance": (
        "Use type-appropriate concrete details. Do not force parameter counts, FLOPs, or benchmark scores "
        "when the term is not a model, benchmark, product, or hardware system."
    ),
}

TYPE_ARTIFACT_POLICIES: dict[str, dict[str, str]] = {
    "foundational_concept": {
        "code_mode": "pseudocode",
        "artifact_kind": "runtime concept map, component table, or mechanism flow",
        "adv2_guidance": (
            "Prefer component tables, runtime loop diagrams, decision-boundary maps, or failure-path maps. "
            "Use mathematical formalism only as a brief aside when it directly improves engineering judgment; "
            "do not center POMDP/policy notation for AI system concepts."
        ),
        "code_guidance": (
            "Use compact pseudocode for runtime/review loops: allowed capabilities, validation, permission, "
            "failure handling, logging/audit. Avoid SDK tutorials and long runnable examples."
        ),
    },
    "problem_failure_mode": {
        "code_mode": "no-code",
        "artifact_kind": "incident taxonomy / detection workflow / mitigation matrix",
        "adv2_guidance": (
            "Use an incident taxonomy, detection workflow, mitigation matrix, or failure tree. "
            "Do not invent formulas unless the references define one."
        ),
        "code_guidance": (
            "Use adv_*_3_code as an operational triage or review procedure. "
            "Do NOT output fenced code, SDK calls, or pretend implementations."
        ),
        "specificity_guidance": "Use concrete failure signals, incident classes, monitoring checks, controls, and mitigation boundaries.",
    },
    "metric_benchmark": {
        "code_mode": "no-code",
        "artifact_kind": "formula interpretation and evaluation protocol",
        "adv2_guidance": "Use the metric formula when standard, then explain averaging, thresholds, and misuse cases.",
        "code_guidance": "Use adv_*_3_code as an evaluation checklist or scoring protocol unless a tiny calculation is essential.",
        "specs_mode": "optional",
    },
    "model_algorithm_family": {
        "code_mode": "pseudocode",
        "artifact_kind": "architecture diagram and algorithm flow",
        "adv2_guidance": "Use architecture diagrams, tensor/data-flow tables, and standard equations when they are core to the model.",
        "specs_mode": "off",
    },
    "training_optimization_method": {
        "code_mode": "pseudocode",
        "artifact_kind": "optimization objective and training loop",
        "adv2_guidance": "Use the objective/loss when standard; otherwise show the training loop and configuration levers.",
    },
    "retrieval_knowledge_system": {
        "code_mode": "pseudocode",
        "artifact_kind": "retrieval pipeline and evaluation workflow",
        "adv2_guidance": "Use ingestion -> chunking -> indexing -> retrieval -> reranking -> grounding flow diagrams.",
    },
    "system_workflow_pattern": {
        "code_mode": "pseudocode",
        "artifact_kind": "runtime workflow and failure-handling path",
        "adv2_guidance": "Use request/control-flow diagrams, state transitions, and observability tables.",
    },
    "data_storage_indexing_system": {
        "code_mode": "contextual",
        "artifact_kind": "storage/index/read-write path",
        "adv2_guidance": "Use storage layout, index path, query path, and scaling tables over abstract math.",
    },
    "protocol_format_data_structure": {
        "code_mode": "contextual",
        "artifact_kind": "schema, handshake, or invariant table",
        "adv2_guidance": "Use schema diagrams, protocol sequence, invariants, and compatibility tables.",
    },
    "capability_feature_spec": {
        "code_mode": "contextual",
        "artifact_kind": "runtime boundary and capability contract",
        "adv2_guidance": "Use control/data-flow, responsibility boundaries, validation rules, and capability limits.",
    },
    "product_platform_service": {
        "code_mode": "contextual",
        "artifact_kind": "API surface, pricing/limit model, and migration constraints",
        "adv2_guidance": "Use official surface tables, rate/pricing semantics, version sensitivity, and lock-in tradeoffs.",
        "specs_mode": "optional",
    },
    "library_framework_sdk": {
        "code_mode": "contextual",
        "artifact_kind": "developer abstraction and integration contract",
        "adv2_guidance": "Use core abstraction diagrams, lifecycle tables, and compatibility constraints.",
    },
    "hardware_runtime_infra": {
        "code_mode": "contextual",
        "artifact_kind": "runtime config, memory model, and latency/throughput table",
        "adv2_guidance": "Use deployment flags, memory/throughput/latency tables, and workload-fit matrices.",
        "specs_mode": "optional",
    },
}

SUBTYPE_ARTIFACT_POLICIES: dict[tuple[str, str], dict[str, str]] = {
    ("foundational_concept", "policy_discourse"): {
        "code_mode": "no-code",
        "artifact_kind": "definition boundary, stakeholder map, and governance claim matrix",
        "adv2_guidance": "Use a scope matrix that separates technical, policy, and safety claims.",
        "code_guidance": "Use adv_*_3_code as a review procedure for classifying claims; do NOT output fenced code.",
    },
    ("foundational_concept", "standard_regulation"): {
        "code_mode": "no-code",
        "artifact_kind": "control objective and audit workflow",
        "adv2_guidance": "Use requirement/control/audit-evidence tables instead of formulas or code.",
        "code_guidance": "Use adv_*_3_code as an implementation-readiness checklist; do NOT output fenced code.",
    },
    ("product_platform_service", "ecosystem_platform"): {
        "code_mode": "no-code",
        "artifact_kind": "ecosystem surface and workflow map",
        "adv2_guidance": "Use asset/workflow/switching-cost tables; avoid SDK snippets unless the term is specifically an SDK.",
        "code_guidance": "Use adv_*_3_code as an adoption or migration review checklist; do NOT output fenced code.",
    },
    ("product_platform_service", "ai_company_ecosystem_actor"): {
        "code_mode": "no-code",
        "specs_mode": "off",
        "artifact_kind": "ecosystem role map, adoption matrix, and switching-risk checklist",
        "adv2_guidance": (
            "Use a company role map: product/model/API surface, developer workflow, infrastructure dependencies, "
            "partnerships, governance posture, and competitive alternatives. Do not use formulas or SDK code."
        ),
        "code_guidance": (
            "Use adv_*_3_code as a vendor/adoption review checklist: workload fit, API/model coverage, "
            "data governance, pricing exposure, lock-in, migration path, and incident/availability risk. "
            "Do NOT output fenced code."
        ),
    },
}

CATEGORY_ARTIFACT_POLICIES: dict[str, dict[str, str]] = {
    "safety-ethics": {
        "code_mode": "no-code",
        "artifact_kind": "incident taxonomy / detection workflow / mitigation matrix",
        "adv2_guidance": (
            "Use incident taxonomy, detection workflow, mitigation matrix, governance boundary, or control evidence table. "
            "Do not force formulas, benchmark tables, or code."
        ),
        "code_guidance": "Use adv_*_3_code as an operational review procedure. Do NOT output fenced code.",
        "specificity_guidance": "Use concrete harms, attack surfaces, controls, incident signals, and review criteria.",
    },
    "math-statistics": {
        "artifact_kind": "formula, derivation, and numerical example",
        "adv2_guidance": "Use formulas and derivations when standard, paired with a small numerical interpretation.",
    },
    "infra-hardware": {
        "artifact_kind": "runtime config, profiling output, and capacity table",
        "adv2_guidance": "Use deployment/runtime artifacts such as flags, memory layout, throughput/latency tables, and bottleneck maps.",
    },
}


def get_artifact_policy(
    term_type: str,
    subtype: str | None = None,
    category: str | None = None,
) -> dict[str, str]:
    policy = dict(DEFAULT_ARTIFACT_POLICY)
    policy.update(TYPE_ARTIFACT_POLICIES.get(term_type, {}))
    policy.update(SUBTYPE_ARTIFACT_POLICIES.get((term_type, subtype or ""), {}))
    policy.update(CATEGORY_ARTIFACT_POLICIES.get(category or "", {}))
    return policy


def build_artifact_policy_block(
    term_type: str,
    subtype: str | None = None,
    category: str | None = None,
    code_mode_hint: str | None = None,
) -> str:
    policy = get_artifact_policy(term_type, subtype, category)
    code_mode = (code_mode_hint or policy.get("code_mode") or "contextual").strip()
    specs_mode = policy.get("specs_mode", "off")
    specs_rule = (
        "Do NOT output adv_ko_specs or adv_en_specs."
        if specs_mode == "off"
        else "Output adv_ko_specs / adv_en_specs only when official references provide concrete values; otherwise use not_published."
    )
    code_rule = (
        "Do NOT output fenced code. Use adv_*_3_code as an operational procedure, review checklist, or implementation boundary."
        if code_mode == "no-code"
        else "Use exactly one compact fenced code or pseudocode capsule in adv_*_3_code."
    )
    return (
        f"## Artifact Policy ({format_term_type_label(term_type, subtype)}; category={category or 'none'})\n"
        "This block overrides generic Advanced instructions whenever they conflict.\n"
        f"- Code mode: {code_mode}. {code_rule}\n"
        f"- Specs mode: {specs_mode}. {specs_rule}\n"
        f"- Preferred technical artifact: {policy['artifact_kind']}.\n"
        f"- adv_*_2_formulas guidance: {policy['adv2_guidance']}\n"
        f"- adv_*_3_code guidance: {policy['code_guidance']}\n"
        f"- Concrete specificity: {policy['specificity_guidance']}\n"
        "- Do not force parameter counts, FLOPs, benchmark scores, formulas, or SDK snippets when this policy says a taxonomy, workflow, matrix, or checklist is the more faithful artifact."
    )


CATEGORY_CONTEXT: dict[str, dict[str, str]] = {
    "cs-fundamentals": {
        "vocabulary": "data structure, algorithm, protocol, runtime, API, compiler, interpreter, hash table, HTTP, thread, process, stack, heap",
        "quality_signals": "Use concrete programming scenarios and official specs where relevant.",
        "anti_patterns": "Do not force AI framing when the concept is fundamentally general CS.",
        "reference_style": "Prefer MDN, RFCs, W3C, language specifications, and official docs.",
        "code_guide": "Use standard library or mainstream framework examples before niche tools.",
        "basic_focus": "Explain the general CS idea first, then connect to AI only when the term genuinely affects AI systems.",
        "advanced_focus": "Cover invariants, complexity, protocol roles, runtime behavior, compatibility, and security boundaries.",
        "good_artifacts": "operation table, protocol sequence, invariant checklist, complexity comparison, minimal standard-library snippet.",
        "forbidden_patterns": "Do not turn every CS term into an LLM term; do not use AI marketing examples as the primary explanation.",
        "example_style": "Use compiler/runtime/API/debugging scenarios with concrete inputs and failure modes.",
    },
    "math-statistics": {
        "vocabulary": "proof, theorem, estimator, variance, convergence, expectation, likelihood, posterior, prior",
        "quality_signals": "Lead with intuition before formulas. Use concrete numerical examples.",
        "anti_patterns": "Do not reduce the concept to only AI usage.",
        "reference_style": "Use textbook notation and foundational sources when available.",
        "code_guide": "Pair math explanation with numpy/scipy examples when code helps.",
        "basic_focus": "Start with the decision or uncertainty problem the concept helps solve before notation.",
        "advanced_focus": "Move from assumptions to formula, interpretation, edge cases, and common misuse in ML evaluation or training.",
        "good_artifacts": "derivation, small numerical example, assumption table, misuse matrix, short numpy/scipy check.",
        "forbidden_patterns": "Do not present formulas without explaining symbols and interpretation; do not reduce the term to a single AI anecdote.",
        "example_style": "Use small numbers, distributions, thresholds, or model-evaluation cases where the reader can verify the intuition.",
    },
    "ml-fundamentals": {
        "vocabulary": "feature, label, overfitting, regularization, cross-validation, hyperparameter, precision, recall, ROC-AUC",
        "quality_signals": "Show full train/evaluate context and compare credible alternatives.",
        "anti_patterns": "Do not treat classical ML as obsolete by default.",
        "reference_style": "Use official library docs and foundational algorithm references.",
        "code_guide": "Prefer scikit-learn style examples for baseline implementations.",
        "basic_focus": "Explain the training/evaluation problem and where the concept appears in a normal ML workflow.",
        "advanced_focus": "Cover assumptions, data splits, metrics, leakage risks, hyperparameters, and production validation gates.",
        "good_artifacts": "train/evaluate pipeline, metric interpretation table, leakage checklist, scikit-learn style compact example.",
        "forbidden_patterns": "Do not frame classical ML as old or irrelevant; do not skip evaluation and deployment failure modes.",
        "example_style": "Use tabular, classification, ranking, or forecasting examples with explicit train/test consequences.",
    },
    "deep-learning": {
        "vocabulary": "tensor, gradient, backpropagation, layer, activation, learning rate, convolution, attention",
        "quality_signals": "Make tensor flow and compute tradeoffs explicit.",
        "anti_patterns": "Do not ignore memory, latency, or training-vs-inference differences.",
        "reference_style": "Use original papers and official implementation/docs when possible.",
        "code_guide": "Prefer PyTorch examples with clear shapes and data flow.",
        "basic_focus": "Explain what representation or optimization problem the neural component solves.",
        "advanced_focus": "Cover tensor shapes, forward/backward flow, memory cost, latency, scaling bottlenecks, and training-vs-inference differences.",
        "good_artifacts": "shape table, forward-pass diagram, loss/objective, PyTorch capsule, compute/memory tradeoff table.",
        "forbidden_patterns": "Do not describe only intuition; do not omit tensor dimensions, bottlenecks, or failure modes.",
        "example_style": "Use model blocks, tensor batches, gradients, and deployment constraints rather than generic AI examples.",
    },
    "llm-genai": {
        "vocabulary": "token, prompt, context window, alignment, agent, tool use, embedding, retrieval, fine-tuning",
        "quality_signals": "Use developer workflows, cost awareness, limitations, and clear responsibility boundaries.",
        "anti_patterns": "Avoid marketing language, vague capability claims, and model-only explanation for system behavior.",
        "reference_style": "Prefer official API docs, benchmark references, and current platform docs.",
        "code_guide": "Show practical API or orchestration patterns, then what the model proposes versus what the host/runtime/orchestrator executes.",
        "basic_focus": "Explain the user-facing capability, the hidden runtime mechanism, and the limitation people usually miss.",
        "advanced_focus": (
            "Cover prompt/context/tool/memory/permission/audit placement, host/runtime/orchestrator boundaries, "
            "tool and memory responsibility, evaluation, cost, latency, and provider portability."
        ),
        "good_artifacts": (
            "request flow, runtime loop, component responsibility table, boundary map, failure-path map, "
            "eval/observability checklist, cost/latency tradeoff matrix."
        ),
        "forbidden_patterns": (
            "Do not repeat platform marketing; do not imply capability labels guarantee reliability or correctness; "
            "do not use academic formalism as the backbone when a system boundary explanation is clearer."
        ),
        "example_style": "Use API workflows, RAG/tool/agent loops, and production failure cases with explicit constraints, permissions, and audit paths.",
    },
    "data-engineering": {
        "vocabulary": "pipeline, schema, partitioning, checkpoint, idempotency, lineage, throughput, latency, backfill",
        "quality_signals": "Discuss scaling, failure recovery, and maintenance cost.",
        "anti_patterns": "Do not treat all storage or indexing approaches as interchangeable.",
        "reference_style": "Prefer official architecture docs and versioned product documentation.",
        "code_guide": "Show data flow, then real integration snippets or configuration.",
        "basic_focus": "Explain what data moves, where it is stored, and what operational problem the system prevents.",
        "advanced_focus": "Cover schema evolution, idempotency, partitioning, consistency, recovery, lineage, and cost under scale.",
        "good_artifacts": "pipeline diagram, read/write path, schema contract, backfill checklist, failure-recovery matrix.",
        "forbidden_patterns": "Do not treat databases, indexes, queues, and pipelines as interchangeable; do not skip maintenance cost.",
        "example_style": "Use ingestion, backfill, checkpoint, streaming, and vector-index scenarios with concrete failure paths.",
    },
    "infra-hardware": {
        "vocabulary": "GPU, CUDA, kernel, throughput, latency, quantization, cluster, container, shard, replica",
        "quality_signals": "Use operational constraints, workload fit, and cost-aware comparisons.",
        "anti_patterns": "Do not explain only theory and skip deployment constraints.",
        "reference_style": "Use vendor docs, benchmarks, and deployment docs.",
        "code_guide": "Prefer deployment config, runtime flags, or profiling examples.",
        "basic_focus": "Explain which workload bottleneck this solves and what practical constraint remains.",
        "advanced_focus": "Cover memory model, throughput/latency, batching, kernel/runtime compatibility, deployment knobs, and cost.",
        "good_artifacts": "runtime config, profiling output, memory/latency table, workload-fit matrix, deployment checklist.",
        "forbidden_patterns": "Do not explain only theory; do not ignore cost, region/availability, compatibility, or operational limits.",
        "example_style": "Use serving, batch inference, GPU memory pressure, quantization, and runtime flag examples.",
    },
    "safety-ethics": {
        "vocabulary": "alignment, adversarial, bias, red teaming, audit, data poisoning, jailbreak, guardrail",
        "quality_signals": "Ground discussion in incidents, detection, and defenses.",
        "anti_patterns": "Avoid purely philosophical discussion when the term has technical mitigations.",
        "reference_style": "Use safety research, standards, and official guidance.",
        "code_guide": "Prefer concrete mitigation patterns, evaluators, and guardrail examples.",
        "basic_focus": "Explain what can go wrong, who is affected, and the first practical defense or governance response.",
        "advanced_focus": "Use threat model, incident timeline, control objective, detection signal, mitigation boundary, and residual risk.",
        "good_artifacts": "threat model, incident taxonomy, incident timeline, detection workflow, mitigation matrix, audit evidence table.",
        "forbidden_patterns": "Avoid purely philosophical framing; do not force code, formulas, or benchmark-style claims when controls and evidence are more relevant.",
        "example_style": "Use red-team findings, policy/control reviews, data or prompt attack paths, and post-incident remediation language.",
    },
    "products-platforms": {
        "vocabulary": "API, SDK, release, pricing, benchmark, migration, deprecation, rate limit, quota, SLA",
        "quality_signals": "Include version/date sensitivity, pricing, and alternatives.",
        "anti_patterns": "Do not repeat marketing claims without tradeoffs.",
        "reference_style": "Prefer official docs, changelogs, and pricing pages.",
        "code_guide": "Show real integration or API usage with version awareness.",
        "basic_focus": "Explain what the product/platform is, who adopts it, and the adoption reason without marketing language.",
        "advanced_focus": "Cover API surface, pricing units, rate limits, quotas, version/date sensitivity, lock-in, migration cost, and alternatives.",
        "good_artifacts": "API surface table, pricing/rate-limit table, migration checklist, lock-in matrix, version/date caveat list.",
        "forbidden_patterns": "Do not repeat vendor marketing; do not list features without tradeoffs, limits, or switching costs.",
        "example_style": "Use official docs/changelog/pricing-backed examples with explicit version/date and operational constraints.",
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
        f"<code_guide>{ctx['code_guide']}</code_guide>\n"
        f"<basic_focus>{ctx['basic_focus']}</basic_focus>\n"
        f"<advanced_focus>{ctx['advanced_focus']}</advanced_focus>\n"
        f"<good_artifacts>{ctx['good_artifacts']}</good_artifacts>\n"
        f"<forbidden_patterns>{ctx['forbidden_patterns']}</forbidden_patterns>\n"
        f"<example_style>{ctx['example_style']}</example_style>"
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
    ("product_platform_service", "ai_company_ecosystem_actor"): "Lead with why this company matters in the AI stack, then explain its product/model/API surface and where readers encounter it in news.",
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

## Bilingual Content Contract

The user message contains TWO parallel locale versions of the same term, labeled `## Korean (KO)` and `## English (EN)`. These are intentional translations of each other, not independent content. Apply these rules:

- **Same idea expressed in both KO and EN is NOT redundancy.** `internal_non_redundancy` measures repetition WITHIN each locale only — e.g., the same example paraphrased across multiple sections of `body_advanced_ko`. Cross-locale parallelism is expected and MUST NOT be penalized.
- **Score each sub-score as the weaker of the two locales.** If KO looks strong and EN looks weak on `mechanism_clarity`, the term as a whole is weak on that dimension — return the lower score. Rationale: a term that only works in one language isn't a good handbook entry.
- **Cite evidence with locale labels.** Always prefix evidence with `[KO]` or `[EN]` (e.g., `[KO] section 'Mechanism' contains specific parameter counts (175B, 12 layers)`). Never mix quotes from both locales in one evidence field.
- **If one locale is a placeholder** (`(no Korean content provided)` or similar), treat that locale as score 0 on all content-dependent sub-scores and mention the missing locale in the evidence.

## Sub-dimensions (9 sub-scores)

### Technical Depth
- **mechanism_clarity**: HOW the system works internally (data flow, algorithm steps, not just WHAT it does)
- **concrete_specifics**: Real numbers when appropriate, or type-appropriate concrete artifacts such as incident classes, control objectives, validation rules, schema constraints, latency/memory limits, or evaluation protocols
- **code_or_formula**: Working code or mathematical formulas when appropriate, or a correct policy-aligned technical procedure/workflow/checklist for no-code terms

### Accuracy
- **factual_correctness**: Claims verifiable against official docs or common technical knowledge
- **hallucination_absence**: No fabricated benchmarks, product names, paper titles, RFC numbers, or entities

### Uniqueness
- **term_differentiation**: Content clearly distinguishes this concept from similar handbook terms
- **internal_non_redundancy**: Each section adds new information; no paraphrasing the same idea across sections

### Structural Completeness
- **required_sections_present**: All expected sections are present with substantive content (not placeholder stubs)
- **format_compliance**: `❌ Mistake:`/`✅ Fix:` markers in the Pitfalls section, `(prerequisite)`/`(alternative)`/`(extension)` tags in the Relations section. (References array is NOT part of the submitted content — do not score its structure.)

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

## Bilingual Content Contract

The user message contains TWO parallel locale versions of the same term, labeled `## Korean (KO)` and `## English (EN)`. These are intentional translations of each other, not independent content. Apply these rules:

- **Same idea expressed in both KO and EN is NOT redundancy.** `non_redundancy` measures repetition WITHIN each locale only — e.g., the same example paraphrased across multiple sections of `body_basic_ko`. Cross-locale parallelism is expected and MUST NOT be penalized.
- **Score each sub-score as the weaker of the two locales.** If KO looks strong and EN looks weak on `plain_language_clarity`, the term as a whole is weak on that dimension — return the lower score. Rationale: a term that only works in one language isn't a good handbook entry.
- **Cite evidence with locale labels.** Always prefix evidence with `[KO]` or `[EN]` (e.g., `[KO] basic_ko hook: "왜 모델이 Overfitting하는가"`). Never mix quotes from both locales in one evidence field.
- **If one locale is a placeholder** (`(no Korean content provided)` or similar), treat that locale as score 0 on all content-dependent sub-scores and mention the missing locale in the evidence.

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
