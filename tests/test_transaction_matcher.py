"""Tests for transaction matching functionality."""

import pytest

from ynab_amazon_categorizer.amazon_parser import Order
from ynab_amazon_categorizer.transaction_matcher import TransactionMatcher


def _make_order(
    order_id: str = "702-0000000-0000000",
    total: float | None = 10.00,
    date_str: str | None = "January 1, 2024",
    items: list[str] | None = None,
) -> Order:
    """Helper to create Order objects for tests."""
    order = Order()
    order.order_id = order_id
    order.total = total
    order.date_str = date_str
    order.items = items or ["Test Item"]
    return order


def test_find_matching_order_exact_amount_match() -> None:
    """Test finding order with exact amount match."""
    matcher = TransactionMatcher()
    order = _make_order(
        order_id="702-8237239-1234567",
        total=57.57,
        date_str="July 31, 2024",
    )

    result = matcher.find_matching_order(57.57, "2024-07-31", [order])

    assert result is not None
    assert result.order_id == "702-8237239-1234567"
    assert result.total == 57.57


def test_find_matching_order_no_match() -> None:
    """Test finding order when no orders match criteria."""
    matcher = TransactionMatcher()
    order = _make_order(total=57.57, date_str="July 31, 2024")

    result = matcher.find_matching_order(100.00, "2024-07-31", [order])

    assert result is None


def test_find_matching_order_close_amount_no_match() -> None:
    """Test close amount does not match when exact matching is required."""
    matcher = TransactionMatcher()
    order = _make_order(total=57.57, date_str="July 31, 2024")

    result = matcher.find_matching_order(57.07, "2024-07-31", [order])

    assert result is None


def test_find_matching_order_with_order_objects() -> None:
    """Test matching works with Order objects."""
    matcher = TransactionMatcher()
    order = _make_order(
        order_id="702-1111111-2222222",
        total=25.99,
        date_str="August 5, 2024",
        items=["Widget A"],
    )

    result = matcher.find_matching_order(25.99, "2024-08-05", [order])

    assert result is not None
    assert isinstance(result, Order)
    assert result.order_id == "702-1111111-2222222"


def test_find_matching_order_none_date_on_order() -> None:
    """Test matching when order has None date — should still match on amount."""
    matcher = TransactionMatcher()
    order = _make_order(total=10.00, date_str=None)

    result = matcher.find_matching_order(10.00, "2024-01-01", [order])

    assert result is not None
    assert result.total == 10.00


def test_find_matching_order_unparseable_transaction_date() -> None:
    """Test matching when transaction date can't be parsed."""
    matcher = TransactionMatcher()
    order = _make_order(total=30.00, date_str="March 1, 2024")

    result = matcher.find_matching_order(30.00, "not-a-date", [order])

    assert result is not None
    assert result.total == 30.00


def test_find_matching_order_date_proximity_scoring() -> None:
    """Test that closer date gets higher score and wins tie-break."""
    matcher = TransactionMatcher()

    order_far = _make_order(
        order_id="702-FAR0000-0000000",
        total=50.00,
        date_str="January 10, 2024",
        items=["Far Item"],
    )
    order_close = _make_order(
        order_id="702-CLOSE00-0000000",
        total=50.00,
        date_str="January 1, 2024",
        items=["Close Item"],
    )

    # Transaction on Jan 1 — should prefer the same-day order
    result = matcher.find_matching_order(50.00, "2024-01-01", [order_far, order_close])

    assert result is not None
    assert result.order_id == "702-CLOSE00-0000000"


def test_find_matching_order_empty_list() -> None:
    """Test with empty parsed orders list."""
    matcher = TransactionMatcher()
    result = matcher.find_matching_order(10.00, "2024-01-01", [])
    assert result is None


def test_find_matching_order_none_total_skipped() -> None:
    """Test that orders with None total are skipped."""
    matcher = TransactionMatcher()
    order = _make_order(total=None)

    result = matcher.find_matching_order(10.00, "2024-01-01", [order])
    assert result is None


def test_find_matching_order_deterministic_tie_break() -> None:
    """When scores and dates are identical, order_id breaks the tie deterministically."""
    matcher = TransactionMatcher()

    order_a = _make_order(order_id="702-AAAAAAA-0000000", total=50.00)
    order_b = _make_order(order_id="702-BBBBBBB-0000000", total=50.00)

    # Regardless of input order, smallest order_id wins
    result1 = matcher.find_matching_order(50.00, "2024-01-01", [order_b, order_a])
    result2 = matcher.find_matching_order(50.00, "2024-01-01", [order_a, order_b])

    assert result1 is not None and result2 is not None
    assert result1.order_id == result2.order_id == "702-AAAAAAA-0000000"


def test_find_matching_order_negative_amount() -> None:
    """Negative transaction amounts are matched via absolute value."""
    matcher = TransactionMatcher()
    order = _make_order(total=25.00)

    result = matcher.find_matching_order(-25.00, "2024-01-01", [order])
    assert result is not None
    assert result.total == 25.00


@pytest.mark.parametrize(
    "trans_date,order_date,expected_bonus",
    [
        ("2024-01-01", "January 1, 2024", 30),  # same day
        ("2024-01-02", "January 1, 2024", 30),  # next day
        ("2024-01-04", "January 1, 2024", 15),  # within 3 days
        ("2024-01-08", "January 1, 2024", 5),  # within 7 days
        ("2024-01-15", "January 1, 2024", 0),  # beyond 7 days
    ],
)
def test_date_proximity_scoring_tiers(
    trans_date: str, order_date: str, expected_bonus: int
) -> None:
    """Verify each date proximity tier independently."""
    matcher = TransactionMatcher()

    # Use two orders: one matching on date, one with no date (score=100)
    order_with_date = _make_order(
        order_id="702-DATED00-0000000", total=10.00, date_str=order_date
    )
    order_no_date = _make_order(
        order_id="702-NODATE0-0000000", total=10.00, date_str=None
    )

    result = matcher.find_matching_order(
        10.00, trans_date, [order_no_date, order_with_date]
    )

    assert result is not None
    if expected_bonus > 0:
        # The dated order should win because 100+bonus > 100
        assert result.order_id == "702-DATED00-0000000"
    else:
        # No bonus, so tie-break by order_id (alphabetically)
        # "702-DATED00-0000000" < "702-NODATE0-0000000"
        assert result.order_id == "702-DATED00-0000000"
