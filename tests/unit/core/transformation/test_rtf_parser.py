"""Tests for core/transformation/rtf_parser.py."""
from __future__ import annotations

import pytest

from doors_excel.core.transformation.rtf_parser import ElementKind, RtfElement, parse_rtf


def _kinds(elements: list[RtfElement]) -> list[ElementKind]:
    return [e.kind for e in elements]


def _texts(elements: list[RtfElement]) -> list[str]:
    return [e.text for e in elements if e.text]


class TestPlainText:
    def test_plain_text_element(self) -> None:
        elements = parse_rtf(r"{\rtf1\ansi Hello world.}")
        assert any(e.kind == ElementKind.PLAIN_TEXT for e in elements)
        all_text = "".join(e.text for e in elements)
        assert "Hello world" in all_text

    def test_empty_rtf(self) -> None:
        elements = parse_rtf(r"{\rtf1\ansi }")
        # May return empty or whitespace-only elements — no crash
        assert isinstance(elements, list)


class TestBoldItalic:
    def test_bold_group(self) -> None:
        elements = parse_rtf(r"{\rtf1\ansi {\b bold text\b0}}")
        bold = [e for e in elements if e.kind == ElementKind.BOLD]
        assert bold
        assert "bold text" in bold[0].text

    def test_italic_group(self) -> None:
        elements = parse_rtf(r"{\rtf1\ansi {\i italic\i0}}")
        italic = [e for e in elements if e.kind == ElementKind.ITALIC]
        assert italic
        assert "italic" in italic[0].text


class TestParagraphBreak:
    def test_par_yields_paragraph_break(self) -> None:
        elements = parse_rtf(r"{\rtf1\ansi First.\par Second.}")
        assert any(e.kind == ElementKind.PARAGRAPH_BREAK for e in elements)

    def test_multiple_par(self) -> None:
        elements = parse_rtf(r"{\rtf1\ansi A.\par B.\par C.}")
        breaks = [e for e in elements if e.kind == ElementKind.PARAGRAPH_BREAK]
        assert len(breaks) >= 2


class TestOleDetection:
    def test_object_yields_ole_element(self) -> None:
        rtf = r"{\rtf1\ansi {\object\objemb{\*\objclass Equation.3}\objdata CAFE} text.}"
        elements = parse_rtf(rtf)
        ole = [e for e in elements if e.kind == ElementKind.OLE_OBJECT]
        assert len(ole) == 1

    def test_pict_yields_inline_picture(self) -> None:
        rtf = r"{\rtf1\ansi {\pict\wmetafile8\picw10\pich10 DEADBEEF} text.}"
        elements = parse_rtf(rtf)
        pict = [e for e in elements if e.kind == ElementKind.INLINE_PICTURE]
        assert len(pict) == 1

    def test_ole_has_rtf_fragment(self) -> None:
        rtf = r"{\rtf1\ansi {\object\objemb\objdata CAFE} text.}"
        elements = parse_rtf(rtf)
        ole = [e for e in elements if e.kind == ElementKind.OLE_OBJECT]
        assert ole[0].rtf_fragment is not None

    def test_font_table_skipped(self) -> None:
        rtf = r"{\rtf1\ansi {\fonttbl{\f0 Times New Roman;}} Hello.}"
        elements = parse_rtf(rtf)
        all_text = " ".join(e.text for e in elements)
        assert "Times New Roman" not in all_text


class TestRichOnly:
    def test_ignorable_groups_are_rich_only(self) -> None:
        # \*\objclass is ignorable — should not leak raw text as plain_text
        rtf = r"{\rtf1\ansi text {\*\someprop value} more.}"
        elements = parse_rtf(rtf)
        # "value" should not appear as PLAIN_TEXT
        plain = [e for e in elements if e.kind == ElementKind.PLAIN_TEXT]
        assert all("value" not in e.text for e in plain)


class TestMixedContent:
    def test_bold_inside_paragraph(self) -> None:
        rtf = r"{\rtf1\ansi Hello {\b World\b0} end.}"
        elements = parse_rtf(rtf)
        kinds = _kinds(elements)
        assert ElementKind.PLAIN_TEXT in kinds
        assert ElementKind.BOLD in kinds

    def test_text_before_and_after_ole(self) -> None:
        rtf = r"{\rtf1\ansi before {\object\objemb\objdata AA} after.}"
        elements = parse_rtf(rtf)
        kinds = _kinds(elements)
        assert ElementKind.OLE_OBJECT in kinds
        assert ElementKind.PLAIN_TEXT in kinds
