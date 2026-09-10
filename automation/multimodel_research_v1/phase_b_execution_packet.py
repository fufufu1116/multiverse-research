from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from automation.multimodel_research_v1.assignment import assignment_sha256
from automation.multimodel_research_v1.catalog_freshness import (
    build_catalog_freshness_receipt,
    catalog_freshness_sha256,
    validate_catalog_freshness_receipt,
)
from automation.multimodel_research_v1.model import (
    NONAUTHORITY_KEYS,
    ResearchContractError,
    require,
    sha256_json,
    validate_task,
)
from automation.multimodel_research_v1.pilot_matrix import (
    PROVIDER_MAP,
    build_provider_pilot_matrix,
    provider_pilot_matrix_sha256,
    validate_provider_pilot_matrix,
)
from automation.multimodel_research_v1.provider_catalog import (
    estimate_smoke_cost_usd_micros,
    validate_provider_catalog,
)
from automation.multimodel_research_v1.provider_result_schema import (
    build_result_v2_response_schema,
    result_v2_response_schema_sha256,
    validate_result_v2_response_schema,
)

ROOT = Path(__file__).resolve().parent

PACKET_SCHEMA = "MULTIVERSE_PHASE_B_FIRST_PROVIDER_EXECUTION_PACKET_v1"
VERIFICATION_SCHEMA = "MULTIVERSE_PROVIDER_OFFICIAL_VERIFICATION_v1"
SELECTION_SCHEMA = "MULTIVERSE_FIRST_PROVIDER_MECHANICAL_SELECTION_v1"
INGESTION_REQUIREMENTS_SCHEMA = "MULTIVERSE_RESULT_INGESTION_REQUIREMENTS_v1"
TERMINATION_RECEIPT_REQUIREMENTS_SCHEMA = "MULTIVERSE_TERMINATION_RECEIPT_REQUIREMENTS_v1"

CATALOG_PATH = ROOT / "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260910.json"
OFFICIAL_VERIFICATION_PATH = ROOT / "PROVIDER_OFFICIAL_VERIFICATION_20260910T144300Z.json"

CANONICAL_MAIN = "60229531f33eefe950abee2c8e46ac834b2e6a60"
CANONICAL_TREE = "0e341a40c82585751ee0cee52aba401dc6559f05"
CANONICAL_MULTIMODEL_SUBTREE = "f7a1fa70dc2410b47a15a47b6dac9252d665ef32"

CATALOG_CHECKED_AT = "2026-09-10T14:43:00Z"
CATALOG_MAX_AGE_SECONDS = 86400
FIRST_SMOKE_MAX_INPUT_TOKENS = 32768
FIRST_SMOKE_MAX_OUTPUT_TOKENS = 4096
REPOSITORY_MAX_COST_USD_MICROS = 1_000_000
TASK_MAX_COMPUTE_SECONDS = 120
TASK_MAX_OUTPUT_BYTES = 50000
TASK_MAX_FINDINGS = 3

SYNTHETIC_FIXTURE = (
    "Synthetic architecture challenge only. A dispatcher accepts a bounded research task, "
    "routes it to one advisory model, and must preserve fail-closed authority boundaries. "
    "Identify up to three architectural failure modes and propose deterministic repository-only validations. "
    "Do not use external facts, private data, live business data, tools, search, file access, memory, or function calls."
)
SYNTHETIC_FIXTURE_SHA256 = hashlib.sha256(SYNTHETIC_FIXTURE.encode()).hexdigest()

WIRE_SCHEMA_ALLOWED_KEYS = {
    "type",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "enum",
    "format",
    "title",
    "description",
}
WIRE_SCHEMA_STRIPPED_KEYS = {
    "minLength",
    "maxLength",
    "pattern",
    "minimum",
    "maximum",
    "minItems",
    "maxItems",
}

PROVIDER_EXPECTATIONS = {
    "GOOGLE_GEMINI": {
        "model_id": "gemini-3.8-flash",
        "lifecycle": "GA",
        "input_usd_micros_per_million_tokens": 750000,
        "output_usd_micros_per_million_tokens": 3750000,
        "transport_policy_ref": "gemini-interactions-v1-stable",
        "allowed_host": "generativelanguage.googleapis.com",
        "allowed_operation": "INTERACTIONS_CREATE_V1",
        "sdk_surface": "interactions.create",
        "api_version": "v1",
    },
    "ANTHROPIC_CLAUDE": {
        "model_id": "claude-haiku-4-5-20251001",
        "lifecycle": "CURRENT",
        "input_usd_micros_per_million_tokens": 1000000,
        "output_usd_micros_per_million_tokens": 5000000,
        "transport_policy_ref": "claude-messages-v1",
        "allowed_host": "api.anthropic.com",
        "allowed_operation": "MESSAGES_CREATE_V1",
        "sdk_surface": "messages.create",
        "api_version": "v1",
    },
}

PACKET_KEYS = {
    "schema",
    "packet_id",
    "canonical",
    "catalog",
    "official_verification",
    "eligible_provider_comparison",
    "mechanical_selection",
    "synthetic_task",
    "strict_local_result_schema",
    "provider_wire_response_schema",
    "pilot_matrix",
    "result_ingestion_requirements",
    "termination_receipt_requirements",
    "limits",
    "authority",
    "hashes",
}

FORBIDDEN_CAPABILITIES = (
    "tools",
    "provider_retrieval_search",
    "code_execution",
    "file_access",
    "provider_memory",
    "function_calling",
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f"JSON_OBJECT_REQUIRED:{path.name}")
    return value


def catalog_snapshot() -> dict[str, Any]:
    value = _read_json(CATALOG_PATH)
    validate_provider_catalog(value)
    return value


def official_verification() -> dict[str, Any]:
    return _read_json(OFFICIAL_VERIFICATION_PATH)


def _nonauthority() -> dict[str, bool]:
    return {key: False for key in sorted(NONAUTHORITY_KEYS)}


def synthetic_task() -> dict[str, Any]:
    task = {
        "schema": "MULTIVERSE_RESEARCH_TASK_v2",
        "task_id": "phase-b-first-provider-pilot-synthetic-001",
        "snapshot_id": "phase-b-first-provider-pilot-synthetic-snapshot-001",
        "created_at": "2026-09-10T11:31:00Z",
        "domain": "core",
        "objective": SYNTHETIC_FIXTURE,
        "source_refs": [
            {
                "kind": "SYNTHETIC_FIXTURE",
                "ref": "phase-b-first-provider-pilot-synthetic-fixture-001",
                "sha256": SYNTHETIC_FIXTURE_SHA256,
                "observed_at": "2026-09-10T11:31:00Z",
            }
        ],
        "allowed_primitives": ["SYNTHETIC_FIXTURE"],
        "constraints": {
            "network_access": "NONE",
            "max_compute_seconds": TASK_MAX_COMPUTE_SECONDS,
            "max_output_bytes": TASK_MAX_OUTPUT_BYTES,
            "max_findings": TASK_MAX_FINDINGS,
        },
        "requested_roles": ["architecture_challenge"],
        "nonauthority": _nonauthority(),
        "evidence_manifest": [
            {
                "primitive": "SYNTHETIC_FIXTURE",
                "ref": "phase-b-first-provider-pilot-synthetic-fixture-001",
                "sha256": SYNTHETIC_FIXTURE_SHA256,
                "observed_at": "2026-09-10T11:31:00Z",
            }
        ],
    }
    return validate_task(task)


def _validate_common_wire_node(node: Any) -> None:
    require(isinstance(node, dict), "WIRE_SCHEMA_NODE_OBJECT")
    unknown = set(node) - WIRE_SCHEMA_ALLOWED_KEYS
    require(
        not unknown,
        "WIRE_SCHEMA_UNSUPPORTED_KEY:" + ",".join(sorted(unknown)),
    )
    require(
        not (set(node) & WIRE_SCHEMA_STRIPPED_KEYS),
        "WIRE_SCHEMA_STRIPPED_CONSTRAINT_PRESENT",
    )
    properties = node.get("properties")
    if properties is not None:
        require(isinstance(properties, dict), "WIRE_SCHEMA_PROPERTIES")
        for child in properties.values():
            _validate_common_wire_node(child)
    items = node.get("items")
    if items is not None:
        _validate_common_wire_node(items)


def build_common_wire_schema(strict_schema: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(strict_schema, dict), "WIRE_SCHEMA_SOURCE_OBJECT")

    def reduce_node(node: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key in WIRE_SCHEMA_STRIPPED_KEYS:
                continue
            require(key in WIRE_SCHEMA_ALLOWED_KEYS, f"WIRE_SCHEMA_SOURCE_KEY:{key}")
            if key == "properties":
                require(isinstance(value, dict), "WIRE_SCHEMA_SOURCE_PROPERTIES")
                out[key] = {
                    prop: reduce_node(child)
                    for prop, child in value.items()
                }
            elif key == "items":
                require(isinstance(value, dict), "WIRE_SCHEMA_SOURCE_ITEMS")
                out[key] = reduce_node(value)
            else:
                out[key] = copy.deepcopy(value)
        return out

    wire = reduce_node(strict_schema)
    _validate_common_wire_node(wire)
    require(wire != strict_schema, "WIRE_SCHEMA_EXPECTED_STRICTER_LOCAL_SCHEMA")
    return wire


def validate_official_verification(
    snapshot: dict[str, Any],
    verification: dict[str, Any],
) -> dict[str, Any]:
    validate_provider_catalog(snapshot)
    require(isinstance(verification, dict), "OFFICIAL_VERIFICATION_OBJECT")
    require(
        set(verification)
        == {
            "schema",
            "checked_at",
            "catalog_snapshot_id",
            "providers",
            "selection_scope",
            "runtime",
            "provider_call_authorized",
            "credential_authorized",
            "spend_authorized",
        },
        "OFFICIAL_VERIFICATION_KEYS",
    )
    require(verification["schema"] == VERIFICATION_SCHEMA, "OFFICIAL_VERIFICATION_SCHEMA")
    require(verification["checked_at"] == CATALOG_CHECKED_AT, "OFFICIAL_VERIFICATION_TIME")
    require(
        verification["catalog_snapshot_id"] == snapshot["snapshot_id"],
        "OFFICIAL_VERIFICATION_CATALOG",
    )
    require(
        verification["selection_scope"]
        == "ALL_CATALOG_PROVIDERS_STABLE_STRUCTURED_TRANSPORT_ELIGIBLE",
        "OFFICIAL_VERIFICATION_SCOPE",
    )
    require(verification["runtime"] == "OFF", "OFFICIAL_VERIFICATION_RUNTIME")
    for key in ("provider_call_authorized", "credential_authorized", "spend_authorized"):
        require(verification[key] is False, f"OFFICIAL_VERIFICATION_AUTHORITY:{key}")

    rows = verification["providers"]
    require(isinstance(rows, list), "OFFICIAL_VERIFICATION_PROVIDERS")
    by_provider = {row.get("provider"): row for row in rows if isinstance(row, dict)}
    require(
        set(by_provider) == {entry["provider"] for entry in snapshot["entries"]},
        "OFFICIAL_VERIFICATION_PROVIDER_SET",
    )
    catalog_by_provider = {entry["provider"]: entry for entry in snapshot["entries"]}
    for provider, expected in PROVIDER_EXPECTATIONS.items():
        row = by_provider[provider]
        entry = catalog_by_provider[provider]
        require(row["model_id"] == entry["model_id"] == expected["model_id"], f"OFFICIAL_MODEL:{provider}")
        require(row["lifecycle"] == entry["lifecycle"] == expected["lifecycle"], f"OFFICIAL_LIFECYCLE:{provider}")
        require(row["classification"] == entry["classification"] == "PINNED_OR_STABLE", f"OFFICIAL_CLASSIFICATION:{provider}")
        require(row["structured_json"] is True and entry["structured_json"] is True, f"OFFICIAL_STRUCTURED:{provider}")
        require(
            row["input_usd_micros_per_million_tokens"]
            == entry["input_usd_micros_per_million_tokens"]
            == expected["input_usd_micros_per_million_tokens"],
            f"OFFICIAL_INPUT_PRICE:{provider}",
        )
        require(
            row["output_usd_micros_per_million_tokens"]
            == entry["output_usd_micros_per_million_tokens"]
            == expected["output_usd_micros_per_million_tokens"],
            f"OFFICIAL_OUTPUT_PRICE:{provider}",
        )
        spec = PROVIDER_MAP[provider]
        for key in ("transport_policy_ref", "allowed_host", "allowed_operation"):
            require(row[key] == spec[key] == expected[key], f"OFFICIAL_TRANSPORT:{provider}:{key}")
        require(row["sdk_surface"] == expected["sdk_surface"], f"OFFICIAL_SDK_SURFACE:{provider}")
        require(row["api_version"] == expected["api_version"], f"OFFICIAL_API_VERSION:{provider}")
        require(row["common_wire_schema_subset_supported"] is True, f"OFFICIAL_WIRE_SCHEMA:{provider}")
        refs = row["official_evidence_refs"]
        require(isinstance(refs, list) and len(refs) >= 4, f"OFFICIAL_EVIDENCE:{provider}")
        for ref in refs:
            require(isinstance(ref, str) and ref.startswith("https://"), f"OFFICIAL_EVIDENCE_URL:{provider}")
    return verification


def official_verification_sha256(
    snapshot: dict[str, Any],
    verification: dict[str, Any],
) -> str:
    validate_official_verification(snapshot, verification)
    return sha256_json(verification)


def build_eligible_provider_comparison(
    snapshot: dict[str, Any],
    verification: dict[str, Any],
) -> list[dict[str, Any]]:
    validate_provider_catalog(snapshot)
    validate_official_verification(snapshot, verification)
    verified = {row["provider"]: row for row in verification["providers"]}
    rows: list[dict[str, Any]] = []
    for entry in snapshot["entries"]:
        provider = entry["provider"]
        row = verified[provider]
        spec = PROVIDER_MAP.get(provider)
        reasons: list[str] = []
        if entry["classification"] != "PINNED_OR_STABLE":
            reasons.append("NOT_STABLE")
        if entry["lifecycle"] not in {"GA", "CURRENT"}:
            reasons.append("LIFECYCLE_NOT_ELIGIBLE")
        if entry["structured_json"] is not True:
            reasons.append("STRUCTURED_JSON_REQUIRED")
        if row["common_wire_schema_subset_supported"] is not True:
            reasons.append("COMMON_WIRE_SCHEMA_UNSUPPORTED")
        if spec is None:
            reasons.append("NO_TRANSPORT")
        else:
            if row["allowed_host"] != spec["allowed_host"]:
                reasons.append("HOST_MISMATCH")
            if row["allowed_operation"] != spec["allowed_operation"]:
                reasons.append("OPERATION_MISMATCH")
            if row["transport_policy_ref"] != spec["transport_policy_ref"]:
                reasons.append("TRANSPORT_POLICY_MISMATCH")
        cost = estimate_smoke_cost_usd_micros(
            snapshot,
            provider,
            FIRST_SMOKE_MAX_INPUT_TOKENS,
            FIRST_SMOKE_MAX_OUTPUT_TOKENS,
        )
        rows.append(
            {
                "provider": provider,
                "model_id": entry["model_id"],
                "eligible": not reasons,
                "rejection_reasons": sorted(reasons),
                "max_input_tokens": FIRST_SMOKE_MAX_INPUT_TOKENS,
                "max_output_tokens": FIRST_SMOKE_MAX_OUTPUT_TOKENS,
                "estimated_max_cost_usd_micros": cost,
            }
        )
    return sorted(rows, key=lambda item: item["provider"])


def mechanically_select_provider(
    comparison: list[dict[str, Any]],
) -> dict[str, Any]:
    eligible = [row for row in comparison if row["eligible"]]
    require(bool(eligible), "NO_ELIGIBLE_PROVIDER")
    selected = min(
        eligible,
        key=lambda row: (
            row["estimated_max_cost_usd_micros"],
            row["provider"],
            row["model_id"],
        ),
    )
    return {
        "schema": SELECTION_SCHEMA,
        "algorithm": "MIN_ESTIMATED_MAX_COST_THEN_PROVIDER_THEN_MODEL",
        "eligible_provider_count": len(eligible),
        "selected_provider": selected["provider"],
        "selected_model_id": selected["model_id"],
        "selected_estimated_max_cost_usd_micros": selected["estimated_max_cost_usd_micros"],
        "spend_authorized": False,
    }


def _seed_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"placeholder": {"type": "string"}},
        "required": ["placeholder"],
    }


def build_first_provider_execution_packet() -> dict[str, Any]:
    snapshot = catalog_snapshot()
    verification = official_verification()
    validate_official_verification(snapshot, verification)
    freshness = build_catalog_freshness_receipt(
        snapshot,
        checked_at=CATALOG_CHECKED_AT,
        max_age_seconds=CATALOG_MAX_AGE_SECONDS,
    )
    comparison = build_eligible_provider_comparison(snapshot, verification)
    selection = mechanically_select_provider(comparison)
    task = synthetic_task()
    provider = selection["selected_provider"]

    seed = build_provider_pilot_matrix(
        task,
        snapshot,
        provider,
        _seed_response_schema(),
        requested_role="architecture_challenge",
    )
    assignment = seed["assignment"]
    strict_schema = build_result_v2_response_schema(task, assignment)
    validate_result_v2_response_schema(task, assignment, strict_schema)
    wire_schema = build_common_wire_schema(strict_schema)
    matrix = build_provider_pilot_matrix(
        task,
        snapshot,
        provider,
        wire_schema,
        requested_role="architecture_challenge",
    )
    require(matrix["assignment"] == assignment, "PACKET_ASSIGNMENT_CHANGED_WITH_RESPONSE_SCHEMA")

    prep = matrix["execution_prep"]
    require(
        prep["proposed_max_cost_usd_micros"]
        == selection["selected_estimated_max_cost_usd_micros"],
        "PACKET_COST_SELECTION_MISMATCH",
    )

    ingestion_requirements = {
        "schema": INGESTION_REQUIREMENTS_SCHEMA,
        "provider": matrix["assignment"]["target_provider"],
        "assignment_sha256": assignment_sha256(task, matrix["assignment"]),
        "strict_local_result_schema_sha256": result_v2_response_schema_sha256(
            task,
            matrix["assignment"],
            strict_schema,
        ),
        "provider_wire_response_schema_sha256": sha256_json(wire_schema),
        "strict_json_object_required": True,
        "duplicate_keys_rejected": True,
        "nonfinite_numbers_rejected": True,
        "completed_observation_required": True,
        "observed_model_exact_match_required": True,
        "assignment_output_byte_ceiling": matrix["assignment"]["max_output_bytes"],
        "local_result_v2_validation_required": True,
    }
    termination_receipt_requirements = {
        "schema": TERMINATION_RECEIPT_REQUIREMENTS_SCHEMA,
        "assignment_sha256": assignment_sha256(task, matrix["assignment"]),
        "request_envelope_sha256": sha256_json(matrix["request_envelope"]),
        "provider_response_id_required_for_nontransport_failure": True,
        "usage_metadata_sha256_required": True,
        "normalized_terminal_state_required": True,
        "termination_result_status_binding_required": True,
        "provider_response_sha256_required": True,
        "result_sha256_required": True,
        "adapter_sha256_required": True,
        "timestamp_monotonicity_required": True,
        "exact_model_attestation_required_for_live_attested": True,
    }

    hashes = {
        "task_sha256": sha256_json(task),
        "assignment_sha256": assignment_sha256(task, matrix["assignment"]),
        "provider_neutral_prompt_sha256": sha256_json(matrix["prompt"]),
        "strict_local_result_schema_sha256": sha256_json(strict_schema),
        "provider_wire_response_schema_sha256": sha256_json(wire_schema),
        "rendered_request_body_sha256": sha256_json(matrix["render"]["body"]),
        "request_envelope_sha256": sha256_json(matrix["request_envelope"]),
        "transport_binding_sha256": prep["transport_binding_sha256"],
        "smoke_profile_sha256": prep["smoke_profile_sha256"],
        "execution_prep_sha256": sha256_json(prep),
        "pilot_matrix_sha256": provider_pilot_matrix_sha256(task, snapshot, wire_schema, matrix),
        "catalog_freshness_sha256": catalog_freshness_sha256(snapshot, freshness),
        "official_verification_sha256": official_verification_sha256(snapshot, verification),
        "result_ingestion_requirements_sha256": sha256_json(ingestion_requirements),
        "termination_receipt_requirements_sha256": sha256_json(termination_receipt_requirements),
    }

    packet = {
        "schema": PACKET_SCHEMA,
        "packet_id": "phase-b-first-provider-pilot-execution-packet-post-pr290-001",
        "canonical": {
            "main": CANONICAL_MAIN,
            "tree": CANONICAL_TREE,
            "multimodel_subtree": CANONICAL_MULTIMODEL_SUBTREE,
        },
        "catalog": {
            "snapshot": snapshot,
            "freshness_receipt": freshness,
        },
        "official_verification": verification,
        "eligible_provider_comparison": comparison,
        "mechanical_selection": selection,
        "synthetic_task": task,
        "strict_local_result_schema": strict_schema,
        "provider_wire_response_schema": wire_schema,
        "pilot_matrix": matrix,
        "result_ingestion_requirements": ingestion_requirements,
        "termination_receipt_requirements": termination_receipt_requirements,
        "limits": {
            "max_attempts": 1,
            "max_input_tokens": FIRST_SMOKE_MAX_INPUT_TOKENS,
            "max_output_tokens": FIRST_SMOKE_MAX_OUTPUT_TOKENS,
            "max_compute_seconds": TASK_MAX_COMPUTE_SECONDS,
            "max_output_bytes": TASK_MAX_OUTPUT_BYTES,
            "proposed_max_cost_usd_micros": prep["proposed_max_cost_usd_micros"],
            "repository_max_cost_usd_micros": REPOSITORY_MAX_COST_USD_MICROS,
        },
        "authority": {
            "provider_call_authority_required": True,
            "credential_handle_authority_required": True,
            "spend_authority_required": True,
            "provider_call_authorized": False,
            "credential_authorized": False,
            "spend_authorized": False,
            "runtime_activation": False,
            "live_execution_performed": False,
            "protected_data": False,
            "live_business_effect": False,
            "adoption_authority": False,
            "runtime": "OFF",
        },
        "hashes": hashes,
    }
    return validate_first_provider_execution_packet(packet)


def validate_first_provider_execution_packet(
    packet: dict[str, Any],
) -> dict[str, Any]:
    require(isinstance(packet, dict) and set(packet) == PACKET_KEYS, "PACKET_SCHEMA_KEYS")
    require(packet["schema"] == PACKET_SCHEMA, "PACKET_SCHEMA_VERSION")
    require(
        packet["canonical"]
        == {
            "main": CANONICAL_MAIN,
            "tree": CANONICAL_TREE,
            "multimodel_subtree": CANONICAL_MULTIMODEL_SUBTREE,
        },
        "PACKET_CANONICAL_DRIFT",
    )

    snapshot = packet["catalog"]["snapshot"]
    freshness = packet["catalog"]["freshness_receipt"]
    validate_provider_catalog(snapshot)
    validate_catalog_freshness_receipt(snapshot, freshness)
    require(freshness["age_seconds"] <= CATALOG_MAX_AGE_SECONDS, "PACKET_CATALOG_STALE")
    verification = validate_official_verification(snapshot, packet["official_verification"])

    comparison = build_eligible_provider_comparison(snapshot, verification)
    require(packet["eligible_provider_comparison"] == comparison, "PACKET_PROVIDER_COMPARISON_DRIFT")
    selection = mechanically_select_provider(comparison)
    require(packet["mechanical_selection"] == selection, "PACKET_SELECTION_DRIFT")
    require(selection["selected_provider"] == "GOOGLE_GEMINI", "PACKET_LOWEST_COST_PROVIDER_CHANGED")

    task = synthetic_task()
    require(packet["synthetic_task"] == task, "PACKET_TASK_DRIFT")
    strict_schema = packet["strict_local_result_schema"]
    wire_schema = packet["provider_wire_response_schema"]
    matrix = packet["pilot_matrix"]
    validate_result_v2_response_schema(task, matrix["assignment"], strict_schema)
    require(wire_schema == build_common_wire_schema(strict_schema), "PACKET_WIRE_SCHEMA_DRIFT")
    validate_provider_pilot_matrix(task, snapshot, wire_schema, matrix)

    capability = matrix["capability_policy"]
    for key in FORBIDDEN_CAPABILITIES:
        require(capability[key] == "NONE", f"PACKET_CAPABILITY_FORBIDDEN:{key}")
    require(capability["streaming"] is False, "PACKET_STREAMING_FORBIDDEN")
    require(capability["structured_output"] == "JSON_ONLY", "PACKET_JSON_ONLY_REQUIRED")
    require(matrix["smoke_profile"]["data_ceiling"] == "SYNTHETIC_ONLY", "PACKET_NON_SYNTHETIC")
    require(matrix["smoke_profile"]["max_attempts_per_assignment"] == 1, "PACKET_SECOND_ATTEMPT")

    prep = matrix["execution_prep"]
    selected_provider = selection["selected_provider"]
    spec = PROVIDER_MAP[selected_provider]
    require(prep["allowed_host"] == spec["allowed_host"], "PACKET_HOST_DRIFT")
    require(prep["allowed_operation"] == spec["allowed_operation"], "PACKET_OPERATION_DRIFT")
    require(prep["credential_material_in_repository"] is False, "PACKET_CREDENTIAL_MATERIAL")
    require(prep["max_attempts"] == 1, "PACKET_PREP_SECOND_ATTEMPT")
    require(prep["max_input_tokens"] == FIRST_SMOKE_MAX_INPUT_TOKENS, "PACKET_INPUT_CEILING")
    require(prep["max_output_tokens"] == FIRST_SMOKE_MAX_OUTPUT_TOKENS, "PACKET_OUTPUT_CEILING")
    require(
        prep["proposed_max_cost_usd_micros"]
        == selection["selected_estimated_max_cost_usd_micros"]
        <= REPOSITORY_MAX_COST_USD_MICROS,
        "PACKET_COST_CEILING",
    )

    limits = packet["limits"]
    require(limits["max_attempts"] == prep["max_attempts"] == 1, "PACKET_LIMIT_ATTEMPTS")
    require(limits["max_input_tokens"] == prep["max_input_tokens"], "PACKET_LIMIT_INPUT")
    require(limits["max_output_tokens"] == prep["max_output_tokens"], "PACKET_LIMIT_OUTPUT")
    require(limits["max_compute_seconds"] == matrix["assignment"]["max_compute_seconds"], "PACKET_LIMIT_COMPUTE")
    require(limits["max_output_bytes"] == matrix["assignment"]["max_output_bytes"], "PACKET_LIMIT_BYTES")
    require(limits["proposed_max_cost_usd_micros"] == prep["proposed_max_cost_usd_micros"], "PACKET_LIMIT_COST")
    require(limits["repository_max_cost_usd_micros"] == REPOSITORY_MAX_COST_USD_MICROS, "PACKET_REPO_COST")

    authority = packet["authority"]
    for key in (
        "provider_call_authority_required",
        "credential_handle_authority_required",
        "spend_authority_required",
    ):
        require(authority[key] is True, f"PACKET_SEPARATE_AUTHORITY_REQUIRED:{key}")
    for key in (
        "provider_call_authorized",
        "credential_authorized",
        "spend_authorized",
        "runtime_activation",
        "live_execution_performed",
        "protected_data",
        "live_business_effect",
        "adoption_authority",
    ):
        require(authority[key] is False, f"PACKET_FORBIDDEN_AUTHORITY:{key}")
    require(authority["runtime"] == "OFF", "PACKET_RUNTIME_NOT_OFF")

    ingestion = packet["result_ingestion_requirements"]
    require(ingestion["schema"] == INGESTION_REQUIREMENTS_SCHEMA, "PACKET_INGESTION_SCHEMA")
    require(ingestion["assignment_sha256"] == assignment_sha256(task, matrix["assignment"]), "PACKET_INGESTION_ASSIGNMENT")
    require(ingestion["strict_local_result_schema_sha256"] == sha256_json(strict_schema), "PACKET_INGESTION_STRICT_SCHEMA")
    require(ingestion["provider_wire_response_schema_sha256"] == sha256_json(wire_schema), "PACKET_INGESTION_WIRE_SCHEMA")
    for key in (
        "strict_json_object_required",
        "duplicate_keys_rejected",
        "nonfinite_numbers_rejected",
        "completed_observation_required",
        "observed_model_exact_match_required",
        "local_result_v2_validation_required",
    ):
        require(ingestion[key] is True, f"PACKET_INGESTION_REQUIRED:{key}")
    require(
        ingestion["assignment_output_byte_ceiling"] == matrix["assignment"]["max_output_bytes"],
        "PACKET_INGESTION_BYTES",
    )

    termination = packet["termination_receipt_requirements"]
    require(termination["schema"] == TERMINATION_RECEIPT_REQUIREMENTS_SCHEMA, "PACKET_TERMINATION_SCHEMA")
    require(termination["assignment_sha256"] == assignment_sha256(task, matrix["assignment"]), "PACKET_TERMINATION_ASSIGNMENT")
    require(termination["request_envelope_sha256"] == sha256_json(matrix["request_envelope"]), "PACKET_TERMINATION_REQUEST")
    for key, value in termination.items():
        if key not in {"schema", "assignment_sha256", "request_envelope_sha256"}:
            require(value is True, f"PACKET_TERMINATION_REQUIRED:{key}")

    expected_hashes = {
        "task_sha256": sha256_json(task),
        "assignment_sha256": assignment_sha256(task, matrix["assignment"]),
        "provider_neutral_prompt_sha256": sha256_json(matrix["prompt"]),
        "strict_local_result_schema_sha256": sha256_json(strict_schema),
        "provider_wire_response_schema_sha256": sha256_json(wire_schema),
        "rendered_request_body_sha256": sha256_json(matrix["render"]["body"]),
        "request_envelope_sha256": sha256_json(matrix["request_envelope"]),
        "transport_binding_sha256": prep["transport_binding_sha256"],
        "smoke_profile_sha256": prep["smoke_profile_sha256"],
        "execution_prep_sha256": sha256_json(prep),
        "pilot_matrix_sha256": provider_pilot_matrix_sha256(task, snapshot, wire_schema, matrix),
        "catalog_freshness_sha256": catalog_freshness_sha256(snapshot, freshness),
        "official_verification_sha256": official_verification_sha256(snapshot, verification),
        "result_ingestion_requirements_sha256": sha256_json(ingestion),
        "termination_receipt_requirements_sha256": sha256_json(termination),
    }
    require(packet["hashes"] == expected_hashes, "PACKET_HASH_BINDING_DRIFT")

    if packet.get("packet_id") != "phase-b-first-provider-pilot-execution-packet-post-pr290-001":
        raise ResearchContractError("PACKET_ID")
    return packet


def first_provider_execution_packet_sha256(packet: dict[str, Any]) -> str:
    validate_first_provider_execution_packet(packet)
    return sha256_json(packet)


def packet_summary() -> dict[str, Any]:
    packet = build_first_provider_execution_packet()
    selection = packet["mechanical_selection"]
    return {
        "schema": "MULTIVERSE_PHASE_B_FIRST_PROVIDER_EXECUTION_PACKET_SUMMARY_v1",
        "packet_sha256": first_provider_execution_packet_sha256(packet),
        "selected_provider": selection["selected_provider"],
        "selected_model_id": selection["selected_model_id"],
        "proposed_max_cost_usd_micros": selection["selected_estimated_max_cost_usd_micros"],
        "catalog_age_seconds": packet["catalog"]["freshness_receipt"]["age_seconds"],
        "hashes": packet["hashes"],
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_execution_performed": False,
        "runtime": "OFF",
    }


if __name__ == "__main__":
    print(json.dumps(packet_summary(), sort_keys=True))
