"""Configuration management."""

import os
from pathlib import Path

from .exceptions import ConfigurationError

try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


class Config:
    """Configuration class for YNAB Amazon Categorizer."""

    def __init__(
        self,
        api_key: str,
        budget_id: str,
        account_id: str | None = None,
        amazon_domain: str = "amazon.ca",
    ):
        self.api_key = api_key
        self.budget_id = budget_id
        self.account_id = account_id
        self.amazon_domain = amazon_domain

    @classmethod
    def from_env(cls) -> "Config":
        # Load .env file if available — only search up to 5 parent levels
        if DOTENV_AVAILABLE:
            env_path = Path.cwd()
            for _ in range(5):
                env_file = env_path / ".env"
                if env_file.exists():
                    load_dotenv(env_file)
                    break
                parent = env_path.parent
                if parent == env_path:
                    break
                env_path = parent

        api_key = os.getenv("YNAB_API_KEY")
        budget_id = os.getenv("YNAB_BUDGET_ID")

        raw_account_id = os.getenv("YNAB_ACCOUNT_ID", "").strip()
        account_id: str | None = (
            raw_account_id if raw_account_id.lower() not in ("", "none") else None
        )

        amazon_domain = os.getenv("AMAZON_DOMAIN", "amazon.ca")

        if not api_key:
            raise ConfigurationError("YNAB_API_KEY environment variable is required")
        if not budget_id:
            raise ConfigurationError("YNAB_BUDGET_ID environment variable is required")

        return cls(api_key, budget_id, account_id, amazon_domain)
