#!/usr/bin/env python3
"""Normalize and cross-check prospective final Day1 Keirin racecard observations.

Research-lane audit hardening only:
- Does not scrape RESULT/PAYOUT/ODDS/PREDICTION/comment pages.
- Does not make >=2-source consensus a new formal-support blocker.
- Single trusted final-racecard source can be SINGLE_SOURCE_READY if complete.
- Any material disagreement among trusted sources fails closed.
"""

from __future__ import annotations
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import re
import unicodedata
from typing import Any

TRUSTED_SOURCES = {"ctc", "kdreams", "winticket", "keirin_jp"}
FORBIDDEN_PAGE_KINDS = {
    "result", "results", "payout", "odds", "prediction", "comment", "comments",
    "結果", "払戻", "オッズ", "予想", "コメント",
}
ALLOWED_PAGE_KINDS = {"final_day1_racecard", "official_day1_racecard", "day1_racecard"}
MATERIAL_FIELDS = (
    "official_registration_number", "rider_name", "race_date", "venue",
    "day", "circumference_m", "race_no", "car_no", "class", "style",
)

class ConsensusError(ValueError):
    pass

def _nfkc(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip()

def normalize_name(value: Any) -> str:
    return re.sub(r"\s+", "", _nfkc(value))

def normalize_venue(value: Any) -> str:
    s = _nfkc(value)
    s = re.sub(r"(競輪場|競輪)$", "", s)
    return s.strip()

def normalize_class(value: Any) -> str:
    s = _nfkc(value).upper().replace(" ", "")
    s = s.replace("級", "").replace("班", "")
    m = re.fullmatch(r"([SAL])([123])", s)
    if not m:
        raise ConsensusError(f"invalid_class:{value}")
    return "".join(m.groups())

def normalize_style(value: Any) -> str:
    s = _nfkc(value).replace(" ", "")
    aliases = {
        "逃": "逃", "逃げ": "逃",
        "追": "追", "追込": "追", "追込み": "追",
        "両": "両", "両用": "両",
    }
    if s not in aliases:
        raise ConsensusError(f"invalid_style:{value}")
    return aliases[s]

def normalize_circumference(value: Any) -> int:
    x = float(value)
    if abs(x - 400.0) < 0.51:
        return 400
    if abs(x - 333.0) < 0.8 or abs(x - 333.33) < 0.8:
        return 333
    raise ConsensusError(f"invalid_circumference:{value}")

def validate_sha256(value: Any) -> str:
    s = _nfkc(value).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", s):
        raise ConsensusError("invalid_source_sha256")
    return s

def validate_capture_time(value: Any) -> str:
    s = _nfkc(value)
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as exc:
        raise ConsensusError("invalid_captured_at_jst") from exc
    if dt.tzinfo is None:
        raise ConsensusError("captured_at_jst_missing_timezone")
    return s

def normalize_observation(obs: dict) -> dict:
    source = _nfkc(obs.get("source_name")).lower()
    if source not in TRUSTED_SOURCES:
        raise ConsensusError(f"untrusted_source:{source or 'missing'}")
    page_kind = _nfkc(obs.get("page_kind")).lower()
    if page_kind in FORBIDDEN_PAGE_KINDS or any(tok in page_kind for tok in ("result", "payout", "odds", "prediction", "comment")):
        raise ConsensusError(f"forbidden_page_kind:{page_kind}")
    if page_kind not in ALLOWED_PAGE_KINDS:
        raise ConsensusError(f"not_final_day1_racecard:{page_kind or 'missing'}")

    url = _nfkc(obs.get("source_url"))
    if not url.startswith(("https://", "http://")):
        raise ConsensusError("invalid_source_url")

    reg = _nfkc(obs.get("official_registration_number"))
    if not re.fullmatch(r"\d{6}", reg):
        raise ConsensusError("invalid_registration")

    try:
        race_no = int(obs.get("race_no"))
        car_no = int(obs.get("car_no"))
    except (ValueError, TypeError) as exc:
        raise ConsensusError("invalid_race_or_car_no") from exc
    if not 1 <= race_no <= 12:
        raise ConsensusError("invalid_race_no")
    if not 1 <= car_no <= 9:
        raise ConsensusError("invalid_car_no")

    day = _nfkc(obs.get("day"))
    if day in {"1", "初日", "DAY1", "day1"}:
        day = "Day1"
    if day != "Day1":
        raise ConsensusError("not_day1")

    race_date = _nfkc(obs.get("race_date"))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", race_date):
        raise ConsensusError("invalid_race_date")

    return {
        "source_name": source,
        "page_kind": page_kind,
        "official_registration_number": reg,
        "rider_name": normalize_name(obs.get("rider_name")),
        "race_date": race_date,
        "venue": normalize_venue(obs.get("venue")),
        "day": day,
        "circumference_m": normalize_circumference(obs.get("circumference_m")),
        "race_no": race_no,
        "car_no": car_no,
        "class": normalize_class(obs.get("class")),
        "style": normalize_style(obs.get("style")),
        "source_url": url,
        "captured_at_jst": validate_capture_time(obs.get("captured_at_jst")),
        "source_sha256": validate_sha256(obs.get("source_sha256")),
        "source_title": _nfkc(obs.get("source_title")),
    }

def _expected_core(expected: dict) -> dict:
    return {
        "official_registration_number": _nfkc(expected.get("official_registration_number")),
        "rider_name": normalize_name(expected.get("rider_name")),
        "race_date": _nfkc(expected.get("race_date")),
        "venue": normalize_venue(expected.get("venue")),
        "day": "Day1",
        "circumference_m": normalize_circumference(expected.get("circumference_m")),
    }

def decide_candidate(expected: dict, observations: list[dict]) -> dict:
    exp = _expected_core(expected)
    normalized = []
    source_seen = set()
    rejected = []

    for raw in observations:
        try:
            obs = normalize_observation(raw)
        except ConsensusError as exc:
            rejected.append({
                "source_name": _nfkc(raw.get("source_name")).lower(),
                "reason": str(exc),
            })
            continue
        if obs["source_name"] in source_seen:
            rejected.append({"source_name": obs["source_name"], "reason": "duplicate_source_observation"})
            continue
        source_seen.add(obs["source_name"])

        mismatch = []
        for field in ("official_registration_number","rider_name","race_date","venue","day","circumference_m"):
            if obs[field] != exp[field]:
                mismatch.append(field)
        if mismatch:
            rejected.append({
                "source_name": obs["source_name"],
                "reason": "locked_candidate_mismatch:" + ",".join(mismatch),
            })
            continue
        normalized.append(obs)

    if not normalized:
        return {
            "status": "NOT_READY",
            "formal_blocker_added": False,
            "expected": exp,
            "accepted_sources": [],
            "rejected_sources": rejected,
            "finalizer_row": None,
        }

    assignment_fields = ("race_no", "car_no", "class", "style")
    reference = normalized[0]
    conflicts = []
    for obs in normalized[1:]:
        diff = [f for f in assignment_fields if obs[f] != reference[f]]
        if diff:
            conflicts.append({
                "source_a": reference["source_name"],
                "source_b": obs["source_name"],
                "fields": diff,
            })
    if conflicts:
        return {
            "status": "CONFLICT_FAIL_CLOSED",
            "formal_blocker_added": False,
            "expected": exp,
            "accepted_sources": [o["source_name"] for o in normalized],
            "rejected_sources": rejected,
            "conflicts": conflicts,
            "finalizer_row": None,
        }

    status = "CONSENSUS_PASS" if len(normalized) >= 2 else "SINGLE_SOURCE_READY"
    chosen = sorted(normalized, key=lambda x: x["source_name"])[0]
    consensus_payload = [
        {
            "source_name": o["source_name"],
            "source_url": o["source_url"],
            "source_sha256": o["source_sha256"],
            "captured_at_jst": o["captured_at_jst"],
        }
        for o in sorted(normalized, key=lambda x: x["source_name"])
    ]
    audit_digest = hashlib.sha256(
        json.dumps(consensus_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()

    row = deepcopy(expected)
    row.update({
        "official_registration_number": exp["official_registration_number"],
        "rider_name": _nfkc(expected.get("rider_name")),
        "race_date": exp["race_date"],
        "venue": exp["venue"],
        "day": "Day1",
        "circumference_m": exp["circumference_m"],
        "race_no": chosen["race_no"],
        "car_no": chosen["car_no"],
        "class": chosen["class"],
        "style": chosen["style"],
        "source": "MULTISITE_FINAL_DAY1_RACECARD_CONSENSUS" if len(normalized) >= 2 else chosen["source_name"].upper()+"_FINAL_DAY1_RACECARD",
        "source_role": "FINAL_DAY1_RACECARD",
        "source_url": chosen["source_url"],
        "captured_at_jst": chosen["captured_at_jst"],
        "trusted_pit_cutoff_jst": None,
        "source_sha256": chosen["source_sha256"],
        "fill_status": status,
        "consensus_audit": {
            "status": status,
            "source_count": len(normalized),
            "sources": consensus_payload,
            "audit_sha256": audit_digest,
            "multi_source_required_for_formal_support": False,
            "material_fields_checked": list(MATERIAL_FIELDS),
        },
    })
    return {
        "status": status,
        "formal_blocker_added": False,
        "expected": exp,
        "accepted_sources": [o["source_name"] for o in normalized],
        "rejected_sources": rejected,
        "finalizer_row": row,
    }

def build_finalizer_manifest(shell: dict, observations_by_registration: dict[str, list[dict]]) -> dict:
    out = deepcopy(shell)
    out["record"] = "KEIRIN_35_FINAL_DAY1_PRE_INPUT_MANIFEST_MULTISITE_NORMALIZED_v1"
    out["normalizer"] = "tools/keirin_final_racecard_consensus_normalizer_v1.py"
    out["normalizer_policy"] = (
        ">=2 exact trusted sources => CONSENSUS_PASS; exactly 1 => SINGLE_SOURCE_READY; "
        "any material disagreement => CONFLICT_FAIL_CLOSED. Multi-source agreement is audit hardening, not a new formal gate."
    )
    decisions = []
    ready_rows = []
    for expected in list(shell.get("rows") or []):
        reg = _nfkc(expected.get("official_registration_number"))
        decision = decide_candidate(expected, list(observations_by_registration.get(reg) or []))
        decisions.append({
            "priority": expected.get("priority"),
            "official_registration_number": reg,
            "rider_name": expected.get("rider_name"),
            **{k: v for k, v in decision.items() if k != "finalizer_row"},
        })
        if decision["finalizer_row"] is not None:
            ready_rows.append(decision["finalizer_row"])
        else:
            ready_rows.append(deepcopy(expected))
    out["rows"] = ready_rows
    out["multisite_consensus_decisions"] = decisions
    out["support_increment_authorized_now"] = 0
    out["result_access_authorized"] = False
    out["runtime"] = False
    return out
