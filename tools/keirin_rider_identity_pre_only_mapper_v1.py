#!/usr/bin/env python3
"""Research-only PRE-only rider identity mapper.

Maps PRE race-card rider names to official KEIRIN.JP registration numbers
without RESULT, payout, odds, human forecasts, or post-race reconstruction.

For prospective rider-affinity eligibility, a race passes only when every rider
is an exact unique name match and the official profile capture corroborates the
same pre-event race date / venue / race number. Historical mapping remains
separate and MUST NOT backfill current profile attributes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

MAPPING_VERSION = "KEIRIN_RIDER_IDENTITY_PRE_ONLY_MAPPER_v1"
FORBIDDEN_INPUT_FIELDS = {
    "result", "results", "finish", "finish_1", "finish_2", "finish_3",
    "payout", "payouts", "odds", "forecast", "prediction", "tips",
    "human_mark", "human_marks", "narabiyoso", "settlement",
}
REQUIRED_PRE_FIELDS = {
    "race_id", "race_date", "venue", "race_no", "car_no",
    "rider_name_raw", "source_url", "source_file_sha256",
}


def normalize_name(value: str) -> str:
    s = unicodedata.normalize("NFKC", str(value))
    s = re.sub(r"[\s\u3000]+", " ", s).strip()
    return s


def normalize_venue(value: str) -> str:
    return normalize_name(value)


def _validate_no_forbidden_fields(fieldnames: list[str] | None) -> None:
    fields = {str(x).strip().lower() for x in (fieldnames or [])}
    bad = sorted(fields & FORBIDDEN_INPUT_FIELDS)
    if bad:
        raise ValueError("FAIL-CLOSED:forbidden_pre_fields=" + ",".join(bad))


def _validate_profile_record(rec: dict[str, Any]) -> dict[str, Any]:
    reg = str(rec.get("registration_number", "")).strip()
    if not re.fullmatch(r"\d{6}", reg):
        raise ValueError(f"FAIL-CLOSED:invalid_registration_number={reg!r}")
    url = str(rec.get("official_profile_url", "")).strip()
    try:
        qs = parse_qs(urlparse(url).query)
        snum = qs.get("snum", [""])[0]
    except Exception:
        snum = ""
    if snum != reg:
        raise ValueError(f"FAIL-CLOSED:profile_url_registration_mismatch={reg}")
    name = normalize_name(rec.get("official_profile_name", ""))
    if not name:
        raise ValueError(f"FAIL-CLOSED:missing_official_profile_name={reg}")
    out = dict(rec)
    out["registration_number"] = reg
    out["official_profile_name_normalized"] = name
    ev = rec.get("current_event")
    if ev is not None:
        if not isinstance(ev, dict):
            raise ValueError(f"FAIL-CLOSED:invalid_current_event={reg}")
        date = str(ev.get("race_date", "")).strip()
        venue = normalize_venue(ev.get("venue", ""))
        try:
            race_no = int(ev.get("race_no"))
        except Exception as exc:
            raise ValueError(f"FAIL-CLOSED:invalid_event_race_no={reg}") from exc
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", date) or not venue or race_no < 1:
            raise ValueError(f"FAIL-CLOSED:invalid_current_event={reg}")
        out["current_event"] = {"race_date": date, "venue": venue, "race_no": race_no}
    return out


def load_catalog(path: Path) -> list[dict[str, Any]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("result_accessed") is not False:
        raise ValueError("FAIL-CLOSED:catalog_result_access_flag_must_be_false")
    if obj.get("evidence_role") not in {"PROSPECTIVE_PRE_ONLY_IDENTITY", "PRE_ONLY_IDENTITY"}:
        raise ValueError("FAIL-CLOSED:catalog_evidence_role")
    records = obj.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("FAIL-CLOSED:empty_identity_catalog")
    return [_validate_profile_record(x) for x in records]


def map_rows(pre_rows: list[dict[str, str]], catalog: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_name: dict[str, list[dict[str, Any]]] = {}
    for rec in catalog:
        by_name.setdefault(rec["official_profile_name_normalized"], []).append(rec)

    mappings: list[dict[str, Any]] = []
    for row in pre_rows:
        raw = row["rider_name_raw"]
        norm = normalize_name(raw)
        cands = by_name.get(norm, [])
        base = {
            "mapping_version": MAPPING_VERSION,
            "race_id": str(row["race_id"]),
            "race_date": str(row["race_date"]),
            "venue": str(row["venue"]),
            "race_no": int(row["race_no"]),
            "car_no": int(row["car_no"]),
            "historical_pre_source_url": str(row["source_url"]),
            "historical_pre_source_hash_if_available": str(row["source_file_sha256"]),
            "rider_name_raw": raw,
            "rider_name_normalized": norm,
        }
        if len(cands) == 0:
            mappings.append({**base, "mapping_status": "FAIL_CLOSED_NO_MATCH", "event_corroborated": False})
            continue
        if len(cands) > 1:
            mappings.append({**base, "mapping_status": "FAIL_CLOSED_MULTIPLE_MATCH", "event_corroborated": False})
            continue

        rec = cands[0]
        ev = rec.get("current_event")
        event_corroborated = False
        status = "EXACT_SINGLE_MATCH_PROFILE_ONLY"
        if ev is not None:
            event_corroborated = (
                ev["race_date"] == str(row["race_date"])
                and normalize_venue(ev["venue"]) == normalize_venue(row["venue"])
                and int(ev["race_no"]) == int(row["race_no"])
            )
            if not event_corroborated:
                mappings.append({
                    **base,
                    "official_registration_number": rec["registration_number"],
                    "official_profile_url": rec["official_profile_url"],
                    "official_profile_name": rec["official_profile_name"],
                    "mapping_status": "FAIL_CLOSED_EVENT_CONTRADICTION",
                    "event_corroborated": False,
                })
                continue
            status = "EXACT_SINGLE_MATCH_EVENT_CORROBORATED"

        mappings.append({
            **base,
            "official_registration_number": rec["registration_number"],
            "official_profile_url": rec["official_profile_url"],
            "official_profile_name": rec["official_profile_name"],
            "mapping_status": status,
            "event_corroborated": event_corroborated,
        })

    race_groups: dict[str, list[dict[str, Any]]] = {}
    for m in mappings:
        race_groups.setdefault(m["race_id"], []).append(m)
    race_summaries = []
    for race_id, xs in sorted(race_groups.items()):
        all_unique = all(x["mapping_status"].startswith("EXACT_SINGLE_MATCH") for x in xs)
        all_event = all(x.get("mapping_status") == "EXACT_SINGLE_MATCH_EVENT_CORROBORATED" for x in xs)
        race_summaries.append({
            "race_id": race_id,
            "riders": len(xs),
            "all_riders_exact_unique": all_unique,
            "all_riders_event_corroborated": all_event,
            "prospective_rider_affinity_identity_gate_pass": bool(all_unique and all_event),
        })
    return mappings, race_summaries


def mapping_hash(mappings: list[dict[str, Any]]) -> str:
    payload = json.dumps(mappings, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pre_csv")
    ap.add_argument("official_identity_catalog_json")
    ap.add_argument("mapping_json")
    ap.add_argument("receipt_json")
    args = ap.parse_args()

    with open(args.pre_csv, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        _validate_no_forbidden_fields(reader.fieldnames)
        missing = sorted(REQUIRED_PRE_FIELDS - set(reader.fieldnames or []))
        if missing:
            raise ValueError("FAIL-CLOSED:missing_pre_fields=" + ",".join(missing))
        pre_rows = list(reader)
    if not pre_rows:
        raise ValueError("FAIL-CLOSED:empty_pre_rows")

    catalog = load_catalog(Path(args.official_identity_catalog_json))
    mappings, race_summaries = map_rows(pre_rows, catalog)
    mh = mapping_hash(mappings)

    out = {
        "record": "KEIRIN_RIDER_IDENTITY_PRE_ONLY_MAPPING_TABLE_v1",
        "mapping_version": MAPPING_VERSION,
        "result_accessed": False,
        "current_profile_attributes_backfilled": False,
        "mapping_sha256": mh,
        "mappings": mappings,
        "race_summaries": race_summaries,
    }
    Path(args.mapping_json).write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    statuses: dict[str, int] = {}
    for x in mappings:
        statuses[x["mapping_status"]] = statuses.get(x["mapping_status"], 0) + 1
    receipt = {
        "record": "KEIRIN_RIDER_IDENTITY_PRE_ONLY_MAPPING_RECEIPT_v1",
        "mapping_version": MAPPING_VERSION,
        "rows_attempted": len(mappings),
        "races_attempted": len(race_summaries),
        "races_all_riders_mapped": sum(x["all_riders_exact_unique"] for x in race_summaries),
        "races_event_corroborated": sum(x["all_riders_event_corroborated"] for x in race_summaries),
        "races_fail_closed_identity": sum(not x["prospective_rider_affinity_identity_gate_pass"] for x in race_summaries),
        "status_counts": statuses,
        "mapping_sha256": mh,
        "result_accessed": False,
        "payout_accessed": False,
        "odds_accessed": False,
        "human_forecast_accessed": False,
        "current_profile_attributes_backfilled": False,
    }
    Path(args.receipt_json).write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
