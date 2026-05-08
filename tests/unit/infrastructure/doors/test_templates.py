"""Unit tests for the Jinja2 DXL template renderer."""
from __future__ import annotations

import pytest

from doors_excel.infrastructure.doors.templates import dxl_value, get_jinja_env, render_template


class TestDxlValueFilter:
    def test_plain_string_unchanged(self) -> None:
        assert dxl_value("hello") == "hello"

    def test_backslash_escaped(self) -> None:
        assert dxl_value("path\\to\\file") == "path\\\\to\\\\file"

    def test_double_quote_escaped(self) -> None:
        assert dxl_value('say "hi"') == 'say \\"hi\\"'

    def test_newline_escaped(self) -> None:
        assert dxl_value("line1\nline2") == "line1\\nline2"

    def test_carriage_return_escaped(self) -> None:
        assert dxl_value("line1\rline2") == "line1\\rline2"

    def test_combined_special_chars(self) -> None:
        raw = 'C:\\dir\\"file"\n'
        result = dxl_value(raw)
        assert "\\\\" in result
        assert '\\"' in result
        assert "\\n" in result

    def test_non_string_coerced(self) -> None:
        assert dxl_value(42) == "42"  # type: ignore[arg-type]

    def test_empty_string(self) -> None:
        assert dxl_value("") == ""


class TestGetJinjaEnv:
    def test_returns_environment(self) -> None:
        from jinja2 import Environment
        env = get_jinja_env()
        assert isinstance(env, Environment)

    def test_dxl_value_filter_registered(self) -> None:
        env = get_jinja_env()
        assert "dxl_value" in env.filters

    def test_autoescape_disabled(self) -> None:
        env = get_jinja_env()
        assert not env.autoescape  # type: ignore[truthy-bool]

    def test_same_instance_returned(self) -> None:
        assert get_jinja_env() is get_jinja_env()


class TestRenderTemplate:
    def test_render_inline_string(self) -> None:
        env = get_jinja_env()
        tmpl = env.from_string("Hello {{ name | dxl_value }}!")
        result = tmpl.render(name="World")
        assert result == "Hello World!"

    def test_render_escapes_via_filter(self) -> None:
        env = get_jinja_env()
        tmpl = env.from_string('value = "{{ val | dxl_value }}"')
        result = tmpl.render(val='He said "hi"')
        assert result == 'value = "He said \\"hi\\""'

    def test_render_template_by_name(self) -> None:
        result = render_template("ping.dxl.j2")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_template_unknown_raises(self) -> None:
        from jinja2 import TemplateNotFound
        with pytest.raises(TemplateNotFound):
            render_template("nonexistent_template.dxl.j2")


class TestExportModuleTemplate:
    def test_renders_without_error(self) -> None:
        rendered = render_template(
            "export_module.dxl.j2",
            module_path="/proj/mod",
            attributes=["Object Text", "Short Name"],
        )
        assert isinstance(rendered, str)
        assert len(rendered) > 0

    def test_module_path_is_escaped(self) -> None:
        rendered = render_template(
            "export_module.dxl.j2",
            module_path='/proj/"evil"\\mod',
            attributes=["Object Text"],
        )
        assert '\\"evil\\"' in rendered
        assert "\\\\mod" in rendered

    def test_attribute_names_appear_in_output(self) -> None:
        rendered = render_template(
            "export_module.dxl.j2",
            module_path="/proj/mod",
            attributes=["Object Text", "Short Name"],
        )
        assert "Object Text" in rendered
        assert "Short Name" in rendered

    def test_two_attributes_each_have_richtext_block(self) -> None:
        rendered = render_template(
            "export_module.dxl.j2",
            module_path="/proj/mod",
            attributes=["Object Text", "Short Name"],
        )
        assert rendered.count("richText") == 2

    def test_field_and_record_sep_constants_present(self) -> None:
        rendered = render_template(
            "export_module.dxl.j2",
            module_path="/proj/mod",
            attributes=["Object Text"],
        )
        assert "\\x1f" in rendered or "\x1f" in rendered
        assert "\\x1e" in rendered or "\x1e" in rendered

    def test_empty_attribute_list_still_renders(self) -> None:
        rendered = render_template(
            "export_module.dxl.j2",
            module_path="/proj/mod",
            attributes=[],
        )
        assert "Module m" in rendered
