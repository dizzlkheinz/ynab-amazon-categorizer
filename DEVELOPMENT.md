# Development Guide

Practical commands and conventions for working on this repository.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync --extra dev
```

## Daily Commands

```bash
# Tests (Windows-safe UTF-8 mode)
python -X utf8 -m pytest tests/ -v

# Coverage
python -X utf8 -m pytest tests/ --cov=src --cov-report=html

# Type checking
uv run --extra dev ty check src tests

# Architecture boundary checks
uv run --extra dev tach check

# Formatting and lint
uv run --extra dev ruff format src tests
uv run --extra dev ruff check src tests --fix

# Run pre-commit checks locally
uv run --extra dev pre-commit run --all-files

# Run the CLI locally
python -X utf8 -m ynab_amazon_categorizer
```

## Development Workflow

1. Add or update tests first for the behavior you want.
2. Implement the smallest change to make tests pass.
3. Run formatting/lint/type-check before committing.
4. Keep `cli.py` orchestration-focused; prefer adding logic to focused modules.

## Testing Notes

- Use `unittest.mock` for YNAB API calls.
- Cover both success and failure paths.
- Validate parser/matcher edge cases with small targeted tests.

## Quality Bar for Commits

- Run `uv run --extra dev pre-commit run --all-files` (or commit with pre-commit installed).
- All stages pass locally:
  - Formatting & linting (`ruff`, `typos`)
  - Type checking (`ty`)
  - Architecture & drift (`tach`, `vibedrift`)
  - Security (`gitleaks`)
  - Unit tests with coverage (`pytest`)
- Any behavior change includes a test update.

## Troubleshooting

If imports fail when running tests, run:

```bash
uv sync --extra dev
uv run --extra dev python -X utf8 -m pytest tests/ -v
```
