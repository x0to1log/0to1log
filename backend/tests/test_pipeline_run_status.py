"""pipeline_runs.status must stay inside the table's CHECK constraint.

2026-10-26: weekly W43 published with empty beginner bodies and tried to write
status "partial"; the CHECK rejected it, so the run row recorded a constraint
violation instead of the real error.
"""

import re
from pathlib import Path

from services.pipeline import _final_run_status

ROOT = Path(__file__).resolve().parents[2]


def _allowed_run_statuses() -> set[str]:
    sql = (ROOT / "supabase/migrations/00002_pipeline_tables.sql").read_text(encoding="utf-8")
    table = sql[sql.index("CREATE TABLE pipeline_runs"):]
    check = re.search(r"CHECK \(status IN \(([^)]*)\)\)", table)
    assert check, "pipeline_runs status CHECK not found"
    return set(re.findall(r"'([a-z_]+)'", check.group(1)))


def test_final_run_status_follows_the_daily_rule():
    assert _final_run_status(2, []) == "success"
    # Posts saved but a step failed (W43: beginner EN empty) is a failure, with
    # the reason kept in last_error by the caller.
    assert _final_run_status(2, ["weekly beginner EN: empty content"]) == "failed"
    assert _final_run_status(0, []) == "failed"
    assert _final_run_status(0, ["Save weekly en: boom"]) == "failed"


def test_final_run_status_values_are_allowed_by_the_db_check():
    allowed = _allowed_run_statuses()
    for posts in (0, 1):
        for errors in ([], ["x"]):
            assert _final_run_status(posts, errors) in allowed


def test_pipeline_never_assigns_partial_as_a_run_status():
    source = (ROOT / "backend/services/pipeline.py").read_text(encoding="utf-8")
    assert not re.search(r"""status\s*=[^\n#]*["']partial["']""", source)
