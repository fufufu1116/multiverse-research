from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Optional, Tuple


RACE_REGIMES = {
    "STANDARD_ORIGINAL_LINE_KEIRIN",
    "INTERNATIONAL_FIXED_PACER",
    "UNKNOWN_OR_OTHER",
}
LINE_OBSERVATION_TYPES = {
    "PRE_EVENT_EXPECTED_LINE",
    "LEGSHOW_OBSERVED_LINE",
    "NONE_OR_UNAVAILABLE",
}
SOURCE_CLASSES = {
    "OFFICIAL_RULE",
    "OFFICIAL_PROGRAM",
    "OFFICIAL_MASTER",
    "PRE_EMPIRICAL_AUTHORIZED",
    "BURNED_OUTCOME_AWARE",
    "EXTERNAL_AGGREGATE",
    "ASSUMPTION_RANGE",
    "ENGINEERING_FIXTURE",
}
RACE_GRADES = {"FI", "FII", "GIII", "GII", "GI", "GP", "OTHER"}
SEX_SCOPES = {"MEN", "WOMEN", "OTHER_OR_UNKNOWN"}


class RealityFoundationError(ValueError):
    """Fail-closed validation error for the reality-calibrated PRE foundation."""


def _require_nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise RealityFoundationError(f"{name}:empty")


def _parse_timestamp(name: str, value: str) -> datetime:
    _require_nonempty(name, value)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RealityFoundationError(f"{name}:invalid_iso8601") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise RealityFoundationError(f"{name}:timezone_required")
    return dt


def _finite_optional(name: str, value: Optional[float], minimum: Optional[float] = None) -> None:
    if value is None:
        return
    if not math.isfinite(float(value)):
        raise RealityFoundationError(f"{name}:nonfinite")
    if minimum is not None and float(value) < minimum:
        raise RealityFoundationError(f"{name}:below_minimum")


def _require_source_class(name: str, value: str, allowed: set[str]) -> None:
    if value not in SOURCE_CLASSES:
        raise RealityFoundationError(f"{name}:unknown_source_class:{value}")
    if value not in allowed:
        raise RealityFoundationError(f"{name}:source_class_not_allowed:{value}")


@dataclass(frozen=True)
class ProgramRegimeSnapshot:
    race_id: str
    event_datetime: str
    prediction_timestamp: str
    decision_timestamp: str
    decision_cutoff_rule_id: str
    venue_id: str
    race_grade: str
    race_class_band: str
    race_stage: str
    race_regime: str
    field_size: int
    sex_scope: str
    program_source: str
    program_source_class: str
    program_source_timestamp: str
    program_provenance_sha: str


@dataclass(frozen=True)
class VenueEnvironmentSnapshot:
    venue_id: str
    bank_length_m: float
    venue_source: str
    venue_source_class: str
    venue_provenance_sha: str
    home_straight_m: Optional[float] = None
    bank_cant_deg: Optional[float] = None
    weather: Optional[str] = None
    temperature_c: Optional[float] = None
    wind_speed_mps: Optional[float] = None
    wind_direction: Optional[str] = None
    environment_source: Optional[str] = None
    environment_source_class: Optional[str] = None
    environment_observation_timestamp: Optional[str] = None
    environment_provenance_sha: Optional[str] = None


@dataclass(frozen=True)
class RiderIdentitySnapshot:
    rider_id: str
    car_no: int
    class_at_cutoff: str
    active_status_at_cutoff: bool
    identity_source: str
    identity_source_class: str
    identity_snapshot_timestamp: str
    identity_provenance_sha: str
    registration_region_or_official_affiliation: Optional[str] = None


@dataclass(frozen=True)
class RiderPreHistorySnapshot:
    rider_id: str
    snapshot_timestamp: str
    source: str
    source_class: str
    provenance_sha: str
    competition_score: Optional[float] = None
    win_rate: Optional[float] = None
    quinella_rate: Optional[float] = None
    trio_rate: Optional[float] = None
    S: Optional[float] = None
    H: Optional[float] = None
    B: Optional[float] = None
    nige: Optional[float] = None
    makuri: Optional[float] = None
    sashi: Optional[float] = None
    mark: Optional[float] = None


@dataclass(frozen=True)
class LineMemberSnapshot:
    rider_id: str
    car_no: int
    line_group_id: str
    line_position: int
    line_size: int
    is_singleton: bool


@dataclass(frozen=True)
class LineSnapshot:
    race_id: str
    line_observation_type: str
    line_source: str
    line_source_class: str
    line_snapshot_timestamp: str
    line_raw_provenance_sha: str
    num_lines: int
    members: Tuple[LineMemberSnapshot, ...]


@dataclass(frozen=True)
class RaceRealityPreSnapshot:
    program: ProgramRegimeSnapshot
    venue_environment: VenueEnvironmentSnapshot
    riders: Tuple[RiderIdentitySnapshot, ...]
    rider_history: Tuple[RiderPreHistorySnapshot, ...]
    line_snapshot: Optional[LineSnapshot] = None


def validate_program(program: ProgramRegimeSnapshot) -> None:
    for name, value in (
        ("race_id", program.race_id),
        ("decision_cutoff_rule_id", program.decision_cutoff_rule_id),
        ("venue_id", program.venue_id),
        ("race_class_band", program.race_class_band),
        ("race_stage", program.race_stage),
        ("program_source", program.program_source),
        ("program_provenance_sha", program.program_provenance_sha),
    ):
        _require_nonempty(name, value)

    if program.race_grade not in RACE_GRADES:
        raise RealityFoundationError(f"race_grade:unknown:{program.race_grade}")
    if program.race_regime not in RACE_REGIMES:
        raise RealityFoundationError(f"race_regime:unknown:{program.race_regime}")
    if program.sex_scope not in SEX_SCOPES:
        raise RealityFoundationError(f"sex_scope:unknown:{program.sex_scope}")
    if not isinstance(program.field_size, int) or program.field_size < 3:
        raise RealityFoundationError("field_size:invalid")

    _require_source_class(
        "program_source_class",
        program.program_source_class,
        {"OFFICIAL_RULE", "OFFICIAL_PROGRAM"},
    )

    prediction = _parse_timestamp("prediction_timestamp", program.prediction_timestamp)
    decision = _parse_timestamp("decision_timestamp", program.decision_timestamp)
    event = _parse_timestamp("event_datetime", program.event_datetime)
    source_time = _parse_timestamp("program_source_timestamp", program.program_source_timestamp)

    if prediction > decision:
        raise RealityFoundationError("prediction_timestamp:after_decision")
    if decision >= event:
        raise RealityFoundationError("decision_timestamp:not_before_event")
    if source_time > decision:
        raise RealityFoundationError("program_source_timestamp:after_decision")


def validate_venue_environment(venue: VenueEnvironmentSnapshot, decision_timestamp: str) -> None:
    _require_nonempty("venue_id", venue.venue_id)
    _require_nonempty("venue_source", venue.venue_source)
    _require_nonempty("venue_provenance_sha", venue.venue_provenance_sha)
    _require_source_class("venue_source_class", venue.venue_source_class, {"OFFICIAL_MASTER"})
    _finite_optional("bank_length_m", venue.bank_length_m, minimum=1.0)
    _finite_optional("home_straight_m", venue.home_straight_m, minimum=1.0)
    _finite_optional("bank_cant_deg", venue.bank_cant_deg, minimum=0.0)
    _finite_optional("temperature_c", venue.temperature_c)
    _finite_optional("wind_speed_mps", venue.wind_speed_mps, minimum=0.0)

    has_environment = any(
        value is not None
        for value in (
            venue.weather,
            venue.temperature_c,
            venue.wind_speed_mps,
            venue.wind_direction,
        )
    )
    if has_environment:
        for name, value in (
            ("environment_source", venue.environment_source),
            ("environment_source_class", venue.environment_source_class),
            ("environment_observation_timestamp", venue.environment_observation_timestamp),
            ("environment_provenance_sha", venue.environment_provenance_sha),
        ):
            if value is None:
                raise RealityFoundationError(f"{name}:required_with_environment")
        _require_nonempty("environment_source", str(venue.environment_source))
        _require_nonempty("environment_provenance_sha", str(venue.environment_provenance_sha))
        _require_source_class(
            "environment_source_class",
            str(venue.environment_source_class),
            {"PRE_EMPIRICAL_AUTHORIZED", "OFFICIAL_MASTER"},
        )
        observed = _parse_timestamp(
            "environment_observation_timestamp",
            str(venue.environment_observation_timestamp),
        )
        decision = _parse_timestamp("decision_timestamp", decision_timestamp)
        if observed > decision:
            raise RealityFoundationError("environment_observation_timestamp:after_decision")
    else:
        extras = (
            venue.environment_source,
            venue.environment_source_class,
            venue.environment_observation_timestamp,
            venue.environment_provenance_sha,
        )
        if any(value is not None for value in extras):
            raise RealityFoundationError("environment_metadata_without_observation")


def validate_rider_identity(rider: RiderIdentitySnapshot, decision_timestamp: str) -> None:
    for name, value in (
        ("rider_id", rider.rider_id),
        ("class_at_cutoff", rider.class_at_cutoff),
        ("identity_source", rider.identity_source),
        ("identity_provenance_sha", rider.identity_provenance_sha),
    ):
        _require_nonempty(name, value)
    if not isinstance(rider.car_no, int) or rider.car_no <= 0:
        raise RealityFoundationError("car_no:invalid")
    if not isinstance(rider.active_status_at_cutoff, bool):
        raise RealityFoundationError("active_status_at_cutoff:not_bool")
    _require_source_class(
        "identity_source_class",
        rider.identity_source_class,
        {"OFFICIAL_PROGRAM", "PRE_EMPIRICAL_AUTHORIZED"},
    )
    snap = _parse_timestamp("identity_snapshot_timestamp", rider.identity_snapshot_timestamp)
    decision = _parse_timestamp("decision_timestamp", decision_timestamp)
    if snap > decision:
        raise RealityFoundationError("identity_snapshot_timestamp:after_decision")


def validate_rider_history(history: RiderPreHistorySnapshot, decision_timestamp: str) -> None:
    for name, value in (
        ("rider_id", history.rider_id),
        ("source", history.source),
        ("provenance_sha", history.provenance_sha),
    ):
        _require_nonempty(name, value)
    _require_source_class(
        "rider_history_source_class",
        history.source_class,
        {"PRE_EMPIRICAL_AUTHORIZED"},
    )
    snap = _parse_timestamp("rider_history_snapshot_timestamp", history.snapshot_timestamp)
    decision = _parse_timestamp("decision_timestamp", decision_timestamp)
    if snap > decision:
        raise RealityFoundationError("rider_history_snapshot_timestamp:after_decision")

    _finite_optional("competition_score", history.competition_score)
    for name, value in (
        ("win_rate", history.win_rate),
        ("quinella_rate", history.quinella_rate),
        ("trio_rate", history.trio_rate),
    ):
        _finite_optional(name, value, minimum=0.0)
        if value is not None and float(value) > 1.0:
            raise RealityFoundationError(f"{name}:above_one")
    for name, value in (
        ("S", history.S),
        ("H", history.H),
        ("B", history.B),
        ("nige", history.nige),
        ("makuri", history.makuri),
        ("sashi", history.sashi),
        ("mark", history.mark),
    ):
        _finite_optional(name, value, minimum=0.0)


def validate_line_snapshot(
    line: LineSnapshot,
    program: ProgramRegimeSnapshot,
    active_riders: Tuple[RiderIdentitySnapshot, ...],
    require_actionable_line: bool,
) -> None:
    if line.race_id != program.race_id:
        raise RealityFoundationError("line_snapshot:race_id_mismatch")
    if line.line_observation_type not in LINE_OBSERVATION_TYPES:
        raise RealityFoundationError(f"line_observation_type:unknown:{line.line_observation_type}")
    _require_nonempty("line_source", line.line_source)
    _require_nonempty("line_raw_provenance_sha", line.line_raw_provenance_sha)
    _require_source_class(
        "line_source_class",
        line.line_source_class,
        {"PRE_EMPIRICAL_AUTHORIZED"},
    )
    line_time = _parse_timestamp("line_snapshot_timestamp", line.line_snapshot_timestamp)
    decision = _parse_timestamp("decision_timestamp", program.decision_timestamp)
    if line_time > decision:
        raise RealityFoundationError("line_snapshot_timestamp:after_decision")

    if line.line_observation_type == "NONE_OR_UNAVAILABLE":
        if line.num_lines != 0 or line.members:
            raise RealityFoundationError("line_none_state:must_be_empty")
        if require_actionable_line:
            raise RealityFoundationError("actionable_line:unavailable")
        return

    if program.race_regime == "INTERNATIONAL_FIXED_PACER":
        raise RealityFoundationError("line_snapshot:not_applicable_to_international_fixed_pacer")
    if program.race_regime == "UNKNOWN_OR_OTHER":
        raise RealityFoundationError("line_snapshot:unknown_regime_fail_closed")

    if line.num_lines <= 0:
        raise RealityFoundationError("num_lines:invalid")

    expected_ids = {r.rider_id for r in active_riders}
    expected_cars = {r.car_no for r in active_riders}
    member_ids = [m.rider_id for m in line.members]
    member_cars = [m.car_no for m in line.members]
    if len(member_ids) != len(set(member_ids)):
        raise RealityFoundationError("line_members:duplicate_rider_id")
    if len(member_cars) != len(set(member_cars)):
        raise RealityFoundationError("line_members:duplicate_car_no")
    if set(member_ids) != expected_ids or set(member_cars) != expected_cars:
        raise RealityFoundationError("line_members:must_match_active_riders")

    identity_car = {r.rider_id: r.car_no for r in active_riders}
    groups: dict[str, list[LineMemberSnapshot]] = {}
    for member in line.members:
        _require_nonempty("line_group_id", member.line_group_id)
        if identity_car.get(member.rider_id) != member.car_no:
            raise RealityFoundationError("line_member:rider_car_identity_mismatch")
        if member.line_position < 0:
            raise RealityFoundationError("line_position:negative")
        if member.line_size <= 0:
            raise RealityFoundationError("line_size:invalid")
        if member.is_singleton != (member.line_size == 1):
            raise RealityFoundationError("is_singleton:inconsistent")
        groups.setdefault(member.line_group_id, []).append(member)

    if line.num_lines != len(groups):
        raise RealityFoundationError("num_lines:mismatch")

    for group_id, members in groups.items():
        size = len(members)
        if any(member.line_size != size for member in members):
            raise RealityFoundationError(f"line_size:mismatch:{group_id}")
        positions = sorted(member.line_position for member in members)
        if positions != list(range(size)):
            raise RealityFoundationError(f"line_position:not_contiguous:{group_id}")


def validate_race_pre_snapshot(
    snapshot: RaceRealityPreSnapshot,
    *,
    require_actionable_line: bool = False,
) -> None:
    """Validate a reality-foundation PRE snapshot without generating truth or outcomes.

    This function is intentionally admission-only. It does not infer missing values,
    choose engineering defaults, generate latent state, score a model, or construct an
    ordered-top3 truth distribution.
    """

    validate_program(snapshot.program)
    validate_venue_environment(snapshot.venue_environment, snapshot.program.decision_timestamp)
    if snapshot.venue_environment.venue_id != snapshot.program.venue_id:
        raise RealityFoundationError("venue_id:mismatch_program_environment")

    if not snapshot.riders:
        raise RealityFoundationError("riders:empty")
    for rider in snapshot.riders:
        validate_rider_identity(rider, snapshot.program.decision_timestamp)

    rider_ids = [r.rider_id for r in snapshot.riders]
    car_nos = [r.car_no for r in snapshot.riders]
    if len(rider_ids) != len(set(rider_ids)):
        raise RealityFoundationError("riders:duplicate_rider_id")
    if len(car_nos) != len(set(car_nos)):
        raise RealityFoundationError("riders:duplicate_car_no")

    active_riders = tuple(r for r in snapshot.riders if r.active_status_at_cutoff)
    if len(active_riders) != snapshot.program.field_size:
        raise RealityFoundationError("field_size:active_rider_count_mismatch")

    if len(snapshot.rider_history) != len(active_riders):
        raise RealityFoundationError("rider_history:count_mismatch")
    for history in snapshot.rider_history:
        validate_rider_history(history, snapshot.program.decision_timestamp)
    history_ids = [h.rider_id for h in snapshot.rider_history]
    if len(history_ids) != len(set(history_ids)):
        raise RealityFoundationError("rider_history:duplicate_rider_id")
    if set(history_ids) != {r.rider_id for r in active_riders}:
        raise RealityFoundationError("rider_history:must_match_active_riders")

    if snapshot.program.race_regime == "UNKNOWN_OR_OTHER" and require_actionable_line:
        raise RealityFoundationError("actionable_line:unknown_regime_fail_closed")

    if snapshot.line_snapshot is None:
        if require_actionable_line:
            raise RealityFoundationError("actionable_line:missing_snapshot")
        return

    validate_line_snapshot(
        snapshot.line_snapshot,
        snapshot.program,
        active_riders,
        require_actionable_line=require_actionable_line,
    )


def foundation_capabilities() -> dict[str, object]:
    """Return explicit scope so callers cannot mistake this module for a generator."""
    return {
        "world_family": "REALITY_CALIBRATED_WORLD_FAMILY",
        "foundation_only": True,
        "truth_generator_implemented": False,
        "outcome_generation_implemented": False,
        "latent_state_generation_implemented": False,
        "model_comparison_implemented": False,
        "real_data_collection_implemented": False,
        "engineering_defaults_inherited": False,
        "supports": [
            "program_regime_contract",
            "venue_environment_contract",
            "persistent_rider_identity_contract",
            "point_in_time_PRE_history_contract",
            "mutable_line_snapshot_contract",
            "fail_closed_decision_time_validation",
        ],
    }
