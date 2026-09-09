from __future__ import annotations

import re
from typing import Any

from automation.multimodel_research_v1.catalog_freshness import (
    catalog_freshness_sha256,
    pilot_freshness_binding_sha256,
    validate_catalog_freshness_receipt,
    validate_pilot_freshness_binding,
)
from automation.multimodel_research_v1.model import require, sha256_json
from automation.multimodel_research_v1.pilot_dry_run import (
    first_provider_pilot_dry_run_sha256,
    validate_first_provider_pilot_dry_run,
)
from automation.multimodel_research_v1.time_attestation import (
    catalog_freshness_time_binding_sha256,
    execution_time_attestation_sha256,
    validate_catalog_freshness_time_binding,
    validate_execution_time_attestation,
)

PRE_EXECUTION_BUNDLE_SCHEMA = "MULTIVERSE_PROVIDER_PRE_EXECUTION_BUNDLE_v1"

PRE_EXECUTION_BUNDLE_KEYS = {
    "schema",
    "bundle_id",
    "prelive_candidate_head",
    "prelive_candidate_seal_blob",
    "provider",
    "model_id",
    "catalog_snapshot_sha256",
    "pilot_dry_run_sha256",
    "catalog_freshness_sha256",
    "pilot_freshness_binding_sha256",
    "time_attestation_sha256",
    "catalog_freshness_time_binding_sha256",
    "checked_at",
    "evidence_chain_complete",
    "provider_call_authorized",
    "credential_authorized",
    "spend_authorized",
    "live_execution_performed",
    "runtime",
    "adoption_authority",
}


def _identifier(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}", value)),
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


def build_provider_pre_execution_bundle(
    snapshot: dict[str, Any],
    pilot_plan: dict[str, Any],
    freshness_receipt: dict[str, Any],
    pilot_freshness_binding: dict[str, Any],
    time_attestation: dict[str, Any],
    freshness_time_binding: dict[str, Any],
) -> dict[str, Any]:
    validate_first_provider_pilot_dry_run(snapshot, pilot_plan)
    validate_catalog_freshness_receipt(snapshot, freshness_receipt)
    validate_pilot_freshness_binding(
        snapshot,
        pilot_plan,
        freshness_receipt,
        pilot_freshness_binding,
    )
    validate_execution_time_attestation(time_attestation)
    validate_catalog_freshness_time_binding(
        snapshot,
        freshness_receipt,
        time_attestation,
        freshness_time_binding,
    )

    require(
        pilot_plan["prelive_candidate_head"]
        == time_attestation["prelive_candidate_head"],
        "PRE_EXECUTION_PRELIVE_HEAD_MISMATCH",
    )
    require(
        pilot_plan["prelive_candidate_seal_blob"]
        == time_attestation["prelive_candidate_seal_blob"],
        "PRE_EXECUTION_PRELIVE_SEAL_MISMATCH",
    )

    bundle = {
        "schema": PRE_EXECUTION_BUNDLE_SCHEMA,
        "bundle_id": "first-provider-pre-execution-bundle-001",
        "prelive_candidate_head": pilot_plan["prelive_candidate_head"],
        "prelive_candidate_seal_blob": pilot_plan["prelive_candidate_seal_blob"],
        "provider": pilot_plan["provider"],
        "model_id": pilot_plan["model_id"],
        "catalog_snapshot_sha256": sha256_json(snapshot),
        "pilot_dry_run_sha256":
            first_provider_pilot_dry_run_sha256(snapshot, pilot_plan),
        "catalog_freshness_sha256":
            catalog_freshness_sha256(snapshot, freshness_receipt),
        "pilot_freshness_binding_sha256":
            pilot_freshness_binding_sha256(
                snapshot,
                pilot_plan,
                freshness_receipt,
                pilot_freshness_binding,
            ),
        "time_attestation_sha256":
            execution_time_attestation_sha256(time_attestation),
        "catalog_freshness_time_binding_sha256":
            catalog_freshness_time_binding_sha256(
                snapshot,
                freshness_receipt,
                time_attestation,
                freshness_time_binding,
            ),
        "checked_at": freshness_receipt["checked_at"],
        "evidence_chain_complete": True,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_execution_performed": False,
        "runtime": "OFF",
        "adoption_authority": False,
    }
    return validate_provider_pre_execution_bundle(
        snapshot,
        pilot_plan,
        freshness_receipt,
        pilot_freshness_binding,
        time_attestation,
        freshness_time_binding,
        bundle,
    )


def validate_provider_pre_execution_bundle(
    snapshot: dict[str, Any],
    pilot_plan: dict[str, Any],
    freshness_receipt: dict[str, Any],
    pilot_freshness_binding: dict[str, Any],
    time_attestation: dict[str, Any],
    freshness_time_binding: dict[str, Any],
    bundle: dict[str, Any],
) -> dict[str, Any]:
    validate_first_provider_pilot_dry_run(snapshot, pilot_plan)
    validate_catalog_freshness_receipt(snapshot, freshness_receipt)
    validate_pilot_freshness_binding(
        snapshot,
        pilot_plan,
        freshness_receipt,
        pilot_freshness_binding,
    )
    validate_execution_time_attestation(time_attestation)
    validate_catalog_freshness_time_binding(
        snapshot,
        freshness_receipt,
        time_attestation,
        freshness_time_binding,
    )

    require(
        pilot_plan["prelive_candidate_head"]
        == time_attestation["prelive_candidate_head"],
        "PRE_EXECUTION_PRELIVE_HEAD_MISMATCH",
    )
    require(
        pilot_plan["prelive_candidate_seal_blob"]
        == time_attestation["prelive_candidate_seal_blob"],
        "PRE_EXECUTION_PRELIVE_SEAL_MISMATCH",
    )
    require(
        isinstance(bundle, dict)
        and set(bundle) == PRE_EXECUTION_BUNDLE_KEYS,
        "PRE_EXECUTION_SCHEMA_KEYS",
    )
    require(
        bundle["schema"] == PRE_EXECUTION_BUNDLE_SCHEMA,
        "PRE_EXECUTION_SCHEMA_VERSION",
    )
    _identifier(bundle["bundle_id"], "PRE_EXECUTION_BUNDLE_ID")
    _git_sha1(
        bundle["prelive_candidate_head"],
        "PRE_EXECUTION_PRELIVE_HEAD",
    )
    _git_sha1(
        bundle["prelive_candidate_seal_blob"],
        "PRE_EXECUTION_PRELIVE_SEAL_BLOB",
    )
    require(
        bundle["prelive_candidate_head"]
        == pilot_plan["prelive_candidate_head"],
        "PRE_EXECUTION_PRELIVE_HEAD_MISMATCH",
    )
    require(
        bundle["prelive_candidate_seal_blob"]
        == pilot_plan["prelive_candidate_seal_blob"],
        "PRE_EXECUTION_PRELIVE_SEAL_MISMATCH",
    )
    require(
        bundle["provider"] == pilot_plan["provider"],
        "PRE_EXECUTION_PROVIDER_MISMATCH",
    )
    require(
        bundle["model_id"] == pilot_plan["model_id"],
        "PRE_EXECUTION_MODEL_MISMATCH",
    )
    require(
        bundle["catalog_snapshot_sha256"] == sha256_json(snapshot),
        "PRE_EXECUTION_CATALOG_SNAPSHOT_SHA256_MISMATCH",
    )
    require(
        bundle["pilot_dry_run_sha256"]
        == first_provider_pilot_dry_run_sha256(snapshot, pilot_plan),
        "PRE_EXECUTION_PILOT_SHA256_MISMATCH",
    )
    require(
        bundle["catalog_freshness_sha256"]
        == catalog_freshness_sha256(snapshot, freshness_receipt),
        "PRE_EXECUTION_FRESHNESS_SHA256_MISMATCH",
    )
    require(
        bundle["pilot_freshness_binding_sha256"]
        == pilot_freshness_binding_sha256(
            snapshot,
            pilot_plan,
            freshness_receipt,
            pilot_freshness_binding,
        ),
        "PRE_EXECUTION_PILOT_FRESHNESS_SHA256_MISMATCH",
    )
    require(
        bundle["time_attestation_sha256"]
        == execution_time_attestation_sha256(time_attestation),
        "PRE_EXECUTION_TIME_ATTESTATION_SHA256_MISMATCH",
    )
    require(
        bundle["catalog_freshness_time_binding_sha256"]
        == catalog_freshness_time_binding_sha256(
            snapshot,
            freshness_receipt,
            time_attestation,
            freshness_time_binding,
        ),
        "PRE_EXECUTION_FRESHNESS_TIME_SHA256_MISMATCH",
    )
    require(
        bundle["checked_at"] == freshness_receipt["checked_at"],
        "PRE_EXECUTION_CHECKED_AT_MISMATCH",
    )
    require(
        bundle["checked_at"] == time_attestation["attested_at"],
        "PRE_EXECUTION_ATTESTED_AT_MISMATCH",
    )
    require(
        bundle["evidence_chain_complete"] is True,
        "PRE_EXECUTION_EVIDENCE_CHAIN_INCOMPLETE",
    )
    for key in (
        "provider_call_authorized",
        "credential_authorized",
        "spend_authorized",
        "live_execution_performed",
        "adoption_authority",
    ):
        require(
            bundle[key] is False,
            f"PRE_EXECUTION_FORBIDDEN_TRUE:{key}",
        )
    require(
        bundle["runtime"] == "OFF",
        "PRE_EXECUTION_RUNTIME_NOT_OFF",
    )
    return bundle


def provider_pre_execution_bundle_sha256(
    snapshot: dict[str, Any],
    pilot_plan: dict[str, Any],
    freshness_receipt: dict[str, Any],
    pilot_freshness_binding: dict[str, Any],
    time_attestation: dict[str, Any],
    freshness_time_binding: dict[str, Any],
    bundle: dict[str, Any],
) -> str:
    validate_provider_pre_execution_bundle(
        snapshot,
        pilot_plan,
        freshness_receipt,
        pilot_freshness_binding,
        time_attestation,
        freshness_time_binding,
        bundle,
    )
    return sha256_json(bundle)
