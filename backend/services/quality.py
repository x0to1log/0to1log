from typing import Any


MIN_CONTENT_CHARS = 4000  # KO floor (v4: all personas min 5000 EN / 4000 KO)
GUIDE_FIELDS = ("one_liner", "action_item", "critical_gotcha", "rotating_item")
RELATED_NEWS_KEYS = ("big_tech", "industry_biz", "new_tools")


def compute_quality(post: dict[str, Any]) -> tuple[int, dict[str, bool]]:
    """Compute quality score (0-4) and flags dict for a post.

    Score 4 = all checks pass (Ready)
    Score 3 = 1 check fails (Minor)
    Score 2 = 2 checks fail (Review)
    Score 0-1 = 3-4 checks fail (Incomplete)
    """
    flags: dict[str, bool] = {}

    # Check content length (business uses learner; research uses original)
    content = (
        post.get("content_learner") or
        post.get("content_original") or
        ""
    )
    flags["short_content"] = len(content) < MIN_CONTENT_CHARS

    # Check guide_items completeness
    guide = post.get("guide_items") or {}
    flags["missing_guide_items"] = not all(guide.get(f) for f in GUIDE_FIELDS)

    # Check related_news completeness
    related = post.get("related_news") or {}
    flags["missing_related_news"] = not all(related.get(k) for k in RELATED_NEWS_KEYS)

    # Check og_image
    flags["missing_og_image"] = not post.get("og_image_url")

    missing_count = sum(flags.values())
    score = max(0, 4 - missing_count)

    return score, flags
