"""Transaction matching functionality."""

from collections.abc import Sequence
from datetime import datetime

from .amazon_parser import Order


def _parse_transaction_date(date_str: str) -> datetime | None:
    """Parse transaction date in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _parse_order_date(date_str: str | None) -> datetime | None:
    """Parse order date in 'Month DD, YYYY' format."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%B %d, %Y")
    except (ValueError, TypeError):
        return None


class TransactionMatcher:
    """Matches Amazon orders with YNAB transactions."""

    def __init__(self) -> None:
        pass

    def find_matching_order(
        self,
        transaction_amount: float,
        transaction_date: str,
        parsed_orders: Sequence[Order],
        used_order_ids: set[str] | None = None,
        max_date_diff_days: int = 14,
    ) -> Order | None:
        """Find the best matching order for a transaction.

        Matching requires an exact amount match (within 1 cent) and, when both
        dates are parseable, a date within ``max_date_diff_days``.
        Ties are broken by date proximity, then by order ID for determinism.

        Orders whose ``order_id`` appears in ``used_order_ids`` are skipped so a
        single order is not matched to multiple transactions of the same amount.
        """
        if not parsed_orders:
            return None

        transaction_amount_abs = abs(transaction_amount)
        trans_date = _parse_transaction_date(transaction_date)

        best_match: Order | None = None
        best_score = 0
        best_date_diff: int | None = None
        best_order_id: str = ""

        for order in parsed_orders:
            if order.total is None:
                continue

            if (
                used_order_ids
                and order.order_id is not None
                and order.order_id in used_order_ids
            ):
                continue

            amount_diff = abs(order.total - transaction_amount_abs)
            if amount_diff >= 0.01:
                continue

            score = 100
            date_diff: int | None = None

            # Check date proximity
            if trans_date:
                order_date = _parse_order_date(order.date_str)
                if order_date:
                    date_diff = abs((trans_date - order_date).days)
                    if date_diff > max_date_diff_days:
                        continue
                    if date_diff <= 1:  # Same or next day
                        score += 30
                    elif date_diff <= 3:  # Within 3 days
                        score += 15
                    elif date_diff <= 7:  # Within a week
                        score += 5

            order_id = order.order_id or ""

            # Deterministic tie-breaking: score > date_diff (lower wins) > order_id
            is_better = False
            if score > best_score:
                is_better = True
            elif score == best_score:
                # Tie on score: prefer closer date
                if date_diff is not None and (
                    best_date_diff is None or date_diff < best_date_diff
                ):
                    is_better = True
                elif date_diff == best_date_diff:
                    # Tie on date too: use order_id as stable key
                    if order_id < best_order_id:
                        is_better = True

            if is_better:
                best_score = score
                best_match = order
                best_date_diff = date_diff
                best_order_id = order_id

        return best_match

    def find_confident_match(
        self,
        transaction_amount: float,
        transaction_date: str,
        parsed_orders: Sequence[Order],
        used_order_ids: set[str] | None = None,
        max_date_diff_days: int = 7,
    ) -> Order | None:
        """Return an order only when the match is unambiguous (for batch use).

        Unlike ``find_matching_order``, this requires *exactly one* unused order
        matching the amount (within 1 cent). If that order has a parseable date
        it must be within ``max_date_diff_days`` of the transaction. Any
        ambiguity (zero or multiple amount matches, or a far-off date) returns
        ``None`` so batch mode never auto-applies a guess.
        """
        amount_abs = abs(transaction_amount)
        trans_date = _parse_transaction_date(transaction_date)

        candidates: list[Order] = []
        for order in parsed_orders:
            if order.total is None:
                continue
            if (
                used_order_ids
                and order.order_id is not None
                and order.order_id in used_order_ids
            ):
                continue
            if abs(order.total - amount_abs) >= 0.01:
                continue
            candidates.append(order)

        if len(candidates) != 1:
            return None

        order = candidates[0]
        if trans_date:
            order_date = _parse_order_date(order.date_str)
            if order_date:
                if abs((trans_date - order_date).days) > max_date_diff_days:
                    return None
        return order
