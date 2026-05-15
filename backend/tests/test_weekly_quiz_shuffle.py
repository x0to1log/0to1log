"""Unit tests for _validate_and_shuffle_weekly_quiz.

Covers:
- Happy path: valid items kept, options set preserved, answer still matches
- Invalid items dropped (wrong option count, answer not in options, empty question, non-dict)
- Excess items trimmed to 3
- Non-list input returns empty list
- Statistical: over 1000 shuffles, correct-answer position is approximately uniform
  (tolerance +/- 5pp per slot) — proves shuffle counters the LLM first-position bias
"""

from collections import Counter

from services.pipeline import (
    _validate_and_shuffle_quiz_item,
    _validate_and_shuffle_weekly_quiz,
)


class TestSingleItemValidator:
    """Covers the single-item helper that both daily and weekly use."""

    def _valid(self) -> dict:
        return {
            "question": "Which model?",
            "options": ["GPT-5", "Claude", "Gemini", "Llama"],
            "answer": "Claude",
            "explanation": "Anthropic released Claude.",
        }

    def test_valid_item_passes_and_preserves_answer_text(self):
        out = _validate_and_shuffle_quiz_item(self._valid())
        assert out is not None
        assert out["answer"] == "Claude"
        assert "Claude" in out["options"]
        assert set(out["options"]) == {"GPT-5", "Claude", "Gemini", "Llama"}

    def test_letter_form_answer_rejected(self):
        """answer='A' must fail — letter doesn't match any option text."""
        item = self._valid()
        item["answer"] = "A"
        assert _validate_and_shuffle_quiz_item(item) is None

    def test_index_form_answer_rejected(self):
        item = self._valid()
        item["answer"] = "0"
        assert _validate_and_shuffle_quiz_item(item) is None

    def test_paraphrased_answer_rejected(self):
        """Answer must be verbatim — 'claude' lowercase fails vs 'Claude'."""
        item = self._valid()
        item["answer"] = "claude"
        assert _validate_and_shuffle_quiz_item(item) is None

    def test_wrong_option_count_rejected(self):
        item = self._valid()
        item["options"] = ["A", "B", "C"]
        assert _validate_and_shuffle_quiz_item(item) is None

    def test_empty_question_rejected(self):
        item = self._valid()
        item["question"] = ""
        assert _validate_and_shuffle_quiz_item(item) is None

    def test_non_dict_returns_none(self):
        assert _validate_and_shuffle_quiz_item(None) is None
        assert _validate_and_shuffle_quiz_item("string") is None
        assert _validate_and_shuffle_quiz_item([1, 2]) is None

    def test_answer_index_form_accepted(self):
        """New contract: writer emits answer_index 0-3, validator resolves text."""
        item = {
            "question": "Which model?",
            "options": ["GPT-5", "Claude", "Gemini", "Llama"],
            "answer_index": 1,
            "explanation": "Anthropic released Claude.",
        }
        out = _validate_and_shuffle_quiz_item(item)
        assert out is not None
        assert out["answer"] == "Claude"
        assert "Claude" in out["options"]

    def test_answer_index_out_of_range_rejected(self):
        item = {
            "question": "Q",
            "options": ["A", "B", "C", "D"],
            "answer_index": 7,
            "explanation": "",
        }
        assert _validate_and_shuffle_quiz_item(item) is None

    def test_answer_index_negative_rejected(self):
        item = {
            "question": "Q",
            "options": ["A", "B", "C", "D"],
            "answer_index": -1,
            "explanation": "",
        }
        assert _validate_and_shuffle_quiz_item(item) is None

    def test_legacy_answer_text_still_accepted(self):
        """Backward-compat for old checkpoints / pre-migration weekly writer."""
        item = {
            "question": "Q",
            "options": ["A", "B", "C", "D"],
            "answer": "B",
            "explanation": "",
        }
        out = _validate_and_shuffle_quiz_item(item)
        assert out is not None
        assert out["answer"] == "B"

    def test_answer_index_takes_precedence_over_legacy_answer(self):
        """If both present, answer_index wins.

        The legacy `answer` field is set to a value NOT in options — a
        "legacy first" buggy implementation would either drop the item
        (legacy text fails the `answer in options` check) or return the
        bad text. Both fail the assertion below."""
        item = {
            "question": "Q",
            "options": ["A", "B", "C", "D"],
            "answer_index": 2,
            "answer": "NOT_IN_OPTIONS",
            "explanation": "",
        }
        out = _validate_and_shuffle_quiz_item(item)
        assert out is not None
        assert out["answer"] == "C"

    def test_answer_index_boolean_rejected(self):
        """isinstance(True, int) is True in Python — explicit guard required."""
        item = {
            "question": "Q",
            "options": ["A", "B", "C", "D"],
            "answer_index": True,
            "explanation": "",
        }
        assert _validate_and_shuffle_quiz_item(item) is None

    def test_answer_index_repaired_when_explanation_supports_a_different_option(self):
        item = {
            "question": "Which pairing best captures the operational constraint and measured impact reported for Switchcraft?",
            "options": [
                "Throughput ceiling; 48% tool-call reduction at 1.7% accuracy loss",
                "Memory budget; 46.6% perplexity improvement on language modeling",
                "Latency budget; 82.9% accuracy with an 84% inference-cost reduction and $3,600 saved per million queries",
                "Token limit; 3x sample-efficiency over parameter-only RL",
            ],
            "answer_index": 3,
            "explanation": (
                "Switchcraft is deployed under a latency budget and reports "
                "82.9% accuracy with an 84% inference-cost reduction, saving "
                "over $3,600 per million queries."
            ),
        }

        out = _validate_and_shuffle_quiz_item(item)

        assert out is not None
        assert out["answer"] == item["options"][2]

    def test_answer_index_repaired_when_explanation_negates_selected_option(self):
        item = {
            "question": "Which claim is directly reported by the EVA-Bench paper's abstract?",
            "options": [
                "The median gap between pass@k and pass^k on EVA-A is 0.44",
                "All evaluated systems exceed 0.5 on both EVA-A and EVA-X pass@1",
                "EVA-Bench uses human-in-the-loop calls for every scoring decision",
                "FoE's 5.2x latency reduction is replicated on EVA-Bench tasks",
            ],
            "answer_index": 1,
            "explanation": (
                "The EVA-Bench abstract reports a median pass@k - pass^k gap "
                "of 0.44 on EVA-A, and that no system exceeds 0.5 on both "
                "EVA-A and EVA-X pass@1; it uses bot-to-bot simulations, "
                "not human-in-the-loop for every score."
            ),
        }

        out = _validate_and_shuffle_quiz_item(item)

        assert out is not None
        assert out["answer"] == item["options"][0]


def _make_valid_item(question: str = "Q", answer: str = "B") -> dict:
    return {
        "question": question,
        "options": ["A", "B", "C", "D"],
        "answer": answer,
        "explanation": "because " + answer,
    }


class TestValidation:
    def test_happy_path_keeps_all_three(self):
        items = [_make_valid_item(f"Q{i}", "B") for i in range(3)]
        result = _validate_and_shuffle_weekly_quiz(items)
        assert len(result) == 3
        for r in result:
            assert r["answer"] == "B"
            assert set(r["options"]) == {"A", "B", "C", "D"}
            assert r["answer"] in r["options"]

    def test_drops_wrong_option_count(self):
        items = [{"question": "Q", "options": ["A", "B", "C"], "answer": "B", "explanation": ""}]
        assert _validate_and_shuffle_weekly_quiz(items) == []

    def test_drops_answer_not_in_options(self):
        items = [{"question": "Q", "options": ["A", "B", "C", "D"], "answer": "X", "explanation": ""}]
        assert _validate_and_shuffle_weekly_quiz(items) == []

    def test_drops_empty_question(self):
        items = [{"question": "", "options": ["A", "B", "C", "D"], "answer": "A", "explanation": ""}]
        assert _validate_and_shuffle_weekly_quiz(items) == []

    def test_drops_non_dict_entries(self):
        items = ["not a dict", None, 42, ["list"]]
        assert _validate_and_shuffle_weekly_quiz(items) == []

    def test_drops_options_not_a_list(self):
        items = [{"question": "Q", "options": "A,B,C,D", "answer": "A", "explanation": ""}]
        assert _validate_and_shuffle_weekly_quiz(items) == []

    def test_trims_excess_to_three(self):
        items = [_make_valid_item(f"Q{i}", "A") for i in range(10)]
        result = _validate_and_shuffle_weekly_quiz(items)
        assert len(result) == 3

    def test_non_list_input_returns_empty(self):
        assert _validate_and_shuffle_weekly_quiz(None) == []
        assert _validate_and_shuffle_weekly_quiz({}) == []
        assert _validate_and_shuffle_weekly_quiz("string") == []
        assert _validate_and_shuffle_weekly_quiz(42) == []

    def test_mixed_valid_invalid_keeps_valid(self):
        items = [
            _make_valid_item("Q1", "A"),
            "invalid",
            _make_valid_item("Q2", "B"),
            {"question": "Q3", "options": ["A"], "answer": "A", "explanation": ""},
        ]
        result = _validate_and_shuffle_weekly_quiz(items)
        assert len(result) == 2
        assert result[0]["question"] == "Q1"
        assert result[1]["question"] == "Q2"

    def test_preserves_explanation(self):
        items = [{
            "question": "Q", "options": ["A", "B", "C", "D"],
            "answer": "C", "explanation": "Because C rocks.",
        }]
        result = _validate_and_shuffle_weekly_quiz(items)
        assert result[0]["explanation"] == "Because C rocks."

    def test_strips_whitespace_in_strings(self):
        items = [{
            "question": "  Q  ", "options": ["  A  ", "B", "C", "D"],
            "answer": "A", "explanation": "  exp  ",
        }]
        result = _validate_and_shuffle_weekly_quiz(items)
        assert result[0]["question"] == "Q"
        # Stripped option "A" must equal the stripped answer "A"
        assert "A" in result[0]["options"]
        assert result[0]["answer"] == "A"
        assert result[0]["explanation"] == "exp"


class TestShuffleDistribution:
    """Shuffle must counter the LLM's tendency to place correct answers in the first
    few positions. Over many runs, the correct-answer index should be ~uniform.
    """

    def test_answer_position_uniform_over_1000_runs(self):
        """Over 1000 shuffles of ['WRONG_A','WRONG_B','CORRECT','WRONG_D'],
        the final index of 'CORRECT' should hit each of the 4 positions
        roughly 250 times (tolerance +/- 5pp = +/- 50).
        """
        N = 1000
        position_counter: Counter = Counter()

        for _ in range(N):
            items = [{
                "question": "Q",
                "options": ["WRONG_A", "WRONG_B", "CORRECT", "WRONG_D"],
                "answer": "CORRECT",
                "explanation": "",
            }]
            result = _validate_and_shuffle_weekly_quiz(items)
            assert len(result) == 1
            idx = result[0]["options"].index("CORRECT")
            position_counter[idx] += 1

        expected_per_slot = N // 4
        tolerance = N * 0.05
        for slot in range(4):
            observed = position_counter[slot]
            assert abs(observed - expected_per_slot) <= tolerance, (
                f"Slot {slot}: observed {observed}/{N}, "
                f"expected ~{expected_per_slot} (+/- {int(tolerance)})"
            )

    def test_shuffle_actually_reorders_sometimes(self):
        """Out of 20 shuffles of a 4-element list, at least one result must differ
        from the input order. Probability of 20 identity shuffles = (1/24)^20 ~ 0,
        so this effectively proves the shuffle runs.
        """
        seen_different = False
        for _ in range(20):
            items = [{
                "question": "Q", "options": ["A", "B", "C", "D"],
                "answer": "A", "explanation": "",
            }]
            result = _validate_and_shuffle_weekly_quiz(items)
            assert set(result[0]["options"]) == {"A", "B", "C", "D"}
            if result[0]["options"] != ["A", "B", "C", "D"]:
                seen_different = True
                break
        assert seen_different, "20 shuffles all produced identity order — shuffle not running"

    def test_each_item_shuffled_independently(self):
        """All 3 items must be shuffled independently, not with a shared permutation.
        Over 100 runs with 3 identical input items, we should see runs where the
        3 items end up in DIFFERENT orders.
        """
        saw_different_orders = False
        for _ in range(100):
            items = [
                {"question": f"Q{i}", "options": ["A", "B", "C", "D"], "answer": "A", "explanation": ""}
                for i in range(3)
            ]
            result = _validate_and_shuffle_weekly_quiz(items)
            orders = [tuple(r["options"]) for r in result]
            if len(set(orders)) > 1:
                saw_different_orders = True
                break
        assert saw_different_orders, (
            "Over 100 runs, 3 items always produced identical permutations — "
            "shuffle is shared across items, not independent"
        )
