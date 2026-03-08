from pydantic import BaseModel
from typing import Optional


class QuizPoll(BaseModel):
    question: str = ""
    options: list[str] = []
    answer: str = ""
    explanation: str = ""


class PromptGuideItems(BaseModel):
    one_liner: str = ""
    action_item: str = ""
    critical_gotcha: str = ""
    rotating_item: str = ""  # market_context | analogy | source_check
    quiz_poll: Optional[QuizPoll] = None


class RelatedNewsItem(BaseModel):
    title: str = ""
    url: str = ""
    summary: str = ""


class RelatedNews(BaseModel):
    big_tech: Optional[RelatedNewsItem] = None
    industry_biz: Optional[RelatedNewsItem] = None
    new_tools: Optional[RelatedNewsItem] = None
