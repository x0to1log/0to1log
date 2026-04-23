"""One-shot probe: does service_tier='flex' work with our GPT-5 models?

Usage (from backend/): python -m scripts.probe_flex_tier
Reads OPENAI_API_KEY from backend/.env. Does NOT touch DB.
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI


# Load backend/.env regardless of cwd
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODELS = ["gpt-5", "gpt-5-mini", "gpt-5-nano"]


async def probe(model: str) -> tuple[str, str, int | None]:
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=60.0)
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
            max_completion_tokens=20,
            service_tier="flex",
            reasoning_effort="low",
        )
        return (model, "ok", resp.usage.total_tokens)
    except Exception as e:
        return (model, f"ERROR: {type(e).__name__}: {str(e)[:200]}", None)


async def main():
    results = await asyncio.gather(*(probe(m) for m in MODELS))
    print(f"\n{'Model':<15} {'Result':<70} {'Tokens'}")
    print("-" * 100)
    for model, status, tokens in results:
        print(f"{model:<15} {status[:70]:<70} {tokens or '-'}")
    failures = [r for r in results if not r[1].startswith("ok")]
    print()
    print(f"Result: {len(results) - len(failures)} of {len(results)} models accept service_tier='flex'")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    asyncio.run(main())
