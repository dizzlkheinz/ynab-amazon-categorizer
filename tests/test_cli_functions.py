"""Tests for extracted CLI helper functions."""


import pytest

from ynab_amazon_categorizer.cli import (
    build_preview,
    build_single_payload,
    build_split_payload,
    compute_split_amount,
    print_config_summary,
)
from ynab_amazon_categorizer.config import Config

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
