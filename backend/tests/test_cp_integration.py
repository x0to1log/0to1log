"""End-to-end CP citation path: writer emits [CITE_N] tokens, apply_citations
substitutes into [N](url). Same infrastructure as body citations — proves the
CP section and body share the same contract."""

import pytest
import re

from services.agents.citation_substitution import (
    apply_citations,
    CitationSubstitutionError,
)


def test_cp_body_cite_substitution_end_to_end():
    """Realistic writer output: body paragraphs + CP section, all with
    [CITE_N] tokens. apply_citations substitutes uniformly."""
    writer_body = """## One-Line Summary
OpenAI launched GPT-5.5 with expanded reasoning. [CITE_1]

## Big Tech
### GPT-5.5 launch

OpenAI announced GPT-5.5 today. [CITE_1]

The model targets enterprise. [CITE_2]

## Community Pulse

**Hacker News** (1041↑) — Mixed reactions center on guardrails and pricing. [CITE_3]

> "Laughed a little to this 'We are releasing GPT-5.5...'"
> — Hacker News [CITE_3]

**r/OpenAI** (642↑) — Pricing draws pushback from developers. [CITE_4]

> "$30 per million output? I thought we were democratising intelligence?!"
> — Reddit [CITE_4]
"""
    citations = [
        {"n": 1, "url": "https://openai.com/index/introducing-gpt-5-5/"},
        {"n": 2, "url": "https://techcrunch.com/2026/04/24/gpt55/"},
        {"n": 3, "url": "https://news.ycombinator.com/item?id=47879092"},
        {"n": 4, "url": "https://www.reddit.com/r/OpenAI/comments/1stqlnh/introducing_gpt55_openai/"},
    ]

    result = apply_citations(writer_body, citations)

    # Body paragraphs substituted
    assert "[1](https://openai.com/index/introducing-gpt-5-5/)" in result
    assert "[2](https://techcrunch.com/2026/04/24/gpt55/)" in result

    # CP block headers substituted
    assert (
        "**Hacker News** (1041↑) — Mixed reactions center on guardrails and pricing. "
        "[3](https://news.ycombinator.com/item?id=47879092)"
    ) in result
    assert (
        "**r/OpenAI** (642↑) — Pricing draws pushback from developers. "
        "[4](https://www.reddit.com/r/OpenAI/comments/1stqlnh/introducing_gpt55_openai/)"
    ) in result

    # CP attributions substituted
    assert "> — Hacker News [3](https://news.ycombinator.com/item?id=47879092)" in result
    assert (
        "> — Reddit [4](https://www.reddit.com/r/OpenAI/comments/1stqlnh/introducing_gpt55_openai/)"
    ) in result

    # No unreplaced [CITE_N] tokens
    assert "[CITE_" not in result

    # No bare attributions
    bare = re.search(r"^>\s*—\s*(?:Hacker News|Reddit|r/\S+?)\s*$", result, re.MULTILINE)
    assert bare is None, f"Found bare attribution: {bare.group(0) if bare else ''}"


def test_cp_multi_platform_topic_uses_two_cite_numbers():
    """A group with both HN + Reddit threads → writer emits TWO blocks,
    each with its own [CITE_N]. Substitution produces distinct URLs for each."""
    writer_body = """## Community Pulse

**Hacker News** (1041↑) — HN discussion focuses on guardrails. [CITE_3]

> "guardrails quote"
> — Hacker News [CITE_3]

**r/OpenAI** (642↑) — Reddit discussion focuses on pricing. [CITE_4]

> "pricing quote"
> — Reddit [CITE_4]
"""
    citations = [
        {"n": 3, "url": "https://news.ycombinator.com/item?id=47879092"},
        {"n": 4, "url": "https://www.reddit.com/r/OpenAI/comments/1stqlnh/x/"},
    ]

    result = apply_citations(writer_body, citations)

    # Two distinct URLs land in two distinct blocks
    assert "[3](https://news.ycombinator.com/item?id=47879092)" in result
    assert "[4](https://www.reddit.com/r/OpenAI/comments/1stqlnh/x/)" in result
    # Count occurrences — each CITE_N appears exactly twice (header + attribution)
    assert result.count("[3](https://news.ycombinator.com/item?id=47879092)") == 2
    assert result.count("[4](https://www.reddit.com/r/OpenAI/comments/1stqlnh/x/)") == 2


def test_cp_has_no_quotes_block_substitutes_cite_in_paragraph():
    """HasQuotes: no → writer emits paragraph ending with [CITE_N],
    no blockquote. Substitution still works."""
    writer_body = """## Community Pulse

**r/OpenAI** (642↑) — Discussion is muted despite high upvote count; most comments are off-topic. [CITE_3]
"""
    citations = [
        {"n": 3, "url": "https://www.reddit.com/r/OpenAI/comments/xyz/t/"},
    ]

    result = apply_citations(writer_body, citations)

    assert "[3](https://www.reddit.com/r/OpenAI/comments/xyz/t/)" in result


def test_apply_citations_raises_on_missing_cite_target():
    """Safety: if the writer emits [CITE_N] but citations[] has no matching n,
    apply_citations raises loudly — same contract as body."""
    writer_body = "**Hacker News** (79↑) — summary. [CITE_9]"
    citations = [{"n": 1, "url": "https://x.com/"}]

    with pytest.raises(CitationSubstitutionError):
        apply_citations(writer_body, citations)
