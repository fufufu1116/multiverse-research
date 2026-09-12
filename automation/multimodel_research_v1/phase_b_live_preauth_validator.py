from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from automation.multimodel_research_v1.phase_b_live_preauth import (
    CANONICAL_MAIN,
    CANONICAL_MULTIMODEL_SUBTREE,
    CANONICAL_TREE,
    EXPECTED_CATALOG_AGE_SECONDS,
    MAX_COST_USD_MICROS,
    build_first_live_provider_preauth,
    first_live_provider_preauth_sha256,
    packet_summary,
    validate_first_live_provider_preauth,
)

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]

REQUIRED = [
    ROOT / "PROVIDER_OFFICIAL_PREAUTH_VERIFICATION_20260910T175400Z.json",
    ROOT / "phase_b_live_preauth.py",
    ROOT / "test_phase_b_live_preauth.py",
    ROOT / "phase_b_live_preauth_validator.py",
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
    ROOT / "CANDIDATE_SEAL_v1.json":
        "ac4352caead5bbfb3c02658262830407beacec8e",
}

FORBIDDEN_EXECUTION_MARKERS = (
    "import requests",
    "import httpx",
    "urllib.request",
    "aiohttp.",
    "socket.",
    "http.client",
    "urlopen(",
    ".interactions.create(",
    ".messages.create(",
)

FORBIDDEN_SECRET_MARKERS = (
    "google_" + "api_key =",
    "gemini_" + "api_key =",
    "anthropic_" + "api_key =",
    "claude_" + "api_key =",
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
        packet = build_first_live_provider_preauth()
        validate_first_live_provider_preauth(packet)
        summary = packet_summary()
        record("preauth:build_and_validate", True)
    except Exception as exc:
        packet = {}
        summary = {}
        record("preauth:build_and_validate", False, repr(exc))

    if packet:
        c = packet["canonical"]
        record("canonical:main", c["main"] == CANONICAL_MAIN, c["main"])
        record("canonical:tree", c["tree"] == CANONICAL_TREE, c["tree"])
        record("canonical:multimodel_subtree", c["multimodel_subtree"] == CANONICAL_MULTIMODEL_SUBTREE, c["multimodel_subtree"])
        record("catalog:fresh_le_24h", packet["catalog_freshness"]["fresh_le_24h"] is True)
        record("catalog:age_exact", packet["catalog_freshness"]["age_seconds"] == EXPECTED_CATALOG_AGE_SECONDS,
               str(packet["catalog_freshness"]["age_seconds"]))

        connection = packet["connection"]
        record("connection:provider", connection["provider"] == "GOOGLE_GEMINI", connection["provider"])
        record("connection:model", connection["model_id"] == "gemini-3.8-flash", connection["model_id"])
        record("connection:api_version", connection["api_version"] == "v1", connection["api_version"])
        record("connection:host", connection["host"] == "generativelanguage.googleapis.com", connection["host"])
        record("connection:operation", connection["operation"] == "INTERACTIONS_CREATE_V1", connection["operation"])

        body = packet["exact_request_body"]
        record("request:store_false", body["store"] is False)
        record("request:background_false", body["background"] is False)
        record("request:stream_false", body["stream"] is False)
        record("request:no_previous_interaction", "previous_interaction_id" not in body)
        record("request:no_tools", "tools" not in body and "tool_choice" not in body)
        record("request:response_format", "response_format" in body and "response_mime_type" not in body)

        record("data:synthetic_only", packet["data_boundary"]["classification"] == "SYNTHETIC_ONLY")
        record("capabilities:all_forbidden", all(value is False for value in packet["capability_ceiling"].values()))
        retry = packet["retry_policy"]
        record("retry:one_attempt", retry["max_attempts"] == 1)
        record("retry:none", all(retry[key] is False for key in (
            "automatic_retry","retry_on_timeout","retry_on_5xx","retry_on_ambiguous_outcome"
        )))

        limits = packet["limits"]
        record("cost:exact_39936", limits["proposed_owner_spend_ceiling_usd_micros"] == MAX_COST_USD_MICROS,
               str(limits["proposed_owner_spend_ceiling_usd_micros"]))
        record("cost:under_one_usd", limits["repository_absolute_ceiling_usd_micros"] == 1_000_000
               and MAX_COST_USD_MICROS <= 1_000_000)

        cred = packet["credential_boundary"]
        record("credential:handle_only", cred["credential_handle_ref"] == "credential-handle-gemini-smoke"
               and cred["credential_material_in_repository"] is False
               and cred["credential_material_in_packet"] is False
               and cred["credential_resolution_authorized"] is False
               and cred["credential_use_authorized"] is False)

        sp = packet["success_policy"]
        record("success:http_not_enough", sp["http_success_alone_is_success"] is False)
        record("success:completed_only", sp["required_native_status"] == "completed"
               and sp["required_normalized_state"] == "COMPLETED"
               and sp["required_result_status"] == "COMPLETED")
        record("success:refusal_interruption_schema_not_success",
               sp["refusal_is_success"] is False
               and sp["interruption_is_success"] is False
               and sp["incomplete_is_success"] is False
               and sp["schema_violation_is_success"] is False)
        record("receipt:first", packet["receipt_policy"]["receipt_required_on_success"] is True
               and packet["receipt_policy"]["receipt_required_on_failure"] is True
               and packet["receipt_policy"]["receipt_grants_authority"] is False)

        authority = packet["authority"]
        record("authority:all_live_false", all(authority[key] is False for key in (
            "provider_call_authorized","credential_authorized","spend_authorized","runtime_activation",
            "live_execution_performed","protected_data","live_business_effect","adoption_authority"
        )))
        record("authority:runtime_off", authority["runtime"] == "OFF")
        record("digest:summary_exact", summary.get("preauth_sha256") == first_live_provider_preauth_sha256(packet),
               str(summary.get("preauth_sha256")))

    production_text = (ROOT / "phase_b_live_preauth.py").read_text().lower()
    for marker in FORBIDDEN_EXECUTION_MARKERS:
        record(f"no_provider_execution:{marker}", marker not in production_text, marker)
    for marker in FORBIDDEN_SECRET_MARKERS:
        record(f"no_secret_material:{marker}", marker not in production_text, marker)

    counts = {
        "phase_a": _test_count(ROOT / "test_phase_a.py"),
        "phase_b_launch": _test_count(ROOT / "test_phase_b_launch_generation.py"),
        "execution_packet": _test_count(ROOT / "test_phase_b_execution_packet.py"),
        "live_preauth": _test_count(ROOT / "test_phase_b_live_preauth.py"),
    }
    record("tests:phase_a_exact_478", counts["phase_a"] == 478, str(counts["phase_a"]))
    record("tests:phase_b_launch_exact_18", counts["phase_b_launch"] == 18, str(counts["phase_b_launch"]))
    record("tests:execution_packet_exact_24", counts["execution_packet"] == 24, str(counts["execution_packet"]))
    record("tests:live_preauth_exact_36", counts["live_preauth"] == 36, str(counts["live_preauth"]))
    record("tests:cumulative_exact_556", sum(counts.values()) == 556, str(sum(counts.values())))

    return {
        "schema": "MULTIVERSE_FIRST_LIVE_PROVIDER_PILOT_PREAUTH_VALIDATOR_v1",
        "verdict": "PASS" if not findings else "FIX_REQUIRED",
        "checks": checks,
        "findings": findings,
        "packet_summary": summary,
        "test_counts": counts,
        "live_provider_execution": False,
        "provider_credentials": False,
        "spend_authorized": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }

if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
