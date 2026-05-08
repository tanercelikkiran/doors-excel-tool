"""Tests for ole_detection.py (REQ-FUN-106)."""
from __future__ import annotations

import io

import pytest
from rtfparse.parser import Rtf_Parser

from doors_excel.core.transformation.ole_detection import (
    collect_image_groups,
    scan_for_ole,
)


def _parse(rtf: str):
    stream = io.BytesIO(rtf.encode("latin-1"))
    p = Rtf_Parser(rtf_file=stream)
    return p.parse_file()


class TestScanForOle:
    def test_plain_text_no_ole(self) -> None:
        root = _parse(r"{\rtf1\ansi Hello world.}")
        assert scan_for_ole(root) is False

    def test_object_group_detected(self) -> None:
        root = _parse(
            r"{\rtf1\ansi text {\object\objemb{\*\objclass Equation.3}\objdata CAFE} end.}"
        )
        assert scan_for_ole(root) is True

    def test_pict_group_detected(self) -> None:
        root = _parse(r"{\rtf1\ansi {\pict\wmetafile8\picw100\pich100 DEADBEEF} text.}")
        assert scan_for_ole(root) is True

    def test_bold_not_ole(self) -> None:
        root = _parse(r"{\rtf1\ansi {\b bold text\b0}}")
        assert scan_for_ole(root) is False


class TestCollectImageGroups:
    def test_no_images_returns_empty(self) -> None:
        root = _parse(r"{\rtf1\ansi Plain.}")
        assert collect_image_groups(root) == []

    def test_single_object_collected(self) -> None:
        root = _parse(
            r"{\rtf1\ansi {\object\objemb{\*\objclass Equation.3}\objdata BEEF} text.}"
        )
        groups = collect_image_groups(root)
        assert len(groups) == 1
        assert groups[0].name == "object"

    def test_single_pict_collected(self) -> None:
        root = _parse(r"{\rtf1\ansi {\pict\wmetafile8\picw10\pich10 FACE} text.}")
        groups = collect_image_groups(root)
        assert len(groups) == 1
        assert groups[0].name == "pict"

    def test_object_and_pict_both_collected(self) -> None:
        root = _parse(
            r"{\rtf1\ansi {\object\objemb\objdata AA} {\pict\wmetafile8 BB} end.}"
        )
        groups = collect_image_groups(root)
        assert len(groups) == 2
        names = {g.name for g in groups}
        assert names == {"object", "pict"}

    def test_pict_inside_object_result_not_duplicated(self) -> None:
        r"""The bitmap preview inside \object\result\pict must not appear separately."""
        root = _parse(
            r"{\rtf1\ansi {\object\objemb\objdata CAFE{\result{\pict\wmetafile8 FACE}}} text.}"
        )
        groups = collect_image_groups(root)
        # Only the \object should appear — not the inner \pict
        assert len(groups) == 1
        assert groups[0].name == "object"

    def test_multiple_objects_ordered(self) -> None:
        root = _parse(
            r"{\rtf1\ansi {\object\objemb\objdata A1} mid {\object\objemb\objdata A2} end.}"
        )
        groups = collect_image_groups(root)
        assert len(groups) == 2
        assert all(g.name == "object" for g in groups)
