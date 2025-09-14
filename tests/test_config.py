"""Tests for configuration management."""

from ynab_amazon_categorizer.config import Config


def test_config_from_env_vars(monkeypatch):
    """Test loading config from environment variables."""
    monkeypatch.setenv("YNAB_API_KEY", "test_api_key")
    monkeypatch.setenv("YNAB_BUDGET_ID", "test_budget_id")

    config = Config.from_env()
    assert config.api_key == "test_api_key"
    assert config.budget_id == "test_budget_id"
    assert config.account_id == "none"  # Should default to "none"


def test_config_missing_env_vars():
    """Test config raises error when required env vars are missing."""
    import pytest

    from ynab_amazon_categorizer.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError):
        Config.from_env()
