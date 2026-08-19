from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Dict, List

HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")

ALLOWED_REGIMES = {
    "STANDARD_ORIGINAL_LINE_KEIRIN",
    "INTERNATIONAL_FIXED_PACER",
    "UNKNOWN_OR_OTHER",
}

ALLOWED_LINE_OBSERVATION_TYPES = {
    "LEGSHOW_OBSERVED_LINE",
    "PRE_EVENT_EXPECTED_LINE",
    "NONE",
}

NONNEGATIVE_COUNT_FIELDS = ("S", "H", "B", "nige", "makuri", "sashi", "mark")


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX64.fullmatch(value))


def validate_pre_structure(record: Dict[str, Any], require_line_for_standard: bool = True) -> List[str]:
    """Return a list of fail-closed validation errors.

    This validator intentionally checks only structural/provenance invariants. It does not
    decide whether a source is legally authorized, scientifically admitted, or useful.
    Those remain separate governance gates.
    """

    errors: List[str] = []

    required_race_fields = (
        "race_id",
        "prediction_timestamp",
        "decision_timestamp",
        "decision_cutoff_rule_id",
        "race_regime",
        "race_regime_source",
        "race_regime_source_timestamp",
        "race_regime_raw_provenance_sha",
        "riders",
    )
    for field in required_race_fields:
        if field not in record:
            errors.append(f"missing_race_field:{field}")

    if errors:
        return errors

    try:
        prediction_ts = _parse_timestamp(record["prediction_timestamp"])
        decision_ts = _parse_timestamp(record["decision_timestamp"])
        regime_ts = _parse_timestamp(record["race_regime_source_timestamp"])
        if prediction_ts > decision_ts:
            errors.append("prediction_timestamp_after_decision_timestamp")
        if regime_ts > decision_ts:
            errors.append("race_regime_source_after_decision_timestamp")
    except Exception as exc:
        errors.append(f"invalid_core_timestamp:{type(exc).__name__}")
        decision_ts = None

    regime = record.get("race_regime")
    if regime not in ALLOWED_REGIMES:
        errors.append("invalid_race_regime")

    if not _valid_sha256(record.get("race_regime_raw_provenance_sha")):
        errors.append("invalid_race_regime_provenance_sha256")

    riders = record.get("riders")
    if not isinstance(riders, list) or not riders:
        errors.append("riders_must_be_nonempty_list")
        return errors

    active = [r for r in riders if isinstance(r, dict) and r.get("active") is True]
    if not active:
        errors.append("no_active_riders")
        return errors

    car_nos = [r.get("car_no") for r in active]
    rider_ids = [r.get("rider_id") for r in active]
    if None in car_nos:
        errors.append("missing_active_car_no")
    if None in rider_ids:
        errors.append("missing_active_rider_id")
    if len(car_nos) != len(set(car_nos)):
        errors.append("duplicate_active_car_no")
    if len(rider_ids) != len(set(rider_ids)):
        errors.append("duplicate_active_rider_id")

    for rider in active:
        car_no = rider.get("car_no")
        for field in NONNEGATIVE_COUNT_FIELDS:
            value = rider.get(field)
            if value is not None:
                try:
                    if float(value) < 0:
                        errors.append(f"negative_{field}:car={car_no}")
                except Exception:
                    errors.append(f"nonnumeric_{field}:car={car_no}")

    if regime == "STANDARD_ORIGINAL_LINE_KEIRIN" and require_line_for_standard:
        required_line_race_fields = (
            "line_source",
            "line_snapshot_timestamp",
            "line_observation_type",
            "line_raw_provenance_sha",
            "num_lines",
        )
        for field in required_line_race_fields:
            if field not in record:
                errors.append(f"missing_line_race_field:{field}")

        if record.get("line_observation_type") not in (
            ALLOWED_LINE_OBSERVATION_TYPES - {"NONE"}
        ):
            errors.append("invalid_line_observation_type_for_standard_regime")

        if not _valid_sha256(record.get("line_raw_provenance_sha")):
            errors.append("invalid_line_provenance_sha256")

        try:
            line_ts = _parse_timestamp(record.get("line_snapshot_timestamp"))
            if decision_ts is not None and line_ts > decision_ts:
                errors.append("line_snapshot_after_decision_timestamp")
        except Exception as exc:
            errors.append(f"invalid_line_snapshot_timestamp:{type(exc).__name__}")

        groups: Dict[Any, List[Dict[str, Any]]] = {}
        for rider in active:
            car_no = rider.get("car_no")
            for field in ("line_group_id", "line_position", "line_size", "is_singleton"):
                if field not in rider:
                    errors.append(f"missing_{field}:car={car_no}")
            group_id = rider.get("line_group_id")
            if group_id is None or group_id == "":
                errors.append(f"empty_line_group_id:car={car_no}")
            groups.setdefault(group_id, []).append(rider)

        if record.get("num_lines") != len(groups):
            errors.append("num_lines_mismatch")

        for group_id, members in groups.items():
            positions = [m.get("line_position") for m in members]
            if all(isinstance(x, int) for x in positions):
                if sorted(positions) != list(range(len(members))):
                    errors.append(f"noncontiguous_line_positions:group={group_id}")
            else:
                errors.append(f"noninteger_line_position:group={group_id}")

            for rider in members:
                car_no = rider.get("car_no")
                if rider.get("line_size") != len(members):
                    errors.append(f"line_size_mismatch:car={car_no}")
                if rider.get("is_singleton") is not (len(members) == 1):
                    errors.append(f"is_singleton_mismatch:car={car_no}")

    if regime in {"INTERNATIONAL_FIXED_PACER", "UNKNOWN_OR_OTHER"}:
        # This is not an error by itself. It is an explicit applicability boundary:
        # C1/N1 line-dependent families must fail closed or route to another family.
        pass

    return errors


def fail_closed(record: Dict[str, Any], require_line_for_standard: bool = True) -> None:
    errors = validate_pre_structure(record, require_line_for_standard=require_line_for_standard)
    if errors:
        raise ValueError("PRE_STRUCTURE_FAIL_CLOSED: " + " | ".join(errors))
