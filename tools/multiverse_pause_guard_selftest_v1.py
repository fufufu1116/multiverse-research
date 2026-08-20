#!/usr/bin/env python3
"""Selftest for multiverse_pause_guard_v1.py candidate."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from multiverse_pause_guard_v1 import ALLOW, DENY, evaluate_file, evaluate_state


BASE = {
    "candidate_generation": 1,
    "safe_mode": {
        "active": True,
        "scope": ["KEIRIN_SCIENTIFIC_EXECUTION"],
    },
}


def expect(decision: str, result: dict, label: str, reason: str | None = None) -> None:
    assert result["decision"] == decision, (label, result)
    if reason is not None:
        assert result["reason_code"] == reason, (label, result)


def main() -> None:
    # Owner pause must block Keirin scientific execution.
    expect(
        DENY,
        evaluate_state(BASE, domain="KEIRIN", operation="SCIENTIFIC_EXECUTION", expected_generation=1),
        "paused keirin scientific execution",
        "OWNER_PAUSE_SCOPE_DENY",
    )

    # Audit/recovery/evidence work remains possible during safe mode.
    for op in ("AUDIT_READ", "RECOVERY_READ_VERIFY", "EVIDENCE_PRESERVATION", "REVERSIBLE_CONTAINMENT"):
        expect(ALLOW, evaluate_state(BASE, domain="KEIRIN", operation=op, expected_generation=1), op)

    # Protected/model/external operations remain denied regardless of pause repair activity.
    for op in ("PROTECTED_DATA_OPEN", "MODEL_PROMOTION", "EXTERNAL_PROVIDER_CONTACT"):
        expect(DENY, evaluate_state(BASE, domain="KEIRIN", operation=op, expected_generation=1), op)

    # Unknown operations and stale generation fail closed.
    expect(DENY, evaluate_state(BASE, domain="KEIRIN", operation="MAGIC_UNKNOWN"), "unknown operation", "UNKNOWN_OPERATION_DENY")
    expect(
        DENY,
        evaluate_state(BASE, domain="KEIRIN", operation="SCIENTIFIC_EXECUTION", expected_generation=0),
        "stale generation",
        "STALE_EXPECTED_GENERATION_DENY",
    )

    # A scoped Keirin pause does not silently become a global scientific pause.
    expect(
        ALLOW,
        evaluate_state(BASE, domain="OTHER_DOMAIN", operation="SCIENTIFIC_EXECUTION", expected_generation=1),
        "outside scoped pause",
        "SAFE_MODE_ACTIVE_BUT_DOMAIN_OUTSIDE_PAUSE_SCOPE",
    )

    # Once safe mode is explicitly inactive, this guard no longer blocks ordinary scientific execution.
    inactive = copy.deepcopy(BASE)
    inactive["candidate_generation"] = 2
    inactive["safe_mode"]["active"] = False
    expect(
        ALLOW,
        evaluate_state(inactive, domain="KEIRIN", operation="SCIENTIFIC_EXECUTION", expected_generation=2),
        "explicit safe-mode exit",
        "SAFE_MODE_INACTIVE_SCIENTIFIC_EXECUTION_NOT_BLOCKED_BY_THIS_GUARD",
    )

    # File-level behavior must deny missing/malformed state and pass valid state.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        missing = root / "missing.json"
        expect(DENY, evaluate_file(missing, domain="KEIRIN", operation="SCIENTIFIC_EXECUTION"), "missing file", "MISSING_STATE_DENY")

        malformed = root / "bad.json"
        malformed.write_text("{not-json", encoding="utf-8")
        expect(
            DENY,
            evaluate_file(malformed, domain="KEIRIN", operation="SCIENTIFIC_EXECUTION"),
            "malformed file",
            "UNREADABLE_OR_MALFORMED_STATE_DENY",
        )

        valid = root / "state.json"
        valid.write_text(json.dumps(BASE), encoding="utf-8")
        expect(
            DENY,
            evaluate_file(valid, domain="KEIRIN", operation="SCIENTIFIC_EXECUTION", expected_generation=1),
            "valid paused file",
            "OWNER_PAUSE_SCOPE_DENY",
        )

    print("MULTIVERSE_PAUSE_GUARD_SELFTEST_PASS")


if __name__ == "__main__":
    main()
