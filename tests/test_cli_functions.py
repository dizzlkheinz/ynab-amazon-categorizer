"""Tests for extracted CLI helper functions."""

from unittest.mock import Mock

import pytest

import ynab_amazon_categorizer.cli as cli_module
from ynab_amazon_categorizer.amazon_parser import Order
from ynab_amazon_categorizer.batch import process_batch
from ynab_amazon_categorizer.cli import (
    _handle_categorize,
    _parse_args,
    build_preview,
    compute_split_amount,
    display_matched_order,
    handle_split,
    print_config_summary,
    process_transaction,
    resolve_memo,
)
from ynab_amazon_categorizer.config import Config
from ynab_amazon_categorizer.exceptions import YNABResponseError
from ynab_amazon_categorizer.memo_generator import (
    MemoGenerator,
    build_batch_memo,
    generate_split_summary_memo,
)
from ynab_amazon_categorizer.models import SaveSubtransaction
from ynab_amazon_categorizer.payloads import (
    build_memo_only_payload,
    build_single_payload,
    build_split_payload,
)
from ynab_amazon_categorizer.transactions import (
    fetch_amazon_transactions,
    is_amazon_payee,
)

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
    """Single-category updates include only fields intentionally changed."""
    result = build_single_payload("cat1", "test memo")

    assert result == {
        "category_id": "cat1",
        "memo": "test memo",
        "approved": True,
    }


def test_build_single_payload_sanitizes_long_memo() -> None:
    """Long memos are truncated via sanitize_memo."""
    long_memo = "A" * 300
    result = build_single_payload("cat1", long_memo)
    assert len(result["memo"]) <= 200


# --- build_split_payload tests ---


def test_build_split_payload() -> None:
    """Split updates include only the requested split fields."""
    subtransactions: list[SaveSubtransaction] = [
        {"amount": -10000, "category_id": "cat1", "memo": "item1"},
        {"amount": -5000, "category_id": "cat2", "memo": "item2"},
    ]
    result = build_split_payload(subtransactions, None, "original")

    assert result["category_id"] is None
    assert result["memo"] == "original"
    assert result["subtransactions"] == subtransactions
    assert result["approved"] is True
    assert set(result) == {"category_id", "memo", "approved", "subtransactions"}


def test_build_split_payload_with_order() -> None:
    """Split payload uses order items for summary memo."""
    order = Order()
    order.items = ["Widget A", "Widget B"]
    subtransactions: list[SaveSubtransaction] = [
        {"amount": -10000, "category_id": "cat1", "memo": "item1"}
    ]

    result = build_split_payload(subtransactions, order, "original")
    assert "Widget A" in result["memo"]
    assert "Widget B" in result["memo"]


def test_resolve_memo_keeps_all_matched_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Single-category matched orders keep all parsed items in the suggested memo."""
    order = Order()
    order.order_id = "702-1234567-7654321"
    order.items = ["Widget A", "Widget B"]

    monkeypatch.setattr("ynab_amazon_categorizer.cli._prompt_line", lambda _prompt: "")

    result = resolve_memo(order, "", MemoGenerator("amazon.com"))

    assert "Widget A" in result
    assert "Widget B" in result
    assert "702-1234567-7654321" in result


# --- print_config_summary tests ---


def test_print_config_summary_masks_secrets(capsys: pytest.CaptureFixture[str]) -> None:
    """Fix #6: No API key or full budget ID appears in output."""
    config = Config(
        api_key="dummy-api-key-for-testing",
        budget_id="abcd-efgh-ijkl-mnop",
        account_id=None,
    )
    print_config_summary(config)

    captured = capsys.readouterr().out

    # Must NOT contain the full API key or budget ID
    assert "dummy-api-key-for-testing" not in captured
    assert "abcd-efgh-ijkl-mnop" not in captured

    # Should show masked info
    assert "API Key: configured" in captured
    assert "mnop" in captured  # last 4 of budget_id
    assert "All accounts" in captured


def test_print_config_summary_with_account(capsys: pytest.CaptureFixture[str]) -> None:
    """Shows 'Account ID: configured' when account is set."""
    config = Config(api_key="key", budget_id="budget", account_id="acct123")
    print_config_summary(config)
    captured = capsys.readouterr().out
    assert "Account ID: configured" in captured


# --- fetch_amazon_transactions tests ---


@pytest.mark.parametrize(
    "payee_name", ["Amazon.com", "AMZN Mktp CA", "AMZ*Marketplace", "amazon.ca"]
)
def test_is_amazon_payee_accepts_vendor_markers(payee_name: str) -> None:
    assert is_amazon_payee(payee_name) is True


@pytest.mark.parametrize(
    "payee_name", ["Ramzi Market", "Glamzone", "Amazing Store", ""]
)
def test_is_amazon_payee_rejects_substring_false_positives(payee_name: str) -> None:
    assert is_amazon_payee(payee_name) is False


def test_fetch_amazon_transactions_filters_correctly() -> None:
    """Verify that fetch_amazon_transactions filters to uncategorized Amazon transactions."""
    mock_client = Mock()
    mock_client.get_data.return_value = {
        "transactions": [
            {
                "id": "t1",
                "account_id": "a1",
                "date": "2025-01-01",
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
                "account_id": "a1",
                "date": "2025-01-02",
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
                "account_id": "a1",
                "date": "2025-01-03",
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
    config = Config(api_key="key", budget_id="budget", account_id=None)

    result = fetch_amazon_transactions(mock_client, config)

    assert len(result) == 1
    assert result[0]["id"] == "t1"


def test_fetch_amazon_transactions_empty_response() -> None:
    """Returns an empty list when the API returns an empty transaction list."""
    mock_client = Mock()
    mock_client.get_data.return_value = {"transactions": []}
    config = Config(api_key="key", budget_id="budget", account_id=None)

    result = fetch_amazon_transactions(mock_client, config)

    assert result == []


@pytest.mark.parametrize("response", [None, {}, {"transactions": "not-a-list"}])
def test_fetch_amazon_transactions_rejects_malformed_collection(
    response: object,
) -> None:
    """A malformed collection cannot masquerade as no matching transactions."""
    mock_client = Mock()
    mock_client.get_data.return_value = response
    config = Config(api_key="key", budget_id="budget", account_id=None)

    with pytest.raises(YNABResponseError, match="transactions collection"):
        fetch_amazon_transactions(mock_client, config)


def test_fetch_amazon_transactions_rejects_malformed_item() -> None:
    """Required transaction fields are validated with item context."""
    mock_client = Mock()
    mock_client.get_data.return_value = {
        "transactions": [{"id": "t1", "payee_name": "Amazon", "amount": "5.00"}]
    }
    config = Config(api_key="key", budget_id="budget", account_id=None)

    with pytest.raises(YNABResponseError, match="transaction at index 0"):
        fetch_amazon_transactions(mock_client, config)


def test_fetch_amazon_transactions_with_account_id() -> None:
    """Uses account-specific endpoint when account_id is set."""
    mock_client = Mock()
    mock_client.get_data.return_value = {"transactions": []}
    config = Config(api_key="key", budget_id="budget", account_id="acct123")

    fetch_amazon_transactions(mock_client, config)

    mock_client.get_data.assert_called_once_with(
        "/budgets/budget/accounts/acct123/transactions"
    )


def test_fetch_amazon_transactions_includes_manual() -> None:
    """Manual transactions (no import_id) are now included."""
    mock_client = Mock()
    mock_client.get_data.return_value = {
        "transactions": [
            {
                "id": "t1",
                "account_id": "a1",
                "date": "2025-01-01",
                "payee_name": "Amazon.com",
                "category_id": None,
                "cleared": "uncleared",
                "amount": -5000,
                "transfer_account_id": None,
                "subtransactions": [],
                # No import_id — manual transaction
            },
        ]
    }
    config = Config(api_key="key", budget_id="budget", account_id=None)

    result = fetch_amazon_transactions(mock_client, config)

    assert len(result) == 1
    assert result[0]["id"] == "t1"


# --- process_transaction display tests ---


def test_prompt_for_orders_displays_parsed_currency_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The parser's currency survives through the first CLI order summary."""
    monkeypatch.setattr(
        cli_module,
        "get_multiline_input_with_custom_submit",
        lambda _prompt: (
            """
        Order placed January 15, 2025
        Total £14.99
        Order # 702-1234567-7654321
        International Product Name With Enough Words To Parse
        """
        ),
    )

    orders = cli_module.prompt_for_amazon_orders_data()

    assert orders is not None
    assert orders[0].currency == "£"
    captured = capsys.readouterr().out
    assert "Order 702-1234567-7654321: £14.99" in captured
    assert "Order 702-1234567-7654321: $14.99" not in captured


def test_process_transaction_displays_inflow_amount_without_negating(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Accepted inflows display with their actual positive sign."""
    transaction = {
        "id": "t1",
        "date": "2025-01-15",
        "payee_name": "Amazon",
        "amount": 10000,
        "memo": "",
    }
    responses = iter(["y", "s"])
    monkeypatch.setattr(
        "ynab_amazon_categorizer.cli._prompt_line", lambda _prompt: next(responses)
    )

    result = process_transaction(
        transaction,
        0,
        1,
        None,
        MemoGenerator(),
        Mock(),
        Mock(),
        {},
        {},
    )

    captured = capsys.readouterr().out
    assert result is True
    assert "Found inflow transaction: Amazon $10.00" in captured
    assert "Amount: 10.00" in captured


def test_process_transaction_uses_matched_order_currency_for_inflow(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A matched non-dollar refund is not presented as a dollar transaction."""
    transaction = {
        "id": "t1",
        "date": "2025-01-15",
        "payee_name": "Amazon",
        "amount": 10000,
        "memo": "",
    }
    order = Order(
        order_id="702-1234567-7654321",
        total=10.00,
        date_str="January 15, 2025",
        currency="£",
    )
    responses = iter(["y", "s"])
    monkeypatch.setattr(
        "ynab_amazon_categorizer.cli._prompt_line", lambda _prompt: next(responses)
    )

    result = process_transaction(
        transaction,
        0,
        1,
        [order],
        MemoGenerator(),
        Mock(),
        Mock(),
        {},
        {},
    )

    assert result is True
    captured = capsys.readouterr().out
    assert "Found inflow transaction: Amazon £10.00" in captured
    assert "Found inflow transaction: Amazon $10.00" not in captured


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


def test_display_matched_order_uses_parsed_currency(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Matched totals retain their Amazon currency prefix during verification."""
    order = Order(
        order_id="702-1234567-7654321",
        total=42.99,
        date_str="January 15, 2025",
        items=["Test Product"],
        currency="£",
    )

    display_matched_order(order, MemoGenerator("amazon.co.uk"))

    captured = capsys.readouterr().out
    assert "Total: £42.99" in captured
    assert "Total: $42.99" not in captured


# --- handle_split tests ---


def _split_order() -> Order:
    order = Order()
    order.order_id = "702-1234567-7654321"
    order.total = 20.00
    order.date_str = "January 1, 2024"
    order.items = ["Widget A", "Widget B"]
    return order


def test_handle_split_two_even_splits(monkeypatch: pytest.MonkeyPatch) -> None:
    """A two-item order splits cleanly into two equal subtransactions."""
    order = _split_order()
    categories = iter([("cat1", "Cat One"), ("cat2", "Cat Two")])
    monkeypatch.setattr(
        "ynab_amazon_categorizer.cli.prompt_for_category_selection",
        lambda *a, **k: next(categories),
    )
    # split-1 amount, split-1 "use suggested?", split-2 amount (default), split-2 memo
    responses = iter(["10", "", "", ""])
    monkeypatch.setattr(
        "ynab_amazon_categorizer.cli._prompt_line", lambda _prompt: next(responses)
    )

    result = handle_split(
        {"amount": -20000}, order, MemoGenerator("amazon.com"), Mock(), {}
    )

    assert result is not None
    assert len(result) == 2
    assert result[0]["amount"] == -10000
    assert result[1]["amount"] == -10000
    assert result[0]["category_id"] == "cat1"
    assert result[1]["category_id"] == "cat2"
    assert "Widget A" in str(result[0]["memo"])
    assert "Widget B" in str(result[1]["memo"])


def test_handle_split_cancel_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Backing out of category selection cancels the whole split."""
    monkeypatch.setattr(
        "ynab_amazon_categorizer.cli.prompt_for_category_selection",
        lambda *a, **k: (None, None),
    )

    result = handle_split(
        {"amount": -20000}, _split_order(), MemoGenerator(), Mock(), {}
    )

    assert result is None


# --- _parse_args / dry-run tests ---


def test_parse_args_dry_run_flag() -> None:
    """--dry-run sets the dry_run attribute."""
    assert _parse_args(["--dry-run"]).dry_run is True
    assert _parse_args([]).dry_run is False


def test_handle_categorize_dry_run_does_not_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In dry-run mode the preview is shown but no API update is sent."""
    transaction = {
        "id": "t1",
        "account_id": "a1",
        "date": "2025-01-15",
        "amount": -15000,
    }
    monkeypatch.setattr(
        "ynab_amazon_categorizer.cli.prompt_for_category_selection",
        lambda *a, **k: ("cat1", "Cat One"),
    )
    monkeypatch.setattr(
        "ynab_amazon_categorizer.cli.get_multiline_input_with_custom_submit",
        lambda *a, **k: "",
    )
    # "Split this transaction?" -> n, "Enter item details manually?" -> n
    responses = iter(["n", "n"])
    monkeypatch.setattr(
        "ynab_amazon_categorizer.cli._prompt_line", lambda _prompt: next(responses)
    )
    ynab_client = Mock()

    result = _handle_categorize(
        transaction,
        None,
        "",
        MemoGenerator(),
        ynab_client,
        Mock(),
        {},
        {},
        dry_run=True,
    )

    assert result == "done"
    ynab_client.update_transaction.assert_not_called()


# --- process_transaction order-consumption tests ---


def _amount_matched_order() -> Order:
    order = Order()
    order.order_id = "702-CONSUME-0000000"
    order.total = 20.00
    order.date_str = "January 1, 2024"
    order.items = ["Widget A"]
    return order


def test_process_transaction_marks_order_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successfully categorized matched order is added to used_order_ids."""
    monkeypatch.setattr(
        "ynab_amazon_categorizer.cli._handle_categorize", lambda *a, **k: "done"
    )
    monkeypatch.setattr("ynab_amazon_categorizer.cli._prompt_line", lambda _prompt: "c")
    used: set[str] = set()
    transaction = {
        "id": "t1",
        "date": "2024-01-01",
        "payee_name": "Amazon",
        "amount": -20000,
        "memo": "",
    }

    result = process_transaction(
        transaction,
        0,
        1,
        [_amount_matched_order()],
        MemoGenerator(),
        Mock(),
        Mock(),
        {},
        {},
        used,
        False,
    )

    assert result is True
    assert "702-CONSUME-0000000" in used


def test_process_transaction_dry_run_does_not_mark_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In dry-run mode a matched order is NOT marked as consumed."""
    monkeypatch.setattr(
        "ynab_amazon_categorizer.cli._handle_categorize", lambda *a, **k: "done"
    )
    monkeypatch.setattr("ynab_amazon_categorizer.cli._prompt_line", lambda _prompt: "c")
    used: set[str] = set()
    transaction = {
        "id": "t1",
        "date": "2024-01-01",
        "payee_name": "Amazon",
        "amount": -20000,
        "memo": "",
    }

    result = process_transaction(
        transaction,
        0,
        1,
        [_amount_matched_order()],
        MemoGenerator(),
        Mock(),
        Mock(),
        {},
        {},
        used,
        True,
    )

    assert result is True
    assert used == set()


# --- batch mode tests ---


def test_parse_args_batch_flag() -> None:
    """--batch sets the batch attribute; flags are independent."""
    assert _parse_args(["--batch"]).batch is True
    assert _parse_args([]).batch is False
    args = _parse_args(["--batch", "--dry-run"])
    assert args.batch is True and args.dry_run is True


@pytest.mark.parametrize("approved", [False, True])
def test_build_memo_only_payload_contains_only_intentional_fields(
    approved: bool,
) -> None:
    """Memo updates preserve approval without resending unrelated fields."""
    result = build_memo_only_payload("Widget A\n https://example/order", approved)

    assert result == {
        "memo": "Widget A\n https://example/order",
        "approved": approved,
    }


def test_build_batch_memo_preserves_existing_memo() -> None:
    """Batch enrichment appends order context without losing an existing memo."""
    order = _batch_order()

    result = build_batch_memo(order, MemoGenerator(), "KEEP THIS NOTE")

    assert result is not None
    assert result.startswith("KEEP THIS NOTE")
    assert "Widget A" in result
    assert order.order_id is not None
    assert order.order_id in result


def test_build_batch_memo_is_idempotent() -> None:
    """Rebuilding a generated memo does not duplicate its order context."""
    order = _batch_order()
    first = build_batch_memo(order, MemoGenerator())
    assert first is not None

    second = build_batch_memo(order, MemoGenerator(), first)

    assert second == first


def test_build_batch_memo_refuses_to_truncate_existing_memo() -> None:
    """An existing memo is never shortened merely to add enrichment."""
    order = _batch_order()
    existing = "X" * 195

    assert build_batch_memo(order, MemoGenerator(), existing) is None


def _batch_txn(txn_id: str, amount: int) -> dict:
    return {
        "id": txn_id,
        "account_id": "a1",
        "date": "2024-01-01",
        "amount": amount,
        "payee_name": "Amazon",
        "category_id": None,
        "approved": False,
        "memo": "",
    }


def _batch_order(order_id: str = "702-1234567-7654321") -> Order:
    order = Order()
    order.order_id = order_id
    order.total = 20.00
    order.date_str = "January 1, 2024"
    order.items = ["Widget A"]
    return order


def test_process_batch_enriches_confident_match() -> None:
    """A confident match gets a memo-only update; category stays None."""
    client = Mock()
    enriched, skipped, failed = process_batch(
        [_batch_txn("t1", -20000)],
        [_batch_order()],
        MemoGenerator("amazon.com"),
        client,
    )

    assert (enriched, skipped, failed) == (1, 0, 0)
    client.update_transaction.assert_called_once()
    txn_id, payload = client.update_transaction.call_args[0]
    assert txn_id == "t1"
    assert "Widget A" in payload["memo"]
    assert set(payload) == {"memo", "approved"}


def test_process_batch_displays_matched_order_currency(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Batch transaction verification uses the matched order's currency."""
    order = _batch_order()
    order.currency = "€"

    result = process_batch(
        [_batch_txn("t1", -20000)],
        [order],
        MemoGenerator(),
        Mock(),
        dry_run=True,
    )

    assert result == (1, 0, 0)
    captured = capsys.readouterr().out
    assert "Amazon -€20.00" in captured
    assert "Amazon -$20.00" not in captured


def test_process_batch_skips_ambiguous() -> None:
    """Two same-amount orders are ambiguous, so nothing is enriched."""
    client = Mock()
    orders = [_batch_order("702-AAAAAAA-0000000"), _batch_order("702-BBBBBBB-0000000")]
    enriched, skipped, failed = process_batch(
        [_batch_txn("t1", -20000)], orders, MemoGenerator(), client
    )

    assert (enriched, skipped, failed) == (0, 1, 0)
    client.update_transaction.assert_not_called()


def test_process_batch_dry_run_no_api_call() -> None:
    """Dry-run counts the enrichment but sends nothing to YNAB."""
    client = Mock()
    enriched, skipped, failed = process_batch(
        [_batch_txn("t1", -20000)], [_batch_order()], MemoGenerator(), client, True
    )

    assert enriched == 1
    client.update_transaction.assert_not_called()


def test_process_batch_counts_failure() -> None:
    """A failed update is counted, not raised."""
    from ynab_amazon_categorizer.exceptions import YNABAPIError

    client = Mock()
    client.update_transaction.side_effect = YNABAPIError("boom", status_code=500)
    enriched, skipped, failed = process_batch(
        [_batch_txn("t1", -20000)], [_batch_order()], MemoGenerator(), client
    )

    assert (enriched, skipped, failed) == (0, 0, 1)


def test_process_batch_preserves_existing_memo() -> None:
    """The batch update sent to YNAB retains pre-existing memo content."""
    client = Mock()
    transaction = _batch_txn("t1", -20000)
    transaction["memo"] = "Imported reference 123"

    result = process_batch([transaction], [_batch_order()], MemoGenerator(), client)

    assert result == (1, 0, 0)
    payload = client.update_transaction.call_args.args[1]
    assert payload["memo"].startswith("Imported reference 123")
    assert set(payload) == {"memo", "approved"}
    assert payload["approved"] is False


def test_process_batch_skips_already_enriched_memo_and_consumes_order() -> None:
    """An idempotent rerun sends no update or reuses the matched order."""
    client = Mock()
    order = _batch_order()
    transaction = _batch_txn("t1", -20000)
    transaction["memo"] = build_batch_memo(order, MemoGenerator())

    result = process_batch(
        [transaction, _batch_txn("t2", -20000)],
        [order],
        MemoGenerator(),
        client,
    )

    assert result == (0, 2, 0)
    client.update_transaction.assert_not_called()


def test_process_batch_skips_when_existing_memo_cannot_be_preserved() -> None:
    """Batch mode skips rather than truncating a nearly-full existing memo."""
    client = Mock()
    transaction = _batch_txn("t1", -20000)
    transaction["memo"] = "X" * 195

    result = process_batch([transaction], [_batch_order()], MemoGenerator(), client)

    assert result == (0, 1, 0)
    client.update_transaction.assert_not_called()


def test_process_batch_oversized_memo_consumes_matched_order() -> None:
    """A too-long memo cannot make its order available to a later transaction."""
    client = Mock()
    transaction = _batch_txn("t1", -20000)
    transaction["memo"] = "X" * 195

    result = process_batch(
        [transaction, _batch_txn("t2", -20000)],
        [_batch_order()],
        MemoGenerator(),
        client,
    )

    assert result == (0, 2, 0)
    client.update_transaction.assert_not_called()


def test_main_batch_dry_run_smoke(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The top-level batch dry-run completes without sending an update."""
    config = Config("secret", "budget")
    client = Mock()
    client.get_categories.return_value = (
        [("Needs: Household", "cat1")],
        {"needs: household": "cat1"},
        {"cat1": "Needs: Household"},
    )
    transaction = _batch_txn("t1", -20000)

    monkeypatch.setattr(Config, "from_env", classmethod(lambda cls: config))
    monkeypatch.setattr(cli_module, "YNABClient", lambda *_args: client)
    monkeypatch.setattr(cli_module, "_prompt_line", lambda _message: "y")
    monkeypatch.setattr(
        cli_module, "prompt_for_amazon_orders_data", lambda: [_batch_order()]
    )
    monkeypatch.setattr(
        cli_module, "fetch_amazon_transactions", lambda *_args: [transaction]
    )

    exit_code = cli_module.main(["--batch", "--dry-run"])

    client.update_transaction.assert_not_called()
    assert exit_code == 0
    assert "Batch complete: 1 enriched" in capsys.readouterr().out


@pytest.mark.parametrize("interrupt", [KeyboardInterrupt(), EOFError()])
def test_main_handles_terminal_interruption(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    interrupt: BaseException,
) -> None:
    """Ctrl+C and EOF exit cleanly without exposing a traceback."""
    config = Config("secret", "budget")
    client = Mock()
    client.get_categories.return_value = (
        [("Needs: Household", "cat1")],
        {"needs: household": "cat1"},
        {"cat1": "Needs: Household"},
    )

    monkeypatch.setattr(Config, "from_env", classmethod(lambda cls: config))
    monkeypatch.setattr(cli_module, "YNABClient", lambda *_args: client)

    def interrupt_prompt(_message: str) -> str:
        raise interrupt

    monkeypatch.setattr(cli_module, "_prompt_line", interrupt_prompt)

    exit_code = cli_module.main([])

    assert exit_code == 130
    assert "Operation cancelled" in capsys.readouterr().out
