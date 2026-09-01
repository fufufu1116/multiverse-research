from __future__ import annotations

import json
from pathlib import Path

from reality_numeric_calibration_v0 import NumericCalibrationRegistry
from reality_pre_tactical_propensity_v0 import (
    TacticalPropensityError,
    build_tactical_evidence_profile,
    event_probability,
    ordinal_band,
    successful_finish_lean,
    successful_finish_technique_mix,
)
from reality_truth_generator_scaffold_v0 import RealityWorldScaffold, TruthExecutionBlocked
from reality_truth_generator_scaffold_v1 import (
    build_actor_state,
    finish_order,
    supported_action_families,
    validate_world_inputs,
)


ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "research_candidates"


def _load(name: str):
    return json.loads((CAND / name).read_text(encoding="utf-8"))


def _must_raise(exc_type, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__}")


def main() -> None:
    tactical = _load("KEIRIN_REALITY_PRE_TACTICAL_PROPENSITY_REGISTRY_20260901_v1.json")
    numeric_raw = _load("KEIRIN_REALITY_NUMERIC_CALIBRATION_REGISTRY_20260901_v1.json")
    numeric = NumericCalibrationRegistry(numeric_raw)

    assert ordinal_band(tactical, "A1", "ST", 0) == "VERY_LOW"
    assert ordinal_band(tactical, "A1", "ST", 1) == "LOW"
    assert ordinal_band(tactical, "A1", "ST", 3) == "MID"
    assert ordinal_band(tactical, "A1", "ST", 8) == "HIGH"
    assert ordinal_band(tactical, "A1", "ST", 10) == "VERY_HIGH"
    _must_raise(TacticalPropensityError, ordinal_band, tactical, "A1", "unknown", 1)

    mix = successful_finish_technique_mix(4, 2, 1, 1)
    assert mix is not None and abs(sum(mix.values()) - 1.0) < 1e-12
    assert successful_finish_lean(4, 2, 1, 1) == "SELF_POWERED_LEAN"
    assert successful_finish_lean(0, 0, 2, 2) == "FOLLOWING_LEAN"
    assert successful_finish_lean(1, 1, 1, 1) == "BALANCED"
    assert successful_finish_lean(0, 0, 0, 0) == "NO_SIGNAL"
    assert successful_finish_technique_mix(0, 0, 0, 0) is None

    profile = build_tactical_evidence_profile(
        tactical,
        "R1",
        "A1",
        "逃",
        ST=8,
        BK=10,
        nige=5,
        makuri=2,
        sashi=0,
        mark=0,
    )
    assert "PRE_HISTORY_SUPPORTS_EARLY_FRONT_POSITION" in profile.evidence_tags_for_expected_line_position(0)
    assert "PRE_HISTORY_SUPPORTS_LATE_FRONT_EXPOSURE" in profile.evidence_tags_for_expected_line_position(0)
    assert profile.successful_technique_lean == "SELF_POWERED_LEAN"

    coords = {"score": 0.6, "B": 0.8, "S": 0.8, "nige": 0.8, "makuri": 0.6, "sashi": 0.2, "mark": 0.2}
    a1 = build_actor_state(numeric, tactical, "R1", "A1", "逃", coords, expected_line_position=0)
    a2 = build_actor_state(numeric, tactical, "R2", "A2", "追", coords, expected_line_position=1)
    a3 = build_actor_state(numeric, tactical, "R3", "A2", "追", coords, expected_line_position=2)
    a4 = build_actor_state(numeric, tactical, "R4", "A1", "逃", coords, expected_line_position=0)
    a5 = build_actor_state(numeric, tactical, "R5", "A2", "追", coords, expected_line_position=1)
    a6 = build_actor_state(numeric, tactical, "R6", "A1", "逃", coords, expected_line_position=0)
    a7 = build_actor_state(numeric, tactical, "R7", "A2", "追", coords, expected_line_position=1)
    assert "INITIATE_PACE" in supported_action_families(a1)
    assert "FOLLOW_EXPECTED_LINE" in supported_action_families(a2)

    world = RealityWorldScaffold("T1_BALANCED_TACTICAL")
    shape = validate_world_inputs(
        world,
        [1, 2, 3, 4, 5, 6, 7],
        [[1, 2, 3], [4, 5], [6, 7]],
        {1: a1, 2: a2, 3: a3, 4: a4, 5: a5, 6: a6, 7: a7},
    )
    assert shape == (3, 2, 2)

    _must_raise(TacticalPropensityError, event_probability, profile)
    _must_raise(TruthExecutionBlocked, finish_order, world)

    print("PASS: PRE tactical propensity foundation remains ordinal and non-outcome")


if __name__ == "__main__":
    main()
