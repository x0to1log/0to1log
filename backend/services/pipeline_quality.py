"""Quality scoring and validation for generated digests.

Contains:
  - _check_digest_quality: main quality gate (LLM-based scoring)
  - Score normalizers: _normalize_scope, _normalize_quality_issue, etc.
  - Score components: _compute_structure_score, _compute_traceability_score, _compute_locale_score
  - Penalty engine: _apply_issue_penalties_and_caps, _extract_structured_issues
  - Blockers: _find_digest_blockers, _check_structural_penalties

Phase 2 will add validate_citation_urls() here.

Extracted from pipeline.py during 2026-04-15 Phase 1.
External callers should still import from services.pipeline (re-exported).
"""
import logging

logger = logging.getLogger(__name__)
