"""Tests for transaction matching functionality."""

from ynab_amazon_categorizer.transaction_matcher import TransactionMatcher


def test_transaction_matcher_initialization():
    """Test transaction matcher can be initialized."""
    matcher = TransactionMatcher()
    assert matcher is not None


def test_find_matching_order_exact_amount_match():
    """Test finding order with exact amount match."""
    matcher = TransactionMatcher()

    # Arrange
    transaction_amount = 57.57
    transaction_date = "2024-07-31"
    parsed_orders = [
        {
            "order_id": "702-8237239-1234567",
            "total": 57.57,
            "date": "July 31, 2024",
            "items": ["Test Item"],
        }
    ]

    # Act
    result = matcher.find_matching_order(
        transaction_amount, transaction_date, parsed_orders
    )

    # Assert
    assert result is not None
    assert result["order_id"] == "702-8237239-1234567"
    assert result["total"] == 57.57


def test_find_matching_order_no_match():
    """Test finding order when no orders match criteria."""
    matcher = TransactionMatcher()

    # Arrange
    transaction_amount = 100.00
    transaction_date = "2024-07-31"
    parsed_orders = [
        {
            "order_id": "702-8237239-1234567",
            "total": 57.57,
            "date": "July 31, 2024",
            "items": ["Test Item"],
        }
    ]

    # Act
    result = matcher.find_matching_order(
        transaction_amount, transaction_date, parsed_orders
    )

    # Assert
    assert result is None


def test_find_matching_order_close_amount_match():
    """Test finding order with close amount match (within $1 tolerance)."""
    matcher = TransactionMatcher()

    # Arrange - amount differs by $0.50, should still match
    transaction_amount = 57.07
    transaction_date = "2024-07-31"
    parsed_orders = [
        {
            "order_id": "702-8237239-1234567",
            "total": 57.57,
            "date": "July 31, 2024",
            "items": ["Test Item"]
        }
    ]

    # Act
    result = matcher.find_matching_order(transaction_amount, transaction_date, parsed_orders)

    # Assert
    assert result is not None
    assert result["order_id"] == "702-8237239-1234567"
