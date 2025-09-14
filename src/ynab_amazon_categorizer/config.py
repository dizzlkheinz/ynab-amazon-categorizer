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

    def __init__(self, api_key: str, budget_id: str, account_id: str = None):
        self.api_key = api_key
        self.budget_id = budget_id
        self.account_id = account_id

    @classmethod
    def from_env(cls):
        # Load .env file if available
        if DOTENV_AVAILABLE:
            # Look for .env file in current directory and parent directories
            env_path = Path.cwd()
            while env_path != env_path.parent:
                env_file = env_path / ".env"
                if env_file.exists():
                    load_dotenv(env_file)
                    break
                env_path = env_path.parent

        api_key = os.getenv("YNAB_API_KEY")
        budget_id = os.getenv("YNAB_BUDGET_ID")
        account_id = os.getenv("YNAB_ACCOUNT_ID", "none")  # Default to "none"

        if not api_key:
            raise ConfigurationError("YNAB_API_KEY environment variable is required")
        if not budget_id:
            raise ConfigurationError("YNAB_BUDGET_ID environment variable is required")

        return cls(api_key, budget_id, account_id)
