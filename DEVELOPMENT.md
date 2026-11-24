# Development Guide

Practical commands, architecture notes, and release instructions for working on or forking this repository.

> **Note:** As of `v2.6.0`, the original author has archived this repository and stopped active development. All tooling and checks are self-contained in this repository so a fork or new maintainer can pick it up cleanly.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync --extra dev
```

## Validation Commands

```bash
# Tests and coverage (Windows-safe UTF-8 mode)
uv run --extra dev python -X utf8 -m pytest tests/ -v --cov=src --cov-report=term-missing

# Formatting and lint (Ruff ALL ruleset configured in pyproject.toml)
uv run --extra dev ruff format --check src tests
uv run --extra dev ruff check src tests

# Type checking (all rules enforced as errors in pyproject.toml)
uv run --extra dev ty check src tests

# Architecture boundary checks (configured in tach.toml)
uv run --extra dev tach check

# Cognitive complexity check
uv run --extra dev complexipy src tests --max-complexity-allowed 10

# Run the CLI locally
uv run python -X utf8 -m ynab_amazon_categorizer --help
```

## Architecture

Source modules live under `src/ynab_amazon_categorizer/`, with module dependency boundaries enforced by `tach.toml`:

- `__init__.py` — package metadata and version lookup (`importlib.metadata`)
- `__main__.py` — `python -m ynab_amazon_categorizer` entry point
- `models.py` — `Order` dataclass, YNAB `TypedDict` models, currency formatting, and transaction schema validation
- `exceptions.py` — typed configuration and YNAB API exception hierarchy
- `config.py` — `.env` (CWD-only) and environment variable loading/validation
- `tax.py` — category-aware sales tax rate calculation and env overrides
- `amazon_parser.py` — Amazon order-history text parsing, item extraction, and deduplication
- `transaction_matcher.py` — amount/date heuristics for interactive and confident batch matching
- `memo_generator.py` — memo sanitization, link generation, split summaries, and batch memo policy
- `payloads.py` — minimal YNAB update payload builders (single, memo-only, split)
- `ynab_client.py` — YNAB REST API session with retry adapter and typed error mapping
- `transactions.py` — transaction fetching, validation, and Amazon payee filtering
- `batch.py` — non-interactive memo enrichment workflow
- `cli.py` — interactive prompt flow, argument parsing, and orchestration

## Development Workflow

1. Add or update tests in `tests/` for the behavior you want.
2. Implement the change in the appropriate focused module (keep `cli.py` focused on orchestration).
3. Run the full validation suite (`ruff`, `ty`, `tach`, `complexipy`, and `pytest` with coverage >= 65%) before committing.

## Testing Notes

- Use `unittest.mock` / `monkeypatch` for YNAB API calls and `prompt_toolkit` prompts.
- Cover both success and failure paths.
- Validate parser/matcher edge cases with small targeted tests.

## Release Process

Versions are derived automatically from Git tags via `setuptools-scm` (written to `src/ynab_amazon_categorizer/_version.py` at build time).

1. Update `CHANGELOG.md` with the release notes.
2. Commit changes and verify `uv build && uvx twine check dist/*`.
3. Create and push an annotated tag matching `v*` (e.g., `git tag -a v2.6.0 -m "Release v2.6.0" && git push origin main v2.6.0`).
4. `.github/workflows/release.yml` automatically builds the package, publishes to PyPI via Trusted Publishing, and creates the GitHub Release.
