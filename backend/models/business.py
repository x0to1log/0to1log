from typing import Optional

from pydantic import BaseModel, field_validator

from models.common import PromptGuideItems, RelatedNews


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

    @field_validator("news_temperature")
    @classmethod
    def clamp_temperature(cls, v: int) -> int:
        return max(1, min(5, v))
