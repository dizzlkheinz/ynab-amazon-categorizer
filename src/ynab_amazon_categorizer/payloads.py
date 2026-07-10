"""Construction of minimal, intentional YNAB transaction updates."""

from .memo_generator import generate_split_summary_memo, sanitize_memo
from .models import Order, SaveSubtransaction, TransactionUpdate


def build_single_payload(
    category_id: str,
    memo: str,
) -> TransactionUpdate:
    """Build an update for category, memo, and approval only."""
    return {
        "category_id": category_id,
        "memo": sanitize_memo(memo),
        "approved": True,
    }


def build_memo_only_payload(memo: str, approved: bool) -> TransactionUpdate:
    """Build a memo update while preserving YNAB's non-optional approval state."""
    return {"memo": sanitize_memo(memo), "approved": approved}


def build_split_payload(
    subtransactions: list[SaveSubtransaction],
    matching_order: Order | None,
    original_memo: str,
) -> TransactionUpdate:
    """Build a minimal update that converts a transaction into a split."""
    memo = (
        generate_split_summary_memo(matching_order)
        if matching_order
        else sanitize_memo(original_memo)
    )
    return {
        "category_id": None,
        "memo": memo,
        "approved": True,
        "subtransactions": subtransactions,
    }
