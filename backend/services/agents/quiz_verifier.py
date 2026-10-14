"""Verify a generated quiz's marked answer against the body it was written from.

Used by daily quiz generation (pipeline_digest._generate_digest_quizzes) before
quizzes are saved, and by scripts/audit_daily_quizzes.py for published posts.

Why: the generator occasionally marks a wrong option while the explanation
argues for the right one (2 of 2 errors found on 2026-10-14), the explanation
repair heuristic does not fire on Korean text, and the QC rubric scores quiz
answers only for the Beginner persona.
"""
from __future__ import annotations

import json
from typing import Any

from services.agents.client import (
    build_completion_kwargs,
    extract_usage_metrics,
    with_flex_retry,
)

QUIZ_VERIFY_SYSTEM_PROMPT = """You verify one multiple-choice quiz against the article body it was written from.
Use ONLY the body. Do not use outside knowledge.

Decide:
- marked_answer_supported: the body supports the option marked as `answer` as the correct choice.
- explanation_consistent: the explanation supports the marked answer and does not contradict it.
- better_option: if a DIFFERENT option is what the body actually supports, copy it verbatim; otherwise null.
- verdict:
  - "ok": marked answer is supported, explanation agrees, no other option is equally correct.
  - "wrong_answer": the body supports a different option than the one marked.
  - "ambiguous": two or more options are defensible from the body.
  - "ungrounded": the body does not contain enough to answer the question.
- evidence: at most 2 sentences quoting or paraphrasing the decisive body passage.

The body and quiz may be Korean; reason in that language but write evidence in English."""

QUIZ_VERIFY_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "quiz_verify",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "marked_answer_supported": {"type": "boolean"},
                "explanation_consistent": {"type": "boolean"},
                "better_option": {"type": ["string", "null"]},
                "verdict": {"type": "string", "enum": ["ok", "wrong_answer", "ambiguous", "ungrounded"]},
                "evidence": {"type": "string"},
            },
            "required": ["marked_answer_supported", "explanation_consistent", "better_option", "verdict", "evidence"],
            "additionalProperties": False,
        },
    },
}


async def verify_quiz(
    client: Any,
    model: str,
    body: str,
    quiz: dict[str, Any],
    *,
    service_tier: str = "flex",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (verdict, usage). Raises on API errors; callers decide fail-open."""
    shown = {k: quiz.get(k) for k in ("question", "options", "answer", "explanation")}
    messages = [
        {"role": "system", "content": QUIZ_VERIFY_SYSTEM_PROMPT},
        {"role": "user", "content": f"=== BODY ===\n{body}\n\n=== QUIZ ===\n{json.dumps(shown, ensure_ascii=False)}"},
    ]
    kwargs = build_completion_kwargs(
        model=model,
        messages=messages,
        max_tokens=600,
        response_format=QUIZ_VERIFY_RESPONSE_FORMAT,
        reasoning_effort="medium",
        service_tier=service_tier,
        prompt_cache_key="quiz-verify",
    )
    response = await with_flex_retry(lambda: client.chat.completions.create(**kwargs))
    verdict = json.loads(response.choices[0].message.content or "{}")
    usage = extract_usage_metrics(response, model, requested_service_tier=service_tier)
    return verdict, usage


def apply_quiz_verdict(quiz: dict[str, Any], verdict: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Decide what to do with a quiz given its verdict.

    Returns (quiz_to_keep or None, action) with action in
    {"kept", "answer_fixed", "rejected"}.

    The answer is swapped only for an index slip: the verifier names an option
    the body supports AND says the explanation disagrees with the marked answer,
    so the existing explanation already argues for the new answer. If the
    explanation backs the wrong answer, swapping would leave it contradicting
    the quiz, so the whole quiz is regenerated instead.
    """
    kind = verdict.get("verdict")
    if kind == "ok":
        return quiz, "kept"
    better = verdict.get("better_option")
    if (
        kind == "wrong_answer"
        and better in (quiz.get("options") or [])
        and verdict.get("explanation_consistent") is False
    ):
        return {**quiz, "answer": better}, "answer_fixed"
    return None, "rejected"
