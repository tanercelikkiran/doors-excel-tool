"""Entry point for `python -m doors_excel` and the `doors-excel` console script."""
from __future__ import annotations

from doors_excel.cli.app import app
from doors_excel.common.logging import setup_logging


def main() -> None:  # pragma: no cover
    setup_logging()
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
