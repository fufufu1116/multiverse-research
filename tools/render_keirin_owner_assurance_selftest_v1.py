#!/usr/bin/env python3
"""Selftest for Owner assurance renderer candidate."""
from __future__ import annotations
import copy
from render_keirin_owner_assurance_v1 import AssuranceError, render

STATE = {
    "status": "DRAFT_NONCANONICAL_STATE_SYNC_CANDIDATE",
    "operational_state": {
        "keirin_research": "PAUSED_FOR_MULTIVERSE_ZERO_BASE_FOUNDATION_AUDIT",
        "new_scientific_execution_allowed": False,
        "owner_action_now": "NONE",
    },
    "latest_legitimate_completed_scientific_checkpoint": {
        "pr": 14,
        "title": "Broad assumption-range topology stress v1",
        "lab": "PASS",
        "auditor": "NOT_RUN_NO_FINAL_VERDICT_LOCATED",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "scenario_race_evaluations": 388800,
    },
    "paused_child_work": {
        "pr": 15,
        "title": "Continuous assumption-surface boundary map v1",
        "automatic_scientific_execution": "DISABLED_MANUAL_ONLY_PAUSE_STUB",
        "post_pause_already_armed_run": 32363915537,
        "post_pause_run_disposition": "QUARANTINED_NOT_ADMITTED",
    },
    "scientific_firewall_preserved": {
        "ECON_HOLDOUT1000": "SEALED",
        "RESULT_PAYOUT": "UNAUTHORIZED",
        "new_untouched_validation_opened": False,
        "model_promotion": "PROHIBITED",
        "real_money_wagering": "OUT_OF_SCOPE",
    },
    "foundation_resume_gate": ["G1", "G2", "G3", "G4", "G5"],
}

LIFECYCLE = {
    "status": "DRAFT_NONCANONICAL_AUDIT_EVIDENCE",
    "registry_is_authoritative": False,
    "open_items": [
        {"pr": 14}, {"pr": 15}, {"pr": 16}
    ],
}

def must_fail(state, lifecycle, label):
    try:
        render(state, lifecycle)
    except AssuranceError:
        return
    raise AssertionError(label)

def main() -> None:
    text = render(STATE, LIFECYCLE)
    assert "PAUSED_FOR_MULTIVERSE_ZERO_BASE_FOUNDATION_AUDIT" in text
    assert "PR #14" in text
    assert "Lab: `PASS`" in text
    assert "Auditor: `NOT_RUN_NO_FINAL_VERDICT_LOCATED`" in text
    assert "388800" in text
    assert "PR #15" in text
    assert "QUARANTINED_NOT_ADMITTED" in text
    assert "ECON_HOLDOUT1000: `SEALED`" in text
    assert "RESULT/PAYOUT: `UNAUTHORIZED`" in text
    assert "**NONE**" in text
    assert "表示専用" in text

    bad = copy.deepcopy(STATE)
    bad["operational_state"]["new_scientific_execution_allowed"] = True
    must_fail(bad, LIFECYCLE, "science-open state must fail")

    bad_life = copy.deepcopy(LIFECYCLE)
    bad_life["registry_is_authoritative"] = True
    must_fail(STATE, bad_life, "second canonical authority must fail")

    missing = copy.deepcopy(LIFECYCLE)
    missing["open_items"] = [{"pr": 14}, {"pr": 15}]
    must_fail(STATE, missing, "missing PR16 must fail")

    duplicate = copy.deepcopy(LIFECYCLE)
    duplicate["open_items"] = [{"pr": 14}, {"pr": 15}, {"pr": 16}, {"pr": 16}]
    must_fail(STATE, duplicate, "duplicate lifecycle PR must fail")

    bad_quarantine = copy.deepcopy(STATE)
    bad_quarantine["paused_child_work"]["post_pause_run_disposition"] = "ADMITTED"
    must_fail(bad_quarantine, LIFECYCLE, "quarantine mismatch must fail")

    print("MULTIVERSE_OWNER_ASSURANCE_RENDERER_SELFTEST_PASS")

if __name__ == "__main__":
    main()
