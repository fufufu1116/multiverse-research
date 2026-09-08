#!/usr/bin/env python3
"""Six-source prospective final Day1 racecard normalizer v2.

Research-lane PRE-only audit utility.
- Explicit six-family allowlist.
- Deterministic typography normalization only (NFKC/whitespace/known labels).
- One complete trusted final racecard can be SINGLE_SOURCE_READY.
- >=2 complete trusted sources agreeing exactly become CONSENSUS_PASS.
- Any disagreement among valid trusted observations fails closed.
- A withdrawal/substitution signal for a locked candidate fails closed.
- Forbidden RESULT/PAYOUT/ODDS/PREDICTION/comment namespaces are never data.
- Multi-source agreement is audit hardening, not a new formal-support blocker.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import re
import unicodedata
from urllib.parse import urlsplit
from typing import Any, Iterable, Mapping

TRUSTED_SOURCE_FAMILIES = {
    "CTC", "KDREAMS", "WINTICKET", "KEIRIN.JP", "CHARILOTO", "ODDSPARK"
}
FORBIDDEN_TOKENS = (
    "result", "results", "結果", "払戻", "payout",
    "odds", "オッズ", "prediction", "予想", "comment", "comments", "コメント",
)
ALLOWED_SOURCE_ROLES = {
    "FINAL_DAY1_RACECARD",
    "OFFICIAL_DAY1_RACECARD",
    "CTC_DAY1_RACECARD",
    "SCHEDULE_DAY1_RACECARD",
}
WITHDRAWAL_STATUSES = {
    "WITHDRAWN", "SCRATCHED", "CANCELLED", "SUBSTITUTED_OUT", "ABSENT",
}
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
CLASS_RE = re.compile(r"^([SAL])([123])$")


class RacecardNormalizerError(ValueError):
    pass


def _nfkc(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def _compact(value: Any) -> str:
    return re.sub(r"\s+", "", _nfkc(value))


def _venue(value: Any) -> str:
    s = _nfkc(value)
    return re.sub(r"(競輪場|競輪)$", "", s).strip()


def _parse_dt(value: Any, field: str) -> str:
    text = _nfkc(value)
    if not text:
        raise RacecardNormalizerError(f"missing_{field}")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise RacecardNormalizerError(f"invalid_{field}") from exc
    if dt.tzinfo is None:
        raise RacecardNormalizerError(f"timezone_required_{field}")
    return dt.isoformat()


def _validate_sha256(value: Any) -> str:
    text = _nfkc(value)
    if not HEX64.fullmatch(text):
        raise RacecardNormalizerError("invalid_source_sha256")
    return text.lower()


def _circ_bucket(value: Any) -> str:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise RacecardNormalizerError("invalid_circumference") from exc
    if abs(x - 400.0) < 0.51:
        return "400"
    if abs(x - 333.0) < 0.8 or abs(x - 333.33) < 0.8:
        return "333_OR_333_33"
    raise RacecardNormalizerError(f"unsupported_circumference:{x}")


def _target_bucket(target: Mapping[str, Any]) -> str:
    raw = _nfkc(target.get("circumference_bucket"))
    if raw.endswith("M"):
        raw = raw[:-1]
    if raw in {"400", "333_OR_333_33"}:
        return raw
    if target.get("circumference_m") is not None:
        return _circ_bucket(target["circumference_m"])
    raise RacecardNormalizerError("target_circumference_missing")


def _race_class(value: Any) -> str:
    s = _compact(value).upper().replace("級", "").replace("班", "")
    m = CLASS_RE.fullmatch(s)
    if not m:
        raise RacecardNormalizerError(f"invalid_class:{_nfkc(value)}")
    return "".join(m.groups())


def _style(value: Any) -> str:
    s = _compact(value)
    aliases = {
        "逃": "逃",
        "逃げ": "逃",
        "追": "追",
        "追込": "追",
        "追込み": "追",
        "両": "両",
    }
    if s not in aliases:
        raise RacecardNormalizerError(f"invalid_style:{_nfkc(value)}")
    return aliases[s]


def _day(value: Any) -> str:
    s = _compact(value)
    aliases = {"Day1": "Day1", "DAY1": "Day1", "day1": "Day1", "1": "Day1", "初日": "Day1"}
    if s not in aliases:
        raise RacecardNormalizerError(f"not_day1:{_nfkc(value)}")
    return "Day1"


def _candidate_index(locked_order: Mapping[str, Any]) -> dict:
    out = {}
    for candidate in locked_order.get("ordered_candidates") or []:
        future = candidate.get("future") or {}
        key = (
            _nfkc(candidate.get("registration")),
            _nfkc(future.get("date")),
            _venue(future.get("venue")),
        )
        if not all(key):
            raise RacecardNormalizerError("invalid_locked_candidate")
        if key in out:
            raise RacecardNormalizerError(f"duplicate_locked_candidate:{key}")
        out[key] = dict(candidate)
    if not out:
        raise RacecardNormalizerError("empty_locked_order")
    return out


def _candidate_key_from_raw(obs: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        _nfkc(obs.get("official_registration_number")),
        _nfkc(obs.get("race_date")),
        _venue(obs.get("venue")),
    )


def _source_family(obs: Mapping[str, Any]) -> str:
    raw = _nfkc(obs.get("source_family")).upper()
    aliases = {"KEIRIN_JP": "KEIRIN.JP", "K DREAMS": "KDREAMS", "K-DREAMS": "KDREAMS"}
    return aliases.get(raw, raw)


def _forbidden_source(obs: Mapping[str, Any]) -> None:
    # Do not scan the hostname: a trusted host such as oddspark.com contains
    # the literal token "odds" even on its safe racecard pages.
    url = _nfkc(obs.get("source_url"))
    parsed = urlsplit(url) if url else None
    url_payload = ""
    if parsed is not None:
        url_payload = " ".join((parsed.path or "", parsed.query or "", parsed.fragment or ""))
    blob = " ".join(
        [
            _nfkc(obs.get("source_role")),
            _nfkc(obs.get("source_namespace")),
            _nfkc(obs.get("source_title")),
            _nfkc(obs.get("page_kind")),
            url_payload,
        ]
    ).lower()
    for token in FORBIDDEN_TOKENS:
        t = token.lower()
        if re.fullmatch(r"[a-z]+", t):
            hit = re.search(rf"(?<![a-z]){re.escape(t)}(?![a-z])", blob) is not None
        else:
            hit = t in blob
        if hit:
            raise RacecardNormalizerError(f"forbidden_source_namespace:{token}")


def _validate_complete_observation(obs: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict:
    family = _source_family(obs)
    if family not in TRUSTED_SOURCE_FAMILIES:
        raise RacecardNormalizerError(f"untrusted_source_family:{family or 'MISSING'}")

    _forbidden_source(obs)

    role = _nfkc(obs.get("source_role")).upper()
    if role not in ALLOWED_SOURCE_ROLES:
        raise RacecardNormalizerError(f"source_role_not_allowed:{role or 'MISSING'}")

    url = _nfkc(obs.get("source_url"))
    if not url.startswith(("https://", "http://")):
        raise RacecardNormalizerError("invalid_source_url")

    status = _nfkc(obs.get("status")).upper()
    if status in WITHDRAWAL_STATUSES:
        raise RacecardNormalizerError(f"withdrawal_or_substitution:{status}")

    future = candidate["future"]
    expected = {
        "official_registration_number": _nfkc(candidate["registration"]),
        "rider_name": _compact(candidate["rider_name"]),
        "race_date": _nfkc(future["date"]),
        "venue": _venue(future["venue"]),
        "day": "Day1",
        "circumference_bucket": _target_bucket(future),
    }
    actual = {
        "official_registration_number": _nfkc(obs.get("official_registration_number")),
        "rider_name": _compact(obs.get("rider_name")),
        "race_date": _nfkc(obs.get("race_date")),
        "venue": _venue(obs.get("venue")),
        "day": _day(obs.get("day")),
        "circumference_bucket": _circ_bucket(obs.get("circumference_m")),
    }
    for field in expected:
        if actual[field] != expected[field]:
            raise RacecardNormalizerError(
                f"{field}_mismatch:{actual[field]!r}!={expected[field]!r}"
            )

    try:
        race_no = int(obs.get("race_no"))
        car_no = int(obs.get("car_no"))
    except (TypeError, ValueError) as exc:
        raise RacecardNormalizerError("invalid_race_or_car_number") from exc
    if not 1 <= race_no <= 12:
        raise RacecardNormalizerError("race_no_out_of_range")
    if not 1 <= car_no <= 9:
        raise RacecardNormalizerError("car_no_out_of_range")

    return {
        "source_family": family,
        "source_role": role,
        "source_namespace": _nfkc(obs.get("source_namespace")),
        "source_url": url,
        "source_sha256": _validate_sha256(obs.get("source_sha256")),
        "captured_at_jst": _parse_dt(obs.get("captured_at_jst"), "captured_at_jst"),
        "official_registration_number": expected["official_registration_number"],
        "rider_name": _nfkc(candidate["rider_name"]),
        "race_date": expected["race_date"],
        "venue": expected["venue"],
        "day": "Day1",
        "circumference_m": 400 if expected["circumference_bucket"] == "400" else 333,
        "race_no": race_no,
        "car_no": car_no,
        "class": _race_class(obs.get("class")),
        "style": _style(obs.get("style")),
    }


def normalize(locked_order: Mapping[str, Any], observations: Iterable[Mapping[str, Any]]) -> dict:
    candidates = _candidate_index(locked_order)
    grouped = defaultdict(list)
    rejected = []
    hard_candidate_blocks = defaultdict(list)
    seen_family = set()

    for raw in observations:
        key = _candidate_key_from_raw(raw)
        candidate = candidates.get(key)
        if candidate is None:
            rejected.append({"key": key, "status": "REJECTED", "reason": "observation_not_in_locked_35_target"})
            continue

        status = _nfkc(raw.get("status")).upper()
        if status in WITHDRAWAL_STATUSES:
            hard_candidate_blocks[key].append(f"withdrawal_or_substitution:{status}")
            continue

        family = _source_family(raw)
        family_key = (key, family)
        if family_key in seen_family:
            rejected.append({"key": key, "status": "REJECTED", "reason": f"duplicate_source_family:{family}"})
            continue
        seen_family.add(family_key)

        try:
            grouped[key].append(_validate_complete_observation(raw, candidate))
        except RacecardNormalizerError as exc:
            rejected.append({"key": key, "source_family": family, "status": "REJECTED", "reason": str(exc)})

    normalized_rows = []
    decisions = []

    for key, candidate in sorted(candidates.items(), key=lambda kv: kv[1].get("priority", 999)):
        rows = grouped.get(key, [])
        if hard_candidate_blocks.get(key):
            decisions.append({
                "key": key, "priority": candidate.get("priority"),
                "status": "CONFLICT_FAIL_CLOSED",
                "reason": ";".join(hard_candidate_blocks[key]),
            })
            continue
        if not rows:
            decisions.append({
                "key": key, "priority": candidate.get("priority"),
                "status": "NOT_READY",
                "reason": "no_complete_trusted_final_day1_racecard",
            })
            continue

        signatures = {
            (r["race_no"], r["car_no"], r["class"], r["style"], r["circumference_m"])
            for r in rows
        }
        if len(signatures) != 1:
            decisions.append({
                "key": key, "priority": candidate.get("priority"),
                "status": "CONFLICT_FAIL_CLOSED",
                "reason": "cross_source_assignment_conflict",
                "observed_assignments": [
                    {k: r[k] for k in ("source_family","race_no","car_no","class","style","circumference_m")}
                    for r in rows
                ],
            })
            continue

        families = sorted({r["source_family"] for r in rows})
        primary = sorted(rows, key=lambda r: (r["source_family"], r["source_url"]))[0]
        status = "CONSENSUS_PASS" if len(families) >= 2 else "SINGLE_SOURCE_READY"
        corroborations = [
            {
                "source_family": r["source_family"],
                "source_url": r["source_url"],
                "source_sha256": r["source_sha256"],
                "captured_at_jst": r["captured_at_jst"],
            }
            for r in sorted(rows, key=lambda r: (r["source_family"], r["source_url"]))
        ]
        audit_sha = hashlib.sha256(
            json.dumps(corroborations, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        out = {
            "priority": candidate.get("priority"),
            "rider_name": primary["rider_name"],
            "official_registration_number": primary["official_registration_number"],
            "race_date": primary["race_date"],
            "venue": primary["venue"],
            "circumference_m": primary["circumference_m"],
            "day": "Day1",
            "race_no": primary["race_no"],
            "car_no": primary["car_no"],
            "class": primary["class"],
            "style": primary["style"],
            "source": "MULTISITE_FINAL_DAY1_RACECARD_CONSENSUS" if len(families) >= 2 else f"{primary['source_family']}_FINAL_DAY1_RACECARD",
            "source_role": "FINAL_DAY1_RACECARD",
            "source_namespace": "MULTISITE_NORMALIZED_FINAL_DAY1_RACECARD",
            "source_url": primary["source_url"],
            "source_sha256": primary["source_sha256"],
            "captured_at_jst": primary["captured_at_jst"],
            "trusted_pit_cutoff_jst": None,
            "fill_status": status,
            "corroboration_count": len(families),
            "corroborating_source_families": families,
            "corroborations": corroborations,
            "consensus_audit_sha256": audit_sha,
            "multi_source_required_for_formal_support": False,
            "exact_cutoff_timestamp_required": False,
        }
        normalized_rows.append(out)
        decisions.append({
            "key": key, "priority": candidate.get("priority"),
            "status": status,
            "corroboration_count": len(families),
            "corroborating_source_families": families,
        })

    has_conflict = any(d["status"] == "CONFLICT_FAIL_CLOSED" for d in decisions)
    return {
        "record": "KEIRIN_MULTISITE_FINAL_RACECARD_NORMALIZATION_OUTPUT_v2",
        "status": "FAIL_CLOSED" if has_conflict else "READY_PARTIAL",
        "normalized_rows": normalized_rows,
        "normalized_row_count": len(normalized_rows),
        "decisions": decisions,
        "rejected_observations": rejected,
        "formal_multi_source_minimum_added": False,
        "result_accessed": False,
        "payout_accessed": False,
        "odds_accessed": False,
        "prediction_accessed": False,
        "runtime": False,
    }


def build_finalizer_manifest(
    shell: Mapping[str, Any],
    locked_order: Mapping[str, Any],
    observations: Iterable[Mapping[str, Any]],
) -> dict:
    result = normalize(locked_order, observations)
    out = deepcopy(dict(shell))
    by_reg = {r["official_registration_number"]: r for r in result["normalized_rows"]}
    rows = []
    for row in out.get("rows") or []:
        reg = _nfkc(row.get("official_registration_number"))
        rows.append(deepcopy(by_reg.get(reg, row)))
    out["rows"] = rows
    out["record"] = "KEIRIN_35_FINAL_DAY1_PRE_INPUT_MANIFEST_MULTISITE_NORMALIZED_v2"
    out["multisite_normalizer"] = "tools/keirin_multisite_final_racecard_normalizer_v2.py"
    out["multisite_normalization"] = result
    out["support_increment_authorized_now"] = 0
    out["result_access_authorized"] = False
    out["runtime"] = False
    return out
