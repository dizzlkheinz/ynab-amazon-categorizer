"""Transaction matching functionality."""


class TransactionMatcher:
    """Matches Amazon orders with YNAB transactions."""

    def __init__(self) -> None:
        pass

    def find_matching_order(self, transaction_amount, transaction_date, parsed_orders):
        if not parsed_orders:
            return None

        for order in parsed_orders:
            if hasattr(order, "total") and order.total:
                amount_diff = abs(order.total - abs(transaction_amount))
                if amount_diff < 1.00:  # Match within $1.00
                    return order

        return None
