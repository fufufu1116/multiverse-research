#!/usr/bin/env python3
"""Exact-head governance integration selftest for Foundation Lab remediation v1.

No Keirin scientific workflow/model/result code is invoked by this test.
"""

from __future__ import annotations

import json
from pathlib import Path

from multiverse_owner_assurance_view_v1 import build_view
from multiverse_pause_guard_v2 import DENY as GUARD_DENY, evaluate_state
from multiverse_zero_history_resume_resolver_v2 import resolve

ROOT = Path(__file__).resolve().parents[1]
GOV = ROOT / "governance"


def load(name: str) -> dict:
    value = json.loads((GOV / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def item(registry: dict, pr: int) -> dict:
    matches = [x for x in registry["open_items"] if x.get("pr") == pr]
    assert len(matches) == 1, (pr, matches)
    return matches[0]


def main() -> None:
    safe = load("MULTIVERSE_SAFE_MODE_STATE_CANDIDATE_20260820_v2.json")
    pointer = load("MULTIVERSE_ZERO_HISTORY_RESUME_POINTER_CANDIDATE_20260820_v2.json")
    lifecycle = load("MULTIVERSE_OPEN_WORK_LIFECYCLE_REGISTRY_20260820_v3.json")
    operational = load("KEIRIN_OPERATIONAL_STATE_SYNC_CANDIDATE_20260820_v3.json")

    # G1 remediation: pause blocks Keirin science and containment no longer self-authorizes.
    science = evaluate_state(safe, domain="KEIRIN", operation="SCIENTIFIC_EXECUTION", expected_generation=2)
    assert science["decision"] == GUARD_DENY and science["reason_code"] == "OWNER_PAUSE_SCOPE_DENY", science
    containment = evaluate_state(safe, domain="KEIRIN", operation="REVERSIBLE_CONTAINMENT", expected_generation=2)
    assert containment["decision"] == GUARD_DENY, containment
    assert containment["reason_code"] == "REVERSIBLE_CONTAINMENT_REQUIRES_SEPARATE_AUDITABLE_PAUSE_REPAIR_AUTHORIZATION", containment

    # G4 remediation: zero-history resolver is orientation-only and structurally cannot authorize science.
    orientation = resolve(pointer)
    assert orientation["mode"] == "ORIENTATION_ONLY", orientation
    assert orientation["decision"] == "DENY", orientation
    assert orientation["scientific_resume_allowed"] is False, orientation
    assert orientation["execution_authority"] == "NONE_ORIENTATION_ONLY", orientation
    assert orientation["read_first_pr"] == 22, orientation
    assert orientation["read_first_anchor_head"] == "6b31cbc226ad135f240b7487a83380fd29e48766", orientation
    assert orientation["fresh_read_current_pr_head_required"] is True, orientation

    # G2/G3 refresh: exact Lab outcomes are represented, not the former REQUESTED snapshot.
    p16 = item(lifecycle, 16)
    p17 = item(lifecycle, 17)
    p18 = item(lifecycle, 18)
    p20 = item(lifecycle, 20)
    p21 = item(lifecycle, 21)
    p22 = item(lifecycle, 22)
    assert (p16["lab_verdict"], p16["lab_comment_id"]) == ("PASS_WITH_FIXES", 5356392738)
    assert (p17["lab_verdict"], p17["lab_comment_id"], p17["g4_may_be_accepted"]) == ("MATERIAL_BLOCK", 5356396200, False)
    assert (p18["lab_verdict"], p18["lab_comment_id"], p18["g5_may_be_accepted"]) == ("PASS_WITH_FIXES", 5356399606, True)
    assert (p20["lab_verdict"], p20["lab_comment_id"]) == ("PASS", 5356402581)
    assert (p21["lab_verdict"], p21["lab_comment_id"], p21["g2_g3_may_be_accepted"]) == ("PASS_WITH_FIXES", 5356410689, False)
    assert p22["current_head_resolution"] == "FRESH_READ_PR22_REQUIRED"

    review = operational["foundation_review_state"]
    assert review["pr17"]["lab_verdict"] == "MATERIAL_BLOCK"
    assert review["pr17"]["G4_MAY_BE_ACCEPTED"] is False
    assert review["pr18"]["G5_MAY_BE_ACCEPTED"] is True
    assert review["pr18"]["stacked_G4_cleared"] is False
    assert review["pr20"]["lab_verdict"] == "PASS"
    assert review["pr21"]["G2_G3_MAY_BE_ACCEPTED"] is False

    # Foundation is still not accepted and science is still paused.
    assert lifecycle["all_foundation_gates_accepted"] is False
    assert lifecycle["scientific_resume_allowed"] is False
    assert operational["all_foundation_gates_accepted"] is False
    assert operational["explicit_scientific_execution_authorization_exists"] is False
    assert operational["scientific_resume_allowed"] is False

    # Existing G5 renderer must accept refreshed inputs without changing G5 logic.
    view = build_view(lifecycle, operational, safe)
    assert "PAUSED（科学実験停止中）" in view
    assert "ECON_HOLDOUT1000:** SEALED" in view
    assert "RESULT/PAYOUT:** UNAUTHORIZED" in view

    # Firewall terminals.
    assert lifecycle["global_scientific_firewall"]["ECON_HOLDOUT1000"] == "SEALED"
    assert lifecycle["global_scientific_firewall"]["RESULT_PAYOUT"] == "UNAUTHORIZED"
    assert operational["scientific_firewall_preserved"]["new_untouched_validation_opened"] is False
    assert operational["scientific_firewall_preserved"]["model_promotion"] == "PROHIBITED"

    print("MULTIVERSE_FOUNDATION_LAB_REMEDIATION_V1_SELFTEST_PASS")
    print("SCIENTIFIC_EXECUTION_PERFORMED=false")
    print("RESULT_PAYOUT_ACCESSED=false")
    print("HOLDOUT_ACCESSED=false")
    print("PR15_QUARANTINED_METRICS_INSPECTED=false")
    print("SCIENTIFIC_RESUME_ALLOWED=false")


if __name__ == "__main__":
    main()
