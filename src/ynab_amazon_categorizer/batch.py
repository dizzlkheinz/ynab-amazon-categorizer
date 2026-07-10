"""Non-interactive memo enrichment policy."""

import logging
from collections.abc import Mapping, Sequence
from typing import Any

import requests

from .exceptions import YNABAPIError
from .memo_generator import MemoGenerator, build_batch_memo
from .models import Order
from .payloads import build_memo_only_payload
from .transaction_matcher import TransactionMatcher
from .ynab_client import YNABClient

logger = logging.getLogger(__name__)


def process_batch(
    transactions: Sequence[Mapping[str, Any]],
    parsed_orders: list[Order] | None,
    memo_generator: MemoGenerator,
    ynab_client: YNABClient,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """Auto-enrich confidently matched memos without changing categories."""
    matcher = TransactionMatcher()
    used_order_ids: set[str] = set()
    enriched = skipped = failed = 0

    for transaction in transactions:
        amount_float = transaction["amount"] / 1000.0
        order = matcher.find_confident_match(
            amount_float,
            transaction["date"],
            parsed_orders or [],
            used_order_ids,
        )
        if order is None:
            skipped += 1
            continue

        original_memo = transaction.get("memo")
        memo = build_batch_memo(
            order,
            memo_generator,
            original_memo if isinstance(original_memo, str) else "",
        )
        if memo is None:
            logger.info(
                "Skipping transaction %s because enrichment would truncate its memo.",
                transaction["id"],
            )
            skipped += 1
            continue

        payload = build_memo_only_payload(
            memo, bool(transaction.get("approved", False))
        )
        payee = transaction.get("payee_name", "N/A")
        summary = memo.splitlines()[0] if memo else ""

        if dry_run:
            print(f"  [dry-run] would enrich {payee} ${amount_float:.2f}: {summary}")
            if order.order_id:
                used_order_ids.add(order.order_id)
            enriched += 1
            continue

        try:
            ynab_client.update_transaction(transaction["id"], payload)
            print(f"  ✓ Enriched {payee} ${amount_float:.2f}: {summary}")
            if order.order_id:
                used_order_ids.add(order.order_id)
            enriched += 1
        except (YNABAPIError, requests.exceptions.RequestException) as exc:
            logger.error("Failed to enrich transaction %s: %s", transaction["id"], exc)
            print(f"  ✗ Failed to enrich {payee} ${amount_float:.2f}: {exc}")
            failed += 1

    return enriched, skipped, failed
