from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from automation.multimodel_research_v1.model import ResearchContractError, require, sha256_json
from automation.multimodel_research_v1.phase_b_execution_packet import (
    build_first_provider_execution_packet,
    first_provider_execution_packet_sha256,
)

ROOT = Path(__file__).resolve().parent

PREAUTH_SCHEMA = "MULTIVERSE_FIRST_LIVE_PROVIDER_PILOT_PREAUTH_v1"
OFFICIAL_VERIFICATION_SCHEMA = "MULTIVERSE_FIRST_LIVE_PROVIDER_PILOT_OFFICIAL_VERIFICATION_v1"
OFFICIAL_VERIFICATION_PATH = ROOT / "PROVIDER_OFFICIAL_PREAUTH_VERIFICATION_20260910T175400Z.json"

CANONICAL_MAIN = "04f314c744abbd0a15591e0437c5de178cfb0ef4"
CANONICAL_TREE = "bff23e37c95b697c6503afeb5161a50dabe5832e"
CANONICAL_MULTIMODEL_SUBTREE = "51f97ee06a81b72932b2a09d2230a19b7ba63a71"
PREDECESSOR_PACKET_SHA256 = "b94e111714478ed75729d9749c4602770cb3fc90661b3fc099aa14a21f180933"

CATALOG_OBSERVED_AT = "2026-09-10T11:31:00Z"
OFFICIAL_CHECKED_AT = "2026-09-10T17:54:00Z"
CATALOG_MAX_AGE_SECONDS = 86400
EXPECTED_CATALOG_AGE_SECONDS = 22980

PROVIDER = "GOOGLE_GEMINI"
MODEL_ID = "gemini-3.8-flash"
API_VERSION = "v1"
HOST = "generativelanguage.googleapis.com"
METHOD = "POST"
PATH = "/v1/interactions"
ENDPOINT = "https://generativelanguage.googleapis.com/v1/interactions"
OPERATION = "INTERACTIONS_CREATE_V1"
SDK_SURFACE = "interactions.create"

MAX_ATTEMPTS = 1
MAX_INPUT_TOKENS = 32768
MAX_OUTPUT_TOKENS = 4096
MAX_COST_USD_MICROS = 39936
REPOSITORY_ABSOLUTE_MAX_COST_USD_MICROS = 1_000_000
CREDENTIAL_HANDLE_REF = "credential-handle-gemini-smoke"

FORBIDDEN_BODY_KEYS = {
    "tools",
    "tool_choice",
    "previous_interaction_id",
    "url_context",
    "google_search",
    "search",
    "code_execution",
    "file_search",
    "files",
    "memory",
    "function_calling",
    "functions",
    "computer_use",
}
EXPECTED_BODY_KEYS = {
    "model",
    "input",
    "response_format",
    "stream",
    "store",
    "background",
    "generation_config",
}

CAPABILITY_KEYS = {
    "tools",
    "search_grounding",
    "code_execution",
    "file_search",
    "memory",
    "function_calling",
    "computer_use",
    "url_context",
    "background_execution",
    "multi_turn_state",
    "previous_interaction_id",
    "streaming",
}

OUTCOME_KEYS = {
    "http_success",
    "observed_provider",
    "observed_model_id",
    "native_status",
    "normalized_state",
    "result_status",
    "strict_schema_valid",
    "semantic_refusal",
    "output_nonempty",
    "unexpected_capability_step",
    "input_tokens",
    "output_tokens",
    "computed_cost_usd_micros",
    "receipt_present",
    "receipt_valid",
}

def _parse_utc(value: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), "PREAUTH_TIME")
    return datetime.fromisoformat(value[:-1] + "+00:00")

def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), "PREAUTH_JSON_OBJECT")
    return value

def official_verification() -> dict[str, Any]:
    return _read_json(OFFICIAL_VERIFICATION_PATH)

def validate_official_verification(value: dict[str, Any]) -> dict[str, Any]:
    expected_keys = {
        "schema",
        "checked_at",
        "provider",
        "model_id",
        "classification",
        "lifecycle",
        "pricing",
        "structured_output",
        "transport",
        "storage",
        "migration",
        "official_evidence_refs",
        "authority",
        "runtime",
    }
    require(isinstance(value, dict) and set(value) == expected_keys, "PREAUTH_OFFICIAL_KEYS")
    require(value["schema"] == OFFICIAL_VERIFICATION_SCHEMA, "PREAUTH_OFFICIAL_SCHEMA")
    require(value["checked_at"] == OFFICIAL_CHECKED_AT, "PREAUTH_OFFICIAL_CHECKED_AT")
    require(value["provider"] == PROVIDER, "PREAUTH_OFFICIAL_PROVIDER")
    require(value["model_id"] == MODEL_ID, "PREAUTH_OFFICIAL_MODEL")
    require(value["classification"] == "STABLE", "PREAUTH_OFFICIAL_CLASSIFICATION")
    require(value["lifecycle"] == "GA", "PREAUTH_OFFICIAL_LIFECYCLE")

    pricing = value["pricing"]
    require(
        pricing == {
            "currency": "USD",
            "basis": "PER_MILLION_TOKENS",
            "input_usd_micros": 750000,
            "output_usd_micros": 3750000,
            "valid_through": "2026-12-31",
        },
        "PREAUTH_OFFICIAL_PRICING",
    )
    require(value["structured_output"] == {
        "supported": True,
        "request_field": "response_format",
        "legacy_response_mime_type_allowed": False,
        "strict_local_semantic_validation_required": True,
    }, "PREAUTH_OFFICIAL_STRUCTURED_OUTPUT")
    require(value["transport"] == {
        "api_version": API_VERSION,
        "host": HOST,
        "method": METHOD,
        "path": PATH,
        "endpoint": ENDPOINT,
        "operation": OPERATION,
        "sdk_surface": SDK_SURFACE,
        "response_steps_field": "steps",
    }, "PREAUTH_OFFICIAL_TRANSPORT")
    require(value["storage"] == {
        "default_store": True,
        "pilot_store": False,
        "store_false_supported": True,
        "stateless_single_turn": True,
        "previous_interaction_id_allowed": False,
        "background_allowed": False,
    }, "PREAUTH_OFFICIAL_STORAGE")
    require(value["migration"] == {
        "guide": "INTERACTIONS_BREAKING_CHANGES_MAY_2026",
        "current_response_field": "steps",
        "legacy_response_field": "outputs",
        "current_format_field": "response_format",
        "legacy_format_field": "response_mime_type",
        "legacy_schema_allowed": False,
    }, "PREAUTH_OFFICIAL_MIGRATION")
    refs = value["official_evidence_refs"]
    require(isinstance(refs, list) and len(refs) >= 6, "PREAUTH_OFFICIAL_REFS")
    for ref in refs:
        require(isinstance(ref, str) and ref.startswith("https://ai.google.dev/"), "PREAUTH_OFFICIAL_REF_DOMAIN")
    require(value["authority"] == {
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
    }, "PREAUTH_OFFICIAL_AUTHORITY")
    require(value["runtime"] == "OFF", "PREAUTH_OFFICIAL_RUNTIME")
    return value

def official_verification_sha256(value: dict[str, Any]) -> str:
    validate_official_verification(value)
    return sha256_json(value)

def _catalog_age_seconds() -> int:
    age = int((_parse_utc(OFFICIAL_CHECKED_AT) - _parse_utc(CATALOG_OBSERVED_AT)).total_seconds())
    require(age == EXPECTED_CATALOG_AGE_SECONDS, "PREAUTH_CATALOG_AGE")
    require(0 <= age <= CATALOG_MAX_AGE_SECONDS, "PREAUTH_CATALOG_STALE")
    return age

def _validate_predecessor(predecessor: dict[str, Any]) -> None:
    require(
        first_provider_execution_packet_sha256(predecessor) == PREDECESSOR_PACKET_SHA256,
        "PREAUTH_PREDECESSOR_PACKET_DRIFT",
    )
    require(predecessor["mechanical_selection"]["selected_provider"] == PROVIDER, "PREAUTH_PREDECESSOR_PROVIDER")
    require(predecessor["mechanical_selection"]["selected_model_id"] == MODEL_ID, "PREAUTH_PREDECESSOR_MODEL")
    require(predecessor["limits"]["max_attempts"] == MAX_ATTEMPTS, "PREAUTH_PREDECESSOR_ATTEMPTS")
    require(predecessor["limits"]["max_input_tokens"] == MAX_INPUT_TOKENS, "PREAUTH_PREDECESSOR_INPUT")
    require(predecessor["limits"]["max_output_tokens"] == MAX_OUTPUT_TOKENS, "PREAUTH_PREDECESSOR_OUTPUT")
    require(predecessor["limits"]["proposed_max_cost_usd_micros"] == MAX_COST_USD_MICROS, "PREAUTH_PREDECESSOR_COST")
    require(predecessor["pilot_matrix"]["smoke_profile"]["data_ceiling"] == "SYNTHETIC_ONLY", "PREAUTH_NOT_SYNTHETIC")

def _validate_exact_body(body: dict[str, Any], predecessor: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(body, dict) and set(body) == EXPECTED_BODY_KEYS, "PREAUTH_BODY_KEYS")
    require(body == predecessor["pilot_matrix"]["render"]["body"], "PREAUTH_BODY_PREDECESSOR_MISMATCH")
    require(body["model"] == MODEL_ID, "PREAUTH_BODY_MODEL")
    require(body["store"] is False, "PREAUTH_STORE_FALSE_REQUIRED")
    require(body["background"] is False, "PREAUTH_BACKGROUND_FORBIDDEN")
    require(body["stream"] is False, "PREAUTH_STREAM_FORBIDDEN")
    require(set(body).isdisjoint(FORBIDDEN_BODY_KEYS), "PREAUTH_DYNAMIC_CAPABILITY_FIELD")
    require(body["generation_config"] == {"max_output_tokens": MAX_OUTPUT_TOKENS}, "PREAUTH_GENERATION_CONFIG")
    rf = body["response_format"]
    require(isinstance(rf, dict) and set(rf) == {"type", "mime_type", "schema"}, "PREAUTH_RESPONSE_FORMAT_KEYS")
    require(rf["type"] == "text" and rf["mime_type"] == "application/json", "PREAUTH_RESPONSE_FORMAT")
    require(rf["schema"] == predecessor["provider_wire_response_schema"], "PREAUTH_WIRE_SCHEMA")
    require("response_mime_type" not in body, "PREAUTH_LEGACY_RESPONSE_MIME_TYPE")
    require("outputs" not in body, "PREAUTH_LEGACY_OUTPUTS")
    require(isinstance(body["input"], str) and body["input"], "PREAUTH_INPUT")
    require("http://" not in body["input"].lower() and "https://" not in body["input"].lower(), "PREAUTH_INPUT_URL_FORBIDDEN")
    return body

def build_first_live_provider_preauth() -> dict[str, Any]:
    predecessor = build_first_provider_execution_packet()
    _validate_predecessor(predecessor)
    verification = validate_official_verification(official_verification())
    body = _validate_exact_body(copy.deepcopy(predecessor["pilot_matrix"]["render"]["body"]), predecessor)
    catalog_age = _catalog_age_seconds()

    capability_ceiling = {key: False for key in sorted(CAPABILITY_KEYS)}
    retry_policy = {
        "max_attempts": MAX_ATTEMPTS,
        "automatic_retry": False,
        "retry_on_timeout": False,
        "retry_on_5xx": False,
        "retry_on_ambiguous_outcome": False,
        "any_retry_requires_new_owner_authority": True,
    }
    credential_boundary = {
        "credential_handle_ref": CREDENTIAL_HANDLE_REF,
        "header_name": "x-goog-api-key",
        "credential_material_in_repository": False,
        "credential_material_in_packet": False,
        "credential_material_in_comments_or_logs": False,
        "credential_resolution_authorized": False,
        "credential_use_authorized": False,
        "owner_secret_copy_paste_required": False,
    }
    success_policy = {
        "http_success_alone_is_success": False,
        "required_native_status": "completed",
        "required_normalized_state": "COMPLETED",
        "required_result_status": "COMPLETED",
        "exact_provider_required": True,
        "exact_model_required": True,
        "strict_local_schema_required": True,
        "semantic_refusal_forbidden": True,
        "nonempty_output_required": True,
        "unexpected_capability_step_forbidden": True,
        "usage_required": True,
        "token_ceiling_required": True,
        "cost_ceiling_required": True,
        "receipt_required_before_success": True,
        "refusal_is_success": False,
        "interruption_is_success": False,
        "incomplete_is_success": False,
        "schema_violation_is_success": False,
    }
    receipt_policy = {
        "receipt_required_on_success": True,
        "receipt_required_on_failure": True,
        "request_identity_required": True,
        "rendered_body_sha256_required": True,
        "predecessor_request_envelope_sha256_required": True,
        "provider_and_model_required": True,
        "native_and_normalized_state_required": True,
        "usage_and_cost_when_known_required": True,
        "schema_validation_state_required": True,
        "semantic_validation_state_required": True,
        "result_validation_state_required": True,
        "receipt_grants_authority": False,
    }
    authority = {
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "runtime_activation": False,
        "live_execution_performed": False,
        "protected_data": False,
        "live_business_effect": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }

    core = {
        "schema": PREAUTH_SCHEMA,
        "preauth_id": "first-live-provider-pilot-preauth-post-pr297-main-001",
        "canonical": {
            "main": CANONICAL_MAIN,
            "tree": CANONICAL_TREE,
            "multimodel_subtree": CANONICAL_MULTIMODEL_SUBTREE,
            "predecessor_execution_packet_sha256": PREDECESSOR_PACKET_SHA256,
        },
        "fresh_official_verification": verification,
        "catalog_freshness": {
            "catalog_snapshot_id": predecessor["catalog"]["snapshot"]["snapshot_id"],
            "catalog_observed_at": CATALOG_OBSERVED_AT,
            "checked_at": OFFICIAL_CHECKED_AT,
            "age_seconds": catalog_age,
            "max_age_seconds": CATALOG_MAX_AGE_SECONDS,
            "fresh_le_24h": True,
        },
        "connection": {
            "provider": PROVIDER,
            "model_id": MODEL_ID,
            "api_version": API_VERSION,
            "host": HOST,
            "method": METHOD,
            "path": PATH,
            "endpoint": ENDPOINT,
            "operation": OPERATION,
            "sdk_surface": SDK_SURFACE,
        },
        "data_boundary": {
            "classification": "SYNTHETIC_ONLY",
            "personal_data": False,
            "owner_specific_data": False,
            "secrets": False,
            "connected_app_data": False,
            "live_business_data": False,
            "protected_data": False,
        },
        "exact_request_body": body,
        "capability_ceiling": capability_ceiling,
        "retry_policy": retry_policy,
        "limits": {
            "max_input_tokens": MAX_INPUT_TOKENS,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "max_attempts": MAX_ATTEMPTS,
            "proposed_owner_spend_ceiling_usd_micros": MAX_COST_USD_MICROS,
            "repository_absolute_ceiling_usd_micros": REPOSITORY_ABSOLUTE_MAX_COST_USD_MICROS,
        },
        "credential_boundary": credential_boundary,
        "strict_result_schema": predecessor["strict_local_result_schema"],
        "result_ingestion_requirements": predecessor["result_ingestion_requirements"],
        "termination_receipt_requirements": predecessor["termination_receipt_requirements"],
        "success_policy": success_policy,
        "receipt_policy": receipt_policy,
        "authority": authority,
        "predecessor_hashes": copy.deepcopy(predecessor["hashes"]),
    }
    core["hashes"] = {
        "official_verification_sha256": official_verification_sha256(verification),
        "predecessor_execution_packet_sha256": PREDECESSOR_PACKET_SHA256,
        "synthetic_task_sha256": predecessor["hashes"]["task_sha256"],
        "provider_neutral_prompt_sha256": predecessor["hashes"]["provider_neutral_prompt_sha256"],
        "strict_local_result_schema_sha256": predecessor["hashes"]["strict_local_result_schema_sha256"],
        "provider_wire_response_schema_sha256": predecessor["hashes"]["provider_wire_response_schema_sha256"],
        "rendered_request_body_sha256": predecessor["hashes"]["rendered_request_body_sha256"],
        "request_envelope_sha256": predecessor["hashes"]["request_envelope_sha256"],
        "transport_binding_sha256": predecessor["hashes"]["transport_binding_sha256"],
        "credential_boundary_sha256": sha256_json(credential_boundary),
        "capability_ceiling_sha256": sha256_json(capability_ceiling),
        "retry_policy_sha256": sha256_json(retry_policy),
        "success_policy_sha256": sha256_json(success_policy),
        "receipt_policy_sha256": sha256_json(receipt_policy),
    }
    return validate_first_live_provider_preauth(core)

def validate_first_live_provider_preauth(packet: dict[str, Any]) -> dict[str, Any]:
    expected_keys = {
        "schema","preauth_id","canonical","fresh_official_verification","catalog_freshness",
        "connection","data_boundary","exact_request_body","capability_ceiling","retry_policy",
        "limits","credential_boundary","strict_result_schema","result_ingestion_requirements",
        "termination_receipt_requirements","success_policy","receipt_policy","authority",
        "predecessor_hashes","hashes",
    }
    require(isinstance(packet, dict) and set(packet) == expected_keys, "PREAUTH_PACKET_KEYS")
    require(packet["schema"] == PREAUTH_SCHEMA, "PREAUTH_SCHEMA")
    require(packet["preauth_id"] == "first-live-provider-pilot-preauth-post-pr297-main-001", "PREAUTH_ID")
    require(packet["canonical"] == {
        "main": CANONICAL_MAIN,
        "tree": CANONICAL_TREE,
        "multimodel_subtree": CANONICAL_MULTIMODEL_SUBTREE,
        "predecessor_execution_packet_sha256": PREDECESSOR_PACKET_SHA256,
    }, "PREAUTH_CANONICAL_DRIFT")

    predecessor = build_first_provider_execution_packet()
    _validate_predecessor(predecessor)
    verification = validate_official_verification(packet["fresh_official_verification"])
    freshness = packet["catalog_freshness"]
    require(freshness == {
        "catalog_snapshot_id": predecessor["catalog"]["snapshot"]["snapshot_id"],
        "catalog_observed_at": CATALOG_OBSERVED_AT,
        "checked_at": OFFICIAL_CHECKED_AT,
        "age_seconds": EXPECTED_CATALOG_AGE_SECONDS,
        "max_age_seconds": CATALOG_MAX_AGE_SECONDS,
        "fresh_le_24h": True,
    }, "PREAUTH_FRESHNESS_DRIFT")

    require(packet["connection"] == {
        "provider": PROVIDER,"model_id": MODEL_ID,"api_version": API_VERSION,"host": HOST,
        "method": METHOD,"path": PATH,"endpoint": ENDPOINT,"operation": OPERATION,"sdk_surface": SDK_SURFACE,
    }, "PREAUTH_CONNECTION_DRIFT")
    _validate_exact_body(packet["exact_request_body"], predecessor)

    require(packet["data_boundary"] == {
        "classification": "SYNTHETIC_ONLY","personal_data": False,"owner_specific_data": False,
        "secrets": False,"connected_app_data": False,"live_business_data": False,"protected_data": False,
    }, "PREAUTH_DATA_BOUNDARY")
    require(packet["capability_ceiling"] == {key: False for key in sorted(CAPABILITY_KEYS)}, "PREAUTH_CAPABILITY_CEILING")
    require(packet["retry_policy"] == {
        "max_attempts": 1,"automatic_retry": False,"retry_on_timeout": False,"retry_on_5xx": False,
        "retry_on_ambiguous_outcome": False,"any_retry_requires_new_owner_authority": True,
    }, "PREAUTH_RETRY_POLICY")
    require(packet["limits"] == {
        "max_input_tokens": MAX_INPUT_TOKENS,"max_output_tokens": MAX_OUTPUT_TOKENS,"max_attempts": 1,
        "proposed_owner_spend_ceiling_usd_micros": MAX_COST_USD_MICROS,
        "repository_absolute_ceiling_usd_micros": REPOSITORY_ABSOLUTE_MAX_COST_USD_MICROS,
    }, "PREAUTH_LIMITS")
    require(MAX_COST_USD_MICROS <= REPOSITORY_ABSOLUTE_MAX_COST_USD_MICROS, "PREAUTH_COST_OVER_REPOSITORY_CEILING")
    require(packet["credential_boundary"] == {
        "credential_handle_ref": CREDENTIAL_HANDLE_REF,"header_name": "x-goog-api-key",
        "credential_material_in_repository": False,"credential_material_in_packet": False,
        "credential_material_in_comments_or_logs": False,"credential_resolution_authorized": False,
        "credential_use_authorized": False,"owner_secret_copy_paste_required": False,
    }, "PREAUTH_CREDENTIAL_BOUNDARY")
    require(packet["strict_result_schema"] == predecessor["strict_local_result_schema"], "PREAUTH_STRICT_SCHEMA_DRIFT")
    require(packet["result_ingestion_requirements"] == predecessor["result_ingestion_requirements"], "PREAUTH_INGESTION_DRIFT")
    require(packet["termination_receipt_requirements"] == predecessor["termination_receipt_requirements"], "PREAUTH_TERMINATION_DRIFT")
    require(packet["predecessor_hashes"] == predecessor["hashes"], "PREAUTH_PREDECESSOR_HASH_DRIFT")

    authority = packet["authority"]
    for key in ("provider_call_authorized","credential_authorized","spend_authorized","runtime_activation",
                "live_execution_performed","protected_data","live_business_effect","adoption_authority"):
        require(authority[key] is False, f"PREAUTH_AUTHORITY_FORBIDDEN:{key}")
    require(authority["runtime"] == "OFF", "PREAUTH_RUNTIME")

    sp = packet["success_policy"]
    require(sp["http_success_alone_is_success"] is False, "PREAUTH_HTTP_ALONE")
    for key in ("refusal_is_success","interruption_is_success","incomplete_is_success","schema_violation_is_success"):
        require(sp[key] is False, f"PREAUTH_BAD_SUCCESS:{key}")
    for key in ("exact_provider_required","exact_model_required","strict_local_schema_required",
                "semantic_refusal_forbidden","nonempty_output_required","unexpected_capability_step_forbidden",
                "usage_required","token_ceiling_required","cost_ceiling_required","receipt_required_before_success"):
        require(sp[key] is True, f"PREAUTH_SUCCESS_GUARD:{key}")
    require(sp["required_native_status"] == "completed", "PREAUTH_NATIVE_STATUS")
    require(sp["required_normalized_state"] == "COMPLETED", "PREAUTH_NORMALIZED_STATE")
    require(sp["required_result_status"] == "COMPLETED", "PREAUTH_RESULT_STATUS")

    rp = packet["receipt_policy"]
    for key in ("receipt_required_on_success","receipt_required_on_failure","request_identity_required",
                "rendered_body_sha256_required","predecessor_request_envelope_sha256_required",
                "provider_and_model_required","native_and_normalized_state_required","usage_and_cost_when_known_required",
                "schema_validation_state_required","semantic_validation_state_required","result_validation_state_required"):
        require(rp[key] is True, f"PREAUTH_RECEIPT_GUARD:{key}")
    require(rp["receipt_grants_authority"] is False, "PREAUTH_RECEIPT_AUTHORITY")

    expected_hashes = {
        "official_verification_sha256": official_verification_sha256(verification),
        "predecessor_execution_packet_sha256": PREDECESSOR_PACKET_SHA256,
        "synthetic_task_sha256": predecessor["hashes"]["task_sha256"],
        "provider_neutral_prompt_sha256": predecessor["hashes"]["provider_neutral_prompt_sha256"],
        "strict_local_result_schema_sha256": predecessor["hashes"]["strict_local_result_schema_sha256"],
        "provider_wire_response_schema_sha256": predecessor["hashes"]["provider_wire_response_schema_sha256"],
        "rendered_request_body_sha256": predecessor["hashes"]["rendered_request_body_sha256"],
        "request_envelope_sha256": predecessor["hashes"]["request_envelope_sha256"],
        "transport_binding_sha256": predecessor["hashes"]["transport_binding_sha256"],
        "credential_boundary_sha256": sha256_json(packet["credential_boundary"]),
        "capability_ceiling_sha256": sha256_json(packet["capability_ceiling"]),
        "retry_policy_sha256": sha256_json(packet["retry_policy"]),
        "success_policy_sha256": sha256_json(packet["success_policy"]),
        "receipt_policy_sha256": sha256_json(packet["receipt_policy"]),
    }
    require(packet["hashes"] == expected_hashes, "PREAUTH_HASH_DRIFT")
    return packet

def first_live_provider_preauth_sha256(packet: dict[str, Any]) -> str:
    validate_first_live_provider_preauth(packet)
    return sha256_json(packet)

def classify_pilot_outcome(outcome: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(outcome, dict) and set(outcome) == OUTCOME_KEYS, "PREAUTH_OUTCOME_KEYS")
    for key in ("input_tokens","output_tokens","computed_cost_usd_micros"):
        require(isinstance(outcome[key], int) and not isinstance(outcome[key], bool) and outcome[key] >= 0,
                f"PREAUTH_OUTCOME_USAGE:{key}")
    reasons: list[str] = []
    if outcome["http_success"] is not True:
        reasons.append("HTTP_NOT_SUCCESS")
    if outcome["observed_provider"] != PROVIDER:
        reasons.append("PROVIDER_MISMATCH")
    if outcome["observed_model_id"] != MODEL_ID:
        reasons.append("MODEL_MISMATCH")
    if outcome["native_status"] != "completed":
        reasons.append("NATIVE_NOT_COMPLETED")
    if outcome["normalized_state"] != "COMPLETED":
        reasons.append("NORMALIZED_NOT_COMPLETED")
    if outcome["result_status"] != "COMPLETED":
        reasons.append("RESULT_NOT_COMPLETED")
    if outcome["strict_schema_valid"] is not True:
        reasons.append("STRICT_SCHEMA_INVALID")
    if outcome["semantic_refusal"] is not False:
        reasons.append("SEMANTIC_REFUSAL")
    if outcome["output_nonempty"] is not True:
        reasons.append("EMPTY_OUTPUT")
    if outcome["unexpected_capability_step"] is not False:
        reasons.append("UNEXPECTED_CAPABILITY_STEP")
    if outcome["input_tokens"] > MAX_INPUT_TOKENS:
        reasons.append("INPUT_TOKEN_CEILING")
    if outcome["output_tokens"] > MAX_OUTPUT_TOKENS:
        reasons.append("OUTPUT_TOKEN_CEILING")
    if outcome["computed_cost_usd_micros"] > MAX_COST_USD_MICROS:
        reasons.append("COST_CEILING")
    if outcome["receipt_present"] is not True:
        reasons.append("RECEIPT_MISSING")
    if outcome["receipt_valid"] is not True:
        reasons.append("RECEIPT_INVALID")
    return {
        "accepted": not reasons,
        "classification": "SUCCESS" if not reasons else "FAIL_CLOSED",
        "failure_reasons": sorted(reasons),
        "advisory_only": True,
        "grants_authority": False,
        "runtime": "OFF",
    }

def valid_success_fixture() -> dict[str, Any]:
    return {
        "http_success": True,
        "observed_provider": PROVIDER,
        "observed_model_id": MODEL_ID,
        "native_status": "completed",
        "normalized_state": "COMPLETED",
        "result_status": "COMPLETED",
        "strict_schema_valid": True,
        "semantic_refusal": False,
        "output_nonempty": True,
        "unexpected_capability_step": False,
        "input_tokens": MAX_INPUT_TOKENS,
        "output_tokens": MAX_OUTPUT_TOKENS,
        "computed_cost_usd_micros": MAX_COST_USD_MICROS,
        "receipt_present": True,
        "receipt_valid": True,
    }

def packet_summary() -> dict[str, Any]:
    packet = build_first_live_provider_preauth()
    return {
        "schema": "MULTIVERSE_FIRST_LIVE_PROVIDER_PILOT_PREAUTH_SUMMARY_v1",
        "preauth_sha256": first_live_provider_preauth_sha256(packet),
        "canonical": packet["canonical"],
        "connection": packet["connection"],
        "store": packet["exact_request_body"]["store"],
        "catalog_age_seconds": packet["catalog_freshness"]["age_seconds"],
        "max_attempts": packet["limits"]["max_attempts"],
        "max_input_tokens": packet["limits"]["max_input_tokens"],
        "max_output_tokens": packet["limits"]["max_output_tokens"],
        "proposed_owner_spend_ceiling_usd_micros": packet["limits"]["proposed_owner_spend_ceiling_usd_micros"],
        "credential_handle_ref": packet["credential_boundary"]["credential_handle_ref"],
        "hashes": packet["hashes"],
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "runtime": "OFF",
    }

if __name__ == "__main__":
    print(json.dumps(packet_summary(), sort_keys=True))
