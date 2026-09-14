from __future__ import annotations

import json
from typing import Any

SCHEMA_VERSION = "PORTABLE_WARDROBE_PASSPORT_v1"
_ALLOWED_PROVENANCE = {"USER_ENTERED", "IMPORTED", "INFERRED", "UNKNOWN"}
_ALLOWED_RESALE_STATUS = {"KEEP", "REVIEW", "SELL", "DONATE"}


def validate_passport(payload: dict[str, Any]) -> None:
    """Fail closed on malformed synthetic portable-wardrobe data.

    This is a research prototype, not a production migration contract.
    """
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unexpected schema_version")
    if payload.get("user_owned_export") is not True:
        raise ValueError("user_owned_export must be true")

    items = payload.get("items")
    wear_events = payload.get("wear_events")
    outfits = payload.get("outfits")
    if not isinstance(items, list) or not isinstance(wear_events, list) or not isinstance(outfits, list):
        raise ValueError("items, wear_events and outfits must be arrays")

    item_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("item must be an object")
        item_id = item.get("item_id")
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError("item_id required")
        if item_id in item_ids:
            raise ValueError("duplicate item_id")
        item_ids.add(item_id)

        if item.get("resale_status") not in _ALLOWED_RESALE_STATUS:
            raise ValueError("unexpected resale_status")
        provenance = item.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError("provenance must be an object")
        if any(value not in _ALLOWED_PROVENANCE for value in provenance.values()):
            raise ValueError("unexpected provenance value")

    for collection_name, collection in (("wear_events", wear_events), ("outfits", outfits)):
        for row in collection:
            refs = row.get("item_ids") if isinstance(row, dict) else None
            if not isinstance(refs, list) or not refs:
                raise ValueError(f"{collection_name} row must reference item_ids")
            unknown = [ref for ref in refs if ref not in item_ids]
            if unknown:
                raise ValueError(f"{collection_name} references unknown item_id")


def canonical_export(payload: dict[str, Any]) -> str:
    validate_passport(payload)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def recovery_candidates(payload: dict[str, Any], *, max_wear_count: int = 2) -> tuple[str, ...]:
    """Synthetic heuristic for UX testing only; not a resale-value estimator."""
    validate_passport(payload)
    if max_wear_count < 0:
        raise ValueError("max_wear_count must be non-negative")
    return tuple(
        item["item_id"]
        for item in payload["items"]
        if item.get("resale_status") in {"REVIEW", "SELL", "DONATE"}
        and isinstance(item.get("wear_count"), int)
        and item["wear_count"] <= max_wear_count
    )
