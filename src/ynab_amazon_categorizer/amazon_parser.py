"""Amazon order parsing functionality."""
import re


class Order:
    """Represents a parsed Amazon order."""
    def __init__(self):
        self.order_id = None
        self.total = None
        self.date_str = None
        self.items = []


class AmazonParser:
    """Parses Amazon order data from order history pages."""

    def parse_orders_page(self, orders_text: str) -> list:
        """Parse Amazon orders page text to extract order information"""
        if not orders_text.strip():
            return []

        orders = []

        # Find all order blocks using regex
        order_pattern = r"Order placed\s*([A-Za-z]+ \d+, \d{4})\s*Total\s*\$(\d+\.?\d*)\s*.*?Order # (\d{3}-\d{7}-\d{7})"
        order_matches = re.finditer(order_pattern, orders_text, re.DOTALL | re.IGNORECASE)

        for match in order_matches:
            order_date = match.group(1).strip()
            order_total = float(match.group(2))
            order_id = match.group(3)

            # Find the content after this order until the next order or end
            start_pos = match.end()
            next_order = re.search(r"Order placed", orders_text[start_pos:], re.IGNORECASE)
            if next_order:
                end_pos = start_pos + next_order.start()
                order_content = orders_text[start_pos:end_pos]
            else:
                order_content = orders_text[
                    start_pos : start_pos + 2000
                ]  # Take next 2000 chars

            # Extract items from the order content
            items = self.extract_items_from_content(order_content)

            if items:  # Only add orders that have identifiable items
                order = Order()
                order.order_id = order_id
                order.total = order_total
                order.date_str = order_date
                order.items = items
                orders.append(order)

        return orders

    def extract_items_from_content(self, order_content):
        """Extract item names from order content."""
        items = []
        lines = order_content.split("\n")

        for line in lines:
            line = line.strip()
            if not line or len(line) < 20:
                continue

            # Skip common UI elements
            skip_patterns = [
                r"^(Buy it again|Track package|View|Return|Write|Get|Share|Leave|Ask)",
                r"^(Delivered|Arriving|Auto-delivered|Package was)",
                r"^(Return items:|Return or replace)",
                r"^\d+\.?\d* out of \d+ stars",
                r"^FREE|^Today by|^Get it|^List:|^Was:|^Limited-time deal",
                r"^\$\d+\.\d+|\(\$\d+\.\d+",
                r"^\d+ sustainability features?$",
                r"^[A-Z\s]+$",  # All caps lines (must be ONLY caps and spaces)
                r"^(Ship to|Order #|View order|Invoice)",
            ]

            if any(re.match(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
                continue

            # Look for product names - they usually contain specific patterns
            if (
                any(
                    word in line.lower()
                    for word in [
                        "pack",
                        "count",
                        "size",
                        "oz",
                        "ml",
                        "lbs",
                        "kg",
                        "inch",
                        "cm",
                    ]
                )
                or re.search(
                    r"[A-Z][a-z].*[A-Z]", line
                )  # Mixed case indicating product names
                or len(line.split()) >= 5
            ):  # Long descriptive lines
                # Clean up the line
                cleaned_line = re.sub(r"\s+", " ", line)
                cleaned_line = re.sub(
                    r"^[-•]\s*", "", cleaned_line
                )  # Remove bullet points

                # Skip if it looks like navigation or common elements
                skip_words = [
                    "account",
                    "orders",
                    "cart",
                    "search",
                    "hello",
                    "browse",
                    "prime",
                    "shipping",
                ]
                if not any(word in cleaned_line.lower() for word in skip_words):
                    items.append(cleaned_line)

        # Remove duplicates and limit items
        seen = set()
        unique_items = []
        for item in items:
            if item not in seen and len(item) > 15:  # Only keep substantial items
                seen.add(item)
                unique_items.append(item)
                if len(unique_items) >= 3:  # Limit to 3 items
                    break

        return unique_items
