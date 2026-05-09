"""Pins May 9 fix: digest writer drops flex on retry.

Background:
  May 7 (research:learner) and May 9 (business:learner) both had all 3
  attempts time out at the 1200s flex limit because the flex queue was
  saturated and we kept re-queueing into the same congested pool.

Fix:
  Attempt 0 uses flex (50% off). Attempt 1+ omits service_tier so the
  request lands on the standard (real-time) endpoint with no queue.
  prompt_cache_key stays constant across attempts so OpenAI's prefix
  cache may carry the cache hit from flex into standard.

These tests are source-level structural pins — they catch regressions
where someone restores unconditional `service_tier="flex"` or breaks
the conditional inclusion pattern. Mocked-runtime tests would be more
expressive but the writer call site is deeply nested in pipeline_digest
plumbing; structural pins are good enough for the regression class
they target.
"""
import re
from pathlib import Path

import pytest


SRC = Path(__file__).parent.parent / "services" / "pipeline_digest.py"


@pytest.fixture(scope="module")
def digest_writer_block() -> str:
    """The MAX_DIGEST_RETRIES outer-attempt loop, up to the citations parse."""
    src = SRC.read_text(encoding="utf-8")
    start = src.find("for attempt in range(MAX_DIGEST_RETRIES + 1):")
    assert start > 0, "could not locate digest writer outer-retry loop"
    # Stop before the recovery-call section (KO recovery, EN recovery,
    # heading recovery) — those still use flex unconditionally and that's
    # a separate scope question.
    end = src.find("# Recover missing locale", start)
    assert end > start, "could not locate end of writer block"
    return src[start:end]


def test_digest_writer_flex_only_on_first_attempt(digest_writer_block: str) -> None:
    """Tier must be flex when attempt == 0, None otherwise."""
    block = digest_writer_block
    # Look for the conditional that picks the tier
    pattern = re.compile(
        r'tier_for_attempt[^=]*=\s*"flex"\s+if\s+attempt\s*==\s*0\s+else\s+None'
    )
    assert pattern.search(block), (
        "expected `tier_for_attempt = \"flex\" if attempt == 0 else None` — "
        "got something else. Did someone hardcode flex again?"
    )


def test_digest_writer_does_not_unconditionally_use_flex(digest_writer_block: str) -> None:
    """Pin the negative: there must be NO bare `service_tier=\"flex\"` in
    the writer call path. The fix conditionally includes it via
    `**extra_tier`. A regression that restores the literal would silently
    re-introduce the May 7+9 retry-storm pathology."""
    block = digest_writer_block
    # Allow the literal in comments/docstrings; check only on lines that
    # look like real kwargs (i.e., not starting with `#`).
    offending_lines = [
        line for line in block.splitlines()
        if 'service_tier="flex"' in line and not line.lstrip().startswith("#")
    ]
    assert offending_lines == [], (
        f"unconditional `service_tier=\"flex\"` found at: {offending_lines}. "
        "Use the attempt-conditional pattern instead."
    )


def test_digest_writer_conditionally_includes_service_tier(digest_writer_block: str) -> None:
    """The kwargs construction must guard service_tier inclusion behind
    `tier_for_attempt is not None`, otherwise None gets serialized to the
    OpenAI client and may behave unpredictably."""
    block = digest_writer_block
    # Look for the guarded inclusion pattern
    pattern = re.compile(
        r'extra_tier\s*=\s*\(\s*\{"service_tier":\s*tier_for_attempt\}\s*'
        r'if\s+tier_for_attempt\s+is\s+not\s+None\s+else\s+\{\}\s*\)',
        re.DOTALL,
    )
    assert pattern.search(block), (
        "expected `extra_tier = ({'service_tier': tier_for_attempt} if "
        "tier_for_attempt is not None else {})` — guard ensures None tier "
        "never reaches the OpenAI client"
    )


def test_digest_writer_preserves_prompt_cache_key_across_attempts(
    digest_writer_block: str,
) -> None:
    """The cache_key must be the SAME f-string regardless of attempt — that's
    what gives OpenAI's prefix cache a chance to carry over flex→standard.
    A regression that varies cache_key per attempt would lose the cache."""
    block = digest_writer_block
    # The cache key f-string should appear exactly once in the writer call
    # (the recovery calls use different keys, but they're outside this block)
    cache_keys = re.findall(
        r'prompt_cache_key=f"([^"]+)"',
        block,
    )
    assert len(cache_keys) == 1, (
        f"expected exactly one prompt_cache_key in writer block, got {cache_keys}. "
        "Recovery cache keys belong outside the main attempt loop."
    )
    assert "{digest_type}" in cache_keys[0] and "{persona_name}" in cache_keys[0]
    # Critically: the key must NOT include the attempt number
    assert "attempt" not in cache_keys[0].lower(), (
        f"cache key {cache_keys[0]!r} contains 'attempt' — this would break "
        "cache reuse across retries, defeating the flex→standard fallback."
    )


def test_digest_writer_logs_tier_on_each_attempt(digest_writer_block: str) -> None:
    """Operational visibility: Railway logs need to show which tier each
    attempt used so we can correlate cost spikes / cached_tokens drops with
    the flex→standard fallback path. Without this, debugging future cost
    regressions becomes guesswork."""
    block = digest_writer_block
    # The starting log line must include the tier label
    assert "tier=%s" in block or "tier=%(tier)s" in block, (
        "expected logger.info(...) with tier=%s placeholder so attempt-tier "
        "pairs are searchable in Railway logs"
    )
    # Failure log also needs tier (for retry-storm postmortems)
    assert block.count("tier=%s") >= 2, (
        "expected tier in BOTH start log and call-failed log so retry-storm "
        "incidents can be traced tier-by-tier"
    )


def test_failed_call_usage_estimate_uses_attempt_tier(digest_writer_block: str) -> None:
    """Cost recording on failure must use the actual attempt tier, not a
    hardcoded 'flex'. Otherwise standard-tier failures get logged at flex
    rates and our books drift from OpenAI's bill."""
    block = digest_writer_block
    pattern = re.compile(
        r'estimate_failed_call_usage\s*\([^)]*requested_service_tier\s*=\s*tier_for_attempt',
        re.DOTALL,
    )
    assert pattern.search(block), (
        "expected estimate_failed_call_usage(..., requested_service_tier=tier_for_attempt). "
        "Hardcoded 'flex' here would mis-cost retries that ran on standard."
    )


def test_real_usage_extraction_uses_attempt_tier(digest_writer_block: str) -> None:
    """Same reason as the failed-call counterpart: real (success-path)
    usage must be costed at the actual tier the request landed on."""
    block = digest_writer_block
    pattern = re.compile(
        r'extract_usage_metrics\s*\([^)]*requested_service_tier\s*=\s*tier_for_attempt',
        re.DOTALL,
    )
    assert pattern.search(block), (
        "expected extract_usage_metrics(..., requested_service_tier=tier_for_attempt). "
        "Hardcoded 'flex' here would understate retry-attempt cost."
    )
