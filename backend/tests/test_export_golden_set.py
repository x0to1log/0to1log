"""Contracts of scripts/export_golden_set.py that protect a labeller's work.

The export is re-run as new days arrive. It must not anchor labels on the
current judge, lose a label, or erase a QC-input snapshot that can no longer
be rebuilt once checkpoints are pruned.
"""
import json

import pytest

from scripts.export_golden_set import (
    agreement,
    build_item,
    build_replay,
    choose_sample,
    export_units,
    group_population,
    keep_earlier_replay,
    label_problems,
    parse_review_labels,
    render_review,
)


def _gate(score, caps):
    return score is not None and score >= 70 and "major_source_cap_84" not in (caps or [])


def _row(date, digest_type, locale, status="published", score=90, caps=None):
    return {
        "pipeline_batch_id": date, "post_type": digest_type, "locale": locale,
        "status": status, "quality_score": score, "caps": caps or [],
    }


def _unit(date="2026-11-13", digest_type="research", gate_pass=True, status="published"):
    return {
        "id": f"{date}-{digest_type}", "date": date, "type": digest_type,
        "status": status, "score": 90, "caps": [], "gate_pass": gate_pass,
    }


def _locale_row(locale):
    return {
        "title": f"Title {locale}", "excerpt": f"Excerpt {locale}", "focus_items": [f"focus {locale}"],
        "content_expert": f"## Section\n\n### Story\n\nExpert body {locale} [1](https://example.com/a)",
        "content_learner": f"Learner body {locale}",
        "content_beginner": "",
        "guide_items": {"quiz_poll_expert": {"question": f"Q {locale}?", "answer": "A"}},
        "fact_pack": {
            "quality_version": "v2",
            "quality_issues": [{"severity": "major", "message": "SECRET JUDGE ISSUE"}],
        },
        "source_cards": [{"id": 1, "url": "https://example.com/a", "title": "Source A"}],
    }


def _item(replay=None):
    return build_item(_unit(), {"en": _locale_row("en"), "ko": _locale_row("ko")}, replay)


def test_group_population_merges_locales_and_needs_both_published():
    rows = [
        _row("2026-11-13", "research", "en"),
        _row("2026-11-13", "research", "ko"),
        _row("2026-11-13", "business", "en", score=92, caps=["major_source_cap_84"]),
        _row("2026-11-13", "business", "ko", status="draft"),
        _row("2026-11-13", "weekly", "en"),
    ]
    units = {u["id"]: u for u in group_population(rows, _gate)}

    assert set(units) == {"2026-11-13-research", "2026-11-13-business"}
    assert units["2026-11-13-research"]["status"] == "published"
    assert units["2026-11-13-research"]["gate_pass"] is True
    assert units["2026-11-13-business"]["status"] == "draft"
    assert units["2026-11-13-business"]["gate_pass"] is False


def test_choose_sample_takes_held_digests_first_and_is_repeatable():
    units = [_unit(f"2026-10-{day:02d}") for day in range(1, 21)]
    units += [_unit(f"2026-11-{day:02d}", gate_pass=False) for day in range(1, 4)]

    chosen = choose_sample(units, 10, seed=7)

    assert len(chosen) == 10
    assert sum(1 for u in chosen if not u["gate_pass"]) == 3
    assert chosen == choose_sample(units, 10, seed=7)
    assert chosen == sorted(chosen, key=lambda u: (u["date"], u["type"]))


def test_review_sheet_hides_what_the_judge_said():
    item = _item()
    sheet = render_review(item)

    assert item["stored"]["quality_score"] == 90
    assert "SECRET JUDGE ISSUE" not in sheet
    assert "quality_score" not in sheet and "90" not in sheet
    assert "Expert body en" in sheet and "Expert body ko" in sheet
    assert "## beginner" not in sheet  # empty persona is skipped
    assert "https://example.com/a" in sheet


def test_labels_round_trip_from_a_filled_review_sheet():
    sheet = render_review(_item())
    assert parse_review_labels(sheet)["verdict"] == ""

    filled = sheet.replace(
        "verdict:            #", "verdict: block      #",
    ).replace("reasons: []", "reasons: [overclaim, locale]").replace('notes: ""', 'notes: "headline overstates"')
    label = parse_review_labels(filled)

    assert label == {
        "id": "2026-11-13-research", "verdict": "block",
        "reasons": ["overclaim", "locale"], "notes": "headline overstates",
    }
    assert label_problems(label) == []


@pytest.mark.parametrize(
    "label, expected",
    [
        ({"verdict": "maybe", "reasons": []}, "verdict must be"),
        ({"verdict": "block", "reasons": []}, "needs at least one reason"),
        ({"verdict": "block", "reasons": ["vibes"]}, "unknown reasons"),
    ],
)
def test_label_problems_reports_unusable_labels(label, expected):
    assert any(expected in problem for problem in label_problems(label))


def test_build_replay_cuts_inputs_to_one_digest_type():
    rank = {
        "research": [{"group_title": "R", "items": [{"url": "https://r/1", "title": "R"}]}],
        "business": [{"group_title": "B", "items": [{"url": "https://b/1", "title": "B"}]}],
    }
    enrich = {
        "enriched_map": {
            "https://r/1": [{"url": "https://r/extra", "content": "extra"}],
            "https://b/1": [{"url": "https://b/extra", "content": "extra"}],
        },
        "raw_content_map": {"https://r/1": "r text", "https://r/extra": "r extra", "https://b/1": "b text"},
    }
    summaries = {"summaries": {"https://r/1": {"sentiment": "mixed"}, "https://b/1": {"sentiment": "positive"}}}

    replay = build_replay("research", rank, summaries, enrich)

    assert [g["group_title"] for g in replay["classified"]] == ["R"]
    assert set(replay["raw_content_map"]) == {"https://r/1", "https://r/extra"}
    assert set(replay["enriched_map"]) == {"https://r/1"}
    assert set(replay["community_summaries"]) == {"https://r/1"}
    assert build_replay("research", None, summaries, enrich) is None
    assert build_replay("research", rank, summaries, None) is None


def test_keep_earlier_replay_survives_pruned_checkpoints():
    saved = _item(replay={"classified": ["kept"]})
    after_prune = _item(replay=None)

    assert keep_earlier_replay(after_prune, saved)["replay"] == {"classified": ["kept"]}
    assert keep_earlier_replay(_item(replay={"classified": ["new"]}), saved)["replay"] == {"classified": ["new"]}
    assert keep_earlier_replay(after_prune, None)["replay"] is None


def test_agreement_counts_human_verdict_against_stored_gate():
    items = {
        "a": {"stored": {"gate_pass": True}},
        "b": {"stored": {"gate_pass": True}},
        "c": {"stored": {"gate_pass": False}},
    }
    labels = [
        {"id": "a", "verdict": "publish"},
        {"id": "b", "verdict": "block"},
        {"id": "c", "verdict": "block"},
        {"id": "missing", "verdict": "block"},
    ]
    table = agreement(labels, items)

    assert table[("publish", "publish")] == 1
    assert table[("block", "publish")] == 1
    assert table[("block", "block")] == 1


def test_reexport_keeps_a_labelled_review_sheet(tmp_path, monkeypatch):
    rows = []
    for locale in ("en", "ko"):
        rows.append({**_locale_row(locale), "post_type": "research", "locale": locale})
    monkeypatch.setattr("services.pipeline._fetch_daily_digest_rows_from_db", lambda sb, date: rows)
    monkeypatch.setattr(
        "scripts.export_golden_set.fetch_checkpoints",
        lambda sb, date: {"rank": None, "community_summarize": None, "enrich": None},
    )

    export_units(None, [_unit()], tmp_path)
    review = tmp_path / "review" / "2026-11-13-research.md"
    review.write_text(review.read_text(encoding="utf-8").replace("verdict:  ", "verdict: publish  ", 1), encoding="utf-8")

    export_units(None, [_unit()], tmp_path)

    assert parse_review_labels(review.read_text(encoding="utf-8"))["verdict"] == "publish"
    item = json.loads((tmp_path / "items" / "2026-11-13-research.json").read_text(encoding="utf-8"))
    assert item["personas"]["expert"]["ko"].startswith("## Section")
