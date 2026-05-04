"""Seed news_domain_filters research_blocklist with 6 mirror/aggregator domains.

Audit basis (2026-05-04): May 4 business-digest review surfaced 6 new
mirror/aggregator domains in source_cards. Per-domain spot-check via
HTTP GET confirmed all 6 are low-quality content-farm or aggregator sites:

- toolsstackai.com    — author 'Tools Stack AI' (generic SEO content factory)
- aidailypost.com     — slow/timeout host, aggregator framing
- aibusinessweekly.net — 856KB HTML (heavy ad/template), uncredentialed author
- epinium.com          — author field is a Facebook URL (unprofessional)
- taxheal.com          — 404 on the cited URL; tax site running AI SEO content
- aipressa.com         — no author, no date, generic 'AI Pressa' branding

Pattern matches what we curated 2026-04-27 (commit 19cc5e2). The recurrence
confirms NQ-43 (classifier improvement) is a real ongoing need — until that
ships, periodic audit + blocklist expansion is the only mitigation.

Mechanism (same as Apr 27 seed):
- Adding to research_blocklist makes _classify_source_meta return
  source_tier='spam'. _enrich_source_passes_quality drops tier='spam'
  before the writer's URL allowlist sees it.
- Railway auto-restart on git push clears the lru_cache so the new
  blocklist takes effect on the next cron.

Run once. Idempotent (skips domains already present).
"""
import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv("C:/Users/amy/Desktop/0to1log/backend/.env")

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

ENTRIES = [
    ("toolsstackai.com", "SEO content-factory site (May 4 audit; recycles funding announcements as analysis)"),
    ("aidailypost.com", "Aggregator framing AI-news domain (May 4 audit)"),
    ("aibusinessweekly.net", "Heavy-ad content farm with uncredentialed bylines (May 4 audit)"),
    ("epinium.com", "Aggregator with Facebook-URL author field (May 4 audit)"),
    ("taxheal.com", "Tax site running AI SEO content; cited URL 404 (May 4 audit)"),
    ("aipressa.com", "Generic 'AI Pressa' branding without author/date metadata (May 4 audit)"),
]

print(f"Seeding {len(ENTRIES)} domains into news_domain_filters/research_blocklist")
print()

existing = (
    sb.table("news_domain_filters")
    .select("domain, filter_type")
    .eq("filter_type", "research_blocklist")
    .execute()
).data
existing_domains = {r["domain"] for r in existing}
print(f"Existing research_blocklist entries: {len(existing_domains)}")

inserted = 0
skipped = 0
for domain, notes in ENTRIES:
    if domain in existing_domains:
        print(f"  [skip ] {domain} (already present)")
        skipped += 1
        continue
    try:
        sb.table("news_domain_filters").insert({
            "domain": domain,
            "filter_type": "research_blocklist",
            "notes": notes,
        }).execute()
        print(f"  [added] {domain}")
        inserted += 1
    except Exception as e:
        print(f"  [FAIL ] {domain}: {e}", file=sys.stderr)

print()
print(f"Inserted: {inserted}  Skipped (already present): {skipped}")
print()
print("NEXT: Railway auto-redeploys on git push, clearing lru_cache. Next cron uses new blocklist.")
