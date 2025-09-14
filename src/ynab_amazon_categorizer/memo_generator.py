"""Memo generation functionality for Amazon order transactions."""


class MemoGenerator:
    """Handles memo generation for Amazon transactions."""

    def __init__(self):
        pass

    def generate_amazon_order_link(self, order_id):
        """Generate Amazon.ca order details link"""
        if order_id:
            return f"https://www.amazon.ca/gp/your-account/order-details?ie=UTF8&orderID={order_id}"
        return None

    def generate_enhanced_memo(self, original_memo, order_id, item_details=None):
        """Generate enhanced memo with order information and item details"""
        # Minimal implementation to pass the test
        order_link = self.generate_amazon_order_link(order_id)
        if order_link:
            return f"{original_memo}\n\nAmazon Order: {order_link}"
        return original_memo
