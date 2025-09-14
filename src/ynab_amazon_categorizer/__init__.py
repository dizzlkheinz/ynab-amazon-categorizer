"""YNAB Amazon Categorizer - Automatically categorize Amazon transactions in YNAB."""

try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:
    # Python < 3.8
    from importlib_metadata import PackageNotFoundError, version

try:
    __version__ = version("ynab-amazon-categorizer")
except PackageNotFoundError:
    # Package not installed, use a default version
    __version__ = "0.0.0+unknown"

__author__ = "dizzlkheinz"
__description__ = (
    "Automatically categorize Amazon transactions in YNAB with rich item information"
)
