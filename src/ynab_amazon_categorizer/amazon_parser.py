"""Amazon order parsing functionality."""

import logging
import re
from datetime import datetime

from .models import Order

logger = logging.getLogger(__name__)

# Maximum items to extract per order (keeps memos manageable)
MAX_ITEMS_PER_ORDER = 10

ORDER_START_LABEL = r"(?:Order placed|Subscription charged on|Digital order placed)"
ORDER_DATE_PATTERN = r"(?:[A-Za-z]+ \d{1,2}, \d{4}|\d{1,2} [A-Za-z]+ \d{4})"
CURRENCY_PREFIX_PATTERN = r"(?:C(?:A|DN)\$|US\$|[$£€])"
ORDER_ID_PATTERN = r"(?:(?:\d{3}|D\d{2})-\d{7}-\d{7})"

ORDER_HEADER_PATTERN = re.compile(
    rf"{ORDER_START_LABEL}\s*"
    rf"(?P<date>{ORDER_DATE_PATTERN})\s*"
    rf"Total\s*(?P<currency>{CURRENCY_PREFIX_PATTERN})\s*"
    rf"(?P<total>[0-9][0-9,]*(?:\.[0-9]{{1,2}})?)\s*"
    rf".*?Order #\s*(?P<order_id>{ORDER_ID_PATTERN})",
    re.DOTALL | re.IGNORECASE,
)

ORDER_CONTENT_BOUNDARY_PATTERN = re.compile(
    rf"^\s*{ORDER_START_LABEL}\b",
    re.IGNORECASE | re.MULTILINE,
)

ORDER_TAIL_SENTINEL_PATTERN = re.compile(
    r"^\s*(?:"
    r"[←<]?\s*Previous\b.*|"
    r"Next\s*[→>]?\s*$|"
    r"Sponsored\s*$|"
    rf"Learn more[ \t]*(?:\r?\n)[ \t]*{CURRENCY_PREFIX_PATTERN}\s*\d|"
    r"Top .+ For You\s*$|"
    r"Get to Know Us\s*$|"
    r"Make Money with Us\s*$|"
    r"Amazon Payment Products\s*$|"
    r"Let Us Help You\s*$"
    r")",
    re.IGNORECASE | re.MULTILINE,
)


class AmazonParser:
    """Parses Amazon order data from order history pages."""

    def _remove_cancelled_orders(self, text: str) -> str:
        """Remove cancelled order blocks so their items don't bleed into adjacent orders."""
        parts = re.split(
            rf"(?=^\s*{ORDER_START_LABEL}\b)",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        kept = []
        for part in parts:
            if (
                re.match(rf"\s*{ORDER_START_LABEL}", part, re.IGNORECASE)
                and "your order was cancelled" in part.lower()
            ):
                continue
            kept.append(part)
        return "".join(kept)

    def _normalize_order_date(self, date_str: str) -> str:
        """Normalize supported English date layouts for the matcher."""
        for date_format in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y"):
            try:
                parsed = datetime.strptime(date_str, date_format)
                return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"
            except ValueError:
                continue
        return date_str

    def parse_orders_page(self, orders_text: str) -> list[Order]:
        """Parse Amazon orders page text to extract order information.

        Orders are kept even when item extraction fails (partial orders)
        so that amount/date matching can still work.
        """
        if not orders_text.strip():
            return []

        orders_text = self._remove_cancelled_orders(orders_text)

        orders = []

        order_matches = list(ORDER_HEADER_PATTERN.finditer(orders_text))

        for idx, match in enumerate(order_matches):
            order_date = self._normalize_order_date(match.group("date").strip())
            order_total = float(match.group("total").replace(",", ""))
            order_currency = match.group("currency")
            order_id = match.group("order_id")

            # Find the content after this order until the next order-like block or end
            start_pos = match.end()
            if idx + 1 < len(order_matches):
                end_pos = order_matches[idx + 1].start()
            else:
                end_pos = len(orders_text)
            end_pos = self._find_order_content_end(orders_text, start_pos, end_pos)
            order_content = orders_text[start_pos:end_pos]

            # Extract items from the order content
            items = self.extract_items_from_content(order_content)

            # Always keep the order even without items (partial order)
            order = Order(
                order_id=order_id,
                total=order_total,
                date_str=order_date,
                items=items,
                currency=order_currency,
            )

            if not items:
                logger.info(
                    "Order %s parsed without items (amount=%.2f). "
                    "It can still match by amount/date.",
                    order_id,
                    order_total,
                )

            orders.append(order)

        return orders

    def _find_order_content_end(
        self, orders_text: str, start_pos: int, default_end: int
    ) -> int:
        """Find the earliest unparsed order-like boundary before the default end."""
        boundary = ORDER_CONTENT_BOUNDARY_PATTERN.search(
            orders_text, start_pos, default_end
        )
        if boundary:
            return boundary.start()
        return default_end

    def _trim_footer(self, order_content: str) -> str:
        """Trim at page footer sentinels to avoid extracting navigation/legal boilerplate."""
        footer_sentinel = ORDER_TAIL_SENTINEL_PATTERN.search(order_content)
        if not footer_sentinel:
            footer_sentinel = re.search(
                r"©\s*\d{4}|To move between items",
                order_content,
                re.IGNORECASE,
            )
        if footer_sentinel:
            return order_content[: footer_sentinel.start()]
        return order_content

    def _get_valid_cleaned_item(self, line: str) -> str | None:
        """Check if a line matches product name criteria and return the cleaned string, or None."""
        line = line.strip()
        if not line or len(line) < 15:
            return None

        # Skip common UI elements and delivery status lines
        skip_patterns = [
            r"^(Buy it again|Track package|View|Return|Write|Get|Share|Leave|Ask)",
            r"^(Delivered|Arriving|Now arriving|Auto-delivered|Package was)",
            r"^(Return items:|Return or replace|Refund issued|Refund:|Returned)",
            r"^(Subscribe & Save|Subscribe now|Skip this delivery|Deliver every"
            r"|Change delivery|Manage subscription|Edit delivery|Set up now)",
            r"^\d+\.?\d* out of \d+ stars",
            r"^FREE|^Today by|^Get it|^List:|^Was:|^Limited-time deal",
            r"^\$\d+\.\d+|\(\$\d+\.\d+",
            r"^\d+ sustainability features?$",
            r"^[A-Z\s]+$",  # All caps lines (must be ONLY caps and spaces)
            r"^(Ship to|Order #|View order|Invoice)",
        ]

        if any(re.match(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
            return None

        # Look for product names - they usually contain specific patterns
        has_product_pattern = (
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
        )  # Long descriptive lines

        if not has_product_pattern:
            return None

        # Clean up the line
        cleaned_line = re.sub(r"\s+", " ", line)
        cleaned_line = re.sub(r"^[-•]\s*", "", cleaned_line)  # Remove bullet points

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
            "mastercard",
            "your brand",
            "registry & gift",
            "attract and engage",
            "interest-based",
        ]
        if any(word in cleaned_line.lower() for word in skip_words):
            return None

        return cleaned_line

    def _deduplicate_and_badge_filter(self, candidates: list[str]) -> list[str]:
        """Build lookup set to detect quantity-badge duplicates and keep up to MAX_ITEMS_PER_ORDER."""
        # Amazon shows "Product Name <qty>" and "Product Name" on adjacent lines when
        # qty > 1. We want to strip the badge only when the bare form also appears.
        candidate_set = set(candidates)
        seen: set[str] = set()
        unique_items: list[str] = []
        for item in candidates:
            stripped = re.sub(r"\s+\d+$", "", item)
            normalized = (
                stripped if (stripped != item and stripped in candidate_set) else item
            )
            if normalized not in seen and len(normalized) > 15:
                seen.add(normalized)
                unique_items.append(normalized)
                if len(unique_items) >= MAX_ITEMS_PER_ORDER:
                    break
        return unique_items

    def extract_items_from_content(self, order_content: str) -> list[str]:
        """Extract item names from order content."""
        order_content = self._trim_footer(order_content)

        candidates: list[str] = []
        for line in order_content.split("\n"):
            cleaned = self._get_valid_cleaned_item(line)
            if cleaned:
                candidates.append(cleaned)

        return self._deduplicate_and_badge_filter(candidates)
