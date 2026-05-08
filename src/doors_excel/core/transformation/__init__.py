"""RTF ↔ Markdown conversion and table structural mapping."""
from __future__ import annotations

from doors_excel.core.transformation.hashing import (
    hash_markdown,
    markdown_unchanged,
    normalize_markdown,
)
from doors_excel.core.transformation.image_placeholders import (
    PLACEHOLDER_RE,
    extract_placeholders,
    make_placeholder,
    replace_placeholder,
    restore_placeholders,
)
from doors_excel.core.transformation.markdown_to_rtf import markdown_to_rtf
from doors_excel.core.transformation.ole_detection import (
    collect_image_groups,
    scan_for_ole,
)
from doors_excel.core.transformation.rtf_parser import (
    ElementKind,
    RtfElement,
    parse_rtf,
)
from doors_excel.core.transformation.rtf_to_markdown import (
    ConversionResult,
    rtf_to_markdown,
)

__all__ = [
    # hashing
    "normalize_markdown",
    "hash_markdown",
    "markdown_unchanged",
    # image placeholders
    "PLACEHOLDER_RE",
    "make_placeholder",
    "extract_placeholders",
    "replace_placeholder",
    "restore_placeholders",
    # ole detection
    "scan_for_ole",
    "collect_image_groups",
    # rtf parser
    "ElementKind",
    "RtfElement",
    "parse_rtf",
    # rtf → markdown
    "ConversionResult",
    "rtf_to_markdown",
    # markdown → rtf
    "markdown_to_rtf",
]
