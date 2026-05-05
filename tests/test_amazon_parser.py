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


def test_cancelled_order_items_do_not_bleed() -> None:
    """Items from a cancelled order must not appear under the preceding valid order."""
    # Order 701-9742314-2110603 ($29.58 capsules) is followed by a cancelled order
    # whose item (Altra sneaker) must not be attributed to the capsules order.
    order_text = """Order placed
April 22, 2026
Total
$29.58
Ship to
Shelby and Kalman Sutker
Order # 701-9742314-2110603
View order details Invoice

Now arriving today 5:15 p.m. - 8:15 p.m.

    Yogti Psyllium Husk Capsules, 300 Count 2
    Yogti Psyllium Husk Capsules, 300 Count
    Buy it again

    Track package
    Return or replace items
    Write a product review

Order placed
April 22, 2026
Order # 701-0552104-1147435

Cancelled
Your order was cancelled. You have not been charged for this order.

    Altra Men's Lone Peak 9 Trail Running Shoe, Tan, 13 Wide
    Altra Men's Lone Peak 9 Trail Running Shoe, Tan, 13 Wide

Order placed
April 22, 2026
Total
$29.73
Ship to
Shelby and Kalman Sutker
Order # 701-5052171-6951446
View order details Invoice

    TEMPTATIONS Cat Treats, Seafood Medley Flavour, 454g Tub 4
    TEMPTATIONS Cat Treats, Seafood Medley Flavour, 454g Tub
    Buy it again
    View your item
"""

    parser = AmazonParser()
    orders = parser.parse_orders_page(order_text)

    # Cancelled order must be omitted entirely
    assert len(orders) == 2
    order_ids = [o.order_id for o in orders]
    assert "701-0552104-1147435" not in order_ids

    capsules_order = next(o for o in orders if o.order_id == "701-9742314-2110603")
    item_text = " ".join(capsules_order.items)
    assert "Altra" not in item_text, "Cancelled-order item bled into adjacent order"
    assert "Psyllium" in item_text


def test_quantity_badge_stripped_from_item_name() -> None:
    """Trailing quantity badge numbers are removed when the bare name also appears."""
    parser = AmazonParser()

    # Amazon shows "Product Name <qty>" then "Product Name" on successive lines.
    order_content = """
    TEMPTATIONS Cat Treats, Seafood Medley Flavour, 454g Tub 4
    TEMPTATIONS Cat Treats, Seafood Medley Flavour, 454g Tub
    Buy it again
    View your item
    Nizoral Anti-Dandruff Shampoo with 2% Ketoconazole, Fresh Scent, 325 ml
    Nizoral Anti-Dandruff Shampoo with 2% Ketoconazole, Fresh Scent, 325 ml
    """

    items = parser.extract_items_from_content(order_content)
    assert len(items) == 2
    assert all("454g Tub" in i or "Ketoconazole" in i for i in items)
    # Bare form preserved, badge number gone
    assert not any(i.endswith(" 4") for i in items)


def test_size_number_not_stripped() -> None:
    """Trailing size numbers (2+ digits) are NOT stripped — they are part of the name."""
    parser = AmazonParser()

    order_content = """
    Corset Femme Tops Floral Renaissance Pirate Overbust Boned Bustier Tops Green Size 10
    Corset Femme Tops Floral Renaissance Pirate Overbust Boned Bustier Tops Green Size 10
    Return items: Eligible through May 17, 2026
    Buy it again
    """

    items = parser.extract_items_from_content(order_content)
    assert len(items) == 1
    assert items[0].endswith("Size 10")


def test_now_arriving_status_line_skipped() -> None:
    """'Now arriving today X:XX p.m.' delivery status must not be extracted as an item."""
    parser = AmazonParser()

    order_content = """
Now arriving today 5:15 p.m. - 8:15 p.m.

    Yogti Psyllium Husk Capsules, 300 Count
    Yogti Psyllium Husk Capsules, 300 Count
    Buy it again
    """

    items = parser.extract_items_from_content(order_content)
    assert all("arriving" not in i.lower() for i in items)
    assert any("Psyllium" in i for i in items)


def test_footer_boilerplate_not_extracted() -> None:
    """Page footer and Amazon nav boilerplate must not appear as items."""
    parser = AmazonParser()

    order_content = """
    Tampax Pearl Tampons, Plastic Applicator, Light Absorbency, 50 Count
    Buy it again
    Protect & Build Your Brand
    Amazon.ca Rewards Mastercard
    Registry & Gift List
    Find, attract and engage customers
    Interest-Based Ads
    © 1996-2026, Amazon.com, Inc. or its affiliates
    Amazon.com.ca ULC | 40 King Street W 47th Floor, Toronto, Ontario, Canada, M5H 3Y2
    Influencers & Associates
    To move between items, use your keyboard's up or down arrows.
    """

    items = parser.extract_items_from_content(order_content)

    assert len(items) == 1
    assert "Tampax" in items[0]
    for word in [
        "Mastercard",
        "Registry",
        "attract",
        "Interest-Based",
        "affiliates",
        "ULC",
        "Influencers",
        "keyboard",
    ]:
        assert not any(word.lower() in item.lower() for item in items), (
            f"Boilerplate '{word}' leaked into items"
        )
