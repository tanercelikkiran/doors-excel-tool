"""Tests for update_module.dxl.j2 template rendering."""
from __future__ import annotations

import pytest
from doors_excel.infrastructure.doors.templates import render_template


class TestUpdateModuleTemplate:
    def test_renders_without_error(self) -> None:
        script = render_template(
            "update_module.dxl.j2",
            module_path="/proj/mod",
            updates=[{"object_id": 1, "attribute": "Object Text", "value": "hello"}],
        )
        assert isinstance(script, str)
        assert len(script) > 0

    def test_contains_module_path(self) -> None:
        script = render_template(
            "update_module.dxl.j2",
            module_path="/proj/mod",
            updates=[],
        )
        assert "/proj/mod" in script

    def test_contains_object_id_for_each_update(self) -> None:
        script = render_template(
            "update_module.dxl.j2",
            module_path="/proj/mod",
            updates=[
                {"object_id": 42, "attribute": "Object Text", "value": "a"},
                {"object_id": 99, "attribute": "Short Name", "value": "b"},
            ],
        )
        assert "42" in script
        assert "99" in script

    def test_dxl_injection_escaped_in_value(self) -> None:
        script = render_template(
            "update_module.dxl.j2",
            module_path="/proj/mod",
            updates=[{"object_id": 1, "attribute": "Object Text", "value": 'say "hello"'}],
        )
        # Raw double-quote must not appear in value; dxl_value escapes it
        assert '"hello"' not in script
        assert '\\"hello\\"' in script

    def test_dxl_injection_escaped_in_attribute(self) -> None:
        script = render_template(
            "update_module.dxl.j2",
            module_path="/proj/mod",
            updates=[{"object_id": 1, "attribute": 'attr"name', "value": "x"}],
        )
        assert 'attr\\"name' in script

    def test_empty_updates_renders_valid_script(self) -> None:
        script = render_template(
            "update_module.dxl.j2",
            module_path="/proj/mod",
            updates=[],
        )
        assert "edit" in script
        assert "save" in script
