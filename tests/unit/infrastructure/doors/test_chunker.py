"""Unit tests for the DXL payload chunker."""
from __future__ import annotations

import pytest

from doors_excel.infrastructure.doors.chunker import (
    DXL_BUFFER_SEGMENT_BYTES,
    DXL_CHUNK_BYTES,
    buffer_segments,
    chunk_dxl,
)


class TestChunkDxl:
    def test_small_payload_returns_single_chunk(self) -> None:
        payload = "x" * 100
        chunks = chunk_dxl(payload)
        assert chunks == [payload]

    def test_exact_boundary_is_one_chunk(self) -> None:
        payload = "x" * DXL_CHUNK_BYTES
        chunks = chunk_dxl(payload)
        assert len(chunks) == 1
        assert chunks[0] == payload

    def test_oversized_payload_splits(self) -> None:
        payload = "x" * (DXL_CHUNK_BYTES + 1)
        chunks = chunk_dxl(payload)
        assert len(chunks) == 2
        assert len(chunks[0]) == DXL_CHUNK_BYTES
        assert chunks[1] == "x"

    def test_all_chunks_within_limit(self) -> None:
        payload = "y" * (DXL_CHUNK_BYTES * 3 + 500)
        for chunk in chunk_dxl(payload):
            assert len(chunk.encode()) <= DXL_CHUNK_BYTES

    def test_empty_payload_returns_one_empty_chunk(self) -> None:
        assert chunk_dxl("") == [""]

    def test_unicode_chars_respect_byte_limit(self) -> None:
        # Each '€' is 3 bytes in UTF-8; ensure byte-aware splitting
        payload = "€" * (DXL_CHUNK_BYTES // 3 + 10)
        for chunk in chunk_dxl(payload):
            assert len(chunk.encode("utf-8")) <= DXL_CHUNK_BYTES

    def test_reassembly_equals_original(self) -> None:
        payload = "abc" * 20_000
        assert "".join(chunk_dxl(payload)) == payload


class TestBufferSegments:
    def test_small_content_single_segment(self) -> None:
        content = "hello world"
        segs = buffer_segments(content)
        assert segs == [content]

    def test_large_content_splits_at_segment_size(self) -> None:
        content = "z" * (DXL_BUFFER_SEGMENT_BYTES * 2 + 100)
        segs = buffer_segments(content)
        assert len(segs) == 3
        assert len(segs[0].encode()) <= DXL_BUFFER_SEGMENT_BYTES
        assert len(segs[1].encode()) <= DXL_BUFFER_SEGMENT_BYTES

    def test_reassembly_equals_original(self) -> None:
        content = "seg" * 15_000
        assert "".join(buffer_segments(content)) == content
