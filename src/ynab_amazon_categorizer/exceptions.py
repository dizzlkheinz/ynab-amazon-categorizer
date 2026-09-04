"""Custom exceptions for YNAB Amazon Categorizer."""


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""


class YNABAPIError(Exception):
    """Base exception for YNAB API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class YNABAuthError(YNABAPIError):
    """Raised when YNAB API authentication fails (401/403)."""


class YNABRateLimitError(YNABAPIError):
    """Raised when YNAB API rate limit is exceeded (429)."""


class YNABNotFoundError(YNABAPIError):
    """Raised when YNAB resource is not found (404)."""


class YNABValidationError(YNABAPIError):
    """Raised when YNAB API rejects the request payload (400)."""


class YNABResponseError(YNABAPIError):
    """Raised when a successful YNAB response has invalid JSON or schema."""
