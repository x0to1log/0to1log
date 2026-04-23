"""Substitute [CITE_N] placeholders with [N](URL) markdown links.

Writer emits placeholder-only bodies (body text says `[CITE_1]`), and a
`citations: [{n, url}]` sidecar list whose `url` values are constrained
by the OpenAI strict json_schema enum (= fact_pack.news_items[].url).
This module converts placeholders into the final markdown form.

Defensive: also rejects raw ``[N](URL)`` patterns in the body — if those
slip through, the writer has ignored the output contract and we want a
loud failure, not silent publication.
"""
from __future__ import annotations

import re
from typing import Mapping, Sequence

_PLACEHOLDER_RE = re.compile(r"\[CITE_(\d+)\]")
_INLINE_CITATION_RE = re.compile(r"\[(\d+)\]\(https?://[^)\s]+\)")


class CitationSubstitutionError(Exception):
    """Raised when body+citations don't form a coherent output."""


def apply_citations(body: str, citations: Sequence[Mapping[str, object]]) -> str:
    """Replace ``[CITE_N]`` placeholders with ``[N](URL)`` markdown links.

    Raises ``CitationSubstitutionError`` when:
    - the body contains an inline ``[N](URL)`` citation (writer violated the
      output contract — it should only emit placeholders), or
    - the body references a placeholder whose ``n`` is missing from
      ``citations``.
    """
    if not body:
        return body

    inline_match = _INLINE_CITATION_RE.search(body)
    if inline_match:
        raise CitationSubstitutionError(
            f"body contains inline citation {inline_match.group(0)!r}; "
            "writer should emit [CITE_N] placeholders instead"
        )

    url_by_n: dict[int, str] = {}
    for c in citations:
        n = int(c["n"])
        url = str(c["url"])
        url_by_n[n] = url

    missing: list[int] = []

    def _sub(m: re.Match) -> str:
        n = int(m.group(1))
        if n not in url_by_n:
            missing.append(n)
            return m.group(0)
        return f"[{n}]({url_by_n[n]})"

    result = _PLACEHOLDER_RE.sub(_sub, body)

    if missing:
        raise CitationSubstitutionError(
            f"body references [CITE_{sorted(set(missing))}] but citations list "
            f"has only n={sorted(url_by_n)}"
        )

    return result
