import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.run_handbook_seed_batch import (
    ExistingTermIndex,
    SeedTerm,
    build_handbook_insert_row,
    execute_seed_batch,
    _insert_pipeline_log,
    load_seed_terms,
    parse_args,
    select_seed_candidates,
    slugify,
)


def _write_jsonl(path, rows):
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_select_seed_candidates_skips_existing_terms_and_aliases(tmp_path):
    seed_file = tmp_path / "01-llm-genai.jsonl"
    _write_jsonl(
        seed_file,
        [
            {"_meta": True, "category": "llm-genai", "target": 180},
            {
                "term": "Structured Outputs",
                "aliases": ["structured output"],
                "type": "capability_feature_spec",
                "note": "[2024+] schema-constrained responses",
            },
            {
                "term": "Context Window",
                "aliases": ["context length"],
                "type": "capability_feature_spec",
                "note": "input range",
            },
            {
                "term": "Prompt Caching",
                "aliases": [],
                "type": "capability_feature_spec",
                "note": "[2024+] repeated prompt discount",
            },
            {
                "term": "ReAct",
                "aliases": [],
                "type": "system_workflow_pattern",
                "note": "reasoning + acting",
            },
        ],
    )

    terms = load_seed_terms(tmp_path)
    existing = ExistingTermIndex(
        terms={"structured output"},
        slugs={slugify("Context Window")},
    )

    candidates = select_seed_candidates(terms, existing, limit=2)

    assert [c.term for c in candidates] == ["Prompt Caching", "ReAct"]
    assert candidates[0].category == "llm-genai"
    assert candidates[0].source_file == "01-llm-genai.jsonl"


def test_select_seed_candidates_supports_offset_after_filtering(tmp_path):
    seed_file = tmp_path / "07-cs-fundamentals.jsonl"
    _write_jsonl(
        seed_file,
        [
            {"_meta": True, "category": "cs-fundamentals", "target": 50},
            {"term": "HTTP", "aliases": [], "type": "protocol_format_data_structure"},
            {"term": "Hash Table", "aliases": [], "type": "protocol_format_data_structure"},
            {"term": "Graph Traversal", "aliases": [], "type": "foundational_concept"},
        ],
    )

    terms = load_seed_terms(tmp_path)
    candidates = select_seed_candidates(
        terms,
        ExistingTermIndex(),
        limit=1,
        offset=1,
    )

    assert [c.term for c in candidates] == ["Hash Table"]


def test_seed_runner_script_runs_from_backend_cwd(tmp_path):
    backend_dir = Path(__file__).resolve().parents[1]
    seed_file = tmp_path / "01-llm-genai.jsonl"
    _write_jsonl(
        seed_file,
            [
                {"_meta": True, "category": "llm-genai", "target": 180},
                {"term": "Pytest Seed Runner Unique Term", "aliases": [], "type": "capability_feature_spec"},
            ],
        )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_handbook_seed_batch.py",
            "--seed-dir",
            str(tmp_path),
            "--limit",
            "1",
        ],
        check=False,
        capture_output=True,
        cwd=backend_dir,
        text=True,
    )

    assert result.returncode == 0
    assert "Pytest Seed Runner Unique Term" in result.stdout


def test_seed_runner_defaults_to_single_concurrency():
    with patch.object(sys, "argv", ["run_handbook_seed_batch.py"]):
        args = parse_args()

    assert args.max_concurrent == 1
    assert args.remediate is False


def test_seed_runner_exposes_opt_in_remediation_flag():
    with patch.object(sys, "argv", ["run_handbook_seed_batch.py", "--remediate"]):
        args = parse_args()

    assert args.remediate is True


def test_build_handbook_insert_row_maps_generated_fields_with_seed_fallbacks():
    seed = SeedTerm(
        term="Prompt Caching",
        aliases=(),
        term_type="capability_feature_spec",
        note="[2024+] repeated prompt discount",
        category="llm-genai",
        slug="prompt-caching",
        source_file="01-llm-genai.jsonl",
        line_number=25,
    )

    row = build_handbook_insert_row(
        seed,
        {
            "korean_name": "프롬프트 캐싱",
            "definition_ko": "반복 프롬프트 비용을 줄이는 기능",
            "definition_en": "A prompt reuse feature.",
            "body_basic_ko": "basic ko",
            "body_basic_en": "basic en",
            "body_advanced_ko": "advanced ko",
            "body_advanced_en": "advanced en",
            "references_ko": [{"url": "https://example.com"}],
            "references_en": [{"url": "https://example.com"}],
            "facet_intent": ["build"],
            "facet_volatility": "fast-changing",
        },
    )

    assert row["term"] == "Prompt Caching"
    assert row["slug"] == "prompt-caching"
    assert row["korean_name"] == "프롬프트 캐싱"
    assert row["categories"] == ["llm-genai"]
    assert row["term_type"] == "capability_feature_spec"
    assert row["facet_intent"] == ["build"]
    assert row["facet_volatility"] == "fast-changing"
    assert row["status"] == "draft"
    assert row["source"] == "seed"


def test_build_handbook_insert_row_keeps_seed_type_when_generated_type_disagrees():
    seed = SeedTerm(
        term="Test-Time Compute",
        aliases=("TTC",),
        term_type="capability_feature_spec",
        note="[2025+] inference-time scaling",
        category="llm-genai",
        slug="test-time-compute",
        source_file="01-llm-genai.jsonl",
        line_number=6,
    )

    row = build_handbook_insert_row(
        seed,
        {
            "term_type": "hardware_runtime_infra",
            "korean_name": "테스트 타임 컴퓨트",
            "definition_ko": "추론 시 연산을 더 쓰는 방식.",
            "definition_en": "An inference-time scaling technique.",
        },
    )

    assert row["term_type"] == "capability_feature_spec"


def test_build_handbook_insert_row_derives_missing_korean_name_from_korean_full():
    seed = SeedTerm(
        term="Computer Use",
        aliases=("computer-use",),
        term_type="capability_feature_spec",
        note="[2024+] screen-control agents",
        category="llm-genai",
        slug="computer-use",
        source_file="01-llm-genai.jsonl",
        line_number=4,
    )

    row = build_handbook_insert_row(
        seed,
        {
            "term_full": "Computer Use",
            "korean_full": "컴퓨터 UI 제어(Computer Use)",
            "definition_ko": "컴퓨터 화면을 조작하는 기능.",
            "definition_en": "A screen-control capability.",
        },
    )

    assert row["korean_name"] == "컴퓨터 UI 제어"


class _FakeResult:
    def __init__(self, data=None):
        self.data = data or []


class _FakeTable:
    def __init__(self, supabase, name):
        self.supabase = supabase
        self.name = name
        self._insert_payload = None
        self._update_payload = None

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def update(self, payload):
        self._update_payload = payload
        return self

    def eq(self, *args, **kwargs):
        return self

    def execute(self):
        if self._insert_payload is not None:
            self.supabase.inserts.setdefault(self.name, []).append(self._insert_payload)
            if self.name == "handbook_terms":
                return _FakeResult([{"id": "term-id-1"}])
            return _FakeResult([self._insert_payload])
        if self._update_payload is not None:
            self.supabase.updates.setdefault(self.name, []).append(self._update_payload)
            return _FakeResult([self._update_payload])
        return _FakeResult([])


class _FakeSupabase:
    def __init__(self):
        self.inserts = {}
        self.updates = {}

    def table(self, name):
        return _FakeTable(self, name)


class _FailingInsertTable:
    def insert(self, payload):
        return self

    def execute(self):
        raise RuntimeError("network unavailable")


class _FailingLogSupabase:
    def table(self, name):
        assert name == "pipeline_logs"
        return _FailingInsertTable()


def test_insert_pipeline_log_is_non_fatal_when_supabase_insert_fails():
    seed = SeedTerm(
        term="Prompt Caching",
        aliases=(),
        term_type="capability_feature_spec",
        note="",
        category="llm-genai",
        slug="prompt-caching",
        source_file="01-llm-genai.jsonl",
        line_number=25,
    )

    _insert_pipeline_log(
        _FailingLogSupabase(),
        run_id="run-1",
        seed=seed,
        status="failed",
        error_message="generation failed",
    )


@pytest.mark.asyncio
async def test_execute_seed_batch_generates_and_inserts_drafts():
    seed = SeedTerm(
        term="Prompt Caching",
        aliases=(),
        term_type="capability_feature_spec",
        note="[2024+] repeated prompt discount",
        category="llm-genai",
        slug="prompt-caching",
        source_file="01-llm-genai.jsonl",
        line_number=25,
    )
    supabase = _FakeSupabase()
    calls = []

    async def fake_generator(
        *,
        term_name,
        korean_name="",
        source="pipeline",
        article_context="",
        categories=None,
        term_type_hint="",
        log_run_id=None,
        skip_quality_check=False,
        skip_self_critique=False,
        skip_post_generation_checks=False,
        remediate_after_generation=False,
    ):
        calls.append(
            {
                "term_name": term_name,
                "source": source,
                "categories": categories,
                "term_type_hint": term_type_hint,
                "log_run_id": log_run_id,
                "skip_quality_check": skip_quality_check,
                "skip_self_critique": skip_self_critique,
                "skip_post_generation_checks": skip_post_generation_checks,
                "remediate_after_generation": remediate_after_generation,
            }
        )
        return (
            {
                "korean_name": "프롬프트 캐싱",
                "definition_ko": "반복 프롬프트 비용을 줄이는 기능",
                "definition_en": "A prompt reuse feature.",
                "categories": categories,
                "_warnings": ["minor warning"],
                "_remediation_issues": [{"code": "definition_too_long", "severity": "medium"}],
                "_quality_gate": {"status": "needs_remediation"},
                "_remediation_status": "not_requested",
            },
            {
                "model_used": "gpt-5",
                "tokens_used": 100,
                "cost_usd": 0.01,
                "input_tokens": 70,
                "output_tokens": 30,
                "cached_tokens": 20,
                "service_tier": "flex",
            },
        )

    result = await execute_seed_batch(
        [seed],
        supabase,
        generator=fake_generator,
        run_key="handbook-seed-test",
        max_concurrent=1,
        draft_only=True,
    )

    assert result.created == 1
    assert result.failed == 0
    assert calls[0]["term_name"] == "Prompt Caching"
    assert calls[0]["source"] == "seed"
    assert calls[0]["categories"] == ["llm-genai"]
    assert calls[0]["term_type_hint"] == "capability_feature_spec"
    assert calls[0]["log_run_id"] == result.run_id
    assert calls[0]["skip_quality_check"] is True
    assert calls[0]["skip_self_critique"] is True
    assert calls[0]["skip_post_generation_checks"] is True
    assert calls[0]["remediate_after_generation"] is False

    inserted_term = supabase.inserts["handbook_terms"][0]
    assert inserted_term["term"] == "Prompt Caching"
    assert inserted_term["status"] == "draft"
    assert inserted_term["source"] == "seed"

    success_log = supabase.inserts["pipeline_logs"][-1]
    assert success_log["run_id"] == result.run_id
    assert success_log["pipeline_type"] == "handbook.seed_generate"
    assert success_log["status"] == "success"
    assert success_log["tokens_used"] is None
    assert success_log["cost_usd"] is None
    assert success_log["debug_meta"]["billing_scope"] == "rollup"
    assert success_log["debug_meta"]["rollup_usage"]["cost_usd"] == 0.01
    assert success_log["debug_meta"]["warnings"] == ["minor warning"]
    assert success_log["debug_meta"]["remediation_issues"] == [{"code": "definition_too_long", "severity": "medium"}]
    assert success_log["debug_meta"]["quality_gate"] == {"status": "needs_remediation"}
    assert success_log["debug_meta"]["remediation_status"] == "not_requested"
    assert supabase.updates["pipeline_runs"][-1]["status"] == "success"


@pytest.mark.asyncio
async def test_execute_seed_batch_passes_remediation_flag_to_generator():
    seed = SeedTerm(
        term="Context Window",
        aliases=(),
        term_type="capability_feature_spec",
        note="token budget",
        category="llm-genai",
        slug="context-window",
        source_file="01-llm-genai.jsonl",
        line_number=26,
    )
    supabase = _FakeSupabase()
    calls = []

    async def fake_generator(**kwargs):
        calls.append(kwargs)
        return (
            {
                "korean_name": "컨텍스트 윈도우",
                "definition_ko": "모델이 한 번에 읽을 수 있는 입력 범위.",
                "definition_en": "The input range a model can read in one turn.",
            },
            {"cost_usd": 0.02},
        )

    result = await execute_seed_batch(
        [seed],
        supabase,
        generator=fake_generator,
        run_key="handbook-seed-remediate-test",
        remediate=True,
    )

    assert result.created == 1
    assert calls[0]["remediate_after_generation"] is True
    assert supabase.inserts["pipeline_logs"][-1]["debug_meta"]["remediation_enabled"] is True


@pytest.mark.asyncio
async def test_execute_seed_batch_times_out_one_term_and_finishes_run():
    seed = SeedTerm(
        term="Slow Term",
        aliases=(),
        term_type="capability_feature_spec",
        note="",
        category="llm-genai",
        slug="slow-term",
        source_file="01-llm-genai.jsonl",
        line_number=30,
    )
    supabase = _FakeSupabase()

    async def slow_generator(**kwargs):
        import asyncio

        await asyncio.sleep(1)
        return ({}, {})

    result = await execute_seed_batch(
        [seed],
        supabase,
        generator=slow_generator,
        run_key="handbook-seed-timeout-test",
        max_concurrent=1,
        term_timeout_seconds=0.01,
    )

    assert result.created == 0
    assert result.failed == 1
    assert "timed out after 0.01s" in result.errors[0]
    failure_log = supabase.inserts["pipeline_logs"][-1]
    assert failure_log["status"] == "failed"
    assert "timed out after 0.01s" in failure_log["error_message"]
    assert supabase.updates["pipeline_runs"][-1]["status"] == "failed"
