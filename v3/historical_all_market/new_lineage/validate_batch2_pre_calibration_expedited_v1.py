from __future__ import annotations

import json
from pathlib import Path

import validate_batch2_pre_calibration_v1 as baseline

HERE = Path(__file__).resolve().parent
GOV = HERE.parent / "governance"
AMENDMENT = GOV / "KEIRIN_PRE_RACECARD_SAMPLE_EXPEDITED_AMENDMENT_20260820_v1.json"
SAMPLE = GOV / "KEIRIN_PRE_RACECARD_SAMPLE_PREREG_20260820_v1.json"

EXPECTED_EVENTS = [
    {
        "venue": "大垣",
        "start_date": "2026-08-21",
        "grade": "F2",
        "bank_length_m": 400,
        "official_schedule_title": "Ｋドリームス杯サテライト姫路賞",
    },
    {
        "venue": "松山",
        "start_date": "2026-08-21",
        "grade": "F2",
        "bank_length_m": 400,
        "official_schedule_title": "前検日コメならウィンチケット杯",
    },
    {
        "venue": "武雄",
        "start_date": "2026-08-21",
        "grade": "F2",
        "bank_length_m": 400,
        "official_schedule_title": "オッズパーク杯",
    },
]

EXPECTED_RACE_SELECTION = {
    "day": "FIRST_DAY_ONLY",
    "order": "RACE_NUMBER_ASCENDING",
    "take_first_eligible_per_event": 3,
    "target_races_max": 9,
    "replacement_across_event_or_date": False,
    "eligible_race": {
        "sex_category": "MALE_ONLY",
        "race_regime": "STANDARD_ORIGINAL_LINE_KEIRIN",
        "field_size": 7,
        "official_pre_racecard_available_before_race": True,
        "exclude_l_grade_or_girls": True,
        "exclude_special_9_or_other_exceptional_format": True,
    },
}

EXPECTED_FIREWALL = {
    "ECON_HOLDOUT1000": "SEALED",
    "DEV2000_C_new_lineage_rescue": "PROHIBITED",
    "same_lineage_B_C_rescue_tuning": "PROHIBITED",
    "scientific_segment_c_scoring_count": 0,
    "new_untouched_validation_opened": False,
    "RESULT_PAYOUT_access": "UNAUTHORIZED",
}

EXPECTED_CLAIM_LIMITS = {
    "MAX_9_PREREGISTERED_RACES_ONLY",
    "ALL_EXPEDITED_SAMPLE_EVENTS_ARE_400M",
    "SAMPLE_ONLY_NOT_POPULATION_FREQUENCY",
    "NO_BANK_COMPARISON_FROM_EXPEDITED_SAMPLE",
    "NO_BANK_SPECIFIC_POPULATION_FREQUENCY",
    "PRE_LINE_FORECAST_IS_NOT_EXECUTED_LINE_TRUTH",
    "NO_LINE_BREAK_RATE",
    "NO_CAUSAL_EFFECT_SIZE",
    "NO_MODEL_PROMOTION",
    "NO_REAL_EDGE_OR_ROI_CLAIM",
    "333_335_500_RACECARD_SAMPLE_UNMEASURED_IN_EXPEDITED_BATCH",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> dict:
    baseline_result = baseline.validate()
    if baseline_result.get("status") != "PASS":
        raise ValueError("baseline_validator_not_pass")

    sample = _load(SAMPLE)
    amendment = _load(AMENDMENT)

    if amendment.get("record") != "KEIRIN_PRE_RACECARD_SAMPLE_EXPEDITED_AMENDMENT_20260820_v1":
        raise ValueError("amendment_record_identity_drift")
    if amendment.get("status") != "PREREGISTERED_EXPEDITED_AMENDMENT_BEFORE_ANY_TARGET_RACECARD_COLLECTION":
        raise ValueError("amendment_status_drift")
    if amendment.get("parent_sample_prereg") != sample.get("record"):
        raise ValueError("amendment_parent_drift")
    if amendment.get("parent_sample_prereg_preserved") is not True:
        raise ValueError("parent_preservation_not_asserted")
    if amendment.get("admissible_fields_and_semantics") != "UNCHANGED_FROM_PARENT_SAMPLE_PREREG":
        raise ValueError("admissible_semantics_drift")
    if amendment.get("gate") != "LAB_REVIEW_REQUIRED_BEFORE_EXPEDITED_COLLECTION":
        raise ValueError("lab_gate_drift")

    plan = amendment.get("active_collection_plan", {})
    algorithm = plan.get("selection_algorithm", {})
    if algorithm != {
        "find_earliest_start_date_in_frozen_inventory": True,
        "earliest_start_date": "2026-08-21",
        "select_all_F2_events_on_earliest_start_date": True,
        "event_order": "venue_unicode_codepoint_ascending",
        "racecard_content_used_for_event_selection": False,
        "result_or_payout_used_for_event_selection": False,
    }:
        raise ValueError("expedited_selection_algorithm_drift")

    frozen_inventory = sample.get("sampling_frame", {}).get("official_f2_candidate_inventory", [])
    if not frozen_inventory:
        raise ValueError("missing_frozen_inventory")
    earliest = min(str(row["start_date"]) for row in frozen_inventory)
    if earliest != "2026-08-21":
        raise ValueError(f"unexpected_earliest_date:{earliest}")

    expected_identity = [(x["venue"], x["start_date"], x["grade"], x["bank_length_m"]) for x in EXPECTED_EVENTS]
    derived = sorted(
        [
            (str(row["venue"]), str(row["start_date"]), str(row["grade"]), int(row["bank_length_m"]))
            for row in frozen_inventory
            if str(row["start_date"]) == earliest
        ],
        key=lambda x: x[0],
    )
    if derived != expected_identity:
        raise ValueError(f"earliest_date_event_derivation_mismatch:{derived}:{expected_identity}")

    if plan.get("events") != EXPECTED_EVENTS:
        raise ValueError("expedited_target_event_drift")
    if plan.get("race_selection") != EXPECTED_RACE_SELECTION:
        raise ValueError("expedited_race_selection_drift")
    if plan.get("replacement_rule") != (
        "If fewer than three eligible races exist in an event, use all eligible races from that event and do not replace them from another event or date."
    ):
        raise ValueError("expedited_replacement_rule_drift")

    if any(int(row["bank_length_m"]) != 400 for row in plan.get("events", [])):
        raise ValueError("expedited_sample_not_all_400m")
    if set(amendment.get("claim_limits", [])) != EXPECTED_CLAIM_LIMITS:
        raise ValueError("expedited_claim_limits_drift")
    if amendment.get("scientific_firewall") != EXPECTED_FIREWALL:
        raise ValueError("expedited_scientific_firewall_drift")
    if amendment.get("scientific_tradeoff", {}).get("bank_comparison_allowed") is not False:
        raise ValueError("bank_comparison_boundary_drift")

    return {
        "record": "KEIRIN_BATCH2_PRE_EXPEDITED_AMENDMENT_VALIDATION_v1",
        "status": "PASS",
        "baseline_parent_validator_pass": True,
        "active_target_date": "2026-08-21",
        "active_target_events": [x["venue"] for x in EXPECTED_EVENTS],
        "active_target_bank_length_m": 400,
        "target_races_max": 9,
        "bank_comparison_allowed": False,
        "target_racecard_collection_gate": "PENDING_LAB_REVIEW_OF_EXPEDITED_AMENDMENT",
        "result_payout_used": False,
        "untouched_real_validation_opened": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2, sort_keys=True))
