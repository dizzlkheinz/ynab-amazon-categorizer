"""Memo generation functionality for Amazon order transactions."""

from typing import Any


class MemoGenerator:
    """Handles memo generation for Amazon transactions."""

    def __init__(self, amazon_domain: str = "amazon.ca") -> None:
        self.amazon_domain = amazon_domain

    def generate_amazon_order_link(self, order_id: str | None) -> str | None:
        """Generate Amazon order details link"""
        if order_id:
            return f"https://www.{self.amazon_domain}/gp/your-account/order-details?ie=UTF8&orderID={order_id}"
        return None

    def generate_enhanced_memo(
        self,
        original_memo: str,
        order_id: str | None,
        item_details: Any | None = None,
    ) -> str:
        """Generate enhanced memo with order information and item details"""
        memo_parts = []
        if original_memo:
            memo_parts.append(original_memo)

        if item_details:
            if isinstance(item_details, dict):
                title = item_details.get("title")
                quantity = item_details.get("quantity")
                price = item_details.get("price")

                details_str = ""
                if title:
                    details_str += str(title)
                if quantity and int(quantity) > 1:
                    details_str += f" (x{quantity})"
                if price:
                    details_str += f" - ${float(price):.2f}"

                if details_str:
                    memo_parts.append(details_str)
            elif isinstance(item_details, str):
                memo_parts.append(item_details)

        order_link = self.generate_amazon_order_link(order_id)
        if order_link:
            memo_parts.append(f"Amazon Order: {order_link}")

        return "\n\n".join(memo_parts) if memo_parts else ""
