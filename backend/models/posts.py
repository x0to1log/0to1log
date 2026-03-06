from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from models.common import PromptGuideItems, RelatedNews


class PostDraftListItem(BaseModel):
    """Draft list endpoint response item — summary view."""
    id: str
    title: str
    slug: str
    category: str
    post_type: Optional[str] = None
    status: str
    news_temperature: Optional[int] = None
    pipeline_batch_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PostDraftDetail(BaseModel):
    """Draft detail endpoint response — full view."""
    id: str
    title: str
    slug: str
    category: str
    post_type: Optional[str] = None
    status: str
    locale: str = "en"

    # Research fields
    content_original: Optional[str] = None
    has_news: Optional[bool] = None
    no_news_notice: Optional[str] = None
    recent_fallback: Optional[str] = None

    # Business persona fields
    content_beginner: Optional[str] = None
    content_learner: Optional[str] = None
    content_expert: Optional[str] = None

    # Shared structured fields
    guide_items: Optional[PromptGuideItems] = None
    related_news: Optional[RelatedNews] = None
    source_urls: list[str] = []
    news_temperature: Optional[int] = None
    tags: list[str] = []

    # Pipeline metadata
    pipeline_batch_id: Optional[str] = None
    translation_group_id: Optional[str] = None
    source_post_id: Optional[str] = None
    source_post_version: Optional[int] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None


class PostUpdateRequest(BaseModel):
    """PATCH /admin/posts/{id}/update request body."""
    title: Optional[str] = None
    content_original: Optional[str] = None
    content_beginner: Optional[str] = None
    content_learner: Optional[str] = None
    content_expert: Optional[str] = None
    guide_items: Optional[PromptGuideItems] = None
    related_news: Optional[RelatedNews] = None
    tags: Optional[list[str]] = None


class PostPublishResponse(BaseModel):
    """PATCH /admin/posts/{id}/publish response."""
    id: str
    slug: str
    status: str
    published_at: datetime


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str


class HealthResponse(BaseModel):
    """GET /health response."""
    status: str
    timestamp: str


class PipelineAcceptedResponse(BaseModel):
    """POST /cron/news-pipeline 202 response."""
    accepted: bool
    message: str
