#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

BASE_MAIN = "7993d8d90d0154913e6335bf5219477cf1f8fd38"
REVIEWED_HEAD = "5ddca980391c0a3692454cdad540825c155852e7"
LAB_COMMENT = 5363706178
AUDITOR_COMMENT = 5363766595
ALLOWED = [
    "source-independent synthetic regression checks only",
    "Digital Twin W0-W4 synthetic stress and failure diagnostics only",
    "C0/C1/N1 comparison only inside those synthetic worlds",
]


def load(path):
    return json.loads(Path(path).read_text())


def load_base(path):
    raw = subprocess.check_output(["git", "show", f"{BASE_MAIN}:{path}"], text=True)
    return json.loads(raw)


owner = load("governance/KEIRIN_OWNER_GATE_LIMITED_SYNTHETIC_EXECUTION_20260821_v1.json")
receipt = load("governance/KEIRIN_LIMITED_SYNTHETIC_EXECUTION_AUTHORIZATION_RECEIPT_20260821_v1.json")
keirin = load("v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json")
vnext = load("multiverse_vnext/VNEXT_CURRENT_STATE_v0.json")
owner_view = Path("KEIRIN_NOW.md").read_text()

assert owner["status"] == "OWNER_APPROVED_SCOPE_SPECIFIC"
assert owner["review_binding"]["exact_reviewed_head"] == REVIEWED_HEAD
assert owner["review_binding"]["lab_pass_comment_id"] == LAB_COMMENT
assert owner["review_binding"]["auditor_pass_comment_id"] == AUDITOR_COMMENT
assert owner["scope"]["allowed"] == ALLOWED
assert owner["fail_closed_conditions"]["approval_reusable_for_other_operations"] is False

assert receipt["preconditions"]["reviewed_exact_head"] == REVIEWED_HEAD
assert receipt["preconditions"]["lab_pass_comment_id"] == LAB_COMMENT
assert receipt["preconditions"]["auditor_pass_comment_id"] == AUDITOR_COMMENT
assert receipt["authorization_scope"]["allowed"] == ALLOWED
assert receipt["authorization_scope"]["scientific_segment_c_scoring_count_must_remain"] == 0
assert "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY" in receipt["evidence_class_limit"]

base_keirin = load_base("v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json")
allowed_keirin_changes = {"updated_jst", "status", "next_gate", "next_exact_actions"}
for key in base_keirin:
    if key not in allowed_keirin_changes:
        assert keirin[key] == base_keirin[key], f"unexpected CURRENT_STATE_KEIRIN change: {key}"
assert keirin["status"] == "LIMITED_SYNTHETIC_SCIENTIFIC_EXECUTION_AUTHORIZED_POST_LAB_AUDITOR_OWNER_GATE"
assert keirin["scientific_state"]["scientific_segment_c_scoring_count"] == 0
assert keirin["scientific_state"]["ECON_HOLDOUT1000"] == "SEALED"
assert keirin["scientific_state"]["new_untouched_validation_opened"] is False
assert keirin["scientific_state"]["current_DEV2000_C_scored_for_new_lineage"] is False
assert keirin["scientific_state"]["same_lineage_B_C_rescue_tuning"] == "PROHIBITED"
assert "NO_RESULT_PAYOUT_ACCESS_FOR_FEATURE_SELECTION_OR_MEMBERSHIP_RECOVERY" in keirin["hard_prohibitions"]
assert "NO_EXTERNAL_PROVIDER_CONTACT" in keirin["hard_prohibitions"]
assert "NO_REAL_MONEY_WAGERING" in keirin["hard_prohibitions"]
assert "NO_SYNTHETIC_AS_REAL_EDGE_EVIDENCE" in keirin["hard_prohibitions"]

base_vnext = load_base("multiverse_vnext/VNEXT_CURRENT_STATE_v0.json")
allowed_vnext_changes = {
    "updated_jst", "current_phase", "state_generation", "parent_valid_state_git_blob_sha",
    "supersedes_state_ref", "write_precondition", "keirin_firewall", "next_actions"
}
for key in base_vnext:
    if key not in allowed_vnext_changes:
        assert vnext[key] == base_vnext[key], f"unexpected VNEXT_CURRENT_STATE change: {key}"
assert vnext["state_generation"] == 12
assert vnext["parent_valid_state_git_blob_sha"] == "f4295fe416667745688f17ab390246cbb64e0dc8"
assert vnext["supersedes_state_ref"]["logical_generation"] == 11
assert vnext["write_precondition"]["expected_canonical_main_head"] == BASE_MAIN
assert vnext["write_precondition"]["expected_audited_pr_head"] == REVIEWED_HEAD

base_fw = base_vnext["keirin_firewall"]
fw = vnext["keirin_firewall"]
for key in base_fw:
    if key not in {"scientific_resume_allowed", "separate_scientific_execution_authorization_required"}:
        assert fw[key] == base_fw[key], f"unexpected firewall change: {key}"
assert fw["scientific_resume_allowed"] is True
assert fw["separate_scientific_execution_authorization_required"] is False
assert fw["ECON_HOLDOUT1000"] == "SEALED"
assert fw["result_payout_access_authorized"] is False
assert fw["pr15_quarantined_metrics_may_be_inspected_for_resume_selection"] is False
assert fw["external_provider_contact_authorized"] is False
assert fw["synthetic_evidence_is_real_world_edge_evidence"] is False

assert "Synthetic（合成）限定で再開許可済み" in owner_view
assert "scientific segment C scoring count は **0のまま**" in owner_view

print("KEIRIN_LIMITED_SYNTHETIC_AUTHORIZATION_SELFTEST_PASS")
print("OWNER_GATE_SCOPE_SPECIFIC=true")
print("LAB_EXACT_HEAD_PASS_BOUND=true")
print("AUDITOR_EXACT_HEAD_PASS_BOUND=true")
print("VNEXT_GENERATION=12")
print("SYNTHETIC_ONLY_SCOPE=true")
print("SCIENTIFIC_SEGMENT_C_SCORING_COUNT=0")
print("PR15_QUARANTINE_PRESERVED=true")
print("RESULT_PAYOUT_AUTHORIZED=false")
print("ECON_HOLDOUT1000=SEALED")
print("REAL_LIVE_INPUT_COLLECTION_AUTHORIZED=false")
print("EXTERNAL_PROVIDER_CONTACT_AUTHORIZED=false")
print("REAL_MONEY_WAGERING_AUTHORIZED=false")
print("SYNTHETIC_IS_REAL_WORLD_EDGE_EVIDENCE=false")
