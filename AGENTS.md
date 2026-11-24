# AGENTS.md

Repository instructions for coding agents working on this project.

> **Project Status:** Archived / unmaintained as of the final `v2.6.0` release. Keep changes minimal, tested, and aligned with the self-contained checks below.

## Project Overview

This is a Python CLI tool that matches Amazon orders to YNAB transactions with item-level memo enrichment and guided categorization.

## Setup and Validation Commands

```bash
# Install project + development dependencies
uv sync --extra dev

# Run tests
uv run --extra dev python -X utf8 -m pytest tests/ -v

# Run tests with coverage
uv run --extra dev python -X utf8 -m pytest tests/ --cov=src --cov-report=term-missing

# Type checking (rules.all = "error" in pyproject.toml)
uv run --extra dev ty check src tests

# Architecture boundary checks (tach.toml)
uv run --extra dev tach check

# Cognitive complexity check
uv run --extra dev complexipy src tests --max-complexity-allowed 10

# Formatting / lint
uv run --extra dev ruff format src tests
uv run --extra dev ruff check src tests --fix

# Run locally
uv run python -X utf8 -m ynab_amazon_categorizer
```

## Architecture

Current modules under `src/ynab_amazon_categorizer/`:
- `__init__.py` - package version and metadata.
- `__main__.py` - module entry point (`python -m ynab_amazon_categorizer`).
- `cli.py` - main CLI entry point and interactive flow.
- `amazon_parser.py` - Amazon order parsing logic.
- `transaction_matcher.py` - amount/date matching logic.
- `memo_generator.py` - memo and order-link generation.
- `ynab_client.py` - YNAB API communication.
- `config.py` - environment config loading/validation.
- `exceptions.py` - configuration and YNAB API exception classes.
- `models.py` - typed domain and YNAB payload models.
- `payloads.py` - minimal YNAB update construction.
- `tax.py` - category-aware split sales tax calculation.
- `transactions.py` - transaction validation and Amazon-payee filtering.
- `batch.py` - non-interactive matching and memo enrichment policy.

Design principles:
- Keep modules single-purpose and composable.
- Keep `cli.py` as orchestration; move business logic into focused modules.
- Prefer typed interfaces and predictable return values for API/parsing layers.
- Add tests for behavior changes before refactoring or extending logic.

Data flow:
1. User copies Amazon orders page text.
2. Parser extracts orders and item details.
3. Tool fetches uncategorized YNAB transactions.
4. Matcher pairs orders with transactions using amount/date heuristics.
5. CLI guides category updates and split transactions.
6. Tool updates YNAB memos/categories via API.

Matching and memo behavior:
- Transaction matching prioritizes amount match with date proximity heuristics.
- Memo generation should include item context and an order link when available.
- Missing/partial order data should degrade gracefully rather than crash updates.

## Configuration Requirements

Create a `.env` with:

```env
YNAB_API_KEY=your_api_key_here
YNAB_BUDGET_ID=your_budget_id_here
YNAB_ACCOUNT_ID=none
```

Optional overrides: `AMAZON_DOMAIN`, `YNAB_DEFAULT_TAX_RATE`, `YNAB_GROCERY_TAX_RATE`, `YNAB_SKIP_SPLIT_PROMPT_SINGLE_ITEM`.

## Dependencies

- `requests` - YNAB API calls
- `prompt_toolkit` - interactive CLI UX
- `python-dotenv` - `.env` loading

## Security Notes

- Never commit real API keys or `.env` contents.
- Do not print full secrets in logs, tests, or screenshots.
- When sharing examples, use placeholder credentials.

## Agent Notes

- On Windows, prefer `python -X utf8` to avoid emoji/category encoding issues.
- Focus processing on likely Amazon payees (`amazon`, `amzn`, `amz`).
- Add or update tests when behavior changes (parser, matcher, memo generation, API payloads).
