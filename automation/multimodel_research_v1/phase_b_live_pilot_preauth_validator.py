from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from automation.multimodel_research_v1.phase_b_live_pilot_preauth import (
    ALLOWED_HOST,
    ALLOWED_OPERATION,
    API_VERSION,
    CURRENT_CANONICAL_MAIN,
    CURRENT_CANONICAL_TREE,
    CURRENT_MULTIMODEL_SUBTREE,
    EXPECTED_CATALOG_AGE_SECONDS,
    FORBIDDEN_BODY_KEYS,
    MAX_COST_USD_MICROS,
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    PREDECESSOR_PACKET_SHA256,
    SELECTED_MODEL,
    SELECTED_PROVIDER,
    build_first_live_provider_preauth_packet,
    first_live_provider_preauth_packet_sha256,
    preauth_summary,
    validate_first_live_provider_preauth_packet,
)

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]

REQUIRED = [
    ROOT / "PROVIDER_OFFICIAL_VERIFICATION_20260910T181300Z.json",
    ROOT / "phase_b_live_pilot_preauth.py",
    ROOT / "test_phase_b_live_pilot_preauth.py",
    ROOT / "phase_b_live_pilot_preauth_validator.py",
]

EXPECTED_GIT_BLOBS = {
    ROOT / "CANDIDATE_SEAL_v1.json":
        "ac4352caead5bbfb3c02658262830407beacec8e",
    ROOT / "phase_b_execution_packet.py":
        "7615b387bb23a0f291c37839a023713978d15bf4",
    ROOT / "gemini_adapter.py":
        "fdd18af6be713c41f4ccfb810854da89eed189d2",
    REPO_ROOT / "automation/review_dispatcher_v1/publisher.py":
        "514505257c04cb5d40cb91d65044c7d3f18d6cb8",
    REPO_ROOT / "automation/review_dispatcher_v1/t2.py":
        "fee70fa6b4cf93455a7f0c04d888be1d5b4bfb2a",
    REPO_ROOT / "buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_LAB_FIXED_v1.yml":
        "2d4ec751dee4e507a08313d403c7d0521c172ae5",
    REPO_ROOT / "buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_AUDITOR_FIXED_v1.yml":
        "c42bae003a3b1dc6d11cf5e6c33996369a4d22d6",
}

FORBIDDEN_NETWORK_EXECUTION_MARKERS = (
    "requests.",
    "httpx.",
    "urllib.request",
    "aiohttp.",
    "socket.",
    "http.client",
    "urlopen(",
    "client." + "interactions.create(",
    "client." + "messages.create(",
)
FORBIDDEN_SECRET_MARKERS = (
    "google_" + "api_key",
    "gemini_" + "api_key",
    "anthropic_" + "api_key",
    "claude_" + "api_key",
)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _test_count(path: Path) -> int:
    return len(re.findall(r"^\s+def test_\d+_", path.read_text(), re.M))


def validate() -> dict:
    checks: dict[str, str] = {}
    findings: list[str] = []

    def record(name: str, condition: bool, detail: str = "") -> None:
        checks[name] = "PASS" if condition else "FIX_REQUIRED"
        if not condition:
            findings.append(f"{name}: {detail}")

    for path in REQUIRED:
        record(f"file:{path.name}", path.is_file(), "missing")
    for path in REQUIRED:
        if path.suffix == ".py" and path.is_file():
            try:
                compile(path.read_text(), str(path), "exec")
                record(f"compile:{path.name}", True)
            except Exception as exc:
                record(f"compile:{path.name}", False, repr(exc))

    for path, expected in EXPECTED_GIT_BLOBS.items():
        actual = _git_blob_sha(path) if path.is_file() else "MISSING"
        record(f"git_blob:{path.name}", actual == expected, f"{actual} != {expected}")

    try:
        packet = build_first_live_provider_preauth_packet()
        validate_first_live_provider_preauth_packet(packet)
        summary = preauth_summary()
        record("preauth:build_and_validate", True)
    except Exception as exc:
        packet = {}
        summary = {}
        record("preauth:build_and_validate", False, repr(exc))

    if packet:
        record("canonical:main", packet["canonical"]["main"] == CURRENT_CANONICAL_MAIN)
        record("canonical:tree", packet["canonical"]["tree"] == CURRENT_CANONICAL_TREE)
        record("canonical:multimodel_subtree", packet["canonical"]["multimodel_subtree"] == CURRENT_MULTIMODEL_SUBTREE)
        record("predecessor:packet_sha", packet["predecessor"]["execution_packet_sha256"] == PREDECESSOR_PACKET_SHA256)

        official = packet["official_recheck"]
        record("official:provider", official["provider"] == SELECTED_PROVIDER)
        record("official:model", official["model_id"] == SELECTED_MODEL)
        record("official:lifecycle", official["lifecycle"] == "GA")
        record("official:structured_json", official["structured_json"] is True)
        record("official:api_version", official["api_version"] == API_VERSION)
        record("official:host", official["allowed_host"] == ALLOWED_HOST)
        record("official:operation", official["allowed_operation"] == ALLOWED_OPERATION)
        record("official:store_default_true", official["default_store"] is True)
        record("official:store_required_false", official["required_store"] is False)
        record("official:response_steps", official["response_shape"] == "steps")
        record("official:migration_note", official["migration_note"] == "MAY_2026_INTERACTIONS_STEPS_SCHEMA")
        record("official:pricing_input", official["input_usd_micros_per_million_tokens"] == 750000)
        record("official:pricing_output", official["output_usd_micros_per_million_tokens"] == 3750000)

        freshness = packet["catalog_freshness"]
        record("catalog:age_24120", freshness["age_seconds"] == EXPECTED_CATALOG_AGE_SECONDS, str(freshness["age_seconds"]))
        record("catalog:fresh_le_24h", 0 <= freshness["age_seconds"] <= 86400, str(freshness["age_seconds"]))

        binding = packet["provider_binding"]
        record("binding:provider", binding["provider"] == SELECTED_PROVIDER)
        record("binding:model", binding["model_id"] == SELECTED_MODEL)
        record("binding:host", binding["allowed_host"] == ALLOWED_HOST)
        record("binding:operation", binding["allowed_operation"] == ALLOWED_OPERATION)
        record("binding:api_version", binding["api_version"] == API_VERSION)

        request = packet["request_contract"]
        body = request["rendered_body"]
        record("request:store_false", request["store"] is False and body["store"] is False)
        record("request:background_false", request["background"] is False and body["background"] is False)
        record("request:stream_false", request["stream"] is False and body["stream"] is False)
        record("request:stateless", request["stateless_single_turn"] is True and request["previous_interaction_id_allowed"] is False)
        record("request:synthetic_only", request["data_ceiling"] == "SYNTHETIC_ONLY")
        record("request:one_attempt", request["max_attempts"] == 1)
        record("request:no_auto_retry", request["automatic_retry_on_timeout"] is False and request["automatic_retry_on_5xx"] is False and request["automatic_retry_on_ambiguous_outcome"] is False)
        record("request:all_capabilities_closed", all(value is False for value in request["capability_closure"].values()))
        record("request:no_forbidden_body_keys", not (set(body) & FORBIDDEN_BODY_KEYS))
        record("request:json", body["response_format"]["mime_type"] == "application/json")

        limits = packet["limits"]
        record("limits:input", limits["max_input_tokens"] == MAX_INPUT_TOKENS)
        record("limits:output", limits["max_output_tokens"] == MAX_OUTPUT_TOKENS)
        record("limits:cost_39936", limits["max_cost_usd_micros"] == MAX_COST_USD_MICROS)
        record("limits:cost_le_1usd", limits["max_cost_usd_micros"] <= limits["owner_ceiling_usd_micros"] <= 1_000_000)

        credential = packet["credential_boundary"]
        record("credential:handle_only", bool(credential["credential_handle_id"]) and credential["credential_material_present"] is False)
        record("credential:no_retrieval", credential["credential_retrieval_authorized"] is False)
        record("credential:no_use", credential["credential_use_authorized"] is False)

        success = packet["response_success_contract"]
        record("success:http_not_sufficient", success["http_success_alone_is_success"] is False)
        record("success:all_guards_required", all(success[key] is True for key in (
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
        )))
        record("receipt:success_and_failure", packet["receipt_contract"]["required_for_success"] is True and packet["receipt_contract"]["required_for_failure"] is True)

        authority = packet["authority"]
        record("authority:all_live_false", all(authority[key] is False for key in (
            "provider_call_authorized",
            "credential_authorized",
            "spend_authorized",
            "runtime_activation",
            "live_execution_performed",
            "protected_data",
            "live_business_effect",
            "adoption_authority",
        )))
        record("authority:owner_gate_required", authority["owner_gate_required_before_provider_call"] is True)
        record("authority:runtime_off", authority["runtime"] == "OFF")

        record("hashes:summary_exact", summary.get("packet_sha256") == first_live_provider_preauth_packet_sha256(packet), str(summary.get("packet_sha256")))
        for key in (
            "synthetic_task_sha256",
            "provider_neutral_prompt_sha256",
            "strict_local_result_schema_sha256",
            "provider_wire_response_schema_sha256",
            "rendered_request_body_sha256",
            "request_envelope_sha256",
        ):
            record(f"hashes:{key}", isinstance(packet["hashes"].get(key), str) and len(packet["hashes"][key]) == 64)

    production_text = (ROOT / "phase_b_live_pilot_preauth.py").read_text().lower()
    for marker in FORBIDDEN_NETWORK_EXECUTION_MARKERS:
        record(f"no_network_execution:{marker}", marker not in production_text, marker)
    for marker in FORBIDDEN_SECRET_MARKERS:
        record(f"no_secret_material:{marker}", marker not in production_text, marker)

    phase_a_count = _test_count(ROOT / "test_phase_a.py")
    phase_b_launch_count = _test_count(ROOT / "test_phase_b_launch_generation.py")
    packet_count = _test_count(ROOT / "test_phase_b_execution_packet.py")
    preauth_count = _test_count(ROOT / "test_phase_b_live_pilot_preauth.py")
    record("tests:phase_a_exact_478", phase_a_count == 478, str(phase_a_count))
    record("tests:phase_b_launch_exact_18", phase_b_launch_count == 18, str(phase_b_launch_count))
    record("tests:execution_packet_exact_24", packet_count == 24, str(packet_count))
    record("tests:preauth_exact_24", preauth_count == 24, str(preauth_count))
    record("tests:cumulative_exact_544", phase_a_count + phase_b_launch_count + packet_count + preauth_count == 544, str(phase_a_count + phase_b_launch_count + packet_count + preauth_count))

    return {
        "schema": "MULTIVERSE_FIRST_LIVE_PROVIDER_PILOT_PREAUTH_VALIDATOR_v1",
        "verdict": "PASS" if not findings else "FIX_REQUIRED",
        "checks": checks,
        "findings": findings,
        "preauth_summary": summary,
        "live_provider_execution": False,
        "provider_credentials": False,
        "spend_authorized": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
