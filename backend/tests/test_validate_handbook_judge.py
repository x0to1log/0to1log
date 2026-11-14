"""Statistics and report of scripts/validate_handbook_judge.py (no DB, no model)."""
import pytest

from scripts.validate_handbook_judge import auc, build_report


def test_auc_bounds_and_ties():
    assert auc([9, 8], [1, 2]) == 1.0
    assert auc([1, 2], [9, 8]) == 0.0
    assert auc([5, 5], [5, 5]) == 0.5
    assert auc([1, 3], [2, 2]) == 0.5
    assert auc([], [1]) is None


def _record(slug, status, adv, basic, source="pipeline", penalty=0, **extra):
    return {
        "slug": slug, "term": slug, "status": status, "source": source,
        "structural_penalty": penalty,
        "adv": None if adv is None else adv - penalty, "adv_sem": adv,
        "basic": None if basic is None else basic - penalty, "basic_sem": basic,
        "judges_missing": [] if adv is not None else ["advanced"],
        "adv_subs": {"accuracy.factual_correctness": 7}, "basic_subs": {},
        "chars": {f: 100 for f in ("body_basic_ko", "body_basic_en", "body_advanced_ko", "body_advanced_en")},
        "cost_usd": 0.2, **extra,
    }


def test_report_separation_gate_and_source_matched_table():
    records = (
        [_record(f"p{i}", "published", 80 + i, 75) for i in range(5)]
        + [_record(f"a{i}", "archived", 60 + i, 75) for i in range(5)]
        + [_record("seed1", "published", 90, 90, source="seed")]
        + [{"slug": "broken", "term": "broken", "status": "archived", "error": "TimeoutError: "}]
    )

    report = build_report(records, repeat=[])

    assert "published 6, archived 5 (errors 1" in report
    # Every published term outscores every archived one on advanced; basic is all ties.
    rows = {line.split(" | ")[0]: line for line in report.split("### ")[0].splitlines() if line.startswith("| ")}
    assert "| 62.0 (1.6) | 1.00 |" in rows["| advanced, judge only"]
    assert "| 75.0 (0.0) | 0.58 |" in rows["| basic, judge only"]
    assert "| advanced ≥ 70 | 6/6 | 0/5 |" in report
    assert "### source = pipeline only (published 5, archived 5)" in report
    assert "- broken: TimeoutError: " in report


def test_report_leaves_unjudged_terms_out_of_scores_and_gate():
    records = [
        _record("p1", "published", 80, 80), _record("p2", "published", None, 80),
        _record("a1", "archived", 60, 60),
    ]

    report = build_report(records, repeat=[])

    assert "judge missing 1" in report
    assert "| advanced ≥ 70 | 1/1 | 0/1 |" in report


def test_report_repeat_pass_counts_gate_flips():
    first = [_record("p1", "published", 72, 80), _record("a1", "archived", 60, 60)]
    second = [_record("p1", "published", 66, 82), _record("a1", "archived", 62, 60)]

    report = build_report(first, repeat=second)

    assert "| advanced | 2 | 4.0 | 6 | 1/2 |" in report
    assert "| basic | 2 | 1.0 | 2 | 0/2 |" in report


def test_execute_flag_is_required_to_call_the_judge():
    from scripts import validate_handbook_judge as mod

    assert mod.parse_args.__module__  # import smoke; the dry-run default is argparse's store_true
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("sys.argv", ["validate_handbook_judge.py"])
        assert mod.parse_args().execute is False
