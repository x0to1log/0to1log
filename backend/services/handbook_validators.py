"""Pre-insertion validators for handbook terms.

Unlike `handbook_quality_checks.py` (post-hoc measurement), these validators
run in the pipeline BEFORE a term is inserted, gating which candidate terms
become handbook rows.

Each validator returns `(ok: bool, reason: str)`. Pure — no DB, no IO.
Given the same (term, term_type) input and config, always returns the same
result.
"""
from __future__ import annotations

import re

from services.handbook_quality_config import (
    ALL_CAPS_ABBREVIATION_PATTERN,
    HR_REGULATORY_BLOCKLIST,
    IMPORTANT_NON_TECH_ALLOWLIST,
    KOREAN_MIN_HANGUL_CHARS,
    MAJOR_AI_PRODUCT_ALLOWLIST,
    MAJOR_MODEL_VERSION_PATTERNS,
    OUT_OF_SCOPE_REGEX,
)


def validate_term_scope(
    term: str,
    term_type: str | None = None,
    _allowlist_override: frozenset[str] | None = None,
) -> tuple[bool, str]:
    """Gate a candidate term against scope rules before insertion.

    Priority order (first match wins):
      1. Empty term -> reject.
      2. Allowlist (IMPORTANT_NON_TECH_ALLOWLIST, or test override) -> accept.
      3. Versioned-model regex match -> accept (e.g., GPT-5, Claude Sonnet 4.6).
      4. HR/regulatory literal blocklist match -> reject.
      5. Standard-family regex match (ISO xxxx, IEC xxxx, ...) -> reject.
      6. `term_type == 'product_platform_service'` AND not in product
         allowlist -> reject.
      7. Otherwise -> accept.

    `_allowlist_override` is a test-only hook that replaces
    IMPORTANT_NON_TECH_ALLOWLIST for that call. Production callers should
    leave it as None.
    """
    term_stripped = term.strip() if term else ""

    # 1. Empty
    if not term_stripped:
        return False, "empty term"

    # 2. Allowlist override (special cases Amy decided to include)
    allowlist = _allowlist_override if _allowlist_override is not None else IMPORTANT_NON_TECH_ALLOWLIST
    if term_stripped in allowlist:
        return True, ""

    # 3. Versioned model names (GPT-5, Claude 4.6, Gemini 3, ...)
    for pattern in MAJOR_MODEL_VERSION_PATTERNS:
        if re.match(pattern, term_stripped):
            return True, ""

    # 4. HR / regulatory literal blocklist
    if term_stripped in HR_REGULATORY_BLOCKLIST:
        return False, f"blocklist match: {term_stripped}"

    # 5. Standard-family regex (ISO xxx, IEC xxx, IEEE xxx, ...)
    for pattern in OUT_OF_SCOPE_REGEX:
        if re.match(pattern, term_stripped):
            return False, f"out_of_scope_pattern match: {pattern}"

    # 6. product_platform_service type without allowlist entry
    if term_type == "product_platform_service" and term_stripped not in MAJOR_AI_PRODUCT_ALLOWLIST:
        return False, f"product term_type but '{term_stripped}' not in MAJOR_AI_PRODUCT_ALLOWLIST"

    # 7. Default: accept
    return True, ""


_HANGUL_RE = re.compile(r"[\uac00-\ud7af]")


def _count_hangul(s: str) -> int:
    return len(_HANGUL_RE.findall(s))


def _matches_global_name_pattern(term: str) -> bool:
    """True if the term is a legitimate 'keep-as-English' global name:
    a versioned model (GPT-5, Claude 4.6, ...) OR an all-caps abbreviation
    (LSTM, RAG, BERT, ...). These have no established Korean form and are
    commonly written as English in Korean tech press.
    """
    for pattern in MAJOR_MODEL_VERSION_PATTERNS:
        if re.match(pattern, term):
            return True
    if re.match(ALL_CAPS_ABBREVIATION_PATTERN, term):
        return True
    return False


def validate_korean_name(term: str, korean_name: str | None) -> tuple[bool, str]:
    """Validate that korean_name is a plausible Korean rendering of term.

    Rules (first match wins):
      1. None / empty / whitespace-only -> accept. (UI shows English only.)
      2. korean_name identical to term -> accept ONLY if term is a global
         name pattern (versioned model, all-caps abbreviation).
      3. Otherwise korean_name MUST contain at least KOREAN_MIN_HANGUL_CHARS
         Hangul syllables. English copies, stray ASCII, and single-char labels
         fail this check.

    Does NOT attempt phonetic-transliteration detection — that's impractical
    without a Korean dictionary. The generation prompt is responsible for
    steering the LLM away from inventing transliterations; this validator
    only enforces the structural minimum (Hangul presence, global-name
    exception, identical-English rejection for non-global terms).
    """
    if korean_name is None:
        return True, ""
    kn = korean_name.strip()
    if not kn:
        return True, ""

    if kn == term.strip():
        if _matches_global_name_pattern(term):
            return True, ""
        return False, (
            f"korean_name identical to English but term '{term}' is not a "
            "global-name pattern (versioned model or all-caps abbreviation)"
        )

    hangul_count = _count_hangul(kn)
    if hangul_count < KOREAN_MIN_HANGUL_CHARS:
        return False, (
            f"korean_name has {hangul_count} Hangul syllable(s), below "
            f"threshold {KOREAN_MIN_HANGUL_CHARS}"
        )

    return True, ""


def validate_term_grounding(
    term: str, source_texts: list[str | None],
) -> tuple[bool, str]:
    """Verify `term` appears verbatim in at least one of `source_texts`.

    This is a queue-level gate (not a reject gate). Ungrounded terms route
    to `status='queued'` so Amy can decide whether the term is legitimately
    new (LLM introducing a concept from general knowledge that the article
    discussed in other wording) or fabricated from fragments.

    Returns (False, reason) when:
      - `source_texts` is empty,
      - `term` is empty,
      - `term` (case-insensitive) never appears as a contiguous substring, OR
      - for multi-word `term`, every component word appears individually in
        sources but the compound phrase itself never does — the canonical
        'fabricated compound' signal.

    Returns (True, "") when the term is verbatim in the combined source text.
    """
    if not source_texts:
        return False, "no source texts to verify grounding against"
    term_stripped = term.strip() if term else ""
    if not term_stripped:
        return False, "empty term"

    term_lower = term_stripped.lower()
    combined_lower = "\n".join((s or "").lower() for s in source_texts)

    if term_lower in combined_lower:
        return True, ""

    words = term_lower.split()
    if len(words) >= 2:
        all_words_present = all(w in combined_lower for w in words)
        if all_words_present:
            return False, (
                f"compound term '{term_stripped}' never appears verbatim "
                "though all component words are individually present in "
                "sources — likely fabricated from fragments"
            )

    return False, f"term '{term_stripped}' not found verbatim in any source"
