"""Tests for the daily digest quiz-only strict JSON schema."""

import pytest
from pydantic import ValidationError

from services.agents.schemas.news_quiz import (
    QuizOneLocale,
    build_news_quiz_json_schema,
)


def test_quiz_schema_requires_persona_keys_for_one_locale():
    schema = build_news_quiz_json_schema("en")["schema"]

    expected = {"expert", "learner", "beginner"}
    assert set(schema["required"]) == expected
    assert set(schema["properties"]) == expected
    assert schema["additionalProperties"] is False


def test_quiz_schema_uses_answer_index_contract():
    quiz_schema = build_news_quiz_json_schema("ko")["schema"]["properties"]["beginner"]
    props = quiz_schema["properties"]

    assert set(quiz_schema["required"]) == {
        "question",
        "answer_index",
        "options",
        "explanation",
    }
    assert props["answer_index"]["type"] == "integer"
    assert props["answer_index"]["minimum"] == 0
    assert props["answer_index"]["maximum"] == 3
    assert "answer" not in props
    assert props["options"]["minItems"] == 4
    assert props["options"]["maxItems"] == 4
    assert props["options"]["items"]["minLength"] == 1


def test_quiz_schema_rejects_unknown_locale():
    with pytest.raises(ValueError):
        build_news_quiz_json_schema("fr")


def test_quiz_pydantic_model_uses_answer_index():
    valid = QuizOneLocale(
        question="Q",
        answer_index=2,
        options=["a", "b", "c", "d"],
        explanation="Because c.",
    )
    assert valid.answer_index == 2

    with pytest.raises(ValidationError):
        QuizOneLocale(
            question="Q",
            answer_index=5,
            options=["a", "b", "c", "d"],
            explanation="",
        )

    with pytest.raises(ValidationError):
        QuizOneLocale(
            question="Q",
            answer_index=-1,
            options=["a", "b", "c", "d"],
            explanation="",
        )


def test_quiz_pydantic_model_rejects_bool_answer_index():
    with pytest.raises(ValidationError):
        QuizOneLocale(
            question="Q",
            answer_index=True,
            options=["a", "b", "c", "d"],
            explanation="",
        )

    with pytest.raises(ValidationError):
        QuizOneLocale(
            question="Q",
            answer_index=False,
            options=["a", "b", "c", "d"],
            explanation="",
        )
