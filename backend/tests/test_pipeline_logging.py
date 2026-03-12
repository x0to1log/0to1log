from unittest.mock import MagicMock, patch


def _make_supabase_mock():
    mock = MagicMock()
    chain = mock.table.return_value
    chain.insert.return_value = chain
    chain.execute.return_value = MagicMock(data=[{"id": "log-1"}])
    return mock


def test_log_pipeline_stage_includes_debug_meta_and_dimensions():
    from services.pipeline import log_pipeline_stage

    mock_db = _make_supabase_mock()

    with patch("services.pipeline.get_supabase", return_value=mock_db):
        log_pipeline_stage(
            run_id="run-1",
            pipeline_type="research.generate.en",
            status="success",
            post_type="research",
            locale="en",
            attempt=2,
            output_summary="Research EN draft generated",
            tokens_used=1234,
            cost_usd=0.12,
            debug_meta={"research_en_len": 6123, "selected_urls": ["https://example.com"]},
        )

    inserted = mock_db.table.return_value.insert.call_args.args[0]
    assert inserted["run_id"] == "run-1"
    assert inserted["attempt"] == 2
    assert inserted["post_type"] == "research"
    assert inserted["locale"] == "en"
    assert inserted["debug_meta"]["research_en_len"] == 6123


def test_normalize_pipeline_error_returns_short_message():
    from services.pipeline import normalize_pipeline_error

    message = normalize_pipeline_error(
        "1 validation error for ResearchPost\ncontent_original\n"
        "  Value error, Content too short: 4838 chars (min 5000)"
    )

    assert message == "Research post too short: 4838 / 5000 chars."
