"""Memo generation functionality for Amazon order transactions."""

import re
from typing import Any

# YNAB memo field maximum length (API rejects longer values)
YNAB_MEMO_MAX_LENGTH = 200


def sanitize_memo(memo: str, max_length: int = YNAB_MEMO_MAX_LENGTH) -> str:
    """Sanitize a memo string for YNAB API submission.

    - Strips control characters (except newlines)
    - Truncates to ``max_length``, preserving an Amazon order link at the
      end when possible.
    """
    if not memo:
        return ""

    # Strip control characters except \n and \r
    memo = re.sub(r"[\x00-\x09\x0b\x0c\x0e-\x1f]", "", memo)
    memo = memo.strip()

    if len(memo) <= max_length:
        return memo

    # Try to preserve the order link at the end
    link_match = re.search(r"(https://www\.\S+)$", memo)
    if link_match:
        link = link_match.group(1)
        available = max_length - len(link) - 4  # 4 for "\n..\n"
        if available > 10:
            return memo[:available].rstrip() + "\n..\n" + link
    # Simple truncation with ellipsis
    return memo[: max_length - 3].rstrip() + "..."


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

        raw = "\n\n".join(memo_parts) if memo_parts else ""
        return sanitize_memo(raw)
