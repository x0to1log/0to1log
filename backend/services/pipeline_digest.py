"""Digest generation for daily news pipeline.

Contains:
  - _generate_digest: main per-persona digest generator (calls LLM, builds JSON output)
  - Content cleaners: _strip_empty_sections, _fix_bold_spacing, _clean_writer_output
  - Item extractors: _extract_digest_items, _map_digest_items_to_group_indexes

Extracted from pipeline.py during 2026-04-15 Phase 1.
External callers should still import from services.pipeline (re-exported).
"""
import logging

logger = logging.getLogger(__name__)
