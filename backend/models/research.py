from pydantic import BaseModel, field_validator
from typing import Optional

from models.common import PromptGuideItems


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

    @field_validator("news_temperature")
    @classmethod
    def clamp_temperature(cls, v: int) -> int:
        return max(1, min(5, v))
