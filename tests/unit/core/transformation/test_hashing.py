"""Tests for core/transformation/hashing.py (REQ-FUN-105.4)."""
from __future__ import annotations

import hashlib

import pytest

from doors_excel.core.transformation.hashing import (
    hash_markdown,
    markdown_unchanged,
    normalize_markdown,
)


class TestNormalizeMarkdown:
    def test_crlf_to_lf(self) -> None:
        assert normalize_markdown("a\r\nb") == "a\nb\n"

    def test_cr_only_to_lf(self) -> None:
        assert normalize_markdown("a\rb") == "a\nb\n"

    def test_trailing_whitespace_stripped(self) -> None:
        assert normalize_markdown("line1   \nline2\t\n") == "line1\nline2\n"

    def test_collapses_triple_blank_lines(self) -> None:
        text = "a\n\n\n\n\nb"
        result = normalize_markdown(text)
        assert "\n\n\n" not in result

    def test_triple_blank_becomes_double(self) -> None:
        result = normalize_markdown("a\n\n\n\nb")
        assert result == "a\n\nb\n"

    def test_exactly_two_blank_lines_preserved(self) -> None:
        result = normalize_markdown("a\n\n\nb")
        # 3 newlines = 2 blank lines — should collapse to 2 blank lines
        assert result == "a\n\nb\n"

    def test_single_blank_line_preserved(self) -> None:
        result = normalize_markdown("a\n\nb")
        assert result == "a\n\nb\n"

    def test_bullet_asterisk_normalized(self) -> None:
        result = normalize_markdown("* item one\n* item two")
        assert result == "- item one\n- item two\n"

    def test_bullet_plus_normalized(self) -> None:
        result = normalize_markdown("+ item")
        assert result == "- item\n"

    def test_bullet_dash_unchanged(self) -> None:
        result = normalize_markdown("- item")
        assert result == "- item\n"

    def test_exactly_one_trailing_newline(self) -> None:
        result = normalize_markdown("text\n\n\n")
        assert result.endswith("\n")
        assert not result.endswith("\n\n")

    def test_no_trailing_newline_added(self) -> None:
        result = normalize_markdown("text")
        assert result == "text\n"

    def test_indented_bullet_normalized(self) -> None:
        result = normalize_markdown("  * item")
        assert "  - item" in result

    def test_ordered_list_not_affected(self) -> None:
        result = normalize_markdown("1. first\n2. second")
        assert result == "1. first\n2. second\n"


class TestHashMarkdown:
    def test_returns_64_char_hex(self) -> None:
        h = hash_markdown("hello")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_stable_across_calls(self) -> None:
        assert hash_markdown("text") == hash_markdown("text")

    def test_different_text_different_hash(self) -> None:
        assert hash_markdown("foo") != hash_markdown("bar")

    def test_semantically_equivalent_same_hash(self) -> None:
        a = "* item\r\ntext  \n"
        b = "- item\ntext\n"
        assert hash_markdown(a) == hash_markdown(b)

    def test_hash_matches_sha256_of_normalized(self) -> None:
        text = "hello\nworld"
        canonical = normalize_markdown(text)
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert hash_markdown(text) == expected


class TestMarkdownUnchanged:
    def test_unchanged_returns_true(self) -> None:
        h = hash_markdown("hello")
        assert markdown_unchanged("hello", h) is True

    def test_changed_returns_false(self) -> None:
        h = hash_markdown("hello")
        assert markdown_unchanged("goodbye", h) is False

    def test_whitespace_variant_returns_true(self) -> None:
        original = "- item\ntext\n"
        stored_hash = hash_markdown(original)
        variant = "* item\r\ntext  \r\n"
        assert markdown_unchanged(variant, stored_hash) is True

    def test_wrong_hash_returns_false(self) -> None:
        assert markdown_unchanged("text", "a" * 64) is False
