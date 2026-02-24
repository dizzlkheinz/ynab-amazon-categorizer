"""Tests for Amazon order parsing functionality."""

from ynab_amazon_categorizer.amazon_parser import AmazonParser


def test_parse_simple_order() -> None:
    """Test parsing a simple Amazon order."""
    order_text = """
    Order placed July 31, 2024
    Total $57.57
    Order # 702-8237239-1234567
    Fancy Feast Grilled Wet Cat Food, Tuna Feast - 85 g Can (24 Pack)
    """

    parser = AmazonParser()
    orders = parser.parse_orders_page(order_text)

    assert len(orders) == 1
    order = orders[0]
    assert order.order_id == "702-8237239-1234567"
    assert order.total == 57.57
    assert order.date_str == "July 31, 2024"
    assert len(order.items) == 1
    assert "Fancy Feast" in order.items[0]


def test_parse_empty_order_text() -> None:
    """Test parsing empty order text returns empty list."""
    parser = AmazonParser()
    orders = parser.parse_orders_page("")
    assert len(orders) == 0


def test_extract_items_from_order_content() -> None:
    """Test extracting items from Amazon order content."""
    parser = AmazonParser()

    order_content = """
    Fancy Feast Grilled Wet Cat Food, Tuna Feast - 85 g Can (24 Pack)
    ACME Brand Premium Dog Treats - Large Size 2 lb bag
    Skip this line
    Buy it again - should be skipped
    Another product: Organic Cat Litter - 20 lbs Natural Clay
    Track package - should be skipped
    """

    items = parser.extract_items_from_content(order_content)

    assert len(items) >= 1
    assert "Fancy Feast Grilled Wet Cat Food, Tuna Feast - 85 g Can (24 Pack)" in items


def test_parse_order_without_items_kept() -> None:
    """Orders without parseable items are still kept (partial orders)."""
    order_text = """
    Order placed January 5, 2025
    Total $15.00
    Order # 702-1111111-2222222
    short
    """
    parser = AmazonParser()
    orders = parser.parse_orders_page(order_text)

    # Order is kept even without items
    assert len(orders) == 1
    assert orders[0].order_id == "702-1111111-2222222"
    assert orders[0].total == 15.00
    assert orders[0].items == []


def test_parse_multiple_orders() -> None:
    """Multiple orders in same text are parsed correctly."""
    order_text = """
    Order placed July 31, 2024
    Total $57.57
    Order # 702-1111111-1111111
    Fancy Feast Grilled Wet Cat Food, Tuna Feast - 85 g Can (24 Pack)

    Order placed August 15, 2024
    Total $89.99
    Order # 702-2222222-2222222
    Wireless Bluetooth Headphones - Over-Ear Noise Cancelling
    """

    parser = AmazonParser()
    orders = parser.parse_orders_page(order_text)

    assert len(orders) == 2
    assert orders[0].order_id == "702-1111111-1111111"
    assert orders[0].total == 57.57
    assert orders[1].order_id == "702-2222222-2222222"
    assert orders[1].total == 89.99


def test_extract_more_than_three_items() -> None:
    """More than 3 items can be extracted (old 3-item limit removed)."""
    parser = AmazonParser()

    order_content = """
    Fancy Feast Grilled Wet Cat Food, Tuna Feast - 85 g Can (24 Pack)
    ACME Brand Premium Dog Treats - Large Size 2 lb bag
    Another product: Organic Cat Litter - 20 lbs Natural Clay
    Super Premium Fancy Dog Collar with LED - Size Medium
    Deluxe Pet Bed Extra Large Orthopedic Memory Foam 36 inch
    """

    items = parser.extract_items_from_content(order_content)
    assert len(items) >= 4  # Should extract more than 3 now
