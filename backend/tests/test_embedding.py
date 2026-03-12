from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_build_embed_text():
    from services.embedding import _build_embed_text
    text = _build_embed_text(
        title="GPT-5 Released",
        excerpt="OpenAI releases GPT-5",
        category="ai-news",
        tags=["openai", "llm"],
    )
    assert "GPT-5 Released" in text
    assert "OpenAI releases GPT-5" in text
    assert "ai-news" in text
    assert "openai" in text


@pytest.mark.asyncio
async def test_embed_post_calls_openai_and_pinecone():
    from services.embedding import embed_post
    from services.embedding import settings

    mock_embedding = [0.1] * settings.embedding_dimensions
    mock_openai = AsyncMock()
    mock_openai.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=mock_embedding)]
    )
    mock_index = MagicMock()
    mock_index.upsert = MagicMock()

    with patch("services.embedding.settings.pinecone_api_key", "test-key"), \
         patch("services.embedding._get_openai_client", return_value=mock_openai), \
         patch("services.embedding._get_pinecone_index", return_value=mock_index):
        await embed_post(
            post_id="abc-123",
            title="GPT-5 Released",
            excerpt="OpenAI releases GPT-5",
            category="ai-news",
            tags=["openai"],
            locale="en",
            slug="gpt-5-released",
            published_at="2026-03-10",
        )

    mock_openai.embeddings.create.assert_called_once_with(
        model=settings.embedding_model,
        input="GPT-5 Released\nOpenAI releases GPT-5\nai-news\nopenai",
        dimensions=settings.embedding_dimensions,
    )
    mock_index.upsert.assert_called_once()
    call_kwargs = mock_index.upsert.call_args
    vectors = call_kwargs[1].get("vectors") or call_kwargs[0][0]
    assert vectors[0]["id"] == "abc-123"
    assert vectors[0]["values"] == mock_embedding
    assert vectors[0]["metadata"]["locale"] == "en"


def test_get_pinecone_index_rejects_dimension_mismatch():
    from services.embedding import _get_pinecone_index

    mock_index = MagicMock()
    mock_pc = MagicMock()
    mock_pc.Index.return_value = mock_index
    mock_pc.describe_index.return_value = {"dimension": 1024, "name": "news-posts"}

    with patch("services.embedding._pinecone_index", None), \
         patch("services.embedding.Pinecone", return_value=mock_pc), \
         patch("services.embedding.settings.pinecone_api_key", "test-key"), \
         patch("services.embedding.settings.pinecone_index_name", "news-posts"), \
         patch("services.embedding.settings.embedding_dimensions", 1536):
        with pytest.raises(RuntimeError, match="news-posts"):
            _get_pinecone_index()
