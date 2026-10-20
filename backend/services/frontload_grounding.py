"""Frontload claim grounding — FRONTLOAD-GROUND-01 Phase 1 (detect and log only).

Numbers and specific names asserted in the expert EN frontload (headline,
excerpt, focus_items) should appear in the source text the writer saw: the
digest user prompt (source bodies + Community Pulse data). Phase 1 only records
what it finds so a week of logs can measure the false-positive rate before
Phase 2 rewrites anything.

QC evidence selection (`pipeline_quality._frontload_claim_tokens`) is left
untouched on purpose: changing it would move QC scores during the GPT-6
observation window. This module reuses its number/name regexes, not its function.
See vault plan 2026-10-15-frontload-claim-grounding.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# pipeline_quality only imports cleanly after services.pipeline (circular
# re-export block at the bottom of pipeline.py); load it first.
import services.pipeline  # noqa: F401, E402
from services.pipeline_quality import (
    _CLAIM_ACRONYM_RE,
    _CLAIM_MIXED_CASE_RE,
    _CLAIM_NUMBER_RE,
    _CLAIM_PHRASE_STOPWORDS,
    _CLAIM_UNIT_VARIANTS,
    _CLAIM_VERSION_RE,
    _GENERIC_ACRONYMS,
    _HYPHEN_VARIANTS,
    _claim_token_pattern,
)

# KO is a translation: unit wording differs ("5,000억 달러" vs "$500 billion"),
# so checking it would only add false positives.
_EN_FIELDS = ("headline", "excerpt")
_EN_LIST_FIELDS = ("focus_items",)

# Frontload words around a number, used to tell "the source states this 95%"
# from "the source has some unrelated 95%" (10-15: "cached inputs 95% off").
_CONTEXT_CHARS = 40
_SOURCE_CONTEXT_CHARS = 150
_CONTEXT_WORD_RE = re.compile(r"[a-z][a-z-]{3,}")
_CONTEXT_STOPWORDS = frozenset({
    "than", "that", "this", "with", "from", "into", "over", "more", "less", "lower",
    "higher", "about", "after", "before", "their", "they", "will", "while", "which",
    "what", "when", "where", "each", "also", "just", "only", "most", "much", "some",
    "billion", "million", "trillion", "percent", "times", "fold",
})

# Single-word model/product names with a number: "GPT-6", "Qwen3", "o4-mini", "E4B".
_MODEL_NAME_RE = re.compile(r"\b[A-Za-z]+-?\d+[A-Za-z0-9]*(?:[.-][A-Za-z0-9]+)*\b")
# Capitalized words and numbers, keeping unit/version tails ("501B", "1.27.1")
# that the QC run regex cuts off ("Beam 501", "OpenHands 1.27").
_NAME_RUN_RE = re.compile(
    r"(?:[A-Z][\w.-]*|\d[\w.]*)(?:\s+(?:[A-Z][\w.-]*|\d[\w.]*))+"
)
# Two words that both appear within this distance count as the same name
# ("501B open Beam" vs a source's "Beam ... 501B parameters").
_PHRASE_WINDOW_CHARS = 200
_MONTHS = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April", "jun": "June",
    "jul": "July", "aug": "August", "sep": "September", "sept": "September",
    "oct": "October", "nov": "November", "dec": "December",
}


@dataclass(frozen=True)
class FrontloadClaim:
    text: str
    kind: str  # "number" | "name" | "phrase"
    variants: tuple[str, ...]
    context: frozenset[str] = frozenset()
    parts: tuple[str, ...] = ()  # phrase words allowed to co-occur instead of matching verbatim


def _en_frontload_text(frontload: dict[str, Any] | None) -> str:
    frontload = frontload or {}
    texts = [str(frontload.get(field) or "") for field in _EN_FIELDS]
    for field in _EN_LIST_FIELDS:
        texts.extend(str(item) for item in frontload.get(field) or [])
    # " | " keeps a Capitalized run from spanning two fields.
    return " | ".join(texts).translate(_HYPHEN_VARIANTS)


def _context_words(text: str, start: int, end: int) -> frozenset[str]:
    # Stay inside the field that holds the number.
    left = text[max(0, start - _CONTEXT_CHARS): start].split("|")[-1]
    right = text[end: end + _CONTEXT_CHARS].split("|")[0]
    words = _CONTEXT_WORD_RE.findall(f"{left} {right}".lower())
    return frozenset(w for w in words if w not in _CONTEXT_STOPWORDS)


def _name_variants(name: str) -> tuple[str, ...]:
    # Writers and sources disagree on "Gemini-4" vs "Gemini 4" and "Nov 30" vs "November 30".
    variants = [name, name.replace("-", " "), name.replace(" ", "-")]
    first, _, rest = name.partition(" ")
    month = _MONTHS.get(first.rstrip(".").lower())
    if month and rest:
        variants.append(f"{month} {rest}")
    return tuple(dict.fromkeys(variants))


def _is_distinctive_number_word(word: str) -> bool:
    # "501B", "1.27.1", "M5", "2030" are safe to look for apart from their pair;
    # a bare "4" or "30" is everywhere.
    digits = sum(ch.isdigit() for ch in word)
    return any(ch.isalpha() for ch in word) or "." in word or digits >= 3


def frontload_claims(frontload: dict[str, Any] | None) -> list[FrontloadClaim]:
    """Numbers and specific names in the EN frontload, each with its match variants.

    Numbers follow the QC evidence rules: decimals, separated or 3+ digit
    numbers, versions, and short integers only with a unit ("63x", "95%").
    Names: mixed-case words, non-generic acronyms, single words with a number
    ("GPT-6"), and two-word Capitalized phrases containing a number ("Gemini 4").
    Plain Title Case phrases and longer n-grams are skipped — they rarely appear
    verbatim (plurals, sentence-initial verbs like "Watch Bolt E4B").
    """
    text = _en_frontload_text(frontload)
    claims: dict[str, FrontloadClaim] = {}

    def add(claim: FrontloadClaim) -> None:
        claims.setdefault(claim.text.lower(), claim)

    versions: set[str] = set()
    for match in _CLAIM_VERSION_RE.finditer(text):
        core = match.group(1)
        versions.add(core)
        add(FrontloadClaim(match.group(0), "number", (core, f"v{core}")))

    for match in _CLAIM_NUMBER_RE.finditer(text):
        core = match.group(1)
        if any(core in version for version in versions):
            continue
        unit = (match.group(2) or match.group(3) or match.group(4) or "").lower()
        digits = core.replace(",", "").replace(".", "")
        distinctive = "." in core or "," in core or len(digits) >= 3
        if not unit and not distinctive:
            continue  # a bare "3" matches unrelated text
        variants = [match.group(0).strip()]
        if distinctive:
            variants += [core, core.replace(",", "")]
        variants += [f"{core}{suffix}" for suffix in _CLAIM_UNIT_VARIANTS.get(unit, ())]
        add(FrontloadClaim(
            match.group(0).strip(),
            "number",
            tuple(dict.fromkeys(variants)),
            _context_words(text, match.start(), match.end()),
        ))

    def add_name(name: str) -> None:
        add(FrontloadClaim(name, "name", _name_variants(name)))

    for match in _CLAIM_MIXED_CASE_RE.finditer(text):
        add_name(match.group(0))
    for match in _CLAIM_ACRONYM_RE.finditer(text):
        if match.group(0) not in _GENERIC_ACRONYMS:
            add_name(match.group(0))
    for match in _MODEL_NAME_RE.finditer(text):
        add_name(match.group(0))
    for match in _NAME_RUN_RE.finditer(text):
        words = [w.rstrip(".") for w in match.group(0).split()]
        for i in range(len(words) - 1):
            pair = words[i:i + 2]
            if any(w in _CLAIM_PHRASE_STOPWORDS for w in pair) or not pair[0][:1].isalpha():
                continue
            if not any(ch.isdigit() for w in pair for ch in w):
                continue
            phrase = " ".join(pair)
            parts = tuple(pair) if all(
                _is_distinctive_number_word(w) or not any(ch.isdigit() for ch in w) for w in pair
            ) else ()
            add(FrontloadClaim(phrase, "phrase", _name_variants(phrase), parts=parts))

    return list(claims.values())


# "AISI", "MoE": letters only, at least two capitals.
_ACRONYM_LIKE_RE = re.compile(r"(?=(?:[a-z]*[A-Z]){2})[A-Za-z]{2,6}")


def _acronym_expansion_pattern(acronym: str) -> str:
    # "MoE" -> "Mixture-of-Experts": one word per letter, joined by space or hyphen.
    return r"\b" + r"[\s-]+".join(rf"{re.escape(letter)}[\w]*" for letter in acronym) + r"\b"


def _positions(token: str, corpus: str) -> list[int]:
    return [m.start() for m in re.finditer(_claim_token_pattern(token), corpus, re.IGNORECASE)]


def _claim_status(claim: FrontloadClaim, corpus: str, corpus_lower: str) -> str:
    positions = [pos for variant in claim.variants for pos in _positions(variant, corpus)]
    if not positions:
        if claim.kind == "name" and _ACRONYM_LIKE_RE.fullmatch(claim.text):
            if re.search(_acronym_expansion_pattern(claim.text), corpus, re.IGNORECASE):
                return "supported"
        if claim.parts:
            first, second = (_positions(part, corpus) for part in claim.parts)
            if any(abs(a - b) <= _PHRASE_WINDOW_CHARS for a in first for b in second):
                return "supported"
        return "unsupported"
    if claim.kind != "number" or not claim.context:
        return "supported"
    for pos in positions:
        nearby = corpus_lower[max(0, pos - _SOURCE_CONTEXT_CHARS): pos + _SOURCE_CONTEXT_CHARS]
        # 5-char prefix: "inputs" should still meet "input", "cached" meet "cache".
        if any(word[:5] in nearby for word in claim.context):
            return "supported"
    return "weak"


def check_frontload_grounding(frontload: dict[str, Any] | None, source_text: str) -> dict[str, Any]:
    """Classify each EN frontload claim against the writer's source text.

    unsupported: no variant appears in the source.
    weak: a number appears, but never near the words around it in the frontload.
    """
    corpus = str(source_text or "").translate(_HYPHEN_VARIANTS)
    corpus_lower = corpus.lower()
    report: dict[str, Any] = {"checked": 0, "unsupported": [], "weak": [], "supported": []}
    for claim in frontload_claims(frontload):
        status = _claim_status(claim, corpus, corpus_lower)
        report["checked"] += 1
        report[status].append({"claim": claim.text, "kind": claim.kind})
    return report
