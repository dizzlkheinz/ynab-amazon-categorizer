"""Tests for configuration management."""

import pytest

import ynab_amazon_categorizer.config as config_module
from ynab_amazon_categorizer.config import Config


def test_config_from_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading config from environment variables."""
    monkeypatch.setattr(config_module, "DOTENV_AVAILABLE", False)
    monkeypatch.delenv("YNAB_ACCOUNT_ID", raising=False)
    monkeypatch.setenv("YNAB_API_KEY", "test_api_key")
    monkeypatch.setenv("YNAB_BUDGET_ID", "test_budget_id")

    config = Config.from_env()
    assert config.api_key == "test_api_key"
    assert config.budget_id == "test_budget_id"
    assert config.account_id == "none"  # Should default to "none"


def test_config_missing_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test config raises error when required env vars are missing."""
    monkeypatch.setattr(config_module, "DOTENV_AVAILABLE", False)
    monkeypatch.delenv("YNAB_API_KEY", raising=False)
    monkeypatch.delenv("YNAB_BUDGET_ID", raising=False)
    monkeypatch.delenv("YNAB_ACCOUNT_ID", raising=False)

    from ynab_amazon_categorizer.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError):
        Config.from_env()


def test_config_amazon_domain_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test AMAZON_DOMAIN environment variable override."""
    monkeypatch.setattr(config_module, "DOTENV_AVAILABLE", False)
    monkeypatch.setenv("YNAB_API_KEY", "key")
    monkeypatch.setenv("YNAB_BUDGET_ID", "budget")
    monkeypatch.setenv("AMAZON_DOMAIN", "amazon.com")
    monkeypatch.delenv("YNAB_ACCOUNT_ID", raising=False)

    config = Config.from_env()
    assert config.amazon_domain == "amazon.com"


def test_config_amazon_domain_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test AMAZON_DOMAIN defaults to amazon.ca."""
    monkeypatch.setattr(config_module, "DOTENV_AVAILABLE", False)
    monkeypatch.setenv("YNAB_API_KEY", "key")
    monkeypatch.setenv("YNAB_BUDGET_ID", "budget")
    monkeypatch.delenv("AMAZON_DOMAIN", raising=False)
    monkeypatch.delenv("YNAB_ACCOUNT_ID", raising=False)

    config = Config.from_env()
    assert config.amazon_domain == "amazon.ca"


def test_config_default_account_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test default account_id is 'none' when not set."""
    monkeypatch.setattr(config_module, "DOTENV_AVAILABLE", False)
    monkeypatch.setenv("YNAB_API_KEY", "key")
    monkeypatch.setenv("YNAB_BUDGET_ID", "budget")
    monkeypatch.delenv("YNAB_ACCOUNT_ID", raising=False)

    config = Config.from_env()
    assert config.account_id == "none"


def test_config_explicit_account_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test explicit account_id is preserved."""
    monkeypatch.setattr(config_module, "DOTENV_AVAILABLE", False)
    monkeypatch.setenv("YNAB_API_KEY", "key")
    monkeypatch.setenv("YNAB_BUDGET_ID", "budget")
    monkeypatch.setenv("YNAB_ACCOUNT_ID", "my-account-123")

    config = Config.from_env()
    assert config.account_id == "my-account-123"
