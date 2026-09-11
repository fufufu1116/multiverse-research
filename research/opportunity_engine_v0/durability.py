from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class DemandDurability(str, Enum):
    EPHEMERAL = "EPHEMERAL"
    CYCLICAL = "CYCLICAL"
    DURABLE = "DURABLE"
    FOUNDATIONAL = "FOUNDATIONAL"


class WaveStage(str, Enum):
    SPECULATIVE = "SPECULATIVE"
    EMERGING = "EMERGING"
    ACCELERATING = "ACCELERATING"
    MATURE = "MATURE"


@dataclass(frozen=True)
class DurabilityWaveProfile:
    # How persistent is the underlying human need independent of a particular product/channel?
    demand_persistence: int
    cross_culture_persistence: int
    recurring_frequency: int
    interface_independence: int

    # How strongly can a new technology/platform lower cost, reduce friction, or unlock new delivery?
    wave_leverage: int
    wave_evidence_strength: int
    independent_adoption_signals: int
    ecosystem_openness: int

    # Risks that can make a durable need unattractive to this owner even when demand itself persists.
    incumbent_capture_risk: int
    regulation_volatility: int
    human_burden: int

    # Concrete non-hype explanation of the old need and new enabling shift.
    enduring_need: str
    enabling_wave: str
    why_wave_changes_economics: str
    historical_analogs: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "demand_persistence",
            "cross_culture_persistence",
            "recurring_frequency",
            "interface_independence",
            "wave_leverage",
            "wave_evidence_strength",
            "ecosystem_openness",
            "incumbent_capture_risk",
            "regulation_volatility",
            "human_burden",
        ):
            value = getattr(self, field_name)
            if not 0 <= value <= 5:
                raise ValueError(f"{field_name} must be between 0 and 5")
        if self.independent_adoption_signals < 0:
            raise ValueError("independent_adoption_signals must be non-negative")
        if not self.enduring_need.strip():
            raise ValueError("enduring_need is required")
        if not self.enabling_wave.strip():
            raise ValueError("enabling_wave is required")
        if not self.why_wave_changes_economics.strip():
            raise ValueError("why_wave_changes_economics is required")


@dataclass(frozen=True)
class DurabilityWaveEvaluation:
    durability: DemandDurability
    wave_stage: WaveStage
    intersection_score: int
    reasons: Tuple[str, ...]
    blockers: Tuple[str, ...]


def _avg(*values: int) -> float:
    return sum(values) / len(values)


def evaluate_durability_wave(profile: DurabilityWaveProfile) -> DurabilityWaveEvaluation:
    reasons = []
    blockers = []

    durability_raw = _avg(
        profile.demand_persistence,
        profile.cross_culture_persistence,
        profile.recurring_frequency,
        profile.interface_independence,
    )
    if durability_raw >= 4.25:
        durability = DemandDurability.FOUNDATIONAL
        reasons.append("UNDERLYING_NEED_IS_FOUNDATIONAL")
    elif durability_raw >= 3.25:
        durability = DemandDurability.DURABLE
        reasons.append("UNDERLYING_NEED_IS_DURABLE")
    elif durability_raw >= 2.0:
        durability = DemandDurability.CYCLICAL
    else:
        durability = DemandDurability.EPHEMERAL

    # Do not call a technology wave real from hype alone. At least two independent adoption
    # signals are required before it can rise above SPECULATIVE.
    if profile.independent_adoption_signals < 2 or profile.wave_evidence_strength <= 1:
        wave_stage = WaveStage.SPECULATIVE
        blockers.append("WAVE_EVIDENCE_TOO_THIN")
    elif profile.wave_evidence_strength >= 4 and profile.independent_adoption_signals >= 4:
        wave_stage = WaveStage.ACCELERATING
        reasons.append("MULTIPLE_STRONG_ADOPTION_SIGNALS")
    elif profile.wave_evidence_strength >= 2:
        wave_stage = WaveStage.EMERGING
        reasons.append("WAVE_HAS_INDEPENDENT_ADOPTION_EVIDENCE")
    else:
        wave_stage = WaveStage.SPECULATIVE

    if profile.interface_independence >= 4:
        reasons.append("NEED_SURVIVES_CHANNEL_CHANGE")
    if profile.wave_leverage >= 4:
        reasons.append("NEW_WAVE_CAN_MATERIALLY_CHANGE_DELIVERY_ECONOMICS")
    if profile.ecosystem_openness >= 4:
        reasons.append("OPEN_ECOSYSTEM_CAN_BE_LEVERAGED")

    if profile.regulation_volatility >= 4:
        blockers.append("REGULATION_VOLATILITY_HIGH")
    if profile.human_burden >= 4:
        blockers.append("DIRECT_OPERATION_HUMAN_BURDEN_HIGH")
    if profile.incumbent_capture_risk >= 4:
        blockers.append("INCUMBENT_CAPTURE_RISK_HIGH")

    # Reward a persistent need meeting a verified enabling wave, but keep operational
    # constraints explicit. A centuries-old market is not automatically a good opportunity.
    positive = (
        durability_raw * 11
        + profile.wave_leverage * 6
        + profile.wave_evidence_strength * 5
        + profile.ecosystem_openness * 4
    )
    penalty = (
        profile.incumbent_capture_risk * 5
        + profile.regulation_volatility * 5
        + profile.human_burden * 5
    )
    if wave_stage == WaveStage.SPECULATIVE:
        penalty += 15

    intersection_score = max(0, min(100, round(positive - penalty)))
    return DurabilityWaveEvaluation(
        durability=durability,
        wave_stage=wave_stage,
        intersection_score=intersection_score,
        reasons=tuple(reasons),
        blockers=tuple(blockers),
    )
