"""Pydantic + JSON schema for daily digest quiz-only generation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


DAILY_QUIZ_PERSONAS: tuple[str, ...] = ("expert", "learner", "beginner")
DAILY_QUIZ_LOCALES: tuple[str, ...] = ("en", "ko")


class QuizOneLocale(BaseModel):
    question: str
    answer_index: int = Field(ge=0, le=3)
    options: list[str] = Field(min_length=4, max_length=4)
    explanation: str = ""

    @field_validator("answer_index", mode="before")
    @classmethod
    def reject_bool(cls, v: Any) -> Any:
        # isinstance(True, int) is True in Python. Pydantic would otherwise
        # map True/False to options[1]/options[0].
        if isinstance(v, bool):
            raise ValueError("answer_index must be an integer, not a bool")
        return v


def build_news_quiz_json_schema(locale: str) -> dict[str, Any]:
    """Build strict schema for one locale-specific quiz call."""

    if locale not in DAILY_QUIZ_LOCALES:
        raise ValueError(f"unsupported quiz locale: {locale}")

    keys = list(DAILY_QUIZ_PERSONAS)
    return {
        "name": f"daily_digest_quizzes_{locale}",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": keys,
            "properties": {key: _quiz_locale_schema() for key in keys},
        },
    }


def _quiz_locale_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["question", "answer_index", "options", "explanation"],
        "properties": {
            "question": {"type": "string"},
            "answer_index": {"type": "integer", "minimum": 0, "maximum": 3},
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 4,
                "maxItems": 4,
            },
            "explanation": {"type": "string"},
        },
    }
