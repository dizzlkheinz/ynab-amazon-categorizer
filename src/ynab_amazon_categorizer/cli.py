import copy
import json
import logging
import os
import sys
from collections.abc import Iterable
from typing import Any

import requests
from prompt_toolkit import prompt
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent

from .amazon_parser import AmazonParser, Order
from .config import Config
from .exceptions import ConfigurationError, YNABAPIError
from .memo_generator import MemoGenerator, sanitize_memo
from .transaction_matcher import TransactionMatcher
from .ynab_client import YNABClient

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---


AMAZON_PAYEE_KEYWORDS = ["amazon", "amzn", "amz"]
YNAB_API_URL = "https://api.ynab.com/v1"


def prompt_for_amazon_orders_data() -> list[Order] | None:
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

    # Use extracted Amazon parser
    amazon_parser = AmazonParser()
    parsed_orders = amazon_parser.parse_orders_page(orders_text)

    # Show what was parsed
    if parsed_orders:
        print(f"\n✓ Successfully parsed {len(parsed_orders)} orders from Amazon data")
        for order in parsed_orders[:3]:
            print(f"  - Order {order.order_id}: ${order.total} on {order.date_str}")
        if len(parsed_orders) > 3:
            print(f"  ... and {len(parsed_orders) - 3} more orders")
    else:
        print("\nNo orders could be parsed from the provided text.")
        print("This might be due to formatting differences in the copied text.")

    return parsed_orders


def get_multiline_input_with_custom_submit(
    prompt_message: str = "Enter multiline text: ",
) -> str | None:
    """Get multiline input with Ctrl+J to submit"""
    kb = KeyBindings()

    @kb.add("escape", "enter")  # Binds Alt+Enter to submit
    def _(event: KeyPressEvent) -> None:
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


def generate_split_summary_memo(matching_order: Order) -> str:
    """Generate a summary memo for split transactions showing all items"""
    if (
        not matching_order
        or not hasattr(matching_order, "items")
        or not matching_order.items
    ):
        return ""

    items = matching_order.items
    if len(items) == 1:
        return sanitize_memo(items[0])

    # Format as: "2 Items:\n- Item 1\n- Item 2"
    summary = f"{len(items)} Items:"
    for item in items:
        summary += f"\n- {item}"

    return sanitize_memo(summary)


def prompt_for_item_details() -> dict[str, str | int | float | list[str] | None] | None:
    """Prompt user to enter item details manually"""
    print("\n--- Manual Item Details Entry ---")

    item_details: dict[str, str | int | float | list[str] | None] = {}

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


# --- Extracted Helper Functions ---


def print_config_summary(config: Config) -> None:
    """Print configuration summary without exposing secrets."""
    print("✓ Configuration loaded successfully")
    print("✓ API Key: configured")
    if config.budget_id and len(config.budget_id) >= 4:
        print(f"✓ Budget ID: ...{config.budget_id[-4:]}")
    else:
        print("✓ Budget ID: configured")
    if config.account_id:
        print("✓ Account ID: configured")
    else:
        print("✓ All accounts")


def build_preview(
    payload: dict[str, Any], category_id_map: dict[str, str]
) -> dict[str, Any]:
    """Build a preview dict from payload with category names injected.

    Uses deep copy to avoid mutating the original payload.
    """
    preview_dict: dict[str, Any] = copy.deepcopy(payload)
    category_id = preview_dict.get("category_id")
    if isinstance(category_id, str):
        category_name = category_id_map.get(category_id, "Unknown Category")
        preview_dict["category_name"] = category_name
    subtransactions_value = preview_dict.get("subtransactions")
    if isinstance(subtransactions_value, list):
        for subtrans in subtransactions_value:
            if not isinstance(subtrans, dict):
                continue
            subtrans_category_id = subtrans.get("category_id")
            if isinstance(subtrans_category_id, str):
                cat_name = category_id_map.get(subtrans_category_id, "Unknown Category")
                subtrans["category_name"] = cat_name
    return preview_dict


def compute_split_amount(amount_float: float, remaining_milliunits: int) -> int:
    """Convert a positive user-entered amount to signed milliunits matching the parent.

    The sign of the result matches ``remaining_milliunits`` (negative for outflows,
    positive for inflows/refunds).

    Raises ``ValueError`` if the amount exceeds the remaining balance.
    """
    split_amount_milliunits = int(round(amount_float * 1000))

    if split_amount_milliunits > abs(remaining_milliunits) + 1:
        raise ValueError(
            f"Amount exceeds remaining. Max {abs(remaining_milliunits / 1000.0):.2f}"
        )

    # Apply sign to match parent transaction direction
    if remaining_milliunits < 0:
        split_amount_milliunits = -abs(split_amount_milliunits)
    else:
        split_amount_milliunits = abs(split_amount_milliunits)

    # Snap to exact remainder when within 1 milliunit
    if abs(abs(split_amount_milliunits) - abs(remaining_milliunits)) <= 1:
        split_amount_milliunits = remaining_milliunits

    return split_amount_milliunits


def build_single_payload(
    transaction: dict[str, Any],
    category_id: str,
    memo: str,
) -> dict[str, Any]:
    """Build update payload for a single-category transaction."""
    return {
        "id": transaction["id"],
        "account_id": transaction["account_id"],
        "date": transaction["date"],
        "amount": transaction["amount"],
        "payee_id": transaction.get("payee_id"),
        "payee_name": transaction.get("payee_name", "N/A"),
        "category_id": category_id,
        "memo": sanitize_memo(memo),
        "cleared": transaction.get("cleared"),
        "approved": True,
        "flag_color": transaction.get("flag_color"),
        "import_id": transaction.get("import_id"),
    }


def build_split_payload(
    transaction: dict[str, Any],
    subtransactions: list[dict[str, int | str | None]],
    matching_order: Order | None,
    original_memo: str,
) -> dict[str, Any]:
    """Build update payload for a split transaction."""
    memo = (
        generate_split_summary_memo(matching_order)
        if matching_order
        else sanitize_memo(original_memo)
    )
    return {
        "id": transaction["id"],
        "account_id": transaction["account_id"],
        "date": transaction["date"],
        "amount": transaction["amount"],
        "payee_id": transaction.get("payee_id"),
        "payee_name": transaction.get("payee_name", "N/A"),
        "category_id": None,
        "memo": memo,
        "cleared": transaction.get("cleared"),
        "approved": True,
        "flag_color": transaction.get("flag_color"),
        "import_id": transaction.get("import_id"),
        "subtransactions": subtransactions,
    }


def fetch_amazon_transactions(
    ynab_client: YNABClient, config: Config
) -> list[dict[str, Any]]:
    """Fetch transactions from YNAB and filter to uncategorized Amazon ones."""
    transactions_endpoint = f"/budgets/{config.budget_id}/transactions"
    if config.account_id:
        transactions_endpoint = (
            f"/budgets/{config.budget_id}/accounts/{config.account_id}/transactions"
        )
    transactions_data = ynab_client.get_data(transactions_endpoint)
    if not isinstance(transactions_data, dict):
        return []
    transactions_raw_obj = transactions_data.get("transactions")
    if not isinstance(transactions_raw_obj, list):
        return []
    transactions_raw: list[Any] = transactions_raw_obj
    transactions: list[dict[str, Any]] = [
        transaction for transaction in transactions_raw if isinstance(transaction, dict)
    ]
    logger.info("Fetched %d transactions.", len(transactions))
    transactions_to_process = []
    for t in transactions:
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
        )
        if is_valid_for_processing:
            transactions_to_process.append(t)
    return transactions_to_process


class CategoryCompleter(Completer):
    def __init__(self, category_list: list[tuple[str, str]]) -> None:
        self.categories = [name for name, _id in category_list]
        self.category_list = category_list

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        text_before_cursor = document.text_before_cursor.lower()
        if text_before_cursor:
            for category_name in self.categories:
                if text_before_cursor in category_name.lower():
                    yield Completion(
                        category_name, start_position=-len(text_before_cursor)
                    )


def prompt_for_category_selection(
    category_completer: CategoryCompleter, name_to_id_map: dict[str, str]
) -> tuple[str | None, str | None]:
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


# --- Extracted per-transaction functions ---


def display_matched_order(matching_order: Order, memo_generator: MemoGenerator) -> None:
    """Display matched order details to the user."""
    print("\n  🎯 MATCHED ORDER FOUND:")
    print(f"     Order ID: {matching_order.order_id}")
    print(
        f"     Total: ${matching_order.total if matching_order.total is not None else 'N/A'}"
    )
    print(
        f"     Date: {matching_order.date_str if matching_order.date_str is not None else 'N/A'}"
    )
    order_link = memo_generator.generate_amazon_order_link(matching_order.order_id)
    print(f"     Order Link: {order_link}")
    if matching_order.items:
        print("     Items:")
        for item in matching_order.items:
            print(f"       - {item}")
    print()


def resolve_memo(
    matching_order: Order | None,
    original_memo: str,
    memo_generator: MemoGenerator,
) -> str:
    """Determine the memo for a single-category transaction.

    Uses matched order data when available, otherwise prompts for manual entry.
    Returns the final memo string (already sanitized).
    """
    item_details: dict[str, str | int | float | list[str] | None] | None = None
    enhanced_memo = None

    # Use matched order data or prompt for manual entry
    if matching_order:
        print("Using matched order data for memo generation...")
        item_details = {
            "order_id": matching_order.order_id or "",
            "items": matching_order.items,
            "total": matching_order.total,
            "date": matching_order.date_str,
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
            items_list = item_details["items"]
            items_text = (
                items_list[0]
                if isinstance(items_list, list) and items_list
                else "Amazon Purchase"
            )
            order_id_value = item_details["order_id"]
            order_link = memo_generator.generate_amazon_order_link(
                order_id_value if isinstance(order_id_value, str) else None
            )
            enhanced_memo = f"{items_text}\n {order_link}" if order_link else items_text
        else:
            # Manual item details
            enhanced_memo = memo_generator.generate_enhanced_memo(
                original_memo, None, item_details
            )
    else:
        # No item details
        enhanced_memo = original_memo

    if enhanced_memo and enhanced_memo != original_memo:
        print("\nSuggested memo:")
        print(f"'{enhanced_memo}'")
        use_suggested = input("Use suggested memo? (y/n, default y): ").lower()
        if use_suggested != "n":
            return sanitize_memo(enhanced_memo)
        else:
            print("Enter custom memo (multiline):")
            memo_input = get_multiline_input_with_custom_submit("> ")
            return sanitize_memo(memo_input.strip()) if memo_input else ""
    else:
        print("Enter optional memo (multiline):")
        memo_input = get_multiline_input_with_custom_submit("> ")
        return sanitize_memo(memo_input.strip()) if memo_input else ""


def handle_split(
    transaction: dict[str, Any],
    matching_order: Order | None,
    memo_generator: MemoGenerator,
    category_completer: CategoryCompleter,
    category_name_map: dict[str, str],
) -> list[dict[str, int | str | None]] | None:
    """Handle split transaction flow.

    Returns list of subtransaction dicts, or None if cancelled.
    """
    print("\n--- Splitting Transaction ---")
    subtransactions: list[dict[str, int | str | None]] = []
    amount_milliunits = transaction["amount"]
    remaining_milliunits = amount_milliunits
    split_count = 1

    while remaining_milliunits != 0:
        print(
            f"\nSplit {split_count}: Amount remaining: {abs(remaining_milliunits / 1000.0):.2f}"
        )

        # Show which item this split is for if we have matched order data
        items: list[str] = matching_order.items if matching_order else []

        if items:
            if split_count <= len(items):
                print(f"Item {split_count}: {items[split_count - 1]}")
            else:
                print("Additional split for remaining items")

        print(f"Enter category name for split {split_count}:")
        category_id, category_name = prompt_for_category_selection(
            category_completer, category_name_map
        )
        if category_id is None:  # User backed out
            print("Cancelling split process.")
            return None

        # Get amount for this split
        while True:
            try:
                max_amount = abs(remaining_milliunits / 1000.0)
                amount_str = input(
                    f"Enter amount for '{category_name}' (positive, max {max_amount:.2f}, default {max_amount:.2f}): "
                )
                if not amount_str:
                    amount_str = str(max_amount)
                split_amount_float = float(amount_str)
                if split_amount_float <= 0:
                    print("Amount must be positive.")
                    continue
                split_amount_milliunits = compute_split_amount(
                    split_amount_float, remaining_milliunits
                )
                if split_amount_milliunits == remaining_milliunits:
                    print("Amount covers remaining balance.")
                break  # Amount valid
            except ValueError as e:
                print(str(e) if str(e) != str(e).lower() else "Invalid amount.")

        # --- ENHANCED SPLIT MEMO INPUT ---
        split_memo = _resolve_split_memo(
            matching_order, memo_generator, category_name, split_count
        )
        # --- END ENHANCED SPLIT MEMO INPUT ---

        subtransactions.append(
            {
                "amount": split_amount_milliunits,
                "category_id": category_id,
                "memo": sanitize_memo(split_memo) if split_memo else None,
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

    if remaining_milliunits == 0 and subtransactions:
        return subtransactions
    return None


def _resolve_split_memo(
    matching_order: Order | None,
    memo_generator: MemoGenerator,
    category_name: str | None,
    split_count: int,
) -> str:
    """Resolve memo for a single split within a split transaction."""
    suggested_split_memo: str = ""

    if matching_order:
        print("Using matched order data for split memo...")
        items = matching_order.items
        order_id = matching_order.order_id

        if split_count <= len(items):
            items_text = items[split_count - 1]
            order_link = memo_generator.generate_amazon_order_link(order_id)
            suggested_split_memo = (
                f"{items_text}\n {order_link}" if order_link else items_text
            )
        else:
            suggested_split_memo = "Additional item"
    else:
        manual_entry = input(
            "Enter item details for this split? (y/n, default n): "
        ).lower()
        if manual_entry == "y":
            item_details = prompt_for_item_details()
            if item_details:
                suggested_split_memo = memo_generator.generate_enhanced_memo(
                    "", None, item_details
                )

    if suggested_split_memo:
        print(f"Suggested memo for '{category_name}' split:")
        print(f"'{suggested_split_memo}'")
        use_suggested = input("Use suggested memo? (y/n, default y): ").lower()
        if use_suggested != "n":
            return suggested_split_memo
        else:
            print(f"Enter custom memo for '{category_name}' split (multiline):")
            split_memo = get_multiline_input_with_custom_submit("> ")
            return split_memo.strip() if split_memo else ""
    else:
        print(f"Enter optional memo for '{category_name}' split (multiline):")
        split_memo_input = get_multiline_input_with_custom_submit("> ")
        return split_memo_input.strip() if split_memo_input else ""


def process_transaction(
    transaction: dict[str, Any],
    index: int,
    total: int,
    parsed_orders: list[Order] | None,
    memo_generator: MemoGenerator,
    ynab_client: YNABClient,
    category_completer: CategoryCompleter,
    category_name_map: dict[str, str],
    category_id_map: dict[str, str],
) -> bool:
    """Process a single transaction through the interactive flow.

    Returns True if processed/skipped, False if user quit.
    """
    transaction_id = transaction["id"]
    date = transaction["date"]
    payee = transaction.get("payee_name", "N/A")
    amount_milliunits = transaction["amount"]
    amount_float = amount_milliunits / 1000.0
    original_memo = transaction.get("memo", "")

    if amount_milliunits > 0:
        print(f"Found inflow transaction: {payee} ${amount_float:.2f}")
        process_inflow = input(
            "Process this inflow (refund/credit)? (y/n, default n): "
        ).lower()
        if process_inflow != "y":
            print("Skipping inflow transaction.")
            return True

    print(f"\n--- Processing Transaction {index + 1}/{total} ---")
    print(f"  ID:   {transaction_id}")
    print(f"  Date: {date}")
    print(f"  Payee: {payee}")
    print(f"  Amount: {-amount_float:.2f}")
    if original_memo:
        print(f"  Original Memo: {original_memo}")

    # Try to find matching order from parsed data and show it
    matching_order: Order | None = None
    if parsed_orders:
        transaction_matcher = TransactionMatcher()
        matching_order = transaction_matcher.find_matching_order(
            amount_float, date, parsed_orders
        )
        if matching_order:
            display_matched_order(matching_order, memo_generator)
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
            return False
        elif action == "s":
            print("Skipping.")
            return True
        elif action == "c":
            result = _handle_categorize(
                transaction,
                matching_order,
                original_memo,
                memo_generator,
                ynab_client,
                category_completer,
                category_name_map,
                category_id_map,
            )
            if result == "done":
                return True
            # result == "continue" means back to action prompt
            continue
        else:
            print("Invalid action. Choose 'c', 's', or 'q'.")


def _handle_categorize(
    transaction: dict[str, Any],
    matching_order: Order | None,
    original_memo: str,
    memo_generator: MemoGenerator,
    ynab_client: YNABClient,
    category_completer: CategoryCompleter,
    category_name_map: dict[str, str],
    category_id_map: dict[str, str],
) -> str:
    """Handle the categorize action for a transaction.

    Returns "done" if the transaction was successfully updated (or split completed),
    or "continue" to go back to the action prompt.
    """
    transaction_id = transaction["id"]
    updated_payload_dict: dict[str, Any] | None = None

    # Check if we should offer splitting
    should_offer_split = bool(
        matching_order and matching_order.items and len(matching_order.items) > 1
    )

    if should_offer_split:
        print("There is more than one item in this transaction.")

    split_decision = input("Split this transaction? (y/n, default n): ").lower()

    if split_decision != "y":
        # --- SINGLE CATEGORY ---
        print("Enter category name for the transaction:")
        category_id, _category_name = prompt_for_category_selection(
            category_completer, category_name_map
        )
        if category_id is None:
            return "continue"

        memo_input = resolve_memo(matching_order, original_memo, memo_generator)

        updated_payload_dict = build_single_payload(
            transaction,
            category_id,
            memo_input if memo_input else original_memo,
        )
    else:
        # --- SPLITTING ---
        subtransactions = handle_split(
            transaction,
            matching_order,
            memo_generator,
            category_completer,
            category_name_map,
        )
        if subtransactions:
            updated_payload_dict = build_split_payload(
                transaction, subtransactions, matching_order, original_memo
            )
        else:
            print("Splitting cancelled. No changes will be made.")

    # --- Confirmation and API Call ---
    if updated_payload_dict:
        print("\n--- Preview Update ---")
        preview_dict = build_preview(updated_payload_dict, category_id_map)
        print(json.dumps(preview_dict, indent=2, ensure_ascii=False))
        confirm = input("Confirm update? (y/n, default y): ").lower()
        if not confirm:
            confirm = "y"
        if confirm == "y":
            try:
                ynab_client.update_transaction(transaction_id, updated_payload_dict)
                print("Update successful.")
                return "done"
            except (YNABAPIError, requests.exceptions.RequestException) as exc:
                logger.error("Failed to update transaction %s: %s", transaction_id, exc)
                print(f"Update failed: {exc}")
                return "continue"
        else:
            print("Update cancelled.")
            return "continue"

    return "continue"


# --- Main Script Logic ---


def main() -> None:
    """Main CLI function."""
    logging.basicConfig(level=logging.INFO)

    # Load configuration using extracted Config class
    try:
        config = Config.from_env()
        print_config_summary(config)
    except ConfigurationError as e:
        logger.error("Configuration error: %s", e)
        print("Please set environment variables or create a .env file.")
        print("See README.md for setup instructions.")
        sys.exit(1)

    # Initialize YNAB client
    ynab_client = YNABClient(config.api_key, config.budget_id)
    memo_generator = MemoGenerator(config.amazon_domain)

    print("Fetching categories...")
    try:
        categories_list, category_name_map, category_id_map = (
            ynab_client.get_categories()
        )
    except (YNABAPIError, requests.exceptions.RequestException) as exc:
        logger.error("Failed to fetch categories: %s", exc)
        print(f"Could not fetch categories: {exc}")
        sys.exit(1)

    if not categories_list:
        print("Exiting due to category fetch error or no usable categories found.")
        sys.exit(1)

    category_completer_instance = CategoryCompleter(categories_list)
    print(f"\nFound {len(categories_list)} usable categories. Completion enabled.")

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
            for order in parsed_orders[:3]:
                print(
                    f"  - Order {order.order_id}: ${getattr(order, 'total', 'N/A')} ({len(getattr(order, 'items', []))} items)"
                )
            if len(parsed_orders) > 3:
                print(f"  ... and {len(parsed_orders) - 3} more orders")
        else:
            print("No valid orders found in provided data.")

    print("\nFetching transactions...")
    try:
        transactions_to_process = fetch_amazon_transactions(ynab_client, config)
    except (YNABAPIError, requests.exceptions.RequestException) as exc:
        logger.error("Failed to fetch transactions: %s", exc)
        print(f"Could not fetch transactions: {exc}")
        sys.exit(1)

    print(
        f"\nFound {len(transactions_to_process)} uncategorized Amazon transaction(s) needing attention."
    )

    # --- Process Transactions (Main Loop) ---
    for i, t in enumerate(transactions_to_process):
        should_continue = process_transaction(
            t,
            i,
            len(transactions_to_process),
            parsed_orders,
            memo_generator,
            ynab_client,
            category_completer_instance,
            category_name_map,
            category_id_map,
        )
        if not should_continue:
            sys.exit(0)

    # End of processing loop
    print("\nFinished processing transactions.")


if __name__ == "__main__":
    main()
