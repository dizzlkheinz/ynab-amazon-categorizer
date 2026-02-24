"""YNAB API client functionality."""

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import (
    YNABAPIError,
    YNABAuthError,
    YNABNotFoundError,
    YNABRateLimitError,
    YNABValidationError,
)

logger = logging.getLogger(__name__)


def _raise_for_ynab_status(response: requests.Response) -> None:
    """Raise a typed exception based on YNAB API response status code."""
    status: int = response.status_code  # type: ignore[assignment]
    if status < 400:
        return

    try:
        detail = response.json().get("error", {}).get("detail", response.text)
    except (ValueError, AttributeError):
        detail = response.text

    if status == 401 or status == 403:
        raise YNABAuthError(
            f"Authentication failed ({status}): {detail}", status_code=status
        )
    if status == 404:
        raise YNABNotFoundError(
            f"Resource not found ({status}): {detail}", status_code=status
        )
    if status == 429:
        raise YNABRateLimitError(
            f"Rate limit exceeded ({status}): {detail}", status_code=status
        )
    if status == 400:
        raise YNABValidationError(
            f"Validation error ({status}): {detail}", status_code=status
        )
    raise YNABAPIError(f"YNAB API error ({status}): {detail}", status_code=status)


class YNABClient:
    """Client for interacting with YNAB API."""

    TIMEOUT = 30  # Default timeout in seconds

    def __init__(self, api_key: str, budget_id: str) -> None:
        self.api_key = api_key
        self.budget_id = budget_id
        self.session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def get_data(self, endpoint: str) -> dict[str, Any] | None:
        """Fetch data from YNAB API.

        Returns the 'data' dict on success, or None if the response
        has no 'data' key.

        Raises typed YNAB exceptions on HTTP errors and
        ``requests.exceptions.RequestException`` on network failures.
        """
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"https://api.ynab.com/v1{endpoint}"
        try:
            response = self.session.get(url, headers=headers, timeout=self.TIMEOUT)
            _raise_for_ynab_status(response)
            json_res = response.json()
            return json_res.get("data")
        except (YNABAPIError, requests.exceptions.RequestException):
            raise
        except (KeyError, ValueError) as exc:
            logger.error("Unexpected response format from %s: %s", endpoint, exc)
            return None

    def update_transaction(self, transaction_id: str, payload: dict[str, Any]) -> bool:
        """Update a YNAB transaction.

        Returns True on success.

        Raises typed YNAB exceptions on HTTP errors and
        ``requests.exceptions.RequestException`` on network failures.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"https://api.ynab.com/v1/budgets/{self.budget_id}/transactions/{transaction_id}"
        response = self.session.put(
            url,
            headers=headers,
            json={"transaction": payload},
            timeout=self.TIMEOUT,
        )
        _raise_for_ynab_status(response)
        return True

    def get_categories(
        self,
    ) -> tuple[list[tuple[str, str]], dict[str, str], dict[str, str]]:
        data = self.get_data(f"/budgets/{self.budget_id}/categories")

        if not data or "category_groups" not in data:
            logger.warning("Could not fetch categories.")
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
