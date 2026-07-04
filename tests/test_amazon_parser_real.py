"""Tests for real Amazon order parsing functionality."""

from ynab_amazon_categorizer.amazon_parser import AmazonParser


def test_parse_actual_amazon_order_format() -> None:
    """Test parsing an actual Amazon order format."""
    order_text = """
    Order placed July 31, 2024
    Total $57.57
    Order # 702-8237239-1234567

    Fancy Feast Grilled Wet Cat Food, Tuna Feast - 85 g Can (24 Pack)
    $25.99

    USB-C Cable, 6ft Fast Charging Cable
    $31.58
    """

    parser = AmazonParser()
    orders = parser.parse_orders_page(order_text)

    assert len(orders) == 1
    order = orders[0]
    assert order.order_id == "702-8237239-1234567"
    assert order.total == 57.57
    assert order.date_str == "July 31, 2024"
    assert len(order.items) >= 1
    assert "Fancy Feast" in str(order.items)


def test_parse_different_order() -> None:
    """Test parsing a different order to force real parsing."""
    order_text = """
    Order placed August 15, 2024
    Total $89.99
    Order # 702-1234567-9876543

    Wireless Bluetooth Headphones - Over-Ear Noise Cancelling
    """

    parser = AmazonParser()
    orders = parser.parse_orders_page(order_text)

    assert len(orders) == 1
    order = orders[0]
    assert order.order_id == "702-1234567-9876543"
    assert order.total == 89.99
    assert order.date_str == "August 15, 2024"


def test_parse_subscribe_and_save_order() -> None:
    """Subscribe & Save delivery-management lines must not leak into items."""
    order_text = """
    Order placed February 3, 2025
    Total $42.18
    Ship to Jane Doe
    Order # 113-7654321-1234567
    View order details Invoice

    Subscribe & Save
    Deliver every 2 months
    Skip this delivery
    Manage subscription
    Bounty Quick-Size Paper Towels, White, 8 Family Rolls = 20 Regular Rolls
    Buy it again
    Track package
    """

    parser = AmazonParser()
    orders = parser.parse_orders_page(order_text)

    assert len(orders) == 1
    order = orders[0]
    assert order.order_id == "113-7654321-1234567"
    assert order.total == 42.18
    assert len(order.items) == 1
    assert "Bounty" in order.items[0]
    for noise in ["Subscribe", "Deliver every", "Skip this", "Manage subscription"]:
        assert not any(noise.lower() in item.lower() for item in order.items), (
            f"Subscription UI line '{noise}' leaked into items"
        )


def test_parse_returned_order_items_survive() -> None:
    """A returned/refunded order still parses, with refund status lines skipped."""
    order_text = """
    Order placed November 20, 2024
    Total $64.99
    Order # 702-9999999-1111111
    View order details Invoice

    Refund issued
    Returned: Refund of $64.99 issued
    Logitech MX Master 3S Wireless Performance Mouse, Ergonomic Design
    Buy it again
    Return or replace items
    """

    parser = AmazonParser()
    orders = parser.parse_orders_page(order_text)

    assert len(orders) == 1
    order = orders[0]
    assert order.total == 64.99
    assert len(order.items) == 1
    assert "Logitech" in order.items[0]
    assert not any("refund" in item.lower() for item in order.items)


def test_parse_digital_order_is_known_gap() -> None:
    """KNOWN LIMITATION (guard, not desired behaviour): digital order numbers use a
    ``D01-`` style prefix that the physical-order regex (``\\d{3}-\\d{7}-\\d{7}``) does
    not match, so digital orders are currently skipped rather than mis-parsed.

    If the parser is later taught to handle digital orders, update this test to
    assert the title is extracted instead of expecting an empty result.
    """
    order_text = """
    Order placed December 1, 2024
    Total $14.99
    Order # D01-2345678-9012345
    Your digital order

    The Pragmatic Programmer: Your Journey to Mastery (Kindle Edition)
    """

    parser = AmazonParser()
    orders = parser.parse_orders_page(order_text)

    # Documents current behaviour: no false match (no crash, no wrong order).
    assert orders == []


def test_parse_multi_order_page_mixed_layouts() -> None:
    """A realistic page with several orders parses each independently."""
    order_text = """
    Order placed March 1, 2025
    Total $19.99
    Order # 702-1000000-1000000
    View order details Invoice
    Delivered March 3, 2025
    Hydro Flask Standard Mouth Water Bottle with Flex Cap, 21 oz
    Buy it again

    Order placed March 5, 2025
    Total $120.00
    Order # 702-2000000-2000000
    Arriving tomorrow
    Anker 737 Power Bank (PowerCore 24K), 140W Portable Charger
    Anker 737 Power Bank (PowerCore 24K), 140W Portable Charger
    Track package

    Order placed March 9, 2025
    Total $7.49
    Order # 702-3000000-3000000
    short
    """

    parser = AmazonParser()
    orders = parser.parse_orders_page(order_text)

    assert len(orders) == 3
    assert [o.order_id for o in orders] == [
        "702-1000000-1000000",
        "702-2000000-2000000",
        "702-3000000-3000000",
    ]
    assert "Hydro Flask" in " ".join(orders[0].items)
    # Duplicate (badge) lines collapse to a single item.
    assert len(orders[1].items) == 1
    assert "Anker" in orders[1].items[0]
    # Third order has no parseable item but is still kept for amount matching.
    assert orders[2].items == []
    assert orders[2].total == 7.49


def test_recommendation_carousel_and_footer_not_extracted_as_items() -> None:
    """A full-page copy includes recommendation carousels and the site footer
    after the real order content. These must be trimmed entirely, not just
    the copyright line at the very end — real example: an order's item list
    picked up 'Self-Publish with Us', 'Groceries & More', and other footer
    nav text because only the final copyright line was used as a cutoff.
    """
    order_text = """Order placed
June 26, 2026
Total
$62.12
Order # 112-1234567-1234567
View order details   View invoice

Delivered July 2
Your package was left near the front door or porch.
 SANDISK 128GB MAX Endurance microSDXC Card with Adapter for Home Security Cameras and Dash cams
SANDISK 128GB MAX Endurance microSDXC Card with Adapter for Home Security Cameras and Dash cams
Return or replace items: Eligible through August 1, 2026
Buy it again
View your item
Get product support
Track package
←Previous
1
2
3
Next→

Customers who viewed items in your browsing history also viewedPage 1 of 3
Previous set of slides
SOSOHOME 6 Gallon Trash Bags, Small Garbage Bags, Fits 5-6 Gallon Bins, Clear
4.5 out of 5 stars 4,410
$8.99 ($0.12/count)
Next set of slides
Continue series you've startedPage 1 of 4
The First Ranger: Frontiers Saga Part 3, Book 11
Ryk Brown
Next set of slides
Your Browsing HistoryView or edit your browsing historyPage 1 of 6
e.l.f. Camo Color Corrector for Dark Circles, Hydrating Under-Eye Brightening
Next set of slides

Back to top
Get to Know Us
Careers
Self-Publish with Us
See More Ways to Make Money
Groceries at Amazon
Groceries & More
Right To Your Door
© 1996-2026, Amazon.com, Inc. or its affiliates
"""
    parser = AmazonParser()
    orders = parser.parse_orders_page(order_text)

    assert len(orders) == 1
    assert orders[0].items == [
        "SANDISK 128GB MAX Endurance microSDXC Card with Adapter for Home "
        "Security Cameras and Dash cams"
    ]


def test_markdown_link_wrapped_order_still_parses() -> None:
    """Some order-history copies (e.g. from a markdown-rendering copy tool)
    wrap every line as '* [Visible Text](https://...)'. This must not break
    the order header match (a '* ' bullet in front of TOTAL/ORDER # used to
    stop the header regex from matching at all — zero orders parsed) or leak
    raw URLs / UI text into the extracted item.
    """
    order_text = """Order placed
June 28, 2026

* TOTAL
$38.72
* SHIP TO
Derek Example
* ORDER # 114-1234567-7654321
* [View order details ](https://www.amazon.com/your-orders/order-details?orderID=x)[View invoice](https://www.amazon.com/gp/css/summary/print.html?orderID=x)
Ask Alexa about this order
Delivered June 30
Your package was left near the front door or porch.

* [Lee Men's Dungarees New Belted Wyoming Cargo Short, Bourbon, 38](https://www.amazon.com/dp/B01IT4V0M0?ref=x)
Return or replace items: Eligible through July 30, 2026
[Buy it again](https://www.amazon.com/gp/buyagain?ats=x)
[View your item](https://www.amazon.com/your-orders/pop?ref=x)
"""
    parser = AmazonParser()
    orders = parser.parse_orders_page(order_text)

    assert len(orders) == 1
    order = orders[0]
    assert order.order_id == "114-1234567-7654321"
    assert order.total == 38.72
    assert order.date_str == "June 28, 2026"
    assert order.items == [
        "Lee Men's Dungarees New Belted Wyoming Cargo Short, Bourbon, 38"
    ]
    # No raw URL or markdown syntax leaked into the item text.
    assert "http" not in order.items[0]
    assert "[" not in order.items[0]


def test_reworded_duplicate_below_flat_similarity_threshold_still_collapses() -> None:
    """A real alt-text/title duplicate pair can score as low as ~60% token
    overlap — well within the range of a genuinely different same-brand item
    (e.g. two distinct sizes can score ~83%), so text similarity alone can't
    reliably separate the two cases. The leading-space structural marker
    (image alt-text line has one, the following title-link line doesn't) is
    checked first and catches this even at low text-similarity.
    """
    order_text = """Order placed
June 5, 2026
Total
$6.53
Order # 114-7654321-1234567

Delivered June 6
Your package was left near the front door or porch.
 Andiker Cat Spring Toy, 12 Pc Colorful Cat Kicker Toys Interactive Cat Toys for Indoor Cats Swatting, Biting, Hunting to Kill Time and Keep Fit
Andiker Interactive Cat Spiral Creative Spring Toy to Kill Time and Keep Fit, Sturdy and Heavy Plastic for Swatting, Biting, Hunting Kitten Toys, Colorful, 12 pcs
Buy it again
"""
    parser = AmazonParser()
    orders = parser.parse_orders_page(order_text)

    assert len(orders) == 1
    assert len(orders[0].items) == 1
    assert "Andiker" in orders[0].items[0]


def test_distinct_size_variant_not_merged_despite_high_similarity() -> None:
    """Two distinct sizes of the same listing can score higher text-similarity
    than a real duplicate pair (see test above), so this must stay as two
    separate items rather than collapsing — the numeric-only-difference
    exception applies regardless of the leading-space structural marker.
    """
    order_text = """Order placed
June 28, 2026
Total
$38.72
Order # 114-1234567-7654321

 Lee Men's Dungarees New Belted Wyoming Cargo Short, Bourbon, 38
Return or replace items: Eligible through July 30, 2026
Buy it again
View your item

 Lee Men's Dungarees New Belted Wyoming Cargo Short, Bourbon, 36
Buy it again
View your item
"""
    parser = AmazonParser()
    orders = parser.parse_orders_page(order_text)

    assert len(orders) == 1
    assert orders[0].items == [
        "Lee Men's Dungarees New Belted Wyoming Cargo Short, Bourbon, 38",
        "Lee Men's Dungarees New Belted Wyoming Cargo Short, Bourbon, 36",
    ]
