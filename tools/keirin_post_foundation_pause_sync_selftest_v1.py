#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VNEXT = ROOT / "multiverse_vnext/VNEXT_CURRENT_STATE_v0.json"
SYNC = ROOT / "governance/KEIRIN_POST_FOUNDATION_PAUSE_SYNC_CANDIDATE_20260821_v1.json"
LEGACY = ROOT / "v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json"
NOW = ROOT / "KEIRIN_NOW.md"
EXPECTED_MAIN = "47240792f9f9833b969c0767cac561941a00b710"
EXPECTED_VNEXT_BLOB = "f4295fe416667745688f17ab390246cbb64e0dc8"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    vnext = load(VNEXT)
    sync = load(SYNC)
    legacy = load(LEGACY)
    now = NOW.read_text(encoding="utf-8")

    assert vnext["state_generation"] == 11
    assert vnext["foundation_acceptance"]["status"] == "ACCEPTED_FROZEN"
    assert vnext["foundation_acceptance"]["all_foundation_gates_accepted"] is True
    assert vnext["keirin_firewall"]["scientific_resume_allowed"] is False
    assert vnext["keirin_firewall"]["separate_scientific_execution_authorization_required"] is True
    assert vnext["keirin_firewall"]["ECON_HOLDOUT1000"] == "SEALED"
    assert vnext["keirin_firewall"]["result_payout_access_authorized"] is False
    assert vnext["keirin_firewall"]["pr15_quarantined_metrics_may_be_inspected_for_resume_selection"] is False

    assert sync["status"] == "DRAFT_NONCANONICAL_TRUTH_SYNC_CANDIDATE"
    assert sync["canonical_main_observed"] == EXPECTED_MAIN
    assert sync["foundation_current_state"]["git_blob_sha"] == EXPECTED_VNEXT_BLOB
    assert sync["foundation_current_state"]["state_generation"] == 11
    ctl = sync["effective_scientific_control"]
    assert ctl["keirin_science"] == "PAUSED"
    assert ctl["scientific_execution_allowed"] is False
    assert ctl["scientific_resume_allowed"] is False
    assert ctl["separate_scientific_execution_authorization_required"] is True
    assert ctl["foundation_acceptance_is_not_scientific_authorization"] is True
    assert ctl["zero_history_is_orientation_only"] is True

    assert sync["latest_legitimate_completed_scientific_checkpoint"]["pr"] == 14
    assert sync["latest_legitimate_completed_scientific_checkpoint"]["exact_lab_reviewed_scientific_head"] == "e70bda39a5d3ce585af4e028b35106b859871bd9"
    assert sync["latest_legitimate_completed_scientific_checkpoint"]["real_world_edge_or_roi_evidence"] is False
    assert sync["quarantine"]["pr15"] == "QUARANTINED_NOT_ADMITTED"
    assert sync["quarantine"]["metrics_may_be_opened_for_resume_selection"] is False

    p = sync["protected_boundaries"]
    assert p["ECON_HOLDOUT1000"] == "SEALED"
    assert p["RESULT_PAYOUT"] == "UNAUTHORIZED"
    assert p["DEV2000_C_new_lineage_rescue"] == "PROHIBITED"
    assert p["same_lineage_B_C_rescue_tuning"] == "PROHIBITED"
    assert p["untouched_validation_opened"] is False
    assert p["model_promotion"] == "PROHIBITED"
    assert p["external_provider_contact_authorized"] is False
    assert p["real_money_wagering"] == "OUT_OF_SCOPE"
    assert p["synthetic_evidence_is_real_world_edge_evidence"] is False

    # The point of this candidate is to neutralize stale pre-pause display truth,
    # not to pretend those older files were already updated.
    assert legacy["updated_jst"] == "2026-08-20T00:29:00+09:00"
    assert legacy["status"].startswith("ACTIVE_RESEARCH_")
    assert "最終更新: 2026-08-20 00:29 JST" in now

    scope = sync["candidate_scope"]
    assert scope["may_resume_science"] is False
    assert scope["may_select_resume_path_from_quarantined_or_protected_results"] is False
    assert scope["may_change_research_goal_or_direction"] is False
    assert scope["may_open_protected_data"] is False

    print("KEIRIN_POST_FOUNDATION_PAUSE_SYNC_SELFTEST_PASS")
    print("FOUNDATION_ACCEPTED=true")
    print("KEIRIN_SCIENCE_PAUSED=true")
    print("SCIENTIFIC_RESUME_ALLOWED=false")
    print("PR15_QUARANTINED_METRICS_INSPECTED=false")
    print("RESULT_PAYOUT_ACCESSED=false")
    print("HOLDOUT_ACCESSED=false")


if __name__ == "__main__":
    main()
