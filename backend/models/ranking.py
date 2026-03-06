from pydantic import BaseModel
from typing import Optional


class NewsCandidate(BaseModel):
    title: str
    url: str
    snippet: str
    source: str  # tavily | hackernews | github


class RankedCandidate(BaseModel):
    title: str
    url: str
    snippet: str
    source: str
    assigned_type: str  # research | business_main | big_tech | industry_biz | new_tools
    relevance_score: float  # 0.0 - 1.0
    ranking_reason: str


class RelatedPicks(BaseModel):
    big_tech: Optional[RankedCandidate] = None
    industry_biz: Optional[RankedCandidate] = None
    new_tools: Optional[RankedCandidate] = None


class NewsRankingResult(BaseModel):
    research_pick: RankedCandidate
    business_main_pick: RankedCandidate
    related_picks: RelatedPicks
