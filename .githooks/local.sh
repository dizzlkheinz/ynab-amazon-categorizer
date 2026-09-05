# Project-specific pre-commit checks for ynab-amazon-categorizer.
run "pytest with coverage"
uv run python -X utf8 -m pytest tests/ -v --cov=src --cov-report=term-missing
