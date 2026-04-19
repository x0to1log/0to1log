from pydantic import BaseModel
from typing import Optional


class QuizPoll(BaseModel):
    question: str = ""
    options: list[str] = []
    answer: str = ""
    explanation: str = ""


class RelatedNewsItem(BaseModel):
    title: str = ""
    url: str = ""
    summary: str = ""


class RelatedNews(BaseModel):
    big_tech: Optional[RelatedNewsItem] = None
    industry_biz: Optional[RelatedNewsItem] = None
    new_tools: Optional[RelatedNewsItem] = None



class SourceCard(BaseModel):
    id: str = ""
    title: str = ""
    publisher: str = ""
    url: str = ""
    published_at: str = ""
    evidence_snippet: str = ""
    claim_ids: list[str] = []
