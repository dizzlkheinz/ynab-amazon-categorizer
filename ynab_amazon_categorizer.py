import requests
import json
from datetime import datetime
import os  # For history file path
import re  # For order ID extraction

# --- NEW: Import prompt_toolkit components ---
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
# --- END NEW ---

# --- CONFIGURATION ---
# Get API credentials from environment variables or config file
YNAB_API_KEY = os.getenv("YNAB_API_KEY")
YNAB_BUDGET_ID = os.getenv("YNAB_BUDGET_ID")
YNAB_ACCOUNT_ID = os.getenv(
    "YNAB_ACCOUNT_ID"
)  # Optional: specific account ID or None for all accounts

# If environment variables aren't set, try loading from config file
if not YNAB_API_KEY or not YNAB_BUDGET_ID:
    config_file = ".env"
    if os.path.exists(config_file):
        print(f"Loading configuration from {config_file}")
        with open(config_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("YNAB_API_KEY="):
                    YNAB_API_KEY = line.split("=", 1)[1]
                elif line.startswith("YNAB_BUDGET_ID="):
                    YNAB_BUDGET_ID = line.split("=", 1)[1]
                elif line.startswith("YNAB_ACCOUNT_ID="):
                    account_id_value = line.split("=", 1)[1]
                    YNAB_ACCOUNT_ID = (
                        account_id_value if account_id_value.lower() != "none" else None
                    )

# Validate required configuration
if not YNAB_API_KEY:
    print("ERROR: YNAB_API_KEY not found!")
    print("Please set it as an environment variable or create a .env file.")
    print("See README.md for setup instructions.")
    exit(1)

if not YNAB_BUDGET_ID:
    print("ERROR: YNAB_BUDGET_ID not found!")
    print("Please set it as an environment variable or create a .env file.")
    print("See README.md for setup instructions.")
    exit(1)

print("✓ Configuration loaded successfully")
print(f"✓ API Key: {YNAB_API_KEY[:8]}..." if YNAB_API_KEY else "✗ No API Key")
print(f"✓ Budget ID: {YNAB_BUDGET_ID[:8]}..." if YNAB_BUDGET_ID else "✗ No Budget ID")
print(
    f"✓ Account ID: {YNAB_ACCOUNT_ID[:8]}..." if YNAB_ACCOUNT_ID else "✓ All accounts"
)
# --- END CONFIGURATION ---

AMAZON_PAYEE_KEYWORDS = ["amazon", "amzn", "amz"]
YNAB_API_URL = "https://api.ynab.com/v1"

# --- Amazon Order Link Functions ---


def generate_amazon_order_link(order_id):
    """Generate Amazon.ca order details link"""
    if order_id:
        return f"https://www.amazon.ca/gp/your-account/order-details?ie=UTF8&orderID={order_id}"
    return None


def add_amazon_link_to_memo(original_memo, order_link):
    """Add Amazon order link to memo, avoiding duplicates"""
    if not order_link:
        return original_memo

    memo = original_memo or ""

    # Check if link already exists
    if order_link in memo:
        return memo

    # Add link with separator if memo already has content
    if memo.strip():
        return f"{memo}\n\nAmazon Order: {order_link}"
    else:
        return f"Amazon Order: {order_link}"


def generate_enhanced_memo(original_memo, order_id, item_details=None):
    """Generate enhanced memo with order information and item details"""
    memo_parts = []

    # Start with original memo if it exists
    if original_memo and original_memo.strip():
        memo_parts.append(original_memo.strip())

    # Add order information
    if order_id:
        order_link = generate_amazon_order_link(order_id)
        if order_link:
            memo_parts.append(f"Amazon Order: {order_link}")

    # Add item details if provided
    if item_details:
        if isinstance(item_details, dict):
            # Handle structured item data
            item_info = []
            if item_details.get("title"):
                item_info.append(f"Item: {item_details['title']}")
            if item_details.get("quantity"):
                item_info.append(f"Qty: {item_details['quantity']}")
            if item_details.get("price"):
                item_info.append(f"Price: ${item_details['price']:.2f}")
            if item_info:
                memo_parts.append(" | ".join(item_info))
        elif isinstance(item_details, str) and item_details.strip():
            # Handle simple string item description
            memo_parts.append(f"Item: {item_details.strip()}")

    return "\n\n".join(memo_parts) if memo_parts else original_memo or ""


def parse_amazon_orders_page(orders_text):
    """Parse Amazon orders page text to extract order information"""
    orders = []

    # Find all order blocks using regex
    order_pattern = r"Order placed\s*([A-Za-z]+ \d+, \d{4})\s*Total\s*\$(\d+\.?\d*)\s*.*?Order # (\d{3}-\d{7}-\d{7})"
    order_matches = re.finditer(order_pattern, orders_text, re.DOTALL | re.IGNORECASE)

    for match in order_matches:
        order_date = match.group(1).strip()
        order_total = float(match.group(2))
        order_id = match.group(3)

        # Find the content after this order until the next order or end
        start_pos = match.end()
        next_order = re.search(r"Order placed", orders_text[start_pos:], re.IGNORECASE)
        if next_order:
            end_pos = start_pos + next_order.start()
            order_content = orders_text[start_pos:end_pos]
        else:
            order_content = orders_text[
                start_pos : start_pos + 2000
            ]  # Take next 2000 chars

        # Extract items from the order content
        items = []
        lines = order_content.split("\n")

        for line in lines:
            line = line.strip()
            if not line or len(line) < 20:
                continue

            # Skip common UI elements
            skip_patterns = [
                r"^(Buy it again|Track package|View|Return|Write|Get|Share|Leave|Ask)",
                r"^(Delivered|Arriving|Auto-delivered|Package was)",
                r"^(Return items:|Return or replace)",
                r"^\d+\.?\d* out of \d+ stars",
                r"^FREE|^Today by|^Get it|^List:|^Was:|^Limited-time deal",
                r"^\$\d+\.\d+|\(\$\d+\.\d+",
                r"^\d+ sustainability features?$",
                r"^[A-Z\s]{10,}$",  # All caps lines
                r"^(Ship to|Order #|View order|Invoice)",
            ]

            if any(re.match(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
                continue

            # Look for product names - they usually contain specific patterns
            if (
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
            ):  # Long descriptive lines
                # Clean up the line
                cleaned_line = re.sub(r"\s+", " ", line)
                cleaned_line = re.sub(
                    r"^[-•]\s*", "", cleaned_line
                )  # Remove bullet points

                # Skip if it looks like navigation or common elements
                skip_words = [
                    "account",
                    "orders",
                    "cart",
                    "search",
                    "hello",
                    "browse",
                    "amazon",
                    "prime",
                    "shipping",
                ]
                if not any(word in cleaned_line.lower() for word in skip_words):
                    items.append(cleaned_line)

        # Remove duplicates and limit items
        seen = set()
        unique_items = []
        for item in items:
            if item not in seen and len(item) > 15:  # Only keep substantial items
                seen.add(item)
                unique_items.append(item)
                if len(unique_items) >= 3:  # Limit to 3 items
                    break

        if unique_items:  # Only add orders that have identifiable items
            orders.append(
                {
                    "order_id": order_id,
                    "total": order_total,
                    "date": order_date,
                    "items": unique_items,
                }
            )

    return orders


def prompt_for_amazon_orders_data():
    """Prompt user to paste Amazon orders page data"""
    print("\n--- Amazon Orders Data Entry ---")
    print("You can copy and paste the content from your Amazon orders page.")
    print("This will help automatically extract order details and item information.")

    print("\nPaste Amazon orders page content:")

    orders_text = get_multiline_input_with_custom_submit("Paste here: ")

    if orders_text is None or orders_text.strip().lower() == "skip":
        print("Skipping Amazon orders data entry.")
        return None

    if not orders_text.strip():
        return None

    parsed_orders = parse_amazon_orders_page(orders_text)

    # Show what was parsed
    if parsed_orders:
        print(f"\n✓ Successfully parsed {len(parsed_orders)} orders from Amazon data")
        for order in parsed_orders[:3]:
            print(
                f"  - Order {order['order_id']}: ${order['total']} on {order['date']}"
            )
        if len(parsed_orders) > 3:
            print(f"  ... and {len(parsed_orders) - 3} more orders")
    else:
        print("\nNo orders could be parsed from the provided text.")
        print("This might be due to formatting differences in the copied text.")

    return parsed_orders


def find_matching_order(transaction_amount, transaction_date, parsed_orders):
    """Find the best matching order for a transaction"""
    if not parsed_orders:
        return None

    transaction_amount_abs = abs(transaction_amount)

    # Convert transaction date to comparable format
    try:
        trans_date = datetime.strptime(transaction_date, "%Y-%m-%d")
    except:
        trans_date = None

    best_match = None
    best_score = 0

    for order in parsed_orders:
        score = 0

        # Check amount match (most important)
        if "total" in order:
            amount_diff = abs(order["total"] - transaction_amount_abs)
            if amount_diff < 0.01:  # Exact match
                score += 100
            elif amount_diff < 1.00:  # Close match
                score += 50
            elif amount_diff < 5.00:  # Reasonable match
                score += 20

        # Check date proximity
        if trans_date and "date" in order:
            try:
                # Parse order date (format like "July 31, 2025")
                order_date = datetime.strptime(order["date"], "%B %d, %Y")
                date_diff = abs((trans_date - order_date).days)
                if date_diff <= 1:  # Same or next day
                    score += 30
                elif date_diff <= 3:  # Within 3 days
                    score += 15
                elif date_diff <= 7:  # Within a week
                    score += 5
            except:
                pass

        if score > best_score:
            best_score = score
            best_match = order

    # Only return match if score is reasonable
    return best_match if best_score >= 20 else None


def get_multiline_input_with_custom_submit(prompt_message="Enter multiline text: "):
    """Get multiline input with Ctrl+J to submit"""
    kb = KeyBindings()

    @kb.add("escape", "enter")  # Binds Alt+Enter to submit
    def _(event):
        """When Alt+Enter is pressed, accept the current buffer's text."""
        event.app.exit(result=event.app.current_buffer.text)

    print("Press Enter for a new line.")
    print("Submit by pressing Alt+Enter.")
    print("Press Ctrl+C to cancel.")

    try:
        user_input = prompt(prompt_message, multiline=True, key_bindings=kb)
        return user_input
    except EOFError:
        print("\nInput cancelled (EOF).")
        return None
    except KeyboardInterrupt:
        print("\nInput cancelled (KeyboardInterrupt).")
        return None


def generate_split_summary_memo(matching_order):
    """Generate a summary memo for split transactions showing all items"""
    if not matching_order or not matching_order.get("items"):
        return ""

    items = matching_order["items"]
    if len(items) == 1:
        return items[0]

    # Format as: "2 Items:\n- Item 1\n- Item 2"
    summary = f"{len(items)} Items:"
    for item in items:
        summary += f"\n- {item}"

    return summary


def prompt_for_item_details():
    """Prompt user to enter item details manually"""
    print("\n--- Manual Item Details Entry ---")

    item_details = {}

    # Get item title/description
    title = input("Enter item title/description (optional): ").strip()
    if title:
        item_details["title"] = title

    # Get quantity
    while True:
        qty_input = input("Enter quantity (optional, press Enter to skip): ").strip()
        if not qty_input:
            break
        try:
            quantity = int(qty_input)
            if quantity > 0:
                item_details["quantity"] = quantity
                break
            else:
                print("Quantity must be positive.")
        except ValueError:
            print("Please enter a valid number.")

    # Get price per item
    while True:
        price_input = input(
            "Enter item price (optional, press Enter to skip): "
        ).strip()
        if not price_input:
            break
        try:
            price = float(price_input.replace("$", "").replace(",", ""))
            if price >= 0:
                item_details["price"] = price
                break
            else:
                print("Price must be non-negative.")
        except ValueError:
            print("Please enter a valid price (e.g., 29.99).")

    return item_details if item_details else None


# --- Helper Functions (Assume they are here as in v3) ---
def get_ynab_data(endpoint):
    # ... (implementation from v3) ...
    headers = {"Authorization": f"Bearer {YNAB_API_KEY}"}
    url = f"{YNAB_API_URL}{endpoint}"
    response = None
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()["data"]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching YNAB data from {endpoint}: {e}")
        if response is not None:
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON response from {endpoint}")
        if response is not None:
            print(f"Response text: {response.text}")
        return None


def update_ynab_transaction(transaction_id, payload):
    # ... (implementation from v3) ...
    headers = {
        "Authorization": f"Bearer {YNAB_API_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{YNAB_API_URL}/budgets/{YNAB_BUDGET_ID}/transactions/{transaction_id}"
    response = None
    try:
        response = requests.put(url, headers=headers, json={"transaction": payload})
        response.raise_for_status()
        print(f"Successfully updated transaction {transaction_id}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error updating YNAB transaction {transaction_id}: {e}")
        if response is not None:
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
        return False
    except json.JSONDecodeError:
        print(f"Error decoding JSON response when updating {transaction_id}")
        if response is not None:
            print(f"Response text: {response.text}")
        return False


def get_categories(budget_id):
    # ... (implementation from v3) ...
    data = get_ynab_data(f"/budgets/{budget_id}/categories")
    if not data or "category_groups" not in data:
        print("Could not fetch categories.")
        return [], {}, {}

    category_list_for_completer = []
    name_to_id_lookup = {}
    id_to_name_lookup = {}
    internal_master_category_group_id = None

    for group in data["category_groups"]:
        if group.get("name") == "Internal Master Category":
            internal_master_category_group_id = group.get("id")
            break

    for group in data["category_groups"]:
        if (
            group.get("hidden", False)
            or group.get("id") == internal_master_category_group_id
        ):
            continue
        group_name = group["name"]
        for category in group["categories"]:
            if (
                not category.get("hidden", False)
                and not category.get("deleted", False)
                and category.get("name") != "Inflow: Ready to Assign"
            ):
                cat_id = category["id"]
                cat_name = category["name"]
                display_name = f"{group_name}: {cat_name}"
                category_list_for_completer.append((display_name, cat_id))
                name_to_id_lookup[display_name.lower()] = cat_id
                id_to_name_lookup[cat_id] = display_name
    category_list_for_completer.sort(key=lambda x: x[0])
    return category_list_for_completer, name_to_id_lookup, id_to_name_lookup


class CategoryCompleter(Completer):
    # ... (implementation from v3) ...
    def __init__(self, category_list):
        self.categories = [name for name, _id in category_list]
        self.category_list = category_list

    def get_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor.lower()
        if text_before_cursor:
            for category_name in self.categories:
                if text_before_cursor in category_name.lower():
                    yield Completion(
                        category_name, start_position=-len(text_before_cursor)
                    )


def prompt_for_category_selection(category_completer, name_to_id_map):
    # ... (implementation from v3) ...
    history_file = os.path.join(os.path.expanduser("~"), ".ynab_amazon_cat_history")
    history = FileHistory(history_file)
    while True:
        try:
            user_input = prompt(
                "Enter category name (Tab to complete, Enter to confirm, leave empty or type 'b' to go back): ",
                completer=category_completer,
                history=history,
                reserve_space_for_menu=5,
            ).strip()
            if not user_input or user_input.lower() == "b":
                return None, None
            input_lower = user_input.lower()
            if input_lower in name_to_id_map:
                selected_id = name_to_id_map[input_lower]
                selected_display_name = ""
                for name, cat_id in category_completer.category_list:
                    if cat_id == selected_id:
                        selected_display_name = name
                        break
                print(f"Selected: {selected_display_name}")
                return selected_id, selected_display_name
            else:
                print(
                    f"Error: '{user_input}' is not a recognized category. Please use Tab completion or try again."
                )
        except EOFError:
            print("\nOperation cancelled by user (EOF).")
            return None, None
        except KeyboardInterrupt:
            print("\nOperation cancelled by user (KeyboardInterrupt).")
            return None, None


# --- Main Script Logic ---

print("Fetching categories...")
categories_list, category_name_map, category_id_map = get_categories(YNAB_BUDGET_ID)

if not categories_list:
    print("Exiting due to category fetch error or no usable categories found.")
    exit()

category_completer_instance = CategoryCompleter(categories_list)
print(f"\nFound {len(categories_list)} usable categories. Completion enabled.")

# Setup history for memo input (optional, but can be nice)
memo_history_file = os.path.join(os.path.expanduser("~"), ".ynab_amazon_memo_history")
memo_history = FileHistory(memo_history_file)

# Ask user if they want to provide Amazon orders data for automatic item detection
print("\n--- Optional: Amazon Orders Data ---")
print(
    "You can paste Amazon orders page content to automatically match transactions with order details."
)
provide_orders = input(
    "Would you like to provide Amazon orders data? (y/n, default y): "
).lower()
if not provide_orders:
    provide_orders = "y"

parsed_orders = None
if provide_orders == "y":
    parsed_orders = prompt_for_amazon_orders_data()
    if parsed_orders:
        print(f"✓ Parsed {len(parsed_orders)} orders from Amazon data")
        for order in parsed_orders[:3]:  # Show first 3
            print(
                f"  - Order {order['order_id']}: ${order.get('total', 'N/A')} ({len(order.get('items', []))} items)"
            )
        if len(parsed_orders) > 3:
            print(f"  ... and {len(parsed_orders) - 3} more orders")
    else:
        print("No valid orders found in provided data.")

print("\nFetching transactions...")
# (Transaction fetching and filtering logic remains the same as v3)
transactions_endpoint = f"/budgets/{YNAB_BUDGET_ID}/transactions"
if YNAB_ACCOUNT_ID:
    transactions_endpoint = (
        f"/budgets/{YNAB_BUDGET_ID}/accounts/{YNAB_ACCOUNT_ID}/transactions"
    )
transactions_data = get_ynab_data(transactions_endpoint)
if transactions_data is None or "transactions" not in transactions_data:
    exit()
transactions = transactions_data["transactions"]
print(f"Fetched {len(transactions)} transactions.")
transactions_to_process = []
for t in transactions:
    # ... (Filtering logic same as v3) ...
    payee_name = t.get("payee_name", "").lower() if t.get("payee_name") else ""
    is_amazon = any(keyword in payee_name for keyword in AMAZON_PAYEE_KEYWORDS)
    is_uncategorized = t.get("category_id") is None
    is_not_reconciled = t.get("cleared") != "reconciled"
    is_valid_for_processing = (
        is_amazon
        and is_uncategorized
        and is_not_reconciled
        and t.get("amount", 0) != 0
        and t.get("transfer_account_id") is None
        and not t.get("subtransactions")
        and t.get("import_id") is not None
    )
    if is_valid_for_processing:
        transactions_to_process.append(t)
print(
    f"\nFound {len(transactions_to_process)} uncategorized Amazon transaction(s) needing attention."
)

# --- Process Transactions (Main Loop) ---
for i, t in enumerate(transactions_to_process):
    # ... (transaction detail extraction same as v3) ...
    transaction_id = t["id"]
    date = t["date"]
    payee = t.get("payee_name", "N/A")
    amount_milliunits = t["amount"]
    amount_float = amount_milliunits / 1000.0
    original_memo = t.get("memo", "")

    if amount_milliunits > 0:
        print(f"Found inflow transaction: {payee} ${amount_float:.2f}")
        process_inflow = input(
            "Process this inflow (refund/credit)? (y/n, default n): "
        ).lower()
        if process_inflow != "y":
            print("Skipping inflow transaction.")
            continue

    print(f"\n--- Processing Transaction {i + 1}/{len(transactions_to_process)} ---")
    print(f"  ID:   {transaction_id}")
    print(f"  Date: {date}")
    print(f"  Payee: {payee}")
    print(f"  Amount: {-amount_float:.2f}")
    if original_memo:
        print(f"  Original Memo: {original_memo}")

    # Try to find matching order from parsed data and show it
    matching_order = None
    if parsed_orders:
        matching_order = find_matching_order(amount_float, date, parsed_orders)
        if matching_order:
            print("\n  🎯 MATCHED ORDER FOUND:")
            print(f"     Order ID: {matching_order['order_id']}")
            print(f"     Total: ${matching_order.get('total', 'N/A')}")
            print(f"     Date: {matching_order.get('date', 'N/A')}")
            print(
                f"     Order Link: {generate_amazon_order_link(matching_order['order_id'])}"
            )
            if matching_order.get("items"):
                print("     Items:")
                for item in matching_order["items"]:
                    print(f"       - {item}")
            print()
        else:
            print("  ⚠ No matching order found in parsed Amazon data")

    while True:  # Action loop (c, s, q)
        action = input(
            "Action? (c = categorize/split, s = skip, q = quit, default c): "
        ).lower()
        if not action:
            action = "c"
        if action == "q":
            print("Quitting.")
            exit()
        elif action == "s":
            print("Skipping.")
            break  # Next transaction
        elif action == "c":
            # --- Categorization Logic ---
            updated_payload_dict = None

            # Check if there are multiple items and suggest splitting
            if (
                matching_order
                and matching_order.get("items")
                and len(matching_order["items"]) > 1
            ):
                print("There is more than one item in this transaction.")

            split_decision = input("Split this transaction? (y/n, default n): ").lower()

            if split_decision != "y":
                # --- SINGLE CATEGORY ---
                print("Enter category name for the transaction:")
                category_id, category_name = prompt_for_category_selection(
                    category_completer_instance, category_name_map
                )
                if category_id is None:
                    continue  # Back to action prompt

                # --- ENHANCED MEMO INPUT WITH AUTOMATIC ITEM DETECTION ---
                enhanced_memo = None

                # Use matched order data or prompt for manual entry
                if matching_order:
                    print("Using matched order data for memo generation...")
                    item_details = {
                        "order_id": matching_order["order_id"],
                        "items": matching_order.get("items", []),
                        "total": matching_order.get("total"),
                        "date": matching_order.get("date"),
                    }
                else:
                    # Ask if user wants to enter item details manually
                    manual_entry = input(
                        "No order match found. Enter item details manually? (y/n, default n): "
                    ).lower()
                    if manual_entry == "y":
                        item_details = prompt_for_item_details()
                    else:
                        item_details = None

                if item_details:
                    if isinstance(item_details, dict) and "items" in item_details:
                        # Auto-matched order data - format as: Item Name\n Order Link
                        items_text = (
                            item_details["items"][0]
                            if item_details["items"]
                            else "Amazon Purchase"
                        )
                        order_link = generate_amazon_order_link(
                            item_details["order_id"]
                        )
                        enhanced_memo = (
                            f"{items_text}\n {order_link}" if order_link else items_text
                        )
                    else:
                        # Manual item details
                        enhanced_memo = generate_enhanced_memo(
                            original_memo, None, item_details
                        )
                else:
                    # No item details
                    enhanced_memo = original_memo

                if enhanced_memo and enhanced_memo != original_memo:
                    print("\nSuggested memo:")
                    print(f"'{enhanced_memo}'")
                    use_suggested = input(
                        "Use suggested memo? (y/n, default y): "
                    ).lower()
                    if use_suggested != "n":
                        memo_input = enhanced_memo
                    else:
                        print("Enter custom memo (multiline):")
                        memo_input = get_multiline_input_with_custom_submit("> ")
                        if memo_input is None:
                            memo_input = ""
                        else:
                            memo_input = memo_input.strip()
                else:
                    print("Enter optional memo (multiline):")
                    memo_input = get_multiline_input_with_custom_submit("> ")
                    if memo_input is None:
                        memo_input = ""
                    else:
                        memo_input = memo_input.strip()
                # --- END ENHANCED MEMO INPUT ---

                update_payload = {
                    # ... (id, account_id, date, amount etc. same as v3) ...
                    "id": transaction_id,
                    "account_id": t["account_id"],
                    "date": t["date"],
                    "amount": amount_milliunits,
                    "payee_id": t.get("payee_id"),
                    "payee_name": payee,
                    "category_id": category_id,
                    "memo": memo_input
                    if memo_input
                    else original_memo,  # Use new memo or keep original
                    "cleared": t.get("cleared"),
                    "approved": True,
                    "flag_color": t.get("flag_color"),
                    "import_id": t.get("import_id"),
                }
                updated_payload_dict = update_payload

            else:
                # --- SPLITTING ---
                print("\n--- Splitting Transaction ---")
                subtransactions = []
                remaining_milliunits = amount_milliunits
                split_count = 1

                while remaining_milliunits != 0:
                    print(
                        f"\nSplit {split_count}: Amount remaining: {abs(remaining_milliunits / 1000.0):.2f}"
                    )

                    # Show which item this split is for if we have matched order data
                    if matching_order and matching_order.get("items"):
                        items = matching_order["items"]
                        if split_count <= len(items):
                            print(f"Item {split_count}: {items[split_count - 1]}")
                        else:
                            print("Additional split for remaining items")

                    print(f"Enter category name for split {split_count}:")
                    category_id, category_name = prompt_for_category_selection(
                        category_completer_instance, category_name_map
                    )
                    if category_id is None:  # User backed out
                        print("Cancelling split process.")
                        subtransactions = []  # Clear partial splits
                        break  # Back to action prompt

                    # Get amount for this split (logic same as v3)
                    while True:
                        try:
                            max_amount = abs(remaining_milliunits / 1000.0)
                            amount_str = input(
                                f"Enter amount for '{category_name}' (positive, max {max_amount:.2f}, default {max_amount:.2f}): "
                            )
                            if not amount_str:
                                amount_str = str(max_amount)
                            # ... (amount validation and calculation same as v3) ...
                            split_amount_float = float(amount_str)
                            if split_amount_float <= 0:
                                print("Amount must be positive.")
                                continue
                            split_amount_milliunits = int(
                                round(split_amount_float * 1000)
                            )
                            if split_amount_milliunits > abs(remaining_milliunits) + 1:
                                print(
                                    f"Amount exceeds remaining. Max {abs(remaining_milliunits / 1000.0):.2f}"
                                )
                                continue
                            split_amount_milliunits = -abs(
                                split_amount_milliunits
                            )  # Ensure negative for outflow
                            if (
                                abs(split_amount_milliunits - remaining_milliunits) <= 1
                            ):  # Equal or very close
                                print("Amount covers remaining balance.")
                                split_amount_milliunits = (
                                    remaining_milliunits  # Assign exact remainder
                                )
                            elif split_amount_milliunits > abs(remaining_milliunits):
                                continue  # Should be caught, but safety
                            break  # Amount valid
                        except ValueError:
                            print("Invalid amount.")

                    # --- ENHANCED SPLIT MEMO INPUT ---
                    # Generate memo for each split based on matched order data
                    suggested_split_memo = ""

                    # Use the already matched order if available
                    if matching_order:
                        print("Using matched order data for split memo...")
                        items = matching_order.get("items", [])
                        if split_count <= len(items):
                            # Use the specific item for this split
                            items_text = items[split_count - 1]
                            order_link = generate_amazon_order_link(
                                matching_order["order_id"]
                            )
                            suggested_split_memo = (
                                f"{items_text}\n {order_link}"
                                if order_link
                                else items_text
                            )
                        else:
                            # Fallback for extra splits beyond available items
                            suggested_split_memo = "Additional item"
                    else:
                        # Ask if user wants to enter item details manually for split
                        manual_entry = input(
                            "Enter item details for this split? (y/n, default n): "
                        ).lower()
                        if manual_entry == "y":
                            item_details = prompt_for_item_details()
                            if item_details:
                                suggested_split_memo = generate_enhanced_memo(
                                    "", None, item_details
                                )

                    # Present the memo suggestion
                    if suggested_split_memo:
                        print(f"Suggested memo for '{category_name}' split:")
                        print(f"'{suggested_split_memo}'")
                        use_suggested = input(
                            "Use suggested memo? (y/n, default y): "
                        ).lower()
                        if use_suggested != "n":
                            split_memo = suggested_split_memo
                        else:
                            print(
                                f"Enter custom memo for '{category_name}' split (multiline):"
                            )
                            split_memo = get_multiline_input_with_custom_submit("> ")
                            if split_memo is None:
                                split_memo = ""
                            else:
                                split_memo = split_memo.strip()
                    else:
                        print(
                            f"Enter optional memo for '{category_name}' split (multiline):"
                        )
                        split_memo = get_multiline_input_with_custom_submit("> ")
                        if split_memo is None:
                            split_memo = ""
                        else:
                            split_memo = split_memo.strip()
                        if split_memo is None:
                            split_memo = ""
                        else:
                            split_memo = split_memo.strip()
                    # --- END ENHANCED SPLIT MEMO INPUT ---

                    subtransactions.append(
                        {
                            "amount": split_amount_milliunits,
                            "category_id": category_id,
                            "memo": split_memo if split_memo else None,
                        }
                    )

                    remaining_milliunits -= split_amount_milliunits
                    split_count += 1

                    if abs(remaining_milliunits) <= 1:  # Handle tiny remainder
                        print("Remaining amount negligible.")
                        if subtransactions:
                            print(
                                f"Adjusting last split amount by {remaining_milliunits} milliunits."
                            )
                            subtransactions[-1]["amount"] += remaining_milliunits
                        remaining_milliunits = 0  # Force complete

                # End of splitting loop
                if remaining_milliunits == 0 and subtransactions:
                    update_payload = {
                        # ... (id, account_id, date, amount etc. same as v3) ...
                        "id": transaction_id,
                        "account_id": t["account_id"],
                        "date": t["date"],
                        "amount": amount_milliunits,
                        "payee_id": t.get("payee_id"),
                        "payee_name": payee,
                        "category_id": None,  # Null for splits
                        "memo": generate_split_summary_memo(matching_order)
                        if matching_order
                        else original_memo,  # Generate summary memo for splits
                        "cleared": t.get("cleared"),
                        "approved": True,
                        "flag_color": t.get("flag_color"),
                        "import_id": t.get("import_id"),
                        "subtransactions": subtransactions,
                    }
                    updated_payload_dict = update_payload
                else:
                    print("Splitting cancelled. No changes will be made.")
                    # updated_payload_dict remains None

            # --- Confirmation and API Call (same as v3) ---
            if updated_payload_dict:
                print("\n--- Preview Update ---")
                # Add category names to preview for better readability
                preview_dict = updated_payload_dict.copy()
                if preview_dict.get("category_id"):
                    category_name = category_id_map.get(
                        preview_dict["category_id"], "Unknown Category"
                    )
                    preview_dict["category_name"] = category_name
                if preview_dict.get("subtransactions"):
                    for subtrans in preview_dict["subtransactions"]:
                        if subtrans.get("category_id"):
                            cat_name = category_id_map.get(
                                subtrans["category_id"], "Unknown Category"
                            )
                            subtrans["category_name"] = cat_name
                print(json.dumps(preview_dict, indent=2, ensure_ascii=False))
                confirm = input("Confirm update? (y/n, default y): ").lower()
                if not confirm:
                    confirm = "y"
                if confirm == "y":
                    if update_ynab_transaction(transaction_id, updated_payload_dict):
                        print("Update successful.")
                        break  # Exit action loop, go to next transaction
                    else:
                        print("Update failed.")
                        continue  # Back to action prompt
                else:
                    print("Update cancelled.")
                    continue  # Back to action prompt
            elif action == "c":
                continue  # Back to action prompt if categorization started but didn't complete
            else:
                continue  # Back to action prompt

        else:  # Invalid action
            print("Invalid action. Choose 'c', 's', or 'q'.")
            # Loop continues asking for action

# End of processing loop
print("\nFinished processing transactions.")
