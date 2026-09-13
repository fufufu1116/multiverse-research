from __future__ import annotations

import math
import random
from statistics import pstdev
from typing import Dict, Mapping

import digital_twin_v1 as v1

Top3 = tuple[int, int, int]


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _sigmoid(value: float) -> float:
    if value >= 0.0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def pre_mechanism_signal(pre: Mapping[str, object]) -> float:
    """Deterministic mechanism signal from ordinary PRE observables only.

    This is deliberately not a regime label. It is a fixed synthetic construction used to
    make mechanism intensity learnable from PRE in Digital Twin v2. Do not change coefficients
    after synthetic outcomes are observed.
    """
    riders = list(pre["riders"])
    if not riders:
        raise ValueError("empty_riders")
    wind = float(pre["wind_speed_mps"])
    line_ids = {int(r["line_group_id"]) for r in riders}
    scores = [float(r["score"]) for r in riders]
    score_std = pstdev(scores)

    wind_term = 0.65 * _clip((wind - 2.2) / 1.5, -2.0, 2.0)
    line_term = 0.45 * (float(len(line_ids)) - 3.0)
    uncertainty_term = 0.50 * _clip(score_std - 1.0, -1.5, 1.5)
    return wind_term + line_term + uncertainty_term


def hidden_mechanism_alpha(pre: Mapping[str, object]) -> float:
    """Scoring-only synthetic truth parameter. Never expose as predictor input."""
    return _sigmoid(-0.30 + pre_mechanism_signal(pre))


def _mix_joint(a: Mapping[Top3, float], b: Mapping[Top3, float], weight_b: float) -> Dict[Top3, float]:
    if not (0.0 <= weight_b <= 1.0):
        raise ValueError("invalid_mix_weight")
    if set(a) != set(b):
        raise ValueError("support_mismatch")
    out = {k: (1.0 - weight_b) * float(a[k]) + weight_b * float(b[k]) for k in a}
    mass = sum(out.values())
    if abs(mass - 1.0) > 1e-10:
        raise ValueError(f"mixture_mass_mismatch:{mass}")
    return out


def learnable_regime_oracle(race: v1.Race) -> tuple[Dict[Top3, float], float]:
    pre = v1.pre_view(race)
    alpha = hidden_mechanism_alpha(pre)
    w0 = v1.world_joint_distribution(race, "W0")
    w2 = v1.world_joint_distribution(race, "W2")
    return _mix_joint(w0, w2, alpha), alpha


def generate_batch(seed: int, n_races: int) -> list[dict[str, object]]:
    """Generate PRE plus scoring-only hidden truth for learnable-regime synthetic tests."""
    if n_races <= 0:
        raise ValueError("nonpositive_n_races")
    outcome_rng = random.Random(seed + 62000)
    out: list[dict[str, object]] = []
    for idx in range(n_races):
        race = v1.generate_race(seed=seed, race_index=idx, event_format="STANDARD_FI_FII_7")
        pre = v1.pre_view(race)
        oracle, alpha = learnable_regime_oracle(race)
        outcome = v1.sample_top3(oracle, outcome_rng)
        out.append({
            "pre": pre,
            "outcome_top3": outcome,
            "oracle_joint": oracle,
            "_scoring_only_hidden": {
                "mechanism_alpha": alpha,
                "pre_mechanism_signal": pre_mechanism_signal(pre),
            },
        })
    return out


def selftest() -> None:
    batch = generate_batch(seed=20260913, n_races=12)
    if len(batch) != 12:
        raise AssertionError("batch_size")
    for row in batch:
        pre = row["pre"]
        if "mechanism_alpha" in pre or "pre_mechanism_signal" in pre:
            raise AssertionError("hidden_regime_leaked_into_pre")
        oracle = row["oracle_joint"]
        if abs(sum(oracle.values()) - 1.0) > 1e-10:
            raise AssertionError("oracle_mass")
        alpha = float(row["_scoring_only_hidden"]["mechanism_alpha"])
        if not (0.0 < alpha < 1.0):
            raise AssertionError("alpha_bounds")
    print("LEARNABLE_REGIME_DIGITAL_TWIN_V2_SELFTEST_PASS")


if __name__ == "__main__":
    selftest()
