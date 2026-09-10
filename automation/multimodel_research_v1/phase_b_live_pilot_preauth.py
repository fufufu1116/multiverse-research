from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from automation.multimodel_research_v1.catalog_freshness import (
    build_catalog_freshness_receipt,
    catalog_freshness_sha256,
    validate_catalog_freshness_receipt,
)
from automation.multimodel_research_v1.model import ResearchContractError, require, sha256_json
from automation.multimodel_research_v1.phase_b_execution_packet import (
    FIRST_SMOKE_MAX_INPUT_TOKENS,
    FIRST_SMOKE_MAX_OUTPUT_TOKENS,
    build_first_provider_execution_packet,
    catalog_snapshot,
    first_provider_execution_packet_sha256,
)

ROOT = Path(__file__).resolve().parent

PREAUTH_SCHEMA = "MULTIVERSE_FIRST_LIVE_PROVIDER_PILOT_PREAUTH_v1"
PREAUTH_SUMMARY_SCHEMA = "MULTIVERSE_FIRST_LIVE_PROVIDER_PILOT_PREAUTH_SUMMARY_v1"
OFFICIAL_RECHECK_SCHEMA = "MULTIVERSE_FIRST_LIVE_PROVIDER_PREAUTH_OFFICIAL_VERIFICATION_v1"
OUTCOME_SCHEMA = "MULTIVERSE_FIRST_LIVE_PROVIDER_PILOT_PREAUTH_OUTCOME_v1"

OFFICIAL_RECHECK_PATH = ROOT / "PROVIDER_OFFICIAL_VERIFICATION_20260910T181300Z.json"

CURRENT_CANONICAL_MAIN = "04f314c744abbd0a15591e0437c5de178cfb0ef4"
CURRENT_CANONICAL_TREE = "bff23e37c95b697c6503afeb5161a50dabe5832e"
CURRENT_MULTIMODEL_SUBTREE = "51f97ee06a81b72932b2a09d2230a19b7ba63a71"

PREDECESSOR_PR = 297
PREDECESSOR_SOURCE_HEAD = "8a5530acb37a05b60a85256f45c0718d92b1c67d"
PREDECESSOR_PACKET_SHA256 = "b94e111714478ed75729d9749c4602770cb3fc90661b3fc099aa14a21f180933"

OFFICIAL_CHECKED_AT = "2026-09-10T18:13:00Z"
CATALOG_MAX_AGE_SECONDS = 86400
EXPECTED_CATALOG_AGE_SECONDS = 24120

SELECTED_PROVIDER = "GOOGLE_GEMINI"
SELECTED_MODEL = "gemini-3.8-flash"
ALLOWED_HOST = "generativelanguage.googleapis.com"
ALLOWED_OPERATION = "INTERACTIONS_CREATE_V1"
API_VERSION = "v1"
SDK_SURFACE = "interactions.create"
HTTP_METHOD = "POST"
ENDPOINT_PATH = "/v1/interactions"

MAX_ATTEMPTS = 1
MAX_INPUT_TOKENS = FIRST_SMOKE_MAX_INPUT_TOKENS
MAX_OUTPUT_TOKENS = FIRST_SMOKE_MAX_OUTPUT_TOKENS
MAX_COST_USD_MICROS = 39936
OWNER_MAX_COST_USD_MICROS = 1_000_000

CREDENTIAL_HANDLE_ID = "GOOGLE_GEMINI_OWNER_SCOPED_CREDENTIAL_HANDLE_V1"

FORBIDDEN_CAPABILITY_NAMES = (
    "tools",
    "search_grounding",
    "provider_retrieval_search",
    "code_execution",
    "file_search",
    "file_access",
    "provider_memory",
    "function_calling",
    "computer_use",
    "url_context",
    "external_url_fetch",
    "background_execution",
    "multi_turn_state",
)

FORBIDDEN_BODY_KEYS = {
    "tools",
    "tool_config",
    "previous_interaction_id",
    "search",
    "search_grounding",
    "code_execution",
    "file_search",
    "function_calling",
    "computer_use",
    "url_context",
}

OUTCOME_KEYS = {
    "http_success",
    "provider",
    "model_id",
    "native_status",
    "strict_local_schema_valid",
    "semantic_refusal",
    "premature_termination",
    "incomplete_observation",
    "termination_valid",
    "receipt_valid",
    "result_or_failure_receipt_present",
    "input_tokens",
    "output_tokens",
    "actual_cost_usd_micros",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f"JSON_OBJECT_REQUIRED:{path.name}")
    return value


def official_recheck() -> dict[str, Any]:
    return _read_json(OFFICIAL_RECHECK_PATH)


def validate_official_recheck(value: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(value, dict), "PREAUTH_OFFICIAL_OBJECT")
    require(value["schema"] == OFFICIAL_RECHECK_SCHEMA, "PREAUTH_OFFICIAL_SCHEMA")
    require(value["checked_at"] == OFFICIAL_CHECKED_AT, "PREAUTH_OFFICIAL_CHECK_TIME")
    expected = {
        "provider": SELECTED_PROVIDER,
        "model_id": SELECTED_MODEL,
        "lifecycle": "GA",
        "classification": "PINNED_OR_STABLE",
        "structured_json": True,
        "api_version": API_VERSION,
        "allowed_host": ALLOWED_HOST,
        "allowed_operation": ALLOWED_OPERATION,
        "sdk_surface": SDK_SURFACE,
        "http_method": HTTP_METHOD,
        "endpoint_path": ENDPOINT_PATH,
        "default_store": True,
        "required_store": False,
        "stateless_single_turn": True,
        "background_compatible_with_store_false": False,
        "response_shape": "steps",
        "migration_note": "MAY_2026_INTERACTIONS_STEPS_SCHEMA",
        "input_usd_micros_per_million_tokens": 750000,
        "output_usd_micros_per_million_tokens": 3750000,
        "pricing_valid_through": "2026-12-31",
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "runtime": "OFF",
    }
    for key, expected_value in expected.items():
        require(value.get(key) == expected_value, f"PREAUTH_OFFICIAL_DRIFT:{key}")
    refs = value.get("official_evidence_refs")
    require(isinstance(refs, list) and len(refs) >= 7, "PREAUTH_OFFICIAL_REFS")
    require(
        all(isinstance(ref, str) and ref.startswith("https://ai.google.dev/") for ref in refs),
        "PREAUTH_OFFICIAL_NON_GOOGLE_REF",
    )
    return value


def _capability_closure() -> dict[str, bool]:
    return {name: False for name in FORBIDDEN_CAPABILITY_NAMES}


def build_first_live_provider_preauth_packet() -> dict[str, Any]:
    predecessor = build_first_provider_execution_packet()
    require(
        first_provider_execution_packet_sha256(predecessor) == PREDECESSOR_PACKET_SHA256,
        "PREAUTH_PREDECESSOR_PACKET_DRIFT",
    )
    selection = predecessor["mechanical_selection"]
    require(selection["selected_provider"] == SELECTED_PROVIDER, "PREAUTH_PROVIDER_SELECTION_DRIFT")
    require(selection["selected_model_id"] == SELECTED_MODEL, "PREAUTH_MODEL_SELECTION_DRIFT")
    require(
        selection["selected_estimated_max_cost_usd_micros"] == MAX_COST_USD_MICROS,
        "PREAUTH_COST_SELECTION_DRIFT",
    )

    snapshot = catalog_snapshot()
    freshness = build_catalog_freshness_receipt(
        snapshot,
        checked_at=OFFICIAL_CHECKED_AT,
        max_age_seconds=CATALOG_MAX_AGE_SECONDS,
    )
    validate_catalog_freshness_receipt(snapshot, freshness)
    verification = validate_official_recheck(official_recheck())

    matrix = predecessor["pilot_matrix"]
    body = copy.deepcopy(matrix["render"]["body"])
    prep = matrix["execution_prep"]

    packet = {
        "schema": PREAUTH_SCHEMA,
        "packet_id": "phase-b-first-live-provider-pilot-preauth-post-pr297-main-001",
        "canonical": {
            "main": CURRENT_CANONICAL_MAIN,
            "tree": CURRENT_CANONICAL_TREE,
            "multimodel_subtree": CURRENT_MULTIMODEL_SUBTREE,
        },
        "predecessor": {
            "integrated_pr": PREDECESSOR_PR,
            "source_head": PREDECESSOR_SOURCE_HEAD,
            "execution_packet_sha256": PREDECESSOR_PACKET_SHA256,
        },
        "official_recheck": verification,
        "catalog_freshness": freshness,
        "provider_binding": {
            "provider": SELECTED_PROVIDER,
            "model_id": SELECTED_MODEL,
            "allowed_host": ALLOWED_HOST,
            "allowed_operation": ALLOWED_OPERATION,
            "api_version": API_VERSION,
            "sdk_surface": SDK_SURFACE,
            "http_method": HTTP_METHOD,
            "endpoint_path": ENDPOINT_PATH,
            "response_shape": "steps",
        },
        "request_contract": {
            "store": False,
            "background": False,
            "stream": False,
            "stateless_single_turn": True,
            "previous_interaction_id_allowed": False,
            "max_attempts": MAX_ATTEMPTS,
            "automatic_retry_on_timeout": False,
            "automatic_retry_on_5xx": False,
            "automatic_retry_on_ambiguous_outcome": False,
            "data_ceiling": "SYNTHETIC_ONLY",
            "capability_closure": _capability_closure(),
            "rendered_body": body,
        },
        "limits": {
            "max_input_tokens": MAX_INPUT_TOKENS,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "max_cost_usd_micros": MAX_COST_USD_MICROS,
            "owner_ceiling_usd_micros": OWNER_MAX_COST_USD_MICROS,
        },
        "credential_boundary": {
            "credential_handle_id": CREDENTIAL_HANDLE_ID,
            "credential_material_present": False,
            "credential_retrieval_authorized": False,
            "credential_use_authorized": False,
            "credential_material_forbidden_in_repository": True,
            "credential_material_forbidden_in_comments": True,
            "credential_material_forbidden_in_logs": True,
            "credential_material_forbidden_in_artifacts": True,
        },
        "response_success_contract": {
            "http_success_alone_is_success": False,
            "exact_provider_required": True,
            "exact_model_required": True,
            "native_completed_required": True,
            "strict_local_schema_required": True,
            "semantic_refusal_is_failure": True,
            "premature_termination_is_failure": True,
            "incomplete_observation_is_failure": True,
            "termination_validation_required": True,
            "receipt_validation_required": True,
            "token_ceiling_required": True,
            "cost_ceiling_required": True,
            "result_or_failure_receipt_required": True,
        },
        "receipt_contract": {
            "required_for_success": True,
            "required_for_failure": True,
            "bind_request_identity": True,
            "bind_provider": True,
            "bind_model": True,
            "bind_terminal_state": True,
            "bind_usage": True,
            "bind_cost": True,
            "bind_result_validation_state": True,
        },
        "authority": {
            "provider_call_authorized": False,
            "credential_authorized": False,
            "spend_authorized": False,
            "runtime_activation": False,
            "live_execution_performed": False,
            "protected_data": False,
            "live_business_effect": False,
            "adoption_authority": False,
            "owner_gate_required_before_provider_call": True,
            "runtime": "OFF",
        },
        "hashes": {
            "predecessor_execution_packet_sha256": PREDECESSOR_PACKET_SHA256,
            "official_recheck_sha256": sha256_json(verification),
            "catalog_freshness_sha256": catalog_freshness_sha256(snapshot, freshness),
            "synthetic_task_sha256": predecessor["hashes"]["task_sha256"],
            "assignment_sha256": predecessor["hashes"]["assignment_sha256"],
            "provider_neutral_prompt_sha256": predecessor["hashes"]["provider_neutral_prompt_sha256"],
            "strict_local_result_schema_sha256": predecessor["hashes"]["strict_local_result_schema_sha256"],
            "provider_wire_response_schema_sha256": predecessor["hashes"]["provider_wire_response_schema_sha256"],
            "rendered_request_body_sha256": predecessor["hashes"]["rendered_request_body_sha256"],
            "request_envelope_sha256": predecessor["hashes"]["request_envelope_sha256"],
            "transport_binding_sha256": predecessor["hashes"]["transport_binding_sha256"],
            "result_ingestion_requirements_sha256": predecessor["hashes"]["result_ingestion_requirements_sha256"],
            "termination_receipt_requirements_sha256": predecessor["hashes"]["termination_receipt_requirements_sha256"],
        },
    }
    return validate_first_live_provider_preauth_packet(packet)


def validate_first_live_provider_preauth_packet(packet: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(packet, dict), "PREAUTH_PACKET_OBJECT")
    require(packet.get("schema") == PREAUTH_SCHEMA, "PREAUTH_SCHEMA")
    require(packet.get("packet_id") == "phase-b-first-live-provider-pilot-preauth-post-pr297-main-001", "PREAUTH_PACKET_ID")
    require(
        packet.get("canonical")
        == {
            "main": CURRENT_CANONICAL_MAIN,
            "tree": CURRENT_CANONICAL_TREE,
            "multimodel_subtree": CURRENT_MULTIMODEL_SUBTREE,
        },
        "PREAUTH_CANONICAL_DRIFT",
    )
    require(
        packet.get("predecessor")
        == {
            "integrated_pr": PREDECESSOR_PR,
            "source_head": PREDECESSOR_SOURCE_HEAD,
            "execution_packet_sha256": PREDECESSOR_PACKET_SHA256,
        },
        "PREAUTH_PREDECESSOR_DRIFT",
    )

    predecessor = build_first_provider_execution_packet()
    require(
        first_provider_execution_packet_sha256(predecessor) == PREDECESSOR_PACKET_SHA256,
        "PREAUTH_PREDECESSOR_PACKET_DRIFT",
    )
    snapshot = catalog_snapshot()
    freshness = packet["catalog_freshness"]
    validate_catalog_freshness_receipt(snapshot, freshness)
    require(freshness["checked_at"] == OFFICIAL_CHECKED_AT, "PREAUTH_FRESHNESS_TIME")
    require(freshness["age_seconds"] == EXPECTED_CATALOG_AGE_SECONDS, "PREAUTH_FRESHNESS_AGE")
    require(0 <= freshness["age_seconds"] <= CATALOG_MAX_AGE_SECONDS, "PREAUTH_CATALOG_STALE")
    verification = validate_official_recheck(packet["official_recheck"])

    require(
        packet["provider_binding"]
        == {
            "provider": SELECTED_PROVIDER,
            "model_id": SELECTED_MODEL,
            "allowed_host": ALLOWED_HOST,
            "allowed_operation": ALLOWED_OPERATION,
            "api_version": API_VERSION,
            "sdk_surface": SDK_SURFACE,
            "http_method": HTTP_METHOD,
            "endpoint_path": ENDPOINT_PATH,
            "response_shape": "steps",
        },
        "PREAUTH_PROVIDER_BINDING_DRIFT",
    )

    matrix = predecessor["pilot_matrix"]
    request = packet["request_contract"]
    require(request["store"] is False, "PREAUTH_STORE_MUST_BE_FALSE")
    require(request["background"] is False, "PREAUTH_BACKGROUND_MUST_BE_FALSE")
    require(request["stream"] is False, "PREAUTH_STREAM_MUST_BE_FALSE")
    require(request["stateless_single_turn"] is True, "PREAUTH_STATELESS_REQUIRED")
    require(request["previous_interaction_id_allowed"] is False, "PREAUTH_MULTI_TURN_FORBIDDEN")
    require(request["max_attempts"] == MAX_ATTEMPTS == 1, "PREAUTH_ONE_ATTEMPT")
    for key in (
        "automatic_retry_on_timeout",
        "automatic_retry_on_5xx",
        "automatic_retry_on_ambiguous_outcome",
    ):
        require(request[key] is False, f"PREAUTH_RETRY_FORBIDDEN:{key}")
    require(request["data_ceiling"] == "SYNTHETIC_ONLY", "PREAUTH_SYNTHETIC_ONLY")
    require(request["capability_closure"] == _capability_closure(), "PREAUTH_CAPABILITY_CLOSURE")

    body = request["rendered_body"]
    require(body == matrix["render"]["body"], "PREAUTH_RENDERED_BODY_DRIFT")
    require(body["model"] == SELECTED_MODEL, "PREAUTH_BODY_MODEL")
    require(body["store"] is False, "PREAUTH_BODY_STORE")
    require(body["background"] is False, "PREAUTH_BODY_BACKGROUND")
    require(body["stream"] is False, "PREAUTH_BODY_STREAM")
    require(body["response_format"]["mime_type"] == "application/json", "PREAUTH_BODY_JSON")
    require(body["generation_config"]["max_output_tokens"] == MAX_OUTPUT_TOKENS, "PREAUTH_BODY_OUTPUT_LIMIT")
    require(not (set(body) & FORBIDDEN_BODY_KEYS), "PREAUTH_BODY_FORBIDDEN_CAPABILITY")

    capability = matrix["capability_policy"]
    for key in (
        "tools",
        "provider_retrieval_search",
        "code_execution",
        "file_access",
        "provider_memory",
        "function_calling",
    ):
        require(capability[key] == "NONE", f"PREAUTH_CANONICAL_CAPABILITY:{key}")
    require(capability["streaming"] is False, "PREAUTH_CANONICAL_STREAMING")

    prep = matrix["execution_prep"]
    require(prep["allowed_host"] == ALLOWED_HOST, "PREAUTH_HOST_DRIFT")
    require(prep["allowed_operation"] == ALLOWED_OPERATION, "PREAUTH_OPERATION_DRIFT")
    require(prep["max_attempts"] == 1, "PREAUTH_PREP_ATTEMPTS")
    require(prep["max_input_tokens"] == MAX_INPUT_TOKENS, "PREAUTH_INPUT_LIMIT")
    require(prep["max_output_tokens"] == MAX_OUTPUT_TOKENS, "PREAUTH_OUTPUT_LIMIT")
    require(prep["proposed_max_cost_usd_micros"] == MAX_COST_USD_MICROS, "PREAUTH_COST_DRIFT")

    limits = packet["limits"]
    require(
        limits
        == {
            "max_input_tokens": MAX_INPUT_TOKENS,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "max_cost_usd_micros": MAX_COST_USD_MICROS,
            "owner_ceiling_usd_micros": OWNER_MAX_COST_USD_MICROS,
        },
        "PREAUTH_LIMITS_DRIFT",
    )
    require(MAX_COST_USD_MICROS <= OWNER_MAX_COST_USD_MICROS, "PREAUTH_OWNER_COST_CEILING")

    credential = packet["credential_boundary"]
    require(credential["credential_handle_id"] == CREDENTIAL_HANDLE_ID, "PREAUTH_CREDENTIAL_HANDLE")
    for key in (
        "credential_material_present",
        "credential_retrieval_authorized",
        "credential_use_authorized",
    ):
        require(credential[key] is False, f"PREAUTH_CREDENTIAL_FORBIDDEN:{key}")
    for key in (
        "credential_material_forbidden_in_repository",
        "credential_material_forbidden_in_comments",
        "credential_material_forbidden_in_logs",
        "credential_material_forbidden_in_artifacts",
    ):
        require(credential[key] is True, f"PREAUTH_CREDENTIAL_BOUNDARY:{key}")

    success = packet["response_success_contract"]
    require(success["http_success_alone_is_success"] is False, "PREAUTH_HTTP_ONLY_FORBIDDEN")
    for key in (
        "exact_provider_required",
        "exact_model_required",
        "native_completed_required",
        "strict_local_schema_required",
        "semantic_refusal_is_failure",
        "premature_termination_is_failure",
        "incomplete_observation_is_failure",
        "termination_validation_required",
        "receipt_validation_required",
        "token_ceiling_required",
        "cost_ceiling_required",
        "result_or_failure_receipt_required",
    ):
        require(success[key] is True, f"PREAUTH_SUCCESS_REQUIREMENT:{key}")

    receipt = packet["receipt_contract"]
    require(all(value is True for value in receipt.values()), "PREAUTH_RECEIPT_CONTRACT")

    authority = packet["authority"]
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
        require(authority[key] is False, f"PREAUTH_AUTHORITY_FORBIDDEN:{key}")
    require(authority["owner_gate_required_before_provider_call"] is True, "PREAUTH_OWNER_GATE_REQUIRED")
    require(authority["runtime"] == "OFF", "PREAUTH_RUNTIME")

    expected_hashes = {
        "predecessor_execution_packet_sha256": PREDECESSOR_PACKET_SHA256,
        "official_recheck_sha256": sha256_json(verification),
        "catalog_freshness_sha256": catalog_freshness_sha256(snapshot, freshness),
        "synthetic_task_sha256": predecessor["hashes"]["task_sha256"],
        "assignment_sha256": predecessor["hashes"]["assignment_sha256"],
        "provider_neutral_prompt_sha256": predecessor["hashes"]["provider_neutral_prompt_sha256"],
        "strict_local_result_schema_sha256": predecessor["hashes"]["strict_local_result_schema_sha256"],
        "provider_wire_response_schema_sha256": predecessor["hashes"]["provider_wire_response_schema_sha256"],
        "rendered_request_body_sha256": predecessor["hashes"]["rendered_request_body_sha256"],
        "request_envelope_sha256": predecessor["hashes"]["request_envelope_sha256"],
        "transport_binding_sha256": predecessor["hashes"]["transport_binding_sha256"],
        "result_ingestion_requirements_sha256": predecessor["hashes"]["result_ingestion_requirements_sha256"],
        "termination_receipt_requirements_sha256": predecessor["hashes"]["termination_receipt_requirements_sha256"],
    }
    require(packet["hashes"] == expected_hashes, "PREAUTH_HASH_BINDING_DRIFT")
    return packet


def _bounded_nonnegative_int(value: Any, code: str) -> int:
    require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, code)
    return value


def classify_preauth_outcome(observation: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(observation, dict) and set(observation) == OUTCOME_KEYS, "PREAUTH_OUTCOME_KEYS")
    reasons: list[str] = []

    if observation["http_success"] is not True:
        reasons.append("HTTP_NOT_SUCCESS")
    if observation["provider"] != SELECTED_PROVIDER:
        reasons.append("PROVIDER_DRIFT")
    if observation["model_id"] != SELECTED_MODEL:
        reasons.append("MODEL_DRIFT")
    if observation["native_status"] != "completed":
        reasons.append("NOT_COMPLETED")
    if observation["strict_local_schema_valid"] is not True:
        reasons.append("STRICT_SCHEMA_INVALID")
    if observation["semantic_refusal"] is not False:
        reasons.append("SEMANTIC_REFUSAL")
    if observation["premature_termination"] is not False:
        reasons.append("PREMATURE_TERMINATION")
    if observation["incomplete_observation"] is not False:
        reasons.append("INCOMPLETE_OBSERVATION")
    if observation["termination_valid"] is not True:
        reasons.append("TERMINATION_INVALID")
    if observation["receipt_valid"] is not True:
        reasons.append("RECEIPT_INVALID")
    if observation["result_or_failure_receipt_present"] is not True:
        reasons.append("RECEIPT_MISSING")

    input_tokens = _bounded_nonnegative_int(observation["input_tokens"], "PREAUTH_INPUT_TOKENS")
    output_tokens = _bounded_nonnegative_int(observation["output_tokens"], "PREAUTH_OUTPUT_TOKENS")
    actual_cost = _bounded_nonnegative_int(observation["actual_cost_usd_micros"], "PREAUTH_ACTUAL_COST")
    if input_tokens > MAX_INPUT_TOKENS:
        reasons.append("INPUT_TOKEN_CEILING_EXCEEDED")
    if output_tokens > MAX_OUTPUT_TOKENS:
        reasons.append("OUTPUT_TOKEN_CEILING_EXCEEDED")
    if actual_cost > MAX_COST_USD_MICROS:
        reasons.append("COST_CEILING_EXCEEDED")

    return {
        "schema": OUTCOME_SCHEMA,
        "success": not reasons,
        "classification": "SUCCESS" if not reasons else "FAIL_CLOSED",
        "failure_reasons": sorted(set(reasons)),
        "provider": observation["provider"],
        "model_id": observation["model_id"],
        "native_status": observation["native_status"],
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "actual_cost_usd_micros": actual_cost,
        "result_or_failure_receipt_present": observation["result_or_failure_receipt_present"] is True,
        "runtime": "OFF",
    }


def first_live_provider_preauth_packet_sha256(packet: dict[str, Any]) -> str:
    validate_first_live_provider_preauth_packet(packet)
    return sha256_json(packet)


def preauth_summary() -> dict[str, Any]:
    packet = build_first_live_provider_preauth_packet()
    return {
        "schema": PREAUTH_SUMMARY_SCHEMA,
        "packet_sha256": first_live_provider_preauth_packet_sha256(packet),
        "canonical": packet["canonical"],
        "provider_binding": packet["provider_binding"],
        "catalog_age_seconds": packet["catalog_freshness"]["age_seconds"],
        "max_attempts": packet["request_contract"]["max_attempts"],
        "max_input_tokens": packet["limits"]["max_input_tokens"],
        "max_output_tokens": packet["limits"]["max_output_tokens"],
        "max_cost_usd_micros": packet["limits"]["max_cost_usd_micros"],
        "credential_handle_id": packet["credential_boundary"]["credential_handle_id"],
        "hashes": packet["hashes"],
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_execution_performed": False,
        "runtime": "OFF",
    }


if __name__ == "__main__":
    print(json.dumps(preauth_summary(), sort_keys=True))
