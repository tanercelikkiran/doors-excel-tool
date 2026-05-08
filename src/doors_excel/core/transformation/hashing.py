"""SHA-256 content hashing for no-change bypass (REQ-FUN-105.4).

Normalization rules (applied in order):
1. Unify line endings to LF (\n).
2. Strip trailing whitespace from each line.
3. Collapse runs of 3+ consecutive blank lines to exactly 2 blank lines.
4. Normalise list bullet characters (* or +) to -.
5. Ensure exactly one trailing newline.

Two Markdown strings are considered "semantically equivalent" iff they
produce the same hash after normalization.  The hash is hex-encoded SHA-256.
"""
from __future__ import annotations

import hashlib
import re

_BULLET_RE = re.compile(r"^([ \t]*)[*+]( )", re.MULTILINE)
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def normalize_markdown(text: str) -> str:
    """Return the canonical form of *text* used for hash comparison."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = _BULLET_RE.sub(r"\1-\2", text)
    text = _MULTI_BLANK_RE.sub("\n\n", text)
    text = text.strip("\n") + "\n"
    return text


def hash_markdown(text: str) -> str:
    """Return a hex-encoded SHA-256 hash of the normalized *text*."""
    canonical = normalize_markdown(text)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def markdown_unchanged(text: str, expected_hash: str) -> bool:
    """Return True when *text* normalizes to *expected_hash*."""
    return hash_markdown(text) == expected_hash
