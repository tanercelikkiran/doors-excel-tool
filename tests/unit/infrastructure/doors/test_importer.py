"""Tests for DoorsImporter — all DXL execution is mocked."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestDoorsImporter:
    def test_empty_updates_does_not_call_run_dxl(self) -> None:
        from doors_excel.infrastructure.doors.importer import DoorsImporter

        mock_conn = MagicMock()
        importer = DoorsImporter(mock_conn)
        importer.apply_updates("/proj/mod", [])
        mock_conn.run_dxl.assert_not_called()

    def test_single_update_calls_run_dxl_once(self) -> None:
        from doors_excel.infrastructure.doors.importer import DoorsImporter

        mock_conn = MagicMock()
        importer = DoorsImporter(mock_conn)
        importer.apply_updates(
            "/proj/mod",
            [{"object_id": 1, "attribute": "Object Text", "value": "hello"}],
        )
        mock_conn.run_dxl.assert_called_once()

    def test_dxl_script_contains_object_id(self) -> None:
        from doors_excel.infrastructure.doors.importer import DoorsImporter

        mock_conn = MagicMock()
        importer = DoorsImporter(mock_conn)
        importer.apply_updates(
            "/proj/mod",
            [{"object_id": 42, "attribute": "Object Text", "value": "val"}],
        )
        script_sent = mock_conn.run_dxl.call_args[0][0]
        assert "42" in script_sent

    def test_large_update_chunks_into_multiple_calls(self) -> None:
        from doors_excel.infrastructure.doors.importer import DoorsImporter

        mock_conn = MagicMock()
        importer = DoorsImporter(mock_conn)

        with patch("doors_excel.infrastructure.doors.importer.chunk_dxl", return_value=["chunk1", "chunk2"]):
            importer.apply_updates(
                "/proj/mod",
                [{"object_id": 1, "attribute": "Object Text", "value": "x"}],
            )
        assert mock_conn.run_dxl.call_count == 2

    def test_multiple_updates_all_rendered(self) -> None:
        from doors_excel.infrastructure.doors.importer import DoorsImporter

        mock_conn = MagicMock()
        importer = DoorsImporter(mock_conn)
        importer.apply_updates(
            "/proj/mod",
            [
                {"object_id": 1, "attribute": "Object Text", "value": "a"},
                {"object_id": 2, "attribute": "Short Name", "value": "b"},
            ],
        )
        script_sent = mock_conn.run_dxl.call_args[0][0]
        assert "1" in script_sent
        assert "2" in script_sent


def test_move_objects_calls_run_dxl(tmp_path):
    """move_objects must render a DXL script and call conn.run_dxl."""
    from unittest.mock import MagicMock, patch
    from doors_excel.infrastructure.doors.importer import DoorsImporter

    mock_conn = MagicMock()
    importer = DoorsImporter(mock_conn)

    moves = [{"object_id": 10, "new_parent_id": 5, "placement": "below"}]
    with patch("doors_excel.infrastructure.doors.importer.render_template", return_value="DXL") as mock_render, \
         patch("doors_excel.infrastructure.doors.importer.chunk_dxl", return_value=["DXL"]):
        importer.move_objects("/proj/mod", moves)

    mock_render.assert_called_once_with(
        "move_objects.dxl.j2",
        module_path="/proj/mod",
        moves=moves,
    )
    mock_conn.run_dxl.assert_called_once_with("DXL")
