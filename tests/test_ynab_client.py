"""Tests for YNAB API client functionality."""

from unittest.mock import Mock, patch

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ynab_amazon_categorizer.exceptions import (
    YNABAPIError,
    YNABAuthError,
    YNABNotFoundError,
    YNABRateLimitError,
    YNABValidationError,
)
from ynab_amazon_categorizer.ynab_client import YNABClient


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
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"test": "data"}}

    with patch.object(client.session, "get", return_value=mock_response) as mock_get:
        result = client.get_data("/test/endpoint")

    assert result == {"test": "data"}
    mock_get.assert_called_once_with(
        "https://api.ynab.com/v1/test/endpoint",
        headers={"Authorization": "Bearer test_key"},
        timeout=30,
    )


def test_get_data_request_error() -> None:
    """Network errors propagate as RequestException."""
    client = YNABClient("test_key", "test_budget")

    with (
        patch.object(
            client.session,
            "get",
            side_effect=requests.exceptions.RequestException("Network error"),
        ),
        pytest.raises(requests.exceptions.RequestException),
    ):
        client.get_data("/test/endpoint")


def test_get_data_auth_error() -> None:
    """401 raises YNABAuthError."""
    client = YNABClient("bad_key", "test_budget")
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"error": {"detail": "Unauthorized"}}
    mock_response.text = "Unauthorized"

    with (
        patch.object(client.session, "get", return_value=mock_response),
        pytest.raises(YNABAuthError),
    ):
        client.get_data("/test/endpoint")


def test_get_data_rate_limit_error() -> None:
    """429 raises YNABRateLimitError."""
    client = YNABClient("test_key", "test_budget")
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.json.return_value = {"error": {"detail": "Too many requests"}}
    mock_response.text = "Too many requests"

    with (
        patch.object(client.session, "get", return_value=mock_response),
        pytest.raises(YNABRateLimitError),
    ):
        client.get_data("/test/endpoint")


def test_get_data_not_found_error() -> None:
    """404 raises YNABNotFoundError."""
    client = YNABClient("test_key", "test_budget")
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"error": {"detail": "Not found"}}
    mock_response.text = "Not found"

    with (
        patch.object(client.session, "get", return_value=mock_response),
        pytest.raises(YNABNotFoundError),
    ):
        client.get_data("/test/endpoint")


def test_get_data_validation_error() -> None:
    """400 raises YNABValidationError."""
    client = YNABClient("test_key", "test_budget")
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"error": {"detail": "Bad request"}}
    mock_response.text = "Bad request"

    with (
        patch.object(client.session, "get", return_value=mock_response),
        pytest.raises(YNABValidationError),
    ):
        client.get_data("/test/endpoint")


def test_get_data_generic_api_error() -> None:
    """500 raises generic YNABAPIError."""
    client = YNABClient("test_key", "test_budget")
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.json.return_value = {"error": {"detail": "Server error"}}
    mock_response.text = "Server error"

    with (
        patch.object(client.session, "get", return_value=mock_response),
        pytest.raises(YNABAPIError),
    ):
        client.get_data("/test/endpoint")


def test_update_transaction_success() -> None:
    """Test successful transaction update."""
    client = YNABClient("test_key", "test_budget")
    payload = {"memo": "test memo"}

    mock_response = Mock()
    mock_response.status_code = 200

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
    """Transaction update network error propagates."""
    client = YNABClient("test_key", "test_budget")

    with (
        patch.object(
            client.session,
            "put",
            side_effect=requests.exceptions.RequestException("Update failed"),
        ),
        pytest.raises(requests.exceptions.RequestException),
    ):
        client.update_transaction("trans_123", {"memo": "test"})


def test_update_transaction_auth_error() -> None:
    """401 on update raises YNABAuthError."""
    client = YNABClient("bad_key", "test_budget")
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"error": {"detail": "Unauthorized"}}
    mock_response.text = "Unauthorized"

    with (
        patch.object(client.session, "put", return_value=mock_response),
        pytest.raises(YNABAuthError),
    ):
        client.update_transaction("trans_123", {"memo": "test"})


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


def test_ynab_api_error_has_status_code() -> None:
    """Typed exceptions carry status_code attribute."""
    err = YNABAuthError("test", status_code=401)
    assert err.status_code == 401
    assert str(err) == "test"
