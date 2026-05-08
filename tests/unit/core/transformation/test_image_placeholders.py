"""Tests for image_placeholders.py (REQ-FUN-114)."""
from __future__ import annotations

from doors_excel.core.transformation.image_placeholders import (
    extract_placeholders,
    make_placeholder,
    replace_placeholder,
    restore_placeholders,
)


class TestMakePlaceholder:
    def test_canonical_format(self) -> None:
        assert make_placeholder(1) == "[IMAGE: 1]"
        assert make_placeholder(3) == "[IMAGE: 3]"

    def test_large_index(self) -> None:
        assert make_placeholder(42) == "[IMAGE: 42]"


class TestExtractPlaceholders:
    def test_no_placeholders(self) -> None:
        assert extract_placeholders("plain text") == []

    def test_single_placeholder(self) -> None:
        assert extract_placeholders("before [IMAGE: 1] after") == [1]

    def test_multiple_placeholders_ordered(self) -> None:
        text = "[IMAGE: 1] text [IMAGE: 2] more [IMAGE: 3]"
        assert extract_placeholders(text) == [1, 2, 3]

    def test_non_sequential_indices(self) -> None:
        text = "[IMAGE: 3] then [IMAGE: 1]"
        assert extract_placeholders(text) == [3, 1]

    def test_extra_whitespace_tolerant(self) -> None:
        assert extract_placeholders("[IMAGE:  2 ]") == [2]

    def test_no_space_after_colon(self) -> None:
        assert extract_placeholders("[IMAGE:1]") == [1]


class TestReplacePlaceholder:
    def test_replaces_first_occurrence(self) -> None:
        result = replace_placeholder("[IMAGE: 1] then [IMAGE: 1]", 1, "RTF_DATA")
        assert result == "RTF_DATA then [IMAGE: 1]"

    def test_replaces_matching_index(self) -> None:
        result = replace_placeholder("before [IMAGE: 2] after", 2, "<pict>")
        assert result == "before <pict> after"

    def test_does_not_replace_other_indices(self) -> None:
        result = replace_placeholder("[IMAGE: 1] [IMAGE: 2]", 1, "X")
        assert result == "X [IMAGE: 2]"

    def test_no_match_returns_unchanged(self) -> None:
        text = "[IMAGE: 3]"
        assert replace_placeholder(text, 5, "X") == text


class TestRestorePlaceholders:
    def test_restores_all(self) -> None:
        text = "a [IMAGE: 1] b [IMAGE: 2] c"
        images = {1: "RTF1", 2: "RTF2"}
        assert restore_placeholders(text, images) == "a RTF1 b RTF2 c"

    def test_missing_key_left_as_is(self) -> None:
        text = "[IMAGE: 1] [IMAGE: 2]"
        images = {1: "A"}
        result = restore_placeholders(text, images)
        assert "A" in result
        assert "[IMAGE: 2]" in result

    def test_empty_images_dict(self) -> None:
        text = "[IMAGE: 1]"
        assert restore_placeholders(text, {}) == "[IMAGE: 1]"

    def test_no_placeholders(self) -> None:
        text = "no placeholders here"
        assert restore_placeholders(text, {1: "X"}) == text
