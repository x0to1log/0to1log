from pydantic import BaseModel, field_validator
from typing import Optional

from models.common import PromptGuideItems


class ResearchPost(BaseModel):
    has_news: bool
    title: str
    slug: str
    content_original: Optional[str] = None
    no_news_notice: Optional[str] = None
    recent_fallback: Optional[str] = None
    guide_items: Optional[PromptGuideItems] = None
    source_urls: list[str] = []
    news_temperature: int  # 1-5
    tags: list[str] = []

    @field_validator("news_temperature")
    @classmethod
    def validate_temperature(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("news_temperature must be between 1 and 5")
        return v

    @field_validator("content_original")
    @classmethod
    def require_content_when_news(cls, v: Optional[str], info) -> Optional[str]:
        if info.data.get("has_news") and not v:
            raise ValueError("content_original required when has_news is True")
        return v
