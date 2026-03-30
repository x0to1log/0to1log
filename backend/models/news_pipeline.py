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


class ClassifiedCandidate(BaseModel):
    """News candidate classified into a category and subcategory."""
    title: str
    url: str
    snippet: str = ""
    source: str = "tavily"
    category: str  # "research" or "business"
    subcategory: str  # e.g., "llm_models", "open_source", "papers", "big_tech", "industry", "new_tools"
    relevance_score: float = 0.0
    reason: str = ""


class GroupedItem(BaseModel):
    """Individual item within a classified group."""
    url: str
    title: str


class ClassifiedGroup(BaseModel):
    """Group of related news items classified together."""
    group_title: str
    items: list[GroupedItem]
    category: str  # "research" or "business"
    subcategory: str
    relevance_score: float = 0.0
    reason: str = ""

    @property
    def primary_url(self) -> str:
        """First item's URL — used for community lookup, ranking compatibility."""
        return self.items[0].url if self.items else ""

    @property
    def urls(self) -> list[str]:
        """All URLs in this group."""
        return [item.url for item in self.items]


class ClassificationResult(BaseModel):
    """LLM classification output — grouped candidates per category."""
    research: list[ClassifiedGroup] = []
    business: list[ClassifiedGroup] = []
    # Flat picks from classify step (before merge)
    research_picks: list[ClassifiedCandidate] = []
    business_picks: list[ClassifiedCandidate] = []


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
    status: str = "complete"
    message: str = ""
    posts_created: int = 0
    errors: list[str] = []
    usage: dict = Field(default_factory=dict)
