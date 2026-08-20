from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
GOV = HERE.parent / "governance"
PREREG = GOV / "KEIRIN_INDEPENDENT_OFFICIAL_PRE_REALISM_SENSOR_PREREG_20260820_v1.json"
CAPTURE_GLOB = "KEIRIN_INDEPENDENT_OFFICIAL_PRE_REALISM_SENSOR_CAPTURE_*_20260820_v1.json"
CENTRAL_OFFICIAL_RACE_HOSTS = {"keirin.jp", "www.keirin.jp"}


def _dt(value: str) -> datetime:
    out = datetime.fromisoformat(value)
    if out.tzinfo is None:
        raise ValueError(f"timezone_required:{value}")
    return out


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _official_race_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and parsed.hostname in CENTRAL_OFFICIAL_RACE_HOSTS


def validate(prereg_path: Path = PREREG, capture_paths: Iterable[Path] | None = None) -> dict:
    prereg = _load(prereg_path)
    if prereg.get("record") != "KEIRIN_INDEPENDENT_OFFICIAL_PRE_REALISM_SENSOR_PREREG_20260820_v1":
        raise ValueError("prereg_identity_drift")
    if prereg.get("status") != "PREREGISTERED_BEFORE_OFFICIAL_PRIMARY_PRE_DISCOVERY_AND_EXTRACTION":
        raise ValueError("prereg_status_drift")

    start = _dt(prereg["window_jst"]["start"])
    end = _dt(prereg["window_jst"]["end"])
    max_races = int(prereg["selection"]["max_races"])
    max_venues = int(prereg["selection"]["max_venues"])
    if prereg["independence_rule"]["source_family"] != "FIRST_PARTY_OFFICIAL_ONLY":
        raise ValueError("source_family_drift")
    if prereg["independence_rule"]["result_or_payout_access"] != "PROHIBITED":
        raise ValueError("result_payout_boundary_drift")
    if prereg["independence_rule"]["third_party_completion"] != "PROHIBITED":
        raise ValueError("third_party_completion_boundary_drift")

    paths = sorted(capture_paths if capture_paths is not None else GOV.glob(CAPTURE_GLOB))
    admitted_total = 0
    venues: set[str] = set()
    seen_keys: set[tuple[str, str, int]] = set()
    checked = 0

    for path in paths:
        row = _load(path)
        checked += 1
        captured = _dt(row["captured_at_jst"])
        admitted = int(row.get("admitted_race_count", 0))
        if admitted < 0:
            raise ValueError(f"negative_admitted_count:{path.name}")

        # Discovery/preflight before the scientific window is permitted only at zero admission.
        if captured < start and admitted != 0:
            raise ValueError(f"pre_window_admission_prohibited:{path.name}")
        if captured > end and admitted != 0:
            raise ValueError(f"post_window_admission_prohibited:{path.name}")

        policy = row.get("policy_observed", {})
        if policy:
            if policy.get("first_party_only") is not True:
                raise ValueError(f"non_first_party_capture:{path.name}")
            if policy.get("bypass") is not False:
                raise ValueError(f"bypass_not_false:{path.name}")
            if policy.get("third_party_completion") is not False:
                raise ValueError(f"third_party_completion_not_false:{path.name}")
            if policy.get("result_or_payout_access") is not False:
                raise ValueError(f"result_or_payout_access_not_false:{path.name}")
            if policy.get("post_race_backfill") is not False:
                raise ValueError(f"post_race_backfill_not_false:{path.name}")
            if policy.get("external_contact") is not False:
                raise ValueError(f"external_contact_not_false:{path.name}")

        races = row.get("admitted_races", [])
        if len(races) != admitted:
            if admitted != 0 or races:
                raise ValueError(f"admitted_count_payload_mismatch:{path.name}")
        for race in races:
            required = ("race_date", "venue", "race_number", "scheduled_start", "field_size", "source_url")
            missing = [key for key in required if key not in race]
            if missing:
                raise ValueError(f"missing_required_fields:{path.name}:{missing}")
            if int(race["field_size"]) != 7:
                raise ValueError(f"non7_field_admitted:{path.name}")
            scheduled = _dt(race["scheduled_start"])
            if not (start <= captured <= end):
                raise ValueError(f"admitted_capture_outside_window:{path.name}")
            if not captured < scheduled:
                raise ValueError(f"not_prospective:{path.name}:{race['venue']}:{race['race_number']}")
            # Scientific race-level admission is intentionally narrower than discovery:
            # only central first-party KEIRIN.JP race pages may supply admitted fields in v1.
            if not _official_race_url(str(race["source_url"])):
                raise ValueError(f"race_source_not_central_official:{path.name}")
            if race.get("source_class") != "FIRST_PARTY_OFFICIAL":
                raise ValueError(f"source_class_not_official:{path.name}")
            key = (str(race["race_date"]), str(race["venue"]), int(race["race_number"]))
            if key in seen_keys:
                raise ValueError(f"duplicate_admitted_race:{key}")
            seen_keys.add(key)
            venues.add(str(race["venue"]))
            admitted_total += 1

    if admitted_total > max_races:
        raise ValueError(f"max_races_exceeded:{admitted_total}>{max_races}")
    if len(venues) > max_venues:
        raise ValueError(f"max_venues_exceeded:{len(venues)}>{max_venues}")

    return {
        "record": "KEIRIN_INDEPENDENT_OFFICIAL_PRE_SENSOR_VALIDATION_v1",
        "status": "PASS",
        "capture_files_checked": checked,
        "admitted_races": admitted_total,
        "admitted_venues": len(venues),
        "central_official_admission_hosts": sorted(CENTRAL_OFFICIAL_RACE_HOSTS),
        "pre_window_zero_admission_preflight_allowed": True,
        "scientific_firewall": {
            "RESULT_PAYOUT_access": "UNAUTHORIZED",
            "third_party_completion": "PROHIBITED",
            "post_race_backfill": "PROHIBITED",
            "external_provider_contact": "PROHIBITED",
        },
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2, sort_keys=True))
