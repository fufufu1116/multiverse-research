#!/usr/bin/env python3
"""Normalize independent final Day1 keirin racecard observations.

PRE-only research utility. Conflicting trusted sources fail closed.
No RESULT/PAYOUT/ODDS/PREDICTION access and no exact cutoff requirement.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import re
from typing import Any, Iterable, Mapping

FORBIDDEN_TOKENS = (
    "result", "results", "結果", "払戻", "payout",
    "odds", "オッズ", "prediction", "予想",
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
STYLE_VALUES = {"逃", "追", "両"}
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


class RacecardNormalizerError(ValueError):
    pass


def _text(value: Any) -> str:
    return str(value or "").strip()


def _parse_dt(value: Any, field: str) -> datetime:
    text = _text(value)
    if not text:
        raise RacecardNormalizerError(f"missing_{field}")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise RacecardNormalizerError(f"invalid_{field}") from exc
    if dt.tzinfo is None:
        raise RacecardNormalizerError(f"timezone_required_{field}")
    return dt


def _validate_sha256(value: Any) -> str:
    text = _text(value)
    if not HEX64.fullmatch(text):
        raise RacecardNormalizerError("invalid_source_sha256")
    return text.lower()


def _circ_bucket(value: Any) -> str:
    x = float(value)
    if abs(x - 400.0) < 0.01:
        return "400"
    if abs(x - 333.0) < 1.0 or abs(x - 333.33) < 1.0:
        return "333_OR_333_33"
    raise RacecardNormalizerError(f"unsupported_circumference:{x}")


def _target_bucket(target: Mapping[str, Any]) -> str:
    raw = _text(target.get("circumference_bucket"))
    if raw.endswith("M"):
        raw = raw[:-1]
    if raw in {"400", "333_OR_333_33"}:
        return raw
    if target.get("circumference_m") is not None:
        return _circ_bucket(target["circumference_m"])
    raise RacecardNormalizerError("target_circumference_missing")


def _candidate_index(locked_order: Mapping[str, Any]) -> dict:
    out = {}
    for candidate in locked_order.get("ordered_candidates") or []:
        future = candidate.get("future") or {}
        key = (
            _text(candidate.get("registration")),
            _text(future.get("date")),
            _text(future.get("venue")),
        )
        if not all(key):
            raise RacecardNormalizerError("invalid_locked_candidate")
        if key in out:
            raise RacecardNormalizerError(f"duplicate_locked_candidate:{key}")
        out[key] = dict(candidate)
    if not out:
        raise RacecardNormalizerError("empty_locked_order")
    return out


def _observation_identity(obs: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        _text(obs.get("official_registration_number")),
        _text(obs.get("race_date")),
        _text(obs.get("venue")),
    )


def _validate_observation(obs: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict:
    status = _text(obs.get("status")).upper()
    if status in WITHDRAWAL_STATUSES:
        raise RacecardNormalizerError(f"withdrawal_or_substitution:{status}")

    source_family = _text(obs.get("source_family")).upper()
    source_role = _text(obs.get("source_role")).upper()
    source_url = _text(obs.get("source_url"))
    source_namespace = _text(obs.get("source_namespace"))
    source_title = _text(obs.get("source_title"))

    if not source_family:
        raise RacecardNormalizerError("missing_source_family")
    if source_role not in ALLOWED_SOURCE_ROLES:
        raise RacecardNormalizerError(f"source_role_not_allowed:{source_role}")
    if not source_url.startswith(("https://", "http://")):
        raise RacecardNormalizerError("invalid_source_url")

    forbidden_blob = " ".join(
        (source_role, source_url, source_namespace, source_title)
    ).lower()
    for token in FORBIDDEN_TOKENS:
        if token.lower() in forbidden_blob:
            raise RacecardNormalizerError(f"forbidden_source_namespace:{token}")

    source_sha256 = _validate_sha256(obs.get("source_sha256"))
    captured = _parse_dt(obs.get("captured_at_jst"), "captured_at_jst")

    future = candidate["future"]
    expected = {
        "official_registration_number": _text(candidate["registration"]),
        "rider_name": _text(candidate["rider_name"]),
        "race_date": _text(future["date"]),
        "venue": _text(future["venue"]),
        "day": "Day1",
    }
    actual = {
        "official_registration_number": _text(obs.get("official_registration_number")),
        "rider_name": _text(obs.get("rider_name")),
        "race_date": _text(obs.get("race_date")),
        "venue": _text(obs.get("venue")),
        "day": _text(obs.get("day")),
    }
    for field in expected:
        if actual[field] != expected[field]:
            raise RacecardNormalizerError(
                f"{field}_mismatch:{actual[field]!r}!={expected[field]!r}"
            )

    if _circ_bucket(obs.get("circumference_m")) != _target_bucket(future):
        raise RacecardNormalizerError("circumference_mismatch")

    try:
        race_no = int(obs.get("race_no"))
        car_no = int(obs.get("car_no"))
    except (TypeError, ValueError) as exc:
        raise RacecardNormalizerError("invalid_race_or_car_number") from exc
    if not (1 <= race_no <= 12):
        raise RacecardNormalizerError("race_no_out_of_range")
    if not (1 <= car_no <= 9):
        raise RacecardNormalizerError("car_no_out_of_range")

    race_class = _text(obs.get("class"))
    style = _text(obs.get("style"))
    if not race_class:
        raise RacecardNormalizerError("missing_class")
    if style not in STYLE_VALUES:
        raise RacecardNormalizerError("invalid_style")

    return {
        "source_family": source_family,
        "source_role": source_role,
        "source_namespace": source_namespace,
        "source_url": source_url,
        "source_sha256": source_sha256,
        "captured_at_jst": captured.isoformat(),
        "official_registration_number": expected["official_registration_number"],
        "rider_name": expected["rider_name"],
        "race_date": expected["race_date"],
        "venue": expected["venue"],
        "day": "Day1",
        "circumference_m": float(obs["circumference_m"]),
        "race_no": race_no,
        "car_no": car_no,
        "class": race_class,
        "style": style,
    }


def normalize(locked_order: Mapping[str, Any], observations: Iterable[Mapping[str, Any]]) -> dict:
    candidates = _candidate_index(locked_order)
    grouped = defaultdict(list)
    seen_source_observation = set()
    rejected = []

    for raw in observations:
        key = _observation_identity(raw)
        candidate = candidates.get(key)
        if candidate is None:
            rejected.append({
                "key": key, "status": "FAIL_CLOSED",
                "reason": "observation_not_in_locked_35_target",
            })
            continue

        dedupe_key = (
            key,
            _text(raw.get("source_family")).upper(),
            _text(raw.get("source_url")),
        )
        if dedupe_key in seen_source_observation:
            rejected.append({
                "key": key, "status": "FAIL_CLOSED",
                "reason": "duplicate_source_observation",
            })
            continue
        seen_source_observation.add(dedupe_key)

        try:
            grouped[key].append(_validate_observation(raw, candidate))
        except RacecardNormalizerError as exc:
            rejected.append({
                "key": key, "status": "FAIL_CLOSED", "reason": str(exc),
            })

    normalized_rows = []
    conflicts = []

    for key, rows in sorted(grouped.items()):
        same_key_rejections = [r for r in rejected if tuple(r["key"]) == key]
        if same_key_rejections:
            conflicts.append({
                "key": key, "status": "FAIL_CLOSED",
                "reason": "one_or_more_observations_invalid",
                "rejections": same_key_rejections,
            })
            continue

        signatures = {
            (
                row["race_no"], row["car_no"], row["class"], row["style"],
                _circ_bucket(row["circumference_m"]),
                row["rider_name"], row["day"],
            )
            for row in rows
        }
        if len(signatures) != 1:
            conflicts.append({
                "key": key, "status": "FAIL_CLOSED",
                "reason": "cross_source_assignment_conflict",
                "observed_assignments": [
                    {
                        "source_family": row["source_family"],
                        "race_no": row["race_no"],
                        "car_no": row["car_no"],
                        "class": row["class"],
                        "style": row["style"],
                        "circumference_m": row["circumference_m"],
                    }
                    for row in rows
                ],
            })
            continue

        families = sorted({row["source_family"] for row in rows})
        primary = sorted(
            rows,
            key=lambda row: (
                row["source_family"], row["source_url"], row["source_sha256"]
            ),
        )[0]
        normalized_rows.append({
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
            "source_role": "FINAL_DAY1_RACECARD",
            "source_namespace": "MULTISITE_NORMALIZED_FINAL_DAY1_RACECARD",
            "source_url": primary["source_url"],
            "source_sha256": primary["source_sha256"],
            "captured_at_jst": primary["captured_at_jst"],
            "corroboration_count": len(families),
            "corroborating_source_families": families,
            "corroborations": [
                {
                    "source_family": row["source_family"],
                    "source_url": row["source_url"],
                    "source_sha256": row["source_sha256"],
                    "captured_at_jst": row["captured_at_jst"],
                }
                for row in sorted(
                    rows, key=lambda r: (r["source_family"], r["source_url"])
                )
            ],
            "exact_cutoff_timestamp_required": False,
        })

    return {
        "record": "KEIRIN_MULTISITE_FINAL_RACECARD_NORMALIZATION_OUTPUT_v1",
        "status": "PASS" if not rejected and not conflicts else "FAIL_CLOSED",
        "normalized_rows": normalized_rows,
        "normalized_row_count": len(normalized_rows),
        "rejected_observations": rejected,
        "conflicts": conflicts,
        "result_accessed": False,
        "payout_accessed": False,
        "odds_accessed": False,
        "prediction_accessed": False,
        "runtime": False,
    }
