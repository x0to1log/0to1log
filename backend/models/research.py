from pydantic import BaseModel, field_validator
from typing import Optional

from models.common import PromptGuideItems, SourceCard


EN_MIN_CONTENT_CHARS = 5000
KO_MIN_CONTENT_CHARS = 4000
MIN_CONTENT_CHARS = KO_MIN_CONTENT_CHARS
TARGET_CONTENT_CHARS = 8000


class ResearchPost(BaseModel):
    has_news: bool = True
    title: str = ""
    slug: str = ""
    content_original: Optional[str] = None
    no_news_notice: Optional[str] = None
    recent_fallback: Optional[str] = None
    guide_items: Optional[PromptGuideItems] = None
    source_urls: list[str] = []
    news_temperature: int = 3  # 1-5
    tags: list[str] = []
    excerpt: str = ""
    focus_items: list[str] = []
    source_cards: list[SourceCard] = []

    @field_validator("content_original")
    @classmethod
    def check_min_length(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) < MIN_CONTENT_CHARS:
            raise ValueError(
                f"Content too short: {len(v)} chars (min {MIN_CONTENT_CHARS})"
            )
        return v

    @field_validator("news_temperature")
    @classmethod
    def clamp_temperature(cls, v: int) -> int:
        return max(1, min(5, v))
