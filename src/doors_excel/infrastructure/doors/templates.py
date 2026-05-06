"""Jinja2 environment and DXL template renderer."""
from __future__ import annotations

from functools import lru_cache
from importlib.resources import files

from jinja2 import Environment, FileSystemLoader


def dxl_value(value: object) -> str:
    """Escape *value* for safe embedding inside a DXL double-quoted string.

    Escapes: backslash → \\\\, double-quote → \\", newline → \\n, CR → \\r.
    """
    text = str(value)
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    text = text.replace("\n", "\\n")
    text = text.replace("\r", "\\r")
    return text


@lru_cache(maxsize=1)
def get_jinja_env() -> Environment:
    """Return the shared Jinja2 environment configured for DXL templates."""
    resource_path = files("doors_excel.resources").joinpath("dxl")
    env = Environment(
        loader=FileSystemLoader(str(resource_path)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    env.filters["dxl_value"] = dxl_value
    return env


def render_template(template_name: str, **context: object) -> str:
    """Load *template_name* from the DXL resources directory and render it."""
    return get_jinja_env().get_template(template_name).render(**context)
