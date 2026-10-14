import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.agents.quiz_verifier import apply_quiz_verdict, verify_quiz

QUIZ = {
    "question": "What does the digest say about Muse integrations?",
    "options": ["They connect automatically", "They need user permission", "They exist everywhere", "They replace tools"],
    "answer": "They connect automatically",
    "explanation": "Integrations need user permission and partner availability; nothing switches automatically.",
}


def _verdict(verdict: str, *, better: str | None = None, explanation_consistent: bool = True) -> dict:
    return {
        "marked_answer_supported": verdict == "ok",
        "explanation_consistent": explanation_consistent,
        "better_option": better,
        "verdict": verdict,
        "evidence": "body passage",
    }


def test_ok_verdict_keeps_quiz_unchanged():
    quiz, action = apply_quiz_verdict(QUIZ, _verdict("ok"))
    assert quiz == QUIZ and action == "kept"


def test_index_slip_is_repaired_when_explanation_already_disagrees():
    # Both real production errors had this shape: explanation right, answer wrong.
    quiz, action = apply_quiz_verdict(
        QUIZ, _verdict("wrong_answer", better="They need user permission", explanation_consistent=False),
    )
    assert action == "answer_fixed"
    assert quiz["answer"] == "They need user permission"
    assert quiz["options"] == QUIZ["options"] and QUIZ["answer"] == "They connect automatically"


def test_wrong_answer_rejected_when_explanation_backs_the_wrong_answer():
    # Swapping the answer would leave an explanation that argues for the wrong option.
    quiz, action = apply_quiz_verdict(
        QUIZ, _verdict("wrong_answer", better="They need user permission", explanation_consistent=True),
    )
    assert quiz is None and action == "rejected"


def test_wrong_answer_rejected_when_better_option_not_in_options():
    quiz, action = apply_quiz_verdict(
        QUIZ, _verdict("wrong_answer", better="Something paraphrased", explanation_consistent=False),
    )
    assert quiz is None and action == "rejected"


@pytest.mark.parametrize("verdict", ["ambiguous", "ungrounded"])
def test_ambiguous_and_ungrounded_are_rejected(verdict):
    quiz, action = apply_quiz_verdict(QUIZ, _verdict(verdict))
    assert quiz is None and action == "rejected"


@pytest.mark.asyncio
async def test_verify_quiz_sends_body_and_quiz_and_returns_verdict_with_usage():
    payload = _verdict("ok")
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))],
        usage=SimpleNamespace(prompt_tokens=900, completion_tokens=80, total_tokens=980, prompt_tokens_details=None),
        service_tier="flex",
    )
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)

    verdict, usage = await verify_quiz(client, "gpt-6.1-sol", "the body text", QUIZ)

    assert verdict == payload
    assert usage["input_tokens"] == 900
    sent = client.chat.completions.create.call_args.kwargs
    assert sent["model"] == "gpt-6.1-sol"
    assert sent["response_format"]["type"] == "json_schema"
    user_msg = sent["messages"][-1]["content"]
    assert "the body text" in user_msg and QUIZ["question"] in user_msg
