from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from automation.multimodel_research_v1.phase_b_live_pilot_preauth import (
    API_VERSION,
    CHECKED_AT,
    CREDENTIAL_HANDLE_REF,
    CURRENT_MAIN,
    CURRENT_MULTIMODEL_SUBTREE,
    CURRENT_TREE,
    ENDPOINT,
    EXPECTED_CATALOG_AGE_SECONDS,
    HOST,
    MAX_ATTEMPTS,
    MAX_COST_USD_MICROS,
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    MODEL_ID,
    OPERATION,
    PREDECESSOR_PACKET_SHA256,
    PROVIDER,
    build_first_live_provider_pilot_preauth,
    classify_pilot_outcome,
    first_live_provider_pilot_preauth_sha256,
    validate_first_live_provider_pilot_preauth,
)

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]

REQUIRED = [
    ROOT / "PROVIDER_PREAUTH_OFFICIAL_VERIFICATION_20260910T175400Z.json",
    ROOT / "phase_b_live_pilot_preauth.py",
    ROOT / "test_phase_b_live_pilot_preauth.py",
    ROOT / "phase_b_live_pilot_preauth_validator.py",
]

EXPECTED_GIT_BLOBS = {
    REPO_ROOT / "automation/review_dispatcher_v1/publisher.py":
        "514505257c04cb5d40cb91d65044c7d3f18d6cb8",
    REPO_ROOT / "automation/review_dispatcher_v1/t2.py":
        "fee70fa6b4cf93455a7f0c04d888be1d5b4bfb2a",
    REPO_ROOT / "buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_LAB_FIXED_v1.yml":
        "2d4ec751dee4e507a08313d403c7d0521c172ae5",
    REPO_ROOT / "buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_AUDITOR_FIXED_v1.yml":
        "c42bae003a3b1dc6d11cf5e6c33996369a4d22d6",
}

FORBIDDEN_NETWORK_MARKERS = (
    "requests.",
    "httpx.",
    "urllib.request",
    "aiohttp.",
    "socket.",
    "http.client",
    "urlopen(",
    ".interactions.create(",
)
FORBIDDEN_SECRET_VALUE_MARKERS = (
    "AIza",
    "sk-ant-",
    "-----BEGIN PRIVATE KEY-----",
)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _test_count(path: Path) -> int:
    return len(re.findall(r"^\s+def test_\d+_", path.read_text(), re.M))


def _success_evidence() -> dict:
    return {
        "http_status": 200,
        "observed_provider": PROVIDER,
        "observed_model_id": MODEL_ID,
        "native_status": "completed",
        "normalized_state": "COMPLETED",
        "strict_schema_valid": True,
        "semantic_refusal": False,
        "semantic_interrupted": False,
        "result_status": "COMPLETED",
        "input_tokens": MAX_INPUT_TOKENS,
        "output_tokens": MAX_OUTPUT_TOKENS,
        "actual_cost_usd_micros": MAX_COST_USD_MICROS,
        "termination_valid": True,
        "receipt_valid": True,
    }


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
        packet = build_first_live_provider_pilot_preauth()
        validate_first_live_provider_pilot_preauth(packet)
        digest = first_live_provider_pilot_preauth_sha256(packet)
        record("preauth:build_and_validate", True)
    except Exception as exc:
        packet = {}
        digest = ""
        record("preauth:build_and_validate", False, repr(exc))

    if packet:
        record("canonical:main", packet["current_canonical"]["main"] == CURRENT_MAIN)
        record("canonical:tree", packet["current_canonical"]["tree"] == CURRENT_TREE)
        record("canonical:subtree", packet["current_canonical"]["multimodel_subtree"] == CURRENT_MULTIMODEL_SUBTREE)
        record("predecessor:packet_hash", packet["predecessor_execution_packet_sha256"] == PREDECESSOR_PACKET_SHA256)

        v = packet["official_verification"]
        record("official:checked_at", v["checked_at"] == CHECKED_AT)
        record("official:fresh_le_24h",
               v["catalog_age_seconds"] == EXPECTED_CATALOG_AGE_SECONDS
               and v["catalog_age_seconds"] <= v["catalog_max_age_seconds"])
        record("official:provider_model", v["provider"] == PROVIDER and v["model_id"] == MODEL_ID)
        record("official:lifecycle_structured",
               v["lifecycle"] == "GA" and v["stable"] is True and v["structured_output_supported"] is True)
        record("official:api",
               v["api"]["host"] == HOST and v["api"]["operation"] == OPERATION
               and v["api"]["api_version"] == API_VERSION and v["api"]["endpoint"] == ENDPOINT)
        record("official:storage", v["api"]["store_default"] is True and v["api"]["required_store"] is False)
        record("official:migration",
               v["migration"]["legacy_outputs_removed"] is True
               and v["migration"]["current_steps_required"] is True
               and v["migration"]["current_response_format_required"] is True)
        record("official:pricing",
               v["pricing"]["input_usd_micros_per_million_tokens"] == 750000
               and v["pricing"]["output_usd_micros_per_million_tokens"] == 3750000
               and v["pricing"]["valid_through"] == "2026-12-31")

        r = packet["request_lock"]
        record("request:provider_model", r["provider"] == PROVIDER and r["model_id"] == MODEL_ID)
        record("request:host_operation_api",
               r["host"] == HOST and r["operation"] == OPERATION
               and r["api_version"] == API_VERSION and r["endpoint"] == ENDPOINT)
        record("request:store_false", r["store"] is False)
        record("request:background_false", r["background"] is False)
        record("request:stream_false", r["stream"] is False)
        record("request:stateless", r["previous_interaction_id"] is None and r["response_schema"] == "steps")
        record("request:response_format_current", r["response_format"] == "CURRENT_POLYMORPHIC_TEXT_JSON_SCHEMA")

        c = packet["capability_lock"]
        record("capability:canonical_none", all(value == "NONE" for value in c["canonical_capabilities"].values()))
        record("capability:extra_forbidden", all(value is False for value in c["additional_forbidden"].values()))
        record("capability:json_nonstreaming", c["structured_output"] == "JSON_ONLY" and c["streaming"] is False)

        retry = packet["retry_policy"]
        record("retry:single_attempt",
               retry["max_attempts"] == MAX_ATTEMPTS == 1
               and retry["automatic_retry"] is False
               and retry["retry_on_timeout"] is False
               and retry["retry_on_5xx"] is False
               and retry["retry_on_ambiguous_provider_outcome"] is False
               and retry["retry_requires_new_owner_authority"] is True)

        limits = packet["limits"]
        record("limits:tokens", limits["max_input_tokens"] == MAX_INPUT_TOKENS and limits["max_output_tokens"] == MAX_OUTPUT_TOKENS)
        record("limits:cost_exact",
               limits["max_cost_usd_micros"] == MAX_COST_USD_MICROS == 39936
               and limits["owner_spend_ceiling_usd_micros"] == MAX_COST_USD_MICROS)

        cred = packet["credential_boundary"]
        record("credential:handle_only",
               cred["credential_handle_ref"] == CREDENTIAL_HANDLE_REF
               and cred["credential_material_present"] is False
               and cred["credential_resolution_performed"] is False
               and cred["credential_use_performed"] is False)
        record("credential:owner_copy_paste_not_required", cred["api_key_copy_paste_required_from_owner"] is False)
        record("credential:not_ready",
               cred["execution_ready"] is False
               and cred["blocker"] == "SEPARATE_OWNER_CREDENTIAL_CALL_SPEND_AUTHORITY_REQUIRED")

        success = _success_evidence()
        record("outcome:all_conditions_pass", classify_pilot_outcome(success) == "PASS")
        record("outcome:http_alone_fails", classify_pilot_outcome({"http_status": 200, "receipt_valid": True}) == "FAIL_CLOSED")
        refusal = dict(success)
        refusal["semantic_refusal"] = True
        refusal["result_status"] = "REFUSED"
        record("outcome:refusal_fails", classify_pilot_outcome(refusal) == "FAIL_CLOSED")
        incomplete = dict(success)
        incomplete["native_status"] = "incomplete"
        record("outcome:incomplete_fails", classify_pilot_outcome(incomplete) == "FAIL_CLOSED")
        no_receipt = dict(success)
        no_receipt["receipt_valid"] = False
        record("outcome:receipt_first", classify_pilot_outcome(no_receipt) == "FAIL_CLOSED_NO_RECEIPT")

        rp = packet["result_or_failure_receipt_policy"]
        record("receipt:all_outcomes",
               rp["receipt_required_for_all_terminal_outcomes"] is True
               and rp["receipt_first"] is True
               and rp["success_without_receipt"] is False
               and rp["binds_usage"] is True
               and rp["binds_cost"] is True
               and rp["binds_result_validation_state"] is True)

        authority = packet["authority"]
        record("authority:all_false",
               all(authority[key] is False for key in (
                   "provider_call_authorized", "credential_authorized", "spend_authorized",
                   "runtime_activation", "live_execution_performed", "protected_data",
                   "live_business_effect", "adoption_authority")))
        record("authority:runtime_off", authority["runtime"] == "OFF")
        record("digest:present", bool(re.fullmatch(r"[0-9a-f]{64}", digest)))

    production_text = (ROOT / "phase_b_live_pilot_preauth.py").read_text()
    for marker in FORBIDDEN_NETWORK_MARKERS:
        record(f"no_network_execution:{marker}", marker not in production_text, marker)
    combined = production_text + (ROOT / "PROVIDER_PREAUTH_OFFICIAL_VERIFICATION_20260910T175400Z.json").read_text()
    for marker in FORBIDDEN_SECRET_VALUE_MARKERS:
        record(f"no_secret_material:{marker}", marker not in combined, marker)

    phase_a_count = _test_count(ROOT / "test_phase_a.py")
    phase_b_count = _test_count(ROOT / "test_phase_b_launch_generation.py")
    exec_count = _test_count(ROOT / "test_phase_b_execution_packet.py")
    preauth_count = _test_count(ROOT / "test_phase_b_live_pilot_preauth.py")
    record("tests:phase_a_exact_478", phase_a_count == 478, str(phase_a_count))
    record("tests:phase_b_exact_18", phase_b_count == 18, str(phase_b_count))
    record("tests:execution_exact_24", exec_count == 24, str(exec_count))
    record("tests:preauth_exact_20", preauth_count == 20, str(preauth_count))
    record("tests:cumulative_exact_540",
           phase_a_count + phase_b_count + exec_count + preauth_count == 540,
           str(phase_a_count + phase_b_count + exec_count + preauth_count))

    return {
        "schema": "MULTIVERSE_FIRST_LIVE_PROVIDER_PILOT_PREAUTH_VALIDATOR_v1",
        "verdict": "PASS" if not findings else "FIX_REQUIRED",
        "checks": checks,
        "findings": findings,
        "packet_sha256": digest,
        "provider": PROVIDER,
        "model_id": MODEL_ID,
        "store": False,
        "max_attempts": 1,
        "max_cost_usd_micros": MAX_COST_USD_MICROS,
        "credential_handle_ref": CREDENTIAL_HANDLE_REF,
        "execution_ready": False,
        "live_provider_execution": False,
        "provider_credentials": False,
        "spend_authorized": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
