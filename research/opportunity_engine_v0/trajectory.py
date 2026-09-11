from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .engine import Evaluation, evaluate
from .market_dynamics import MarketDynamics, MarketDynamicsAssessment, MarketPattern, assess_market_dynamics
from .model import Decision, OpportunityCandidate


class Trajectory(str, Enum):
    REJECT = "REJECT"
    WATCH = "WATCH"
    HARVEST_AND_EXIT = "HARVEST_AND_EXIT"
    TEST_FOR_DURABILITY = "TEST_FOR_DURABILITY"
    BUILD_DURABLE = "BUILD_DURABLE"


@dataclass(frozen=True)
class StrategicAssessment:
    core: Evaluation
    dynamics: MarketDynamicsAssessment
    trajectory: Trajectory
    reasons: tuple[str, ...]


def assess_strategy(candidate: OpportunityCandidate, dynamics: MarketDynamics) -> StrategicAssessment:
    core = evaluate(candidate)
    market = assess_market_dynamics(dynamics)
    reasons: list[str] = []

    if core.decision == Decision.REJECT:
        return StrategicAssessment(core, market, Trajectory.REJECT, ("core_rejected",))
    if not market.eligible:
        return StrategicAssessment(core, market, Trajectory.REJECT, ("market_dynamics_ineligible",))

    short_lived = candidate.demand_life_days is not None and candidate.demand_life_days <= 60
    fast_build = (
        candidate.demand_life_days is not None
        and candidate.build_days <= candidate.demand_life_days * 0.10
    )

    if market.immunity_pressure >= 4 and market.adaptation_score < 3:
        reasons.append("immunity_outpaces_adaptation")
        if short_lived and fast_build and core.decision in {Decision.MICRO_TEST, Decision.BUILD_CANDIDATE}:
            reasons.append("capture_before_decay")
            return StrategicAssessment(core, market, Trajectory.HARVEST_AND_EXIT, tuple(reasons))
        return StrategicAssessment(core, market, Trajectory.WATCH, tuple(reasons))

    if short_lived and fast_build and market.diffusion_score >= 3.5:
        reasons.append("short_window_fast_diffusion")
        return StrategicAssessment(core, market, Trajectory.HARVEST_AND_EXIT, tuple(reasons))

    if (
        market.pattern == MarketPattern.SYMBIOTIC
        and market.durable_value_score >= 4
        and market.adaptation_score >= 3
        and market.immunity_pressure < 4
        and core.decision in {Decision.MICRO_TEST, Decision.BUILD_CANDIDATE}
    ):
        reasons.append("durable_mutual_value_with_adaptation")
        return StrategicAssessment(core, market, Trajectory.BUILD_DURABLE, tuple(reasons))

    if core.decision in {Decision.MICRO_TEST, Decision.BUILD_CANDIDATE}:
        reasons.append("economics_pass_but_durability_unproven")
        return StrategicAssessment(core, market, Trajectory.TEST_FOR_DURABILITY, tuple(reasons))

    reasons.append("insufficient_economic_signal")
    return StrategicAssessment(core, market, Trajectory.WATCH, tuple(reasons))
