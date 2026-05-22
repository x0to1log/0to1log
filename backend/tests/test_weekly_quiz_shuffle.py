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

    def test_blank_option_rejected(self):
        item = self._valid()
        item["options"] = ["A", " ", "C", "D"]
        item["answer_index"] = 0
        item.pop("answer", None)

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

    def test_unique_long_answer_hint_is_rejected(self):
        item = {
            "question": "What is the safest takeaway?",
            "options": [
                "Local testing is possible.",
                "Quality is guaranteed.",
                "Remote GPUs are required.",
                (
                    "Local testing is possible, but the team still needs "
                    "task-specific quality checks before production use."
                ),
            ],
            "answer_index": 3,
            "explanation": (
                "The digest says local testing is possible and explains that "
                "teams still need task-specific quality checks."
            ),
        }

        assert _validate_and_shuffle_quiz_item(item) is None

    def test_tied_long_answer_is_not_rejected_as_length_hint(self):
        item = {
            "question": "What is the safest takeaway?",
            "options": [
                "Local testing is possible, but teams still need targeted quality checks.",
                "Remote use is possible, but teams still need targeted privacy checks.",
                "Studio quality is guaranteed for all teams and tasks.",
                "The release removes the need for further listening tests.",
            ],
            "answer_index": 0,
            "explanation": (
                "The digest says local testing is possible but teams still need "
                "targeted quality checks."
            ),
        }

        out = _validate_and_shuffle_quiz_item(item)

        assert out is not None
        assert out["answer"] == item["options"][0]

    def test_answer_index_repaired_when_explanation_supports_a_different_option(self):
        item = {
            "question": "Which pairing best captures the operational constraint and measured impact reported for Switchcraft?",
            "options": [
                "Throughput ceiling; 48% tool-call reduction at 1.7% accuracy loss across simulated agents",
                "Memory budget; 46.6% perplexity improvement on long-form language modeling tasks",
                "Latency budget; 82.9% accuracy with an 84% inference-cost reduction and $3,600 saved per million queries",
                "Token limit; 3x sample-efficiency over parameter-only RL during tool-use training",
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

    def test_repair_does_not_select_option_labeled_incorrect(self):
        item = {
            "question": "Which limitation most affects production-scale trust?",
            "options": [
                "The evidence is preliminary, so large-scale gains still need validation.",
                "The method has no code available, so it cannot be reproduced.",
                "The selection step is gradient-free, which makes standard optimization impossible.",
                "The paper proves universal linear scaling across every hardware setup.",
            ],
            "answer_index": 0,
            "explanation": (
                "The strongest caveat is that experiments are preliminary and small-scale, "
                "lacking explicit wall-clock breakdowns. Option 2 is incorrect because "
                "gradient-free selection avoids a costly backward kernel; it does not make "
                "optimization impossible."
            ),
        }

        out = _validate_and_shuffle_quiz_item(item)

        assert out is not None
        assert out["answer"] == item["options"][0]

    def test_repair_selects_training_wrapper_over_inference_distractor(self):
        item = {
            "question": (
                "What is the key functional change Lighthouse Attention introduces, "
                "and why does that matter for models trained on very long contexts?"
            ),
            "options": [
                "It replaces standard attention permanently with a subquadratic kernel so deployed models use less memory and lower inference latency at serving time.",
                "It wraps standard attention during most of training to compress long sequences and is removed in a short recovery stage, lowering training time and memory without changing inference behavior.",
                "It accelerates inference by removing attention computation at serving time and routing tokens to fewer experts while changing deployed model behavior.",
                "It requires a new complex backward-pass kernel during training, which increases implementation difficulty but reduces inference cost after deployment.",
            ],
            "answer_index": 0,
            "explanation": (
                "Lighthouse is a training-time wrapper that hierarchically compresses "
                "long sequences during most of pretraining and then is removed in a "
                "brief recovery stage so the final model uses ordinary attention at "
                "inference. That matters because it reduces the quadratic training-time "
                "costs associated with very long contexts while leaving inference-time "
                "behavior unchanged. The one option is wrong because the method is "
                "explicitly training-only and does not change deployed inference kernels. "
                "The one option confuses Lighthouse with expert routing methods and is "
                "wrong. The one option is wrong because the selection step is gradient-free, "
                "avoiding a complex custom backward kernel."
            ),
        }

        out = _validate_and_shuffle_quiz_item(item)

        assert out is not None
        assert out["answer"] == item["options"][1]

    def test_repair_does_not_override_tide_answer_due_question_overlap(self):
        item = {
            "question": (
                "What does TIDE do to speed up diffusion MoE LLM inference "
                "without retraining, according to the digest?"
            ),
            "options": [
                "It cuts expert I/O by exploiting temporal stability of expert activations and refreshes expert placement at optimized intervals.",
                "It converts the diffusion decoder into an autoregressive decoder to avoid parallel expert I/O.",
                "It fine-tunes the model to use fewer experts per token so less data is moved during diffusion decoding.",
                "It compresses expert activations with lossy quantization to reduce CPU-GPU transfer volume.",
            ],
            "answer_index": 0,
            "explanation": (
                "The digest describes TIDE as an inference-time, lossless optimization "
                "that exploits temporal stability of expert activations and uses "
                "interval-based expert refreshes to reduce expert I/O and CPU work "
                "without retraining."
            ),
        }

        out = _validate_and_shuffle_quiz_item(item)

        assert out is not None
        assert out["answer"] == item["options"][0]

    def test_repair_does_not_select_negated_rope_distractor(self):
        item = {
            "question": (
                "According to the digest, what is the correct practical takeaway "
                "about increasing the RoPE base to extend context length?"
            ),
            "options": [
                "Raising the RoPE base forces a trade-off: it can help distinguish tokens but degrades the model's ability to distinguish positions.",
                "Minor changes to RoPE base can be compensated by stacking more heads and layers, so there is no need to change positional encodings.",
                "Raising the RoPE base is a free win: it preserves both token and position discrimination at larger lengths.",
                "Setting a very large RoPE base completely eliminates the randomization effect and restores locality bias at extreme lengths.",
            ],
            "answer_index": 0,
            "explanation": (
                "The digest explains the paper proves a trade-off: increasing the RoPE "
                "base helps tell tokens apart but sacrifices the ability to distinguish "
                "positions, and stacking heads/layers does not overcome this theoretical "
                "limit."
            ),
        }

        out = _validate_and_shuffle_quiz_item(item)

        assert out is not None
        assert out["answer"] == item["options"][0]

    def test_repair_handles_curly_apostrophe_negation_in_correct_option(self):
        item = {
            "question": (
                "Which safe conclusion should you draw from the digest about "
                "Lighthouse Attention and its effect on deployed models?"
            ),
            "options": [
                "Lighthouse is a drop-in inference optimization you can enable on production servers without retraining.",
                "Lighthouse makes models less accurate at the end of training because it replaces full attention throughout the model's lifetime.",
                "Lighthouse reduces pretraining compute and memory needs but is removed before deployment, so it doesn’t change inference behavior.",
                "Lighthouse permanently changes the model so deployed systems will run a different, faster attention kernel at inference.",
            ],
            "answer_index": 1,
            "explanation": (
                "The digest clearly states that Lighthouse is a training-only wrapper "
                "that compresses sequences during most pretraining and is removed in "
                "a recovery phase so the final model uses ordinary full attention at "
                "inference. Therefore it reduces training cost without altering deployed "
                "inference behavior. The other options are incorrect: it does not change "
                "the inference kernel permanently, the reported experiments do not claim "
                "worse final accuracy, and it is not an inference-time toggle that can "
                "be enabled without retraining."
            ),
        }

        out = _validate_and_shuffle_quiz_item(item)

        assert out is not None
        assert out["answer"] == item["options"][2]

    def test_explanation_position_markers_are_removed_before_shuffle(self):
        item = {
            "question": "무엇이 가장 안전한 해석인가?",
            "options": [
                "잘못된 배포 과장",
                "본문과 맞는 신중한 해석",
                "근거 없는 자동화 주장",
                "전문가 조언 대체 주장",
            ],
            "answer_index": 1,
            "explanation": (
                "정답(1): 본문과 맞는 신중한 해석입니다. "
                "(0)은 틀렸습니다. Option 3 is incorrect because it overclaims."
            ),
        }

        out = _validate_and_shuffle_quiz_item(item)

        assert out is not None
        assert out["answer"] == "본문과 맞는 신중한 해석"
        assert "정답(1)" not in out["explanation"]
        assert "(0)" not in out["explanation"]
        assert "Option 3" not in out["explanation"]

    def test_korean_ordinal_option_markers_are_removed_before_shuffle(self):
        item = {
            "question": "요약에 따르면 가장 안전한 결론은 무엇인가?",
            "options": [
                "잘못된 첫 번째 보기",
                "본문에 근거한 안전한 결론",
                "과장된 세 번째 보기",
                "근거 없는 네 번째 보기",
            ],
            "answer_index": 1,
            "explanation": (
                "정답은 두 번째 옵션입니다. 본문에 근거한 안전한 결론입니다. "
                "첫 번째 옵션은 틀렸습니다. Option 4 is also wrong."
            ),
        }

        out = _validate_and_shuffle_quiz_item(item)

        assert out is not None
        assert out["answer"] == "본문에 근거한 안전한 결론"
        assert "정답은 두 번째 옵션" not in out["explanation"]
        assert "첫 번째 옵션" not in out["explanation"]
        assert "Option 4" not in out["explanation"]

    def test_correct_answer_labels_are_removed_before_shuffle(self):
        item = {
            "question": "According to the digest, what changed?",
            "options": [
                "The unsupported overclaim",
                "The grounded takeaway",
                "The unrelated metric",
                "The opposite of the digest",
            ],
            "answer_index": 1,
            "explanation": (
                "Correct: The correct answer is the grounded takeaway because the "
                "digest states this directly."
            ),
        }

        out = _validate_and_shuffle_quiz_item(item)

        assert out is not None
        assert out["answer"] == "The grounded takeaway"
        assert "Correct:" not in out["explanation"]
        assert "The correct answer is" not in out["explanation"]


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
