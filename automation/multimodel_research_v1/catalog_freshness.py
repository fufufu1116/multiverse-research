from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from automation.multimodel_research_v1.model import require, sha256_json
from automation.multimodel_research_v1.pilot_dry_run import (
    first_provider_pilot_dry_run_sha256,
    validate_first_provider_pilot_dry_run,
)
from automation.multimodel_research_v1.provider_catalog import (
    validate_provider_catalog,
)

FRESHNESS_SCHEMA = "MULTIVERSE_PROVIDER_CATALOG_FRESHNESS_v1"
PILOT_FRESHNESS_BINDING_SCHEMA = "MULTIVERSE_FIRST_PROVIDER_PILOT_FRESHNESS_BINDING_v1"
MAX_EXECUTION_CATALOG_AGE_SECONDS = 86400

FRESHNESS_KEYS = {
    "schema", "snapshot_sha256", "snapshot_id", "snapshot_observed_at",
    "checked_at", "max_age_seconds", "age_seconds", "pricing_window_valid",
    "model_catalog_fresh", "provider_call_authorized", "credential_authorized",
    "spend_authorized", "live_execution_performed", "runtime",
}

BINDING_KEYS = {
    "schema", "pilot_dry_run_sha256", "catalog_freshness_sha256",
    "provider", "model_id", "checked_at", "fresh_catalog_bound",
    "provider_call_authorized", "credential_authorized", "spend_authorized",
    "live_execution_performed", "runtime",
}


def _parse_utc(value: Any, code: str) -> datetime:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value)),
        code,
    )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RuntimeError(code) from exc
    require(parsed.tzinfo == timezone.utc, code)
    return parsed


def _validate_pricing_window(snapshot: dict[str, Any], checked: datetime) -> None:
    checked_date = checked.date()
    for entry in snapshot["entries"]:
        valid_through = entry["pricing_valid_through"]
        if valid_through is None:
            continue
        require(
            checked_date <= datetime.strptime(valid_through, "%Y-%m-%d").date(),
            "CATALOG_PRICING_WINDOW_EXPIRED",
        )


def build_catalog_freshness_receipt(
    snapshot: dict[str, Any],
    *,
    checked_at: str,
    max_age_seconds: int = MAX_EXECUTION_CATALOG_AGE_SECONDS,
) -> dict[str, Any]:
    validate_provider_catalog(snapshot)
    observed = _parse_utc(snapshot["observed_at"], "CATALOG_FRESHNESS_OBSERVED_AT")
    checked = _parse_utc(checked_at, "CATALOG_FRESHNESS_CHECKED_AT")
    require(checked >= observed, "CATALOG_FRESHNESS_CHECK_BEFORE_SNAPSHOT")
    require(
        isinstance(max_age_seconds, int)
        and not isinstance(max_age_seconds, bool)
        and 1 <= max_age_seconds <= MAX_EXECUTION_CATALOG_AGE_SECONDS,
        "CATALOG_FRESHNESS_MAX_AGE",
    )
    age_seconds = int((checked - observed).total_seconds())
    require(age_seconds <= max_age_seconds, "CATALOG_SNAPSHOT_STALE")
    _validate_pricing_window(snapshot, checked)

    receipt = {
        "schema": FRESHNESS_SCHEMA,
        "snapshot_sha256": sha256_json(snapshot),
        "snapshot_id": snapshot["snapshot_id"],
        "snapshot_observed_at": snapshot["observed_at"],
        "checked_at": checked_at,
        "max_age_seconds": max_age_seconds,
        "age_seconds": age_seconds,
        "pricing_window_valid": True,
        "model_catalog_fresh": True,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_execution_performed": False,
        "runtime": "OFF",
    }
    return validate_catalog_freshness_receipt(snapshot, receipt)


def validate_catalog_freshness_receipt(
    snapshot: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    validate_provider_catalog(snapshot)
    require(isinstance(receipt, dict) and set(receipt) == FRESHNESS_KEYS, "CATALOG_FRESHNESS_SCHEMA_KEYS")
    require(receipt["schema"] == FRESHNESS_SCHEMA, "CATALOG_FRESHNESS_SCHEMA_VERSION")
    require(receipt["snapshot_sha256"] == sha256_json(snapshot), "CATALOG_FRESHNESS_SNAPSHOT_SHA256_MISMATCH")
    require(receipt["snapshot_id"] == snapshot["snapshot_id"], "CATALOG_FRESHNESS_SNAPSHOT_ID_MISMATCH")
    require(receipt["snapshot_observed_at"] == snapshot["observed_at"], "CATALOG_FRESHNESS_OBSERVED_AT_MISMATCH")

    observed = _parse_utc(receipt["snapshot_observed_at"], "CATALOG_FRESHNESS_OBSERVED_AT")
    checked = _parse_utc(receipt["checked_at"], "CATALOG_FRESHNESS_CHECKED_AT")
    require(checked >= observed, "CATALOG_FRESHNESS_CHECK_BEFORE_SNAPSHOT")

    max_age_seconds = receipt["max_age_seconds"]
    require(
        isinstance(max_age_seconds, int)
        and not isinstance(max_age_seconds, bool)
        and 1 <= max_age_seconds <= MAX_EXECUTION_CATALOG_AGE_SECONDS,
        "CATALOG_FRESHNESS_MAX_AGE",
    )
    age_seconds = int((checked - observed).total_seconds())
    require(receipt["age_seconds"] == age_seconds, "CATALOG_FRESHNESS_AGE_MISMATCH")
    require(age_seconds <= max_age_seconds, "CATALOG_SNAPSHOT_STALE")
    _validate_pricing_window(snapshot, checked)
    require(receipt["pricing_window_valid"] is True, "CATALOG_PRICING_WINDOW_NOT_VALID")
    require(receipt["model_catalog_fresh"] is True, "CATALOG_NOT_FRESH")

    for key in ("provider_call_authorized", "credential_authorized", "spend_authorized", "live_execution_performed"):
        require(receipt[key] is False, f"CATALOG_FRESHNESS_FORBIDDEN_TRUE:{key}")
    require(receipt["runtime"] == "OFF", "CATALOG_FRESHNESS_RUNTIME_NOT_OFF")
    return receipt


def catalog_freshness_sha256(snapshot: dict[str, Any], receipt: dict[str, Any]) -> str:
    validate_catalog_freshness_receipt(snapshot, receipt)
    return sha256_json(receipt)


def build_pilot_freshness_binding(
    snapshot: dict[str, Any],
    pilot_plan: dict[str, Any],
    freshness_receipt: dict[str, Any],
) -> dict[str, Any]:
    validate_first_provider_pilot_dry_run(snapshot, pilot_plan)
    validate_catalog_freshness_receipt(snapshot, freshness_receipt)
    binding = {
        "schema": PILOT_FRESHNESS_BINDING_SCHEMA,
        "pilot_dry_run_sha256": first_provider_pilot_dry_run_sha256(snapshot, pilot_plan),
        "catalog_freshness_sha256": catalog_freshness_sha256(snapshot, freshness_receipt),
        "provider": pilot_plan["provider"],
        "model_id": pilot_plan["model_id"],
        "checked_at": freshness_receipt["checked_at"],
        "fresh_catalog_bound": True,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_execution_performed": False,
        "runtime": "OFF",
    }
    return validate_pilot_freshness_binding(snapshot, pilot_plan, freshness_receipt, binding)


def validate_pilot_freshness_binding(
    snapshot: dict[str, Any],
    pilot_plan: dict[str, Any],
    freshness_receipt: dict[str, Any],
    binding: dict[str, Any],
) -> dict[str, Any]:
    validate_first_provider_pilot_dry_run(snapshot, pilot_plan)
    validate_catalog_freshness_receipt(snapshot, freshness_receipt)
    require(isinstance(binding, dict) and set(binding) == BINDING_KEYS, "PILOT_FRESHNESS_BINDING_SCHEMA_KEYS")
    require(binding["schema"] == PILOT_FRESHNESS_BINDING_SCHEMA, "PILOT_FRESHNESS_BINDING_SCHEMA_VERSION")
    require(binding["pilot_dry_run_sha256"] == first_provider_pilot_dry_run_sha256(snapshot, pilot_plan), "PILOT_FRESHNESS_PLAN_SHA256_MISMATCH")
    require(binding["catalog_freshness_sha256"] == catalog_freshness_sha256(snapshot, freshness_receipt), "PILOT_FRESHNESS_RECEIPT_SHA256_MISMATCH")
    require(binding["provider"] == pilot_plan["provider"], "PILOT_FRESHNESS_PROVIDER_MISMATCH")
    require(binding["model_id"] == pilot_plan["model_id"], "PILOT_FRESHNESS_MODEL_MISMATCH")
    require(binding["checked_at"] == freshness_receipt["checked_at"], "PILOT_FRESHNESS_CHECKED_AT_MISMATCH")
    require(binding["fresh_catalog_bound"] is True, "PILOT_FRESHNESS_NOT_BOUND")
    for key in ("provider_call_authorized", "credential_authorized", "spend_authorized", "live_execution_performed"):
        require(binding[key] is False, f"PILOT_FRESHNESS_FORBIDDEN_TRUE:{key}")
    require(binding["runtime"] == "OFF", "PILOT_FRESHNESS_RUNTIME_NOT_OFF")
    return binding


def pilot_freshness_binding_sha256(
    snapshot: dict[str, Any],
    pilot_plan: dict[str, Any],
    freshness_receipt: dict[str, Any],
    binding: dict[str, Any],
) -> str:
    validate_pilot_freshness_binding(snapshot, pilot_plan, freshness_receipt, binding)
    return sha256_json(binding)
