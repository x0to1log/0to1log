"""_clean_writer_output strips $$X$$ LaTeX-math wrappers around numeric values.

GPT-5 writer habitually wraps dollar amounts in $$X$$ for both EN and KO
output (`$$1.5$$ billion`, `$$15$$억 달러`). Frontend's remark-math +
rehype-katex then renders these as math, breaking typography. 2026-05-05
audit: 177 occurrences across 20 published posts. This test guards the
post-process strip in _clean_writer_output.
"""
from services.pipeline import _clean_writer_output


def test_strips_double_dollar_around_simple_number():
    out = _clean_writer_output("valued at $$1.5$$ billion")
    assert out == "valued at 1.5 billion"


def test_strips_double_dollar_in_korean_context():
    out = _clean_writer_output("이 합작사가 $$15$$억 달러 가치에")
    assert out == "이 합작사가 15억 달러 가치에"


def test_strips_double_dollar_with_thousands_separator():
    out = _clean_writer_output("baseline of $$181,000$$ in spending")
    assert out == "baseline of 181,000 in spending"


def test_strips_multiple_double_dollar_in_one_line():
    out = _clean_writer_output(
        "raising $$4$$ billion for a separate venture, valued at $$10$$ billion"
    )
    assert out == "raising 4 billion for a separate venture, valued at 10 billion"


def test_strips_back_to_back_double_dollar_with_em_dash():
    """Real case from May 1: '$$1.25$$ billion–$$1.75$$ billion'."""
    out = _clean_writer_output("$$1.25$$ billion–$$1.75$$ billion in passive inflows")
    assert out == "1.25 billion–1.75 billion in passive inflows"


def test_does_not_touch_single_dollar_money():
    """Single $ before a number (e.g. '$1.5 billion') is normal currency
    formatting and is not interpreted as math by remark-math (no closing $).
    Must not be stripped."""
    text = "valued at $1.5 billion in funding"
    out = _clean_writer_output(text)
    assert out == text


def test_does_not_touch_double_dollar_with_non_numeric_content():
    """A future LaTeX expression like $$\\\\sum_i x_i$$ has letters/operators
    inside; our regex only targets numeric content. Non-numeric $$...$$
    passes through unchanged. (Hypothetical — news bodies don't have real
    math, but defensive.)"""
    text = r"genuine math: $$\sum_i x_i$$"
    out = _clean_writer_output(text)
    assert out == text


def test_idempotent_on_already_clean_content():
    text = "Revenue grew 50% to $5 billion last quarter."
    out = _clean_writer_output(text)
    assert out == text


def test_strips_unit_suffix_billions():
    """Real case from Apr 5: '$$765B$$' for $765 billion."""
    out = _clean_writer_output("market cap of $$765B$$")
    assert out == "market cap of 765B"


def test_strips_unit_suffix_trillions():
    out = _clean_writer_output("a $$1.75T$$ valuation")
    assert out == "a 1.75T valuation"


def test_strips_range_with_em_dash():
    out = _clean_writer_output("around $$50–75B$$ in revenue")
    assert out == "around 50–75B in revenue"


def test_strips_korean_currency_unit():
    """Real case from Apr 7: '$$2,526억 달러$$'."""
    out = _clean_writer_output("매출 $$2,526억 달러$$ 기록")
    assert out == "매출 2,526억 달러 기록"


def test_does_not_touch_real_math_with_backslash():
    """Real case from Apr 12 research-digest: '$$\\sqrt{d}$$' is genuine math."""
    text = r"complexity is $$\sqrt{d}$$"
    out = _clean_writer_output(text)
    assert out == text


def test_does_not_touch_math_with_caret():
    """Apr 12: '$$L^p$$' (math exponent)."""
    text = "in $$L^p$$ space"
    out = _clean_writer_output(text)
    assert out == text


def test_does_not_touch_single_math_variable():
    """A single math letter without digits stays as math."""
    text = "where $$d$$ is the dimension"
    out = _clean_writer_output(text)
    assert out == text


def test_does_not_touch_math_with_braces_and_backslash():
    """Apr 12: '$$\\widetilde{\\Omega}(\\sqrt{d})$$'."""
    text = r"bound is $$\widetilde{\Omega}(\sqrt{d})$$ on dimension"
    out = _clean_writer_output(text)
    assert out == text


def test_does_not_touch_math_with_equals_sign():
    """Apr 12: '$$\\varepsilon=d^{-O(1)}$$'."""
    text = r"setting $$\varepsilon=d^{-O(1)}$$"
    out = _clean_writer_output(text)
    assert out == text
