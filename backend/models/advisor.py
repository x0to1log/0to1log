from pydantic import BaseModel
from typing import Literal, Optional


class AiAdviseRequest(BaseModel):
    action: Literal["generate", "seo", "review", "factcheck"]
    post_id: str
    title: str
    content: str
    category: str
    tags: list[str] = []
    excerpt: str = ""
    slug: str = ""
    post_type: str = ""
    guide_items: Optional[dict] = None


class AiAdviseResponse(BaseModel):
    action: str
    success: bool
    result: dict
    model_used: str
    tokens_used: int


# --- Per-action result models (for validation) ---

class GenerateResult(BaseModel):
    guide_items: dict
    excerpt: str
    tags: list[str]
    slug: str


class SeoResult(BaseModel):
    title_suggestions: list[str]
    tag_recommendations: list[str]
    excerpt_suggestion: str
    seo_notes: str


class ReviewChecklistItem(BaseModel):
    category: str
    status: Literal["pass", "warn", "fail"]
    message: str


class ReviewResult(BaseModel):
    checklist: list[ReviewChecklistItem]
    summary: str
    score: int


class FactcheckClaim(BaseModel):
    claim: str
    verdict: Literal["verified", "unverified", "no_source"]
    source: Optional[str] = None
    note: str = ""


class FactcheckResult(BaseModel):
    claims: list[FactcheckClaim]
    broken_links: list[str] = []
    missing_labels: list[str] = []
    overall_confidence: Literal["high", "medium", "low"]
