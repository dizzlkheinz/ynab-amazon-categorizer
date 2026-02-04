"""Transaction matching functionality."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from .amazon_parser import Order


class TransactionMatcher:
    """Matches Amazon orders with YNAB transactions."""

    def __init__(self) -> None:
        pass

    def find_matching_order(
        self,
        transaction_amount: float,
        transaction_date: str,
        parsed_orders: Sequence[Order | dict[str, Any]],
    ) -> Order | dict[str, Any] | None:
        """Find the best matching order for a transaction.

        Matching requires an exact amount match (within 1 cent).
        Date is used only as a tie-breaker between exact-amount matches.
        """
        if not parsed_orders:
            return None

        transaction_amount_abs = abs(transaction_amount)

        # Convert transaction date to comparable format
        try:
            trans_date = datetime.strptime(transaction_date, "%Y-%m-%d")
        except Exception:
            trans_date = None

        best_match = None
        best_score = 0

        for order in parsed_orders:
            score = 0

            # Check amount match (required) - handle both object and dict formats
            order_total = None
            if hasattr(order, "total"):
                order_total = order.total
            elif isinstance(order, dict) and "total" in order:
                order_total = order["total"]

            if order_total is None:
                continue

            amount_diff = abs(order_total - transaction_amount_abs)
            if amount_diff >= 0.01:
                continue

            score += 100

            # Check date proximity - handle both object and dict formats
            order_date_str = None
            if hasattr(order, "date_str"):
                order_date_str = order.date_str
            elif isinstance(order, dict) and "date" in order:
                order_date_str = order["date"]

            if trans_date and isinstance(order_date_str, str) and order_date_str:
                try:
                    # Parse order date (format like "July 31, 2025")
                    order_date = datetime.strptime(order_date_str, "%B %d, %Y")
                    date_diff = abs((trans_date - order_date).days)
                    if date_diff <= 1:  # Same or next day
                        score += 30
                    elif date_diff <= 3:  # Within 3 days
                        score += 15
                    elif date_diff <= 7:  # Within a week
                        score += 5
                except Exception:
                    pass

            if score > best_score:
                best_score = score
                best_match = order

        return best_match
