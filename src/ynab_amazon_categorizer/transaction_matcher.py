"""Transaction matching functionality."""

import logging
from collections.abc import Sequence
from datetime import datetime

from .amazon_parser import Order

logger = logging.getLogger(__name__)


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
    ) -> Order | None:
        """Find the best matching order for a transaction.

        Matching requires an exact amount match (within 1 cent).
        Ties are broken by date proximity, then by order ID for determinism.

        Orders whose ``order_id`` appears in ``used_order_ids`` are skipped so a
        single order is not matched to multiple transactions of the same amount.
        """
        if not parsed_orders:
            return None

        transaction_amount_abs = abs(transaction_amount)

        # Convert transaction date to comparable format
        try:
            trans_date = datetime.strptime(transaction_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            trans_date = None

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
            if trans_date and isinstance(order.date_str, str) and order.date_str:
                try:
                    order_date = datetime.strptime(order.date_str, "%B %d, %Y")
                    date_diff = abs((trans_date - order_date).days)
                    if date_diff <= 1:  # Same or next day
                        score += 30
                    elif date_diff <= 3:  # Within 3 days
                        score += 15
                    elif date_diff <= 7:  # Within a week
                        score += 5
                except (ValueError, TypeError):
                    pass

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

        try:
            trans_date: datetime | None = datetime.strptime(
                transaction_date, "%Y-%m-%d"
            )
        except (ValueError, TypeError):
            trans_date = None

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
        if trans_date and isinstance(order.date_str, str) and order.date_str:
            try:
                order_date = datetime.strptime(order.date_str, "%B %d, %Y")
                if abs((trans_date - order_date).days) > max_date_diff_days:
                    return None
            except (ValueError, TypeError):
                pass
        return order
