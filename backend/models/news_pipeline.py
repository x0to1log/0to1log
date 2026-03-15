"""Pydantic models for AI News Pipeline v2."""
from pydantic import BaseModel, Field
from typing import Optional


class NewsCandidate(BaseModel):
    """Raw news item from Tavily search."""
    title: str
    url: str
    snippet: str = ""
    source: str = "tavily"
    raw_content: str = ""


class RankedCandidate(BaseModel):
    """News candidate after LLM ranking."""
    title: str
    url: str
    snippet: str = ""
    source: str = "tavily"
    assigned_type: str  # "research" or "business"
    relevance_score: float = 0.0
    ranking_reason: str = ""


class RankingResult(BaseModel):
    """LLM ranking output."""
    research: Optional[RankedCandidate] = None
    business: Optional[RankedCandidate] = None


class FactClaim(BaseModel):
    id: str
    claim: str
    why_it_matters: str = ""
    source_ids: list[str] = []
    confidence: str = "medium"


class FactNumber(BaseModel):
    value: str
    context: str = ""
    source_id: str = ""


class FactEntity(BaseModel):
    name: str
    role: str = ""
    url: str = ""


class FactSource(BaseModel):
    id: str
    title: str = ""
    publisher: str = ""
    url: str = ""
    published_at: str = ""


class FactPack(BaseModel):
    """Structured facts extracted from a news article + community reactions."""
    headline: str
    headline_ko: str = ""
    key_facts: list[FactClaim] = []
    numbers: list[FactNumber] = []
    entities: list[FactEntity] = []
    sources: list[FactSource] = []
    community_summary: str = ""


class PersonaOutput(BaseModel):
    """EN+KO content from a single persona LLM call."""
    en: str = ""
    ko: str = ""


class PipelineResult(BaseModel):
    """Final result of the daily pipeline run."""
    batch_id: str
    posts_created: int = 0
    errors: list[str] = []
    usage: dict = Field(default_factory=dict)
