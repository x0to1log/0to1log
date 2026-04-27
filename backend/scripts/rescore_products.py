"""Re-score existing ai_products rows against the current PRODUCT_QUALITY_RUBRIC.

No regeneration — just reads the row, calls _score_profile(), prints the
per-dimension breakdown. Use after rubric edits to validate the scoring change
without burning ~21k tokens per product on full regeneration.

Run from backend dir:
    .venv/Scripts/python scripts/rescore_products.py
"""
from __future__ import annotations

import asyncio
import logging
import sys

sys.path.insert(0, ".")

from core.database import get_supabase  # noqa: E402
from core.config import settings  # noqa: E402
from services.agents.client import get_openai_client  # noqa: E402
from services.agents.product_advisor import _score_profile, _aggregate_quality_score  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("rescore_products")

SLUGS = [
    # Earliest batch
    "hugging-face", "runway-ml", "semantic-scholar",
    # Yesterday batch
    "claude", "cursor", "n8n", "elevenlabs", "adobe-firefly", "lovable",
    # Sanity batch
    "openai-api", "gemini-cli", "llama", "flowise", "luma-ai", "ideogram", "recraft-v3",
    # Batch 3
    "suno", "udio", "supertone-play", "chatgpt", "notebooklm",
    "openclaw", "antigravity", "theres-an-ai-for-that", "geeknews", "latent.space",
    # Batch 4
    "perplexity", "gemini", "grok", "midjourney", "sora",
    "google-veo-3.1", "github-copilot", "v0", "replicate-run-ai-with-an-api",
    # Batch 5
    "stable-diffusion", "dall-e-3", "windsurf", "bolt.new", "klingai",
    "pika", "zapier", "arxiv", "anthropic-api",
    # Batch 6
    "make", "typeform", "mixpanel", "posthog", "intercom",
    "replit-ai", "pytorch", "tabnine", "alphaxiv", "app",
    # Batch 7
    "canva", "figma", "gamma", "leonardo.ai", "heygen-ai-video-generator",
    "dify", "langflow", "tensorflow", "pinecone", "weights-biases",
    # Batch 8
    "sora-2", "kling-2.6", "hailuo-ai", "bubble", "magnific-ai",
    "whisk", "helicone", "langsmith", "genspark", "microsoft-designer",
]


def row_to_profile(row: dict) -> dict:
    """Map ai_products row → profile dict shape the scorer expects.

    Must include every KO field: validate_ko_completeness compares
    description vs description_ko, editor_note vs editor_note_ko,
    pricing_detail vs pricing_detail_ko. Missing them produces a
    false-positive 0 score on ko_completeness.
    """
    return {
        "tagline": row.get("tagline") or "",
        "tagline_ko": row.get("tagline_ko") or "",
        "description": row.get("description") or "",
        "description_en": row.get("description") or "",
        "description_ko": row.get("description_ko") or "",
        "features": row.get("features") or [],
        "features_ko": row.get("features_ko") or [],
        "use_cases": row.get("use_cases") or [],
        "editor_note": row.get("editor_note") or "",
        "editor_note_ko": row.get("editor_note_ko") or "",
        "pricing": row.get("pricing"),
        "pricing_detail": row.get("pricing_detail") or "",
        "pricing_detail_ko": row.get("pricing_detail_ko") or "",
    }


async def main() -> None:
    sb = get_supabase()
    if not sb:
        print("No supabase client")
        return

    res = sb.table("ai_products").select(
        "slug,tagline,tagline_ko,description,description_ko,"
        "features,features_ko,use_cases,"
        "editor_note,editor_note_ko,"
        "pricing,pricing_detail,pricing_detail_ko"
    ).in_("slug", SLUGS).execute()

    rows = {r["slug"]: r for r in (res.data or [])}
    client = get_openai_client()

    for slug in SLUGS:
        row = rows.get(slug)
        if not row:
            print(f"== {slug}: not found in DB ==\n")
            continue
        profile = row_to_profile(row)
        # facts={} — we don't store technical_specs separately; judge will see
        # an empty specs list, which only affects facts_coverage scoring (already
        # measured in the prior run, not what we're testing here).
        score, tokens = await _score_profile(
            profile, {}, client, settings.openai_model_nano,
        )
        if not score:
            print(f"== {slug}: scoring failed ==\n")
            continue
        overall = _aggregate_quality_score(score)
        print(f"== {slug}: overall={overall}/100 (tokens={tokens}) ==")
        for dim in ("specificity", "grounding", "voice", "bilingual"):
            d = score.get(dim) or {}
            avg = d.get("score")
            subs = {
                k: v.get("score")
                for k, v in d.items()
                if isinstance(v, dict) and "score" in v
            }
            print(f"  {dim}: avg={avg} {subs}")
            # Print evidence quotes for voice dim — that's what we just rewrote
            if dim == "voice":
                for k, v in d.items():
                    if isinstance(v, dict):
                        ev = (v.get("evidence") or "")[:140]
                        print(f"    {k}: {ev!r}")
        print(f"  top_issue: {score.get('top_issue')}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
