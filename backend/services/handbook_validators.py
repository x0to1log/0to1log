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
    HR_REGULATORY_BLOCKLIST,
    IMPORTANT_NON_TECH_ALLOWLIST,
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
