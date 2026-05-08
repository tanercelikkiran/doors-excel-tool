"""rtfparse wrapper — parse RTF text and expose a classified element sequence.

Element classification
----------------------
Convertible (→ GFM Markdown):
    plain_text, bold, italic, underline, strikethrough,
    paragraph_break, unordered_list_item, ordered_list_item, hyperlink

Rich-only (→ plain text + warning):
    color, font_size, font_change, shading, nested_table, unknown_group

OLE / image (→ [IMAGE: N]):
    ole_object, inline_picture

Each element is a dict:
    {"kind": <ElementKind>, "text": <str>, "rtf_fragment": <str|None>}

"rtf_fragment" is set only for ole_object and inline_picture so that the
caller can stash the original RTF for round-trip restoration.

Input encoding
--------------
DOORS RTF strings arrive as Python str (via COM).  Internally we encode to
cp1252 bytes before feeding rtfparse (matching \\ansicpg1252).
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Iterator

from rtfparse.entities import Control_Word, Group, Plain_Text
from rtfparse.parser import Rtf_Parser

from doors_excel.core.transformation.ole_detection import collect_image_groups

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class ElementKind(Enum):
    # Convertible
    PLAIN_TEXT = auto()
    BOLD = auto()
    ITALIC = auto()
    UNDERLINE = auto()
    STRIKETHROUGH = auto()
    PARAGRAPH_BREAK = auto()
    UNORDERED_LIST_ITEM = auto()
    ORDERED_LIST_ITEM = auto()
    HYPERLINK = auto()
    # Rich-only (lose formatting, keep text)
    RICH_ONLY = auto()
    # OLE / images
    OLE_OBJECT = auto()
    INLINE_PICTURE = auto()


@dataclass
class RtfElement:
    kind: ElementKind
    text: str = ""
    rtf_fragment: str | None = None
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Group names that we recognise and can convert
# ---------------------------------------------------------------------------
_CONVERTIBLE_GROUP = frozenset({"b", "i", "ul", "strike", "ulnone"})
# Group names that carry rich-only formatting (no structural text meaning)
_RICH_ONLY_GROUP = frozenset({"cf", "cb", "highlight", "shading"})
# Control words that signal a paragraph break
_PAR_CW = frozenset({"par", "pard"})
# Control words that indicate a list item (DOORS uses \pn ... \pntext)
_LIST_CW = frozenset({"pntext"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_rtf(rtf: str) -> list[RtfElement]:
    """Parse *rtf* (a Python str) and return a flat list of RtfElement objects."""
    encoded = rtf.encode("cp1252", errors="replace")
    stream = io.BytesIO(encoded)
    p = Rtf_Parser(rtf_file=stream)
    root = p.parse_file()
    elements: list[RtfElement] = []
    _walk_group(root, elements, skip_names={"fonttbl", "colortbl", "stylesheet", "info"})
    return elements


# ---------------------------------------------------------------------------
# Tree walker
# ---------------------------------------------------------------------------

def _walk_group(
    group: Group,
    out: list[RtfElement],
    *,
    skip_names: frozenset[str] | set[str] | None = None,
) -> None:
    skip = skip_names or set()
    name = group.name if hasattr(group, "name") else ""

    if name in skip:
        return

    # OLE / picture — emit a placeholder element and do not descend
    if name == "object":
        out.append(RtfElement(kind=ElementKind.OLE_OBJECT, rtf_fragment=_group_source(group)))
        return
    if name == "pict":
        out.append(RtfElement(kind=ElementKind.INLINE_PICTURE, rtf_fragment=_group_source(group)))
        return

    # Convertible inline formatting groups
    if name in ("b",):
        _wrap_children(group, out, ElementKind.BOLD, skip)
        return
    if name in ("i",):
        _wrap_children(group, out, ElementKind.ITALIC, skip)
        return
    if name in ("ul",):
        _wrap_children(group, out, ElementKind.UNDERLINE, skip)
        return
    if name in ("strike",):
        _wrap_children(group, out, ElementKind.STRIKETHROUGH, skip)
        return

    # Rich-only groups — flatten to plain text with a warning
    if name in _RICH_ONLY_GROUP or (group.ignorable and name not in ("", "rtf")):
        text = _flatten_text(group)
        if text:
            out.append(RtfElement(
                kind=ElementKind.RICH_ONLY,
                text=text,
                warnings=[f"Rich-only RTF element '\\{name}' converted to plain text"],
            ))
        return

    # Descend into any other group
    for child in group.structure:
        _dispatch(child, out, skip)


def _wrap_children(
    group: Group,
    out: list[RtfElement],
    kind: ElementKind,
    skip: set[str] | frozenset[str],
) -> None:
    """Collect children into a single RtfElement of *kind*."""
    inner: list[RtfElement] = []
    for child in group.structure:
        _dispatch(child, inner, skip)
    text = "".join(e.text for e in inner if e.text)
    if text:
        out.append(RtfElement(kind=kind, text=text))
    # Propagate any warnings from inner elements
    for e in inner:
        if e.warnings:
            out.append(e)


def _dispatch(
    node,
    out: list[RtfElement],
    skip: set[str] | frozenset[str],
) -> None:
    if isinstance(node, Group):
        _walk_group(node, out, skip_names=skip)
    elif isinstance(node, Plain_Text):
        text = node.text
        if text and text.strip():
            out.append(RtfElement(kind=ElementKind.PLAIN_TEXT, text=text))
    elif isinstance(node, Control_Word):
        cw = node.control_name
        if cw in _PAR_CW:
            out.append(RtfElement(kind=ElementKind.PARAGRAPH_BREAK))


def _flatten_text(group: Group) -> str:
    """Recursively extract all plain text from *group*."""
    parts: list[str] = []
    for child in group.structure:
        if isinstance(child, Plain_Text):
            parts.append(child.text)
        elif isinstance(child, Group):
            parts.append(_flatten_text(child))
    return "".join(parts)


def _group_source(group: Group) -> str:
    """Return a lightweight identifier string for an OLE/pict group."""
    name = getattr(group, "name", "")
    return f"<rtf:{name}>"
