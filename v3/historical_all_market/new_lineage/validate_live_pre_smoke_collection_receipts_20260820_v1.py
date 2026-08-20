from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOV = ROOT / "governance"

RACE2_FILE = GOV / "KEIRIN_LIVE_PRE_SMOKE_20260820_CAPTURE_ATTEMPT_02_v1.json"
TERMINAL = {
    3: ("KEIRIN_LIVE_PRE_SMOKE_20260820_CAPTURE_ATTEMPT_03_v1.json", "RACE_3_UNMEASURED_PRIMARY_PRE_NOT_ESTABLISHED_PROSPECTIVELY"),
    4: ("KEIRIN_LIVE_PRE_SMOKE_20260820_CAPTURE_ATTEMPT_05_v1.json", "RACE_4_UNMEASURED_PRIMARY_PRE_NOT_ESTABLISHED_PROSPECTIVELY"),
    5: ("KEIRIN_LIVE_PRE_SMOKE_20260820_CAPTURE_ATTEMPT_07_v1.json", "RACE_5_UNMEASURED_PRIMARY_PRE_NOT_ESTABLISHED_PROSPECTIVELY"),
    6: ("KEIRIN_LIVE_PRE_SMOKE_20260820_CAPTURE_ATTEMPT_09_v1.json", "RACE_6_UNMEASURED_PRIMARY_PRE_AND_ELIGIBILITY_NOT_ESTABLISHED_PROSPECTIVELY"),
    7: ("KEIRIN_LIVE_PRE_SMOKE_20260820_CAPTURE_ATTEMPT_10_v1.json", "RACE_7_UNMEASURED_PRIMARY_PRE_AND_ELIGIBILITY_NOT_ESTABLISHED_PROSPECTIVELY"),
    8: ("KEIRIN_LIVE_PRE_SMOKE_20260820_CAPTURE_ATTEMPT_11_v1.json", "RACE_8_UNMEASURED_PRIMARY_PRE_AND_ELIGIBILITY_NOT_ESTABLISHED_PROSPECTIVELY"),
    9: ("KEIRIN_LIVE_PRE_SMOKE_20260820_CAPTURE_ATTEMPT_12_v1.json", "RACE_9_UNMEASURED_PRIMARY_PRE_AND_ELIGIBILITY_NOT_ESTABLISHED_PROSPECTIVELY"),
    10: ("KEIRIN_LIVE_PRE_SMOKE_20260820_CAPTURE_ATTEMPT_13_v1.json", "RACE_10_UNMEASURED_PRIMARY_PRE_AND_ELIGIBILITY_NOT_ESTABLISHED_PROSPECTIVELY"),
    11: ("KEIRIN_LIVE_PRE_SMOKE_20260820_CAPTURE_ATTEMPT_14_v1.json", "RACE_11_UNMEASURED_PRIMARY_PRE_AND_ELIGIBILITY_NOT_ESTABLISHED_PROSPECTIVELY"),
}
DISPOSITION = GOV / "KEIRIN_LIVE_PRE_SMOKE_20260820_COLLECTION_DISPOSITION_v1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_firewall(fw: dict, label: str) -> None:
    if not str(fw.get("RESULT_PAYOUT_access", "")).startswith("UNAUTHORIZED"):
        raise ValueError(f"{label}:result_payout_boundary")
    if fw.get("odds_used") is not False:
        raise ValueError(f"{label}:odds_used")
    if fw.get("post_race_line_truth_used") is not False:
        raise ValueError(f"{label}:post_race_line_truth_used")
    if fw.get("ECON_HOLDOUT1000") != "SEALED":
        raise ValueError(f"{label}:econ_holdout_unsealed")
    if fw.get("untouched_validation_opened") is not False:
        raise ValueError(f"{label}:untouched_opened")
    if fw.get("model_promotion") is not False:
        raise ValueError(f"{label}:model_promotion")


def validate() -> dict:
    race2 = load(RACE2_FILE)
    prior2 = race2.get("prior_candidate_race_2", {})
    if race2.get("candidate_race") != 3:
        raise ValueError("race2_handoff_not_to_race3")
    if prior2.get("admission_state") != "NOT_ADMITTED_PRIMARY_RACE_LEVEL_PRE_WAS_NOT_ESTABLISHED_DURING_PROSPECTIVE_CAPTURE":
        raise ValueError("race2_terminal_disposition_drift")
    if prior2.get("result_or_payout_checked") is not False:
        raise ValueError("race2_result_or_payout_checked")
    check_firewall(race2.get("firewall", {}), "race2_handoff")

    times = [datetime.fromisoformat(race2["captured_at_jst"])]
    for race in range(3, 12):
        filename, expected_status = TERMINAL[race]
        data = load(GOV / filename)
        if data.get("candidate_race") != race:
            raise ValueError(f"race{race}:candidate_drift")
        if data.get("status") != expected_status:
            raise ValueError(f"race{race}:terminal_status_drift")
        if not str(data.get("scientific_disposition", "")).startswith("UNMEASURED"):
            raise ValueError(f"race{race}:scientific_disposition_drift")
        expected_next = race + 1 if race < 11 else None
        if data.get("next_candidate") != expected_next:
            raise ValueError(f"race{race}:next_candidate_drift")
        check_firewall(data.get("firewall", {}), f"race{race}")
        times.append(datetime.fromisoformat(data["captured_at_jst"]))

    if any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError("terminal_receipt_timestamps_not_strictly_increasing")

    disposition = load(DISPOSITION)
    if disposition.get("status") != "COLLECTION_CLOSED_ZERO_ADMITTED_SAMPLE_CURRENT_SAFE_PRIMARY_PRE_PATHS_UNAVAILABLE":
        raise ValueError("collection_disposition_status_drift")
    if disposition.get("race_numbers_traversed_in_order") != list(range(2, 12)):
        raise ValueError("race_traversal_order_drift")
    if disposition.get("admitted_races") != [] or disposition.get("admitted_sample_count") != 0:
        raise ValueError("nonzero_admitted_sample")
    if disposition.get("scientific_interpretation") != "ACCESS_MEASUREMENT_OUTCOME_ONLY_NOT_A_NEGATIVE_MODEL_OR_POPULATION_RESULT":
        raise ValueError("scientific_interpretation_drift")
    if disposition.get("live_pre_collection_may_continue_for_this_preregistered_target_day") is not False:
        raise ValueError("collection_not_closed")
    if disposition.get("untouched_validation_may_open") is not False:
        raise ValueError("untouched_gate_opened")
    check_firewall(disposition.get("firewall", {}), "disposition")
    if datetime.fromisoformat(disposition["captured_at_jst"]) <= times[-1]:
        raise ValueError("disposition_not_after_terminal_receipts")

    return {
        "record": "KEIRIN_LIVE_PRE_SMOKE_20260820_COLLECTION_RECEIPT_VALIDATION_v1",
        "status": "PASS",
        "terminal_races_checked": list(range(2, 12)),
        "admitted_sample_count": 0,
        "result_payout_used": False,
        "odds_used": False,
        "untouched_validation_opened": False,
        "model_promotion": False,
        "next_gate": "LAB_REVIEW_COLLECTION_EVIDENCE_ONLY",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2, sort_keys=True))
