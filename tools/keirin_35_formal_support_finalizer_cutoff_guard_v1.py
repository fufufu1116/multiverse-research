#!/usr/bin/env python3
"""Prospective cutoff-binding guard for the locked 35-rider Keirin finalizer.

This module adds a fail-closed provenance layer in front of
keirin_35_formal_support_finalizer_v1. It performs no network access and
must never inspect RESULT, PAYOUT, ODDS, predictions, or human comments.

A future PRE row is eligible for delegation to v1 only when its event has
an independently captured, SHA-256-bound cutoff record that was itself
captured no later than the cutoff and whose cutoff timestamp exactly
matches the row's trusted_pit_cutoff_jst.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from keirin_35_formal_support_finalizer_v1 import (
    FinalizerError,
    finalize as finalize_v1,
    parse_dt,
    validate_sha256,
)

JST_OFFSET = timedelta(hours=9)
LOCKED_STATUS = "LOCKED_TRUSTED_PRE_CUTOFF"


class CutoffBindingError(FinalizerError):
    pass


def _event_key(venue: Any, race_date: Any) -> tuple[str, str]:
    return str(venue or ""), str(race_date or "")


def _require_jst(value: str, field: str):
    dt = parse_dt(value, field)
    if dt.utcoffset() != JST_OFFSET:
        raise CutoffBindingError(f"jst_offset_required_{field}")
    return dt


def validate_cutoff_bindings(future_pre: dict, cutoff_manifest: dict) -> dict:
    bindings = list(cutoff_manifest.get("event_bindings") or [])
    by_event = {}
    for binding in bindings:
        key = _event_key(binding.get("venue"), binding.get("race_date"))
        if not all(key):
            raise CutoffBindingError("binding_event_key_missing")
        if key in by_event:
            raise CutoffBindingError(f"duplicate_cutoff_binding:{key}")
        by_event[key] = binding

    rows = list(future_pre.get("rows") or [])
    checked_events = set()
    for row in rows:
        key = _event_key(row.get("venue"), row.get("race_date"))
        binding = by_event.get(key)
        if binding is None:
            raise CutoffBindingError(f"missing_cutoff_binding:{key}")
        if binding.get("status") != LOCKED_STATUS:
            raise CutoffBindingError(f"cutoff_binding_not_locked:{key}")

        cutoff_raw = str(binding.get("trusted_pit_cutoff_jst") or "")
        source_url = str(binding.get("cutoff_source_url") or "")
        source_sha = str(binding.get("cutoff_source_sha256") or "")
        source_captured_raw = str(binding.get("cutoff_source_captured_at_jst") or "")

        if not source_url.startswith(("https://", "http://")):
            raise CutoffBindingError(f"cutoff_source_url_missing:{key}")
        validate_sha256(source_sha)

        cutoff = _require_jst(cutoff_raw, "trusted_pit_cutoff_jst")
        source_captured = _require_jst(
            source_captured_raw, "cutoff_source_captured_at_jst"
        )
        if source_captured > cutoff:
            raise CutoffBindingError(f"cutoff_source_captured_after_cutoff:{key}")

        row_cutoff_raw = str(row.get("trusted_pit_cutoff_jst") or "")
        row_cutoff = _require_jst(row_cutoff_raw, "row_trusted_pit_cutoff_jst")
        if row_cutoff != cutoff:
            raise CutoffBindingError(f"row_cutoff_not_exact_binding:{key}")

        row_captured = _require_jst(
            str(row.get("captured_at_jst") or ""), "row_captured_at_jst"
        )
        if row_captured > cutoff:
            raise CutoffBindingError(f"row_captured_after_bound_cutoff:{key}")

        checked_events.add(key)

    return {
        "status": "PASS",
        "checked_rows": len(rows),
        "checked_events": [
            {"venue": venue, "race_date": race_date}
            for venue, race_date in sorted(checked_events)
        ],
        "result_accessed": False,
        "payout_accessed": False,
        "odds_accessed": False,
        "prediction_accessed": False,
    }


def finalize_with_cutoff_guard(
    order: dict,
    matrix: dict,
    registry: dict,
    future_pre: dict,
    cutoff_manifest: dict,
) -> dict:
    guard = validate_cutoff_bindings(future_pre, cutoff_manifest)
    out = finalize_v1(order, matrix, registry, future_pre)
    out["cutoff_binding_guard"] = guard
    out["cutoff_binding_manifest_record"] = cutoff_manifest.get("record")
    return out
