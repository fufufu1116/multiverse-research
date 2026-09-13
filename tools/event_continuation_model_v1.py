from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any


def _ts(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def evaluate(event: dict[str, Any], seen_keys: set[str]) -> dict[str, Any]:
    required = ["event_id", "completed_at", "detected_at", "result", "next_stage", "requires_gate", "generation"]
    for key in required:
        if key not in event:
            raise ValueError(f"missing:{key}")

    raw = f"{event['event_id']}|{event['next_stage']}|{event['generation']}"
    key = hashlib.sha256(raw.encode()).hexdigest()
    latency = max(0, int((_ts(event["detected_at"]) - _ts(event["completed_at"])).total_seconds()))

    if key in seen_keys:
        decision = "NOOP_DUPLICATE"
        reason = "already_seen"
    elif event["result"] != "success":
        decision = "STOP"
        reason = "upstream_not_success"
    elif bool(event["requires_gate"]):
        decision = "STOP"
        reason = "gate_required"
    else:
        decision = "READY_FOR_NEXT_SAFE_STAGE"
        reason = "owner_free"

    return {
        "idempotency_key": key,
        "decision": decision,
        "reason": reason,
        "next_stage": event["next_stage"] if decision == "READY_FOR_NEXT_SAFE_STAGE" else None,
        "detection_latency_seconds": latency,
        "runtime": "OFF",
    }
