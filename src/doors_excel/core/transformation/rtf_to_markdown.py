"""RTF → GFM Markdown conversion (REQ-FUN-105.1, REQ-FUN-105.2, REQ-FUN-114).

Convertible RTF elements → GFM:
    plain text   → as-is
    \\b          → **text**
    \\i          → _text_
    \\ul         → <u>text</u>   (GFM has no underline; HTML inline is canonical)
    \\strike     → ~~text~~
    \\par        → paragraph break (double newline)
    OLE/\\object → [IMAGE: N]  (N = 1-based per-cell counter)
    \\pict       → [IMAGE: N]

Rich-only elements (colors, font size/face, shading, nested tables) are
converted to plain text and a warning is emitted (REQ-FUN-105.2).

Return value
------------
``rtf_to_markdown(rtf)`` returns a ``ConversionResult`` named tuple:
    markdown   str              — GFM markdown string
    images     dict[int, str]   — maps image index → rtf_fragment identifier
    warnings   list[str]        — one entry per rich-only fallback
    has_ole    bool             — True if any OLE/image was found (REQ-FUN-106)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from doors_excel.core.transformation.image_placeholders import make_placeholder
from doors_excel.core.transformation.rtf_parser import ElementKind, RtfElement, parse_rtf


@dataclass
class ConversionResult:
    markdown: str
    images: dict[int, str]
    warnings: list[str]
    has_ole: bool


def rtf_to_markdown(rtf: str) -> ConversionResult:
    """Convert *rtf* (Python str) to GFM Markdown.

    Rich-only formatting is stripped to plain text; a warning is emitted for
    each occurrence (REQ-FUN-105.2).  OLE objects and inline pictures are
    replaced with ``[IMAGE: N]`` placeholders (REQ-FUN-114).
    """
    elements = parse_rtf(rtf)
    parts: list[str] = []
    images: dict[int, str] = {}
    warnings: list[str] = []
    image_counter = 0
    pending_par = False

    for elem in elements:
        kind = elem.kind

        if kind == ElementKind.PARAGRAPH_BREAK:
            pending_par = True
            continue

        if kind in (ElementKind.OLE_OBJECT, ElementKind.INLINE_PICTURE):
            if pending_par and parts:
                parts.append("\n\n")
                pending_par = False
            image_counter += 1
            images[image_counter] = elem.rtf_fragment or ""
            parts.append(make_placeholder(image_counter))
            continue

        # Flush pending paragraph break before any text content
        if pending_par and parts:
            parts.append("\n\n")
            pending_par = False

        text = elem.text
        if not text:
            continue

        if kind == ElementKind.PLAIN_TEXT:
            parts.append(text)
        elif kind == ElementKind.BOLD:
            parts.append(f"**{text}**")
        elif kind == ElementKind.ITALIC:
            parts.append(f"_{text}_")
        elif kind == ElementKind.UNDERLINE:
            parts.append(f"<u>{text}</u>")
        elif kind == ElementKind.STRIKETHROUGH:
            parts.append(f"~~{text}~~")
        elif kind == ElementKind.RICH_ONLY:
            parts.append(text)
            warnings.extend(elem.warnings)
        else:
            parts.append(text)

    markdown = "".join(parts).strip()
    return ConversionResult(
        markdown=markdown,
        images=images,
        warnings=warnings,
        has_ole=bool(images),
    )
