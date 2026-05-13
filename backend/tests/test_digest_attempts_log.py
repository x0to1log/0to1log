"""Pins May 11 observability fix: digest writer records per-attempt detail.

Background:
  Stage Timeline already shows tier, cached_tokens, reasoning_tokens, errors,
  and the full debug_meta JSON (collapsible). The one remaining gap was
  per-attempt visibility — when 5/7 research:learner failed 3 times in 58
  minutes, the stage row only showed the final attempt. Couldn't see whether
  attempts 1+2 timed out, hit different tiers, or had different errors.

Fix:
  attempts_log: list[dict] accumulates an entry per attempt (success or
  failure) inside the digest writer's outer-retry loop. Captured fields:
    - attempt (1-indexed)
    - tier ("flex" | "standard")
    - duration_s
    - status ("success" | "schema_reject" | "failed")
    - error_class / error_message (when failed)
    - ko_recovered / en_recovered (when success had locale recovery)
  Embedded in the stage row's debug_meta so the existing admin Stage
  Timeline JSON panel surfaces it without any frontend change.

These are source-level structural pins. A regression that drops the
attempts_log push or omits the field from a debug_meta dict gets caught
at CI.
"""
import re
from pathlib import Path

import pytest


SRC = Path(__file__).parent.parent / "services" / "pipeline_digest.py"


@pytest.fixture(scope="module")
def writer_block() -> str:
    """Outer attempt loop through all three exit-point _log_stage calls."""
    src = SRC.read_text(encoding="utf-8")
    start = src.find("attempts_log: list[dict[str, Any]] = []")
    assert start > 0, "could not find attempts_log initialization"
    end = src.find("# Validate: expert/learner remain the hard requirement.", start)
    assert end > start
    return src[start:end]


def test_attempts_log_initialized_per_persona(writer_block: str) -> None:
    """The list must reset for each persona (expert / learner) — sharing it
    across personas would conflate two independent retry timelines into one."""
    src = SRC.read_text(encoding="utf-8")
    init = src.find("attempts_log: list[dict[str, Any]] = []")
    persona_loop_start = src.find("for persona_name in DAILY_DIGEST_PERSONAS")
    attempt_loop_start = src.find("for attempt in range(MAX_DIGEST_RETRIES + 1):")
    assert persona_loop_start < init < attempt_loop_start, (
        "attempts_log must initialize INSIDE the persona loop but BEFORE the "
        "attempt loop; otherwise it carries entries across personas"
    )


def test_attempt_start_time_captured(writer_block: str) -> None:
    """duration_s requires a per-attempt start. t_attempt is the marker."""
    block = writer_block
    assert "t_attempt = time.monotonic()" in block, (
        "expected t_attempt = time.monotonic() at start of each attempt"
    )


def test_success_path_appends_attempts_log_entry(writer_block: str) -> None:
    """Success path must record before _log_stage so the entry is in the
    debug_meta dict that gets persisted."""
    block = writer_block
    success_segment = block[block.find("personas[persona_name] = persona_output"):
                            block.find("break  # success")]
    # Should contain the append with status=success
    assert "attempts_log.append" in success_segment
    assert '"status": "success"' in success_segment
    # And carry the recovery flags so we can see if recovery added cost
    assert "ko_recovered" in success_segment
    assert "en_recovered" in success_segment


def test_schema_reject_appends_attempts_log_entry(writer_block: str) -> None:
    """BadRequestError (strict-schema validation fail) is its own status —
    distinct from generic failure because it implies a model output problem,
    not infrastructure. Useful for prompt-debugging vs queue-debugging."""
    block = writer_block
    schema_segment = block[block.find("except openai.BadRequestError as schema_err:"):
                           block.find("except Exception as e:")]
    assert "attempts_log.append" in schema_segment
    assert '"status": "schema_reject"' in schema_segment
    assert "type(schema_err).__name__" in schema_segment


def test_general_exception_appends_attempts_log_entry(writer_block: str) -> None:
    """Catch-all for timeout / network / parse errors. error_class +
    error_message preserved for postmortem (capped at 200 chars to avoid
    bloating debug_meta with stack-trace-sized payloads)."""
    block = writer_block
    # Grab from "except Exception as e:" to end of block
    exc_segment = block[block.find("except Exception as e:"):]
    assert "attempts_log.append" in exc_segment
    assert '"status": "failed"' in exc_segment
    assert "type(e).__name__" in exc_segment
    assert "str(e)[:200]" in exc_segment, (
        "error_message must be truncated; full exception strings can be huge"
    )


def test_attempts_log_in_all_three_log_stage_debug_meta(writer_block: str) -> None:
    """The list lives only in memory — to survive into the admin UI it must
    be in the debug_meta dict of every _log_stage call (success, schema-fail,
    general-fail). Missing one would silently lose the timeline for that
    failure class."""
    block = writer_block
    log_stage_calls = re.findall(
        r'await\s+_log_stage\s*\((.*?)\)\s*\n',
        block,
        flags=re.DOTALL,
    )
    assert len(log_stage_calls) == 3, (
        f"expected 3 _log_stage calls in writer block, got {len(log_stage_calls)}"
    )
    for i, call in enumerate(log_stage_calls):
        assert '"attempts_log": attempts_log' in call, (
            f"_log_stage call #{i+1} missing attempts_log in debug_meta"
        )


def test_attempts_log_entry_includes_tier(writer_block: str) -> None:
    """tier per attempt is the data point that proves whether the
    flex→standard fallback fired. Without it, retry-storm postmortems
    can't tell whether the right tier was used."""
    block = writer_block
    # Each append must include the tier field
    appends = re.findall(
        r'attempts_log\.append\s*\(\s*\{(.*?)\}\s*\)',
        block,
        flags=re.DOTALL,
    )
    assert len(appends) == 3, f"expected 3 appends (success + 2 failure paths), got {len(appends)}"
    for i, body in enumerate(appends):
        assert '"tier": tier_label' in body, f"append #{i+1} missing tier"
        assert '"duration_s"' in body, f"append #{i+1} missing duration_s"
        assert '"attempt": attempt + 1' in body, f"append #{i+1} missing 1-indexed attempt"
