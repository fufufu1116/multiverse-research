from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "governance" / "KEIRIN_LIVE_PRE_DISTRIBUTOR_FALLBACK_PREREG_20260820_v1.json"

EXPECTED_CANDIDATES = [4, 7, 8, 9, 10, 11]
EXPECTED_SOURCES = [
    "RAKUTEN_KDREAMS_PUBLIC_PRE",
    "WINTICKET_PUBLIC_PRE",
    "NETKEIRIN_PUBLIC_PRE",
]
EXPECTED_TIER = "PUBLIC_PRE_DISTRIBUTOR_ENGINEERING_ONLY_NOT_PRIMARY_CALIBRATION"
EXPECTED_LIMITS = {
    "NOT_OFFICIAL_PRIMARY_CALIBRATION",
    "NOT_POPULATION_SAMPLE",
    "NO_CAUSAL_EFFECT",
    "NO_BANK_COMPARISON",
    "NO_REAL_LINE_FREQUENCY_OR_STRENGTH_CLAIM",
    "NO_MODEL_EDGE_OR_ROI",
    "NO_MODEL_PROMOTION",
    "NO_RESULT_OR_PAYOUT",
    "NO_UNTOUCHED_VALIDATION_OPEN",
}


def validate() -> dict:
    data = json.loads(PREREG.read_text(encoding="utf-8"))
    if data.get("record") != "KEIRIN_LIVE_PRE_DISTRIBUTOR_FALLBACK_PREREG_20260820_v1":
        raise ValueError("record_identity_drift")
    if data.get("status") != "PREREGISTERED_BEFORE_DISTRIBUTOR_RACECARD_COLLECTION":
        raise ValueError("status_drift")
    if data.get("chronology_authority") != "GIT_COMMIT_ANCESTRY_AND_COMMIT_TIMESTAMP":
        raise ValueError("chronology_authority_drift")
    if data.get("activation_condition") != "DIRECT_OFFICIAL_RACE_LEVEL_PRE_NOT_SAFELY_RETRIEVABLE_BEFORE_TARGET_RACE_CAPTURE":
        raise ValueError("activation_condition_drift")
    if data.get("evidence_tier") != EXPECTED_TIER:
        raise ValueError("evidence_tier_drift")
    if data.get("candidate_race_order") != EXPECTED_CANDIDATES:
        raise ValueError("candidate_order_drift")
    if data.get("source_priority") != EXPECTED_SOURCES:
        raise ValueError("source_priority_drift")
    rule = data.get("selection_rule", {})
    expected_rule = {
        "iterate_candidate_race_order": True,
        "capture_only_while_race_is_strictly_pre_start_or_pre_sales_deadline": True,
        "require_7_riders": True,
        "require_male": True,
        "require_standard_original_line_keirin": True,
        "take_first_successfully_pre_captured": 3,
        "max_races": 3,
        "missed_or_inaccessible_race": "RECORD_AND_CONTINUE_ASCENDING_LIST",
        "replacement_outside_event_or_date": False,
    }
    if rule != expected_rule:
        raise ValueError("selection_rule_drift")
    prohibited = set(data.get("prohibited_fields_or_paths", []))
    required_prohibited = {"RESULT", "PAYOUT", "FINAL_ODDS", "POST_RACE_LINE_RECONSTRUCTION", "HINDSIGHT_SELECTION"}
    if prohibited != required_prohibited:
        raise ValueError("prohibited_path_drift")
    if set(data.get("claim_limits", [])) != EXPECTED_LIMITS:
        raise ValueError("claim_limits_drift")
    fw = data.get("scientific_firewall", {})
    if fw.get("ECON_HOLDOUT1000") != "SEALED":
        raise ValueError("econ_holdout_unsealed")
    if fw.get("RESULT_PAYOUT_access") != "UNAUTHORIZED":
        raise ValueError("result_payout_gate_drift")
    if fw.get("new_untouched_validation_opened") is not False:
        raise ValueError("untouched_validation_opened")
    if fw.get("model_promotion") is not False:
        raise ValueError("model_promotion_opened")
    if fw.get("new_spend") is not False:
        raise ValueError("new_spend_opened")
    return {
        "record": "KEIRIN_LIVE_PRE_DISTRIBUTOR_FALLBACK_VALIDATION_20260820_v1",
        "status": "PASS",
        "collection_gate": "PENDING_INDEPENDENT_LAB_REVIEW",
        "evidence_tier": EXPECTED_TIER,
        "max_races": 3,
        "result_payout_used": False,
        "untouched_validation_opened": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2, sort_keys=True))
