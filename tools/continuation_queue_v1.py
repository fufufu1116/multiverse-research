from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
from typing import Any


def _ts(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def queue_key(item: dict[str, Any]) -> str:
    raw = f"{item['source_event_id']}|{item['stage']}|{item['generation']}"
    return hashlib.sha256(raw.encode()).hexdigest()


def validate_item(item: dict[str, Any]) -> None:
    required = {
        "source_event_id",
        "stage",
        "generation",
        "enqueued_at",
        "requires_gate",
        "runtime",
    }
    missing = required - set(item)
    if missing:
        raise ValueError(f"missing:{sorted(missing)}")
    if item["runtime"] != "OFF":
        raise ValueError("runtime_must_be_off")


def enqueue(state: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    validate_item(item)
    key = queue_key(item)
    items = dict(state.get("items", {}))
    if key in items:
        return {"state": state, "created": False, "queue_key": key}
    record = dict(item)
    record.update({"queue_key": key, "status": "READY", "lease": None})
    items[key] = record
    out = {"schema": "MULTIVERSE_CONTINUATION_QUEUE_v1", "items": items}
    return {"state": out, "created": True, "queue_key": key}


def claim(state: dict[str, Any], key: str, executor_id: str, now: str, lease_seconds: int = 300) -> dict[str, Any]:
    if lease_seconds <= 0:
        raise ValueError("lease_seconds")
    items = dict(state.get("items", {}))
    if key not in items:
        return {"state": state, "claimed": False, "reason": "not_found"}
    rec = dict(items[key])
    if rec.get("requires_gate"):
        return {"state": state, "claimed": False, "reason": "gate_required"}
    lease = rec.get("lease")
    now_dt = _ts(now)
    if lease is not None and _ts(lease["expires_at"]) > now_dt:
        return {"state": state, "claimed": False, "reason": "leased"}
    expires = datetime.fromtimestamp(now_dt.timestamp() + lease_seconds, tz=timezone.utc).isoformat()
    rec["lease"] = {"executor_id": executor_id, "claimed_at": now_dt.isoformat(), "expires_at": expires}
    rec["status"] = "CLAIMED"
    items[key] = rec
    return {"state": {"schema": "MULTIVERSE_CONTINUATION_QUEUE_v1", "items": items}, "claimed": True, "reason": "claimed"}


def complete(state: dict[str, Any], key: str, executor_id: str, completed_at: str, outcome: str) -> dict[str, Any]:
    items = dict(state.get("items", {}))
    if key not in items:
        raise ValueError("not_found")
    rec = dict(items[key])
    lease = rec.get("lease")
    if lease is None or lease.get("executor_id") != executor_id:
        raise ValueError("executor_mismatch")
    rec["status"] = "DONE" if outcome == "success" else "FAILED"
    rec["completed_at"] = _ts(completed_at).isoformat()
    rec["outcome"] = outcome
    rec["lease"] = None
    items[key] = rec
    return {"schema": "MULTIVERSE_CONTINUATION_QUEUE_v1", "items": items}


def idle_metrics(state: dict[str, Any], now: str) -> dict[str, Any]:
    now_dt = _ts(now)
    waits: list[int] = []
    blocked = {"gate_required": 0, "leased": 0, "ready": 0}
    for rec in state.get("items", {}).values():
        if rec.get("status") == "DONE":
            continue
        waits.append(max(0, int((now_dt - _ts(rec["enqueued_at"])).total_seconds())))
        if rec.get("requires_gate"):
            blocked["gate_required"] += 1
        elif rec.get("lease"):
            blocked["leased"] += 1
        else:
            blocked["ready"] += 1
    return {
        "open_items": len(waits),
        "average_wait_seconds": int(sum(waits) / len(waits)) if waits else 0,
        "max_wait_seconds": max(waits) if waits else 0,
        "blocked": blocked,
        "runtime": "OFF",
    }
