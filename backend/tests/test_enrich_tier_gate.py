"""Enrich-stage TIER gate (mirrors CLASSIFICATION_SYSTEM_PROMPT gate).

2026-05-06 audit: research-digest had 14 source cards, 9 of which were
TIER-3 enrichment leaks (labs.scale.com, llm-stats.com, dev.to, oreilly.com,
pointofai.com, etc.) brought in by Exa find_similar. The classify-stage
gate doesn't cover enrichment — this test pins the enrich-stage gate.
"""
from services.news_collection import _enrich_source_passes_quality


def _payload(url="https://example.com/foo", kind="analysis", tier="secondary", confidence="low"):
    return {"url": url, "source_kind": kind, "source_tier": tier, "source_confidence": confidence}


# --- TIER-1: official_site / paper / official_repo / primary tier ---

def test_official_site_passes():
    ok, _ = _enrich_source_passes_quality(
        _payload("https://openai.com/blog/foo", kind="official_site", tier="primary", confidence="high"),
        source="merge",
    )
    assert ok is True


def test_paper_passes():
    ok, _ = _enrich_source_passes_quality(
        _payload("https://arxiv.org/abs/2604.12345", kind="paper", tier="primary", confidence="high"),
        source="merge",
    )
    assert ok is True


def test_primary_tier_with_non_analysis_kind_passes():
    ok, _ = _enrich_source_passes_quality(
        _payload("https://www.reuters.com/x", kind="media", tier="primary", confidence="high"),
        source="merge",
    )
    assert ok is True


def test_primary_tier_with_analysis_kind_falls_through():
    """tier=primary + kind=analysis is the documented edge case — falls
    through to TIER-2/3 evaluation, NOT auto-pass as TIER-1."""
    payload = _payload("https://unknown.com/x", kind="analysis", tier="primary", confidence="low")
    ok, reason = _enrich_source_passes_quality(payload, source="exa_enrich")
    assert ok is False
    assert "TIER-3" in reason


# --- TIER-2: secondary + medium/high confidence OR known-trusted media ---

def test_secondary_high_confidence_passes():
    ok, _ = _enrich_source_passes_quality(
        _payload("https://techcrunch.com/x", kind="media", tier="secondary", confidence="high"),
        source="exa_enrich",
    )
    assert ok is True


def test_secondary_medium_confidence_passes():
    ok, _ = _enrich_source_passes_quality(
        _payload("https://verge.com/x", kind="media", tier="secondary", confidence="medium"),
        source="exa_enrich",
    )
    assert ok is True


def test_known_trusted_overrides_low_confidence():
    """axios.com classified as confidence=low (NQ-43 issue) — must still pass."""
    ok, _ = _enrich_source_passes_quality(
        _payload("https://www.axios.com/2026/05/06/foo", kind="analysis", tier="secondary", confidence="low"),
        source="exa_enrich",
    )
    assert ok is True


def test_known_trusted_subdomain_passes():
    """labs.example.axios.com still matches axios.com via suffix logic."""
    ok, _ = _enrich_source_passes_quality(
        _payload("https://blog.bloomberg.com/foo", kind="analysis", tier="secondary", confidence="low"),
        source="exa_enrich",
    )
    assert ok is True


# --- TIER-3: rejected ---

def test_tier3_seo_aggregator_rejected():
    """May 6 incident pattern: pointofai.com, knightli.com, etc."""
    ok, reason = _enrich_source_passes_quality(
        _payload("https://pointofai.com/foo", kind="analysis", tier="secondary", confidence="low"),
        source="exa_enrich",
    )
    assert ok is False
    assert "TIER-3" in reason


def test_tier3_dev_to_rejected():
    """Common Exa find_similar leak source."""
    ok, reason = _enrich_source_passes_quality(
        _payload("https://dev.to/foo/bar", kind="analysis", tier="secondary", confidence="low"),
        source="exa_enrich",
    )
    assert ok is False


def test_tier3_substack_rejected():
    ok, reason = _enrich_source_passes_quality(
        _payload(
            "https://nandigamharikrishna.substack.com/p/foo",
            kind="analysis", tier="secondary", confidence="low",
        ),
        source="exa_enrich",
    )
    assert ok is False


def test_tier3_unknown_blog_rejected():
    ok, reason = _enrich_source_passes_quality(
        _payload("https://random-ai-blog.com/post", kind="analysis", tier="secondary", confidence="low"),
        source="exa_enrich",
    )
    assert ok is False


# --- Pre-existing rules still apply ---

def test_spam_blocked():
    ok, reason = _enrich_source_passes_quality(
        _payload("https://zamin.uz/foo", kind="analysis", tier="spam", confidence="low"),
        source="exa_enrich",
    )
    assert ok is False
    assert "spam" in reason


def test_official_repo_via_exa_enrich_blocked():
    """Existing rule: github user repos via find_similar are noisy."""
    ok, reason = _enrich_source_passes_quality(
        _payload("https://github.com/randomuser/repo", kind="official_repo", tier="primary", confidence="medium"),
        source="exa_enrich",
    )
    assert ok is False
    assert "github.com" in reason


def test_official_repo_via_merge_passes():
    """Same official_repo classified differently when source is 'merge' (not exa_enrich)."""
    ok, _ = _enrich_source_passes_quality(
        _payload("https://github.com/openai/cookbook", kind="official_repo", tier="primary", confidence="medium"),
        source="merge",
    )
    assert ok is True
