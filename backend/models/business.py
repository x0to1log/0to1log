"""BusinessPost schema — v4 Expert-First Cascade."""

from typing import Any, Optional

from pydantic import BaseModel, field_validator

from models.common import PromptGuideItems, RelatedNews


# --- Length thresholds (v4: all personas equal) ---
EN_MIN_CONTENT_CHARS = 5000      # EN generation floor
KO_MIN_CONTENT_CHARS = 3000      # KO translation floor (~45% of EN, Korean syllable chars)
MIN_CONTENT_CHARS = EN_MIN_CONTENT_CHARS
TARGET_CONTENT_CHARS = 6500      # target 6000-7000
EN_MIN_ANALYSIS_CHARS = 2500
KO_MIN_ANALYSIS_CHARS = 1000
MIN_ANALYSIS_CHARS = EN_MIN_ANALYSIS_CHARS


class BusinessPost(BaseModel):
    """Business Analyst 포스트 검증 스키마 (v4: Expert-First Cascade)."""

    title: str = ""
    slug: str = ""
    fact_pack: dict[str, Any] = {}          # structured facts (key_facts, numbers, entities, timeline)
    source_cards: list[dict[str, Any]] = []  # per-source evidence cards
    content_analysis: str = ""               # shared analysis framework (min 2500 EN / 2000 KO)
    content_beginner: str = ""               # beginner version (min 5000 EN / 4000 KO)
    content_learner: str = ""                # learner version  (min 5000 EN / 4000 KO)
    content_expert: str = ""                 # expert version   (min 5000 EN / 4000 KO)
    guide_items: Optional[PromptGuideItems] = None
    related_news: Optional[RelatedNews] = None
    source_urls: list[str] = []
    news_temperature: int = 3  # 1-5
    tags: list[str] = []
    excerpt: str = ""
    focus_items: list[str] = []

    @field_validator("fact_pack", mode="before")
    @classmethod
    def coerce_fact_pack(cls, v: Any) -> dict[str, Any]:
        if isinstance(v, list):
            return {"items": v}
        return v

    @field_validator("content_analysis")
    @classmethod
    def check_analysis_min_length(cls, v: str) -> str:
        if v and len(v) < KO_MIN_ANALYSIS_CHARS:
            raise ValueError(
                f"Content too short: {len(v)} chars (min {KO_MIN_ANALYSIS_CHARS})"
            )
        return v

    @field_validator("content_beginner", "content_learner", "content_expert")
    @classmethod
    def check_min_length(cls, v: str) -> str:
        if v and len(v) < KO_MIN_CONTENT_CHARS:
            raise ValueError(
                f"Content too short: {len(v)} chars (min {KO_MIN_CONTENT_CHARS})"
            )
        return v

    @field_validator("news_temperature")
    @classmethod
    def clamp_temperature(cls, v: int) -> int:
        return max(1, min(5, v))
