"""Mine handbook seed candidates from published news (HB-CLAUDE-CURATE-01).

Terms our own published news keeps using but the handbook lacks are the
highest-value seed candidates: readers already meet them, and each new entry
gets internal links from the news that mentions it. The April seed lists
(2026-04-19-handbook-seed-800/) fill in foundational terms news rarely names.

Steps (read-only on the DB; only OpenAI luna calls cost money, < $1 total):
  1. extract terms from every published EN news body (existing
     advisor.extract_terms_from_content), cached per post in extracted.jsonl
  2. aggregate by normalized term: posts mentioning it, first/last seen
  3. apply the news pipeline's code filters (validate_term_scope +
     handbook_term_shape_filter) and drop terms already in handbook_terms
  4. add April seed terms not yet in the DB, marking overlaps
  5. optional nano gate (gate_candidate_terms) on news terms seen 2+ times,
     cached in gate.jsonl so reruns keep the same decisions
  6. write candidates.jsonl + candidates.md (Amy's review table), with a
     near-duplicate hint between candidates

See vault plan 2026-10-23-handbook-seed-claude (결정 0).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import services.pipeline  # noqa: E402,F401  (load order: pipeline before advisor helpers)
from core.database import get_supabase  # noqa: E402
from scripts.run_handbook_seed_batch import DEFAULT_SEED_DIR, load_seed_terms, slugify  # noqa: E402
from services.agents.prompts_handbook_types import normalize_term_key  # noqa: E402
from services.handbook_validators import validate_term_scope  # noqa: E402
from services.pipeline import handbook_term_shape_filter  # noqa: E402

DEFAULT_OUT_DIR = (
    BACKEND_DIR.parent / "vault" / "09-Implementation" / "plans" / "2026-10-23-handbook-seed-claude"
)
GATE_BATCH = 20  # gate_candidate_terms caps output at 1000 tokens


@dataclass
class Candidate:
    key: str
    names: Counter = field(default_factory=Counter)
    korean_names: Counter = field(default_factory=Counter)
    categories: Counter = field(default_factory=Counter)
    posts: set[str] = field(default_factory=set)
    dates: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    low_confidence: int = 0
    seed: dict[str, Any] | None = None
    status: str = "candidate"
    status_reason: str = ""
    gate: str = ""
    gate_reason: str = ""

    @property
    def term(self) -> str:
        if self.names:
            return self.names.most_common(1)[0][0]
        return str((self.seed or {}).get("term", self.key))

    @property
    def category(self) -> str:
        if self.categories:
            return self.categories.most_common(1)[0][0]
        return str((self.seed or {}).get("category", ""))

    @property
    def source(self) -> str:
        if self.posts and self.seed:
            return "news+seed"
        return "news" if self.posts else "seed"

    def as_row(self) -> dict[str, Any]:
        return {
            "term": self.term,
            "korean_name": self.korean_names.most_common(1)[0][0] if self.korean_names else "",
            "category": self.category,
            "source": self.source,
            "posts": len(self.posts),
            "first_seen": min(self.dates) if self.dates else "",
            "last_seen": max(self.dates) if self.dates else "",
            "status": self.status,
            "status_reason": self.status_reason,
            "gate": self.gate,
            "gate_reason": self.gate_reason,
            "seed_type": (self.seed or {}).get("type", ""),
            "aliases": list((self.seed or {}).get("aliases", [])),
            "reason": self.reasons[0] if self.reasons else (self.seed or {}).get("note", ""),
            "post_slugs": sorted(self.posts)[:10],
        }


# --- existing handbook index ------------------------------------------------

@dataclass
class ExistingIndex:
    keys: set[str] = field(default_factory=set)      # normalized term / term_full / korean_name
    slugs: set[str] = field(default_factory=set)


def build_existing_index(rows: list[dict[str, Any]]) -> ExistingIndex:
    index = ExistingIndex()
    for row in rows:
        for column in ("term", "term_full"):
            key = normalize_term_key(str(row.get(column) or ""))
            if key:
                index.keys.add(key)
        if row.get("korean_name"):
            index.keys.add(str(row["korean_name"]).strip().lower())
        if row.get("slug"):
            index.slugs.add(str(row["slug"]).strip().lower())
    return index


def _initials(name: str) -> str:
    words = name.replace("-", " ").split()
    return "".join(w[0] for w in words if w[:1].isupper()).lower()


def existing_match(name: str, index: ExistingIndex, korean_name: str = "") -> str:
    """Why `name` already exists in the handbook, or "" — mirrors the news
    pipeline's slug / term / abbreviation / initials dedup, in memory."""
    key = normalize_term_key(name)
    if slugify(name) in index.slugs:
        return "slug"
    if key and key in index.keys:
        return "term"
    if korean_name and korean_name.strip().lower() in index.keys:
        return "korean_name"
    short = name.split("(")[0].strip()
    if short != name and normalize_term_key(short) in index.keys:
        return "abbreviation"
    initials = _initials(name)
    if len(initials) >= 3 and initials in index.keys:
        return "initials"
    return ""


# --- aggregation ------------------------------------------------------------

def aggregate_extractions(extractions: list[dict[str, Any]]) -> dict[str, Candidate]:
    """extractions: [{slug, published_at, terms: [...]}] -> candidates by normalized key."""
    candidates: dict[str, Candidate] = {}
    for post in extractions:
        date = str(post.get("published_at") or "")[:10]
        seen_in_post: set[str] = set()
        for term in post.get("terms") or []:
            name = str(term.get("term") or "").strip()
            key = normalize_term_key(name)
            if not key:
                continue
            cand = candidates.setdefault(key, Candidate(key=key))
            cand.names[name] += 1
            if term.get("korean_name"):
                cand.korean_names[str(term["korean_name"]).strip()] += 1
            if term.get("category"):
                cand.categories[str(term["category"])] += 1
            if term.get("reason") and len(cand.reasons) < 3:
                cand.reasons.append(str(term["reason"]))
            if term.get("confidence") == "low":
                cand.low_confidence += 1
            if key not in seen_in_post:
                seen_in_post.add(key)
                cand.posts.add(str(post.get("slug")))
                if date:
                    cand.dates.append(date)
    return candidates


def apply_filters(candidates: dict[str, Candidate], index: ExistingIndex) -> None:
    for cand in candidates.values():
        name = cand.term
        korean = cand.korean_names.most_common(1)[0][0] if cand.korean_names else ""
        match = existing_match(name, index, korean)
        if not match and cand.seed:
            for alias in cand.seed.get("aliases") or []:
                match = existing_match(alias, index)
                if match:
                    break
        if match:
            cand.status, cand.status_reason = "exists", match
            continue
        if not cand.posts:
            continue  # seed-only: the April lists were curated against the same scope
        ok, reason = validate_term_scope(name)
        if not ok:
            cand.status, cand.status_reason = "out_of_scope", reason
            continue
        cats, reason = handbook_term_shape_filter({"term": name, "category": cand.category})
        if cats is None:
            cand.status, cand.status_reason = "filtered", reason


def merge_seed_terms(candidates: dict[str, Candidate], seeds: list[Any]) -> None:
    alias_to_key: dict[str, str] = {}
    for key, cand in candidates.items():
        alias_to_key[key] = key
    for seed in seeds:
        keys = [normalize_term_key(seed.term), *(normalize_term_key(a) for a in seed.aliases)]
        target = next((alias_to_key[k] for k in keys if k in alias_to_key), None)
        payload = {
            "term": seed.term, "aliases": list(seed.aliases), "type": seed.term_type,
            "note": seed.note, "category": seed.category,
        }
        if target:
            candidates[target].seed = payload
        else:
            key = keys[0]
            candidates[key] = Candidate(key=key, seed=payload)
            alias_to_key[key] = key


_SIMILAR_STOPWORDS = frozenset({
    "ai", "llm", "model", "models", "the", "of", "for", "and", "automatic", "based", "system",
})


def _stems(term: str) -> frozenset[str]:
    # 6-char stems: "tokenization"/"tokenizer" -> "tokeni", "sandboxing"/"sandbox" -> "sandbo".
    words = normalize_term_key(term).split()
    return frozenset(w[:6] for w in words if w not in _SIMILAR_STOPWORDS and len(w) >= 3)


def similar_candidates(terms: list[str]) -> dict[int, list[int]]:
    """Index -> other indexes whose stem set equals or contains/is contained by it
    ("Red Teaming" ~ "AI Red Teaming", "Tokenization" ~ "Tokenizer"). A review
    hint for merging near-duplicates; the gate only compares against the DB."""
    stems = [_stems(t) for t in terms]
    similar: dict[int, list[int]] = {}
    for i, a in enumerate(stems):
        if not a:
            continue
        for j, b in enumerate(stems):
            if i != j and b and (a <= b or b <= a):
                similar.setdefault(i, []).append(j)
    return similar


def rank(candidates: dict[str, Candidate]) -> list[Candidate]:
    def sort_key(c: Candidate):
        gate_order = {"accept": 0, "": 1, "queue": 2, "reject": 3}.get(c.gate, 1)
        return (gate_order, -len(c.posts), -(int(max(c.dates).replace("-", "")) if c.dates else 0), c.term.lower())
    return sorted((c for c in candidates.values() if c.status == "candidate"), key=sort_key)


# --- IO ---------------------------------------------------------------------

def fetch_news(supabase, limit: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        page = (
            supabase.table("news_posts")
            .select("slug,post_type,published_at,title,content_expert")
            .eq("status", "published")
            .eq("locale", "en")
            .order("published_at", desc=True)
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        rows += page
        if len(page) < 1000:
            break
        start += 1000
    return rows[:limit] if limit else rows


def fetch_existing_terms(supabase) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        page = (
            supabase.table("handbook_terms")
            .select("term,term_full,korean_name,slug,status")
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        rows += page
        if len(page) < 1000:
            break
        start += 1000
    return rows


def load_cache(path: Path, key: str = "slug") -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    cache: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            cache[row[key]] = row
    return cache


async def extract_all(posts: list[dict[str, Any]], cache_path: Path, concurrency: int) -> list[dict[str, Any]]:
    from services.agents.advisor import extract_terms_from_content

    cache = load_cache(cache_path)
    todo = [p for p in posts if p["slug"] not in cache and (p.get("content_expert") or p.get("title"))]
    print(f"extract: {len(posts)} posts, {len(cache)} cached, {len(todo)} to call")
    sem = asyncio.Semaphore(concurrency)
    cost = 0.0

    async def one(post: dict[str, Any]) -> None:
        nonlocal cost
        async with sem:
            try:
                terms, usage = await extract_terms_from_content(post.get("content_expert") or post["title"])
            except Exception as exc:  # keep going; rerun picks it up
                print(f"  ! {post['slug']}: {type(exc).__name__}: {exc}")
                return
        cost += float(usage.get("cost_usd") or 0)
        row = {"slug": post["slug"], "published_at": post["published_at"], "post_type": post["post_type"], "terms": terms}
        cache[post["slug"]] = row
        with cache_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    await asyncio.gather(*(one(p) for p in todo))
    print(f"extract: done, new cost ${cost:.4f}")
    return [cache[p["slug"]] for p in posts if p["slug"] in cache]


async def gate(candidates: list[Candidate], existing_terms: list[str], cache_path: Path) -> None:
    """Nano gate, cached by term so reruns keep the decisions Amy already saw."""
    from services.agents.advisor import gate_candidate_terms

    cache = load_cache(cache_path, key="term")
    for c in candidates:
        if c.term in cache:
            c.gate, c.gate_reason = cache[c.term]["decision"], cache[c.term]["reason"]
    todo = [c for c in candidates if c.term not in cache]
    print(f"gate: {len(candidates) - len(todo)} cached, {len(todo)} to call")
    for i in range(0, len(todo), GATE_BATCH):
        batch = todo[i:i + GATE_BATCH]
        payload = [{"term": c.term, "category": c.category, "reason": c.reasons[0] if c.reasons else ""} for c in batch]
        decisions = {d["term"]: d for d in await gate_candidate_terms(payload, existing_terms)}
        with cache_path.open("a", encoding="utf-8") as f:
            for c in batch:
                d = decisions.get(c.term, {})
                c.gate, c.gate_reason = d.get("decision", ""), d.get("reason", "")
                f.write(json.dumps({"term": c.term, "decision": c.gate, "reason": c.gate_reason}, ensure_ascii=False) + "\n")


def write_outputs(out_dir: Path, ranked: list[Candidate], all_cands: dict[str, Candidate], news_count: int) -> None:
    rows = [c.as_row() for c in ranked]
    with (out_dir / "candidates.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    status_counts = Counter(c.status for c in all_cands.values())
    news_ranked = [r for r in rows if r["posts"] >= 2]
    seed_only = [r for r in rows if r["source"] == "seed"]
    lines = [
        "# Handbook seed candidates — review table",
        "",
        f"> 생성: `backend/scripts/mine_handbook_candidates.py` · 뉴스 {news_count}편 · 계획 [[2026-10-23-handbook-seed-claude]]",
        "> 표시 열 `ok`에 승인(o) / 제외(x)를 적어 주세요. 비워 두면 미검토.",
        "",
        f"- 후보(남은 것): **{len(rows)}** — 뉴스 2편 이상 {len(news_ranked)}, 뉴스 1편 {sum(1 for r in rows if r['posts'] == 1)}, 기존 시드 목록만 {len(seed_only)}",
        f"- 제외: 이미 핸드북에 있음 {status_counts.get('exists', 0)}, 범위 밖 {status_counts.get('out_of_scope', 0)}, 형태 필터 {status_counts.get('filtered', 0)}",
        "",
        "## 1. 뉴스에 2편 이상 나온 용어 (우선)",
        "",
        "`비슷` = 이 표 안에서 같은 개념일 수 있는 후보의 # (하나만 승인하거나 합치기).",
        "",
        "| # | ok | term | 한국어 | category | 편수 | 최근 | source | gate | 비슷 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    similar = similar_candidates([r["term"] for r in news_ranked])
    for i, r in enumerate(news_ranked, 1):
        gate_cell = r["gate"] + (f" — {r['gate_reason'][:60]}" if r["gate"] in ("queue", "reject") and r["gate_reason"] else "")
        similar_cell = ", ".join(f"#{j + 1}" for j in similar.get(i - 1, [])[:3])
        lines.append(
            f"| {i} |  | {r['term']} | {r['korean_name']} | {r['category']} | {r['posts']} | {r['last_seen']} "
            f"| {r['source']} | {gate_cell} | {similar_cell} |"
        )
    lines += ["", "## 2. 기존 시드 목록에만 있는 용어 (카테고리별)", ""]
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for r in seed_only:
        by_cat.setdefault(r["category"], []).append(r)
    for cat in sorted(by_cat):
        lines += [f"### {cat} ({len(by_cat[cat])})", "", "| ok | term | type | note |", "|---|---|---|---|"]
        for r in by_cat[cat]:
            lines.append(f"|  | {r['term']} | {r['seed_type']} | {r['reason'][:70]} |")
        lines.append("")
    lines += ["## 3. 뉴스 1편에만 나온 용어", "", "`candidates.jsonl`에 있음 (posts=1). 기본 제외 — 필요하면 검색해서 추가.", ""]
    (out_dir / "candidates.md").write_text("\n".join(lines), encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--limit", type=int, default=None, help="only the N most recent posts")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--skip-gate", action="store_true", help="skip the nano gate call")
    args = parser.parse_args()

    supabase = get_supabase()
    if not supabase:
        raise SystemExit("Supabase not configured")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    posts = fetch_news(supabase, args.limit)
    extractions = await extract_all(posts, args.out_dir / "extracted.jsonl", args.concurrency)
    existing_rows = fetch_existing_terms(supabase)
    index = build_existing_index(existing_rows)

    candidates = aggregate_extractions(extractions)
    merge_seed_terms(candidates, load_seed_terms(DEFAULT_SEED_DIR))
    apply_filters(candidates, index)

    if not args.skip_gate:
        to_gate = [c for c in candidates.values() if c.status == "candidate" and len(c.posts) >= 2]
        print(f"gate: {len(to_gate)} news terms seen in 2+ posts")
        await gate(to_gate, [str(r.get("term") or "") for r in existing_rows], args.out_dir / "gate.jsonl")

    ranked = rank(candidates)
    write_outputs(args.out_dir, ranked, candidates, len(posts))
    print(f"wrote {len(ranked)} candidates to {args.out_dir}")


if __name__ == "__main__":
    asyncio.run(main())
