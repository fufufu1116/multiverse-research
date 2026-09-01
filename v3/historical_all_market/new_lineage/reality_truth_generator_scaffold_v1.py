"""Reality world scaffold with PRE tactical evidence attached to synthetic actors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from reality_numeric_calibration_v0 import NumericCalibrationRegistry
from reality_pre_tactical_propensity_v0 import (
    TacticalEvidenceProfile,
    TacticalPropensityError,
    build_tactical_evidence_profile,
)
from reality_truth_generator_scaffold_v0 import (
    RealityWorldScaffold,
    RiderPrototype,
    TruthExecutionBlocked,
    build_rider_prototype,
    validate_line_partition,
)


@dataclass(frozen=True)
class RealityActorState:
    rider: RiderPrototype
    tactical_evidence: TacticalEvidenceProfile
    expected_line_position: int
    evidence_tags: tuple[str, ...]


def build_actor_state(
    numeric_registry: NumericCalibrationRegistry,
    tactical_registry: Mapping[str, object],
    rider_id: str,
    class_band: str,
    style: str,
    coordinates: Mapping[str, float],
    *,
    expected_line_position: int,
    mode: str = "central",
) -> RealityActorState:
    rider = build_rider_prototype(
        numeric_registry,
        rider_id,
        class_band,
        style,
        coordinates,
        mode,
    )
    tactical = build_tactical_evidence_profile(
        tactical_registry,
        rider_id,
        class_band,
        style,
        ST=rider.S,
        BK=rider.B,
        nige=rider.nige,
        makuri=rider.makuri,
        sashi=rider.sashi,
        mark=rider.mark,
    )
    tags = tactical.evidence_tags_for_expected_line_position(expected_line_position)
    return RealityActorState(rider, tactical, expected_line_position, tags)


def supported_action_families(actor: RealityActorState) -> tuple[str, ...]:
    """Return possible action families supported by actor role/history, without rates."""
    if actor.expected_line_position < 0:
        raise TacticalPropensityError("expected_line_position must be nonnegative")
    actions = {"MAINTAIN_POSITION", "FINAL_SPRINT"}
    if actor.expected_line_position == 0:
        actions.add("INITIATE_PACE")
        actions.add("RESPOND_TO_INITIATIVE_CONFLICT")
    else:
        actions.add("FOLLOW_EXPECTED_LINE")
        actions.add("POSITION_DEFENSE")
        actions.add("SWITCH_IF_LINE_LOST")
    if "STYLE_SUPPORTS_SELF_POWERED_ACTION" in actor.evidence_tags:
        actions.add("SELF_POWERED_ATTACK")
    if "STYLE_SUPPORTS_FOLLOWING_ACTION" in actor.evidence_tags:
        actions.add("FOLLOW_OR_CHASE")
    if "PRE_HISTORY_SUPPORTS_EARLY_FRONT_POSITION" in actor.evidence_tags:
        actions.add("SEEK_EARLY_FRONT_POSITION")
    if "PRE_HISTORY_SUPPORTS_LATE_FRONT_EXPOSURE" in actor.evidence_tags:
        actions.add("SUSTAIN_FRONT_EXPOSURE_SCENARIO")
    return tuple(sorted(actions))


def validate_world_inputs(
    world: RealityWorldScaffold,
    active_car_numbers: Sequence[int],
    groups: Sequence[Sequence[int]],
    actors_by_car: Mapping[int, RealityActorState],
) -> tuple[int, ...]:
    shape = validate_line_partition(active_car_numbers, groups)
    if set(actors_by_car) != set(active_car_numbers):
        raise TacticalPropensityError("exactly one actor state required for each active car")
    for group in groups:
        for pos, car in enumerate(group):
            actor = actors_by_car[car]
            if actor.expected_line_position != pos:
                raise TacticalPropensityError("actor expected-line position inconsistent with partition")
    _ = world
    return shape


def finish_order(*_args: object, **_kwargs: object) -> tuple[int, ...]:
    raise TruthExecutionBlocked("finish generation remains blocked until tactical event-rate evidence is admitted")
