import json
import logging

from models.ranking import RankedCandidate, RelatedPicks
from models.business import BusinessPost
from services.agents.client import get_openai_client
from services.agents.prompts import BUSINESS_SYSTEM_PROMPT
from core.config import settings

logger = logging.getLogger(__name__)


def _build_business_user_prompt(
    candidate: RankedCandidate,
    related: RelatedPicks,
    context: str,
    batch_id: str,
) -> str:
    """Build the user prompt for the business analyst agent."""
    related_section = "## Related News 후보\n"
    if related.big_tech:
        related_section += f"- Big Tech: {related.big_tech.title} ({related.big_tech.url})\n"
    if related.industry_biz:
        related_section += f"- Industry & Biz: {related.industry_biz.title} ({related.industry_biz.url})\n"
    if related.new_tools:
        related_section += f"- New Tools: {related.new_tools.title} ({related.new_tools.url})\n"

    return (
        f"아래 메인 뉴스와 관련 뉴스를 바탕으로 3페르소나 포스트를 작성하세요.\n\n"
        f"## 메인 뉴스\n"
        f"제목: {candidate.title}\n"
        f"URL: {candidate.url}\n"
        f"요약: {candidate.snippet}\n"
        f"랭킹 이유: {candidate.ranking_reason}\n\n"
        f"{related_section}\n"
        f"## Tavily 수집 컨텍스트\n{context}\n\n"
        f"slug: {batch_id}-business-daily"
    )


async def generate_business_post(
    candidate: RankedCandidate,
    related: RelatedPicks,
    context: str,
    batch_id: str,
) -> BusinessPost:
    """Step 3-B: Generate a 3-persona business post using gpt-4o.

    Takes the main business pick and related news picks to produce
    content for beginner/learner/expert personas plus guide_items and related_news.
    """
    client = get_openai_client()
    user_prompt = _build_business_user_prompt(candidate, related, context, batch_id)

    response = await client.chat.completions.create(
        model=settings.openai_model_main,
        messages=[
            {"role": "system", "content": BUSINESS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    raw = response.choices[0].message.content
    logger.info("Business agent raw response length: %d", len(raw))

    data = json.loads(raw)
    result = BusinessPost.model_validate(data)
    return result
