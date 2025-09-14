"""Tests for Amazon order parsing functionality."""

from ynab_amazon_categorizer.amazon_parser import AmazonParser


def test_parse_simple_order():
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


def test_parse_empty_order_text():
    """Test parsing empty order text returns empty list."""
    parser = AmazonParser()
    orders = parser.parse_orders_page("")
    assert len(orders) == 0


def test_extract_items_from_order_content():
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
