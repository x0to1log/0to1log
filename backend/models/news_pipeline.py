"""Pydantic models for the AI News Pipeline."""
from pydantic import BaseModel, Field


class NewsCandidate(BaseModel):
    """Raw news item from Tavily search."""
    title: str
    url: str
    snippet: str = ""
    source: str = "tavily"
    raw_content: str = ""
    source_kind: str = ""
    source_confidence: str = ""
    source_tier: str = ""

class ClassifiedCandidate(BaseModel):
    """News candidate classified into a category and subcategory."""
    title: str
    url: str
    snippet: str = ""
    source: str = "tavily"
    category: str  # "research" or "business"
    subcategory: str  # e.g., "llm_models", "open_source", "papers", "big_tech", "industry", "new_tools"
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
    reason: str = ""

    @property
    def primary_url(self) -> str:
        """First item's URL — used for community lookup, ranking compatibility."""
        return self.items[0].url if self.items else ""

    @property
    def urls(self) -> list[str]:
        """All URLs in this group."""
        return [item.url for item in self.items]


class ThreadInfo(BaseModel):
    """Per-platform community thread record. Each ThreadInfo represents one
    discussion thread (HN OR Reddit) — quotes and sentiment scoped to that
    thread alone, no cross-platform mixing."""
    platform: str  # "hackernews" or "reddit"
    url: str       # thread URL (item?id=... or /r/sub/comments/...)
    subreddit: str | None = None  # only for platform="reddit"
    upvotes: int
    comments: int
    sentiment: str | None = "mixed"  # positive / mixed / negative / neutral / None (off-topic)
    quotes: list[str] = []           # English quotes from THIS thread only
    quotes_ko: list[str] = []        # KO translations, 1:1 with quotes
    key_point: str | None = None     # one-line discussion summary


class CommunityInsight(BaseModel):
    """Summarized community reaction for a news group. Two shapes coexist:
    - NEW: threads (list[ThreadInfo]) carries per-platform records with provenance
    - LEGACY: flat fields (quotes/quotes_ko/source_label/hn_url/reddit_url) for
      backward compatibility with checkpoints from before 2026-04-26
    Use synthesized_threads() to get a uniform list[ThreadInfo] regardless of shape.
    """
    threads: list[ThreadInfo] = []

    # Legacy fields — DO NOT remove; old checkpoint loading depends on them.
    sentiment: str = "neutral"  # positive / mixed / negative / neutral
    quotes: list[str] = []  # 0-2 representative quotes (English original)
    quotes_ko: list[str] = []  # 0-2 Korean translations of quotes
    key_point: str | None = None  # 1-line discussion summary (English)
    source_label: str = ""  # e.g. "Hacker News 342↑ · 89 comments"
    hn_url: str | None = None  # Hacker News thread URL (if HN discussion found)
    reddit_url: str | None = None  # Reddit thread URL (if Reddit discussion found)

    def synthesized_threads(self) -> list[ThreadInfo]:
        """Return per-platform threads, synthesizing from legacy fields if needed.
        New checkpoints set `threads` directly; old ones derive from the flat
        fields. Quotes from legacy data are placed under the dominant (higher-
        upvote) thread since legacy data has no per-quote provenance."""
        if self.threads:
            return self.threads

        derived: list[ThreadInfo] = []
        # Parse upvotes/comments from source_label
        import re as _re
        hn_match = _re.search(r"Hacker News\s+(\d[\d,]*)↑(?:\s*·\s*(\d[\d,]*)\s*comments?)?", self.source_label or "")
        reddit_match = _re.search(r"r/(\S+?)\s*\(\s*(\d[\d,.]*)([Kk])?↑\)", self.source_label or "")

        if self.hn_url and hn_match:
            hn_upvotes = int(hn_match.group(1).replace(",", ""))
            hn_comments = int(hn_match.group(2).replace(",", "")) if hn_match.group(2) else 0
            derived.append(ThreadInfo(
                platform="hackernews",
                url=self.hn_url,
                upvotes=hn_upvotes,
                comments=hn_comments,
                sentiment=self.sentiment,
                quotes=[],     # placeholder; quotes assigned to dominant below
                quotes_ko=[],
                key_point=self.key_point,
            ))

        if self.reddit_url and reddit_match:
            sub = reddit_match.group(1).rstrip(")")
            digits = reddit_match.group(2).replace(",", "")
            kmult = (reddit_match.group(3) or "").upper() == "K"
            r_upvotes = int(float(digits) * (1000 if kmult else 1))
            derived.append(ThreadInfo(
                platform="reddit",
                url=self.reddit_url,
                subreddit=sub,
                upvotes=r_upvotes,
                comments=0,  # legacy source_label rarely has Reddit comment count
                sentiment=self.sentiment,
                quotes=[],
                quotes_ko=[],
                key_point=self.key_point,
            ))

        # Place all legacy quotes under the dominant (highest-upvote) thread
        if derived and (self.quotes or self.quotes_ko):
            derived.sort(key=lambda t: t.upvotes, reverse=True)
            derived[0].quotes = list(self.quotes or [])
            derived[0].quotes_ko = list(self.quotes_ko or [])

        return derived


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
    source_kind: str = ""
    source_confidence: str = ""
    source_tier: str = ""


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
