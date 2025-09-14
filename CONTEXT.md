# Development Context & Continuation Guide

This document provides essential context for continuing development after context is cleared.

## Project State Summary

**YNAB Amazon Categorizer** has been successfully refactored from a monolithic 1500-line script to a modern, well-tested Python package. The project automatically categorizes Amazon transactions in YNAB with rich item information.

### Current Progress: 95% Complete - MAJOR REFACTORING COMPLETED

- ✅ **Foundation**: Modular architecture, TDD setup, 21 passing tests (300% increase)
- ✅ **YNAB API Client**: Complete extraction with 6 tests, full error handling
- ✅ **Amazon Parser**: Enhanced with item extraction, 5 tests covering real scenarios  
- ✅ **Configuration**: Production-ready environment management with validation
- ✅ **Transaction Matching**: Complete with 4 tests, amount matching algorithms extracted
- ✅ **Memo Generation**: Complete with 4 tests, order link generation and enhanced memos
- ✅ **CLI Refactoring**: Completed as thin orchestration layer (909 lines, 40% reduction)

## Critical Implementation Details

### TDD Guard Active
- **Command**: `tdd-guard on` is enabled
- **Behavior**: Automatically runs tests when files change
- **Requirement**: All new functionality MUST be test-driven

### Core Architecture Pattern

```python
# ALWAYS follow this pattern for new modules:

# 1. Write failing test first
def test_new_functionality():
    """Test description."""
    # Test implementation that will fail
    pass

# 2. Create minimal implementation to pass
class NewModule:
    def new_method(self):
        pass  # Minimal stub

# 3. Iterate with more tests and implementation
```

### Key Files Completed

1. **`cli.py` (REFACTORED - 909 lines)**: Successfully converted to thin orchestration layer
2. **`amazon_parser.py`**: Complete with regex-based order parsing and item extraction
3. **`config.py`**: Complete environment-based configuration with validation
4. **`ynab_client.py`**: Complete API client with comprehensive error handling
5. **`transaction_matcher.py`**: Complete matching algorithms with tolerance handling
6. **`memo_generator.py`**: Complete memo generation with order links
7. **`tests/`**: 21 comprehensive tests covering all functionality

### All Major Extractions Completed

**Successfully extracted from legacy `cli.py`:**

1. **YNAB API Client** (`ynab_client.py`):
   ```python
   def get_data(endpoint)           # Generic API fetching
   def update_transaction(...)      # Transaction updates
   def get_categories()             # Category management
   ```

2. **Transaction Matching** (`transaction_matcher.py`):
   ```python
   def find_matching_order(amount, date, parsed_orders)  # With tolerance algorithms
   ```

3. **Memo Generation** (`memo_generator.py`):
   ```python
   def generate_amazon_order_link(order_id)    # Amazon.ca order links
   def generate_enhanced_memo(...)             # Rich memo creation
   ```

## Development Workflow

### Setup Commands
```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run tests (ALWAYS use UTF-8 on Windows)
python -X utf8 -m pytest tests/ -v

# Type checking (using global config)
uvx ty check --python "C:\Program Files\Python313\python.exe" --extra-search-path "c:\Program Files\Python313\Scripts" --extra-search-path "C:\Users\ksutk\AppData\Roaming\Python\Python313\site-packages"
```

### TDD Process Example
```bash
# 1. Write failing test
# 2. Run test to see failure
python -X utf8 -m pytest tests/test_new_module.py::test_new_function -v

# 3. Implement minimal code to pass
# 4. Run test to see it pass
python -X utf8 -m pytest tests/test_new_module.py::test_new_function -v

# 5. Refactor and repeat
```

## Hook System Notes

**TDD Guard Hook**: Blocks premature implementation
- Will reject adding complex functionality without failing tests first
- Forces minimal implementation approach
- Maintains strict TDD discipline

**Example of Blocked Operation**:
```python
# ❌ This will be blocked:
def complex_function():
    # 50 lines of implementation without tests
    
# ✅ This is allowed:
def complex_function():
    pass  # Minimal stub to make test pass
```

## Current Test Coverage

**21 passing tests across 6 modules (300% increase from baseline):**
- `test_amazon_parser.py`: 3 tests (basic parsing, empty input, item extraction)
- `test_amazon_parser_real.py`: 2 tests (real order formats)
- `test_config.py`: 2 tests (env vars, error handling)  
- `test_ynab_client.py`: 6 tests (initialization, API calls, error handling)
- `test_transaction_matcher.py`: 4 tests (matching algorithms, tolerance handling)
- `test_memo_generator.py`: 4 tests (link generation, enhanced memos, edge cases)

## Package Structure

```
src/ynab_amazon_categorizer/
├── __init__.py              # ✅ Version handling
├── __main__.py              # ✅ Entry point
├── cli.py                   # ✅ REFACTORED: Orchestration layer (909 lines)
├── amazon_parser.py         # ✅ Complete with item extraction (5 tests)
├── config.py                # ✅ Complete with validation (2 tests)
├── ynab_client.py           # ✅ Complete API client (6 tests)
├── transaction_matcher.py   # ✅ Complete matching algorithms (4 tests)
├── memo_generator.py        # ✅ Complete memo generation (4 tests)
└── exceptions.py            # ✅ Complete error handling

tests/                       # ✅ 21 passing tests
├── test_amazon_parser.py
├── test_amazon_parser_real.py
├── test_config.py
├── test_ynab_client.py
├── test_transaction_matcher.py
└── test_memo_generator.py

pyproject.toml              # ✅ Complete with dev deps
.pre-commit-config.yaml     # ✅ Ready for use
TODO.md                     # 📋 Detailed task list
CONTEXT.md                  # 📖 This file
CLAUDE.md                   # 📖 Claude Code instructions
```

## Environment Setup

**Required Environment Variables** (for real usage):
```bash
YNAB_API_KEY=your_api_key_here
YNAB_BUDGET_ID=your_budget_id_here
YNAB_ACCOUNT_ID=none  # Optional
```

**Development Dependencies** (already configured):
- pytest, pytest-cov (testing)
- black, ruff (formatting/linting)
- mypy (type checking)
- pre-commit (git hooks)

## Continuation Strategy

### Phase 1: Core Refactoring ✅ COMPLETED
1. ✅ Extract YNAB API client with tests (6 tests)
2. ✅ Complete Amazon parser with item extraction (5 tests)
3. ✅ Extract transaction matching logic (4 tests)
4. ✅ Extract memo generation functionality (4 tests)

### Phase 2: CLI Refactoring ✅ COMPLETED  
1. ✅ Make `cli.py` a thin orchestration layer (909 lines, 40% reduction)
2. ✅ Move interactive components to separate modules
3. ✅ Maintain existing user interface completely

### Phase 3: Infrastructure & Enhanced Features (Next Steps)
1. ⏳ Setup CI/CD Pipeline - GitHub Actions for automated testing
2. Multi-domain Amazon support (.com, .uk, .ca)
3. Batch processing capabilities
4. ML-based categorization suggestions

## Testing Philosophy

**Strict TDD** - Never write implementation without a failing test:
1. Red: Write failing test
2. Green: Minimal implementation to pass
3. Refactor: Improve while keeping tests green
4. Repeat in small increments

This disciplined approach has been maintained throughout the refactoring and is critical for continued success.

## Quick Start for Continuation

```bash
# 1. Navigate to project
cd C:\Users\ksutk\projects\ynab-amazon-categorizer

# 2. Activate TDD guard
# (Type: tdd-guard on)

# 3. Check current status
python -X utf8 -m pytest tests/ -v

# 4. Start with next extraction task
# (See TODO.md for specific next steps)
```

The project is well-positioned for continued development with a solid foundation, comprehensive testing, and clear next steps documented.