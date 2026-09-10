from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from automation.multimodel_research_v1.catalog_freshness import (
    build_catalog_freshness_receipt,
)
from automation.multimodel_research_v1.launch_generation import (
    CANONICAL_MAIN,
    CANONICAL_MULTIMODEL_SUBTREE,
    CANONICAL_TREE,
    PREDECESSOR_CANDIDATE_SEAL_BLOB,
    REVIEWED_AUDITOR_BUILD,
    REVIEWED_AUDITOR_COMMENT,
    REVIEWED_HEAD,
    REVIEWED_LAB_BUILD,
    REVIEWED_LAB_COMMENT,
    REVIEWED_PR,
    REVIEWED_T1_COMMENT,
    REVIEWED_T2_COMMENT,
    REVIEWED_TEST_COUNT,
    build_current_canonical_launch_generation,
    validate_current_canonical_launch_generation,
)
from automation.multimodel_research_v1.model import (
    ResearchContractError,
    sha256_json,
)
from automation.multimodel_research_v1.provider_catalog import (
    validate_provider_catalog,
)

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]

OLD_CATALOG = ROOT / "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
NEW_CATALOG = ROOT / "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260910.json"
GENERATION_FILE = ROOT / "PHASE_B_LAUNCH_GENERATION_20260910.json"
HISTORICAL_SEAL = ROOT / "CANDIDATE_SEAL_v1.json"

REQUIRED = [
    NEW_CATALOG,
    GENERATION_FILE,
    ROOT / "launch_generation.py",
    ROOT / "phase_b_launch_chain.py",
    ROOT / "test_phase_b_launch_generation.py",
]

EXPECTED_GIT_BLOBS = {
    HISTORICAL_SEAL:
        "ac4352caead5bbfb3c02658262830407beacec8e",
    NEW_CATALOG:
        "6ba85c23bbe666baf204d29ae2145b510a164528",
    REPO_ROOT / "automation/review_dispatcher_v1/publisher.py":
        "514505257c04cb5d40cb91d65044c7d3f18d6cb8",
    REPO_ROOT / "automation/review_dispatcher_v1/t2.py":
        "fee70fa6b4cf93455a7f0c04d888be1d5b4bfb2a",
    REPO_ROOT / "buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_LAB_FIXED_v1.yml":
        "2d4ec751dee4e507a08313d403c7d0521c172ae5",
    REPO_ROOT / "buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_AUDITOR_FIXED_v1.yml":
        "c42bae003a3b1dc6d11cf5e6c33996369a4d22d6",
}

FORBIDDEN_PROVIDER_MARKERS = (
    "anthropic_api_key",
    "google_api_key",
    "gemini_api_key",
    "claude_api_key",
)

FORBIDDEN_NETWORK_EXECUTION_MARKERS = (
    "requests.",
    "httpx.",
    "urllib.request",
    "aiohttp.",
    "socket.",
    "http.client",
    "urlopen(",
    "client.interactions.create(",
    "client.messages.create(",
    "anthropic(",
    "genai.client(",
)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def validate() -> dict:
    checks: dict[str, str] = {}
    findings: list[str] = []

    def record(name: str, condition: bool, detail: str = "") -> None:
        if condition:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: {detail}")

    for path in REQUIRED:
        record(f"file:{path.name}", path.is_file(), "missing")

    for path in REQUIRED:
        if path.suffix != ".py" or not path.is_file():
            continue
        try:
            compile(path.read_text(), str(path), "exec")
            record(f"compile:{path.name}", True)
        except Exception as exc:
            record(f"compile:{path.name}", False, repr(exc))

    for path, expected in EXPECTED_GIT_BLOBS.items():
        actual = _git_blob_sha(path) if path.is_file() else "MISSING"
        record(
            f"git_blob:{path.name}",
            actual == expected,
            f"{actual} != {expected}",
        )

    old_snapshot = json.loads(OLD_CATALOG.read_text())
    new_snapshot = json.loads(NEW_CATALOG.read_text())
    static_generation = json.loads(GENERATION_FILE.read_text())

    try:
        validate_provider_catalog(old_snapshot)
        record("catalog:old_snapshot_schema_valid", True)
    except Exception as exc:
        record("catalog:old_snapshot_schema_valid", False, repr(exc))

    try:
        validate_provider_catalog(new_snapshot)
        record("catalog:new_snapshot_schema_valid", True)
    except Exception as exc:
        record("catalog:new_snapshot_schema_valid", False, repr(exc))

    try:
        build_catalog_freshness_receipt(
            old_snapshot,
            checked_at="2026-09-10T11:35:00Z",
        )
        record(
            "catalog:old_snapshot_stale_current_check",
            False,
            "stale catalog unexpectedly accepted",
        )
    except ResearchContractError as exc:
        record(
            "catalog:old_snapshot_stale_current_check",
            str(exc) == "CATALOG_SNAPSHOT_STALE",
            str(exc),
        )

    try:
        new_freshness = build_catalog_freshness_receipt(
            new_snapshot,
            checked_at="2026-09-10T11:35:00Z",
        )
        record(
            "catalog:new_snapshot_age_240",
            new_freshness["age_seconds"] == 240,
            str(new_freshness.get("age_seconds")),
        )
        record(
            "catalog:new_snapshot_within_24h",
            new_freshness["age_seconds"]
            <= new_freshness["max_age_seconds"]
            <= 86400,
            str(new_freshness),
        )
    except Exception as exc:
        record("catalog:new_snapshot_age_240", False, repr(exc))
        record("catalog:new_snapshot_within_24h", False, repr(exc))

    try:
        generation = build_current_canonical_launch_generation(
            new_snapshot
        )
        validate_current_canonical_launch_generation(
            new_snapshot,
            generation,
        )
        record(
            "launch_generation:static_exact",
            static_generation == generation,
            "static generation differs from deterministic build",
        )
    except Exception as exc:
        generation = {}
        record("launch_generation:static_exact", False, repr(exc))

    if generation:
        exact_fields = {
            "canonical_main": CANONICAL_MAIN,
            "canonical_tree": CANONICAL_TREE,
            "canonical_multimodel_subtree":
                CANONICAL_MULTIMODEL_SUBTREE,
            "reviewed_pr": REVIEWED_PR,
            "reviewed_head": REVIEWED_HEAD,
            "reviewed_lab_build": REVIEWED_LAB_BUILD,
            "reviewed_lab_comment": REVIEWED_LAB_COMMENT,
            "reviewed_t1_comment": REVIEWED_T1_COMMENT,
            "reviewed_auditor_build": REVIEWED_AUDITOR_BUILD,
            "reviewed_auditor_comment": REVIEWED_AUDITOR_COMMENT,
            "reviewed_t2_comment": REVIEWED_T2_COMMENT,
            "reviewed_test_count": REVIEWED_TEST_COUNT,
            "predecessor_candidate_seal_blob":
                PREDECESSOR_CANDIDATE_SEAL_BLOB,
        }
        for key, expected in exact_fields.items():
            record(
                f"launch_generation:{key}",
                generation.get(key) == expected,
                f"{generation.get(key)} != {expected}",
            )
        record(
            "launch_generation:predecessor_seal_historical_only",
            generation.get("predecessor_seal_is_historical_only") is True,
            str(generation.get("predecessor_seal_is_historical_only")),
        )
        record(
            "launch_generation:fresh_catalog_sha256",
            generation.get("provider_catalog_snapshot_sha256")
            == sha256_json(new_snapshot),
            str(generation.get("provider_catalog_snapshot_sha256")),
        )

        for key in (
            "provider_call_authorized",
            "credential_authorized",
            "spend_authorized",
            "live_execution_performed",
            "protected_data_effect",
            "live_business_effect",
            "adoption_authority",
        ):
            record(
                f"launch_generation:nonauthority:{key}",
                generation.get(key) is False,
                str(generation.get(key)),
            )
        record(
            "launch_generation:runtime_off",
            generation.get("runtime") == "OFF",
            str(generation.get("runtime")),
        )

    entries = {
        item["provider"]: item
        for item in new_snapshot["entries"]
    }
    gemini = entries.get("GOOGLE_GEMINI", {})
    claude = entries.get("ANTHROPIC_CLAUDE", {})
    record(
        "catalog:gemini_current_model",
        gemini.get("model_id") == "gemini-3.8-flash",
        str(gemini.get("model_id")),
    )
    record(
        "catalog:gemini_current_input_price",
        gemini.get("input_usd_micros_per_million_tokens") == 750000,
        str(gemini.get("input_usd_micros_per_million_tokens")),
    )
    record(
        "catalog:gemini_current_output_price",
        gemini.get("output_usd_micros_per_million_tokens") == 3750000,
        str(gemini.get("output_usd_micros_per_million_tokens")),
    )
    record(
        "catalog:gemini_pricing_window",
        gemini.get("pricing_valid_through") == "2026-12-31",
        str(gemini.get("pricing_valid_through")),
    )
    record(
        "catalog:claude_current_model",
        claude.get("model_id") == "claude-haiku-4-5-20251001",
        str(claude.get("model_id")),
    )
    record(
        "catalog:claude_current_input_price",
        claude.get("input_usd_micros_per_million_tokens") == 1000000,
        str(claude.get("input_usd_micros_per_million_tokens")),
    )
    record(
        "catalog:claude_current_output_price",
        claude.get("output_usd_micros_per_million_tokens") == 5000000,
        str(claude.get("output_usd_micros_per_million_tokens")),
    )

    new_production_text = "\n".join(
        (
            ROOT / "launch_generation.py",
            ROOT / "phase_b_launch_chain.py",
        )[i].read_text().lower()
        for i in range(2)
    )
    for marker in FORBIDDEN_PROVIDER_MARKERS:
        record(
            f"no_provider_credentials:{marker}",
            marker not in new_production_text,
            marker,
        )
    for marker in FORBIDDEN_NETWORK_EXECUTION_MARKERS:
        record(
            f"no_network_execution:{marker}",
            marker not in new_production_text,
            marker,
        )

    phase_a_text = (ROOT / "test_phase_a.py").read_text()
    phase_b_text = (ROOT / "test_phase_b_launch_generation.py").read_text()
    phase_a_count = len(
        re.findall(r"^\s+def test_\d+_", phase_a_text, re.M)
    )
    phase_b_count = len(
        re.findall(r"^\s+def test_\d+_", phase_b_text, re.M)
    )
    record(
        "tests:phase_a_exact_478",
        phase_a_count == 478,
        f"{phase_a_count} != 478",
    )
    record(
        "tests:phase_b_exact_18",
        phase_b_count == 18,
        f"{phase_b_count} != 18",
    )
    record(
        "tests:cumulative_exact_496",
        phase_a_count + phase_b_count == 496,
        f"{phase_a_count + phase_b_count} != 496",
    )

    return {
        "schema": "MULTIVERSE_PHASE_B_LAUNCH_GENERATION_VALIDATOR_v1",
        "verdict": "PASS" if not findings else "FIX_REQUIRED",
        "checks": checks,
        "findings": findings,
        "live_provider_execution": False,
        "provider_credentials": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
