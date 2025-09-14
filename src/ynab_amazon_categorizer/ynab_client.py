"""YNAB API client functionality."""

import requests


class YNABClient:
    """Client for interacting with YNAB API."""

    def __init__(self, api_key: str, budget_id: str) -> None:
        self.api_key = api_key
        self.budget_id = budget_id

    def get_data(self, endpoint):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"https://api.ynab.com/v1{endpoint}"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()["data"]
        except requests.exceptions.RequestException:
            return None

    def update_transaction(self, transaction_id, payload):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"https://api.ynab.com/v1/budgets/{self.budget_id}/transactions/{transaction_id}"
        try:
            response = requests.put(url, headers=headers, json={"transaction": payload})
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False

    def get_categories(self):
        data = self.get_data(f"/budgets/{self.budget_id}/categories")

        if not data or "category_groups" not in data:
            print("Could not fetch categories.")
            return [], {}, {}

        category_list_for_completer = []
        name_to_id_lookup = {}
        id_to_name_lookup = {}
        internal_master_category_group_id = None

        # Find the Internal Master Category group ID to exclude it
        for group in data["category_groups"]:
            if group.get("name") == "Internal Master Category":
                internal_master_category_group_id = group.get("id")
                break

        # Process all category groups
        for group in data["category_groups"]:
            if (
                group.get("hidden", False)
                or group.get("id") == internal_master_category_group_id
            ):
                continue

            group_name = group["name"]

            for category in group.get("categories", []):
                if category.get("hidden", False) or category.get("deleted", False):
                    continue

                category_name = category["name"]
                category_id = category["id"]
                full_category_name = f"{group_name}: {category_name}"

                category_list_for_completer.append((full_category_name, category_id))
                name_to_id_lookup[full_category_name.lower()] = category_id
                id_to_name_lookup[category_id] = full_category_name

        return category_list_for_completer, name_to_id_lookup, id_to_name_lookup
