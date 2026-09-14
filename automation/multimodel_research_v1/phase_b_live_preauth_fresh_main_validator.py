from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from automation.multimodel_research_v1.phase_b_live_preauth_fresh_main import (
    CANONICAL_MAIN,
    CANONICAL_MULTIMODEL_SUBTREE,
    CANONICAL_TREE,
    FIXED_AUDITOR_STEPS_BLOB,
    FIXED_LAB_STEPS_BLOB,
    MAX_COST_USD_MICROS,
    PR313_REQUEST_ARBITRATION_BLOB,
    PR313_REQUEST_ARBITRATION_TEST_BLOB,
    PUBLISHER_BLOB,
    T2_BLOB,
    build_first_live_provider_preauth,
    first_live_provider_preauth_sha256,
    packet_summary,
    validate_first_live_provider_preauth,
)

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]

EXPECTED_GIT_BLOBS = {
    REPO_ROOT / "automation/review_dispatcher_v1/request_arbitration_v6.py": PR313_REQUEST_ARBITRATION_BLOB,
    REPO_ROOT / "automation/review_dispatcher_v1/test_request_arbitration_v6.py": PR313_REQUEST_ARBITRATION_TEST_BLOB,
    REPO_ROOT / "automation/review_dispatcher_v1/publisher.py": PUBLISHER_BLOB,
    REPO_ROOT / "automation/review_dispatcher_v1/t2.py": T2_BLOB,
    REPO_ROOT / "buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_LAB_FIXED_v1.yml": FIXED_LAB_STEPS_BLOB,
    REPO_ROOT / "buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_AUDITOR_FIXED_v1.yml": FIXED_AUDITOR_STEPS_BLOB,
}

FORBIDDEN_MARKERS = (
    "import requests", "import httpx", "urllib.request", "aiohttp.", "socket.",
    "http.client", "urlopen(", ".interactions.create(", ".messages.create(",
)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _test_count(path: Path) -> int:
    return len(re.findall(r"^\s+def test_\d+_", path.read_text(), re.M))


def validate() -> dict:
    checks = {}
    findings = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        checks[name] = "PASS" if ok else "FIX_REQUIRED"
        if not ok:
            findings.append(f"{name}: {detail}")

    for path, expected in EXPECTED_GIT_BLOBS.items():
        actual = _git_blob_sha(path) if path.is_file() else "MISSING"
        record(f"control_blob:{path.name}", actual == expected, f"{actual} != {expected}")

    try:
        packet = build_first_live_provider_preauth()
        validate_first_live_provider_preauth(packet)
        summary = packet_summary()
        record("preauth:build_validate", True)
    except Exception as exc:
        packet = {}
        summary = {}
        record("preauth:build_validate", False, repr(exc))

    if packet:
        c = packet["canonical"]
        record("canonical:main", c["main"] == CANONICAL_MAIN, c["main"])
        record("canonical:tree", c["tree"] == CANONICAL_TREE, c["tree"])
        record("canonical:multimodel_subtree", c["multimodel_subtree"] == CANONICAL_MULTIMODEL_SUBTREE, c["multimodel_subtree"])
        record("authority:runtime_off", packet["authority"]["runtime"] == "OFF")
        record("authority:all_false", all(v is False for k, v in packet["authority"].items() if k != "runtime"))
        record("request:store_false", packet["exact_request_body"]["store"] is False)
        record("retry:one_attempt", packet["retry_policy"]["max_attempts"] == 1)
        record("cost:bounded", packet["limits"]["proposed_owner_spend_ceiling_usd_micros"] == MAX_COST_USD_MICROS)
        record("digest:exact", summary.get("preauth_sha256") == first_live_provider_preauth_sha256(packet))

    successor_text = (ROOT / "phase_b_live_preauth_fresh_main.py").read_text().lower()
    legacy_text = (ROOT / "phase_b_live_preauth.py").read_text().lower()
    for marker in FORBIDDEN_MARKERS:
        record(f"no_execution:{marker}", marker not in successor_text and marker not in legacy_text, marker)

    counts = {
        "phase_a": _test_count(ROOT / "test_phase_a.py"),
        "phase_b_launch": _test_count(ROOT / "test_phase_b_launch_generation.py"),
        "execution_packet": _test_count(ROOT / "test_phase_b_execution_packet.py"),
        "pr305_preauth": _test_count(ROOT / "test_phase_b_live_preauth.py"),
        "fresh_successor": _test_count(ROOT / "test_phase_b_live_preauth_fresh_main.py"),
    }
    record("tests:phase_a_478", counts["phase_a"] == 478, str(counts["phase_a"]))
    record("tests:phase_b_launch_18", counts["phase_b_launch"] == 18, str(counts["phase_b_launch"]))
    record("tests:execution_packet_24", counts["execution_packet"] == 24, str(counts["execution_packet"]))
    record("tests:pr305_preauth_36", counts["pr305_preauth"] == 36, str(counts["pr305_preauth"]))
    record("tests:fresh_successor_8", counts["fresh_successor"] == 8, str(counts["fresh_successor"]))
    record("tests:cumulative_564", sum(counts.values()) == 564, str(sum(counts.values())))

    return {
        "schema": "MULTIVERSE_FIRST_LIVE_PROVIDER_PILOT_PREAUTH_FRESH_MAIN_VALIDATOR_v1",
        "verdict": "PASS" if not findings else "FIX_REQUIRED",
        "checks": checks,
        "findings": findings,
        "test_counts": counts,
        "packet_summary": summary,
        "provider_call_authorized": False,
        "provider_credentials": False,
        "spend_authorized": False,
        "live_effect": False,
        "runtime": "OFF",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
