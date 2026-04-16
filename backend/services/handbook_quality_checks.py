"""Objective (no-LLM) quality checks for handbook terms.

Each check returns (failed: bool, reason: str). Pure — no DB, no IO.
Given the same term + config, always returns the same result.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from services.handbook_quality_config import (
    ARCHITECTURE_KEYWORDS,
    ARCHITECTURE_REQUIRED_TYPES,
    CURRENT_MODELS,
    DATED_CLAIM_PATTERNS,
    PAPER_REFERENCE_PATTERNS,
    PAPER_REFERENCE_REQUIRED_TYPES,
    STALE_AGE_DAYS,
    STALE_MODELS,
)


def _all_bodies(term: dict) -> str:
    parts = [
        term.get("body_advanced_en") or "",
        term.get("body_advanced_ko") or "",
        term.get("body_basic_en") or "",
        term.get("body_basic_ko") or "",
    ]
    return "\n".join(parts)


def check_stale_model_comparison(term: dict) -> tuple[bool, str]:
    """Fail if term mentions stale models without any current-gen counterpart."""
    body = _all_bodies(term)
    stale_hits = [m for m in STALE_MODELS if m in body]
    if not stale_hits:
        return False, ""
    current_hits = [m for m in CURRENT_MODELS if m in body]
    if current_hits:
        return False, ""
    return True, f"mentions {stale_hits} without any current-gen model"


def check_missing_architecture_detail(term: dict) -> tuple[bool, str]:
    """Fail if term_type requires architecture detail but none present."""
    if term.get("term_type") not in ARCHITECTURE_REQUIRED_TYPES:
        return False, ""
    body = _all_bodies(term)
    body_lower = body.lower()
    hits = [k for k in ARCHITECTURE_KEYWORDS if k.lower() in body_lower]
    if hits:
        return False, ""
    return True, f"term_type={term.get('term_type')} but no architecture keyword found"
