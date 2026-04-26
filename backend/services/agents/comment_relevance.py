"""LLM-as-judge relevance filter for community comments.

Given a candidate pool of HN/Reddit comments (typically top voted 30) and
the article context, ask gpt-5-nano which comments are actually about the
article topic. Filter out tangential rants, political flame wars, off-topic
discussions that happen to be top-voted in big threads.

Apr 25 DeepSeek case: HN thread had 1357 comments; top voted were political
(Tiananmen, Iran-Israel, Mexico cartels) not technical. Sending those to the
summarizer triggered sentiment=null drop and lost the entire CP section.

Cost: ~$0.001 per call (gpt-5-nano). At 6 groups × 1-2 platforms/day,
~$0.008-0.012/day extra. Negligible.

Fallback semantics (R3 from plan revisions):
- API failure (exception) → fail-OPEN: return candidates[:max_pick]
- Malformed LLM response → fail-OPEN: same as API failure
- Valid LLM judgment of [] (or all-invalid indexes) → fail-CLOSED: return []
  (let summarizer's sentiment=null path drop the section honestly — Apr 25
  DeepSeek case was 'all top-voted are off-topic' and that's the intended
  signal, not a degradation case)
"""
import logging
from typing import Any

from core.config import settings
from services.agents.client import (
    build_completion_kwargs,
    extract_usage_metrics,
    get_openai_client,
    parse_ai_json,
    with_flex_retry,
)

logger = logging.getLogger(__name__)


_RELEVANCE_FILTER_PROMPT = """You are filtering community comments for an AI news digest.

Given:
- An article (title + excerpt)
- A list of candidate comments from a discussion thread (HN or Reddit), top-voted first

Your job: pick the comments that are SUBSTANTIVELY ABOUT the article's topic. Drop:
- Off-topic political/social rants (mentions of Tiananmen, Iran, USA politics, racial issues, etc. when the article is about a tech/AI release)
- Pure emotional reactions with no information
- Generic comments that could apply to any article ("Wow, this is huge")
- Meta-comments about HN/Reddit itself
- Comments that admit to not reading the article

Keep:
- Technical critique with specifics (architecture, benchmarks, performance numbers)
- Deployment / production concerns (cost, integration, edge cases)
- Comparisons to alternatives (named tools, methods, prior work)
- Substantive disagreement or supporting evidence
- Personal experience reports relevant to the article topic

Output JSON only:
{"selected_indexes": [<comment indexes you picked, 0-based, max 10>]}

Pick the smallest set that captures the substantive discussion. If a comment is borderline, drop it. If NO comment is substantively about the article topic (top-voted is all off-topic noise), return an EMPTY list — that signals 'this section should not appear'."""


async def filter_relevant_comments(
    candidates: list[str],
    article_title: str,
    article_excerpt: str,
    max_pick: int = 10,
) -> tuple[list[str], dict[str, Any]]:
    """Filter candidates down to article-relevant comments via gpt-5-nano.

    Returns (filtered_comments, usage_dict).

    Fallback semantics:
    - Empty input → ([], {})
    - API/parse exception → fail-OPEN: candidates[:max_pick]
    - Malformed LLM shape (data not dict, selected_indexes not list) →
      fail-OPEN: candidates[:max_pick]
    - Valid LLM response with empty/all-invalid indexes → fail-CLOSED: []
      (intended signal: 'drop the section')
    - Otherwise: filtered subset, capped at max_pick
    """
    if not candidates:
        return [], {}

    client = get_openai_client()
    # gpt-5-nano via openai_model_nano if defined, else openai_model_light
    model = getattr(settings, "openai_model_nano", None) or settings.openai_model_light

    numbered = "\n\n".join(f"[{i}] {c}" for i, c in enumerate(candidates))
    user_content = (
        f"## Article\nTitle: {article_title}\nExcerpt: {article_excerpt}\n\n"
        f"## Candidate comments (top-voted first)\n\n{numbered}"
    )

    kwargs = build_completion_kwargs(
        model=model,
        messages=[
            {"role": "system", "content": _RELEVANCE_FILTER_PROMPT},
            {"role": "user", "content": user_content},
        ],
        max_tokens=200,
        response_format={"type": "json_object"},
        service_tier="flex",
        prompt_cache_key="cp-comment-relevance",
    )

    # ----- API call layer (exception = fail-open) -----
    try:
        response = await with_flex_retry(
            lambda: client.chat.completions.create(**kwargs),
        )
        raw_output = response.choices[0].message.content or ""
        data = parse_ai_json(raw_output, "comment_relevance_filter")
        usage = extract_usage_metrics(response, model, requested_service_tier="flex")
    except Exception as e:
        logger.warning(
            "Comment relevance filter API failure (%s) — fail-open to top-%d voted",
            e, max_pick,
        )
        return candidates[:max_pick], {}

    # ----- Response shape layer (malformed = fail-open) -----
    if not isinstance(data, dict):
        logger.warning(
            "Comment relevance filter returned non-dict (%s) — fail-open to top-%d voted",
            type(data).__name__, max_pick,
        )
        return candidates[:max_pick], usage

    selected_indexes = data.get("selected_indexes")
    if not isinstance(selected_indexes, list):
        logger.warning(
            "Comment relevance filter missing selected_indexes list (got %r) — "
            "fail-open to top-%d voted",
            type(selected_indexes).__name__, max_pick,
        )
        return candidates[:max_pick], usage

    # ----- Index validation layer (LLM made a judgment; we just sanitize) -----
    valid: list[str] = []
    for idx in selected_indexes:
        if not isinstance(idx, int):
            continue
        if 0 <= idx < len(candidates):
            valid.append(candidates[idx])
        if len(valid) >= max_pick:
            break

    # ----- Result layer -----
    # Empty result here means LLM either selected [] or all selected indexes
    # were out of range. Either way, treat as 'LLM judged nothing relevant'
    # → fail-CLOSED. The summarizer's sentiment=null path will drop the
    # section honestly. Apr 25 DeepSeek is exactly this case.
    if not valid:
        logger.info(
            "Comment relevance filter selected 0 valid comments — fail-closed "
            "(letting summarizer drop the section)",
        )

    return valid, usage
