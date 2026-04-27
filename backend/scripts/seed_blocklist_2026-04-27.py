"""Seed news_domain_filters research_blocklist with 18 confirmed mirror/aggregator domains.

Audit basis (2026-04-27):
- 14-day source_card audit revealed 21 candidates flagged confidence='low'.
- Per-domain content inspection (URL patterns, titles, body-citation status) confirmed
  18 are genuinely low-quality (mirrors, paper-content aggregators, predatory journals).
- 3 candidates were excluded as legitimate niche content despite 'low' classification:
  tianpan.co (personal tech blog), zhihang-fu.github.io (academic publication page),
  agent-sh.github.io (agnix framework documentation). The misclassification of these
  is the motivating signal for sprint task NQ-43 (classifier improvement).

Mechanism:
- Adding to research_blocklist makes _classify_source_meta return source_tier='spam'.
- _enrich_source_passes_quality drops tier='spam' before the source ever enters the
  writer's URL allowlist.
- Note: _load_domain_filters uses lru_cache; Railway must be restarted for the
  blocklist to take effect on the live container.

Run once. Idempotent (skips domains already present).
"""
import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv("C:/Users/amy/Desktop/0to1log/backend/.env")

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

# 18 domains, grouped by audit basis
ENTRIES = [
    # Apr 26 incident (6) — confirmed mirrors
    ("zamin.uz", "Mirror site (Apr 26 audit; reposts mainstream AI news)"),
    ("dailyofusa.com", "Mirror site (Apr 26 audit)"),
    ("news247network.com", "Mirror site (Apr 26 audit)"),
    ("briefglance.com", "Aggregator (Apr 26 audit)"),
    ("harianbasis.co", "Mirror site (Apr 26 audit)"),
    ("central-asia.news", "Mirror site (Apr 26 audit)"),

    # Paper / literature aggregators (4)
    ("liner.com", "Paper-review aggregator; reposts arxiv content as /review/{slug}"),
    ("aisecurity-portal.org", "Literature-database aggregator (no original content)"),
    ("ai-navigate-news.com", "AI news aggregator with UUID URLs"),
    ("eurekaselect.com", "Bentham Science (widely flagged as predatory publisher)"),

    # Mainstream-news rewriters (4)
    ("mlq.ai", "Rewrites mainstream funding/business news under own domain"),
    ("prfintech.com", "Press-release wire aggregator (funding rounds)"),
    ("ppc.land", "Rewrites mainstream tech news under own domain"),
    ("israel.timesofnews.com", "Aggregator subdomain (mainstream news rehosted)"),

    # Low-quality blogs / aggregators (4)
    ("letsdatascience.com", "Low-quality data science blog with rehosted content"),
    ("neomanex.com", "Generic blog aggregator (small-LLM enterprise listicles)"),
    ("stnkw.com", "AI-tutorials aggregator with wholesale rehosted articles"),
    ("dasroot.net", "Single-author 'Technical news' aggregator"),
]

print(f"Seeding {len(ENTRIES)} domains into news_domain_filters/research_blocklist")
print()

# Fetch existing to skip duplicates
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
print("NEXT: restart Railway to clear lru_cache so the new blocklist takes effect.")
