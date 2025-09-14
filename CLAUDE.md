# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python CLI tool that automatically categorizes Amazon transactions in YNAB (You Need A Budget) with rich item information. The tool parses Amazon order pages and matches them with YNAB transactions to provide detailed memos and smart categorization suggestions.

## Key Commands

### Development & Testing
```bash
# Install in development mode with dev dependencies
uv pip install -e ".[dev]"

# Run tests
python -X utf8 -m pytest tests/ -v

# Run tests with coverage
python -X utf8 -m pytest tests/ --cov=src --cov-report=html

# Type checking (using global instructions format)
uvx ty check --python "C:\Program Files\Python313\python.exe" --extra-search-path "c:\Program Files\Python313\Scripts" --extra-search-path "C:\Users\ksutk\AppData\Roaming\Python\Python313\site-packages"

# Code formatting
uvx black src/ tests/
uvx ruff check src/ tests/ --fix

# Run the tool locally
python -X utf8 -m ynab_amazon_categorizer

# Or run as module
python -X utf8 src/ynab_amazon_categorizer/cli.py
```

### Running the Tool
```bash
# Run with uvx (recommended for users)
uvx ynab-amazon-categorizer

# Install as tool and run
uv tool install ynab-amazon-categorizer
ynab-amazon-categorizer
```

## Architecture

### New Modular Structure (In Progress)
- **CLI Interface**: `src/ynab_amazon_categorizer/cli.py` - Main CLI entry point
- **Amazon Parser**: `src/ynab_amazon_categorizer/amazon_parser.py` - Order parsing logic 
- **YNAB Client**: `src/ynab_amazon_categorizer/ynab_client.py` - API communication
- **Configuration**: `src/ynab_amazon_categorizer/config.py` - Settings management
- **Tests**: `tests/` directory with comprehensive test coverage
- **Entry points**: `__main__.py` and console script in pyproject.toml

### Legacy Structure (Being Refactored)
- **Single-file CLI**: Main logic in `src/ynab_amazon_categorizer/cli.py` (~1500 lines)
- **Configuration**: Environment variables or `.env` file for YNAB API credentials

### Key Components in cli.py

1. **Amazon Order Parsing** (`parse_amazon_orders_page`): Extracts order information from copied Amazon order history pages using regex patterns
2. **YNAB API Integration**: Functions to fetch transactions, categories, and update transaction details
3. **Transaction Matching**: Matches Amazon orders with YNAB transactions by amount and date proximity
4. **Interactive CLI**: Uses `prompt_toolkit` for enhanced user interaction with tab completion and keyboard shortcuts
5. **Memo Generation**: Creates rich memos with item details and Amazon order links

### Data Flow
1. User copies Amazon order page content
2. Tool parses orders and fetches YNAB transactions
3. Matches orders to transactions by amount/date
4. Presents matched items for categorization
5. Suggests transaction splitting for multiple items
6. Updates YNAB with enhanced memos and categories

## Configuration Requirements

The tool requires YNAB API credentials in `.env` file:
```
YNAB_API_KEY=your_api_key_here
YNAB_BUDGET_ID=your_budget_id_here  
YNAB_ACCOUNT_ID=none  # Optional: specific account or 'none' for all
```

## Dependencies

- `requests`: YNAB API communication
- `prompt_toolkit`: Enhanced CLI with tab completion and history

## Important Notes

- Always use `python -X utf8` on Windows for proper emoji support in category names
- The tool processes uncategorized transactions with Amazon-related payee names ("amazon", "amzn", "amz")
- Transaction splitting is suggested when multiple items are found in a single order
- Generated memos include item names and direct Amazon order links for easy reference