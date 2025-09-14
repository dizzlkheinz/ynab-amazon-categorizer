"""Tests for memo generation functionality."""

from ynab_amazon_categorizer.memo_generator import MemoGenerator


def test_memo_generator_initialization():
    """Test MemoGenerator can be initialized."""
    generator = MemoGenerator()
    assert generator is not None


def test_generate_amazon_order_link():
    """Test Amazon order link generation."""
    generator = MemoGenerator()

    # Test with valid order ID
    order_id = "702-8237239-1234567"
    expected_link = f"https://www.amazon.ca/gp/your-account/order-details?ie=UTF8&orderID={order_id}"

    result = generator.generate_amazon_order_link(order_id)
    assert result == expected_link


def test_generate_amazon_order_link_empty():
    """Test Amazon order link generation with empty order ID."""
    generator = MemoGenerator()

    result = generator.generate_amazon_order_link("")
    assert result is None

    result = generator.generate_amazon_order_link(None)
    assert result is None


def test_generate_enhanced_memo_basic():
    """Test basic enhanced memo generation."""
    generator = MemoGenerator()

    original_memo = "Test memo"
    order_id = "702-8237239-1234567"

    result = generator.generate_enhanced_memo(original_memo, order_id)

    assert "Test memo" in result
    assert "amazon.ca" in result
    assert order_id in result
