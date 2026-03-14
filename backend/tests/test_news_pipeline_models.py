"""Tests for AI News Pipeline v2 Pydantic models."""
import pytest
from pydantic import ValidationError


def test_fact_pack_valid():
    from models.news_pipeline import FactPack
    data = {
        "headline": "OpenAI releases GPT-5",
        "key_facts": [{"id": "f1", "claim": "GPT-5 achieves 95% on MMLU", "why_it_matters": "Significant improvement", "source_ids": ["s1"], "confidence": "high"}],
        "numbers": [{"value": "95%", "context": "MMLU benchmark score", "source_id": "s1"}],
        "entities": [{"name": "OpenAI", "role": "developer", "url": "https://openai.com"}],
        "sources": [{"id": "s1", "title": "OpenAI Blog", "publisher": "openai.com", "url": "https://openai.com/blog/gpt-5", "published_at": "2026-03-15"}],
        "community_summary": "Reddit users are excited but skeptical.",
    }
    fp = FactPack.model_validate(data)
    assert fp.headline == "OpenAI releases GPT-5"
    assert len(fp.key_facts) == 1
    assert fp.key_facts[0].id == "f1"
    assert len(fp.sources) == 1


def test_fact_pack_missing_headline_fails():
    from models.news_pipeline import FactPack
    with pytest.raises(ValidationError):
        FactPack.model_validate({"key_facts": [], "numbers": [], "entities": [], "sources": [], "community_summary": ""})


def test_fact_pack_empty_lists_ok():
    from models.news_pipeline import FactPack
    fp = FactPack.model_validate({"headline": "Minor update", "key_facts": [], "numbers": [], "entities": [], "sources": [], "community_summary": ""})
    assert fp.headline == "Minor update"
    assert fp.key_facts == []


def test_persona_output_valid():
    from models.news_pipeline import PersonaOutput
    po = PersonaOutput.model_validate({"en": "## Summary\nEnglish content", "ko": "## 핵심 요약\n한국어"})
    assert len(po.en) > 10
    assert len(po.ko) > 5


def test_persona_output_empty_string_allowed():
    from models.news_pipeline import PersonaOutput
    po = PersonaOutput.model_validate({"en": "", "ko": ""})
    assert po.en == ""


def test_ranked_candidate_valid():
    from models.news_pipeline import RankedCandidate
    rc = RankedCandidate.model_validate({"title": "GPT-5 Released", "url": "https://example.com/gpt5", "snippet": "OpenAI announces GPT-5.", "source": "tavily", "assigned_type": "research", "relevance_score": 0.95, "ranking_reason": "Major model release"})
    assert rc.assigned_type == "research"
    assert rc.relevance_score == 0.95


def test_news_candidate_minimal():
    from models.news_pipeline import NewsCandidate
    nc = NewsCandidate.model_validate({"title": "Some news", "url": "https://example.com", "snippet": "A snippet", "source": "tavily"})
    assert nc.title == "Some news"


def test_pipeline_result_structure():
    from models.news_pipeline import PipelineResult
    pr = PipelineResult(batch_id="2026-03-15", posts_created=4, errors=[], usage={"model_used": "gpt-4o", "tokens_used": 5000, "cost_usd": 0.05})
    assert pr.batch_id == "2026-03-15"
    assert pr.posts_created == 4


def test_pipeline_result_with_errors():
    from models.news_pipeline import PipelineResult
    pr = PipelineResult(batch_id="2026-03-15", posts_created=2, errors=["research fact extraction failed"], usage={})
    assert len(pr.errors) == 1
