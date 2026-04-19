# backend/services/handbook_quality_config.py
"""Config for objective handbook quality checks.

Deliberately a Python module (not DB-hosted) for Phase 1. If check rules
stabilize and need runtime edits, migrate to a Supabase table like
`news_domain_filters` did.

Update this file as the AI landscape evolves. Last reviewed: 2026-04-16.
"""
from __future__ import annotations

# Models considered "previous generation" as of 2026-04-16. Mentioning them
# without a current-generation counterpart suggests stale comparison tables.
STALE_MODELS: frozenset[str] = frozenset({
    "GPT-4",
    "GPT-4o",
    "GPT-4 Turbo",
    "Gemini 1.0",
    "Gemini 1.5",
    "Claude 3 Opus",
    "Claude 3 Sonnet",
    "Claude 3.5 Sonnet",
    "Llama 2",
    "Llama 3",
    "Mistral 7B",
})

# Current-generation models as of 2026-04-16. Presence of any of these
# alongside stale models means the comparison is mixed (less stale).
CURRENT_MODELS: frozenset[str] = frozenset({
    "GPT-5",
    "GPT-5.2",
    "Claude Opus 4.6",
    "Claude Sonnet 4.6",
    "Claude Haiku 4.5",
    "Gemini 3",
    "Llama 4",
})

# Term types that should contain architecture/parameter/benchmark detail
# in body_advanced. Based on the 8-type system from HQ-13 (commit 4f9d809).
ARCHITECTURE_REQUIRED_TYPES: frozenset[str] = frozenset({
    "model_family",
    "technique_algorithm",
    "infrastructure_tool",
})

# Term types that should cite an arxiv/paper link in body_advanced.
PAPER_REFERENCE_REQUIRED_TYPES: frozenset[str] = frozenset({
    "technique_algorithm",
    "research_method",
})

# Flags terms older than this many days as "potentially stale due to age".
# Not a failure on its own, but informs refresh prioritization.
STALE_AGE_DAYS: int = 90

# Regex patterns for dated claims. Matches "as of 2023", "2024 baseline",
# "2024년 기준", etc. Phrases that explicitly anchor content to a past year
# trigger a flag. Korean patterns use lookarounds instead of \b because
# Hangul syllables are \w in Python's Unicode mode — \b between digit and
# 년 does not create a word boundary.
DATED_CLAIM_PATTERNS: tuple[str, ...] = (
    r"\bas of (?:20[12]\d)\b",
    r"(?<!\d)(?:20[12]\d)(?:년)?\s*(?:baseline|기준)(?!\w)",
    r"(?<!\w)현재\s*(?:20[12]\d)(?:년)?(?!\d)",
    r"(?<!\w)기준일[^\n]*?(?:20[12]\d)(?:년)?(?!\d)",
)

# Architecture keywords expected in body_advanced for ARCHITECTURE_REQUIRED_TYPES.
# Presence of ANY keyword passes the check. Multilingual (EN + KO).
ARCHITECTURE_KEYWORDS: frozenset[str] = frozenset({
    # EN
    "parameters", "parameter count", "layers", "attention heads",
    "FLOPs", "context window", "training data", "token count",
    "architecture", "transformer", "encoder", "decoder",
    # KO
    "파라미터", "어텐션", "어텐션 헤드", "레이어", "임베딩",
    "아키텍처", "트랜스포머", "학습 데이터",
})

# Paper-reference regex. Matches arxiv.org, paperswithcode, doi.org, OR a markdown
# link whose text looks like a paper title ("Vaswani et al.", "Attention Is All You Need").
PAPER_REFERENCE_PATTERNS: tuple[str, ...] = (
    r"arxiv\.org/(?:abs|pdf)/\d{4}\.\d{4,5}",
    r"paperswithcode\.com",
    r"doi\.org/10\.",
    r"et al\.",
)


# ============================================================================
# Scope gate config (added 2026-04-19 for Chunk A of selection hardening plan)
# These constants drive the `validate_term_scope()` gate in handbook_validators.py
# ============================================================================

# Literal term names that should always be rejected as out-of-scope.
# Amy-curated from manually-archived terms (2026-04-17 batch cleanup retro).
HR_REGULATORY_BLOCKLIST: frozenset[str] = frozenset({
    # HR / business-operations
    "acquihire",
    "acqui-hire",
    "headcount",
    # Specific regulatory standards (general "AI regulation" concepts stay via allowlist)
    "ISO 42001",
    "ISO 27001",
    "SOC 2",
    "GDPR Article 22",
})

# Regex patterns for whole families to reject. Easier to maintain than
# enumerating every ISO/IEC number.
OUT_OF_SCOPE_REGEX: tuple[str, ...] = (
    r"^ISO\s*\d+(?:[:\-]\d+)?$",     # any ISO xxxxx, ISO xxx:yyyy
    r"^IEC\s*\d+",                   # any IEC standard
    r"^IEEE\s*\d+",                  # any IEEE standard
    r"^NIST\s*SP\s*\d",              # NIST Special Publications
    r"^SOC\s*\d",                    # SOC 1/2/3
)

# Curated exceptions — specific named regulations that ARE in scope for
# the AI handbook (e.g., landmark AI legislation). Must be an exact match.
# Start EMPTY — Amy adds as needed. Do NOT try to anticipate.
IMPORTANT_NON_TECH_ALLOWLIST: frozenset[str] = frozenset({
    # e.g., "EU AI Act", "AI Safety Institute" — add deliberately when needed
})

# Major AI product brand names that pass the `product_platform_service`
# term_type auto-reject. Amy-curated (2026-04-19). Intentionally small —
# models like ChatGPT/Claude/Gemini tend to be classified as
# `model_algorithm_family`, not `product_platform_service`, so they don't
# need to be on this list. This list is for true product brands like Firefly
# that the LLM classifies as product but Amy wants included.
MAJOR_AI_PRODUCT_ALLOWLIST: frozenset[str] = frozenset({
    "Firefly",
})

# Regex patterns for legitimate versioned-model names. Terms matching these
# auto-accept scope gate regardless of term_type classification. Covers
# patterns like "GPT-5.2", "Claude 4.6", "Gemini 3", "Llama 4", "o3".
MAJOR_MODEL_VERSION_PATTERNS: tuple[str, ...] = (
    r"^GPT-\d",                                    # GPT-4, GPT-5, GPT-5.2
    r"^Claude\s+(?:\d+(?:\.\d+)?|\w+(?:\s+\d+(?:\.\d+)?)?)$",  # Claude 4.6, Claude Opus, Claude Sonnet 4.6
    r"^Gemini\s+\d",                               # Gemini 2, Gemini 3
    r"^Llama\s+\d",                                # Llama 3, Llama 4
    r"^Mistral\s+\w+",                             # Mistral Large, Mistral Small
    r"^o\d",                                       # o1, o3, o4
    r"^DeepSeek[- ]",                              # DeepSeek-R1, DeepSeek V3
    r"^(?:GPT|Claude|Gemini|Llama)-?[A-Z][a-z]+",  # GPT-Rosalind, Claude-Code
)
