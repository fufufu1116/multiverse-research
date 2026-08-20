from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOV = HERE.parent / "governance"
ANCHOR = GOV / "KEIRIN_BANK_LENGTH_SCHEDULE_WINDOW_ANCHOR_20260821_0831_v1.json"
SAMPLE = GOV / "KEIRIN_PRE_RACECARD_SAMPLE_PREREG_20260820_v1.json"

EXPECTED_COUNTS = {"333": 4, "335": 1, "400": 20, "500": 2, "total_events": 27}
EXPECTED_SAMPLE_BANKS = {333, 400, 500}
WINDOW_START = date(2026, 8, 21)
WINDOW_END = date(2026, 8, 31)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> dict:
    anchor = _load(ANCHOR)
    sample = _load(SAMPLE)

    if anchor.get("status") != "VERIFIED_SCOPED_REALITY_ANCHOR_CORRECTED":
        raise ValueError("unexpected_anchor_status")
    events = anchor.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("missing_event_inventory")

    identities = [(str(x["venue"]), str(x["start"])) for x in events]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate_event_identity")

    bank_counts: Counter[int] = Counter()
    for row in events:
        d = date.fromisoformat(str(row["start"]))
        if not (WINDOW_START <= d <= WINDOW_END):
            raise ValueError(f"event_outside_window:{row}")
        bank = int(row["bank_m"])
        if bank not in {333, 335, 400, 500}:
            raise ValueError(f"unexpected_bank_length:{bank}")
        bank_counts[bank] += 1

    actual_counts = {
        "333": bank_counts[333],
        "335": bank_counts[335],
        "400": bank_counts[400],
        "500": bank_counts[500],
        "total_events": len(events),
    }
    if actual_counts != EXPECTED_COUNTS:
        raise ValueError(f"anchor_count_mismatch:{actual_counts}")
    if anchor.get("counts") != EXPECTED_COUNTS:
        raise ValueError(f"declared_count_mismatch:{anchor.get('counts')}")

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

    event_index = {(str(x["venue"]), str(x["start"])): int(x["bank_m"]) for x in events}
    sample_events = sample.get("sampling_frame", {}).get("events", [])
    if len(sample_events) != 3:
        raise ValueError("unexpected_sample_event_count")

    sample_banks = set()
    for row in sample_events:
        key = (str(row["venue"]), str(row["start_date"]))
        if key not in event_index:
            raise ValueError(f"sample_event_not_in_anchor:{key}")
        declared_bank = int(row["bank_length_m"])
        if event_index[key] != declared_bank:
            raise ValueError(f"sample_bank_mismatch:{key}")
        if str(row.get("grade")) != "F2":
            raise ValueError(f"sample_not_f2:{key}")
        sample_banks.add(declared_bank)

    if sample_banks != EXPECTED_SAMPLE_BANKS:
        raise ValueError(f"sample_bank_coverage_mismatch:{sorted(sample_banks)}")

    if sample.get("source_policy", {}).get("yahoo") != "SENSOR_ONLY_DISCOVERY_CONTRADICTION_NOT_SAMPLE_TRUTH":
        raise ValueError("yahoo_boundary_drift")
    if sample.get("source_policy", {}).get("result_or_payout") != "PROHIBITED":
        raise ValueError("result_payout_boundary_drift")
    if sample.get("scientific_firewall", {}).get("new_untouched_validation_opened") is not False:
        raise ValueError("untouched_validation_gate_drift")

    return {
        "record": "KEIRIN_BATCH2_PRE_CALIBRATION_VALIDATION_v1",
        "status": "PASS",
        "anchor_event_count": len(events),
        "anchor_bank_counts": actual_counts,
        "sample_event_count": len(sample_events),
        "sample_bank_coverage": sorted(sample_banks),
        "yahoo_role": "SENSOR_ONLY",
        "result_payout_used": False,
        "untouched_real_validation_opened": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2, sort_keys=True))
