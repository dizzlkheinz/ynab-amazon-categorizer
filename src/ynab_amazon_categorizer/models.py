"""Typed domain models used across parsing, matching, and YNAB updates."""

from dataclasses import dataclass, field
from datetime import date
from typing import NotRequired, TypedDict, cast


@dataclass(slots=True)
class Order:
    """A parsed Amazon order.

    Optional scalar fields allow partially parsed orders to remain useful for
    matching while making their shape explicit and easy to construct in tests.
    """

    order_id: str | None = None
    total: float | None = None
    date_str: str | None = None
    items: list[str] = field(default_factory=list)
    currency: str | None = None


def format_currency_amount(amount: float | None, currency: str | None = None) -> str:
    """Format an amount with its parsed currency, defaulting legacy orders to dollars."""
    if amount is None:
        return "N/A"
    sign = "-" if amount < 0 else ""
    return f"{sign}{currency or '$'}{abs(amount):.2f}"


class YNABTransaction(TypedDict):
    """YNAB transaction fields consumed by this application."""

    id: str
    account_id: str
    date: str
    amount: int
    payee_id: NotRequired[str | None]
    payee_name: NotRequired[str | None]
    category_id: NotRequired[str | None]
    memo: NotRequired[str | None]
    cleared: NotRequired[str | None]
    approved: NotRequired[bool]
    flag_color: NotRequired[str | None]
    import_id: NotRequired[str | None]
    transfer_account_id: NotRequired[str | None]
    subtransactions: NotRequired[list[object]]


class SaveSubtransaction(TypedDict):
    """Fields accepted when creating a YNAB split subtransaction."""

    amount: int
    category_id: str
    memo: str | None


class TransactionUpdate(TypedDict, total=False):
    """Minimal set of fields intentionally changed in a YNAB update."""

    category_id: str | None
    memo: str
    approved: bool
    subtransactions: list[SaveSubtransaction]


def validate_ynab_transaction(value: object) -> YNABTransaction:
    """Validate the YNAB fields required by filtering and processing."""
    if not isinstance(value, dict):
        raise ValueError("expected an object")
    raw = cast(dict[str, object], value)

    for field_name in ("id", "account_id", "date"):
        field_value = raw.get(field_name)
        if not isinstance(field_value, str) or not field_value:
            raise ValueError(f"{field_name} must be a non-empty string")

    try:
        date.fromisoformat(cast(str, raw["date"]))
    except ValueError as exc:
        raise ValueError("date must use ISO YYYY-MM-DD format") from exc

    amount = raw.get("amount")
    if not isinstance(amount, int) or isinstance(amount, bool):
        raise ValueError("amount must be an integer number of milliunits")

    nullable_strings = (
        "payee_id",
        "payee_name",
        "category_id",
        "memo",
        "cleared",
        "flag_color",
        "import_id",
        "transfer_account_id",
    )
    for field_name in nullable_strings:
        field_value = raw.get(field_name)
        if field_value is not None and not isinstance(field_value, str):
            raise ValueError(f"{field_name} must be a string or null")

    approved = raw.get("approved")
    if approved is not None and not isinstance(approved, bool):
        raise ValueError("approved must be a boolean")

    subtransactions = raw.get("subtransactions")
    if subtransactions is not None and not isinstance(subtransactions, list):
        raise ValueError("subtransactions must be a list")

    return cast(YNABTransaction, raw)
