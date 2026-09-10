#!/usr/bin/env python3
"""PRE-only fallback top1 robustness diagnostic for KEIRIN research.

This module does not fit a model, fetch data, inspect results/payouts/odds, or
change any purchase decision. It proves whether the S0 top1 identity is stable
against the full supported style-fallback correction range for |q| <= a fixed
bound.

For S0 z_i = beta * score_i and fallback z_i = beta*score_i + q*delta_i,
the largest possible pairwise fallback perturbation is
|q| * (max(delta) - min(delta)). Therefore a positive S0 score gap larger than
that perturbation divided by beta is sufficient to make the top1 identity
invariant to any supported fallback-style assignment.
"""

from math import isfinite
from typing import Mapping


class FallbackTop1RobustnessError(ValueError):
    pass


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FallbackTop1RobustnessError(f"{label}_must_be_numeric")
    x = float(value)
    if not isfinite(x):
        raise FallbackTop1RobustnessError(f"{label}_must_be_finite")
    return x


def required_score_gap(beta, delta_min, delta_max, abs_q_bound=1.0):
    b = _finite_number(beta, "beta")
    lo = _finite_number(delta_min, "delta_min")
    hi = _finite_number(delta_max, "delta_max")
    q = _finite_number(abs_q_bound, "abs_q_bound")
    if b <= 0.0:
        raise FallbackTop1RobustnessError("beta_must_be_positive")
    if hi < lo:
        raise FallbackTop1RobustnessError("delta_max_must_be_at_least_delta_min")
    if q < 0.0:
        raise FallbackTop1RobustnessError("abs_q_bound_must_be_nonnegative")
    return q * (hi - lo) / b


def evaluate_top1_robustness(
    scores: Mapping[int, float],
    *,
    beta,
    delta_min,
    delta_max,
    abs_q_bound=1.0,
):
    if not isinstance(scores, Mapping) or len(scores) < 2:
        raise FallbackTop1RobustnessError("at_least_two_scores_required")

    clean = {}
    for car, score in scores.items():
        if isinstance(car, bool) or not isinstance(car, int) or car < 1:
            raise FallbackTop1RobustnessError("car_numbers_must_be_positive_integers")
        clean[car] = _finite_number(score, f"score_car_{car}")

    b = _finite_number(beta, "beta")
    lo = _finite_number(delta_min, "delta_min")
    hi = _finite_number(delta_max, "delta_max")
    q = _finite_number(abs_q_bound, "abs_q_bound")
    threshold = required_score_gap(b, lo, hi, q)

    ranked = sorted(clean.items(), key=lambda kv: (-kv[1], kv[0]))
    top_car, top_score = ranked[0]
    second_car, second_score = ranked[1]
    score_gap = top_score - second_score
    fallback_spread = q * (hi - lo)
    base_logit_gap = b * score_gap
    worst_case_logit_margin = base_logit_gap - fallback_spread
    robust = score_gap > 0.0 and worst_case_logit_margin > 0.0

    return {
        "top_car": top_car,
        "second_car": second_car,
        "top_score": top_score,
        "second_score": second_score,
        "score_gap": score_gap,
        "required_score_gap": threshold,
        "base_logit_gap": base_logit_gap,
        "worst_case_fallback_pairwise_logit_spread": fallback_spread,
        "worst_case_logit_margin": worst_case_logit_margin,
        "robust_top1_under_supported_fallback": robust,
        "interpretation": (
            "TOP1_INVARIANT_UNDER_SUPPORTED_FALLBACK_BOUND"
            if robust
            else "TOP1_NOT_PROVEN_INVARIANT_UNDER_SUPPORTED_FALLBACK_BOUND"
        ),
        "decision_rule_changed": False,
        "profitability_evidence": False,
    }
