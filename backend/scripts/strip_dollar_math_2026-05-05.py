"""One-shot DB cleanup: strip $$X$$ LaTeX-display-math wrapping from past news posts.

Audit basis (2026-05-05):
GPT-5 writer wraps dollar amounts and numeric values in $$X$$ as a model
artifact. Frontend remark-math + rehype-katex then renders these as math,
breaking typography (numbers in math italic mid-sentence). Bulk scan
across news_posts (Apr 1+) found 177 occurrences across 20 published
posts in content_expert and content_learner only.

This script applies the same regex used by _clean_writer_output (post-process
fix in pipeline_digest.py) to all affected rows. Dry-run by default —
pass --apply to actually update.

Pattern: r"\\$\\$([\\d,.\\s]+?)\\$\\$" -> r"\\1"
- Matches purely-numeric content between $$ markers
- Leaves any genuine LaTeX math with letters/operators untouched
- Idempotent (re-running on already-clean content is a no-op)

Affected fields: content_expert, content_learner. excerpt/focus_items/
guide_items confirmed clean by audit.

Run:
  python strip_dollar_math_2026-05-05.py            # dry run (counts only)
  python strip_dollar_math_2026-05-05.py --apply    # write to DB
"""
import os
import re
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client

load_dotenv("C:/Users/amy/Desktop/0to1log/backend/.env")
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

DOLLAR_MATH_RE = re.compile(
    r"\$\$([\d][\d,.\s\-–%a-zA-Z억만조달러원円€£¥]*?)\$\$"
)


def strip_dollar_math(text: str) -> tuple[str, int]:
    """Return (fixed_text, count_replaced)."""
    if not text:
        return text, 0
    n = 0
    def _sub(m):
        nonlocal n
        n += 1
        return m.group(1)
    fixed = DOLLAR_MATH_RE.sub(_sub, text)
    return fixed, n


def main():
    apply = "--apply" in sys.argv
    print(f"Mode: {'APPLY (writes to DB)' if apply else 'DRY RUN (no writes)'}")
    print()

    posts = (
        sb.table("news_posts")
        .select("id, slug, content_expert, content_learner, pipeline_batch_id, status")
        .gte("pipeline_batch_id", "2026-04-01")
        .execute()
    ).data

    affected = 0
    total_replaced = 0
    for p in posts:
        e_text = p.get("content_expert") or ""
        l_text = p.get("content_learner") or ""
        e_fixed, e_n = strip_dollar_math(e_text)
        l_fixed, l_n = strip_dollar_math(l_text)
        if e_n == 0 and l_n == 0:
            continue
        affected += 1
        total_replaced += e_n + l_n
        print(f"  [{p['status']:10s}] {p['slug']:45s} expert={e_n:3d} learner={l_n:3d}")
        if apply:
            update = {"updated_at": datetime.now(timezone.utc).isoformat()}
            if e_n > 0:
                update["content_expert"] = e_fixed
            if l_n > 0:
                update["content_learner"] = l_fixed
            sb.table("news_posts").update(update).eq("id", p["id"]).execute()

    print()
    print(f"Posts affected: {affected}")
    print(f"Total replacements: {total_replaced}")
    if apply:
        print()
        print("✅ Applied to DB. Frontend will re-fetch on next request (Astro ISR).")
    else:
        print()
        print("Dry-run complete. Re-run with --apply to write to DB.")


if __name__ == "__main__":
    main()
