# doors-excel-tool

Bidirectional IBM DOORS ↔ Microsoft Excel synchronisation tool.

## Quick Start

```bash
poetry install
poetry run doors-excel --help
```

## Development

```bash
poetry run pytest          # tests
poetry run ruff check src/ # lint
poetry run ruff format src/ # format
poetry run mypy src/       # type-check
```

## Documentation

See `docs/` for full requirements, architecture, and UI specification.
