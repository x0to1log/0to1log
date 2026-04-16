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
