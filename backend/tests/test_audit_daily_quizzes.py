from scripts.audit_daily_quizzes import iter_quizzes, structural_quiz_issue

OPTIONS = ["alpha", "beta", "gamma", "delta"]


def test_structural_issue_none_for_consistent_quiz():
    assert structural_quiz_issue({"options": OPTIONS, "answer": "beta", "answer_index": 1}) is None


def test_structural_issue_flags_answer_outside_options():
    assert "not in options" in structural_quiz_issue({"options": OPTIONS, "answer": "epsilon"})


def test_structural_issue_flags_index_text_mismatch():
    issue = structural_quiz_issue({"options": OPTIONS, "answer": "beta", "answer_index": 2})
    assert "answer_index" in issue


def test_iter_quizzes_pairs_each_quiz_with_its_persona_body():
    rows = [{
        "slug": "2026-09-28-research-digest", "locale": "en", "post_type": "research",
        "content_expert": "expert body", "content_learner": "learner body",
        "guide_items": {
            "quiz_poll_expert": {"question": "q1"},
            "quiz_poll_learner": {"question": "q2"},
            "sources_expert": [],
        },
    }]
    items = list(iter_quizzes(rows))
    assert [(i["persona"], i["body"], i["quiz"]["question"]) for i in items] == [
        ("expert", "expert body", "q1"),
        ("learner", "learner body", "q2"),
    ]
    assert items[0]["slug"] == "2026-09-28-research-digest" and items[0]["locale"] == "en"
