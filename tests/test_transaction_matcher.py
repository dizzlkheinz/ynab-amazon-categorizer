"""Tests for transaction matching functionality."""

from typing import Any, cast

from ynab_amazon_categorizer.amazon_parser import Order
from ynab_amazon_categorizer.transaction_matcher import TransactionMatcher


def test_transaction_matcher_initialization() -> None:
    """Test transaction matcher can be initialized."""
    matcher = TransactionMatcher()
    assert matcher is not None


def test_find_matching_order_exact_amount_match() -> None:
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
    if isinstance(result, dict):
        result_dict = cast(dict[str, Any], result)
        assert result_dict["order_id"] == "702-8237239-1234567"
        assert result_dict["total"] == 57.57
    else:
        assert result.order_id == "702-8237239-1234567"
        assert result.total == 57.57


def test_find_matching_order_no_match() -> None:
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


def test_find_matching_order_close_amount_no_match() -> None:
    """Test close amount does not match when exact matching is required."""
    matcher = TransactionMatcher()

    # Arrange - amount differs by $0.50 and should not match
    transaction_amount = 57.07
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


# --- New edge case tests ---


def test_find_matching_order_with_order_objects() -> None:
    """Test matching works with Order objects (not just dicts)."""
    matcher = TransactionMatcher()

    order = Order()
    order.order_id = "702-1111111-2222222"
    order.total = 25.99
    order.date_str = "August 5, 2024"
    order.items = ["Widget A"]

    result = matcher.find_matching_order(25.99, "2024-08-05", [order])

    assert result is not None
    assert isinstance(result, Order)
    assert result.order_id == "702-1111111-2222222"


def test_find_matching_order_none_date_on_order() -> None:
    """Test matching when order has None date — should still match on amount."""
    matcher = TransactionMatcher()

    order = Order()
    order.order_id = "702-0000000-0000000"
    order.total = 10.00
    order.date_str = None
    order.items = ["Item"]

    result = matcher.find_matching_order(10.00, "2024-01-01", [order])

    assert result is not None
    assert isinstance(result, Order)
    assert result.total == 10.00


def test_find_matching_order_unparseable_transaction_date() -> None:
    """Test matching when transaction date can't be parsed."""
    matcher = TransactionMatcher()

    parsed_orders = [
        {
            "order_id": "702-1234567-1234567",
            "total": 30.00,
            "date": "March 1, 2024",
            "items": ["Gadget"],
        }
    ]

    result = matcher.find_matching_order(30.00, "not-a-date", parsed_orders)

    assert result is not None
    result_dict = cast(dict[str, Any], result)
    assert result_dict["total"] == 30.00


def test_find_matching_order_date_proximity_scoring() -> None:
    """Test that closer date gets higher score and wins tie-break."""
    matcher = TransactionMatcher()

    order_far = Order()
    order_far.order_id = "702-FAR"
    order_far.total = 50.00
    order_far.date_str = "January 10, 2024"
    order_far.items = ["Far Item"]

    order_close = Order()
    order_close.order_id = "702-CLOSE"
    order_close.total = 50.00
    order_close.date_str = "January 1, 2024"
    order_close.items = ["Close Item"]

    # Transaction on Jan 1 — should prefer the same-day order
    result = matcher.find_matching_order(50.00, "2024-01-01", [order_far, order_close])

    assert result is not None
    assert isinstance(result, Order)
    assert result.order_id == "702-CLOSE"


def test_find_matching_order_empty_list() -> None:
    """Test with empty parsed orders list."""
    matcher = TransactionMatcher()
    result = matcher.find_matching_order(10.00, "2024-01-01", [])
    assert result is None


def test_find_matching_order_none_total_skipped() -> None:
    """Test that orders with None total are skipped."""
    matcher = TransactionMatcher()

    order = Order()
    order.order_id = "702-NONE"
    order.total = None
    order.date_str = "January 1, 2024"
    order.items = ["Item"]

    result = matcher.find_matching_order(10.00, "2024-01-01", [order])
    assert result is None
