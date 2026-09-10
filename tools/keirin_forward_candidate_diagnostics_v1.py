#!/usr/bin/env python3
"""Non-decision-changing diagnostics for the KEIRIN forward candidate lane.

This module does not fetch racecards, odds, results, or payouts. It does not
place bets. It only exposes algebraic diagnostics implied by already-frozen
research rules so those implications can be replayed exactly.

Authority is unchanged:
- the forward prespec and price gate v2 remain the decision authority;
- these helpers must not retune or reinterpret an already-frozen observation.
"""

from math import isfinite

CORE_MIN_MULTIPLE = 1.10
CORE_MAX_ODDS = 20.0


class CandidateDiagnosticError(ValueError):
    pass


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CandidateDiagnosticError(f"{label}_must_be_numeric")
    x = float(value)
    if not isfinite(x):
        raise CandidateDiagnosticError(f"{label}_must_be_finite")
    return x


def _probability(value, label="probability"):
    x = _finite_number(value, label)
    if not (0.0 < x <= 1.0):
        raise CandidateDiagnosticError(f"{label}_must_be_in_(0,1]")
    return x


def core_feasibility_floor(
    min_multiple=CORE_MIN_MULTIPLE,
    max_core_odds=CORE_MAX_ODDS,
):
    """Minimum ticket probability that can qualify anywhere inside CORE."""
    multiple = _finite_number(min_multiple, "min_multiple")
    max_odds = _finite_number(max_core_odds, "max_core_odds")
    if multiple <= 0.0:
        raise CandidateDiagnosticError("min_multiple_must_be_positive")
    if max_odds < 1.0:
        raise CandidateDiagnosticError("max_core_odds_must_be_at_least_1")
    return multiple / max_odds


def minimum_core_odds(
    probability,
    min_multiple=CORE_MIN_MULTIPLE,
    max_core_odds=CORE_MAX_ODDS,
):
    """Return exact minimum CORE odds and whether CORE qualification is possible."""
    p = _probability(probability)
    multiple = _finite_number(min_multiple, "min_multiple")
    max_odds = _finite_number(max_core_odds, "max_core_odds")
    if multiple <= 0.0:
        raise CandidateDiagnosticError("min_multiple_must_be_positive")
    if max_odds < 1.0:
        raise CandidateDiagnosticError("max_core_odds_must_be_at_least_1")
    threshold = multiple / p
    return {
        "probability": p,
        "minimum_odds": threshold,
        "max_core_odds": max_odds,
        "core_possible": bool(threshold <= max_odds),
    }


def paired_value_thresholds_are_redundant(
    minimum_probability_multiple,
    minimum_expected_roi,
    *,
    tolerance=1e-12,
):
    """Check whether the two numeric gates are algebraically the same cutoff.

    probability_multiple = p * odds
    expected_roi = p * odds - 1
    They are the same cutoff iff min_multiple == 1 + min_expected_roi.
    """
    multiple = _finite_number(
        minimum_probability_multiple, "minimum_probability_multiple"
    )
    ev = _finite_number(minimum_expected_roi, "minimum_expected_roi")
    tol = _finite_number(tolerance, "tolerance")
    if tol < 0.0:
        raise CandidateDiagnosticError("tolerance_must_be_nonnegative")
    return abs(multiple - (1.0 + ev)) <= tol


def fallback_pairwise_score_equivalent(
    style_deltas,
    beta,
    *,
    q_abs=1.0,
):
    """Maximum pairwise fallback perturbation expressed in score points."""
    if not style_deltas:
        raise CandidateDiagnosticError("style_deltas_must_not_be_empty")
    ds = [_finite_number(x, "style_delta") for x in style_deltas]
    b = _finite_number(beta, "beta")
    q = _finite_number(q_abs, "q_abs")
    if b <= 0.0:
        raise CandidateDiagnosticError("beta_must_be_positive")
    if q < 0.0:
        raise CandidateDiagnosticError("q_abs_must_be_nonnegative")
    logit_spread = (max(ds) - min(ds)) * q
    return {
        "max_pairwise_logit_spread": logit_spread,
        "equivalent_score_points": logit_spread / b,
    }


def equal_stake_uniform_minimum_odds(
    ticket_probabilities,
    *,
    required_roi=0.10,
):
    """Uniform odds needed for an equal-stake N-ticket set at target ROI."""
    if not ticket_probabilities:
        raise CandidateDiagnosticError("ticket_probabilities_must_not_be_empty")
    ps = [_probability(x, "ticket_probability") for x in ticket_probabilities]
    roi = _finite_number(required_roi, "required_roi")
    if roi <= -1.0:
        raise CandidateDiagnosticError("required_roi_must_be_greater_than_-1")
    return len(ps) * (1.0 + roi) / sum(ps)


def lower_probability_addition_dilutes_uniform_screen(
    best_ticket_probability,
    added_ticket_probability,
    *,
    required_roi=0.10,
):
    """True when adding a lower-probability ticket worsens uniform-odds screening."""
    best = _probability(best_ticket_probability, "best_ticket_probability")
    added = _probability(added_ticket_probability, "added_ticket_probability")
    single = equal_stake_uniform_minimum_odds([best], required_roi=required_roi)
    pair = equal_stake_uniform_minimum_odds(
        [best, added], required_roi=required_roi
    )
    return {
        "single_ticket_uniform_minimum_odds": single,
        "two_ticket_uniform_minimum_odds": pair,
        "dilutes": bool(pair > single),
        "added_probability_lower_than_best": bool(added < best),
    }
