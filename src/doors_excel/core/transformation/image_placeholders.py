"""[IMAGE: N] placeholder insertion and extraction (REQ-FUN-114).

Placeholders use 1-based sequential integers scoped *per object* (per cell).
An 'images' dict maps each integer N to the raw RTF fragment (str) that was
replaced — enabling round-trip restoration in markdown_to_rtf.

Canonical placeholder syntax:  [IMAGE: N]   (exact, no extra whitespace)
"""
from __future__ import annotations

import re

PLACEHOLDER_RE = re.compile(r"\[IMAGE:\s*(\d+)\s*\]")
_CANONICAL_TMPL = "[IMAGE: {n}]"


def make_placeholder(n: int) -> str:
    """Return the canonical placeholder string for image index *n*."""
    return _CANONICAL_TMPL.format(n=n)


def extract_placeholders(text: str) -> list[int]:
    """Return all image indices referenced in *text*, in order of appearance."""
    return [int(m.group(1)) for m in PLACEHOLDER_RE.finditer(text)]


def replace_placeholder(text: str, n: int, rtf_fragment: str) -> str:
    """Replace the first occurrence of ``[IMAGE: N]`` in *text* with *rtf_fragment*."""
    pattern = re.compile(r"\[IMAGE:\s*" + str(n) + r"\s*\]")
    return pattern.sub(rtf_fragment, text, count=1)


def restore_placeholders(text: str, images: dict[int, str]) -> str:
    """Replace every ``[IMAGE: N]`` in *text* using the *images* mapping.

    Indices without a mapping in *images* are left as-is.
    """
    def _replacer(m: re.Match) -> str:
        n = int(m.group(1))
        return images.get(n, m.group(0))

    return PLACEHOLDER_RE.sub(_replacer, text)
