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
