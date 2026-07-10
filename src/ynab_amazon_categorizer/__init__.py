"""Match Amazon orders to YNAB transactions and guide categorization."""

try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:
    # Python < 3.8
    from importlib_metadata import (  # type: ignore[no-redef]
        PackageNotFoundError,
        version,
    )

try:
    __version__ = version("ynab-amazon-categorizer")
except PackageNotFoundError:
    # Package not installed, use a default version
    __version__ = "0.0.0+unknown"

__author__ = "dizzlkheinz"
__description__ = "Match Amazon orders to YNAB transactions with rich item information"
