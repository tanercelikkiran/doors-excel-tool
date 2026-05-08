"""Smoke tests for core/transformation/__init__.py re-exports."""
from __future__ import annotations


class TestTransformationReExports:
    def test_hashing_symbols(self) -> None:
        from doors_excel.core.transformation import (
            hash_markdown,
            markdown_unchanged,
            normalize_markdown,
        )
        for fn in (normalize_markdown, hash_markdown, markdown_unchanged):
            assert callable(fn)

    def test_image_placeholder_symbols(self) -> None:
        from doors_excel.core.transformation import (
            PLACEHOLDER_RE,
            extract_placeholders,
            make_placeholder,
            replace_placeholder,
            restore_placeholders,
        )
        assert hasattr(PLACEHOLDER_RE, "finditer")
        for fn in (make_placeholder, extract_placeholders, replace_placeholder, restore_placeholders):
            assert callable(fn)

    def test_ole_detection_symbols(self) -> None:
        from doors_excel.core.transformation import collect_image_groups, scan_for_ole
        assert callable(scan_for_ole)
        assert callable(collect_image_groups)

    def test_rtf_parser_symbols(self) -> None:
        from doors_excel.core.transformation import ElementKind, RtfElement, parse_rtf
        assert callable(parse_rtf)
        assert isinstance(ElementKind, type) or hasattr(ElementKind, "__mro__")

    def test_rtf_to_markdown_symbols(self) -> None:
        from doors_excel.core.transformation import ConversionResult, rtf_to_markdown
        assert callable(rtf_to_markdown)

    def test_markdown_to_rtf_symbol(self) -> None:
        from doors_excel.core.transformation import markdown_to_rtf
        assert callable(markdown_to_rtf)

    def test_dunder_all_complete(self) -> None:
        import doors_excel.core.transformation as m
        if not hasattr(m, "__all__"):
            return
        expected = [
            "normalize_markdown", "hash_markdown", "markdown_unchanged",
            "PLACEHOLDER_RE", "make_placeholder", "extract_placeholders",
            "replace_placeholder", "restore_placeholders",
            "scan_for_ole", "collect_image_groups",
            "ElementKind", "RtfElement", "parse_rtf",
            "ConversionResult", "rtf_to_markdown",
            "markdown_to_rtf",
        ]
        for name in expected:
            assert name in m.__all__, f"{name!r} missing from __all__"
