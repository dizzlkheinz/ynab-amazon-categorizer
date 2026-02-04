"""Tests for memo generation functionality."""

from ynab_amazon_categorizer.memo_generator import MemoGenerator


def test_memo_generator_initialization() -> None:
    """Test MemoGenerator can be initialized."""
    generator = MemoGenerator()
    assert generator is not None


def test_generate_amazon_order_link() -> None:
    """Test Amazon order link generation."""
    generator = MemoGenerator()

    # Test with valid order ID
    order_id = "702-8237239-1234567"
    expected_link = f"https://www.amazon.ca/gp/your-account/order-details?ie=UTF8&orderID={order_id}"

    result = generator.generate_amazon_order_link(order_id)
    assert result == expected_link


def test_generate_amazon_order_link_empty() -> None:
    """Test Amazon order link generation with empty order ID."""
    generator = MemoGenerator()

    result = generator.generate_amazon_order_link("")
    assert result is None

    result = generator.generate_amazon_order_link(None)
    assert result is None


def test_generate_enhanced_memo_basic() -> None:
    """Test basic enhanced memo generation."""
    generator = MemoGenerator()

    original_memo = "Test memo"
    order_id = "702-8237239-1234567"

    result = generator.generate_enhanced_memo(original_memo, order_id)

    assert "Test memo" in result
    assert "amazon.ca" in result
    assert order_id in result


def test_generate_amazon_order_link_custom_domain() -> None:
    """Test order link uses custom domain when provided."""
    generator = MemoGenerator("amazon.com")
    order_id = "702-8237239-1234567"

    result = generator.generate_amazon_order_link(order_id)

    assert result is not None
    assert "amazon.com" in result
    assert "amazon.ca" not in result
    assert order_id in result


def test_generate_enhanced_memo_with_item_details() -> None:
    """Test enhanced memo includes item title, quantity, and price."""
    generator = MemoGenerator()
    item_details = {"title": "USB Cable", "quantity": 2, "price": 9.99}

    result = generator.generate_enhanced_memo("", "702-8237239-1234567", item_details)

    assert "USB Cable" in result
    assert "x2" in result
    assert "$9.99" in result
    assert "amazon.ca" in result


def test_generate_enhanced_memo_item_details_no_order_id() -> None:
    """Test enhanced memo with item details but no order link."""
    generator = MemoGenerator()
    item_details = {"title": "Keyboard", "quantity": 1, "price": 49.99}

    result = generator.generate_enhanced_memo("", None, item_details)

    assert "Keyboard" in result
    assert "$49.99" in result
    # No order link should be present
    assert "amazon.ca" not in result
