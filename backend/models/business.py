from typing import Optional

from pydantic import BaseModel, field_validator

from models.common import PromptGuideItems, RelatedNews


MIN_CONTENT_CHARS = 3000
TARGET_CONTENT_CHARS = 4500


class BusinessPost(BaseModel):
    title: str = ""
    slug: str = ""
    content_beginner: str = ""
    content_learner: str = ""
    content_expert: str = ""
    guide_items: Optional[PromptGuideItems] = None
    related_news: Optional[RelatedNews] = None
    source_urls: list[str] = []
    news_temperature: int = 3  # 1-5
    tags: list[str] = []
    excerpt: str = ""
    focus_items: list[str] = []

    @field_validator("content_beginner", "content_learner", "content_expert")
    @classmethod
    def check_min_length(cls, v: str) -> str:
        if v and len(v) < MIN_CONTENT_CHARS:
            raise ValueError(
                f"Content too short: {len(v)} chars (min {MIN_CONTENT_CHARS})"
            )
        return v

    @field_validator("news_temperature")
    @classmethod
    def clamp_temperature(cls, v: int) -> int:
        return max(1, min(5, v))
