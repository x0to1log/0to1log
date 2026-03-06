from pydantic import BaseModel, field_validator

from models.common import PromptGuideItems, RelatedNews


class BusinessPost(BaseModel):
    title: str
    slug: str
    content_beginner: str
    content_learner: str
    content_expert: str
    guide_items: PromptGuideItems
    related_news: RelatedNews
    source_urls: list[str] = []
    news_temperature: int  # 1-5
    tags: list[str] = []

    @field_validator("news_temperature")
    @classmethod
    def validate_temperature(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("news_temperature must be between 1 and 5")
        return v
