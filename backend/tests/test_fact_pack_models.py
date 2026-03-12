from models.business import BusinessPost
from models.research import ResearchPost


def _make_source_card(card_id: str, claim_ids: list[str]) -> dict:
    return {
        "id": card_id,
        "title": "OpenAI launches new enterprise bundle",
        "publisher": "OpenAI",
        "url": f"https://openai.com/blog/{card_id}",
        "published_at": "2026-03-12T00:00:00Z",
        "evidence_snippet": "Official announcement describing the new enterprise plan.",
        "claim_ids": claim_ids,
    }


def test_business_post_accepts_fact_pack_analysis_and_source_cards():
    post = BusinessPost.model_validate(
        {
            "title": "OpenAI expands enterprise bundles",
            "slug": "2026-03-12-business-daily",
            "content_analysis": "## Core Analysis\n" + ("Shared analysis context. " * 120),
            "content_beginner": "## The Story\n" + ("Beginner insight. " * 220),
            "content_learner": "## What Happened\n" + ("Learner insight. " * 220),
            "content_expert": "## Executive Summary\n" + ("Expert insight. " * 220),
            "fact_pack": [
                {
                    "id": "claim-1",
                    "claim": "OpenAI launched a new enterprise bundle. [[1]]",
                    "why_it_matters": "Bundling affects procurement and vendor selection.",
                    "source_ids": ["src-1"],
                    "confidence": "high",
                }
            ],
            "source_cards": [_make_source_card("src-1", ["claim-1"])],
            "excerpt": "Enterprise bundles change how teams compare vendors.",
            "focus_items": [
                "OpenAI changed enterprise packaging.",
                "Procurement decisions may speed up.",
                "Watch contract and pricing disclosures next.",
            ],
            "source_urls": ["https://openai.com/blog/src-1"],
            "news_temperature": 4,
            "tags": ["enterprise", "pricing"],
        }
    )

    assert post.content_analysis.startswith("## Core Analysis")
    assert post.fact_pack[0].source_ids == ["src-1"]
    assert post.source_cards[0].claim_ids == ["claim-1"]


def test_research_post_accepts_source_cards_for_citation_rendering():
    post = ResearchPost.model_validate(
        {
            "has_news": True,
            "title": "OpenAI publishes a new evaluation report",
            "slug": "2026-03-12-research-daily",
            "content_original": "## 1. What Happened\n"
            + ("Research detail with source markers [[1]]. " * 160),
            "excerpt": "A new evaluation report changes how teams think about deployment risk.",
            "focus_items": [
                "OpenAI published a new evaluation report.",
                "Evaluation quality affects production trust.",
                "Watch whether benchmark disclosures expand.",
            ],
            "source_cards": [_make_source_card("src-1", ["claim-1"])],
            "source_urls": ["https://openai.com/blog/src-1"],
            "news_temperature": 3,
            "tags": ["evaluation", "research"],
        }
    )

    assert post.source_cards[0].publisher == "OpenAI"
