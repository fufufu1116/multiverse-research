from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOV = HERE.parent / "governance"
ANCHOR = GOV / "KEIRIN_BANK_LENGTH_SCHEDULE_WINDOW_ANCHOR_20260821_0831_v1.json"
SAMPLE = GOV / "KEIRIN_PRE_RACECARD_SAMPLE_PREREG_20260820_v1.json"
BATCH = GOV / "KEIRIN_REALITY_CALIBRATION_BATCH2_PREREG_v1.json"
YAHOO = GOV / "KEIRIN_BATCH2_YAHOO_SENSOR_LOG_20260820_v1.json"

EXPECTED_COUNTS = {"333": 4, "335": 1, "400": 20, "500": 2, "total_events": 27}
TARGET_BANKS = (333, 400, 500)
WINDOW_START = date(2026, 8, 21)
WINDOW_END = date(2026, 8, 31)

EXPECTED_SAMPLE_FIREWALL = {
    "ECON_HOLDOUT1000": "SEALED",
    "DEV2000_C_new_lineage_rescue": "PROHIBITED",
    "same_lineage_B_C_rescue_tuning": "PROHIBITED",
    "scientific_segment_c_scoring_count": 0,
    "new_untouched_validation_opened": False,
    "RESULT_PAYOUT_access": "UNAUTHORIZED",
}
EXPECTED_BATCH_FIREWALL = dict(EXPECTED_SAMPLE_FIREWALL)
EXPECTED_YAHOO_FIREWALL = {
    "RESULT_PAYOUT_access": "UNAUTHORIZED",
    "new_untouched_validation_opened": False,
    "bulk_scraping_or_bypass": "PROHIBITED",
}
EXPECTED_ANCHOR_FIREWALL = {
    "RESULT_PAYOUT_used": False,
    "untouched_real_validation_opened": False,
    "ECON_HOLDOUT1000": "SEALED",
}

# Exact official-schedule F2 candidate inventory for the locked window. Time-band icons
# do not exclude an F2 event. Race-level male/original-line/7-rider eligibility is
# applied only after event selection.
EXPECTED_F2_CANDIDATES = (
    ("大垣", "2026-08-21", "F2", 400),
    ("松山", "2026-08-21", "F2", 400),
    ("武雄", "2026-08-21", "F2", 400),
    ("立川", "2026-08-22", "F2", 400),
    ("和歌山", "2026-08-23", "F2", 400),
    ("青森", "2026-08-24", "F2", 400),
    ("宇都宮", "2026-08-24", "F2", 500),
    ("熊本", "2026-08-24", "F2", 400),
    ("松阪", "2026-08-25", "F2", 400),
    ("高知", "2026-08-25", "F2", 500),
    ("伊東", "2026-08-27", "F2", 333),
    ("岸和田", "2026-08-27", "F2", 400),
    ("小松島", "2026-08-27", "F2", 400),
    ("四日市", "2026-08-29", "F2", 400),
    ("いわき平", "2026-08-30", "F2", 400),
    ("静岡", "2026-08-30", "F2", 400),
    ("岐阜", "2026-08-30", "F2", 400),
    ("和歌山", "2026-08-30", "F2", 400),
)
EXPECTED_TARGET_TITLES = {
    ("大垣", "2026-08-21"): "Ｋドリームス杯サテライト姫路賞",
    ("宇都宮", "2026-08-24"): "オッズパーク杯",
    ("伊東", "2026-08-27"): "前検コメはウィンチケット杯",
}
EXPECTED_EVENT_ELIGIBILITY = {
    "official_schedule_grade": "F2",
    "time_band_policy": "INCLUDE_ALL_OFFICIAL_F2_SCHEDULE_ENTRIES_REGARDLESS_OF_DAY_NIGHT_MORNING_MIDNIGHT_OR_OTHER_TIME_BAND_ICON",
    "girls_mixed_event_policy": "DO_NOT_EXCLUDE_EVENT_ONLY_BECAUSE_GIRLS_RACES_MAY_BE_PRESENT; APPLY_MALE_FILTER_AT_RACE_SELECTION_STAGE",
    "special_event_policy": "EVENT_SELECTION_USES_GRADE_AND_BANK_ONLY; RACE_SELECTION_LATER_EXCLUDES_NONSTANDARD_OR_NON_ORIGINAL_LINE_RACES",
    "racecard_content_used_for_event_selection": False,
    "result_or_payout_used_for_event_selection": False,
}
EXPECTED_SELECTION_ALGORITHM = {
    "target_bank_lengths_m": [333, 400, 500],
    "group_candidates_by": "bank_length_m",
    "sort_key": ["start_date_ascending", "venue_unicode_codepoint_ascending"],
    "select": "FIRST_CANDIDATE_PER_TARGET_BANK_AFTER_SORT",
    "tie_break_is_racecard_independent": True,
    "bank_335_policy": "NO_F2_CANDIDATE_IN_WINDOW_SO_UNMEASURED_IN_THIS_SMALL_SAMPLE",
}
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
EXPECTED_REPLACEMENT_RULE = (
    "If fewer than three eligible races exist in an event, use all eligible races from "
    "that event and do not replace them with races from another event or another date."
)
EXPECTED_CLAIM_LIMITS = {
    "MAX_9_PREREGISTERED_RACES_ONLY",
    "SAMPLE_ONLY_NOT_POPULATION_FREQUENCY",
    "NO_BANK_SPECIFIC_POPULATION_FREQUENCY_FROM_THIS_SAMPLE",
    "PRE_LINE_FORECAST_IS_NOT_EXECUTED_LINE_TRUTH",
    "NO_LINE_BREAK_RATE",
    "NO_CAUSAL_EFFECT_SIZE",
    "NO_MODEL_PROMOTION",
    "NO_REAL_EDGE_OR_ROI_CLAIM",
    "BANK_335_UNMEASURED_IN_THIS_SMALL_SAMPLE",
}
EXPECTED_YAHOO_NOT_PROMOTED = {
    "BANK_WIND_EFFECT_SIZE",
    "LINE_EFFECT_SIZE",
    "LINE_BREAK_RATE",
    "HEAVY_TAIL_SHOCK",
    "MARKET_STRENGTH_BIAS",
    "global bank-specific upset frequency",
    "global line-resolution frequency",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_tuple(row: dict) -> tuple[str, str, str, int]:
    return (
        str(row["venue"]),
        str(row["start_date"]),
        str(row["grade"]),
        int(row["bank_length_m"]),
    )


def _select_targets(candidates: tuple[tuple[str, str, str, int], ...]) -> list[tuple[str, str, str, int]]:
    selected = []
    for bank in TARGET_BANKS:
        rows = [row for row in candidates if row[3] == bank]
        if not rows:
            raise ValueError(f"missing_f2_candidate_for_target_bank:{bank}")
        # ISO dates and Python strings make this exactly the preregistered
        # start_date ascending, then venue Unicode code-point ascending rule.
        selected.append(sorted(rows, key=lambda x: (x[1], x[0]))[0])
    return selected


def validate() -> dict:
    anchor = _load(ANCHOR)
    sample = _load(SAMPLE)
    batch = _load(BATCH)
    yahoo = _load(YAHOO)

    # Exact artifact identities / statuses.
    if anchor.get("record") != "KEIRIN_BANK_LENGTH_SCHEDULE_WINDOW_ANCHOR_20260821_0831_v1":
        raise ValueError("anchor_record_identity_drift")
    if anchor.get("status") != "VERIFIED_SCOPED_REALITY_ANCHOR_CORRECTED":
        raise ValueError("unexpected_anchor_status")
    if sample.get("record") != "KEIRIN_PRE_RACECARD_SAMPLE_PREREG_20260820_v1":
        raise ValueError("sample_record_identity_drift")
    if sample.get("status") != "PREREGISTERED_BEFORE_TARGET_RACECARD_COLLECTION_AMENDED_PRE_COLLECTION_AFTER_LAB_BLOCK":
        raise ValueError("unexpected_sample_status")
    if sample.get("parent_batch") != "KEIRIN_REALITY_CALIBRATION_BATCH2_PREREG_v1":
        raise ValueError("sample_parent_identity_drift")
    if batch.get("record") != "KEIRIN_REALITY_CALIBRATION_BATCH2_PREREG_v1" or batch.get("status") != "PREREGISTERED_PUBLIC_PRE_ONLY_CALIBRATION_BATCH":
        raise ValueError("batch_identity_or_status_drift")
    if yahoo.get("record") != "KEIRIN_BATCH2_YAHOO_SENSOR_LOG_20260820_v1" or yahoo.get("status") != "SENSOR_ONLY_NO_NUMERIC_TRUTH_PROMOTION":
        raise ValueError("yahoo_identity_or_status_drift")

    # Schedule anchor consistency.
    events = anchor.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("missing_event_inventory")
    identities = [(str(x["venue"]), str(x["start"])) for x in events]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate_event_identity")

    bank_counts: Counter[int] = Counter()
    event_index: dict[tuple[str, str], int] = {}
    for row in events:
        d = date.fromisoformat(str(row["start"]))
        if not (WINDOW_START <= d <= WINDOW_END):
            raise ValueError(f"event_outside_window:{row}")
        bank = int(row["bank_m"])
        if bank not in {333, 335, 400, 500}:
            raise ValueError(f"unexpected_bank_length:{bank}")
        key = (str(row["venue"]), str(row["start"]))
        event_index[key] = bank
        bank_counts[bank] += 1

    actual_counts = {
        "333": bank_counts[333],
        "335": bank_counts[335],
        "400": bank_counts[400],
        "500": bank_counts[500],
        "total_events": len(events),
    }
    if actual_counts != EXPECTED_COUNTS or anchor.get("counts") != EXPECTED_COUNTS:
        raise ValueError(f"anchor_count_mismatch:{actual_counts}:{anchor.get('counts')}")

    props = anchor.get("event_level_proportions", {})
    expected_props = {
        "333": 4 / 27,
        "335": 1 / 27,
        "400": 20 / 27,
        "500": 2 / 27,
        "short_333_or_335": 5 / 27,
    }
    for key, expected in expected_props.items():
        actual = float(props.get(key, -1.0))
        if abs(actual - expected) > 1e-12:
            raise ValueError(f"proportion_mismatch:{key}:{actual}:{expected}")
    if anchor.get("scientific_firewall") != EXPECTED_ANCHOR_FIREWALL:
        raise ValueError("anchor_scientific_firewall_drift")

    # Event selection must be independently reproducible from the frozen candidate inventory.
    frame = sample.get("sampling_frame", {})
    if frame.get("window") != "2026-08-21_through_2026-08-31":
        raise ValueError("sample_window_drift")
    if frame.get("event_eligibility_rule") != EXPECTED_EVENT_ELIGIBILITY:
        raise ValueError("event_eligibility_rule_drift")
    if frame.get("selection_algorithm") != EXPECTED_SELECTION_ALGORITHM:
        raise ValueError("selection_algorithm_drift")

    candidate_rows = frame.get("official_f2_candidate_inventory")
    if not isinstance(candidate_rows, list):
        raise ValueError("missing_official_f2_candidate_inventory")
    observed_candidates = tuple(_candidate_tuple(row) for row in candidate_rows)
    if observed_candidates != EXPECTED_F2_CANDIDATES:
        raise ValueError(f"f2_candidate_inventory_drift:{observed_candidates}")
    for venue, start, grade, bank in observed_candidates:
        if grade != "F2":
            raise ValueError(f"candidate_not_f2:{venue}:{start}")
        if event_index.get((venue, start)) != bank:
            raise ValueError(f"candidate_not_in_anchor_or_bank_mismatch:{venue}:{start}:{bank}")

    expected_selected = _select_targets(EXPECTED_F2_CANDIDATES)
    sample_events = frame.get("events", [])
    if len(sample_events) != 3:
        raise ValueError("unexpected_sample_event_count")
    actual_selected = [_candidate_tuple(row) for row in sample_events]
    if actual_selected != expected_selected:
        raise ValueError(f"sample_selection_mismatch:{actual_selected}:{expected_selected}")
    for row in sample_events:
        key = (str(row["venue"]), str(row["start_date"]))
        if row.get("official_schedule_title") != EXPECTED_TARGET_TITLES.get(key):
            raise ValueError(f"target_title_identity_drift:{key}")

    # Race-level collection gate is exact and must not drift after target racecards are visible.
    if frame.get("race_selection") != EXPECTED_RACE_SELECTION:
        raise ValueError("race_selection_rule_drift")
    if frame.get("replacement_rule") != EXPECTED_REPLACEMENT_RULE:
        raise ValueError("replacement_rule_drift")
    if frame.get("population_claim") is not False:
        raise ValueError("population_claim_drift")

    # PRE semantics.
    fields = sample.get("admissible_fields", {})
    if fields.get("CLASS") != {
        "status": "VERIFIED_OFFICIAL_PRE_FIELD",
        "use": "WITHIN_BAND_CLASS_SAMPLE_ANCHOR",
    }:
        raise ValueError("class_semantic_drift")
    if fields.get("STYLE") != {
        "status": "VERIFIED_OFFICIAL_PRE_FIELD",
        "values": ["逃", "両", "追"],
        "use": "STYLE_SAMPLE_AND_STYLE_BY_PRE_LINE_POSITION_IF_LINE_FORECAST_AVAILABLE",
    }:
        raise ValueError("style_semantic_drift")
    line = fields.get("PRE_LINE_FORECAST", {})
    if line.get("status") != "OFFICIAL_SERVICE_PRE_INFORMATION_CANDIDATE":
        raise ValueError("pre_line_forecast_status_drift")
    if line.get("semantic_guard") != "Treat as pre-race lineup forecast/prediction, not as verified executed line truth.":
        raise ValueError("pre_line_forecast_semantic_guard_drift")
    if line.get("derived_target_name") != "PRE_LINE_FORECAST_SHAPE_FREQUENCY":
        raise ValueError("pre_line_forecast_target_name_drift")
    if line.get("if_unavailable") != "Do not infer line membership from prefecture, style, score, commentary, or later results. Leave line-derived targets unmeasured.":
        raise ValueError("pre_line_forecast_unavailable_rule_drift")

    # Yahoo is a sensor only; verify the log itself, not just a pointer string.
    if sample.get("source_policy", {}).get("yahoo") != "SENSOR_ONLY_DISCOVERY_CONTRADICTION_NOT_SAMPLE_TRUTH":
        raise ValueError("sample_yahoo_boundary_drift")
    if batch.get("source_policy", {}).get("yahoo_role") != "SENSOR_ONLY_DISCOVERY_CONTRADICTION_NOT_NUMERIC_TRUTH":
        raise ValueError("batch_yahoo_boundary_drift")
    observations = yahoo.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ValueError("missing_yahoo_observations")
    for i, observation in enumerate(observations):
        if observation.get("classification") != "SENSOR_ONLY" or observation.get("numeric_use") != "PROHIBITED":
            raise ValueError(f"yahoo_observation_boundary_drift:{i}")
    if set(yahoo.get("not_promoted_from_yahoo", [])) != EXPECTED_YAHOO_NOT_PROMOTED:
        raise ValueError("yahoo_not_promoted_set_drift")
    if yahoo.get("scientific_firewall") != EXPECTED_YAHOO_FIREWALL:
        raise ValueError("yahoo_scientific_firewall_drift")

    # Parent batch + sample firewalls and claim limits are exact.
    if batch.get("scientific_firewall") != EXPECTED_BATCH_FIREWALL:
        raise ValueError("batch_scientific_firewall_drift")
    if batch.get("promotion_rule") != "NO_MODEL_PROMOTION_FROM_BATCH2_CALIBRATION_ALONE":
        raise ValueError("batch_promotion_rule_drift")
    if batch.get("untouched_real_validation_may_open") is not False:
        raise ValueError("batch_untouched_validation_gate_drift")
    if sample.get("scientific_firewall") != EXPECTED_SAMPLE_FIREWALL:
        raise ValueError("sample_scientific_firewall_drift")
    if set(sample.get("claim_limits", [])) != EXPECTED_CLAIM_LIMITS:
        raise ValueError("sample_claim_limits_drift")

    return {
        "record": "KEIRIN_BATCH2_PRE_CALIBRATION_VALIDATION_v2",
        "status": "PASS",
        "anchor_event_count": len(events),
        "anchor_bank_counts": actual_counts,
        "official_f2_candidate_count": len(observed_candidates),
        "selected_targets": [
            {"venue": x[0], "start_date": x[1], "grade": x[2], "bank_length_m": x[3]}
            for x in actual_selected
        ],
        "event_selection_algorithm_verified": True,
        "race_selection_rule_verified": True,
        "pre_line_forecast_semantics_verified": True,
        "yahoo_sensor_log_verified": True,
        "all_scientific_firewalls_verified": True,
        "target_racecard_collection_gate": "PENDING_LAB_MICRO_RECHECK",
        "result_payout_used": False,
        "untouched_real_validation_opened": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2, sort_keys=True))
