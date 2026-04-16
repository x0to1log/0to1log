"""Persistence and notification helpers for the news pipeline.

Contains:
  - promote_drafts: scheduled draft -> published promotion logic
  - _send_draft_alert: email/Slack alert when digest saved as draft
  - _notify_auto_publish: notification when draft auto-published
  - _fetch_week_digests, _fetch_week_handbook_terms: weekly aggregation helpers
  - _send_weekly_email: weekly recap email sender

Extracted from pipeline.py during 2026-04-15 news-pipeline-hardening Phase 1.
External callers should still import from services.pipeline (re-exported).
"""
import logging

logger = logging.getLogger(__name__)
