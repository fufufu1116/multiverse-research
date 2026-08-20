#!/usr/bin/env python3
"""Selftest for zero-history resume resolver candidate."""

from __future__ import annotations

import copy

from multiverse_zero_history_resume_resolver_v1 import resolve


BASE = {
    "current_operational_resolution": {
        "mode": "FOUNDATION_AUDIT_CONTINUATION",
        "scientific_resume_allowed": False,
        "read_first_pr": 16,
        "read_first_exact_head": "45b1721c73bafffcf1635af46e56e5f6c06f4a55",
    },
    "paused_child": {
        "post_pause_run_disposition": "QUARANTINED_NOT_ADMITTED"
    },
    "foundation_gates": {
        "G1_PAUSE_SEMANTICS_FIXED": "CANDIDATE_IMPLEMENTED_SELFTEST_PASS_REVIEW_PENDING",
        "G2_CURRENT_STATE_SYNCHRONIZED": "CANDIDATE_EXISTS_REVIEW_PENDING",
        "G3_REVIEW_LIFECYCLE_REGISTRY_EXISTS": "CANDIDATE_EXISTS_REVIEW_PENDING",
        "G4_ZERO_HISTORY_RESUME_POINTER_DETERMINISTIC": "THIS_CANDIDATE_REVIEW_PENDING",
        "G5_OWNER_ASSURANCE_MINIMAL_VIEW": "CANDIDATE_EXISTS_REVIEW_PENDING",
    },
    "resume_permission_requirements": ["EXAMPLE_REQUIREMENT"]
}


def expect(mode: str, allowed: bool, value: dict, label: str) -> None:
    result = resolve(value)
    assert result["mode"] == mode, (label, result)
    assert result["scientific_resume_allowed"] is allowed, (label, result)


def main() -> None:
    # Current Owner pause must orient to PR #16 and deny scientific resume.
    expect("FOUNDATION_AUDIT_CONTINUATION", False, BASE, "current pause orientation")
    current = resolve(BASE)
    assert current["read_first_pr"] == 16
    assert current["read_first_exact_head"] == "45b1721c73bafffcf1635af46e56e5f6c06f4a55"

    # Contradictory pause mode cannot authorize execution.
    contradiction = copy.deepcopy(BASE)
    contradiction["current_operational_resolution"]["scientific_resume_allowed"] = True
    expect("RECOVERY_AMBIGUOUS", False, contradiction, "pause contradiction")

    # Missing/changed G1-G5 set fails closed.
    missing_gate = copy.deepcopy(BASE)
    del missing_gate["foundation_gates"]["G5_OWNER_ASSURANCE_MINIMAL_VIEW"]
    expect("RECOVERY_AMBIGUOUS", False, missing_gate, "missing gate")

    # Leaving pause mode does not resume science while G1-G5 remain unaccepted.
    gates_pending = copy.deepcopy(BASE)
    gates_pending["current_operational_resolution"]["mode"] = "POST_AUDIT_REVIEW"
    expect("FOUNDATION_GATE_INCOMPLETE", False, gates_pending, "gates pending")

    # Even with all gates accepted, unresolved quarantine blocks resume before any metric-aware choice.
    quarantine_pending = copy.deepcopy(gates_pending)
    for key in quarantine_pending["foundation_gates"]:
        quarantine_pending["foundation_gates"][key] = "PASS"
    expect("QUARANTINE_DISPOSITION_REQUIRED", False, quarantine_pending, "quarantine unresolved")

    # After neutral quarantine disposition, an explicit accepted resume pointer is still required.
    pointer_missing = copy.deepcopy(quarantine_pending)
    pointer_missing["paused_child"]["post_pause_run_disposition"] = "REJECTED_WITHOUT_METRIC_INSPECTION"
    expect("EXPLICIT_RESUME_POINTER_REQUIRED", False, pointer_missing, "explicit pointer missing")

    # A present pointer that does not explicitly authorize scientific execution remains closed.
    pointer_closed = copy.deepcopy(pointer_missing)
    pointer_closed["accepted_resume_pointer"] = {
        "pr": 14,
        "exact_head": "e70bda39a5d3ce585af4e028b35106b859871bd9",
        "next_gate": "EXAMPLE_NEXT_GATE",
        "scientific_resume_allowed": False,
    }
    expect("EXPLICIT_RESUME_POINTER_PRESENT_BUT_CLOSED", False, pointer_closed, "explicit pointer closed")

    # Only a structurally valid, explicit accepted pointer can authorize resume.
    pointer_open = copy.deepcopy(pointer_closed)
    pointer_open["accepted_resume_pointer"]["scientific_resume_allowed"] = True
    expect("SCIENTIFIC_RESUME_EXPLICITLY_AUTHORIZED", True, pointer_open, "explicit pointer open")

    print("MULTIVERSE_ZERO_HISTORY_RESUME_RESOLVER_SELFTEST_PASS")


if __name__ == "__main__":
    main()
