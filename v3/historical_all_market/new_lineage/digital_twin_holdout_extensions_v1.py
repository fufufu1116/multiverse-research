from __future__ import annotations

import math
from typing import Dict, Mapping

from digital_twin_v1 import Race, Top3
from digital_twin_stress_grid_v1 import (
    StressAssumptions,
    _stable_utilities,
    stress_truth_joint,
)

SIGNED_CONTEXT_REVERSAL = StressAssumptions(
    scenario_id="HX_SIGNED_BANK_WIND_REVERSAL",
    world_family="HX_SIGNED_CONTEXT",
    assurance="ASSUMPTION_RANGE_ONLY",
    line_static_scale=0.80,
    relation_strength=0.35,
    wind_effect_scale=-1.00,
    bank_effect_scale=-1.00,
    disruption_weight=0.00,
    shock_sigma=0.00,
    shock_temperature=1.00,
    disrupted_relation_strength=0.00,
)

ALTERNATE_CONDITIONAL_ID = "HX_ALTERNATE_CONDITIONAL_CROSS_LINE_ANTI_CHAIN"


def _softmax(values: Mapping[int, float]) -> Dict[int, float]:
    if not values:
        raise ValueError("empty_softmax")
    if not all(math.isfinite(float(v)) for v in values.values()):
        raise ValueError("nonfinite_softmax_input")
    m = max(float(v) for v in values.values())
    ex = {k: math.exp(float(v) - m) for k, v in values.items()}
    z = sum(ex.values())
    if not math.isfinite(z) or z <= 0.0:
        raise ValueError("invalid_softmax_mass")
    return {k: v / z for k, v in ex.items()}


def signed_context_reversal_joint(race: Race) -> Dict[Top3, float]:
    """Fresh Lab-prescribed signed bank/wind reversal stress.

    Negative context scales are engineering reversal stresses only. They are not claims that
    real bank/wind effects have those signs or magnitudes.
    """
    return stress_truth_joint(race, SIGNED_CONTEXT_REVERSAL)


def alternate_conditional_joint(race: Race) -> Dict[Top3, float]:
    """Non-mirroring conditional truth family for architecture robustness.

    Unlike the legacy W2 truth, this mechanism does NOT reward the N1 proxy's specific
    same-line/follower/forward-chain motif. Rank-2 and rank-3 instead emphasize cross-line
    diversification, head-position candidates, and explicit penalty of the standard forward
    same-line chain. It therefore tests whether conditional architecture generalizes beyond
    a truth generator that resembles its hand-coded features.

    This is synthetic engineering truth only, not a real-keirin mechanism claim.
    """
    base_cfg = StressAssumptions(
        scenario_id=ALTERNATE_CONDITIONAL_ID,
        world_family="HX_ALT_CONDITIONAL",
        assurance="ASSUMPTION_RANGE_ONLY",
        line_static_scale=0.65,
        relation_strength=0.00,
        wind_effect_scale=1.00,
        bank_effect_scale=1.00,
        disruption_weight=0.00,
        shock_sigma=0.00,
        shock_temperature=1.00,
        disrupted_relation_strength=0.00,
    )
    util = _stable_utilities(race, base_cfg)
    riders = {r.car_no: r for r in race.riders}
    cars = list(riders)
    p1 = _softmax(util)
    joint: Dict[Top3, float] = {}

    for first in cars:
        rf = riders[first]
        second_logits: Dict[int, float] = {}
        for candidate in cars:
            if candidate == first:
                continue
            rc = riders[candidate]
            cross_line = float(rc.line_id != rf.line_id)
            candidate_head = float(rc.line_position == 0)
            standard_follower = float(
                rc.line_id == rf.line_id
                and rc.line_position == rf.line_position + 1
            )
            second_logits[candidate] = (
                util[candidate]
                + 0.24 * cross_line
                + 0.10 * candidate_head
                - 0.14 * standard_follower
            )
        p2 = _softmax(second_logits)

        for second in second_logits:
            rs = riders[second]
            third_logits: Dict[int, float] = {}
            for candidate in cars:
                if candidate in (first, second):
                    continue
                rc = riders[candidate]
                new_line = float(
                    rc.line_id != rf.line_id and rc.line_id != rs.line_id
                )
                candidate_head = float(rc.line_position == 0)
                standard_chain = float(
                    rf.line_id == rs.line_id == rc.line_id
                    and rf.line_position < rs.line_position < rc.line_position
                )
                position_inversion = float(
                    rc.line_id == rs.line_id
                    and rc.line_position < rs.line_position
                )
                third_logits[candidate] = (
                    util[candidate]
                    + 0.26 * new_line
                    + 0.08 * candidate_head
                    + 0.12 * position_inversion
                    - 0.20 * standard_chain
                )
            p3 = _softmax(third_logits)

            for third in third_logits:
                joint[(first, second, third)] = (
                    p1[first] * p2[second] * p3[third]
                )

    z = sum(joint.values())
    if not math.isfinite(z) or z <= 0.0:
        raise ValueError("alternate_conditional_invalid_mass")
    joint = {k: v / z for k, v in joint.items()}
    if abs(sum(joint.values()) - 1.0) > 1e-10:
        raise ValueError("alternate_conditional_mass_mismatch")
    return joint


def validate_holdout_extensions(race: Race) -> None:
    signed = signed_context_reversal_joint(race)
    alternate = alternate_conditional_joint(race)
    for name, obj in (
        (SIGNED_CONTEXT_REVERSAL.scenario_id, signed),
        (ALTERNATE_CONDITIONAL_ID, alternate),
    ):
        if abs(sum(obj.values()) - 1.0) > 1e-10:
            raise ValueError(f"holdout_extension_mass_failed:{name}")
        if any(p < 0.0 or not math.isfinite(p) for p in obj.values()):
            raise ValueError(f"holdout_extension_probability_failed:{name}")
