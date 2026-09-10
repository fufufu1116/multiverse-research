from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from automation.multimodel_research_v1.catalog_freshness import (
    catalog_freshness_sha256,
    validate_catalog_freshness_receipt,
)
from automation.multimodel_research_v1.model import require, sha256_json

TIME_ATTESTATION_SCHEMA = "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1"
FRESHNESS_TIME_BINDING_SCHEMA = "MULTIVERSE_CATALOG_FRESHNESS_TIME_BINDING_v1"

TIME_ATTESTATION_KEYS = {
    "schema",
    "attestation_id",
    "source",
    "source_ref",
    "source_observation_sha256",
    "attested_at",
    "recorded_at",
    "prelive_candidate_head",
    "prelive_candidate_seal_blob",
    "provider_call_authorized",
    "credential_authorized",
    "spend_authorized",
    "live_execution_performed",
    "runtime",
}

FRESHNESS_TIME_BINDING_KEYS = {
    "schema",
    "catalog_freshness_sha256",
    "time_attestation_sha256",
    "snapshot_id",
    "checked_at",
    "attested_at",
    "time_exact_match",
    "provider_call_authorized",
    "credential_authorized",
    "spend_authorized",
    "live_execution_performed",
    "runtime",
}

MAX_RECORDING_DELAY_SECONDS = 60


def _identifier(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}", value)),
        code,
    )
    return value


def _sha256(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"[0-9a-f]{64}", value)),
        code,
    )
    return value


def _git_sha1(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"[0-9a-f]{40}", value)),
        code,
    )
    return value


def _parse_utc(value: Any, code: str) -> datetime:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value)),
        code,
    )
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RuntimeError(code) from exc


def validate_execution_time_attestation(
    attestation: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(attestation, dict)
        and set(attestation) == TIME_ATTESTATION_KEYS,
        "TIME_ATTESTATION_SCHEMA_KEYS",
    )
    require(
        attestation["schema"] == TIME_ATTESTATION_SCHEMA,
        "TIME_ATTESTATION_SCHEMA_VERSION",
    )
    _identifier(attestation["attestation_id"], "TIME_ATTESTATION_ID")
    require(
        attestation["source"] == "CONTROL_RUNTIME_CLOCK",
        "TIME_ATTESTATION_SOURCE",
    )
    _identifier(attestation["source_ref"], "TIME_ATTESTATION_SOURCE_REF")
    _sha256(
        attestation["source_observation_sha256"],
        "TIME_ATTESTATION_SOURCE_SHA256",
    )
    attested = _parse_utc(
        attestation["attested_at"],
        "TIME_ATTESTATION_ATTESTED_AT",
    )
    recorded = _parse_utc(
        attestation["recorded_at"],
        "TIME_ATTESTATION_RECORDED_AT",
    )
    require(
        recorded >= attested,
        "TIME_ATTESTATION_RECORDED_BEFORE_ATTESTED",
    )
    require(
        int((recorded - attested).total_seconds())
        <= MAX_RECORDING_DELAY_SECONDS,
        "TIME_ATTESTATION_RECORDING_DELAY_EXCEEDED",
    )
    _git_sha1(
        attestation["prelive_candidate_head"],
        "TIME_ATTESTATION_PRELIVE_HEAD",
    )
    _git_sha1(
        attestation["prelive_candidate_seal_blob"],
        "TIME_ATTESTATION_PRELIVE_SEAL_BLOB",
    )

    for key in (
        "provider_call_authorized",
        "credential_authorized",
        "spend_authorized",
        "live_execution_performed",
    ):
        require(
            attestation[key] is False,
            f"TIME_ATTESTATION_FORBIDDEN_TRUE:{key}",
        )
    require(
        attestation["runtime"] == "OFF",
        "TIME_ATTESTATION_RUNTIME_NOT_OFF",
    )
    return attestation


def execution_time_attestation_sha256(
    attestation: dict[str, Any],
) -> str:
    validate_execution_time_attestation(attestation)
    return sha256_json(attestation)


def build_catalog_freshness_time_binding(
    snapshot: dict[str, Any],
    freshness_receipt: dict[str, Any],
    time_attestation: dict[str, Any],
) -> dict[str, Any]:
    validate_catalog_freshness_receipt(snapshot, freshness_receipt)
    validate_execution_time_attestation(time_attestation)

    require(
        freshness_receipt["checked_at"]
        == time_attestation["attested_at"],
        "FRESHNESS_TIME_NOT_EXACT",
    )

    binding = {
        "schema": FRESHNESS_TIME_BINDING_SCHEMA,
        "catalog_freshness_sha256":
            catalog_freshness_sha256(snapshot, freshness_receipt),
        "time_attestation_sha256":
            execution_time_attestation_sha256(time_attestation),
        "snapshot_id": freshness_receipt["snapshot_id"],
        "checked_at": freshness_receipt["checked_at"],
        "attested_at": time_attestation["attested_at"],
        "time_exact_match": True,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_execution_performed": False,
        "runtime": "OFF",
    }
    return validate_catalog_freshness_time_binding(
        snapshot,
        freshness_receipt,
        time_attestation,
        binding,
    )


def validate_catalog_freshness_time_binding(
    snapshot: dict[str, Any],
    freshness_receipt: dict[str, Any],
    time_attestation: dict[str, Any],
    binding: dict[str, Any],
) -> dict[str, Any]:
    validate_catalog_freshness_receipt(snapshot, freshness_receipt)
    validate_execution_time_attestation(time_attestation)
    require(
        isinstance(binding, dict)
        and set(binding) == FRESHNESS_TIME_BINDING_KEYS,
        "FRESHNESS_TIME_BINDING_SCHEMA_KEYS",
    )
    require(
        binding["schema"] == FRESHNESS_TIME_BINDING_SCHEMA,
        "FRESHNESS_TIME_BINDING_SCHEMA_VERSION",
    )
    require(
        binding["catalog_freshness_sha256"]
        == catalog_freshness_sha256(snapshot, freshness_receipt),
        "FRESHNESS_TIME_CATALOG_SHA256_MISMATCH",
    )
    require(
        binding["time_attestation_sha256"]
        == execution_time_attestation_sha256(time_attestation),
        "FRESHNESS_TIME_ATTESTATION_SHA256_MISMATCH",
    )
    require(
        binding["snapshot_id"] == freshness_receipt["snapshot_id"],
        "FRESHNESS_TIME_SNAPSHOT_ID_MISMATCH",
    )
    require(
        binding["checked_at"] == freshness_receipt["checked_at"],
        "FRESHNESS_TIME_CHECKED_AT_MISMATCH",
    )
    require(
        binding["attested_at"] == time_attestation["attested_at"],
        "FRESHNESS_TIME_ATTESTED_AT_MISMATCH",
    )
    require(
        binding["checked_at"] == binding["attested_at"],
        "FRESHNESS_TIME_NOT_EXACT",
    )
    require(
        binding["time_exact_match"] is True,
        "FRESHNESS_TIME_EXACT_MATCH_FALSE",
    )
    for key in (
        "provider_call_authorized",
        "credential_authorized",
        "spend_authorized",
        "live_execution_performed",
    ):
        require(
            binding[key] is False,
            f"FRESHNESS_TIME_FORBIDDEN_TRUE:{key}",
        )
    require(
        binding["runtime"] == "OFF",
        "FRESHNESS_TIME_RUNTIME_NOT_OFF",
    )
    return binding


def catalog_freshness_time_binding_sha256(
    snapshot: dict[str, Any],
    freshness_receipt: dict[str, Any],
    time_attestation: dict[str, Any],
    binding: dict[str, Any],
) -> str:
    validate_catalog_freshness_time_binding(
        snapshot,
        freshness_receipt,
        time_attestation,
        binding,
    )
    return sha256_json(binding)
