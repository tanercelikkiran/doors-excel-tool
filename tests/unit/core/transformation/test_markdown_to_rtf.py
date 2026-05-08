"""Tests for markdown_to_rtf.py (REQ-FUN-105.3)."""
from __future__ import annotations

import pytest

from doors_excel.core.transformation.markdown_to_rtf import markdown_to_rtf


class TestRtfStructure:
    def test_has_rtf_header(self) -> None:
        result = markdown_to_rtf("hello")
        assert result.startswith(r"{\rtf1\ansi")

    def test_has_closing_brace(self) -> None:
        result = markdown_to_rtf("hello")
        assert result.endswith("}")

    def test_has_font_table(self) -> None:
        result = markdown_to_rtf("hello")
        assert "fonttbl" in result

    def test_plain_text_in_output(self) -> None:
        result = markdown_to_rtf("hello world")
        assert "hello world" in result


class TestBoldItalic:
    def test_bold_renders_b_control(self) -> None:
        result = markdown_to_rtf("**bold**")
        assert r"\b " in result
        assert r"\b0}" in result
        assert "bold" in result

    def test_italic_renders_i_control(self) -> None:
        result = markdown_to_rtf("_italic_")
        assert r"\i " in result
        assert r"\i0}" in result
        assert "italic" in result

    def test_strikethrough_renders_strike(self) -> None:
        result = markdown_to_rtf("~~struck~~")
        assert r"\strike " in result
        assert r"\strike0}" in result
        assert "struck" in result


class TestUnderline:
    def test_html_u_becomes_ul(self) -> None:
        result = markdown_to_rtf("<u>underlined</u>")
        assert r"\ul " in result
        assert r"\ul0}" in result
        assert "underlined" in result


class TestParagraphs:
    def test_paragraph_has_par(self) -> None:
        result = markdown_to_rtf("First paragraph.\n\nSecond paragraph.")
        assert r"\par" in result

    def test_two_paragraphs_two_par(self) -> None:
        result = markdown_to_rtf("Para one.\n\nPara two.")
        assert result.count(r"\par") >= 2


class TestLists:
    def test_unordered_list_bullet(self) -> None:
        result = markdown_to_rtf("- item one\n- item two")
        assert r"\bullet" in result
        assert "item one" in result
        assert "item two" in result

    def test_ordered_list_numbered(self) -> None:
        result = markdown_to_rtf("1. first\n2. second")
        assert "1." in result
        assert "2." in result
        assert "first" in result
        assert "second" in result

    def test_ordered_list_tab(self) -> None:
        result = markdown_to_rtf("1. first")
        assert r"\tab" in result


class TestHeadings:
    def test_heading_bold(self) -> None:
        result = markdown_to_rtf("# Heading One")
        assert r"\b " in result
        assert "Heading One" in result

    def test_heading_has_par(self) -> None:
        result = markdown_to_rtf("# Title")
        assert r"\par" in result


class TestLinks:
    def test_link_uses_field(self) -> None:
        result = markdown_to_rtf("[click here](http://example.com)")
        assert r"\field" in result
        assert "HYPERLINK" in result
        assert "http://example.com" in result
        assert "click here" in result


class TestEscaping:
    def test_backslash_escaped(self) -> None:
        result = markdown_to_rtf(r"path\to\file")
        # Backslashes in plain text must be doubled
        assert r"\\" in result

    def test_brace_escaped(self) -> None:
        result = markdown_to_rtf("{value}")
        assert r"\{" in result
        assert r"\}" in result


class TestImageRestoration:
    def test_placeholder_restored_from_images(self) -> None:
        images = {1: r"{\pict\wmetafile8 DEADBEEF}"}
        result = markdown_to_rtf("[IMAGE: 1] text", images=images)
        assert r"\pict" in result or "DEADBEEF" in result

    def test_missing_image_leaves_placeholder(self) -> None:
        result = markdown_to_rtf("[IMAGE: 2] text", images={})
        assert "[IMAGE: 2]" in result

    def test_no_images_dict_leaves_placeholder(self) -> None:
        result = markdown_to_rtf("[IMAGE: 1]")
        assert "[IMAGE: 1]" in result


class TestEmptyInput:
    def test_empty_string(self) -> None:
        result = markdown_to_rtf("")
        assert result.startswith(r"{\rtf1")
        assert result.endswith("}")
