"""Probe GPT-6 candidates for the Chat Completions params production sends.

Usage (from backend/): python -m scripts.probe_model_capabilities
Reads OPENAI_API_KEY from backend/.env. Does NOT touch DB.

Each probe mirrors a real call shape from services/ (see
2026-10-13-news-pipeline-gpt6-upgrade.md Task 1.2). Prompts are tiny, so a
full run costs cents. Supersedes probe_flex_tier.py for the GPT-6 migration.
"""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

CANDIDATES = ["gpt-6-luna", "gpt-6.1-sol"]
BASELINE = ["gpt-5-mini"]
ALIAS_CHECK = ["gpt-5", "gpt-5-mini", "gpt-5-nano"]

OK_PROMPT = [{"role": "user", "content": "Reply with the single word: ok"}]
JSON_PROMPT = [{"role": "user", "content": 'Return JSON: {"answer": "ok"}'}]

# Same shape as services/agents/client.py strict json_schema builder
STRICT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "probe",
        "schema": {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}

PROBES: dict[str, dict] = {
    "baseline effort=low": {"messages": OK_PROMPT, "reasoning_effort": "low"},
    "service_tier=flex": {"messages": OK_PROMPT, "reasoning_effort": "low", "service_tier": "flex"},
    "json_object": {
        "messages": JSON_PROMPT, "reasoning_effort": "low",
        "response_format": {"type": "json_object"},
    },
    "json_schema strict": {"messages": JSON_PROMPT, "reasoning_effort": "low", "response_format": STRICT_SCHEMA},
    "prompt_cache_key": {"messages": OK_PROMPT, "reasoning_effort": "low", "prompt_cache_key": "probe-gpt6"},
    "verbosity=low": {"messages": OK_PROMPT, "reasoning_effort": "low", "verbosity": "low"},
    "effort=high": {"messages": OK_PROMPT, "reasoning_effort": "high"},
    "max_completion=96000": {"messages": OK_PROMPT, "reasoning_effort": "low", "max_completion_tokens": 96000},
    "temperature=0.2": {"messages": OK_PROMPT, "reasoning_effort": "low", "temperature": 0.2},
    # The dominant production shape: flex + json_object + cache key
    "PROD combo": {
        "messages": JSON_PROMPT, "reasoning_effort": "low", "service_tier": "flex",
        "response_format": {"type": "json_object"}, "prompt_cache_key": "probe-gpt6",
    },
}


async def run_probe(client: AsyncOpenAI, model: str, name: str, params: dict) -> dict:
    kwargs = {"model": model, "max_completion_tokens": 400, **params}
    try:
        resp = await client.chat.completions.create(**kwargs)
        usage = resp.usage
        details = getattr(usage, "completion_tokens_details", None)
        content = (resp.choices[0].message.content or "").strip()
        return {
            "model": model, "probe": name, "status": "ok",
            "resolved": resp.model, "tier": getattr(resp, "service_tier", None),
            "reasoning": getattr(details, "reasoning_tokens", None),
            "total": usage.total_tokens,
            "note": "EMPTY CONTENT" if not content else content[:30],
        }
    except Exception as e:
        return {
            "model": model, "probe": name, "status": "ERR",
            "resolved": "-", "tier": "-", "reasoning": "-", "total": "-",
            "note": f"{type(e).__name__}: {str(e)[:110]}",
        }


async def main() -> None:
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=180.0)
    tasks = [
        run_probe(client, m, name, params)
        for m in CANDIDATES + BASELINE
        for name, params in PROBES.items()
    ]
    tasks += [run_probe(client, m, "alias resolve", PROBES["baseline effort=low"]) for m in ALIAS_CHECK]
    results = await asyncio.gather(*tasks)

    header = f"{'Model':<12} {'Probe':<22} {'St':<4} {'Resolved':<24} {'Tier':<8} {'Rsn':>5} {'Tot':>6}  Note"
    print("\n" + header)
    print("-" * 130)
    for r in results:
        print(
            f"{r['model']:<12} {r['probe']:<22} {r['status']:<4} {str(r['resolved']):<24} "
            f"{str(r['tier']):<8} {str(r['reasoning']):>5} {str(r['total']):>6}  {r['note']}"
        )
    errors = [r for r in results if r["status"] != "ok"]
    print(f"\n{len(results) - len(errors)} of {len(results)} probes succeeded")


if __name__ == "__main__":
    asyncio.run(main())
