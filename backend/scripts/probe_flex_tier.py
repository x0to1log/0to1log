"""Probes for GPT-5 API parameter support.

Usage (from backend/): python -m scripts.probe_flex_tier
Reads OPENAI_API_KEY from backend/.env. Does NOT touch DB.

Probes:
  - service_tier="flex" (cheaper async tier)
  - verbosity="low" (trim chattiness on JSON outputs)
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODELS = ["gpt-5", "gpt-5-mini", "gpt-5-nano"]


async def probe_flex(client: AsyncOpenAI, model: str) -> tuple[str, str, str, int | None]:
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
            max_completion_tokens=20,
            service_tier="flex",
            reasoning_effort="low",
        )
        return (model, "service_tier=flex", "ok", resp.usage.total_tokens)
    except Exception as e:
        return (model, "service_tier=flex", f"ERROR: {type(e).__name__}: {str(e)[:150]}", None)


async def probe_verbosity(client: AsyncOpenAI, model: str) -> tuple[str, str, str, int | None]:
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
            max_completion_tokens=20,
            verbosity="low",
            reasoning_effort="low",
        )
        return (model, "verbosity=low", "ok", resp.usage.total_tokens)
    except Exception as e:
        return (model, "verbosity=low", f"ERROR: {type(e).__name__}: {str(e)[:150]}", None)


async def main():
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=60.0)
    tasks = []
    for m in MODELS:
        tasks.append(probe_flex(client, m))
        tasks.append(probe_verbosity(client, m))
    results = await asyncio.gather(*tasks)

    print(f"\n{'Model':<13} {'Probe':<22} {'Result':<60} {'Tokens'}")
    print("-" * 105)
    for model, probe, status, tokens in results:
        print(f"{model:<13} {probe:<22} {status[:60]:<60} {tokens or '-'}")
    failures = [r for r in results if not r[2].startswith("ok")]
    print()
    print(f"Result: {len(results) - len(failures)} of {len(results)} probes succeeded")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    asyncio.run(main())
