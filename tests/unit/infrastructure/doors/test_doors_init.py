"""Smoke tests that infrastructure/doors/__init__.py re-exports the public API."""
from __future__ import annotations


class TestDoorsPackageReExports:
    def test_chunker_symbols_importable(self) -> None:
        from doors_excel.infrastructure.doors import (
            DXL_BUFFER_SEGMENT_BYTES,
            DXL_CHUNK_BYTES,
            buffer_segments,
            chunk_dxl,
        )
        assert isinstance(DXL_CHUNK_BYTES, int)
        assert isinstance(DXL_BUFFER_SEGMENT_BYTES, int)
        assert callable(chunk_dxl)
        assert callable(buffer_segments)

    def test_template_symbols_importable(self) -> None:
        from doors_excel.infrastructure.doors import (
            dxl_value,
            get_jinja_env,
            render_template,
        )
        assert callable(dxl_value)
        assert callable(render_template)
        assert callable(get_jinja_env)

    def test_connection_importable(self) -> None:
        from doors_excel.infrastructure.doors import DoorsConnection
        assert isinstance(DoorsConnection, type)

    def test_keepalive_importable(self) -> None:
        from doors_excel.infrastructure.doors import (
            DEFAULT_INTERVAL_SECONDS,
            KeepAliveWatchdog,
        )
        assert isinstance(KeepAliveWatchdog, type)
        assert isinstance(DEFAULT_INTERVAL_SECONDS, int)

    def test_dunder_all_contains_key_symbols(self) -> None:
        import doors_excel.infrastructure.doors as m
        if hasattr(m, "__all__"):
            for name in [
                "chunk_dxl", "buffer_segments",
                "dxl_value", "render_template",
                "DoorsConnection",
                "KeepAliveWatchdog",
            ]:
                assert name in m.__all__, f"{name!r} missing from __all__"
