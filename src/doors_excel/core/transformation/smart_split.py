"""Smart split for Excel 32 767-char cell limit (C-3)."""
from __future__ import annotations

EXCEL_CELL_LIMIT = 32_767


def smart_split(text: str, limit: int = EXCEL_CELL_LIMIT) -> list[str]:
    """Split *text* into chunks each ≤ *limit* characters.

    Prefers splitting at newline boundaries; falls back to hard split.
    """
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        # Find the last newline within the limit
        cut = remaining.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        else:
            cut += 1  # include the newline in the preceding chunk
        chunks.append(remaining[:cut])
        remaining = remaining[cut:]
    if remaining:
        chunks.append(remaining)
    return chunks


def split_column_headers(base: str, chunk_count: int) -> list[str]:
    """Return header names for *chunk_count* split columns.

    chunk_count=1 → [base]
    chunk_count=3 → [base, base_1, base_2]
    """
    if chunk_count <= 1:
        return [base]
    return [base] + [f"{base}_{i}" for i in range(1, chunk_count)]


def join_split_columns(base: str, row_data: dict[str, str | None]) -> str:
    """Reconstruct the full value by concatenating base + overflow columns."""
    parts = [row_data.get(base) or ""]
    i = 1
    while True:
        key = f"{base}_{i}"
        if key not in row_data:
            break
        parts.append(row_data[key] or "")
        i += 1
    return "".join(parts)
