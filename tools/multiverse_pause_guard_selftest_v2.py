#!/usr/bin/env python3
"""Selftest for Multiverse pause guard v2 candidate."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from multiverse_pause_guard_v2 import ALLOW, DENY, evaluate_file, evaluate_state

BASE = {
    "candidate_generation": 2,
    "safe_mode": {"active": True, "scope": ["KEIRIN_SCIENTIFIC_EXECUTION"]},
}


def expect(decision: str, result: dict, label: str, reason: str | None = None) -> None:
    assert result["decision"] == decision, (label, result)
    if reason is not None:
        assert result["reason_code"] == reason, (label, result)


def main() -> None:
    expect(
        DENY,
        evaluate_state(BASE, domain="KEIRIN", operation="SCIENTIFIC_EXECUTION", expected_generation=2),
        "paused keirin science",
        "OWNER_PAUSE_SCOPE_DENY",
    )

    for op in ("AUDIT_READ", "RECOVERY_READ_VERIFY", "EVIDENCE_PRESERVATION"):
        expect(ALLOW, evaluate_state(BASE, domain="KEIRIN", operation=op, expected_generation=2), op)

    expect(
        DENY,
        evaluate_state(BASE, domain="KEIRIN", operation="REVERSIBLE_CONTAINMENT", expected_generation=2),
        "containment requires separate authorization",
        "REVERSIBLE_CONTAINMENT_REQUIRES_SEPARATE_AUDITABLE_PAUSE_REPAIR_AUTHORIZATION",
    )

    for op in ("PROTECTED_DATA_OPEN", "MODEL_PROMOTION", "EXTERNAL_PROVIDER_CONTACT"):
        expect(DENY, evaluate_state(BASE, domain="KEIRIN", operation=op, expected_generation=2), op)

    expect(DENY, evaluate_state(BASE, domain="KEIRIN", operation="MAGIC_UNKNOWN"), "unknown", "UNKNOWN_OPERATION_DENY")
    expect(
        DENY,
        evaluate_state(BASE, domain="KEIRIN", operation="SCIENTIFIC_EXECUTION", expected_generation=1),
        "stale generation",
        "STALE_EXPECTED_GENERATION_DENY",
    )

    expect(
        ALLOW,
        evaluate_state(BASE, domain="OTHER_DOMAIN", operation="SCIENTIFIC_EXECUTION", expected_generation=2),
        "outside pause scope",
        "SAFE_MODE_ACTIVE_BUT_DOMAIN_OUTSIDE_PAUSE_SCOPE",
    )

    inactive = copy.deepcopy(BASE)
    inactive["candidate_generation"] = 3
    inactive["safe_mode"]["active"] = False
    expect(
        ALLOW,
        evaluate_state(inactive, domain="KEIRIN", operation="SCIENTIFIC_EXECUTION", expected_generation=3),
        "inactive science",
        "SAFE_MODE_INACTIVE_SCIENTIFIC_EXECUTION_NOT_BLOCKED_BY_THIS_GUARD",
    )
    expect(
        DENY,
        evaluate_state(inactive, domain="KEIRIN", operation="REVERSIBLE_CONTAINMENT", expected_generation=3),
        "inactive containment still separately authorized",
        "REVERSIBLE_CONTAINMENT_REQUIRES_SEPARATE_AUTHORIZATION",
    )

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        expect(DENY, evaluate_file(root / "missing.json", domain="KEIRIN", operation="SCIENTIFIC_EXECUTION"), "missing", "MISSING_STATE_DENY")
        bad = root / "bad.json"
        bad.write_text("{not-json", encoding="utf-8")
        expect(DENY, evaluate_file(bad, domain="KEIRIN", operation="SCIENTIFIC_EXECUTION"), "malformed", "UNREADABLE_OR_MALFORMED_STATE_DENY")
        good = root / "state.json"
        good.write_text(json.dumps(BASE), encoding="utf-8")
        expect(DENY, evaluate_file(good, domain="KEIRIN", operation="SCIENTIFIC_EXECUTION", expected_generation=2), "valid paused", "OWNER_PAUSE_SCOPE_DENY")

    print("MULTIVERSE_PAUSE_GUARD_V2_SELFTEST_PASS")


if __name__ == "__main__":
    main()
