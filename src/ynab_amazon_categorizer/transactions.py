"""YNAB transaction validation and selection policy."""

import logging
import re

from .config import Config
from .exceptions import YNABResponseError
from .models import YNABTransaction, validate_ynab_transaction
from .ynab_client import YNABClient

logger = logging.getLogger(__name__)

AMAZON_PAYEE_PATTERN = re.compile(
    r"(?<![a-z0-9])(?:amazon(?=$|[^a-z0-9])|amzn(?=$|[^a-z0-9]|mkt)|amz(?=$|[^a-z0-9]))",
    re.IGNORECASE,
)


def is_amazon_payee(payee_name: str) -> bool:
    """Return whether a payee contains a standalone Amazon merchant marker."""
    return AMAZON_PAYEE_PATTERN.search(payee_name) is not None


def fetch_amazon_transactions(
    ynab_client: YNABClient,
    config: Config,
    include_reconciled: bool = False,
) -> list[YNABTransaction]:
    """Fetch and validate uncategorized, non-transfer Amazon transactions."""
    endpoint = f"/budgets/{config.budget_id}/transactions"
    if config.account_id:
        endpoint = (
            f"/budgets/{config.budget_id}/accounts/{config.account_id}/transactions"
        )

    data = ynab_client.get_data(endpoint)
    if not isinstance(data, dict):
        raise YNABResponseError("Unexpected transactions collection response")
    raw_transactions = data.get("transactions")
    if not isinstance(raw_transactions, list):
        raise YNABResponseError("Unexpected transactions collection response")

    transactions: list[YNABTransaction] = []
    for index, raw_transaction in enumerate(raw_transactions):
        try:
            transactions.append(validate_ynab_transaction(raw_transaction))
        except ValueError as exc:
            raise YNABResponseError(
                f"Unexpected transaction at index {index}: {exc}"
            ) from exc

    logger.info("Fetched %d transactions.", len(transactions))
    return [
        transaction
        for transaction in transactions
        if _should_process(transaction, include_reconciled)
    ]


def _should_process(
    transaction: YNABTransaction, include_reconciled: bool = False
) -> bool:
    payee_name = transaction.get("payee_name")
    return bool(
        isinstance(payee_name, str)
        and is_amazon_payee(payee_name)
        and transaction.get("category_id") is None
        and (include_reconciled or transaction.get("cleared") != "reconciled")
        and transaction["amount"] != 0
        and transaction.get("transfer_account_id") is None
        and not transaction.get("subtransactions")
    )
