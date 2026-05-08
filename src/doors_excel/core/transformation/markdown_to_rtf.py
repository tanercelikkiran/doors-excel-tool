"""GFM Markdown → DOORS-compatible RTF conversion (REQ-FUN-105.3).

Output format
-------------
Produces RTF 1 with \\ansicpg1252, a minimal font table (Times New Roman as
\\f0), and default paragraph formatting.  This matches the encoding DOORS
expects for DXL attribute writes.

Supported GFM constructs → RTF:
    plain text          → plain text
    **bold**            → {\\b text\\b0}
    _italic_            → {\\i text\\i0}
    <u>underline</u>    → {\\ul text\\ul0}
    ~~strikethrough~~   → {\\strike text\\strike0}
    paragraph break     → \\par\\n
    * / - unordered list item → \\bullet  text\\par
    1. ordered list item      → N.\\tab text\\par
    [link](url)         → {\\field{\\*\\fldinst HYPERLINK "url"}{\\fldrslt text}}
    # Heading N         → bold text (headings have no native DOORS equivalent)
    [IMAGE: N]          → restored from *images* dict, or left as literal text

Images
------
Pass ``images={1: "<rtf_fragment>", ...}`` to restore OLE/pict placeholders.
If an index is missing from *images* the placeholder is emitted as plain text.

Encoding
--------
Returns a Python str (not bytes).  DOORS COM accepts Python str for DXL.
"""
from __future__ import annotations

from mistune import create_markdown
from mistune.plugins.formatting import strikethrough

from doors_excel.core.transformation.image_placeholders import (
    PLACEHOLDER_RE,
    restore_placeholders,
)

_RTF_HEADER = (
    r"{\rtf1\ansi\ansicpg1252\deff0"
    r"{\fonttbl{\f0\froman\fcharset0 Times New Roman;}}"
    r"\f0\fs24 "
)
_RTF_FOOTER = r"}"

_MD_PARSER = create_markdown(renderer=None, plugins=[strikethrough])


def markdown_to_rtf(md: str, images: dict[int, str] | None = None) -> str:
    """Convert GFM *md* to a DOORS-compatible RTF string.

    *images* maps image index (1-based) to the original RTF fragment.
    If *images* is ``None`` or a key is missing, placeholders become plain text.
    """
    if images:
        md = restore_placeholders(md, images)

    tokens = _MD_PARSER(md) or []
    body = _render_tokens(tokens)
    return _RTF_HEADER + body + _RTF_FOOTER


# ---------------------------------------------------------------------------
# Token renderer
# ---------------------------------------------------------------------------

def _render_tokens(tokens: list[dict]) -> str:
    parts: list[str] = []
    for token in tokens:
        parts.append(_render_token(token))
    return "".join(parts)


def _render_token(token: dict) -> str:
    t = token.get("type", "")

    if t == "paragraph":
        inner = _render_children(token)
        return inner + r"\par" + "\n"

    if t == "blank_line":
        return ""

    if t == "text":
        return _escape(token.get("raw", ""))

    if t == "softbreak":
        return " "

    if t == "linebreak":
        return r"\line "

    if t == "strong":
        inner = _render_children(token)
        return r"{\b " + inner + r"\b0}"

    if t == "emphasis":
        inner = _render_children(token)
        return r"{\i " + inner + r"\i0}"

    if t == "strikethrough":
        inner = _render_children(token)
        return r"{\strike " + inner + r"\strike0}"

    if t == "inline_html":
        raw = token.get("raw", "")
        if raw.lower() == "<u>":
            return r"{\ul "
        if raw.lower() == "</u>":
            return r"\ul0}"
        return ""

    if t == "link":
        url = token.get("attrs", {}).get("url", "")
        inner = _render_children(token)
        url_esc = _escape(url)
        return (
            r"{\field{\*\fldinst HYPERLINK " + f'"{url_esc}"' + r"}{\fldrslt " + inner + r"}}"
        )

    if t == "heading":
        inner = _render_children(token)
        return r"{\b " + inner + r"\b0}" + r"\par" + "\n"

    if t == "list":
        return _render_list(token)

    if t == "list_item":
        inner = _render_children(token)
        return inner

    if t == "block_text":
        return _render_children(token)

    if t == "codespan":
        return _escape(token.get("raw", ""))

    if t == "code":
        return _escape(token.get("raw", "")) + r"\par" + "\n"

    # Unknown — render children if present, else raw text
    if "children" in token:
        return _render_children(token)
    return _escape(token.get("raw", ""))


def _render_list(token: dict) -> str:
    ordered = token.get("attrs", {}).get("ordered", False)
    parts: list[str] = []
    counter = 1
    for item in token.get("children", []):
        inner = _render_children(item)
        if ordered:
            parts.append(f"{counter}.\\tab " + inner + r"\par" + "\n")
            counter += 1
        else:
            parts.append(r"\bullet " + inner + r"\par" + "\n")
    return "".join(parts)


def _render_children(token: dict) -> str:
    return _render_tokens(token.get("children", []))


def _escape(text: str) -> str:
    """Escape RTF special characters: backslash, braces."""
    return text.replace("\\", "\\\\").replace("{", r"\{").replace("}", r"\}")
