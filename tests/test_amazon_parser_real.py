"""Tests for real Amazon order parsing functionality."""

from ynab_amazon_categorizer.amazon_parser import AmazonParser


def test_parse_actual_amazon_order_format():
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


def test_parse_different_order():
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
