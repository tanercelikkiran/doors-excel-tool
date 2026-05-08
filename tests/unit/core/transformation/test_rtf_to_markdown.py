"""Tests for rtf_to_markdown.py (REQ-FUN-105.1, REQ-FUN-105.2, REQ-FUN-114)."""
from __future__ import annotations

import pytest

from doors_excel.core.transformation.rtf_to_markdown import ConversionResult, rtf_to_markdown


class TestPlainConversion:
    def test_plain_text_round_trip(self) -> None:
        result = rtf_to_markdown(r"{\rtf1\ansi Hello world.}")
        assert "Hello world" in result.markdown

    def test_empty_rtf(self) -> None:
        result = rtf_to_markdown(r"{\rtf1\ansi }")
        assert isinstance(result.markdown, str)
        assert result.warnings == []
        assert result.has_ole is False


class TestFormattingConversion:
    def test_bold_becomes_double_asterisk(self) -> None:
        result = rtf_to_markdown(r"{\rtf1\ansi {\b bold\b0}}")
        assert "**bold**" in result.markdown

    def test_italic_becomes_underscore(self) -> None:
        result = rtf_to_markdown(r"{\rtf1\ansi {\i italic\i0}}")
        assert "_italic_" in result.markdown

    def test_underline_becomes_html_u(self) -> None:
        result = rtf_to_markdown(r"{\rtf1\ansi {\ul underlined\ulnone}}")
        assert "<u>underlined</u>" in result.markdown

    def test_strikethrough_becomes_tilde(self) -> None:
        result = rtf_to_markdown(r"{\rtf1\ansi {\strike struck\strike0}}")
        assert "~~struck~~" in result.markdown

    def test_paragraph_break_becomes_double_newline(self) -> None:
        result = rtf_to_markdown(r"{\rtf1\ansi First.\par Second.}")
        assert "\n\n" in result.markdown
        assert "First" in result.markdown
        assert "Second" in result.markdown


class TestOlePlaceholders:
    def test_object_yields_image_placeholder(self) -> None:
        rtf = r"{\rtf1\ansi {\object\objemb{\*\objclass Equation.3}\objdata CAFE} text.}"
        result = rtf_to_markdown(rtf)
        assert "[IMAGE: 1]" in result.markdown
        assert result.has_ole is True

    def test_pict_yields_image_placeholder(self) -> None:
        rtf = r"{\rtf1\ansi {\pict\wmetafile8\picw10\pich10 FACE} text.}"
        result = rtf_to_markdown(rtf)
        assert "[IMAGE: 1]" in result.markdown
        assert result.has_ole is True

    def test_images_dict_populated(self) -> None:
        rtf = r"{\rtf1\ansi {\object\objemb\objdata AA} text.}"
        result = rtf_to_markdown(rtf)
        assert 1 in result.images
        assert result.images[1] is not None

    def test_multiple_images_sequential(self) -> None:
        rtf = r"{\rtf1\ansi {\object\objemb\objdata A1} mid {\object\objemb\objdata A2} end.}"
        result = rtf_to_markdown(rtf)
        assert "[IMAGE: 1]" in result.markdown
        assert "[IMAGE: 2]" in result.markdown
        assert 1 in result.images
        assert 2 in result.images

    def test_no_ole_flag_when_plain(self) -> None:
        result = rtf_to_markdown(r"{\rtf1\ansi plain text}")
        assert result.has_ole is False


class TestReturnType:
    def test_returns_conversion_result(self) -> None:
        result = rtf_to_markdown(r"{\rtf1\ansi text}")
        assert isinstance(result, ConversionResult)
        assert isinstance(result.markdown, str)
        assert isinstance(result.images, dict)
        assert isinstance(result.warnings, list)
        assert isinstance(result.has_ole, bool)


class TestMixedContent:
    def test_text_and_bold_in_same_result(self) -> None:
        result = rtf_to_markdown(r"{\rtf1\ansi Hello {\b World\b0} end.}")
        assert "Hello" in result.markdown
        assert "**World**" in result.markdown
        assert "end" in result.markdown

    def test_font_table_not_in_output(self) -> None:
        rtf = r"{\rtf1\ansi {\fonttbl{\f0 Arial;}} Hello.}"
        result = rtf_to_markdown(rtf)
        assert "Arial" not in result.markdown
        assert "Hello" in result.markdown
