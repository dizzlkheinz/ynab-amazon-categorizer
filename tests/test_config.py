"""Tests for configuration management."""

from pathlib import Path

import pytest

import ynab_amazon_categorizer.config as config_module
from ynab_amazon_categorizer.config import Config
from ynab_amazon_categorizer.exceptions import ConfigurationError


def test_config_from_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading config from environment variables."""
    monkeypatch.setattr(config_module, "DOTENV_AVAILABLE", False)
    monkeypatch.delenv("YNAB_ACCOUNT_ID", raising=False)
    monkeypatch.setenv("YNAB_API_KEY", "test_api_key")
    monkeypatch.setenv("YNAB_BUDGET_ID", "test_budget_id")

    config = Config.from_env()
    assert config.api_key == "test_api_key"
    assert config.budget_id == "test_budget_id"
    assert config.account_id is None  # Default is now None


def test_config_missing_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test config raises error when required env vars are missing."""
    monkeypatch.setattr(config_module, "DOTENV_AVAILABLE", False)
    monkeypatch.delenv("YNAB_API_KEY", raising=False)
    monkeypatch.delenv("YNAB_BUDGET_ID", raising=False)
    monkeypatch.delenv("YNAB_ACCOUNT_ID", raising=False)

    with pytest.raises(ConfigurationError):
        Config.from_env()


def test_config_does_not_load_dotenv_from_parent_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Running in a child directory cannot silently adopt parent credentials."""
    parent = tmp_path / "parent"
    child = parent / "child"
    child.mkdir(parents=True)
    (parent / ".env").write_text(
        "YNAB_API_KEY=parent-key\nYNAB_BUDGET_ID=parent-budget\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(child)
    monkeypatch.setattr(config_module, "DOTENV_AVAILABLE", True)
    monkeypatch.delenv("YNAB_API_KEY", raising=False)
    monkeypatch.delenv("YNAB_BUDGET_ID", raising=False)

    with pytest.raises(ConfigurationError):
        Config.from_env()


def test_config_loads_dotenv_from_current_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A .env in the explicit working directory remains supported."""
    (tmp_path / ".env").write_text(
        "YNAB_API_KEY=local-key\nYNAB_BUDGET_ID=local-budget\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config_module, "DOTENV_AVAILABLE", True)
    monkeypatch.delenv("YNAB_API_KEY", raising=False)
    monkeypatch.delenv("YNAB_BUDGET_ID", raising=False)

    config = Config.from_env()

    assert config.api_key == "local-key"
    assert config.budget_id == "local-budget"


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
    """Test default account_id is None when not set."""
    monkeypatch.setattr(config_module, "DOTENV_AVAILABLE", False)
    monkeypatch.setenv("YNAB_API_KEY", "key")
    monkeypatch.setenv("YNAB_BUDGET_ID", "budget")
    monkeypatch.delenv("YNAB_ACCOUNT_ID", raising=False)

    config = Config.from_env()
    assert config.account_id is None


def test_config_explicit_account_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test explicit account_id is preserved."""
    monkeypatch.setattr(config_module, "DOTENV_AVAILABLE", False)
    monkeypatch.setenv("YNAB_API_KEY", "key")
    monkeypatch.setenv("YNAB_BUDGET_ID", "budget")
    monkeypatch.setenv("YNAB_ACCOUNT_ID", "my-account-123")

    config = Config.from_env()
    assert config.account_id == "my-account-123"


def test_config_none_string_treated_as_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Account ID of 'none' (any case) is treated as None."""
    monkeypatch.setattr(config_module, "DOTENV_AVAILABLE", False)
    monkeypatch.setenv("YNAB_API_KEY", "key")
    monkeypatch.setenv("YNAB_BUDGET_ID", "budget")

    for value in ("none", "None", "NONE", "  none  "):
        monkeypatch.setenv("YNAB_ACCOUNT_ID", value)
        config = Config.from_env()
        assert config.account_id is None, f"Expected None for YNAB_ACCOUNT_ID={value!r}"


def test_config_empty_account_id_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty string account_id is treated as None."""
    monkeypatch.setattr(config_module, "DOTENV_AVAILABLE", False)
    monkeypatch.setenv("YNAB_API_KEY", "key")
    monkeypatch.setenv("YNAB_BUDGET_ID", "budget")
    monkeypatch.setenv("YNAB_ACCOUNT_ID", "")

    config = Config.from_env()
    assert config.account_id is None
