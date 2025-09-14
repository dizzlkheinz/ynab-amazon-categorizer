"""Tests for YNAB API client functionality."""

from unittest.mock import Mock, patch

import requests

from ynab_amazon_categorizer.ynab_client import YNABClient


def test_ynab_client_initialization():
    """Test YNAB client can be initialized with API key and budget ID."""
    client = YNABClient("test_api_key", "test_budget_id")
    assert client.api_key == "test_api_key"
    assert client.budget_id == "test_budget_id"


@patch("ynab_amazon_categorizer.ynab_client.requests.get")
def test_get_data_success(mock_get):
    """Test successful YNAB API data retrieval."""
    # Arrange
    mock_response = Mock()
    mock_response.json.return_value = {"data": {"test": "data"}}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    client = YNABClient("test_key", "test_budget")

    # Act
    result = client.get_data("/test/endpoint")

    # Assert
    assert result == {"test": "data"}
    mock_get.assert_called_once_with(
        "https://api.ynab.com/v1/test/endpoint",
        headers={"Authorization": "Bearer test_key"},
    )


@patch("ynab_amazon_categorizer.ynab_client.requests.get")
def test_get_data_request_error(mock_get):
    """Test YNAB API request error handling."""
    # Arrange
    mock_get.side_effect = requests.exceptions.RequestException("Network error")
    client = YNABClient("test_key", "test_budget")

    # Act
    result = client.get_data("/test/endpoint")

    # Assert
    assert result is None


@patch("ynab_amazon_categorizer.ynab_client.requests.put")
def test_update_transaction_success(mock_put):
    """Test successful transaction update."""
    # Arrange
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_put.return_value = mock_response

    client = YNABClient("test_key", "test_budget")
    payload = {"memo": "test memo"}

    # Act
    result = client.update_transaction("trans_123", payload)

    # Assert
    assert result is True
    mock_put.assert_called_once_with(
        "https://api.ynab.com/v1/budgets/test_budget/transactions/trans_123",
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json",
        },
        json={"transaction": payload},
    )


@patch("ynab_amazon_categorizer.ynab_client.requests.put")
def test_update_transaction_error(mock_put):
    """Test transaction update error handling."""
    # Arrange
    mock_put.side_effect = requests.exceptions.RequestException("Update failed")
    client = YNABClient("test_key", "test_budget")

    # Act
    result = client.update_transaction("trans_123", {"memo": "test"})

    # Assert
    assert result is False


def test_get_categories_calls_get_data():
    """Test that get_categories properly calls get_data method."""
    # Arrange
    client = YNABClient("test_key", "test_budget")

    # Mock the get_data method to return categories data
    client.get_data = Mock(
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

    # Act
    categories, name_to_id, id_to_name = client.get_categories()

    # Assert
    client.get_data.assert_called_once_with("/budgets/test_budget/categories")
    assert len(categories) == 1
    assert categories[0] == ("Test Group: Test Category", "cat1")
    assert "test group: test category" in name_to_id
    assert "cat1" in id_to_name
