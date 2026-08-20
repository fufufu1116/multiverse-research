#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "governance/KEIRIN_CANONICAL_PAUSE_STATE_REWRITE_PLAN_CANDIDATE_20260821_v1.json"
VNEXT = ROOT / "multiverse_vnext/VNEXT_CURRENT_STATE_v0.json"
LEGACY = ROOT / "v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json"

EXPECTED_MAIN = "47240792f9f9833b969c0767cac561941a00b710"
EXPECTED_VNEXT_BLOB = "f4295fe416667745688f17ab390246cbb64e0dc8"
EXPECTED_LEGACY_BLOB = "248616ba6e8e671d044793ff82bbec2a04804611"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    plan = load(PLAN)
    vnext = load(VNEXT)
    legacy = load(LEGACY)

    assert plan["status"] == "DRAFT_NONCANONICAL_REWRITE_PLAN_ONLY"
    assert plan["canonical_main_observed"] == EXPECTED_MAIN
    assert plan["target"]["expected_current_blob_sha"] == EXPECTED_LEGACY_BLOB
    assert plan["target"]["must_fail_closed_on_blob_or_main_drift"] is True
    assert plan["authoritative_precedence_source"]["expected_blob_sha"] == EXPECTED_VNEXT_BLOB
    assert plan["authoritative_precedence_source"]["state_generation"] == 11

    assert vnext["state_generation"] == 11
    assert vnext["foundation_acceptance"]["status"] == "ACCEPTED_FROZEN"
    assert vnext["keirin_firewall"]["scientific_resume_allowed"] is False
    assert vnext["keirin_firewall"]["separate_scientific_execution_authorization_required"] is True

    assert legacy["updated_jst"] == plan["target"]["expected_legacy_updated_jst"]
    assert legacy["status"].startswith(plan["target"]["expected_legacy_status_prefix"])

    rewrite = plan["proposed_rewrite_semantics"]
    assert rewrite["status"].startswith("PAUSED_")
    assert rewrite["scientific_execution_allowed"] is False
    assert rewrite["scientific_resume_allowed"] is False
    assert rewrite["foundation_acceptance_is_not_scientific_authorization"] is True
    assert rewrite["zero_history_orientation_is_not_scientific_authorization"] is True
    assert rewrite["preserve_historical_scientific_architecture_and_diagnostics"] is True
    assert rewrite["preserve_latest_legitimate_completed_scientific_checkpoint"] is True
    assert rewrite["do_not_import_quarantined_or_protected_results"] is True

    checkpoint = plan["latest_legitimate_completed_scientific_checkpoint"]
    assert checkpoint["pr"] == 14
    assert checkpoint["exact_lab_reviewed_scientific_head"] == "e70bda39a5d3ce585af4e028b35106b859871bd9"
    assert checkpoint["real_world_edge_or_roi_evidence"] is False

    q = plan["quarantine"]
    assert q["pr15"] == "QUARANTINED_NOT_ADMITTED"
    assert q["metrics_may_be_opened_for_resume_selection"] is False

    p = plan["protected_boundaries"]
    assert p["ECON_HOLDOUT1000"] == "SEALED"
    assert p["RESULT_PAYOUT"] == "UNAUTHORIZED"
    assert p["DEV2000_C_new_lineage_rescue"] == "PROHIBITED"
    assert p["same_lineage_B_C_rescue_tuning"] == "PROHIBITED"
    assert p["untouched_validation_opened"] is False
    assert p["model_promotion"] == "PROHIBITED"
    assert p["external_provider_contact_authorized"] is False
    assert p["real_money_wagering"] == "OUT_OF_SCOPE"
    assert p["synthetic_evidence_is_real_world_edge_evidence"] is False

    c = plan["preservation_contract"]
    assert c["may_delete_legacy_architecture_history"] is False
    assert c["may_change_research_goal_or_direction"] is False
    assert c["may_promote_model_or_lineage"] is False
    assert c["may_open_protected_data"] is False
    assert c["may_resume_science"] is False
    assert c["actual_target_file_modified_by_this_plan"] is False

    dep = plan["dependency"]
    assert dep["pr26"] == 26
    assert dep["pr26_frozen_head"] == "9a06997638bac405b4035cdbb23d833acdc5b86a"
    assert dep["lab_verdict_required_before_any_canonical_rewrite"] is True

    print("KEIRIN_CANONICAL_PAUSE_REWRITE_PLAN_SELFTEST_PASS")
    print("ACTUAL_LEGACY_CURRENT_STATE_MODIFIED=false")
    print("SCIENTIFIC_EXECUTION_PERFORMED=false")
    print("SCIENTIFIC_RESUME_ALLOWED=false")
    print("RESULT_PAYOUT_ACCESSED=false")
    print("HOLDOUT_ACCESSED=false")
    print("PR15_QUARANTINED_METRICS_INSPECTED=false")


if __name__ == "__main__":
    main()
