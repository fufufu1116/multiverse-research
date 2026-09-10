from __future__ import annotations

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
OFFICIAL_SCHEMA = "MULTIVERSE_FIRST_LIVE_PROVIDER_PREAUTH_OFFICIAL_VERIFICATION_v1"
OFFICIAL_PATH = ROOT / "PROVIDER_PREAUTH_OFFICIAL_VERIFICATION_20260910T175400Z.json"

CURRENT_MAIN = "04f314c744abbd0a15591e0437c5de178cfb0ef4"
CURRENT_TREE = "bff23e37c95b697c6503afeb5161a50dabe5832e"
CURRENT_MULTIMODEL_SUBTREE = "51f97ee06a81b72932b2a09d2230a19b7ba63a71"

PREDECESSOR_PACKET_SHA256 = "b94e111714478ed75729d9749c4602770cb3fc90661b3fc099aa14a21f180933"
CATALOG_BLOB_SHA1 = "6ba85c23bbe666baf204d29ae2145b510a164528"
CHECKED_AT = "2026-09-10T17:54:00Z"
CATALOG_OBSERVED_AT = "2026-09-10T11:31:00Z"
MAX_CATALOG_AGE_SECONDS = 86400
EXPECTED_CATALOG_AGE_SECONDS = 22980

PROVIDER = "GOOGLE_GEMINI"
MODEL_ID = "gemini-3.8-flash"
HOST = "generativelanguage.googleapis.com"
OPERATION = "INTERACTIONS_CREATE_V1"
API_VERSION = "v1"
ENDPOINT = "https://generativelanguage.googleapis.com/v1/interactions"

MAX_ATTEMPTS = 1
MAX_INPUT_TOKENS = 32768
MAX_OUTPUT_TOKENS = 4096
MAX_COST_USD_MICROS = 39936
CREDENTIAL_HANDLE_REF = "OWNER_MANAGED_GEMINI_API_KEY_HANDLE_V1"

FORBIDDEN_REQUEST_FIELDS = {
    "tools",
    "tool_choice",
    "previous_interaction_id",
    "url_context",
    "file_search",
    "code_execution",
    "computer_use",
    "function_calling",
}
FORBIDDEN_CAPABILITIES = {
    "tools",
    "provider_retrieval_search",
    "code_execution",
    "file_access",
    "provider_memory",
    "function_calling",
}
EXTRA_FORBIDDEN_CAPABILITIES = {
    "computer_use",
    "url_context",
    "background_execution",
    "multi_turn_state",
}
SUCCESS_REQUIRED = {
    "http_success",
    "provider_exact",
    "model_exact",
    "native_completed",
    "normalized_completed",
    "strict_schema_valid",
    "semantic_non_refusal",
    "semantic_non_interrupted",
    "result_completed",
    "token_ceiling_ok",
    "cost_ceiling_ok",
    "termination_valid",
    "receipt_valid",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), "PREAUTH_JSON_OBJECT_REQUIRED")
    return value


def _parse_utc(value: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), "PREAUTH_TIME_FORMAT")
    return datetime.fromisoformat(value[:-1] + "+00:00")


def validate_official_verification(record: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(record, dict), "PREAUTH_OFFICIAL_OBJECT")
    required = {
        "schema", "checked_at", "source_class", "catalog_snapshot_id",
        "catalog_blob_sha1", "catalog_observed_at", "catalog_age_seconds",
        "catalog_max_age_seconds", "provider", "model_id", "lifecycle", "stable",
        "structured_output_supported", "api", "pricing", "migration",
        "official_evidence_refs", "provider_call_authorized",
        "credential_authorized", "spend_authorized", "live_execution_performed",
        "runtime",
    }
    require(set(record) == required, "PREAUTH_OFFICIAL_KEYS")
    require(record["schema"] == OFFICIAL_SCHEMA, "PREAUTH_OFFICIAL_SCHEMA")
    require(record["checked_at"] == CHECKED_AT, "PREAUTH_OFFICIAL_CHECKED_AT")
    require(record["source_class"] == "PUBLIC_OFFICIAL_DOCUMENTATION_ONLY", "PREAUTH_OFFICIAL_SOURCE_CLASS")
    require(record["catalog_snapshot_id"] == "provider-model-catalog-20260910", "PREAUTH_OFFICIAL_CATALOG")
    require(record["catalog_blob_sha1"] == CATALOG_BLOB_SHA1, "PREAUTH_OFFICIAL_CATALOG_BLOB")
    require(record["catalog_observed_at"] == CATALOG_OBSERVED_AT, "PREAUTH_OFFICIAL_CATALOG_OBSERVED")
    actual_age = int((_parse_utc(record["checked_at"]) - _parse_utc(record["catalog_observed_at"])).total_seconds())
    require(actual_age == EXPECTED_CATALOG_AGE_SECONDS, "PREAUTH_OFFICIAL_AGE_COMPUTE")
    require(record["catalog_age_seconds"] == actual_age, "PREAUTH_OFFICIAL_AGE")
    require(record["catalog_max_age_seconds"] == MAX_CATALOG_AGE_SECONDS, "PREAUTH_OFFICIAL_MAX_AGE")
    require(0 <= actual_age <= MAX_CATALOG_AGE_SECONDS, "PREAUTH_OFFICIAL_STALE")
    require(record["provider"] == PROVIDER, "PREAUTH_OFFICIAL_PROVIDER")
    require(record["model_id"] == MODEL_ID, "PREAUTH_OFFICIAL_MODEL")
    require(record["lifecycle"] == "GA" and record["stable"] is True, "PREAUTH_OFFICIAL_LIFECYCLE")
    require(record["structured_output_supported"] is True, "PREAUTH_OFFICIAL_STRUCTURED")

    api = record["api"]
    require(api == {
        "host": HOST,
        "operation": OPERATION,
        "api_version": API_VERSION,
        "endpoint": ENDPOINT,
        "sdk_surface": "interactions.create",
        "response_schema": "steps",
        "response_format_field": "response_format",
        "store_default": True,
        "required_store": False,
        "background_required": False,
        "stream_required": False,
        "previous_interaction_id_allowed": False,
    }, "PREAUTH_OFFICIAL_API")

    pricing = record["pricing"]
    require(pricing == {
        "currency": "USD",
        "basis": "PER_MILLION_TOKENS",
        "input_usd_micros_per_million_tokens": 750000,
        "output_usd_micros_per_million_tokens": 3750000,
        "valid_through": "2026-12-31",
    }, "PREAUTH_OFFICIAL_PRICING")

    migration = record["migration"]
    require(migration == {
        "may_2026_breaking_changes_reviewed": True,
        "legacy_outputs_removed": True,
        "current_steps_required": True,
        "current_response_format_required": True,
    }, "PREAUTH_OFFICIAL_MIGRATION")
    refs = record["official_evidence_refs"]
    require(isinstance(refs, list) and len(refs) >= 6, "PREAUTH_OFFICIAL_REFS")
    require(all(isinstance(ref, str) and ref.startswith("https://ai.google.dev/") for ref in refs), "PREAUTH_OFFICIAL_REF_DOMAIN")
    for key in ("provider_call_authorized", "credential_authorized", "spend_authorized", "live_execution_performed"):
        require(record[key] is False, f"PREAUTH_OFFICIAL_AUTHORITY:{key}")
    require(record["runtime"] == "OFF", "PREAUTH_OFFICIAL_RUNTIME")
    return record


def official_verification() -> dict[str, Any]:
    return validate_official_verification(_read_json(OFFICIAL_PATH))


def _predecessor() -> dict[str, Any]:
    packet = build_first_provider_execution_packet()
    require(first_provider_execution_packet_sha256(packet) == PREDECESSOR_PACKET_SHA256, "PREAUTH_PREDECESSOR_PACKET_DRIFT")
    selection = packet["mechanical_selection"]
    require(selection["selected_provider"] == PROVIDER, "PREAUTH_PREDECESSOR_PROVIDER")
    require(selection["selected_model_id"] == MODEL_ID, "PREAUTH_PREDECESSOR_MODEL")
    require(selection["selected_estimated_max_cost_usd_micros"] == MAX_COST_USD_MICROS, "PREAUTH_PREDECESSOR_COST")
    limits = packet["limits"]
    require(limits["max_attempts"] == MAX_ATTEMPTS, "PREAUTH_PREDECESSOR_ATTEMPTS")
    require(limits["max_input_tokens"] == MAX_INPUT_TOKENS, "PREAUTH_PREDECESSOR_INPUT")
    require(limits["max_output_tokens"] == MAX_OUTPUT_TOKENS, "PREAUTH_PREDECESSOR_OUTPUT")
    return packet


def classify_pilot_outcome(evidence: dict[str, Any]) -> str:
    require(isinstance(evidence, dict), "PREAUTH_OUTCOME_OBJECT")
    if evidence.get("receipt_valid") is not True:
        return "FAIL_CLOSED_NO_RECEIPT"
    checks = {
        "http_success": evidence.get("http_status") is not None and 200 <= evidence["http_status"] < 300,
        "provider_exact": evidence.get("observed_provider") == PROVIDER,
        "model_exact": evidence.get("observed_model_id") == MODEL_ID,
        "native_completed": evidence.get("native_status") == "completed",
        "normalized_completed": evidence.get("normalized_state") == "COMPLETED",
        "strict_schema_valid": evidence.get("strict_schema_valid") is True,
        "semantic_non_refusal": evidence.get("semantic_refusal") is False,
        "semantic_non_interrupted": evidence.get("semantic_interrupted") is False,
        "result_completed": evidence.get("result_status") == "COMPLETED",
        "token_ceiling_ok": (
            isinstance(evidence.get("input_tokens"), int)
            and not isinstance(evidence.get("input_tokens"), bool)
            and 0 <= evidence["input_tokens"] <= MAX_INPUT_TOKENS
            and isinstance(evidence.get("output_tokens"), int)
            and not isinstance(evidence.get("output_tokens"), bool)
            and 0 <= evidence["output_tokens"] <= MAX_OUTPUT_TOKENS
        ),
        "cost_ceiling_ok": (
            isinstance(evidence.get("actual_cost_usd_micros"), int)
            and not isinstance(evidence.get("actual_cost_usd_micros"), bool)
            and 0 <= evidence["actual_cost_usd_micros"] <= MAX_COST_USD_MICROS
        ),
        "termination_valid": evidence.get("termination_valid") is True,
        "receipt_valid": True,
    }
    return "PASS" if set(checks) == SUCCESS_REQUIRED and all(checks.values()) else "FAIL_CLOSED"


def _build_unchecked(verification: dict[str, Any]) -> dict[str, Any]:
    predecessor = _predecessor()
    matrix = predecessor["pilot_matrix"]
    body = matrix["render"]["body"]
    capability = matrix["capability_policy"]
    prep = matrix["execution_prep"]
    require(body.get("store") is False, "PREAUTH_STORE_FALSE_REQUIRED")
    require(body.get("background") is False, "PREAUTH_BACKGROUND_FALSE_REQUIRED")
    require(body.get("stream") is False, "PREAUTH_STREAM_FALSE_REQUIRED")
    require("previous_interaction_id" not in body, "PREAUTH_MULTI_TURN_FORBIDDEN")
    require(not (FORBIDDEN_REQUEST_FIELDS & set(body)), "PREAUTH_FORBIDDEN_REQUEST_FIELD")
    require(body.get("model") == MODEL_ID, "PREAUTH_BODY_MODEL")
    response_format = body.get("response_format")
    require(
        isinstance(response_format, dict)
        and response_format.get("type") == "text"
        and response_format.get("mime_type") == "application/json"
        and response_format.get("schema") == predecessor["provider_wire_response_schema"],
        "PREAUTH_RESPONSE_FORMAT",
    )
    for key in FORBIDDEN_CAPABILITIES:
        require(capability[key] == "NONE", f"PREAUTH_CAPABILITY:{key}")
    require(capability["streaming"] is False, "PREAUTH_CAPABILITY_STREAMING")
    require(capability["structured_output"] == "JSON_ONLY", "PREAUTH_CAPABILITY_JSON")
    require(prep["allowed_host"] == HOST, "PREAUTH_HOST")
    require(prep["allowed_operation"] == OPERATION, "PREAUTH_OPERATION")
    require(prep["max_attempts"] == MAX_ATTEMPTS, "PREAUTH_ATTEMPTS")
    require(prep["max_input_tokens"] == MAX_INPUT_TOKENS, "PREAUTH_INPUT_CEILING")
    require(prep["max_output_tokens"] == MAX_OUTPUT_TOKENS, "PREAUTH_OUTPUT_CEILING")
    require(prep["proposed_max_cost_usd_micros"] == MAX_COST_USD_MICROS, "PREAUTH_COST_CEILING")

    request_lock = {
        "provider": PROVIDER,
        "model_id": MODEL_ID,
        "host": HOST,
        "operation": OPERATION,
        "api_version": API_VERSION,
        "endpoint": ENDPOINT,
        "store": False,
        "background": False,
        "stream": False,
        "response_schema": "steps",
        "response_format": "CURRENT_POLYMORPHIC_TEXT_JSON_SCHEMA",
        "previous_interaction_id": None,
        "forbidden_request_fields": sorted(FORBIDDEN_REQUEST_FIELDS),
        "rendered_request_body_sha256": predecessor["hashes"]["rendered_request_body_sha256"],
        "request_envelope_sha256": predecessor["hashes"]["request_envelope_sha256"],
    }
    capability_lock = {
        "canonical_capabilities": {key: "NONE" for key in sorted(FORBIDDEN_CAPABILITIES)},
        "additional_forbidden": {key: False for key in sorted(EXTRA_FORBIDDEN_CAPABILITIES)},
        "structured_output": "JSON_ONLY",
        "streaming": False,
    }
    retry_policy = {
        "max_attempts": 1,
        "automatic_retry": False,
        "retry_on_timeout": False,
        "retry_on_5xx": False,
        "retry_on_ambiguous_provider_outcome": False,
        "retry_requires_new_owner_authority": True,
    }
    limits = {
        "max_input_tokens": MAX_INPUT_TOKENS,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "max_cost_usd_micros": MAX_COST_USD_MICROS,
        "owner_spend_ceiling_usd_micros": MAX_COST_USD_MICROS,
        "cost_formula": "CEIL((INPUT_TOKENS*750000 + OUTPUT_TOKENS*3750000)/1000000)",
    }
    credential_boundary = {
        "credential_handle_ref": CREDENTIAL_HANDLE_REF,
        "credential_material_present": False,
        "credential_resolution_performed": False,
        "credential_use_performed": False,
        "api_key_copy_paste_required_from_owner": False,
        "credential_authorized": False,
        "provider_call_authorized": False,
        "spend_authorized": False,
        "execution_ready": False,
        "blocker": "SEPARATE_OWNER_CREDENTIAL_CALL_SPEND_AUTHORITY_REQUIRED",
    }
    outcome_policy = {
        "http_success_alone_is_success": False,
        "schema_valid_json_alone_is_success": False,
        "success_requires_all": sorted(SUCCESS_REQUIRED),
        "refusal_is_success": False,
        "blocked_is_success": False,
        "premature_termination_is_success": False,
        "incomplete_is_success": False,
        "empty_is_success": False,
        "transport_failure_is_success": False,
        "model_mismatch_is_success": False,
        "token_ceiling_violation_is_success": False,
        "cost_ceiling_violation_is_success": False,
    }
    receipt_policy = {
        "receipt_required_for_all_terminal_outcomes": True,
        "receipt_first": True,
        "binds_request_identity": True,
        "binds_provider_model": True,
        "binds_terminal_state": True,
        "binds_usage": True,
        "binds_cost": True,
        "binds_result_validation_state": True,
        "binds_termination_record": True,
        "success_without_receipt": False,
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
    hashes = {
        "predecessor_execution_packet_sha256": PREDECESSOR_PACKET_SHA256,
        "predecessor_task_sha256": predecessor["hashes"]["task_sha256"],
        "predecessor_assignment_sha256": predecessor["hashes"]["assignment_sha256"],
        "predecessor_prompt_sha256": predecessor["hashes"]["provider_neutral_prompt_sha256"],
        "predecessor_strict_schema_sha256": predecessor["hashes"]["strict_local_result_schema_sha256"],
        "predecessor_wire_schema_sha256": predecessor["hashes"]["provider_wire_response_schema_sha256"],
        "predecessor_rendered_body_sha256": predecessor["hashes"]["rendered_request_body_sha256"],
        "predecessor_request_envelope_sha256": predecessor["hashes"]["request_envelope_sha256"],
        "official_verification_sha256": sha256_json(verification),
        "request_lock_sha256": sha256_json(request_lock),
        "capability_lock_sha256": sha256_json(capability_lock),
        "retry_policy_sha256": sha256_json(retry_policy),
        "limits_sha256": sha256_json(limits),
        "credential_boundary_sha256": sha256_json(credential_boundary),
        "outcome_policy_sha256": sha256_json(outcome_policy),
        "receipt_policy_sha256": sha256_json(receipt_policy),
    }
    return {
        "schema": PREAUTH_SCHEMA,
        "packet_id": "first-live-provider-pilot-preauth-post-pr297-main-001",
        "current_canonical": {
            "main": CURRENT_MAIN,
            "tree": CURRENT_TREE,
            "multimodel_subtree": CURRENT_MULTIMODEL_SUBTREE,
        },
        "predecessor_execution_packet_sha256": PREDECESSOR_PACKET_SHA256,
        "official_verification": verification,
        "data_ceiling": "SYNTHETIC_ONLY",
        "request_lock": request_lock,
        "capability_lock": capability_lock,
        "retry_policy": retry_policy,
        "limits": limits,
        "credential_boundary": credential_boundary,
        "outcome_acceptance_policy": outcome_policy,
        "result_or_failure_receipt_policy": receipt_policy,
        "authority": authority,
        "hashes": hashes,
    }


def build_first_live_provider_pilot_preauth() -> dict[str, Any]:
    verification = official_verification()
    packet = _build_unchecked(verification)
    return validate_first_live_provider_pilot_preauth(packet)


def validate_first_live_provider_pilot_preauth(packet: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(packet, dict), "PREAUTH_PACKET_OBJECT")
    require(packet["schema"] == PREAUTH_SCHEMA, "PREAUTH_SCHEMA")
    require(packet["packet_id"] == "first-live-provider-pilot-preauth-post-pr297-main-001", "PREAUTH_PACKET_ID")
    require(packet["current_canonical"] == {
        "main": CURRENT_MAIN,
        "tree": CURRENT_TREE,
        "multimodel_subtree": CURRENT_MULTIMODEL_SUBTREE,
    }, "PREAUTH_CANONICAL_DRIFT")
    require(packet["predecessor_execution_packet_sha256"] == PREDECESSOR_PACKET_SHA256, "PREAUTH_PREDECESSOR_HASH")
    verification = validate_official_verification(packet["official_verification"])
    require(packet["data_ceiling"] == "SYNTHETIC_ONLY", "PREAUTH_NOT_SYNTHETIC")
    expected = _build_unchecked(verification)
    require(packet == expected, "PREAUTH_EXACT_MISMATCH")
    return packet


def first_live_provider_pilot_preauth_sha256(packet: dict[str, Any]) -> str:
    validate_first_live_provider_pilot_preauth(packet)
    return sha256_json(packet)


def packet_summary() -> dict[str, Any]:
    packet = build_first_live_provider_pilot_preauth()
    return {
        "schema": "MULTIVERSE_FIRST_LIVE_PROVIDER_PILOT_PREAUTH_SUMMARY_v1",
        "packet_sha256": first_live_provider_pilot_preauth_sha256(packet),
        "current_canonical": packet["current_canonical"],
        "provider": PROVIDER,
        "model_id": MODEL_ID,
        "endpoint": ENDPOINT,
        "store": False,
        "max_attempts": 1,
        "max_input_tokens": MAX_INPUT_TOKENS,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "max_cost_usd_micros": MAX_COST_USD_MICROS,
        "credential_handle_ref": CREDENTIAL_HANDLE_REF,
        "execution_ready": False,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "runtime": "OFF",
        "hashes": packet["hashes"],
    }


if __name__ == "__main__":
    print(json.dumps(packet_summary(), sort_keys=True))
