from __future__ import annotations

from dataclasses import replace

from broad_stress_fast_kernel_v1 import stress_truth_array
from digital_twin_stress_grid_v1 import StressAssumptions
from digital_twin_v1 import Race

COMMON_SHOCK_SCENARIO_TAG = "CONTINUOUS_SURFACE_COMMON_SHOCK_V1"


def continuous_surface_truth_array(race: Race, cfg: StressAssumptions):
    """Evaluate the existing locked synthetic truth formula with common shock draws.

    The parent fast kernel seeds deterministic shock residuals from scenario_id,
    race_id and car number. A continuous sensitivity surface needs parameter points
    to share the same underlying residual draw so differences are driven by the
    assumption coordinates rather than by a different shock direction per point.

    Therefore only the internal shock-seed tag is replaced by one fixed surface tag.
    All numeric truth parameters, race state and the parent truth formula remain
    unchanged. The returned object is still synthetic engineering truth only.
    """
    if cfg.assurance != "ASSUMPTION_RANGE_ONLY":
        raise ValueError("continuous_surface_truth_requires_assumption_range_label")
    fixed_tag_cfg = replace(cfg, scenario_id=COMMON_SHOCK_SCENARIO_TAG)
    return stress_truth_array(race, fixed_tag_cfg)
