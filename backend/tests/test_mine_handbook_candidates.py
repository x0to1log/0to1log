"""HB-CLAUDE-CURATE-01: handbook seed candidates mined from published news."""
from scripts.mine_handbook_candidates import (
    aggregate_extractions,
    apply_filters,
    build_existing_index,
    existing_match,
    merge_seed_terms,
    rank,
)
from scripts.run_handbook_seed_batch import SeedTerm


def _post(slug, date, *terms):
    return {"slug": slug, "published_at": f"{date}T00:00:00+00:00", "terms": list(terms)}


def _term(name, category="llm-genai", korean="", confidence="high"):
    return {"term": name, "korean_name": korean, "category": category, "confidence": confidence, "reason": f"{name} matters"}


def _seed(term, category="math-statistics", aliases=()):
    return SeedTerm(term=term, aliases=tuple(aliases), term_type="foundational_concept", note="seed note",
                    category=category, slug=term.lower().replace(" ", "-"), source_file="x.jsonl", line_number=1)


def test_aggregation_counts_posts_not_mentions_and_tracks_dates():
    cands = aggregate_extractions([
        _post("a", "2026-09-01", _term("Mixture of Experts"), _term("mixture-of-experts")),
        _post("b", "2026-10-20", _term("Mixture of Experts", korean="전문가 혼합")),
    ])
    moe = cands["mixture of experts"]
    assert len(moe.posts) == 2
    assert (min(moe.dates), max(moe.dates)) == ("2026-09-01", "2026-10-20")
    assert moe.korean_names.most_common(1)[0][0] == "전문가 혼합"


def test_existing_terms_match_by_slug_full_name_korean_and_initials():
    index = build_existing_index([
        {"term": "RAG", "term_full": "Retrieval-Augmented Generation", "korean_name": "검색 증강 생성", "slug": "rag"},
        {"term": "Transformer", "term_full": None, "korean_name": "트랜스포머", "slug": "transformer"},
    ])
    assert existing_match("Retrieval-Augmented Generation", index) == "term"
    assert existing_match("transformer", index) == "slug"
    assert existing_match("Transformers architecture", index, korean_name="트랜스포머") == "korean_name"
    assert existing_match("RAG (Retrieval-Augmented Generation)", index) in {"abbreviation", "term"}
    assert existing_match("Speculative Decoding", index) == ""


def test_filters_drop_existing_out_of_scope_and_shape_failures():
    cands = aggregate_extractions([
        _post("a", "2026-10-01", _term("RAG"), _term("Speculative Decoding"), _term("AI-powered search"),
              _term("Cost Efficiency"), _term("KV Cache", category="not-a-category")),
    ])
    apply_filters(cands, build_existing_index([{"term": "RAG", "slug": "rag"}]))
    status = {c.term: (c.status, c.status_reason) for c in cands.values()}
    assert status["RAG"] == ("exists", "slug")
    assert status["Speculative Decoding"][0] == "candidate"
    assert status["AI-powered search"][0] == "filtered"
    assert status["Cost Efficiency"] == ("filtered", "blocklisted (not handbook-worthy)")
    assert status["KV Cache"][0] == "filtered"


def test_seed_terms_merge_with_news_by_alias_and_seed_only_terms_are_kept():
    cands = aggregate_extractions([_post("a", "2026-10-01", _term("MoE"))])
    merge_seed_terms(cands, [_seed("Mixture of Experts", "deep-learning", aliases=["MoE"]), _seed("Bayes' Theorem")])
    apply_filters(cands, build_existing_index([]))
    moe = cands["moe"]
    assert moe.source == "news+seed"
    bayes = next(c for c in cands.values() if c.term == "Bayes' Theorem")
    assert bayes.source == "seed" and bayes.status == "candidate"


def test_seed_term_already_in_handbook_under_an_alias_is_excluded():
    cands = {}
    merge_seed_terms(cands, [_seed("Low-Rank Adaptation", "llm-genai", aliases=["LoRA"])])
    apply_filters(cands, build_existing_index([{"term": "LoRA", "slug": "lora"}]))
    assert next(iter(cands.values())).status == "exists"


def test_rank_puts_gate_accepts_first_then_more_posts_then_recency():
    cands = aggregate_extractions([
        _post("a", "2026-10-01", _term("Alpha Term"), _term("Beta Term")),
        _post("b", "2026-10-02", _term("Beta Term"), _term("Gamma Term")),
        _post("c", "2026-10-20", _term("Gamma Term")),
    ])
    apply_filters(cands, build_existing_index([]))
    cands["alpha term"].gate = "accept"
    cands["beta term"].gate = "accept"
    cands["gamma term"].gate = "reject"
    assert [c.term for c in rank(cands)] == ["Beta Term", "Alpha Term", "Gamma Term"]


def test_similar_candidates_flags_near_duplicates_only():
    from scripts.mine_handbook_candidates import similar_candidates

    terms = ["Red Teaming", "AI Red Teaming", "Tokenization", "Tokenizer", "Speech Recognition",
             "Automatic Speech Recognition", "World Model", "Flow Matching"]
    sim = similar_candidates(terms)
    assert 1 in sim[0] and 0 in sim[1]          # Red Teaming ~ AI Red Teaming
    assert 3 in sim[2]                          # Tokenization ~ Tokenizer
    assert 5 in sim[4]                          # Speech Recognition ~ Automatic ...
    assert 6 not in sim and 7 not in sim        # unrelated terms get no hint
