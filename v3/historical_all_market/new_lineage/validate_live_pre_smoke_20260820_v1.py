from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "governance" / "KEIRIN_LIVE_PRE_SMOKE_20260820_PREREG_v1.json"

EXPECTED_EVENT = {
    "venue": "玉野",
    "venue_code": "61",
    "start_date": "2026-08-20",
    "grade": "F2",
    "time_band": "NIGHT",
    "title": "おもちゃ王国杯＆マリンホテルＣ",
    "day": 1,
    "official_event_format": {
        "a1_a2": "5R_3DAY_7_RIDERS",
        "challenge": "4R_3DAY_7_RIDERS",
        "girls": "COEXISTS_7_RIDERS",
    },
}
EXPECTED_RACE_SELECTION = {
    "date": "2026-08-20",
    "scheduled_start_cutoff_jst": "16:30",
    "order": "RACE_NUMBER_ASCENDING",
    "take_first_eligible": 3,
    "max_races": 3,
    "eligible": {
        "scheduled_start_at_or_after_cutoff": True,
        "sex_category": "MALE_ONLY",
        "race_regime": "STANDARD_ORIGINAL_LINE_KEIRIN",
        "field_size": 7,
        "official_pre_racecard_available_before_start": True,
        "exclude_l_grade_or_girls": True,
        "exclude_special_or_nonstandard_regime": True,
    },
    "replacement": "NO_REPLACEMENT_OUTSIDE_TARGET_EVENT_OR_DATE",
}
EXPECTED_FIREWALL = {
    "ECON_HOLDOUT1000": "SEALED",
    "DEV2000_C_new_lineage_rescue": "PROHIBITED",
    "same_lineage_B_C_rescue_tuning": "PROHIBITED",
    "PR3_consumed_holdout_reuse": "PROHIBITED",
    "RESULT_PAYOUT_access": "UNAUTHORIZED",
    "new_untouched_validation_opened": False,
}
EXPECTED_LIMITS = {
    "MAX_3_RACES",
    "SAME_DAY_SMOKE_NOT_POPULATION_SAMPLE",
    "NO_CAUSAL_EFFECT",
    "NO_LINE_BREAK_RATE",
    "NO_BANK_COMPARISON",
    "NO_MODEL_EDGE_OR_ROI",
    "NO_MODEL_PROMOTION",
    "NO_RESULT_OR_PAYOUT",
    "NO_UNTOUCHED_VALIDATION_OPEN",
}


def validate() -> dict:
    data = json.loads(PREREG.read_text(encoding="utf-8"))
    if data.get("record") != "KEIRIN_LIVE_PRE_SMOKE_20260820_PREREG_v1":
        raise ValueError("record_identity_drift")
    if data.get("status") != "PREREGISTERED_BEFORE_TARGET_RACECARD_COLLECTION":
        raise ValueError("status_drift")
    if data.get("chronology_authority") != "GIT_COMMIT_ANCESTRY_AND_COMMIT_TIMESTAMP":
        raise ValueError("chronology_authority_drift")
    disclosure = data.get("pre_prereg_disclosure", {})
    if disclosure.get("race_allocations_read") is not False:
        raise ValueError("race_allocations_were_read_pre_prereg")
    if disclosure.get("line_forecast_read") is not False:
        raise ValueError("line_forecast_was_read_pre_prereg")
    if disclosure.get("odds_read") is not False:
        raise ValueError("odds_were_read_pre_prereg")
    if disclosure.get("result_or_payout_read") is not False:
        raise ValueError("result_or_payout_was_read_pre_prereg")
    if disclosure.get("selection_used_participant_strength_or_stats") is not False:
        raise ValueError("selection_depended_on_participant_strength")
    if data.get("target_event") != EXPECTED_EVENT:
        raise ValueError("target_event_drift")
    if data.get("race_selection") != EXPECTED_RACE_SELECTION:
        raise ValueError("race_selection_drift")
    if data.get("line_semantics") != "OFFICIAL_PRE_LINE_FORECAST_IS_FORECAST_NOT_EXECUTED_TRUTH; IF_UNAVAILABLE_DO_NOT_INFER":
        raise ValueError("line_semantics_drift")
    if data.get("planned_use") != "MECHANICAL_AND_SCHEMA_REALITY_SMOKE_ONLY":
        raise ValueError("planned_use_drift")
    if set(data.get("claim_limits", [])) != EXPECTED_LIMITS:
        raise ValueError("claim_limits_drift")
    if data.get("scientific_firewall") != EXPECTED_FIREWALL:
        raise ValueError("scientific_firewall_drift")
    return {
        "record": "KEIRIN_LIVE_PRE_SMOKE_20260820_VALIDATION_v1",
        "status": "PASS",
        "target": "玉野 2026-08-20 F2 NIGHT DAY1",
        "max_races": 3,
        "collection_gate": "PENDING_LAB_REVIEW",
        "result_payout_used": False,
        "untouched_validation_opened": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2, sort_keys=True))
