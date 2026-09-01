from __future__ import annotations

import copy
import json
from pathlib import Path

from reality_numeric_calibration_v0 import NumericCalibrationError, NumericCalibrationRegistry
from reality_truth_generator_scaffold_v0 import (
    TruthExecutionBlocked,
    build_rider_prototype,
    finish_order,
    validate_line_partition,
)


REGISTRY = Path("v3/historical_all_market/research_candidates/KEIRIN_REALITY_NUMERIC_CALIBRATION_REGISTRY_20260901_v1.json")


def must_fail(fn, exc_type):
    try:
        fn()
    except exc_type:
        return
    raise AssertionError("expected failure")


def main() -> None:
    raw = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry = NumericCalibrationRegistry(raw)
    assert registry.tactical_numeric_available() is False

    assert abs(registry.score("S1", 0.5) - 106.69) < 1e-9
    assert abs(registry.score("A3", 0.5) - 72.24) < 1e-9
    assert registry.score("S1", 0.0) == 102.549
    assert registry.score("S1", 1.0) == 111.652
    assert registry.score("A2", 0.0, "stress") == 70.0
    assert registry.score("A2", 1.0, "stress") == 88.8

    assert registry.style_feature("逃", "B", 0.5) == 8.5
    assert registry.style_feature("追", "B", 0.5) == 0.0
    assert registry.style_feature("両", "makuri", 0.5) == 1.0

    rider = build_rider_prototype(
        registry,
        "R-TEST",
        "A1",
        "逃",
        {"score":0.5,"B":0.5,"S":0.5,"nige":0.5,"makuri":0.5,"sashi":0.5,"mark":0.5},
    )
    assert rider.competition_score == 90.0
    assert rider.B == 8.5

    assert validate_line_partition((1,2,3,4,5,6,7), ((1,2,3,4),(5,6,7))) == (4,3)
    assert validate_line_partition((1,2,3,4,5,6,7), ((1,2,3),(4,5),(6,7))) == (3,2,2)
    must_fail(lambda: validate_line_partition((1,2,3,4,5,6,7), ((1,2,3),(4,5),(6,))), NumericCalibrationError)

    bad = copy.deepcopy(raw)
    bad["tactical_numeric_status"]["switching_probability"] = 0.2
    must_fail(lambda: NumericCalibrationRegistry(bad), NumericCalibrationError)
    must_fail(lambda: registry.score("A1", 1.2), NumericCalibrationError)
    must_fail(lambda: finish_order(), TruthExecutionBlocked)

    print("PASS_REALITY_NUMERIC_CALIBRATION_SCAFFOLD_V0")


if __name__ == "__main__":
    main()
