"""Deterministic Python validators for product profiles.

These replace LLM judgment for sub-scores that are mechanically checkable —
counting, regex, substring match, structural checks. The LLM rubric is then
reserved for purely subjective sub-scores (tone, voice, naturalness,
specificity grading).

Each validator returns a dict in the shape the rubric uses:
    {"score": int 0-10, "evidence": str}

Why this design:
- Eliminates LLM judge nondeterminism for ~half of the rubric.
- Makes the same content produce the same score every time.
- Catches actionable bugs (e.g., pricing_detail_ko == pricing_detail) at
  scoring time, surfacing in top_issue without waiting for human spot-check.
- Cuts LLM judge token cost by shrinking the rubric.
"""

from __future__ import annotations

import re

# Mirror PROFILE_EN_SYSTEM's BANNED WORDS list. Keep in sync.
BANNED_WORDS: tuple[str, ...] = (
    "empower", "transform", "seamless", "cutting-edge", "revolutionary",
    "game-changing", "industry-leading", "next-generation", "state-of-the-art",
    "robust", "innovative", "leverage", "unleash",
)

HANGUL_RE = re.compile(r"[가-힣]")
NUMBER_TOKEN_RE = re.compile(r"\b\d+[\w.]*\b")
LONG_WORD_RE = re.compile(r"\b[a-z]{6,}\b")

# Generic words that appear in most spec sentences and aren't distinctive.
SPEC_STOPWORDS: frozenset[str] = frozenset({
    "context", "window", "tokens", "supports", "available", "languages",
    "models", "include", "includes", "capacity", "limits",
})


def _spec_signals(spec_str: str) -> list[str]:
    """Extract distinctive tokens from a spec for substring matching.

    Combines numbers (with optional units like '200k', '4.5', '60s') and
    long words excluding common spec-sentence noise.
    """
    s = str(spec_str).lower()
    nums = NUMBER_TOKEN_RE.findall(s)
    words = [w for w in LONG_WORD_RE.findall(s) if w not in SPEC_STOPWORDS]
    return nums + words


def validate_facts_coverage(profile: dict, facts: dict) -> dict:
    """Did facts.technical_specs get reflected in features?

    Score guide (mirrors LLM rubric, but deterministic):
      10 = 2+ specs visible in features
       8 = facts.technical_specs is empty (honest empty)
       5 = exactly 1 spec visible when 2+ were available
       0 = facts had specs but features ignored them entirely
    """
    specs = facts.get("technical_specs") if isinstance(facts, dict) else None
    if not specs or not isinstance(specs, list):
        return {"score": 8, "evidence": "facts.technical_specs is empty (honest)"}

    features = profile.get("features") or []
    features_blob = " ".join(str(f) for f in features).lower()

    matched: list[str] = []
    for spec in specs:
        signals = _spec_signals(spec)
        if any(sig in features_blob for sig in signals):
            matched.append(str(spec)[:60])

    n_specs = len(specs)
    n_matched = len(matched)

    if n_matched >= 2:
        score = 10
    elif n_matched == 1 and n_specs >= 2:
        score = 5
    elif n_matched == 0:
        score = 0
    else:  # 1 spec total, 1 matched
        score = 10

    return {
        "score": score,
        "evidence": f"{n_matched}/{n_specs} technical_specs reflected in features",
    }


def validate_pricing_integrity(profile: dict) -> dict:
    """Does the pricing label match the pricing_detail markdown content?

    Catches contradictions like pricing='freemium' but pricing_detail has no
    free tier.
    """
    label = profile.get("pricing")
    detail = profile.get("pricing_detail") or ""

    if not label and not detail:
        return {"score": 8, "evidence": "pricing=null AND pricing_detail empty (honest)"}

    detail_low = detail.lower()
    has_free_tier = bool(re.search(r"\$\s*0\b|\bfree\b|\$0/", detail_low))
    has_paid_tier = bool(re.search(r"\$\s*\d", detail_low.replace("$0", "$_zero_")))
    has_enterprise = bool(re.search(r"\benterprise\b|\bcontact\b|\bcustom\b", detail_low))

    if label == "freemium":
        if has_free_tier and has_paid_tier:
            return {"score": 10, "evidence": "freemium label confirmed by free+paid tiers"}
        if not has_free_tier:
            return {"score": 0, "evidence": "label=freemium but no free tier in detail"}
        return {"score": 5, "evidence": "label=freemium but only free tier visible"}

    if label == "free":
        if has_paid_tier:
            return {"score": 5, "evidence": "label=free but paid tiers exist in detail"}
        return {"score": 10, "evidence": "free label confirmed"}

    if label == "paid":
        if has_free_tier:
            return {"score": 5, "evidence": "label=paid but free tier exists"}
        return {"score": 10, "evidence": "paid label confirmed"}

    if label == "enterprise":
        return {"score": 10, "evidence": "enterprise label"}

    if label is None and detail:
        return {"score": 5, "evidence": "pricing label is null but pricing_detail has content"}

    return {"score": 8, "evidence": f"label={label!r}, detail length={len(detail)}"}


def validate_ko_length_compliance(profile: dict) -> dict:
    """tagline_ko ≤ 22 chars AND features_ko count == features count.

    Both purely mechanical. No LLM input needed.
    """
    tagline_ko = profile.get("tagline_ko") or ""
    features = profile.get("features") or []
    features_ko = profile.get("features_ko") or []

    tag_ok = len(tagline_ko) <= 22
    cnt_ok = len(features) == len(features_ko)

    if tag_ok and cnt_ok:
        score, label = 10, "both met"
    elif tag_ok ^ cnt_ok:
        score, label = 5, "one violated"
    else:
        score, label = 0, "both violated"

    return {
        "score": score,
        "evidence": (
            f"tagline_ko={len(tagline_ko)} chars (limit 22, "
            f"{'OK' if tag_ok else 'OVER'}); "
            f"features_ko count={len(features_ko)} vs features={len(features)} "
            f"({'match' if cnt_ok else 'mismatch'}) — {label}"
        ),
    }


def validate_ko_completeness(profile: dict) -> dict:
    """Detect KO fields that are missing or were left as verbatim EN copies.

    Catches the antigravity-style bug where pricing_detail_ko was identical
    to pricing_detail (LLM skipped translation).
    """
    issues: list[str] = []

    pd = (profile.get("pricing_detail") or "").strip()
    pdk = (profile.get("pricing_detail_ko") or "").strip()
    if pd and pdk:
        if pd == pdk:
            issues.append("pricing_detail_ko identical to EN")
        elif not HANGUL_RE.search(pdk):
            issues.append("pricing_detail_ko has no Korean characters")

    en = (profile.get("editor_note") or "").strip()
    enk = (profile.get("editor_note_ko") or "").strip()
    if en:
        if not enk:
            issues.append("editor_note_ko missing")
        elif en == enk:
            issues.append("editor_note_ko identical to EN")
        elif not HANGUL_RE.search(enk):
            issues.append("editor_note_ko has no Korean characters")

    desc = (profile.get("description") or profile.get("description_en") or "").strip()
    desc_ko = (profile.get("description_ko") or "").strip()
    if desc:
        if not desc_ko:
            issues.append("description_ko missing")
        elif desc_ko == desc:
            issues.append("description_ko identical to EN")
        elif not HANGUL_RE.search(desc_ko):
            issues.append("description_ko has no Korean characters")

    if not issues:
        return {"score": 10, "evidence": "all KO fields present and translated"}
    if len(issues) == 1:
        return {"score": 5, "evidence": issues[0]}
    return {"score": 0, "evidence": "; ".join(issues)}


def validate_banned_words(profile: dict) -> dict:
    """Banned marketing words in description?

    Score guide:
      10 = zero banned words
       5 = exactly 1 banned word
       0 = 2+ banned words
    """
    desc = (
        profile.get("description")
        or profile.get("description_en")
        or ""
    ).lower()

    found = [w for w in BANNED_WORDS if w in desc]

    if not found:
        return {"score": 10, "evidence": "no banned words in description"}
    if len(found) == 1:
        return {"score": 5, "evidence": f"1 banned word: '{found[0]}'"}
    return {"score": 0, "evidence": f"{len(found)} banned words: {found}"}


def run_all_python_validators(profile: dict, facts: dict | None) -> dict[str, dict]:
    """Run every Python validator and return the sub-score dict.

    Keys match the sub-score names referenced by the dimension structure.
    """
    return {
        "facts_coverage": validate_facts_coverage(profile, facts or {}),
        "pricing_integrity": validate_pricing_integrity(profile),
        "banned_words": validate_banned_words(profile),
        "ko_length_compliance": validate_ko_length_compliance(profile),
        "ko_completeness": validate_ko_completeness(profile),
    }


def critical_generation_issues(profile: dict) -> list[str]:
    """Return list of critical issues for use at generation time.

    Empty list = profile passes hard checks. Non-empty = something is
    seriously wrong (verbatim KO copy, missing required KO field, etc.)
    that warrants logging or a retry.
    """
    issues: list[str] = []

    completeness = validate_ko_completeness(profile)
    if completeness["score"] < 10:
        issues.append(f"ko_completeness: {completeness['evidence']}")

    length = validate_ko_length_compliance(profile)
    if length["score"] == 0:
        issues.append(f"ko_length_compliance: {length['evidence']}")

    pricing = validate_pricing_integrity(profile)
    if pricing["score"] == 0:
        issues.append(f"pricing_integrity: {pricing['evidence']}")

    return issues
