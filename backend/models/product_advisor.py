"""Pydantic models for Product AI Advisor."""

from pydantic import BaseModel, Field
from typing import Literal


class ProductGenerateRequest(BaseModel):
    action: Literal[
        "generate_from_url",
        "generate_search_corpus",
        "pricing_detail",
        "tagline_en",
        "tagline_ko",
        "description_en",
        "description_ko",
    ]
    url: str | None = None
    name: str | None = None
    slug: str | None = None
    context: str | None = None  # optional existing content for context


class ProductGenerateResponse(BaseModel):
    action: str
    success: bool
    result: str | dict
    model_used: str
    tokens_used: int


# -----------------------------------------------------------------------------
# Structured output schemas for LLM responses (OpenAI json_schema strict mode).
#
# Why Pydantic here: OpenAI "strict" mode enforces these counts/enums at API
# level and auto-retries on violations → eliminates features count drift,
# EN/KO count mismatch, and malformed enum values that previously slipped
# through json_object mode.
#
# Note: `minLength`/`maxLength` on string fields is NOT supported in strict
# mode — we keep those constraints in the prompt (e.g. tagline ≤ 12 words).
# -----------------------------------------------------------------------------

PRODUCT_CATEGORY = Literal[
    "assistant", "image", "video", "audio", "coding",
    "workflow", "builder", "platform", "research", "community",
]
PRICING_LABEL = Literal["free", "freemium", "paid", "enterprise"]
PLATFORM = Literal["web", "ios", "android", "api", "desktop"]


class ProductProfileEN(BaseModel):
    """Strict schema for the EN profile (13 fields)."""
    name: str
    tagline: str
    description_en: str
    pricing: PRICING_LABEL | None
    platform: list[PLATFORM]
    korean_support: bool
    tags: list[str] = Field(min_length=3, max_length=5)
    primary_category: PRODUCT_CATEGORY
    secondary_categories: list[PRODUCT_CATEGORY]
    features: list[str] = Field(min_length=3, max_length=5)
    use_cases: list[str] = Field(min_length=2, max_length=3)
    getting_started: list[str] = Field(min_length=3, max_length=3)
    pricing_detail: str | None


class ProductProfileKO(BaseModel):
    """Strict schema for the KO profile (7 fields).

    features_ko / use_cases_ko / getting_started_ko share EN's count bounds.
    The 'count must match EN exactly' rule stays in the prompt — schema
    enforces the legal range (3-5, 2-3, 3) but can't cross-reference EN.
    """
    name_ko: str | None
    tagline_ko: str
    description_ko: str
    features_ko: list[str] = Field(min_length=3, max_length=5)
    use_cases_ko: list[str] = Field(min_length=2, max_length=3)
    getting_started_ko: list[str] = Field(min_length=3, max_length=3)
    pricing_detail_ko: str | None
