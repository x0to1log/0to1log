"""Pydantic models for Blog AI Advisor (separate from News advisor)."""

from pydantic import BaseModel
from typing import Literal


# ---------------------------------------------------------------------------
# Blog Advise (all actions except translate)
# ---------------------------------------------------------------------------

class BlogAdviseRequest(BaseModel):
    action: Literal[
        "outline", "draft", "rewrite", "suggest",
        "review", "generate",
        "conceptcheck", "voicecheck", "retrocheck",
    ]
    post_id: str
    title: str
    content: str
    category: str
    tags: list[str] = []
    excerpt: str = ""
    slug: str = ""


class BlogAdviseResponse(BaseModel):
    action: str
    success: bool
    result: dict
    model_used: str
    tokens_used: int


# ---------------------------------------------------------------------------
# Per-action result models (new blog-only actions)
# ---------------------------------------------------------------------------

class OutlineSection(BaseModel):
    heading: str
    subsections: list[str] = []
    description: str = ""


class OutlineResult(BaseModel):
    sections: list[OutlineSection]


class DraftResult(BaseModel):
    content: str


class RewriteChange(BaseModel):
    section: str
    before: str
    after: str
    reason: str


class RewriteResult(BaseModel):
    changes: list[RewriteChange]


class SuggestItem(BaseModel):
    section: str
    type: Literal["add", "remove", "strengthen", "restructure"]
    message: str
    priority: Literal["high", "medium", "low"]


class SuggestResult(BaseModel):
    suggestions: list[SuggestItem]


# ---------------------------------------------------------------------------
# Blog Translate
# ---------------------------------------------------------------------------

class BlogTranslateRequest(BaseModel):
    source_post_id: str
    title: str
    content: str
    excerpt: str = ""
    tags: list[str] = []
    category: str
    locale: str  # source locale — target is the opposite


class BlogTranslateResponse(BaseModel):
    success: bool
    translated_post_id: str
    translated_slug: str
    target_locale: str
    translation_group_id: str
    model_used: str
    tokens_used: int
