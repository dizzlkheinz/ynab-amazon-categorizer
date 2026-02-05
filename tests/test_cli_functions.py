"""Tests for extracted CLI helper functions."""

from unittest.mock import Mock

import pytest

from ynab_amazon_categorizer.amazon_parser import Order
from ynab_amazon_categorizer.cli import (
    build_preview,
    build_single_payload,
    build_split_payload,
    compute_split_amount,
    display_matched_order,
    fetch_amazon_transactions,
    generate_split_summary_memo,
    print_config_summary,
)
from ynab_amazon_categorizer.config import Config
from ynab_amazon_categorizer.memo_generator import MemoGenerator

# --- build_preview tests ---


def test_build_preview_does_not_mutate() -> None:
    """Fix #1: build_preview uses deepcopy so the original payload is not mutated."""
    payload = {
        "id": "t1",
        "category_id": "cat1",
        "subtransactions": [
            {"amount": -5000, "category_id": "cat2", "memo": "item"},
        ],
    }
    category_id_map = {"cat1": "Groceries", "cat2": "Household"}

    preview = build_preview(payload, category_id_map)

    # Preview should have injected names
    assert preview["category_name"] == "Groceries"
    assert preview["subtransactions"][0]["category_name"] == "Household"

    # Original payload must NOT have category_name keys
    assert "category_name" not in payload
    assert "category_name" not in payload["subtransactions"][0]


def test_build_preview_adds_category_names() -> None:
    """Category names are resolved from the id map."""
    payload = {"category_id": "c1"}
    result = build_preview(payload, {"c1": "Fun Money"})
    assert result["category_name"] == "Fun Money"


def test_build_preview_unknown_category() -> None:
    """Unknown category IDs get a fallback label."""
    payload = {"category_id": "unknown_id"}
    result = build_preview(payload, {})
    assert result["category_name"] == "Unknown Category"


# --- compute_split_amount tests ---


def test_compute_split_amount_outflow() -> None:
    """Outflow (negative remaining) produces a negative result."""
    result = compute_split_amount(10.0, -20000)
    assert result == -10000


def test_compute_split_amount_inflow() -> None:
    """Fix #2: Inflow (positive remaining) produces a positive result."""
    result = compute_split_amount(10.0, 20000)
    assert result == 10000


def test_compute_split_amount_snap() -> None:
    """When the amount is within 1 milliunit of remaining, snap to exact remainder."""
    # 10.0 * 1000 = 10000, remaining is -10001 → difference is 1 → snap
    result = compute_split_amount(10.0, -10001)
    assert result == -10001


def test_compute_split_amount_exceeds() -> None:
    """Raises ValueError when amount exceeds the remaining balance."""
    with pytest.raises(ValueError, match="exceeds remaining"):
        compute_split_amount(25.0, -20000)


# --- build_single_payload tests ---


def test_build_single_payload() -> None:
    """Verify single-category payload structure."""
    transaction = {
        "id": "t1",
        "account_id": "a1",
        "date": "2025-01-15",
        "amount": -15000,
        "payee_id": "p1",
        "payee_name": "Amazon",
        "cleared": "uncleared",
        "flag_color": None,
        "import_id": "imp1",
    }
    result = build_single_payload(transaction, "cat1", "test memo")

    assert result["id"] == "t1"
    assert result["category_id"] == "cat1"
    assert result["memo"] == "test memo"
    assert result["approved"] is True
    assert result["amount"] == -15000


# --- build_split_payload tests ---


def test_build_split_payload() -> None:
    """Verify split payload structure."""
    transaction = {
        "id": "t1",
        "account_id": "a1",
        "date": "2025-01-15",
        "amount": -15000,
        "payee_id": "p1",
        "payee_name": "Amazon",
        "cleared": "uncleared",
        "flag_color": None,
        "import_id": "imp1",
    }
    subtransactions = [
        {"amount": -10000, "category_id": "cat1", "memo": "item1"},
        {"amount": -5000, "category_id": "cat2", "memo": "item2"},
    ]
    result = build_split_payload(transaction, subtransactions, None, "original")

    assert result["category_id"] is None
    assert result["memo"] == "original"
    assert result["subtransactions"] == subtransactions
    assert result["approved"] is True


# --- print_config_summary tests ---


def test_print_config_summary_masks_secrets(capsys: pytest.CaptureFixture[str]) -> None:
    """Fix #6: No API key or full budget ID appears in output."""
    config = Config(
        api_key="sk-secret-api-key-12345678",
        budget_id="abcd-efgh-ijkl-mnop",
        account_id="none",
    )
    print_config_summary(config)

    captured = capsys.readouterr().out

    # Must NOT contain the full API key or budget ID
    assert "sk-secret-api-key-12345678" not in captured
    assert "abcd-efgh-ijkl-mnop" not in captured

    # Should show masked info
    assert "API Key: configured" in captured
    assert "mnop" in captured  # last 4 of budget_id
    assert "All accounts" in captured


# --- fetch_amazon_transactions tests ---


def test_fetch_amazon_transactions_filters_correctly() -> None:
    """Verify that fetch_amazon_transactions filters to uncategorized Amazon transactions."""
    mock_client = Mock()
    mock_client.get_data.return_value = {
        "transactions": [
            {
                "id": "t1",
                "payee_name": "Amazon.com",
                "category_id": None,
                "cleared": "uncleared",
                "amount": -5000,
                "transfer_account_id": None,
                "subtransactions": [],
                "import_id": "imp1",
            },
            {
                "id": "t2",
                "payee_name": "Grocery Store",
                "category_id": None,
                "cleared": "uncleared",
                "amount": -3000,
                "transfer_account_id": None,
                "subtransactions": [],
                "import_id": "imp2",
            },
            {
                "id": "t3",
                "payee_name": "AMZN Mktp US",
                "category_id": "cat1",  # already categorized
                "cleared": "uncleared",
                "amount": -2000,
                "transfer_account_id": None,
                "subtransactions": [],
                "import_id": "imp3",
            },
        ]
    }
    config = Config(api_key="key", budget_id="budget", account_id="none")

    result = fetch_amazon_transactions(mock_client, config)

    assert len(result) == 1
    assert result[0]["id"] == "t1"


def test_fetch_amazon_transactions_empty_response() -> None:
    """Returns empty list when API returns no data."""
    mock_client = Mock()
    mock_client.get_data.return_value = None
    config = Config(api_key="key", budget_id="budget", account_id="none")

    result = fetch_amazon_transactions(mock_client, config)

    assert result == []


def test_fetch_amazon_transactions_with_account_id() -> None:
    """Uses account-specific endpoint when account_id is set."""
    mock_client = Mock()
    mock_client.get_data.return_value = {"transactions": []}
    config = Config(api_key="key", budget_id="budget", account_id="acct123")

    fetch_amazon_transactions(mock_client, config)

    mock_client.get_data.assert_called_once_with(
        "/budgets/budget/accounts/acct123/transactions"
    )


# --- generate_split_summary_memo tests ---


def test_generate_split_summary_memo_single_item() -> None:
    """Single-item order returns item directly."""
    order = Order()
    order.items = ["Widget X"]
    assert generate_split_summary_memo(order) == "Widget X"


def test_generate_split_summary_memo_multiple_items() -> None:
    """Multiple items returns formatted list."""
    order = Order()
    order.items = ["Widget A", "Widget B"]
    result = generate_split_summary_memo(order)
    assert result == "2 Items:\n- Widget A\n- Widget B"


def test_generate_split_summary_memo_no_items() -> None:
    """Order with no items returns empty string."""
    order = Order()
    order.items = []
    assert generate_split_summary_memo(order) == ""


# --- display_matched_order tests ---


def test_display_matched_order_with_order_object(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Display order details from an Order object."""
    order = Order()
    order.order_id = "702-1234567-7654321"
    order.total = 42.99
    order.date_str = "January 15, 2025"
    order.items = ["Test Product"]

    memo_gen = MemoGenerator("amazon.com")
    display_matched_order(order, memo_gen)

    captured = capsys.readouterr().out
    assert "702-1234567-7654321" in captured
    assert "42.99" in captured
    assert "Test Product" in captured


def test_display_matched_order_with_dict(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Display order details from a dict."""
    order_dict = {
        "order_id": "702-DICT",
        "total": 19.99,
        "date_str": "Feb 1, 2025",
        "items": ["Dict Item"],
    }

    memo_gen = MemoGenerator("amazon.ca")
    display_matched_order(order_dict, memo_gen)

    captured = capsys.readouterr().out
    assert "702-DICT" in captured
    assert "19.99" in captured
    assert "Dict Item" in captured
