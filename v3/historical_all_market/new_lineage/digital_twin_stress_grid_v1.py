from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Tuple

from digital_twin_v1 import (
    Race,
    Top3,
    _deterministic_shock_utilities,
    _joint_from_utilities,
    _mix_joint,
)


@dataclass(frozen=True)
class StressAssumptions:
    scenario_id: str
    world_family: str
    assurance: str
    line_static_scale: float
    relation_strength: float
    wind_effect_scale: float
    bank_effect_scale: float
    disruption_weight: float
    shock_sigma: float
    shock_temperature: float
    disrupted_relation_strength: float


def _class_term(rider_class: str) -> float:
    return {
        "S1": 0.08,
        "S2": -0.03,
        "A1": 0.05,
        "A2": -0.03,
        "A3": 0.0,
    }[rider_class]


def _base_utility(r, race: Race, cfg: StressAssumptions) -> float:
    style_term = {"逃": 0.06, "両": 0.04, "追": 0.0}[r.style]
    wind_penalty = (
        0.035
        * cfg.wind_effect_scale
        * race.wind_speed_mps
        * (1.0 if r.style == "逃" else 0.25)
    )
    bank_term = (
        0.04 * cfg.bank_effect_scale
        if (race.bank_length_m <= 333 and r.style in {"逃", "両"})
        else 0.0
    )
    return r.latent_skill + _class_term(r.rider_class) + style_term + bank_term - wind_penalty


def _line_strengths(race: Race) -> Dict[int, float]:
    groups: Dict[int, list[float]] = {}
    for r in race.riders:
        groups.setdefault(r.line_id, []).append(r.latent_skill)
    return {line: sum(vals) / len(vals) for line, vals in groups.items()}


def _stable_utilities(race: Race, cfg: StressAssumptions) -> Dict[int, float]:
    line_strength = _line_strengths(race)
    out: Dict[int, float] = {}
    for r in race.riders:
        value = _base_utility(r, race, cfg)
        if cfg.line_static_scale > 0.0:
            pos_bonus = {0: 0.04, 1: 0.10, 2: 0.05}.get(r.line_position, 0.0)
            size_bonus = 0.025 * max(0, r.line_size - 1)
            value += cfg.line_static_scale * (
                0.16 * line_strength[r.line_id] + pos_bonus + size_bonus
            )
        out[r.car_no] = value
    return out


def _no_line_utilities(race: Race, cfg: StressAssumptions) -> Dict[int, float]:
    return {r.car_no: _base_utility(r, race, cfg) for r in race.riders}


def stress_truth_joint(race: Race, cfg: StressAssumptions) -> Dict[Top3, float]:
    """Synthetic truth under an explicitly non-calibrated assumption scenario."""
    stable = _joint_from_utilities(
        race,
        _stable_utilities(race, cfg),
        relation_strength=cfg.relation_strength,
    )
    if cfg.disruption_weight <= 0.0:
        return stable

    disrupted_util = _deterministic_shock_utilities(
        race,
        _no_line_utilities(race, cfg),
        sigma=cfg.shock_sigma,
        temperature=cfg.shock_temperature,
        tag=f"{cfg.scenario_id}-shock",
    )
    disrupted = _joint_from_utilities(
        race,
        disrupted_util,
        relation_strength=cfg.disrupted_relation_strength,
    )
    return _mix_joint(stable, disrupted, weight_b=cfg.disruption_weight)


# Every value below is an engineering stress assumption, not a measured real-keirin
# coefficient or frequency. These ten scenarios are now LOCKED LEGACY SYNTHETIC HOLDOUT
# diagnostics: they may be re-evaluated after a new model is frozen, but they must not be
# used to fit or retune C1/N1 coefficients.
ASSUMPTION_GRID: Tuple[StressAssumptions, ...] = (
    StressAssumptions(
        "W0_NULL_CONTEXT", "W0", "ASSUMPTION_RANGE_ONLY",
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0,
    ),
    StressAssumptions(
        "W0_CONTEXT_MODERATE", "W0", "ASSUMPTION_RANGE_ONLY",
        0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 0.0,
    ),
    StressAssumptions(
        "W1_STATIC_LINE_WEAK", "W1", "ASSUMPTION_RANGE_ONLY",
        0.50, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 0.0,
    ),
    StressAssumptions(
        "W1_STATIC_LINE_STRONG", "W1", "ASSUMPTION_RANGE_ONLY",
        1.50, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 0.0,
    ),
    StressAssumptions(
        "W2_CONDITIONAL_LINE_WEAK", "W2", "ASSUMPTION_RANGE_ONLY",
        0.75, 0.50, 1.0, 1.0, 0.0, 0.0, 1.0, 0.0,
    ),
    StressAssumptions(
        "W2_CONDITIONAL_LINE_STRONG", "W2", "ASSUMPTION_RANGE_ONLY",
        1.25, 1.50, 1.0, 1.0, 0.0, 0.0, 1.0, 0.0,
    ),
    StressAssumptions(
        "W3_DISRUPTION_LOW", "W3", "ASSUMPTION_RANGE_ONLY",
        1.0, 1.0, 1.0, 1.0, 0.15, 0.35, 1.10, 0.15,
    ),
    StressAssumptions(
        "W3_DISRUPTION_HIGH", "W3", "ASSUMPTION_RANGE_ONLY",
        1.0, 1.0, 1.0, 1.0, 0.45, 0.75, 1.25, 0.10,
    ),
    StressAssumptions(
        "W4_HEAVY_TAIL_MODERATE", "W4", "ASSUMPTION_RANGE_ONLY",
        0.70, 0.50, 1.0, 1.0, 0.35, 0.90, 1.50, 0.0,
    ),
    StressAssumptions(
        "W4_HEAVY_TAIL_SEVERE", "W4", "ASSUMPTION_RANGE_ONLY",
        0.40, 0.20, 1.5, 1.0, 0.55, 1.25, 1.90, 0.0,
    ),
)


def validate_assumption_grid(
    grid: Tuple[StressAssumptions, ...] = ASSUMPTION_GRID,
) -> None:
    ids = [x.scenario_id for x in grid]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_stress_scenario_id")

    families = {x.world_family for x in grid}
    if families != {"W0", "W1", "W2", "W3", "W4"}:
        raise ValueError(f"world_family_coverage_failed:{sorted(families)}")

    by_family = {f: 0 for f in families}
    for cfg in grid:
        by_family[cfg.world_family] += 1
        if cfg.assurance != "ASSUMPTION_RANGE_ONLY":
            raise ValueError(f"scenario_not_labeled_assumption:{cfg.scenario_id}")
        if cfg.line_static_scale < 0.0 or cfg.relation_strength < 0.0:
            raise ValueError(f"negative_line_parameter:{cfg.scenario_id}")

        # Bank/wind stress is explicitly allowed to be signed. The calibration registry
        # requires signed / near-zero / moderate worlds; negative scale means an engineering
        # reversal stress, not a claim that the real causal effect is negative.
        for name, value in (
            ("wind_effect_scale", cfg.wind_effect_scale),
            ("bank_effect_scale", cfg.bank_effect_scale),
        ):
            if not math.isfinite(value) or abs(value) > 3.0:
                raise ValueError(f"invalid_signed_context_parameter:{cfg.scenario_id}:{name}")

        if not (0.0 <= cfg.disruption_weight <= 1.0):
            raise ValueError(f"invalid_disruption_weight:{cfg.scenario_id}")
        if cfg.shock_sigma < 0.0 or cfg.shock_temperature <= 0.0:
            raise ValueError(f"invalid_shock_parameter:{cfg.scenario_id}")
        if cfg.disrupted_relation_strength < 0.0:
            raise ValueError(f"invalid_disrupted_relation_strength:{cfg.scenario_id}")

    if any(n < 2 for n in by_family.values()):
        raise ValueError(f"insufficient_range_per_world:{by_family}")
