# YNAB Amazon Categorizer - Development Guide

**Last Updated**: January 16, 2025  
**Target Audience**: Developers continuing the refactoring process  
**Methodology**: Test-Driven Development (TDD) with Strict Discipline

## 🎯 Development Philosophy

This project follows **strict Test-Driven Development (TDD)** methodology to ensure high code quality, comprehensive test coverage, and maintainable architecture. Every line of functionality is driven by a failing test.

### Core Principles
1. **Red-Green-Refactor**: Write failing test → Minimal implementation → Improve design
2. **Incremental Progress**: Small, verifiable changes with immediate feedback
3. **Zero Regressions**: All tests must pass at every commit
4. **Minimal Implementation**: Only write code required to make tests pass

## 🚨 TDD Guard System

### Automated Enforcement
The project uses a **TDD Guard** system that automatically:
- Blocks over-implementation (writing too much code for a failing test)
- Prevents adding multiple tests simultaneously  
- Enforces minimal implementation patterns
- Maintains strict red-green-refactor cycle

### Example Enforcement
```python
# ❌ BLOCKED: Over-implementation
def new_function():
    # 50 lines of complex logic without failing test
    
# ✅ ALLOWED: Minimal implementation  
def new_function():
    pass  # Just enough to make test pass
```

## 🛠️ Development Environment Setup

### Prerequisites
- Python 3.7+
- [uv](https://docs.astral.sh/uv/) (recommended for dependency management)
- Git for version control

### Installation
```bash
# Clone repository
git clone https://github.com/dizzlkheinz/ynab-amazon-categorizer.git
cd ynab-amazon-categorizer

# Install with development dependencies
uv pip install -e ".[dev]"

# Verify installation
python -X utf8 -m pytest tests/ -v
```

### Development Dependencies
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",           # Testing framework
    "pytest-cov>=4.0.0",      # Coverage reporting
    "black>=22.0.0",           # Code formatting
    "ruff>=0.1.0",             # Linting and formatting
    "mypy>=1.0.0",             # Static type checking
    "pre-commit>=3.0.0",       # Git hooks for quality
]
```

## 🧪 TDD Development Workflow

### Step-by-Step TDD Process

#### 1. RED: Write a Failing Test
```bash
# Create a new test that fails
def test_new_functionality():
    """Test description of expected behavior."""
    # Arrange: Set up test data
    client = MyClass()
    
    # Act: Call the method that doesn't exist yet
    result = client.new_method("test_input")
    
    # Assert: Verify expected behavior
    assert result == "expected_output"

# Run test to see failure
python -X utf8 -m pytest tests/test_my_module.py::test_new_functionality -v
```

#### 2. GREEN: Minimal Implementation
```python
# Add minimal code to make test pass
class MyClass:
    def new_method(self, input_data):
        return "expected_output"  # Hardcoded to pass test

# Run test to see it pass
python -X utf8 -m pytest tests/test_my_module.py::test_new_functionality -v
```

#### 3. REFACTOR: Improve Design
```python
# Improve implementation while keeping test green
class MyClass:
    def new_method(self, input_data):
        # Better implementation that still passes test
        return self._process_input(input_data)
    
    def _process_input(self, data):
        return "expected_output"

# Run test again to ensure it still passes
python -X utf8 -m pytest tests/test_my_module.py::test_new_functionality -v
```

#### 4. REPEAT: Add More Tests
```python
# Add another test for different behavior
def test_new_functionality_edge_case():
    """Test edge case handling."""
    client = MyClass()
    result = client.new_method("")
    assert result == "default_value"
```

### TDD Anti-Patterns to Avoid

#### ❌ Writing Multiple Tests at Once
```python
# DON'T DO THIS - TDD Guard will block
def test_feature_a(): ...
def test_feature_b(): ...
def test_feature_c(): ...
```

#### ❌ Over-Implementation
```python  
# DON'T DO THIS - Too much logic for one failing test
def new_method(self, data):
    if not data:
        return "default"
    processed = self._validate_input(data)
    result = self._complex_processing(processed)
    return self._format_output(result)
```

#### ❌ Skipping Red Phase
```python
# DON'T DO THIS - Implementation before test
def new_method(self):
    return "result"
    
# Test written after implementation
def test_new_method():
    assert obj.new_method() == "result"
```

## 🔧 Essential Development Commands

### Testing Commands
```bash
# Run all tests with UTF-8 support (required on Windows)
python -X utf8 -m pytest tests/ -v

# Run specific test file
python -X utf8 -m pytest tests/test_ynab_client.py -v

# Run specific test
python -X utf8 -m pytest tests/test_ynab_client.py::test_get_data_success -v

# Run tests with coverage report
python -X utf8 -m pytest tests/ --cov=src --cov-report=html

# View coverage report
# Open htmlcov/index.html in browser
```

### Type Checking
```bash
# Run type checker (using global configuration)
uvx ty check --python "C:\Program Files\Python313\python.exe" --extra-search-path "c:\Program Files\Python313\Scripts" --extra-search-path "C:\Users\ksutk\AppData\Roaming\Python\Python313\site-packages"
```

### Code Quality
```bash
# Format code
uvx black src/ tests/

# Check and fix linting issues
uvx ruff check src/ tests/ --fix

# Install pre-commit hooks (when ready)
uvx pre-commit install
```

### Running the Tool
```bash
# Run as module (development)
python -X utf8 -m ynab_amazon_categorizer

# Run with uvx (production-like)
uvx ynab-amazon-categorizer
```

## 📝 Test Writing Guidelines

### Test Structure: Arrange-Act-Assert
```python
def test_function_behavior():
    """Clear description of what this test verifies."""
    # Arrange: Set up test data and conditions
    client = YNABClient("test_key", "test_budget")
    expected_result = {"test": "data"}
    
    # Act: Call the function being tested
    result = client.get_data("/test/endpoint")
    
    # Assert: Verify the expected behavior
    assert result == expected_result
```

### Mock External Dependencies
```python
from unittest.mock import Mock, patch

@patch('ynab_amazon_categorizer.ynab_client.requests.get')
def test_api_call_success(mock_get):
    """Test successful API call handling."""
    # Arrange: Mock the external dependency
    mock_response = Mock()
    mock_response.json.return_value = {"data": {"test": "data"}}
    mock_get.return_value = mock_response
    
    client = YNABClient("key", "budget")
    
    # Act: Call method that uses external dependency
    result = client.get_data("/endpoint")
    
    # Assert: Verify behavior and mock interactions
    assert result == {"test": "data"}
    mock_get.assert_called_once_with(
        "https://api.ynab.com/v1/endpoint",
        headers={"Authorization": "Bearer key"}
    )
```

### Test Naming Conventions
- `test_function_name_expected_behavior()`
- `test_function_name_error_condition()`  
- `test_function_name_edge_case()`

Examples:
- `test_get_data_success()`
- `test_get_data_request_error()`
- `test_parse_orders_empty_input()`

## 🏗️ Module Development Pattern

### 1. Create Module Structure
```python
# src/ynab_amazon_categorizer/new_module.py
"""Brief description of module purpose."""

class NewModule:
    """Main class for the module."""
    
    def __init__(self, required_param: str) -> None:
        self.param = required_param
    
    # Methods will be added via TDD
```

### 2. Create Test File
```python
# tests/test_new_module.py
"""Tests for new module functionality."""

from ynab_amazon_categorizer.new_module import NewModule

def test_new_module_initialization():
    """Test module can be initialized with required parameters."""
    module = NewModule("test_param")
    assert module.param == "test_param"
```

### 3. Follow TDD Cycle for Each Method
1. Write failing test for new method
2. Add minimal method stub
3. Run test to see specific failure
4. Implement minimal code to pass
5. Refactor if needed
6. Repeat for next functionality

## 📊 Current Codebase Navigation

### Module Responsibilities
```python
# Configuration management
from ynab_amazon_categorizer.config import Config

# YNAB API interactions  
from ynab_amazon_categorizer.ynab_client import YNABClient

# Amazon order parsing
from ynab_amazon_categorizer.amazon_parser import AmazonParser

# Custom exceptions
from ynab_amazon_categorizer.exceptions import ConfigurationError
```

### Test Organization
```
tests/
├── test_config.py           # Config validation (2 tests)
├── test_ynab_client.py      # YNAB API client (6 tests)  
├── test_amazon_parser.py    # Basic parsing (3 tests)
└── test_amazon_parser_real.py # Real data parsing (2 tests)
```

### Legacy Code Locations
```python
# cli.py - Functions ready for extraction:
# Lines 150-200: Transaction matching logic
# Lines 25-81: Memo generation functions  
# Lines 370-430: Interactive CLI components
```

## 🎯 Next Development Tasks

### Immediate Priority: Transaction Matching
```python
# Target extraction from cli.py
def find_matching_order(transaction_amount, transaction_date, parsed_orders):
    # Date proximity matching
    # Amount tolerance handling  
    # Multiple match resolution
```

**TDD Approach**:
1. Write test for exact amount/date match
2. Implement minimal matching logic
3. Add test for amount tolerance
4. Enhance matching with tolerance
5. Add test for date proximity
6. Implement date range matching
7. Continue incrementally

### Development Sequence
1. **Create `transaction_matcher.py`** with basic structure
2. **Add test file** `test_transaction_matcher.py`
3. **Extract matching logic** following TDD cycle
4. **Integrate with existing modules**
5. **Update CLI to use new matcher**

## 🚀 Contributing Guidelines

### Code Standards
- ✅ **Type hints required** for all new code
- ✅ **Docstrings required** for all public methods
- ✅ **Error handling** must be comprehensive  
- ✅ **Tests required** before implementation

### Commit Standards
```bash
# Good commit messages
git commit -m "Add failing test for transaction matching by amount"
git commit -m "Implement minimal amount matching to pass test"  
git commit -m "Refactor matching logic for better readability"

# Bad commit messages  
git commit -m "WIP"
git commit -m "Fix stuff"
git commit -m "Add transaction matching feature"
```

### Pull Request Process
1. **All tests must pass**: `python -X utf8 -m pytest tests/ -v`
2. **Type checking clean**: Run type checker
3. **Code formatted**: `uvx black src/ tests/`
4. **Linting clean**: `uvx ruff check src/ tests/`
5. **Documentation updated**: Update relevant .md files

## 🔍 Debugging and Troubleshooting  

### Common Issues

#### Tests Not Running
```bash
# Ensure UTF-8 encoding on Windows
python -X utf8 -m pytest tests/ -v

# Check module installation
pip list | grep ynab-amazon-categorizer
```

#### Import Errors
```bash
# Reinstall in development mode
uv pip install -e ".[dev]"

# Check Python path
python -c "import sys; print(sys.path)"
```

#### TDD Guard Violations
- **Over-implementation**: Write less code, just enough to pass test
- **Multiple tests**: Add one test at a time
- **Missing tests**: Write failing test before implementation

### Performance Monitoring
```bash
# Profile test execution
python -X utf8 -m pytest tests/ -v --durations=10

# Memory usage during tests
python -X utf8 -m pytest tests/ -v --memmon
```

## 📚 Learning Resources

### TDD Resources
- [Test Driven Development: By Example](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530) by Kent Beck
- [Growing Object-Oriented Software, Guided by Tests](https://www.amazon.com/Growing-Object-Oriented-Software-Guided-Tests/dp/0321503627)

### Python Testing
- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)

### Code Quality
- [PEP 8 Style Guide](https://pep8.org/)
- [Type Hints (PEP 484)](https://pep.python.org/pep-0484/)

---

*Following these development practices ensures high code quality, comprehensive test coverage, and maintainable architecture throughout the refactoring process.*