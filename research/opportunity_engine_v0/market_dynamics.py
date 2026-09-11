from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MarketPattern(str, Enum):
    ACUTE = "ACUTE"
    SEASONAL = "SEASONAL"
    LATENT = "LATENT"
    CHRONIC = "CHRONIC"
    SYMBIOTIC = "SYMBIOTIC"


@dataclass(frozen=True)
class MarketDynamics:
    """Research-only market diffusion model.

    The biological vocabulary is deliberately metaphorical. It is used to
    reason about diffusion, habituation, substitution, recurrence and durable
    mutual value; it is not a claim that customers are literal hosts or that
    harmful dependence is desirable.
    """

    transmission: int
    host_fit: int
    habituation_immunity: int
    ai_substitution_immunity: int
    incumbent_immunity: int
    mutation_capacity: int
    recurrence: int
    network_effect: int
    embeddedness: int
    mutual_value: int
    latency_days: float = 0.0
    event_triggered: bool = False
    deceptive_retention_required: bool = False
    harmful_dependence_risk: int = 0

    def __post_init__(self) -> None:
        score_fields = (
            "transmission",
            "host_fit",
            "habituation_immunity",
            "ai_substitution_immunity",
            "incumbent_immunity",
            "mutation_capacity",
            "recurrence",
            "network_effect",
            "embeddedness",
            "mutual_value",
            "harmful_dependence_risk",
        )
        for field_name in score_fields:
            value = getattr(self, field_name)
            if not 0 <= value <= 5:
                raise ValueError(f"{field_name} must be between 0 and 5")
        if self.latency_days < 0:
            raise ValueError("latency_days must be non-negative")


@dataclass(frozen=True)
class MarketDynamicsAssessment:
    pattern: MarketPattern
    diffusion_score: float
    immunity_pressure: float
    adaptation_score: float
    durable_value_score: float
    eligible: bool
    reasons: tuple[str, ...]


def assess_market_dynamics(dynamics: MarketDynamics) -> MarketDynamicsAssessment:
    """Assess how a market may spread, fade, recur or become durable.

    High 'immunity' means the opportunity is easier to neutralize through
    habituation, general AI substitution or incumbent commoditization.
    Harmful dependence and deceptive retention fail closed.
    """

    immunity_pressure = round(
        (
            dynamics.habituation_immunity
            + dynamics.ai_substitution_immunity
            + dynamics.incumbent_immunity
        )
        / 3,
        2,
    )
    diffusion_score = round(
        (
            0.45 * dynamics.transmission
            + 0.25 * dynamics.host_fit
            + 0.20 * dynamics.network_effect
            + 0.10 * dynamics.recurrence
        ),
        2,
    )
    adaptation_score = round(
        (
            0.45 * dynamics.mutation_capacity
            + 0.30 * dynamics.recurrence
            + 0.25 * dynamics.host_fit
        ),
        2,
    )
    durable_value_score = round(
        (
            0.45 * dynamics.mutual_value
            + 0.35 * dynamics.embeddedness
            + 0.20 * dynamics.recurrence
        ),
        2,
    )

    reasons: list[str] = []
    eligible = True
    if dynamics.deceptive_retention_required:
        eligible = False
        reasons.append("deceptive_retention_required")
    if dynamics.harmful_dependence_risk >= 4:
        eligible = False
        reasons.append("harmful_dependence_risk_high")

    if dynamics.mutual_value >= 4 and dynamics.embeddedness >= 4 and dynamics.recurrence >= 3:
        pattern = MarketPattern.SYMBIOTIC
    elif dynamics.embeddedness >= 4:
        pattern = MarketPattern.CHRONIC
    elif dynamics.recurrence >= 4:
        pattern = MarketPattern.SEASONAL
    elif dynamics.event_triggered and dynamics.latency_days >= 7:
        pattern = MarketPattern.LATENT
    else:
        pattern = MarketPattern.ACUTE

    if immunity_pressure >= 4:
        reasons.append("high_immunity_pressure")
    if adaptation_score >= 4:
        reasons.append("strong_adaptation_capacity")
    if durable_value_score >= 4:
        reasons.append("strong_durable_mutual_value")
    if diffusion_score >= 4:
        reasons.append("strong_diffusion")

    return MarketDynamicsAssessment(
        pattern=pattern,
        diffusion_score=diffusion_score,
        immunity_pressure=immunity_pressure,
        adaptation_score=adaptation_score,
        durable_value_score=durable_value_score,
        eligible=eligible,
        reasons=tuple(reasons),
    )
