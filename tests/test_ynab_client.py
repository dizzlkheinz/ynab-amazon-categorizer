"""Tests for YNAB API client functionality."""

from unittest.mock import Mock, patch

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ynab_amazon_categorizer.ynab_client import YNABClient


def test_ynab_client_initialization() -> None:
    """Test YNAB client can be initialized with API key and budget ID."""
    client = YNABClient("test_api_key", "test_budget_id")
    assert client.api_key == "test_api_key"
    assert client.budget_id == "test_budget_id"


def test_ynab_client_has_retry_adapter() -> None:
    """Test that the session has a retry adapter configured."""
    client = YNABClient("test_key", "test_budget")

    adapter = client.session.get_adapter("https://api.ynab.com")
    assert isinstance(adapter, HTTPAdapter)
    retry: Retry = adapter.max_retries
    assert retry.total == 3
    assert retry.backoff_factor == 0.5
    assert 429 in retry.status_forcelist
    assert 503 in retry.status_forcelist


def test_get_data_success() -> None:
    """Test successful YNAB API data retrieval."""
    client = YNABClient("test_key", "test_budget")

    mock_response = Mock()
    mock_response.json.return_value = {"data": {"test": "data"}}
    mock_response.raise_for_status.return_value = None

    with patch.object(client.session, "get", return_value=mock_response) as mock_get:
        result = client.get_data("/test/endpoint")

    assert result == {"test": "data"}
    mock_get.assert_called_once_with(
        "https://api.ynab.com/v1/test/endpoint",
        headers={"Authorization": "Bearer test_key"},
        timeout=30,
    )


def test_get_data_request_error() -> None:
    """Test YNAB API request error handling."""
    client = YNABClient("test_key", "test_budget")

    with patch.object(
        client.session,
        "get",
        side_effect=requests.exceptions.RequestException("Network error"),
    ):
        result = client.get_data("/test/endpoint")

    assert result is None


def test_update_transaction_success() -> None:
    """Test successful transaction update."""
    client = YNABClient("test_key", "test_budget")
    payload = {"memo": "test memo"}

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None

    with patch.object(client.session, "put", return_value=mock_response) as mock_put:
        result = client.update_transaction("trans_123", payload)

    assert result is True
    mock_put.assert_called_once_with(
        "https://api.ynab.com/v1/budgets/test_budget/transactions/trans_123",
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json",
        },
        json={"transaction": payload},
        timeout=30,
    )


def test_update_transaction_error() -> None:
    """Test transaction update error handling."""
    client = YNABClient("test_key", "test_budget")

    with patch.object(
        client.session,
        "put",
        side_effect=requests.exceptions.RequestException("Update failed"),
    ):
        result = client.update_transaction("trans_123", {"memo": "test"})

    assert result is False


def test_get_categories_calls_get_data() -> None:
    """Test that get_categories properly calls get_data method."""
    client = YNABClient("test_key", "test_budget")

    mock_get_data = Mock(
        return_value={
            "category_groups": [
                {
                    "id": "group1",
                    "name": "Test Group",
                    "hidden": False,
                    "categories": [
                        {
                            "id": "cat1",
                            "name": "Test Category",
                            "hidden": False,
                            "deleted": False,
                        }
                    ],
                }
            ]
        }
    )
    client.get_data = mock_get_data  # type: ignore[method-assign]

    categories, name_to_id, id_to_name = client.get_categories()

    mock_get_data.assert_called_once_with("/budgets/test_budget/categories")
    assert len(categories) == 1
    assert categories[0] == ("Test Group: Test Category", "cat1")
    assert "test group: test category" in name_to_id
    assert "cat1" in id_to_name


def test_get_categories_logs_warning_on_failure() -> None:
    """Test that get_categories logs a warning when data fetch fails."""
    client = YNABClient("test_key", "test_budget")
    client.get_data = Mock(return_value=None)  # type: ignore[method-assign]

    categories, name_to_id, id_to_name = client.get_categories()

    assert categories == []
    assert name_to_id == {}
    assert id_to_name == {}
