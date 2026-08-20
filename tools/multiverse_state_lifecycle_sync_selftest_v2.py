#!/usr/bin/env python3
"""Fail-closed selftest for the noncanonical Multiverse state/lifecycle v2 sync candidate.

This test reads governance JSON only. It does not execute Keirin science, access
RESULT/PAYOUT, open holdouts, contact providers, or authorize resume.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / "governance/MULTIVERSE_OPEN_WORK_LIFECYCLE_REGISTRY_20260820_v2.json"
OPERATIONAL = ROOT / "governance/KEIRIN_OPERATIONAL_STATE_SYNC_CANDIDATE_20260820_v2.json"
MAIN = "819afb723c8f14000757b2e53b6664d71ab01227"


def load(path: Path):
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), path
    return value


def by_pr(items, pr):
    found = [x for x in items if x.get("pr") == pr]
    assert len(found) == 1, (pr, len(found))
    return found[0]


def main() -> int:
    lifecycle = load(LIFECYCLE)
    operational = load(OPERATIONAL)

    assert lifecycle["registry_is_authoritative"] is False
    assert lifecycle["canonical_main_observed"] == MAIN
    assert operational["canonical_main_observed"] == MAIN
    assert lifecycle["owner_global_keirin_directive"] == "PAUSED_FOR_MULTIVERSE_ZERO_BASE_FOUNDATION_AUDIT"
    assert lifecycle["review_truth_rule"] == "REVIEW_REQUESTED_IS_NOT_REVIEW_PASSED; LAB_PASS_APPLIES_ONLY_TO_ITS_EXACT_REVIEWED_HEAD."

    items = lifecycle["open_items"]
    expected_prs = {1, 4, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20}
    assert {x["pr"] for x in items} == expected_prs
    assert len(items) == len(expected_prs)

    expected_heads = {
        12: "05f636ce82b3eeb45bedc6652182f1dda6a7481b",
        13: "096ffebf24c5c3f747ff3024899f4512c5a8b348",
        14: "500a96f8bc38d151a4240f0aba576e7ede9e232b",
        15: "6d10cad66cf4e6040faec547f155b8a5c9e0ea03",
        16: "45b1721c73bafffcf1635af46e56e5f6c06f4a55",
        17: "3d95f20d65eaaa0647f0c854b6bcebc31258938a",
        18: "5240242543f475bb72fa5eaed4bb4d2db892062e",
        20: "0d896bc5349c8eb5837ec90f79de336af761d00c",
    }
    for pr, head in expected_heads.items():
        assert by_pr(items, pr)["current_head"] == head

    pr12 = by_pr(items, 12)
    assert pr12["lab_reviewed_head"] == "2e070d8094abdda9138865787e5540087fa05ea3"
    assert pr12["current_head"] != pr12["lab_reviewed_head"]
    assert "PAUSE_CONTROL_HEAD" in pr12["classification"]
    assert pr12["automatic_scientific_execution"] == "DISABLED_MANUAL_ONLY_PAUSE_STUB"

    pr14 = by_pr(items, 14)
    assert pr14["lab_reviewed_head"] == "e70bda39a5d3ce585af4e028b35106b859871bd9"
    assert pr14["current_head"] != pr14["lab_reviewed_head"]
    assert "LAB_PASS" in pr14["classification"]
    assert "PAUSE_CONTROL_HEAD" in pr14["classification"]
    assert pr14["automatic_scientific_execution"] == "DISABLED_MANUAL_ONLY_PAUSE_STUBS_ATOMIC_TWO_WORKFLOW_CHANGE"

    pr15 = by_pr(items, 15)
    assert {"PAUSED", "QUARANTINED"}.issubset(set(pr15["classification"]))
    assert pr15["post_pause_run_disposition"] == "QUARANTINED_NOT_ADMITTED"

    for pr in (16, 17, 18, 20):
        item = by_pr(items, pr)
        assert "LAB_REVIEW_REQUESTED" in item["classification"]
        assert item["review_state"] == "LAB_REVIEW_REQUESTED_NO_FINAL_RESULT"
        assert "LAB_PASS" not in item["classification"]

    closed = lifecycle["recent_closed_items"]
    assert len(closed) == 1
    assert closed[0]["pr"] == 19
    assert closed[0]["state"] == "CLOSED_NOT_MERGED"
    assert closed[0]["superseded_by_pr"] == 18
    assert closed[0]["scientific_execution_resumed"] is False

    op = operational["operational_state"]
    assert op["keirin_research"] == "PAUSED_FOR_MULTIVERSE_ZERO_BASE_FOUNDATION_AUDIT"
    assert op["new_scientific_execution_allowed"] is False
    assert op["audit_recovery_evidence_work_allowed"] is True
    assert op["foundation_stack_prs"] == [16, 17, 18, 20]
    assert operational["scientific_resume_allowed"] is False
    assert operational["all_foundation_gates_accepted"] is False
    assert operational["explicit_resume_pointer_accepted"] is False

    latest = operational["latest_legitimate_completed_scientific_checkpoint"]
    assert latest["pr"] == 14
    assert latest["exact_lab_reviewed_scientific_head"] == pr14["lab_reviewed_head"]
    assert latest["current_pause_control_head"] == pr14["current_head"]
    assert latest["real_world_model_winner_claim"] is False
    assert latest["model_promotion_allowed"] is False

    for pr in (16, 17, 18, 20):
        state = operational["foundation_review_state"][f"pr{pr}"]
        assert state["head"] == by_pr(items, pr)["current_head"]
        assert state["state"] == "LAB_REVIEW_REQUESTED_NO_FINAL_RESULT"

    exposure = operational["workflow_pause_exposure"]
    assert exposure["workflow_count"] == 59
    assert exposure["keirin_sensitive_name_count"] == 56
    assert exposure["sensitive_push_self_file_only"] == 41
    assert exposure["sensitive_push_restricted_paths"] == 11
    assert exposure["sensitive_push_any_path"] == 0
    assert exposure["sensitive_pull_request_any_path"] == 0
    assert exposure["sensitive_schedule"] == 0
    assert exposure["target_workflow_execution_performed_by_inventory"] is False

    for value in operational["foundation_resume_gate"].values():
        assert "PENDING" in value

    lf = lifecycle["global_scientific_firewall"]
    of = operational["scientific_firewall_preserved"]
    assert lf["ECON_HOLDOUT1000"] == of["ECON_HOLDOUT1000"] == "SEALED"
    assert lf["RESULT_PAYOUT"] == of["RESULT_PAYOUT"] == "UNAUTHORIZED"
    assert lf["UNTOUCHED_VALIDATION"] == "CLOSED"
    assert of["new_untouched_validation_opened"] is False
    assert lf["MODEL_PROMOTION"] == of["model_promotion"] == "PROHIBITED"
    assert lf["REAL_MONEY_WAGERING"] == of["real_money_wagering"] == "OUT_OF_SCOPE"
    assert lifecycle["owner_action_now"] == operational["owner_action_now"] == "NONE"

    print("MULTIVERSE_STATE_LIFECYCLE_SYNC_V2_SELFTEST_PASS")
    print("SCIENTIFIC_EXECUTION_PERFORMED=false")
    print("RESULT_PAYOUT_ACCESSED=false")
    print("HOLDOUT_ACCESSED=false")
    print("SCIENTIFIC_RESUME_ALLOWED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
