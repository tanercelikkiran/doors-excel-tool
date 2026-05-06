"""DXL payload splitter — enforces the 48 KB COM argument limit."""
from __future__ import annotations

DXL_CHUNK_BYTES: int = 48 * 1024       # 49152 — hard COM argument limit
DXL_BUFFER_SEGMENT_BYTES: int = 32 * 1024  # 32768 — iterative Buffer accumulation


def _split_bytes(text: str, max_bytes: int) -> list[str]:
    encoded = text.encode("utf-8")
    segments: list[str] = []
    start = 0
    while start < len(encoded):
        end = start + max_bytes
        chunk_bytes = encoded[start:end]
        # Walk back until valid UTF-8 boundary
        while True:
            try:
                decoded = chunk_bytes.decode("utf-8")
                segments.append(decoded)
                start += len(chunk_bytes)
                break
            except UnicodeDecodeError:
                chunk_bytes = chunk_bytes[:-1]
    return segments


def chunk_dxl(payload: str) -> list[str]:
    """Split *payload* into chunks each ≤ DXL_CHUNK_BYTES bytes (UTF-8)."""
    if not payload:
        return [""]
    if len(payload.encode("utf-8")) <= DXL_CHUNK_BYTES:
        return [payload]
    return _split_bytes(payload, DXL_CHUNK_BYTES)


def buffer_segments(content: str) -> list[str]:
    """Split *content* into segments ≤ DXL_BUFFER_SEGMENT_BYTES bytes for iterative Buffer accumulation."""
    if not content:
        return [""]
    if len(content.encode("utf-8")) <= DXL_BUFFER_SEGMENT_BYTES:
        return [content]
    return _split_bytes(content, DXL_BUFFER_SEGMENT_BYTES)
