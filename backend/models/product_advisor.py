"""Pydantic models for Product AI Advisor."""

from pydantic import BaseModel
from typing import Literal


class ProductGenerateRequest(BaseModel):
    action: Literal[
        "generate_from_url",
        "generate_search_corpus",
        "tagline_en",
        "tagline_ko",
        "description_en",
        "description_ko",
    ]
    url: str | None = None
    name: str | None = None
    context: str | None = None  # optional existing content for context


class ProductGenerateResponse(BaseModel):
    action: str
    success: bool
    result: str | dict
    model_used: str
    tokens_used: int
