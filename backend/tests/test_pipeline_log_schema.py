import re
from pathlib import Path


def _pipeline_log_status_values_from_migrations() -> set[str]:
    root = Path(__file__).resolve().parents[2]
    migration_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((root / "supabase" / "migrations").glob("*.sql"))
    )

    constraint_matches = list(
        re.finditer(
            r"pipeline_logs_status_check.*?CHECK\s*\(\s*status\s+IN\s*\((.*?)\)\s*\)",
            migration_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
    )
    if constraint_matches:
        values_blob = constraint_matches[-1].group(1)
    else:
        create_match = re.search(
            r"CREATE\s+TABLE\s+pipeline_logs\s*\(.*?status\s+TEXT\s+NOT\s+NULL\s+CHECK\s*"
            r"\(\s*status\s+IN\s*\((.*?)\)\s*\)",
            migration_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        assert create_match, "pipeline_logs status check not found in migrations"
        values_blob = create_match.group(1)

    return set(re.findall(r"'([^']+)'", values_blob))


def test_pipeline_logs_status_constraint_allows_statuses_used_by_pipeline_code():
    allowed = _pipeline_log_status_values_from_migrations()

    assert {"started", "success", "failed", "retried", "no_news"} <= allowed
    assert "skipped" in allowed
    assert "queued" in allowed
