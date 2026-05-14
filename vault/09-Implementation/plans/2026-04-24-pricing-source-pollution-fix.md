# Pricing Source Pollution Fix — Port Handbook Grounding Patterns

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prevent off-topic search results (e.g., Northeastern University's "Claude for Education" page) from polluting product profiles by porting 4 grounding/authority patterns from the handbook and news pipelines into product advisor's pricing search.

**Architecture:**
- **Domain-anchored Brave query** first (site:{root_domain}), fallback to open query only when restricted returns empty.
- **Blocklist filter** on every result (`.edu`, `/students/`, `reddit.com`, etc.) — bans known noise sources.
- **Relevance validation** — every result must mention the product name AND a pricing keyword in title+description. Drops educational/off-topic pages that mention the product incidentally.
- **PRIMARY/SECONDARY tiering** — label pricing sources by tier in the fact-extraction prompt. Same-domain / official pages are PRIMARY; third-party/unfiltered results are SECONDARY. Prompt rule: "Extract pricing_tiers from PRIMARY only. SECONDARY is supplementary context."

**Tech Stack:** Python 3.11, async httpx + Tavily SDK, OpenAI SDK.

**Scope:** Only `_fetch_pricing_sources()` and `_extract_product_facts()` in `backend/services/agents/product_advisor.py` + a small EXTRACT_FACTS_SYSTEM prompt edit. No changes to `_search_brave_product` (tech specs search) — that path already works fine.

---

## Current Behavior (the bug)

Claude regeneration 3rd run:
- URL: `https://claude.ai/new` → root domain: `claude.ai`
- Brave query: `"Claude" pricing plans cost monthly` (no site filter)
- Top result: Northeastern Univ. "Claude Enterprise for students and faculty"
- Fact extraction treats Northeastern page as "## Source: Brave Search (official pricing)"
- Result: tagline becomes `"Enterprise Claude access for Northeastern students, faculty, and staff"`; secondary_categories shifts to `["research", "workflow"]`; pricing=null

## Target Behavior

- Brave pricing query tries `site:claude.ai` first → returns few/zero results (Claude's pricing is actually on claude.com)
- Fallback to open query → gets Northeastern + real pricing mixed
- Blocklist filter drops Northeastern (.edu in URL)
- Relevance filter keeps only results mentioning "Claude" AND pricing keywords
- Remaining results labeled as PRIMARY (claude.ai/claude.com/anthropic.com) or SECONDARY (other domains)
- LLM sees labeled sources with explicit authority rule → generates correct pricing

---

## Task 1: Add blocklist + relevance helper functions

**Files:**
- Modify: `backend/services/agents/product_advisor.py`

### Step 1.1: Add constants at top of file (after existing imports, before first prompt constant)

Find the section just after `logger = logging.getLogger(__name__)`. Add:

```python
# --- Pricing source filtering ---
# Domains/paths to exclude from pricing search results. Educational, forum,
# and opinion-blog sources are OFF-topic for product pricing even when they
# mention the product + "pricing". See 2026-04-24 Northeastern incident.
PRICING_DOMAIN_BLOCKLIST = (
    ".edu", ".gov",
    "/students/", "/faculty/", "/university/", "/college/",
    "reddit.com", "medium.com", "substack.com", "quora.com",
    "coursera.org", "udemy.com", "skillshare.com",
)

# Any of these must appear in a pricing result's title+description for it
# to be considered on-topic. Prevents "Claude for Education" pages from
# being classified as pricing pages just because they mention Claude.
PRICING_KEYWORDS = (
    "price", "pricing", "plan", "tier", "subscription",
    "$", "/mo", "/month", "per month", "per year",
    "free tier", "paid", "premium",
)
```

### Step 1.2: Add root-domain extraction helper

Insert after `_resolve_logo_url()` function (which returns the Clearbit URL). Find it with grep and add the new helper right after:

```python
def _extract_root_domain(url: str) -> str:
    """Extract hostname for same-domain matching.

    "https://claude.ai/new" → "claude.ai"
    "https://www.cursor.com/pricing" → "cursor.com"
    """
    if not url:
        return ""
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def _is_blocked_pricing_source(result_url: str) -> bool:
    """True if URL matches any PRICING_DOMAIN_BLOCKLIST pattern."""
    if not result_url:
        return False
    low = result_url.lower()
    return any(bad in low for bad in PRICING_DOMAIN_BLOCKLIST)


def _is_relevant_pricing_result(title: str, snippet: str, product_name: str) -> bool:
    """Result is relevant only if title+snippet mention product AND a pricing keyword."""
    text = f"{title} {snippet}".lower()
    has_product = product_name.lower() in text if product_name else True
    has_pricing = any(kw in text for kw in PRICING_KEYWORDS)
    return has_product and has_pricing


def _classify_pricing_tier(result_url: str, product_root_domain: str) -> str:
    """Return 'primary' when result is on the product's own domain, 'secondary' otherwise."""
    if not product_root_domain:
        return "secondary"
    result_host = _extract_root_domain(result_url)
    if not result_host:
        return "secondary"
    # Exact or subdomain match
    if result_host == product_root_domain or result_host.endswith("." + product_root_domain):
        return "primary"
    return "secondary"
```

### Step 1.3: Syntax check

```bash
cd backend && python -c "import ast; ast.parse(open('services/agents/product_advisor.py', encoding='utf-8').read()); print('OK')"
```

### Step 1.4: Commit

```bash
git add backend/services/agents/product_advisor.py
git commit -m "feat(product-advisor): add pricing source filtering helpers

blocklist (.edu/.gov/forum/opinion blogs), relevance validator
(product+pricing keywords required), tier classifier (primary if
same domain as product URL). Ports patterns from handbook's
validate_term_grounding + news pipeline's source_tier. No behavior
change yet — called in next task."
```

---

## Task 2: Rewrite `_fetch_pricing_sources()` with domain-anchored query + filtering + tier labels

**Files:**
- Modify: `backend/services/agents/product_advisor.py` (the `_fetch_pricing_sources()` function)

### Step 2.1: Replace the whole function

The current function returns a single flat string. New version returns a tier-labeled structure. It's cleaner to rewrite than to patch incrementally.

Locate `async def _fetch_pricing_sources(name: str, url: str) -> str:` and replace the entire function (lines ~542-640) with this version:

```python
async def _fetch_pricing_sources(name: str, url: str) -> str:
    """Gather pricing info from 3 parallel sources, filter noise, tier-label.

    Returns merged labeled text (max 6000 chars) with explicit PRIMARY / SECONDARY
    sections. Fact extraction uses the labels to weight trust.

    Sources:
      A. Tavily direct crawl of {url}/pricing (always PRIMARY if raw_content found)
      B. Brave site:{root_domain} query → PRIMARY; falls back to open query if empty
      C. Tavily general search → mixed, filtered + tier-classified per result

    Filtering:
      - _is_blocked_pricing_source → drop .edu/.gov/forum/opinion domains
      - _is_relevant_pricing_result → drop results not mentioning product+pricing
    """
    loop = asyncio.get_event_loop()
    root_domain = _extract_root_domain(url)

    async def _crawl_pricing_url() -> str:
        """A. Direct crawl. Always PRIMARY when content retrieved."""
        if not url or not settings.tavily_api_key:
            return ""
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=settings.tavily_api_key)
            base = url.rstrip("/")
            pricing_url = f"{base}/pricing"
            result = await loop.run_in_executor(
                None,
                lambda: tavily.search(pricing_url, max_results=1, include_raw_content=True),
            )
            for r in result.get("results", []):
                raw = r.get("raw_content") or r.get("content") or ""
                if raw:
                    return f"[PRIMARY] Direct crawl ({pricing_url}):\n{raw[:3000]}"
        except Exception as e:
            logger.debug("Direct pricing crawl failed for %s: %s", url, e)
        return ""

    async def _brave_pricing_search() -> tuple[list[str], list[str]]:
        """B. Brave. Try site:domain first; fall back to open query.
        Returns (primary_snippets, secondary_snippets).
        """
        if not settings.brave_api_key or not name:
            return [], []
        primary: list[str] = []
        secondary: list[str] = []

        async def _run_brave(q: str) -> list[dict]:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10) as http:
                    resp = await http.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        params={"q": q, "count": 5},
                        headers={"X-Subscription-Token": settings.brave_api_key, "Accept": "application/json"},
                    )
                    resp.raise_for_status()
                    return resp.json().get("web", {}).get("results", [])
            except Exception as e:
                logger.debug("Brave pricing query failed (%s): %s", q, e)
                return []

        # 1st attempt: domain-anchored
        results: list[dict] = []
        if root_domain:
            results = await _run_brave(f'"{name}" pricing plans site:{root_domain}')
        # Fallback: open query (filtering compensates for lack of site anchor)
        if not results:
            results = await _run_brave(f'"{name}" pricing plans cost monthly')

        for r in results[:5]:
            r_url = r.get("url", "")
            if _is_blocked_pricing_source(r_url):
                logger.debug("Brave pricing: blocked %s", r_url)
                continue
            title = r.get("title", "")
            desc = r.get("description", "")[:600]
            extra = r.get("extra_snippets", []) or []
            snippet_body = "\n".join(extra[:2]) if extra else desc
            if not _is_relevant_pricing_result(title, snippet_body, name):
                logger.debug("Brave pricing: off-topic %s — %s", r_url, title[:80])
                continue
            rendered = f"[{title}]({r_url})\n{snippet_body}"
            tier = _classify_pricing_tier(r_url, root_domain)
            (primary if tier == "primary" else secondary).append(rendered)

        return primary, secondary

    async def _tavily_pricing_search() -> tuple[list[str], list[str]]:
        """C. Tavily general. Filtered + tier-classified."""
        if not settings.tavily_api_key or not name:
            return [], []
        primary: list[str] = []
        secondary: list[str] = []
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=settings.tavily_api_key)
            results = await loop.run_in_executor(
                None,
                lambda: tavily.search(
                    f"{name} pricing plans cost",
                    max_results=5,
                    include_raw_content=True,
                ),
            )
            for r in results.get("results", []):
                r_url = r.get("url", "")
                if _is_blocked_pricing_source(r_url):
                    continue
                title = r.get("title", "")
                raw = r.get("raw_content") or r.get("content") or ""
                if not raw:
                    continue
                if not _is_relevant_pricing_result(title, raw[:400], name):
                    continue
                tier = _classify_pricing_tier(r_url, root_domain)
                rendered = f"[{title}]({r_url})\n{raw[:2000]}"
                (primary if tier == "primary" else secondary).append(rendered)
        except Exception as e:
            logger.debug("Tavily pricing search failed for %s: %s", name, e)
        return primary, secondary

    # Run A+B+C in parallel
    crawl_result, (brave_primary, brave_secondary), (tavily_primary, tavily_secondary) = await asyncio.gather(
        _crawl_pricing_url(), _brave_pricing_search(), _tavily_pricing_search(),
    )

    primary_parts: list[str] = []
    if crawl_result:
        primary_parts.append(crawl_result)
    primary_parts.extend(brave_primary)
    primary_parts.extend(tavily_primary)

    secondary_parts: list[str] = brave_secondary + tavily_secondary

    sections: list[str] = []
    if primary_parts:
        sections.append(
            "### PRIMARY (product-domain pricing — trust for pricing_tiers)\n\n"
            + "\n\n".join(primary_parts)
        )
    if secondary_parts:
        sections.append(
            "### SECONDARY (third-party context — do NOT extract pricing_tiers from these)\n\n"
            + "\n\n".join(secondary_parts)
        )

    merged = "\n\n---\n\n".join(sections)[:6000]
    logger.info(
        "Pricing sources for %s: primary=%d, secondary=%d, total_chars=%d",
        name, len(primary_parts), len(secondary_parts), len(merged),
    )
    return merged
```

### Step 2.2: Syntax check

```bash
cd backend && python -c "import ast; ast.parse(open('services/agents/product_advisor.py', encoding='utf-8').read()); print('OK')"
```

### Step 2.3: Commit

```bash
git add backend/services/agents/product_advisor.py
git commit -m "fix(product-advisor): domain-anchored pricing search + filter + tier labels

Three changes to _fetch_pricing_sources:
1. Brave tries site:{root_domain} first; falls back to open query
   only when domain-anchored returns empty.
2. Every result runs through _is_blocked_pricing_source (drops .edu,
   forum, opinion-blog domains) and _is_relevant_pricing_result
   (requires product name + pricing keyword in title+snippet).
3. Results tier-classified into PRIMARY (same domain as product URL)
   vs SECONDARY. Output now has labeled sections so the fact
   extraction prompt can treat them with different authority.

Fixes Northeastern-class pollution where off-topic .edu pages were
accepted as official pricing sources."
```

---

## Task 3: Update EXTRACT_FACTS_SYSTEM to respect tier labels

**Files:**
- Modify: `backend/services/agents/product_advisor.py` (EXTRACT_FACTS_SYSTEM prompt)

### Step 3.1: Add tier-awareness rule

Find `EXTRACT_FACTS_SYSTEM`. Locate the `Rules:` section (ends with "Empty array or null for fields with no evidence."). Add a new rule item at the end of the rules list, BEFORE the `## Example (ChatGPT)` block:

Current block ends like this:
```
- For pricing_tiers: null if no pricing info in sources. Include all tiers visible.
- Empty array or null for fields with no evidence.

## Example (ChatGPT)
```

Insert between the two lines:
```
- For pricing_tiers: extract ONLY from sources labeled PRIMARY. If sources are
  labeled "### PRIMARY" and "### SECONDARY", PRIMARY contains the product's own
  pricing page (trusted). SECONDARY is third-party context (blogs, reviews) —
  do NOT extract pricing_tiers from SECONDARY even when it quotes prices. If
  only SECONDARY exists and PRIMARY is empty, set pricing_tiers=null.
```

### Step 3.2: Syntax check

```bash
cd backend && python -c "import ast; ast.parse(open('services/agents/product_advisor.py', encoding='utf-8').read()); print('OK')"
```

### Step 3.3: Commit

```bash
git add backend/services/agents/product_advisor.py
git commit -m "feat(product-advisor): teach EXTRACT_FACTS to prefer PRIMARY pricing tier

Adds explicit rule: extract pricing_tiers only from sources labeled
PRIMARY in the user prompt. SECONDARY sources (third-party blogs,
university pages, forums) provide context but must not drive pricing
facts. Pairs with the tier labeling in _fetch_pricing_sources."
```

---

## Task 4: Regenerate and verify

### Step 4.1: Re-run the 3-product regeneration script

```bash
cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/regenerate_products.py 2>&1 | tail -40
```

Expected output shape:
- `claude`: tagline should NOT mention Northeastern/university/students
- `claude`: pricing should be "freemium" (matches Anthropic's public tier structure) or null if Brave returned nothing on the restricted query
- All 3 products succeed with 0 validation warnings (or same warnings as last run only)

### Step 4.2: Pull DB state and compare

Query `product_generation_logs` for the three new runs and `ai_products` for the resulting rows. Specifically verify:

- Claude `tagline` does not contain "Northeastern", "student", "faculty", "university"
- Claude `primary_category` is `"assistant"`
- Claude `secondary_categories` does not contain `"research"` (unless genuinely justified)
- Cursor, n8n unchanged or improved (baseline regression check)

### Step 4.3: Push

```bash
git push origin main
```

---

## Out of Scope (future / separate plans)

- Adding `validate_term_grounding`-style verbatim substring check to fact extraction results. The relevance validator in Task 1 is a lighter version of this; full port would require touching the fact prompt too.
- Applying tier labels to `brave_content` (technical specs search). Out of scope — that search path already filters by site:{domain} and hasn't shown pollution.
- Creating a Supabase `product_pricing_blocklist` table like news does with `news_domain_filters`. Overkill for solo project; Python tuple suffices.

## Known Trade-offs

- **False negatives risk:** `_is_relevant_pricing_result` requires both product name AND a pricing keyword. If a product's official pricing page uses creative wording (no "$" sign, uses "cost" in graphics only), the text scrape might fail the validator. Mitigation: blocklist is narrow; relevance filter requires only ONE of many pricing keywords.
- **Fallback domain mismatch:** Some products (Claude, Copilot) have pricing on a sibling domain. `site:claude.ai` returns nothing but open query returns Northeastern. Relevance + blocklist compensates; tier classifier correctly marks the fallback results as SECONDARY so at worst pricing_tiers stays null instead of polluted.
- **Log noise:** New `logger.info` line on every pricing fetch. Acceptable — lets us debug cache/search behavior in production logs.

## Rollback

Three commits; can revert individually. Most impactful revert: Task 2 (the rewrite of `_fetch_pricing_sources`). Reverting it restores the previous behavior but re-opens Northeastern-class pollution.
