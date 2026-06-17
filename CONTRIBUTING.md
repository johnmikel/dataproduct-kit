# Contributing

Thanks for considering a contribution to `dataproduct-kit`.

This project is early alpha. The best contributions are small, well-tested
changes that improve local validation, standards exports, documentation, or the
SaaS churn demo.

## Local setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

## Verify before opening a pull request

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m pip check
```

## Development guidelines

- Keep v1 local-first: no cloud credentials or long-running services required.
- Prefer standards-aligned outputs over custom-only formats.
- Add tests for new validation behavior, CLI behavior, and exported wire shapes.
- Keep demo data synthetic and safe to publish.
- Avoid adding MCP, catalog sync, or warehouse integrations before their scope is
  documented in the roadmap.

## Pull requests

Please include:

- A short summary of the behavior change.
- Tests for the change.
- Any compatibility impact on manifest fields or CLI output.
- Before/after examples if README-facing behavior changes.
