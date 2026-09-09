from __future__ import annotations

import re
from typing import Any

from automation.multimodel_research_v1.model import (
    require,
    sha256_json,
)
from automation.multimodel_research_v1.provider_catalog import (
    catalog_entry,
    validate_first_smoke_candidate,
    validate_provider_catalog,
)

PILOT_DRY_RUN_SCHEMA = "MULTIVERSE_FIRST_PROVIDER_PILOT_DRY_RUN_v1"

PILOT_DRY_RUN_KEYS = {
    "schema",
    "plan_id",
    "phase",
    "prelive_candidate_head",
    "prelive_candidate_seal_blob",
    "catalog_snapshot_sha256",
    "provider",
    "model_id",
    "catalog_entry_sha256",
    "planned_provider_count",
    "planned_call_count",
    "max_attempts",
    "max_input_tokens",
    "max_output_tokens",
    "estimated_max_cost_usd_micros",
    "data_ceiling",
    "structured_output",
    "network_execution_in_repository",
    "credential_material_in_repository",
    "provider_call_authority_required",
    "credential_authority_required",
    "spend_authority_required",
    "provider_call_authorized",
    "credential_authorized",
    "spend_authorized",
    "live_execution_performed",
    "runtime",
    "adoption_authority",
}

MATRIX_ROW_KEYS = {
    "provider",
    "model_id",
    "estimated_max_cost_usd_micros",
    "selection_authority",
    "selected",
    "spend_authority",
}


def _git_sha1(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"[0-9a-f]{40}", value)),
        code,
    )
    return value


def _identifier(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(
            re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}",
                value,
            )
        ),
        code,
    )
    return value


def build_first_provider_pilot_dry_run(
    snapshot: dict[str, Any],
    provider: str,
    *,
    prelive_candidate_head: str,
    prelive_candidate_seal_blob: str,
    max_input_tokens: int = 32768,
    max_output_tokens: int = 4096,
    max_cost_usd_micros: int = 1_000_000,
) -> dict[str, Any]:
    validate_provider_catalog(snapshot)
    _git_sha1(
        prelive_candidate_head,
        "PILOT_PRELIVE_HEAD",
    )
    _git_sha1(
        prelive_candidate_seal_blob,
        "PILOT_PRELIVE_SEAL_BLOB",
    )

    candidate = validate_first_smoke_candidate(
        snapshot,
        provider,
        max_input_tokens=max_input_tokens,
        max_output_tokens=max_output_tokens,
        max_cost_usd_micros=max_cost_usd_micros,
    )

    plan = {
        "schema": PILOT_DRY_RUN_SCHEMA,
        "plan_id": "first-provider-pilot-dry-run-001",
        "phase": "PHASE_B_FIRST_PROVIDER_PILOT_PREPARATION_ONLY",
        "prelive_candidate_head": prelive_candidate_head,
        "prelive_candidate_seal_blob": prelive_candidate_seal_blob,
        "catalog_snapshot_sha256": sha256_json(snapshot),
        "provider": candidate["provider"],
        "model_id": candidate["model_id"],
        "catalog_entry_sha256": candidate["catalog_entry_sha256"],
        "planned_provider_count": 1,
        "planned_call_count": 1,
        "max_attempts": 1,
        "max_input_tokens": max_input_tokens,
        "max_output_tokens": max_output_tokens,
        "estimated_max_cost_usd_micros":
            candidate["estimated_max_cost_usd_micros"],
        "data_ceiling": "SYNTHETIC_ONLY",
        "structured_output": "JSON_ONLY",
        "network_execution_in_repository": False,
        "credential_material_in_repository": False,
        "provider_call_authority_required": True,
        "credential_authority_required": True,
        "spend_authority_required": True,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_execution_performed": False,
        "runtime": "OFF",
        "adoption_authority": False,
    }
    validate_first_provider_pilot_dry_run(
        snapshot,
        plan,
    )
    return plan


def validate_first_provider_pilot_dry_run(
    snapshot: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    validate_provider_catalog(snapshot)

    require(
        isinstance(plan, dict)
        and set(plan) == PILOT_DRY_RUN_KEYS,
        "PILOT_SCHEMA_KEYS",
    )
    require(
        plan["schema"] == PILOT_DRY_RUN_SCHEMA,
        "PILOT_SCHEMA_VERSION",
    )
    _identifier(plan["plan_id"], "PILOT_PLAN_ID")
    require(
        plan["phase"]
        == "PHASE_B_FIRST_PROVIDER_PILOT_PREPARATION_ONLY",
        "PILOT_PHASE",
    )
    _git_sha1(
        plan["prelive_candidate_head"],
        "PILOT_PRELIVE_HEAD",
    )
    _git_sha1(
        plan["prelive_candidate_seal_blob"],
        "PILOT_PRELIVE_SEAL_BLOB",
    )
    require(
        plan["catalog_snapshot_sha256"]
        == sha256_json(snapshot),
        "PILOT_CATALOG_SNAPSHOT_SHA256_MISMATCH",
    )

    entry = catalog_entry(
        snapshot,
        plan["provider"],
    )
    require(
        plan["model_id"] == entry["model_id"],
        "PILOT_MODEL_ID_MISMATCH",
    )

    candidate = validate_first_smoke_candidate(
        snapshot,
        plan["provider"],
        max_input_tokens=plan["max_input_tokens"],
        max_output_tokens=plan["max_output_tokens"],
        max_cost_usd_micros=1_000_000,
    )
    require(
        plan["catalog_entry_sha256"]
        == candidate["catalog_entry_sha256"],
        "PILOT_CATALOG_ENTRY_SHA256_MISMATCH",
    )
    require(
        plan["estimated_max_cost_usd_micros"]
        == candidate["estimated_max_cost_usd_micros"],
        "PILOT_COST_ESTIMATE_MISMATCH",
    )

    require(
        plan["planned_provider_count"] == 1,
        "PILOT_EXACTLY_ONE_PROVIDER",
    )
    require(
        plan["planned_call_count"] == 1,
        "PILOT_EXACTLY_ONE_CALL",
    )
    require(
        plan["max_attempts"] == 1,
        "PILOT_EXACTLY_ONE_ATTEMPT",
    )
    require(
        plan["data_ceiling"] == "SYNTHETIC_ONLY",
        "PILOT_SYNTHETIC_ONLY",
    )
    require(
        plan["structured_output"] == "JSON_ONLY",
        "PILOT_JSON_ONLY",
    )

    require(
        plan["network_execution_in_repository"] is False,
        "PILOT_NETWORK_EXECUTION_FORBIDDEN",
    )
    require(
        plan["credential_material_in_repository"] is False,
        "PILOT_CREDENTIAL_MATERIAL_FORBIDDEN",
    )

    for key in (
        "provider_call_authority_required",
        "credential_authority_required",
        "spend_authority_required",
    ):
        require(
            plan[key] is True,
            f"PILOT_AUTHORITY_REQUIRED:{key}",
        )

    for key in (
        "provider_call_authorized",
        "credential_authorized",
        "spend_authorized",
        "live_execution_performed",
        "adoption_authority",
    ):
        require(
            plan[key] is False,
            f"PILOT_FORBIDDEN_TRUE:{key}",
        )

    require(
        plan["runtime"] == "OFF",
        "PILOT_RUNTIME_NOT_OFF",
    )
    return plan


def first_provider_pilot_dry_run_sha256(
    snapshot: dict[str, Any],
    plan: dict[str, Any],
) -> str:
    validate_first_provider_pilot_dry_run(
        snapshot,
        plan,
    )
    return sha256_json(plan)


def build_pilot_candidate_matrix(
    snapshot: dict[str, Any],
    *,
    max_input_tokens: int = 32768,
    max_output_tokens: int = 4096,
) -> list[dict[str, Any]]:
    validate_provider_catalog(snapshot)
    rows = []
    for provider in (
        "GOOGLE_GEMINI",
        "ANTHROPIC_CLAUDE",
    ):
        candidate = validate_first_smoke_candidate(
            snapshot,
            provider,
            max_input_tokens=max_input_tokens,
            max_output_tokens=max_output_tokens,
        )
        row = {
            "provider": provider,
            "model_id": candidate["model_id"],
            "estimated_max_cost_usd_micros":
                candidate["estimated_max_cost_usd_micros"],
            "selection_authority": False,
            "selected": False,
            "spend_authority": False,
        }
        require(
            set(row) == MATRIX_ROW_KEYS,
            "PILOT_MATRIX_ROW_SCHEMA",
        )
        rows.append(row)

    return sorted(
        rows,
        key=lambda item: (
            item["estimated_max_cost_usd_micros"],
            item["provider"],
        ),
    )
