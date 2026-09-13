from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def make_receipt(queue_key: str, executor_id: str, event: str, occurred_at: str, reason: str) -> dict[str, Any]:
    if not queue_key or not executor_id or not event or not reason:
        raise ValueError("required")
    dt = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return {
        "schema": "MULTIVERSE_CONTINUATION_RECEIPT_v1",
        "queue_key": queue_key,
        "executor_id": executor_id,
        "event": event,
        "occurred_at": dt.astimezone(timezone.utc).isoformat(),
        "reason": reason,
        "runtime": "OFF",
    }


def summarize(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for receipt in receipts:
        if receipt.get("runtime") != "OFF":
            raise ValueError("runtime_must_be_off")
        event = str(receipt.get("event", "UNKNOWN"))
        counts[event] = counts.get(event, 0) + 1
    return {
        "receipt_count": len(receipts),
        "events": counts,
        "runtime": "OFF",
    }
