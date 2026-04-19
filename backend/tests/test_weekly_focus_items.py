"""Unit tests for _validate_focus_items helper."""
from services.pipeline import _validate_focus_items


class TestValidation:
    def test_happy_path_three_items(self):
        items = ['a', 'b', 'c']
        assert _validate_focus_items(items) == ['a', 'b', 'c']

    def test_rejects_wrong_count(self):
        assert _validate_focus_items(['a', 'b']) == []
        assert _validate_focus_items(['a', 'b', 'c', 'd']) == []
        assert _validate_focus_items([]) == []

    def test_rejects_non_list(self):
        assert _validate_focus_items(None) == []
        assert _validate_focus_items('a,b,c') == []
        assert _validate_focus_items({'a': 1}) == []

    def test_strips_whitespace(self):
        assert _validate_focus_items(['  a  ', 'b', 'c']) == ['a', 'b', 'c']

    def test_rejects_empty_string_item(self):
        assert _validate_focus_items(['a', '', 'c']) == []
        assert _validate_focus_items(['a', '   ', 'c']) == []

    def test_stringifies_non_string_items(self):
        # Defensive: LLM might return a number or bool
        assert _validate_focus_items([1, 2, 3]) == ['1', '2', '3']
