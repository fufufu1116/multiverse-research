from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from automation.multimodel_research_v1.phase_b_execution_packet import (
    CANONICAL_MAIN,
    CANONICAL_MULTIMODEL_SUBTREE,
    CANONICAL_TREE,
    REPOSITORY_MAX_COST_USD_MICROS,
    build_first_provider_execution_packet,
    first_provider_execution_packet_sha256,
    packet_summary,
    validate_first_provider_execution_packet,
)

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]

REQUIRED = [
    ROOT / "PROVIDER_OFFICIAL_VERIFICATION_20260910T144300Z.json",
    ROOT / "phase_b_execution_packet.py",
    ROOT / "test_phase_b_execution_packet.py",
    ROOT / "phase_b_execution_packet_validator.py",
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
        packet = build_first_provider_execution_packet()
        validate_first_provider_execution_packet(packet)
        summary = packet_summary()
        record("packet:build_and_validate", True)
    except Exception as exc:
        packet = {}
        summary = {}
        record("packet:build_and_validate", False, repr(exc))

    if packet:
        canonical = packet["canonical"]
        record("canonical:main", canonical["main"] == CANONICAL_MAIN, canonical["main"])
        record("canonical:tree", canonical["tree"] == CANONICAL_TREE, canonical["tree"])
        record(
            "canonical:multimodel_subtree",
            canonical["multimodel_subtree"] == CANONICAL_MULTIMODEL_SUBTREE,
            canonical["multimodel_subtree"],
        )

        freshness = packet["catalog"]["freshness_receipt"]
        record("catalog:fresh_le_24h", 0 <= freshness["age_seconds"] <= 86400, str(freshness["age_seconds"]))
        record("catalog:age_11520", freshness["age_seconds"] == 11520, str(freshness["age_seconds"]))

        rows = {row["provider"]: row for row in packet["eligible_provider_comparison"]}
        record("selection:eligible_provider_count_2", sum(row["eligible"] for row in rows.values()) == 2)
        record(
            "selection:gemini_cost_39936",
            rows["GOOGLE_GEMINI"]["estimated_max_cost_usd_micros"] == 39936,
            str(rows["GOOGLE_GEMINI"]["estimated_max_cost_usd_micros"]),
        )
        record(
            "selection:claude_cost_53248",
            rows["ANTHROPIC_CLAUDE"]["estimated_max_cost_usd_micros"] == 53248,
            str(rows["ANTHROPIC_CLAUDE"]["estimated_max_cost_usd_micros"]),
        )
        selection = packet["mechanical_selection"]
        record("selection:lowest_cost_gemini", selection["selected_provider"] == "GOOGLE_GEMINI", str(selection))
        record("selection:model_exact", selection["selected_model_id"] == "gemini-3.8-flash", selection["selected_model_id"])
        record(
            "selection:cost_under_repo_ceiling",
            selection["selected_estimated_max_cost_usd_micros"] == 39936
            and selection["selected_estimated_max_cost_usd_micros"] <= REPOSITORY_MAX_COST_USD_MICROS,
            str(selection["selected_estimated_max_cost_usd_micros"]),
        )

        matrix = packet["pilot_matrix"]
        smoke = matrix["smoke_profile"]
        prep = matrix["execution_prep"]
        capability = matrix["capability_policy"]
        record("packet:synthetic_only", smoke["data_ceiling"] == "SYNTHETIC_ONLY")
        record("packet:one_attempt", smoke["max_attempts_per_assignment"] == prep["max_attempts"] == 1)
        record("packet:credential_reference_only", prep["credential_material_in_repository"] is False)
        record("packet:host_exact", prep["allowed_host"] == "generativelanguage.googleapis.com", prep["allowed_host"])
        record("packet:operation_exact", prep["allowed_operation"] == "INTERACTIONS_CREATE_V1", prep["allowed_operation"])
        record("packet:network_provider_only", prep["network_scope"] == "PROVIDER_API_ONLY", prep["network_scope"])
        record(
            "packet:no_dynamic_capabilities",
            all(
                capability[key] == "NONE"
                for key in (
                    "tools",
                    "provider_retrieval_search",
                    "code_execution",
                    "file_access",
                    "provider_memory",
                    "function_calling",
                )
            ),
        )
        record("packet:json_only", capability["structured_output"] == "JSON_ONLY" and capability["streaming"] is False)
        record(
            "packet:strict_wire_schema_distinct",
            packet["hashes"]["strict_local_result_schema_sha256"]
            != packet["hashes"]["provider_wire_response_schema_sha256"],
        )
        record(
            "packet:ingestion_bound",
            packet["result_ingestion_requirements"]["strict_local_result_schema_sha256"]
            == packet["hashes"]["strict_local_result_schema_sha256"]
            and packet["result_ingestion_requirements"]["provider_wire_response_schema_sha256"]
            == packet["hashes"]["provider_wire_response_schema_sha256"],
        )
        record(
            "packet:termination_receipt_bound",
            packet["termination_receipt_requirements"]["assignment_sha256"]
            == packet["hashes"]["assignment_sha256"]
            and packet["termination_receipt_requirements"]["request_envelope_sha256"]
            == packet["hashes"]["request_envelope_sha256"],
        )
        authority = packet["authority"]
        record(
            "authority:all_live_forbidden",
            all(
                authority[key] is False
                for key in (
                    "provider_call_authorized",
                    "credential_authorized",
                    "spend_authorized",
                    "runtime_activation",
                    "live_execution_performed",
                    "protected_data",
                    "live_business_effect",
                    "adoption_authority",
                )
            ),
        )
        record("authority:separate_authorities_required", all(
            authority[key] is True for key in (
                "provider_call_authority_required",
                "credential_handle_authority_required",
                "spend_authority_required",
            )
        ))
        record("authority:runtime_off", authority["runtime"] == "OFF")

        record(
            "packet:digest_summary_exact",
            summary.get("packet_sha256") == first_provider_execution_packet_sha256(packet),
            str(summary.get("packet_sha256")),
        )

    production_text = (ROOT / "phase_b_execution_packet.py").read_text().lower()
    for marker in FORBIDDEN_NETWORK_EXECUTION_MARKERS:
        record(f"no_network_execution:{marker}", marker not in production_text, marker)
    for marker in FORBIDDEN_SECRET_MARKERS:
        record(f"no_secret_material:{marker}", marker not in production_text, marker)

    phase_a_count = _test_count(ROOT / "test_phase_a.py")
    phase_b_count = _test_count(ROOT / "test_phase_b_launch_generation.py")
    packet_count = _test_count(ROOT / "test_phase_b_execution_packet.py")
    record("tests:phase_a_exact_478", phase_a_count == 478, str(phase_a_count))
    record("tests:phase_b_launch_exact_18", phase_b_count == 18, str(phase_b_count))
    record("tests:packet_exact_24", packet_count == 24, str(packet_count))
    record("tests:cumulative_exact_520", phase_a_count + phase_b_count + packet_count == 520, str(phase_a_count + phase_b_count + packet_count))

    return {
        "schema": "MULTIVERSE_PHASE_B_FIRST_PROVIDER_EXECUTION_PACKET_VALIDATOR_v1",
        "verdict": "PASS" if not findings else "FIX_REQUIRED",
        "checks": checks,
        "findings": findings,
        "packet_summary": summary,
        "live_provider_execution": False,
        "provider_credentials": False,
        "spend_authorized": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
