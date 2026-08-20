#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json"
TRANSFORMER = ROOT / "tools/keirin_fixed_path_pause_rewrite_dry_run_v1.py"

spec = importlib.util.spec_from_file_location("rewrite", TRANSFORMER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def main() -> None:
    original = json.loads(LEGACY.read_text(encoding="utf-8"))
    rewritten = mod.build_rewrite(original)

    assert original["status"].startswith("ACTIVE_RESEARCH_")
    assert rewritten["status"] == mod.NEW_STATUS
    assert rewritten["updated_jst"] == mod.NEW_UPDATED_JST
    assert rewritten["next_gate"] == mod.NEW_NEXT_GATE

    ctl = rewritten["effective_scientific_execution_control"]
    assert ctl["state_generation_context"] == 11
    assert ctl["keirin_science"] == "PAUSED"
    assert ctl["scientific_execution_allowed"] is False
    assert ctl["scientific_resume_allowed"] is False
    assert ctl["separate_scientific_execution_authorization_required"] is True
    assert ctl["foundation_acceptance_is_not_scientific_authorization"] is True
    assert ctl["zero_history_orientation_is_not_scientific_authorization"] is True
    assert ctl["latest_legitimate_completed_scientific_checkpoint"]["pr"] == 14
    assert ctl["latest_legitimate_completed_scientific_checkpoint"]["exact_lab_reviewed_scientific_head"] == "e70bda39a5d3ce585af4e028b35106b859871bd9"
    assert ctl["latest_legitimate_completed_scientific_checkpoint"]["real_world_edge_or_roi_evidence"] is False
    assert ctl["pr15"]["status"] == "QUARANTINED_NOT_ADMITTED"
    assert ctl["pr15"]["metrics_may_be_inspected_for_resume_selection"] is False

    assert rewritten["pre_pause_next_gate_historical"] == original["next_gate"]
    assert rewritten["pre_pause_next_exact_actions_historical"] == original["next_exact_actions"]

    allowed_changed_original_keys = {"updated_jst", "status", "next_gate", "next_exact_actions"}
    for key, value in original.items():
        if key not in allowed_changed_original_keys:
            assert rewritten[key] == value, f"unexpected historical mutation: {key}"

    # Explicitly pin the most sensitive inherited scientific/protection state.
    assert rewritten["scientific_state"] == original["scientific_state"]
    assert rewritten["scientific_state"]["ECON_HOLDOUT1000"] == "SEALED"
    assert rewritten["scientific_state"]["same_lineage_B_C_rescue_tuning"] == "PROHIBITED"
    assert rewritten["scientific_state"]["current_DEV2000_C_scored_for_new_lineage"] is False
    assert rewritten["parent_diagnostic_state"] == original["parent_diagnostic_state"]
    assert rewritten["architecture_lessons"] == original["architecture_lessons"]
    assert rewritten["stage0_design_artifacts"] == original["stage0_design_artifacts"]
    assert rewritten["source_rights_state"] == original["source_rights_state"]
    assert rewritten["source_independent_implementation"] == original["source_independent_implementation"]
    assert rewritten["digital_twin_state"] == original["digital_twin_state"]
    assert rewritten["probability_object_contract"] == original["probability_object_contract"]
    assert rewritten["validation_candidate"] == original["validation_candidate"]
    assert rewritten["data_recovery_state"] == original["data_recovery_state"]
    assert rewritten["hard_prohibitions"] == original["hard_prohibitions"]

    # The new current action list itself must be governance-only and fail closed.
    joined = "\n".join(rewritten["next_exact_actions"])
    assert "PAUSED" in joined
    assert "PR #15 QUARANTINED_NOT_ADMITTED" in joined
    assert "ECON_HOLDOUT1000 SEALED" in joined
    assert "RESULT/PAYOUT UNAUTHORIZED" in joined
    assert "Do not open untouched validation" in joined
    assert "Await independent Lab determination" in joined

    print("KEIRIN_FIXED_PATH_PAUSE_REWRITE_DRY_RUN_SELFTEST_PASS")
    print("HISTORICAL_ARCHITECTURE_PRESERVED=true")
    print("OLD_NEXT_ACTIONS_PRESERVED_AS_HISTORICAL=true")
    print("ACTUAL_FIXED_PATH_MODIFIED=false")
    print("SCIENTIFIC_EXECUTION_PERFORMED=false")
    print("SCIENTIFIC_RESUME_ALLOWED=false")
    print("RESULT_PAYOUT_ACCESSED=false")
    print("HOLDOUT_ACCESSED=false")
    print("PR15_QUARANTINED_METRICS_INSPECTED=false")


if __name__ == "__main__":
    main()
