#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIFE = ROOT / "governance/MULTIVERSE_OPEN_WORK_LIFECYCLE_REGISTRY_20260820_v4.json"
OP = ROOT / "governance/KEIRIN_OPERATIONAL_STATE_SYNC_CANDIDATE_20260820_v4.json"
EVID = ROOT / "governance/MULTIVERSE_FOUNDATION_ACCEPTANCE_EVIDENCE_CANDIDATE_20260820_v1.json"
EXPECTED_MAIN = "819afb723c8f14000757b2e53b6664d71ab01227"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def item(reg: dict, pr: int) -> dict:
    hits = [x for x in reg["open_items"] if x.get("pr") == pr]
    assert len(hits) == 1, (pr, len(hits))
    return hits[0]


def main() -> None:
    life, op, ev = load(LIFE), load(OP), load(EVID)
    assert life["canonical_main_observed"] == EXPECTED_MAIN
    assert op["canonical_main_observed"] == EXPECTED_MAIN
    assert ev["canonical_main_observed"] == EXPECTED_MAIN
    assert life["registry_is_authoritative"] is False

    p14, p15, p16, p22, p23, p24 = [item(life, p) for p in (14, 15, 16, 22, 23, 24)]
    assert "LAB_PASS" in p14["classification"]
    assert {"PAUSED", "QUARANTINED"}.issubset(set(p15["classification"]))
    assert "ACTIVE" in p16["classification"]  # compatibility safety invariant of reviewed Owner Assurance v1
    assert p22["lab_comment_id"] == 5356781881
    assert p22["auditor_comment_id"] == 5357226704
    assert p22["minor_fix_closed_by_pr"] == 23
    assert p23["lab_comment_id"] == 5357391050
    assert {"ACTIVE", "FINAL_ACCEPTANCE_CANDIDATE", "AUDITOR_ACCEPTANCE_REVIEW_PENDING"}.issubset(set(p24["classification"]))
    assert p24["current_head_resolution"] == "FRESH_READ_PR24_REQUIRED"

    assert life["all_foundation_gates_accepted"] is False
    assert life["foundation_acceptance_candidate_pr"] == 24
    assert life["scientific_resume_allowed"] is False
    for value in life["foundation_gate_summary"].values():
        assert "NOT_YET_ACCEPTED" in value

    state = op["operational_state"]
    assert state["active_foundation_remediation_pr"] == 24
    assert state["active_foundation_acceptance_pr"] == 24
    assert state["new_scientific_execution_allowed"] is False
    assert op["foundation_acceptance_candidate_ready"] is True
    assert op["all_foundation_gates_accepted"] is False
    assert op["explicit_scientific_execution_authorization_exists"] is False
    assert op["scientific_resume_allowed"] is False
    assert op["foundation_review_state"]["pr24"]["final_auditor_acceptance_review"] == "NOT_YET_PERFORMED"

    assert ev["status"] == "DRAFT_NONCANONICAL_NOT_ACCEPTED"
    assert ev["candidate_pr"] == 24
    assert ev["candidate_head_resolution"] == "FRESH_READ_PR24_REQUIRED"
    assert ev["unresolved_release_blocking_findings"] == []
    assert ev["final_auditor_required"] is True
    assert ev["atomic_transition_candidate"]["fail_closed_on_main_drift"] is True
    assert ev["atomic_transition_candidate"]["fail_closed_on_pr_head_drift"] is True
    limits = ev["acceptance_effect_limit"]
    for key in (
        "keirin_scientific_execution_authority_created",
        "zero_history_execution_authority_created",
        "scientific_resume_allowed",
        "result_payout_access_authorized",
        "holdout_access_authorized",
        "untouched_validation_opened",
        "model_promotion_allowed",
        "pr15_quarantined_metrics_may_be_inspected",
        "external_provider_contact_authorized",
    ):
        assert limits[key] is False, key

    fw = op["scientific_firewall_preserved"]
    assert fw["ECON_HOLDOUT1000"] == "SEALED"
    assert fw["RESULT_PAYOUT"] == "UNAUTHORIZED"
    assert fw["new_untouched_validation_opened"] is False
    assert fw["model_promotion"] == "PROHIBITED"

    print("MULTIVERSE_FOUNDATION_ACCEPTANCE_CANDIDATE_SELFTEST_PASS")
    print("FOUNDATION_ACCEPTED=false")
    print("FINAL_AUDITOR_REQUIRED=true")
    print("KEIRIN_SCIENTIFIC_RESUME_ALLOWED=false")
    print("PR15_QUARANTINED_METRICS_INSPECTED=false")


if __name__ == "__main__":
    main()
