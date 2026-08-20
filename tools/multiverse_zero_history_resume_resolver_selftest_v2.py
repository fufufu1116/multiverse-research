#!/usr/bin/env python3
"""Selftest for zero-history orientation resolver v2 candidate."""

from __future__ import annotations

import copy

from multiverse_zero_history_resume_resolver_v2 import DENY, resolve

BASE = {
    "record": "MULTIVERSE_ZERO_HISTORY_RESUME_POINTER_CANDIDATE_20260820_v2",
    "canonical_authority": False,
    "execution_authority": "NONE_ORIENTATION_ONLY",
    "current_operational_resolution": {
        "mode": "FOUNDATION_LAB_REMEDIATION_CONTINUATION",
        "scientific_resume_allowed": False,
        "read_first_pr": 22,
        "read_first_anchor_head": "6b31cbc226ad135f240b7487a83380fd29e48766",
        "fresh_read_current_pr_head_required": True,
    },
    "paused_child": {
        "post_pause_run_disposition": "QUARANTINED_NOT_ADMITTED"
    },
    "foundation_gates": {
        "G1_PAUSE_SEMANTICS_FIXED": "LAB_FIX_IN_REMEDIATION_REVIEW_PENDING",
        "G2_CURRENT_STATE_SYNCHRONIZED": "LAB_REFRESH_IN_REMEDIATION_REVIEW_PENDING",
        "G3_REVIEW_LIFECYCLE_REGISTRY_EXISTS": "LAB_REFRESH_IN_REMEDIATION_REVIEW_PENDING",
        "G4_ZERO_HISTORY_RESUME_POINTER_DETERMINISTIC": "LAB_MATERIAL_BLOCK_V1_REMEDIATED_BY_ORIENTATION_ONLY_V2_REVIEW_PENDING",
        "G5_OWNER_ASSURANCE_MINIMAL_VIEW": "LAB_G5_MAY_BE_ACCEPTED_YES_NOT_CANONICAL",
    },
    "external_execution_authorization_requirements": [
        "SEPARATE_CANONICAL_EXECUTION_AUTHORIZATION_GATE_REQUIRED"
    ],
}


def assert_never_authorizes(value: dict, label: str, expected_mode: str | None = None, expected_reason: str | None = None) -> dict:
    result = resolve(value)
    assert result["decision"] == DENY, (label, result)
    assert result["scientific_resume_allowed"] is False, (label, result)
    assert result["execution_authority"] == "NONE_ORIENTATION_ONLY", (label, result)
    if expected_mode is not None:
        assert result["mode"] == expected_mode, (label, result)
    if expected_reason is not None:
        assert result["reason_code"] == expected_reason, (label, result)
    return result


def main() -> None:
    current = assert_never_authorizes(BASE, "current", "ORIENTATION_ONLY", "OWNER_PAUSE_FOUNDATION_REMEDIATION_ORIENTATION")
    assert current["read_first_pr"] == 22
    assert current["read_first_anchor_head"] == "6b31cbc226ad135f240b7487a83380fd29e48766"
    assert current["fresh_read_current_pr_head_required"] is True

    # A locally edited orientation pointer cannot self-authorize execution.
    embedded_true = copy.deepcopy(BASE)
    embedded_true["current_operational_resolution"]["scientific_resume_allowed"] = True
    assert_never_authorizes(embedded_true, "embedded true", "RECOVERY_AMBIGUOUS", "EMBEDDED_EXECUTION_AUTHORITY_FORBIDDEN")

    # Reintroducing the v1-style accepted_resume_pointer is explicitly forbidden.
    injected_pointer = copy.deepcopy(BASE)
    injected_pointer["accepted_resume_pointer"] = {
        "pr": 14,
        "exact_head": "e70bda39a5d3ce585af4e028b35106b859871bd9",
        "next_gate": "EXAMPLE",
        "scientific_resume_allowed": True,
    }
    assert_never_authorizes(injected_pointer, "injected pointer", "RECOVERY_AMBIGUOUS", "EMBEDDED_ACCEPTED_RESUME_POINTER_FORBIDDEN")

    # Even caller-asserted all-PASS gates never produce ALLOW.
    all_pass = copy.deepcopy(BASE)
    all_pass["current_operational_resolution"]["mode"] = "POST_FOUNDATION_REVIEW"
    for key in all_pass["foundation_gates"]:
        all_pass["foundation_gates"][key] = "PASS"
    assert_never_authorizes(all_pass, "all pass", "ORIENTATION_ONLY", "ORIENTATION_ONLY_EXTERNAL_EXECUTION_GATE_REQUIRED")

    # Arbitrary quarantine text cannot become execution authority because this resolver has none.
    arbitrary_quarantine = copy.deepcopy(all_pass)
    arbitrary_quarantine["paused_child"]["post_pause_run_disposition"] = "ARBITRARY_LOCAL_STRING"
    assert_never_authorizes(arbitrary_quarantine, "arbitrary quarantine", "ORIENTATION_ONLY")

    # Structural corruption fails closed.
    missing_gate = copy.deepcopy(BASE)
    del missing_gate["foundation_gates"]["G5_OWNER_ASSURANCE_MINIMAL_VIEW"]
    assert_never_authorizes(missing_gate, "missing gate", "RECOVERY_AMBIGUOUS", "FOUNDATION_GATE_SET_MISMATCH")

    bad_anchor = copy.deepcopy(BASE)
    bad_anchor["current_operational_resolution"]["read_first_anchor_head"] = "short"
    assert_never_authorizes(bad_anchor, "bad anchor", "RECOVERY_AMBIGUOUS", "INVALID_ORIENTATION_TARGET")

    canonical_claim = copy.deepcopy(BASE)
    canonical_claim["canonical_authority"] = True
    assert_never_authorizes(canonical_claim, "canonical claim", "RECOVERY_AMBIGUOUS", "ORIENTATION_POINTER_MUST_REMAIN_NONCANONICAL")

    print("MULTIVERSE_ZERO_HISTORY_RESUME_RESOLVER_V2_SELFTEST_PASS")


if __name__ == "__main__":
    main()
