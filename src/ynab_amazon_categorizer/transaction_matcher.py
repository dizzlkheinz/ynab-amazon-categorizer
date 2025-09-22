"""Transaction matching functionality."""
from datetime import datetime


class TransactionMatcher:
    """Matches Amazon orders with YNAB transactions."""

    def __init__(self) -> None:
        pass

    def find_matching_order(self, transaction_amount, transaction_date, parsed_orders):
        """Find the best matching order for a transaction using sophisticated scoring"""
        if not parsed_orders:
            return None

        transaction_amount_abs = abs(transaction_amount)

        # Convert transaction date to comparable format
        try:
            trans_date = datetime.strptime(transaction_date, "%Y-%m-%d")
        except:
            trans_date = None

        best_match = None
        best_score = 0

        for order in parsed_orders:
            score = 0

            # Check amount match (most important) - handle both object and dict formats
            order_total = None
            if hasattr(order, "total"):
                order_total = order.total
            elif isinstance(order, dict) and "total" in order:
                order_total = order["total"]

            if order_total:
                amount_diff = abs(order_total - transaction_amount_abs)
                if amount_diff < 0.01:  # Exact match
                    score += 100
                elif amount_diff < 1.00:  # Close match
                    score += 50
                elif amount_diff < 5.00:  # Reasonable match
                    score += 20

            # Check date proximity - handle both object and dict formats
            order_date_str = None
            if hasattr(order, "date_str"):
                order_date_str = order.date_str
            elif isinstance(order, dict) and "date" in order:
                order_date_str = order["date"]

            if trans_date and order_date_str:
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
                except:
                    pass

            if score > best_score:
                best_score = score
                best_match = order

        # Only return match if score is reasonable and includes some amount matching
        # Date alone should not be sufficient - need at least some amount proximity
        has_amount_score = False
        if best_match:
            # Re-check if the best match has any amount scoring
            order_total = None
            if hasattr(best_match, "total"):
                order_total = best_match.total
            elif isinstance(best_match, dict) and "total" in best_match:
                order_total = best_match["total"]

            if order_total:
                amount_diff = abs(order_total - transaction_amount_abs)
                if amount_diff < 5.00:  # Must be within $5 for any match
                    has_amount_score = True

        return best_match if best_score >= 20 and has_amount_score else None
