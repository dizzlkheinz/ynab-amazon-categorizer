"""Amazon order parsing functionality."""

import logging
import re

logger = logging.getLogger(__name__)

# Maximum items to extract per order (keeps memos manageable)
MAX_ITEMS_PER_ORDER = 10

ORDER_CONTENT_BOUNDARY_PATTERN = re.compile(
    r"^\s*(?:Order placed|Subscription charged on|Digital order placed)\b",
    re.IGNORECASE | re.MULTILINE,
)

ORDER_TAIL_SENTINEL_PATTERN = re.compile(
    r"^\s*(?:"
    r"[←<]?\s*Previous\b.*|"
    r"Next set of slides\b.*|"
    r"Next\s*[→>]?\s*$|"
    r"Sponsored\s*$|"
    r"Learn more[ \t]*(?:\r?\n)[ \t]*\$\d|"
    r"Top .+ For You\s*$|"
    r"Customers who (?:viewed|bought)\b.*|"
    r"Continue series you\b.*|"
    r"Your Browsing History\b.*|"
    r"Back to top\b.*|"
    r"Get to Know Us\s*$|"
    r"Make Money with Us\s*$|"
    r"Amazon Payment Products\s*$|"
    r"Let Us Help You\s*$"
    r")",
    re.IGNORECASE | re.MULTILINE,
)

# Sanity cap for a detected quantity badge (see _deduplicate_and_badge_filter).
# Above this, a trailing number is more likely a coincidental part of the
# title (e.g. a model number) than a genuine "you bought N of these" badge.
MAX_REASONABLE_BADGE_QTY = 12


def _normalize_markdown_text(text: str) -> str:
    """Strip markdown-link and bullet-marker syntax from a full page of text.

    Some order-history copies (e.g. from a markdown-rendering copy tool)
    wrap every line as "* [Visible Text](https://...)". Left as-is, this
    breaks the order-header regex below (a "* " bullet in front of "TOTAL"
    or "ORDER #" stops the \\s*-only gaps in that pattern from matching
    through it) as well as per-item extraction (skip_patterns are anchored
    to the start of the line, so a leading "* [" hides "Buy it again",
    "View", etc., and the raw URL would otherwise get glued onto extracted
    item text). Applied once up front so every downstream check — the order
    header, cancelled-order detection, and item extraction — sees plain text.
    """
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1 ", text)  # [text](url) -> text
    text = re.sub(r"(?m)^[ \t]*[-•*]\s*", "", text)  # leading bullet markers
    return text


# Amazon sometimes emits an image's alt-text line and the product-link text
# for the *same* item as two separate lines that are reworded/reordered
# rather than character-for-character identical (e.g. "Soft Pink" vs.
# "Soft Fashion Pink", clauses in a different order). A plain string-equality
# or quantity-badge check won't catch that, so near-duplicates are detected
# by token overlap (order-independent) instead. Threshold picked from real
# examples: true alt-text/title pairs for the same item score ~0.85-0.95;
# genuinely different items (even same brand) score well under 0.3.
NEAR_DUPLICATE_JACCARD_THRESHOLD = 0.7

# Real alt-text/title pairs can score as low as ~0.6 (well within range of a
# genuinely different same-brand item's title, e.g. two different sizes of
# the same listing) — text similarity alone can't cleanly separate the two
# cases. But there's a reliable structural marker: in real order-history
# copies, an item's image alt-text line has a leading space, and the
# following (unindented) title-link line for the *same* item never does.
# When that pattern is present, this much lower floor is enough — it's only
# there to rule out two unrelated lines that coincidentally landed adjacent.
ADJACENT_DUPLICATE_JACCARD_FLOOR = 0.3


def _item_token_set(text: str) -> set[str]:
    """Lowercased alphanumeric tokens of an item line, for similarity checks."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _differs_only_numerically(a: str, b: str) -> bool:
    """True if the only tokens that differ between two lines are pure numbers.

    e.g. "...Bourbon, 38" vs. "...Bourbon, 36" — that's the "same listing,
    different size/quantity/model number" case, a real separate line item,
    not a reworded repeat of the same one, regardless of how similar the
    rest of the text is or whether the two lines are structurally adjacent.
    """
    tokens_a, tokens_b = _item_token_set(a), _item_token_set(b)
    differing_tokens = tokens_a.symmetric_difference(tokens_b)
    return bool(differing_tokens) and all(t.isdigit() for t in differing_tokens)


def _token_overlap(a: str, b: str) -> float:
    """Jaccard similarity of two lines' token sets. 0 if either has no tokens."""
    tokens_a, tokens_b = _item_token_set(a), _item_token_set(b)
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _is_duplicate_item_pair(
    prev_item: str, prev_had_leading_space: bool, item: str, had_leading_space: bool
) -> bool:
    """True if `item` is a reworded repeat of the immediately preceding kept item.

    Prefers the structural signal (leading-space alt-text line immediately
    followed by a non-indented title line) when present, since it reliably
    separates true duplicates from genuinely different same-brand items in a
    way text similarity alone cannot (real examples overlap: a true
    duplicate can score lower than a real distinct-size variant). Falls back
    to the plain similarity check otherwise.
    """
    if _differs_only_numerically(prev_item, item):
        return False
    if prev_had_leading_space and not had_leading_space:
        return _token_overlap(prev_item, item) >= ADJACENT_DUPLICATE_JACCARD_FLOOR
    return _token_overlap(prev_item, item) >= NEAR_DUPLICATE_JACCARD_THRESHOLD


class Order:
    """Represents a parsed Amazon order."""

    def __init__(self) -> None:
        self.order_id: str | None = None
        self.total: float | None = None
        self.date_str: str | None = None
        self.items: list[str] = []


class AmazonParser:
    """Parses Amazon order data from order history pages."""

    def _remove_cancelled_orders(self, text: str) -> str:
        """Remove cancelled order blocks so their items don't bleed into adjacent orders."""
        parts = re.split(r"(?=Order placed)", text, flags=re.IGNORECASE)
        kept = []
        for part in parts:
            if (
                re.match(r"\s*Order placed", part, re.IGNORECASE)
                and "your order was cancelled" in part.lower()
            ):
                continue
            kept.append(part)
        return "".join(kept)

    def parse_orders_page(self, orders_text: str) -> list[Order]:
        """Parse Amazon orders page text to extract order information.

        Orders are kept even when item extraction fails (partial orders)
        so that amount/date matching can still work.
        """
        if not orders_text.strip():
            return []

        orders_text = _normalize_markdown_text(orders_text)

        orders_text = self._remove_cancelled_orders(orders_text)

        orders = []

        # Find all order blocks using regex
        order_pattern = r"Order placed\s*([A-Za-z]+ \d+, \d{4})\s*Total\s*\$([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*.*?Order # (\d{3}-\d{7}-\d{7})"
        order_matches = list(
            re.finditer(order_pattern, orders_text, re.DOTALL | re.IGNORECASE)
        )

        for idx, match in enumerate(order_matches):
            order_date = match.group(1).strip()
            order_total = float(match.group(2).replace(",", ""))
            order_id = match.group(3)

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
            order = Order()
            order.order_id = order_id
            order.total = order_total
            order.date_str = order_date
            order.items = items

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
        """Trim at the earliest footer/recommendation-carousel sentinel.

        A full page copy includes real order content first, then Amazon's
        "recommended for you" carousels, "continue reading" carousels,
        browsing history, and the site-wide footer nav — all of which are
        long, mixed-case, multi-word lines that would otherwise pass the
        product-name heuristics below. Cutting at the *first* sentinel found
        (rather than only the copyright line at the very end) removes all of
        that in one go, since none of it is genuine order content.
        """
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

        # Normalize markdown link formatting before any other checks. Some
        # order-history copies (e.g. from a markdown-rendering copy tool)
        # wrap every line as "* [Visible Text](https://...)". Left as-is,
        # the leading "* [" defeats the line-start-anchored skip_patterns
        # below (e.g. "* [Buy it again](...)" no longer starts with "Buy it
        # again"), and the raw URL would otherwise get glued onto extracted
        # item text.
        line = re.sub(r"^[-•*]\s*", "", line)  # leading bullet marker
        line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1 ", line)  # [text](url) -> text
        line = re.sub(r"\s+", " ", line).strip()
        if not line or len(line) < 15:
            return None

        # Skip common UI elements and delivery status lines
        skip_patterns = [
            r"^(Buy it again|Track package|View|Return|Write|Get|Share|Leave|Ask)\b",
            r"^(Delivered|Arriving|Now arriving|Auto-delivered|Package was)",
            r"^(Your package|Your order|Your item|Your shipment|Your refund"
            r"|Your replacement)\b",
            r"^(Return items:|Return or replace|Refund issued|Refund:|Returned"
            r"|Return started)",
            r"^(Subscribe & Save|Subscribe now|Skip this delivery|Deliver every"
            r"|Change delivery|Manage subscription|Edit delivery|Set up now)",
            r"^\d+\.?\d* out of \d+ stars",
            r"^FREE|^Today by|^Get it|^List:|^Was:|^Limited-time deal",
            r"^\$\d+\.\d+|\(\$\d+\.\d+",
            r"^\d+ sustainability features?$",
            r"^(Ship to|Order #|View order|Invoice)",
        ]

        if any(re.match(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
            return None

        # All-caps lines (e.g. shouty UI labels) are skipped too, but this
        # check must stay case-sensitive — matched under the shared
        # re.IGNORECASE above, "[A-Z]" would also match lowercase letters and
        # wrongly reject any ordinary product title made up of only letters
        # and spaces (no digits/punctuation).
        if re.match(r"^[A-Z\s]+$", line):
            return None

        # Look for product names - they usually contain specific patterns
        has_product_pattern = (
            any(
                re.search(rf"\b{re.escape(word)}\b", line, re.IGNORECASE)
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

        # Whitespace/bullet normalization already happened above.
        cleaned_line = line

        # Skip if it looks like navigation or common elements. Word-boundary
        # matched (not plain substring) so single words like "cart" or
        # "prime" don't false-positive inside real product words — "cart"
        # is a substring of "Carton"/"Cartridge", "prime" of "Primer",
        # "orders" of "Recorders"/"Borders", etc.
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
        if any(
            re.search(rf"\b{re.escape(word)}\b", cleaned_line, re.IGNORECASE)
            for word in skip_words
        ):
            return None

        return cleaned_line

    def _deduplicate_and_badge_filter(
        self, candidates: list[tuple[str, bool]]
    ) -> list[str]:
        """Resolve quantity-badge duplicates and drop (near-)duplicate lines.

        ``candidates`` pairs each cleaned line with whether its *raw* source
        line had leading whitespace — see _is_duplicate_item_pair for why
        that matters. Keeps up to MAX_ITEMS_PER_ORDER entries.
        """
        # Amazon shows "Product Name <qty>" and "Product Name" on adjacent lines when
        # qty > 1. Rather than collapsing that pair to a single entry (which would
        # hide the fact that 2+ units were bought and make it impossible to split
        # them into separate line items later), the bare name is repeated once per
        # unit — capped at MAX_REASONABLE_BADGE_QTY so a coincidental trailing
        # number that isn't really a quantity (e.g. part of a model number)
        # doesn't blow up the item list.
        candidate_texts = {text for text, _ in candidates}
        seen: set[str] = set()
        unique_items: list[str] = []
        last_kept_had_leading_space = False

        for item, had_leading_space in candidates:
            badge_match = re.search(r"\s+(\d+)$", item)
            stripped = item[: badge_match.start()] if badge_match else item
            is_badge = bool(
                badge_match and stripped != item and stripped in candidate_texts
            )
            normalized = stripped if is_badge else item

            if normalized in seen or len(normalized) <= 15:
                continue
            # Skip a reworded/reordered repeat of the item we *just* kept
            # (e.g. an image alt-text line immediately followed by the
            # product-link text for the same item) rather than treating it
            # as a second, different item.
            if unique_items and _is_duplicate_item_pair(
                unique_items[-1],
                last_kept_had_leading_space,
                normalized,
                had_leading_space,
            ):
                continue

            seen.add(normalized)
            qty = int(badge_match.group(1)) if is_badge else 1
            if qty < 1 or qty > MAX_REASONABLE_BADGE_QTY:
                qty = 1
            for _ in range(qty):
                if len(unique_items) >= MAX_ITEMS_PER_ORDER:
                    break
                unique_items.append(normalized)
            last_kept_had_leading_space = had_leading_space
            if len(unique_items) >= MAX_ITEMS_PER_ORDER:
                break
        return unique_items

    def extract_items_from_content(self, order_content: str) -> list[str]:
        """Extract item names from order content."""
        order_content = self._trim_footer(order_content)

        candidates: list[tuple[str, bool]] = []
        for line in order_content.split("\n"):
            had_leading_space = line[:1].isspace() if line else False
            cleaned = self._get_valid_cleaned_item(line)
            if cleaned:
                candidates.append((cleaned, had_leading_space))

        return self._deduplicate_and_badge_filter(candidates)
