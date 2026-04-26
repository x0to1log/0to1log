"""Guard that HN + Reddit comment fetch returns up to TOP_N (now 30) raw
comments, providing enough candidate pool for the gpt-5-nano relevance
filter (Task 3). Prior limit was 5-10 — too small to filter usefully."""

import pytest


@pytest.mark.parametrize("module_attr,expected_min", [
    ("HN_COMMENTS_TOP_N", 30),
    ("REDDIT_COMMENTS_TOP_N", 30),
])
def test_collection_top_n_constants_at_least_30(module_attr, expected_min):
    """The collection module must export named constants for top-N comments
    per platform, and they must be >= 30 after this change."""
    import services.news_collection as nc
    n = getattr(nc, module_attr, None)
    assert n is not None, f"{module_attr} must be defined as a module constant"
    assert n >= expected_min, f"{module_attr} = {n}, expected >= {expected_min}"
