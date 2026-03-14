from services.quality import compute_quality


def test_perfect_post():
    post = {
        "content_learner": "x" * 4001,
        "guide_items": {
            "one_liner": "a", "action_item": "b",
            "critical_gotcha": "c", "rotating_item": "d",
        },
        "related_news": {
            "big_tech": {"title": "t", "url": "u", "summary": "s"},
            "industry_biz": {"title": "t", "url": "u", "summary": "s"},
            "new_tools": {"title": "t", "url": "u", "summary": "s"},
        },
        "og_image_url": "https://example.com/img.jpg",
    }
    score, flags = compute_quality(post)
    assert score == 4
    assert not any(flags.values())


def test_empty_post():
    score, flags = compute_quality({})
    assert score == 0
    assert all(flags.values())


def test_partial_post():
    post = {
        "content_learner": "x" * 4001,
        "guide_items": {"one_liner": "a"},  # missing 3 fields
    }
    score, flags = compute_quality(post)
    assert flags["missing_guide_items"] is True
    assert flags["short_content"] is False
    assert score == 1  # 3 flags: missing_guide_items + missing_related_news + missing_og_image → score = max(0, 4-3) = 1
