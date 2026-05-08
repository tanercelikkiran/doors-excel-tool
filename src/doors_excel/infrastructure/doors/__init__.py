"""COM/pywin32 bridge, Jinja2 DXL template engine, keep-alive watchdog."""
from __future__ import annotations

from doors_excel.infrastructure.doors.chunker import (
    DXL_BUFFER_SEGMENT_BYTES,
    DXL_CHUNK_BYTES,
    buffer_segments,
    chunk_dxl,
)
from doors_excel.infrastructure.doors.connection import DoorsConnection
from doors_excel.infrastructure.doors.exporter import DoorsExporter
from doors_excel.infrastructure.doors.keepalive import (
    DEFAULT_INTERVAL_SECONDS,
    KeepAliveWatchdog,
)
from doors_excel.infrastructure.doors.templates import (
    dxl_value,
    get_jinja_env,
    render_template,
)

__all__ = [
    # chunker
    "DXL_CHUNK_BYTES",
    "DXL_BUFFER_SEGMENT_BYTES",
    "chunk_dxl",
    "buffer_segments",
    # templates
    "dxl_value",
    "render_template",
    "get_jinja_env",
    # connection
    "DoorsConnection",
    # exporter
    "DoorsExporter",
    # keepalive
    "KeepAliveWatchdog",
    "DEFAULT_INTERVAL_SECONDS",
]
