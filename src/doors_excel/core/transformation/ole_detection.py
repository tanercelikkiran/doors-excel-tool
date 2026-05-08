"""OLE and image detection in parsed RTF trees (REQ-FUN-106).

Detection rules (two unambiguous cases):
- Group(name='object')  →  embedded OLE object (equation, ActiveX, …)
- Group(name='pict') that is NOT inside an object's \\result sub-group
  →  inline picture

A Group named 'object' may contain a '\\result' sub-group that itself holds
a 'pict' (the bitmap preview).  We do NOT report that inner 'pict' as a
standalone image — only the enclosing 'object' is reported.

Public API
----------
scan_for_ole(root) → bool
    True if the tree contains any OLE object or standalone picture.

collect_image_groups(root) → list[Group]
    Return all top-level OLE/image Groups in document order.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rtfparse.entities import Group

if TYPE_CHECKING:
    pass

_OLE_NAMES = frozenset({"object", "pict"})


def scan_for_ole(root: Group) -> bool:
    """Return True if *root* contains any OLE object or standalone picture."""
    return bool(collect_image_groups(root))


def collect_image_groups(root: Group) -> list[Group]:
    """Return all OLE/image Groups in document order.

    ``\\object`` groups are collected wholesale (the inner ``\\result.pict``
    is not listed separately).  Standalone ``\\pict`` groups (not nested
    inside an ``\\object``) are also collected.
    """
    result: list[Group] = []
    _collect(root, result, inside_object=False)
    return result


def _collect(node: Group, result: list[Group], *, inside_object: bool) -> None:
    for child in node.structure:
        if not isinstance(child, Group):
            continue
        name = child.name
        if name == "object":
            result.append(child)
            # Don't descend — the inner \result.pict is part of this object
        elif name == "pict" and not inside_object:
            result.append(child)
        elif name == "result":
            # Descend into \result but mark that we're inside an object context
            _collect(child, result, inside_object=True)
        else:
            _collect(child, result, inside_object=inside_object)
