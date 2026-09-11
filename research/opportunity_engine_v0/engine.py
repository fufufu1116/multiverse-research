from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from .model import Decision, OpportunityCandidate, RevenueRoute


@dataclass(frozen=True)
class Evaluation:
    decision: Decision
    score: int
    revenue_route: RevenueRoute
    reasons: Tuple[str, ...]
    hard_failures: Tuple[str, ...]


def _weighted(value: int, weight: float) -> float:
    return (value / 5.0) * weight


def simulate_unit_economics(
    *,
    visitors: int,
    conversion_rate: float,
    profit_per_conversion_yen: float,
    ad_revenue_per_1000_visitors_yen: float = 0.0,
    variable_cost_per_visitor_yen: float = 0.0,
    fixed_cost_yen: float = 0.0,
) -> Dict[str, float]:
    if visitors < 0:
        raise ValueError("visitors must be non-negative")
    if not 0.0 <= conversion_rate <= 1.0:
        raise ValueError("conversion_rate must be between 0 and 1")
    if min(profit_per_conversion_yen, ad_revenue_per_1000_visitors_yen, variable_cost_per_visitor_yen, fixed_cost_yen) < 0:
        raise ValueError("economic inputs must be non-negative")
    conversions = visitors * conversion_rate
    conversion_profit = conversions * profit_per_conversion_yen
    advertising_profit = (visitors / 1000.0) * ad_revenue_per_1000_visitors_yen
    variable_cost = visitors * variable_cost_per_visitor_yen
    total_profit = conversion_profit + advertising_profit - variable_cost - fixed_cost_yen
    return {"visitors": float(visitors), "conversions": conversions, "conversion_profit_yen": conversion_profit, "advertising_profit_yen": advertising_profit, "variable_cost_yen": variable_cost, "fixed_cost_yen": fixed_cost_yen, "profit_yen": total_profit}


def choose_revenue_route(candidate: OpportunityCandidate) -> RevenueRoute:
    short_lived = candidate.demand_life_days is not None and candidate.demand_life_days <= 60
    scores = {
        RevenueRoute.ADVERTISING: candidate.attention * 2 + (3 if short_lived else 0),
        RevenueRoute.AFFILIATE: candidate.purchase_intent * 2 + candidate.distribution,
        RevenueRoute.ONE_TIME: candidate.buyer_clarity + candidate.purchase_intent + candidate.why_now,
        RevenueRoute.SUBSCRIPTION: candidate.reusable_asset * 2 + candidate.buyer_clarity + (0 if short_lived else 3),
        RevenueRoute.TRANSACTION_FEE: candidate.purchase_intent + candidate.action_completion * 2 + candidate.buyer_clarity,
        RevenueRoute.INTERNAL_ASSET: candidate.proprietary_edge * 2 + candidate.reusable_asset * 2 + candidate.why_not_before,
    }
    return max(scores, key=lambda route: (scores[route], route.value))


def evaluate(candidate: OpportunityCandidate) -> Evaluation:
    hard_failures = []
    reasons = []
    if not candidate.evidence_verified: hard_failures.append("UNVERIFIED_EVIDENCE")
    if not candidate.competitor_research.complete: hard_failures.append("COMPETITOR_RESEARCH_INCOMPLETE")
    if candidate.deceptive_tactics_required: hard_failures.append("DECEPTIVE_TACTICS_REQUIRED")
    if candidate.unverified_personal_claims_required: hard_failures.append("UNVERIFIED_PERSONAL_CLAIMS_REQUIRED")
    if candidate.legal_risk >= 4: hard_failures.append("LEGAL_RISK_TOO_HIGH")
    if candidate.ai_substitutability >= 4 and candidate.proprietary_edge < 3 and candidate.action_completion < 3: hard_failures.append("AI_SUBSTITUTABLE_WITHOUT_EDGE")
    if candidate.buyer_clarity <= 1 and candidate.purchase_intent <= 1: hard_failures.append("NO_CLEAR_PAYER_OR_PURCHASE_INTENT")
    if candidate.demand_life_days is not None:
        if candidate.build_days > candidate.demand_life_days * 0.40: hard_failures.append("BUILD_TOO_SLOW_FOR_DEMAND_LIFE")
        if not candidate.exit_trigger: hard_failures.append("MISSING_EXIT_TRIGGER")
    if len(candidate.future_steps) < 3: hard_failures.append("FUTURE_HORIZON_TOO_SHALLOW")
    if hard_failures:
        return Evaluation(Decision.REJECT, 0, choose_revenue_route(candidate), tuple(reasons), tuple(hard_failures))
    positive = sum((_weighted(candidate.buyer_clarity,9), _weighted(candidate.attention,8), _weighted(candidate.purchase_intent,10), _weighted(candidate.why_now,8), _weighted(candidate.why_not_before,5), _weighted(candidate.proprietary_edge,12), _weighted(candidate.action_completion,8), _weighted(candidate.reusable_asset,10), _weighted(candidate.distribution,10)))
    if candidate.expected_profit_low_yen > candidate.initial_cost_yen:
        positive += 10; reasons.append("LOW_CASE_PAYS_BACK_INITIAL_COST")
    elif candidate.expected_profit_base_yen > candidate.initial_cost_yen:
        positive += 5; reasons.append("BASE_CASE_PAYS_BACK_INITIAL_COST")
    else: reasons.append("PAYBACK_NOT_PROVEN")
    penalties = sum((_weighted(candidate.competitor_pressure,8), _weighted(candidate.incumbent_crush_risk,10), _weighted(candidate.ai_substitutability,8), _weighted(candidate.legal_risk,10), _weighted(candidate.human_burden,8)))
    if candidate.demand_life_days is not None:
        build_share = candidate.build_days / candidate.demand_life_days
        if build_share <= 0.10:
            positive += 5; reasons.append("FAST_ENOUGH_FOR_SHORT_LIVED_DEMAND")
        elif build_share > 0.25:
            penalties += 5; reasons.append("DEMAND_LIFE_MARGIN_IS_THIN")
    score = max(0, min(100, round(positive - penalties)))
    if candidate.expected_profit_low_yen > candidate.initial_cost_yen and score >= 72: decision = Decision.BUILD_CANDIDATE
    elif candidate.expected_profit_base_yen > candidate.initial_cost_yen and score >= 55: decision = Decision.MICRO_TEST
    else: decision = Decision.WATCH
    return Evaluation(decision, score, choose_revenue_route(candidate), tuple(reasons), ())
