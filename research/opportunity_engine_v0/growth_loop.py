from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class LoopDecision(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    UNSAFE_OR_POLICY_FRAGILE = "UNSAFE_OR_POLICY_FRAGILE"
    ONE_WAY_AMPLIFIER = "ONE_WAY_AMPLIFIER"
    FRAGILE_LOOP = "FRAGILE_LOOP"
    LOOP_READY = "LOOP_READY"


@dataclass(frozen=True)
class GrowthChannel:
    name: str
    owned: bool
    platform_dependency_risk: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("channel name is required")
        if not 0 <= self.platform_dependency_risk <= 5:
            raise ValueError("platform_dependency_risk must be between 0 and 5")


@dataclass(frozen=True)
class LoopEdge:
    source: str
    destination: str
    mechanism: str
    verified_available: bool
    evidence_count: int
    user_value: int
    friction: int
    intent_strength: int
    attribution_quality: int
    reusable_asset_gain: int
    platform_policy_risk: int
    legal_risk: int
    deceptive_tactic_required: bool = False

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.destination.strip() or self.source == self.destination:
            raise ValueError("edge requires two distinct channels")
        if not self.mechanism.strip():
            raise ValueError("mechanism is required")
        if not isinstance(self.evidence_count, int) or self.evidence_count < 0:
            raise ValueError("evidence_count must be non-negative")
        for name in (
            "user_value",
            "friction",
            "intent_strength",
            "attribution_quality",
            "reusable_asset_gain",
            "platform_policy_risk",
            "legal_risk",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 5:
                raise ValueError(f"{name} must be an integer from 0 to 5")


@dataclass(frozen=True)
class GrowthLoopAssessment:
    decision: LoopDecision
    score: int
    closed_pairs: Tuple[Tuple[str, str], ...]
    reasons: Tuple[str, ...]
    blockers: Tuple[str, ...]
    estimated_loop_multiplier: float


def _edge_score(edge: LoopEdge) -> float:
    positive = (
        edge.user_value * 7
        + edge.intent_strength * 6
        + edge.attribution_quality * 4
        + edge.reusable_asset_gain * 4
        + min(edge.evidence_count, 3) * 2
    )
    negative = (
        edge.friction * 6
        + edge.platform_policy_risk * 5
        + edge.legal_risk * 7
    )
    return max(0.0, min(100.0, positive - negative))


def assess_growth_loop(
    *,
    channels: Tuple[GrowthChannel, ...],
    edges: Tuple[LoopEdge, ...],
) -> GrowthLoopAssessment:
    """Assess whether distribution can form a user-benefiting bidirectional loop.

    A loop is stronger than a one-way funnel only when users have a real reason to
    travel in both directions. Platform traffic is useful, but the engine rewards
    an owned capture point so that the whole system does not disappear when one
    platform changes API, ranking, policy or economics.
    """
    if len(channels) < 2:
        raise ValueError("at least two channels are required")
    names = [channel.name for channel in channels]
    if len(set(names)) != len(names):
        raise ValueError("channel names must be unique")
    name_set = set(names)
    if not edges:
        return GrowthLoopAssessment(
            LoopDecision.UNVERIFIED, 0, (), (), ("NO_LOOP_EDGES",), 1.0
        )

    blockers = []
    verified_edges = []
    for edge in edges:
        if edge.source not in name_set or edge.destination not in name_set:
            raise ValueError("edge references an unknown channel")
        if not edge.verified_available or edge.evidence_count < 1:
            blockers.append("UNVERIFIED_EDGE")
            continue
        if edge.deceptive_tactic_required:
            blockers.append("DECEPTIVE_TACTIC_REQUIRED")
            continue
        if edge.legal_risk >= 4:
            blockers.append("LEGAL_RISK_TOO_HIGH")
            continue
        if edge.platform_policy_risk >= 5:
            blockers.append("PLATFORM_POLICY_RISK_TOO_HIGH")
            continue
        verified_edges.append(edge)

    if not verified_edges:
        decision = (
            LoopDecision.UNSAFE_OR_POLICY_FRAGILE
            if blockers
            else LoopDecision.UNVERIFIED
        )
        return GrowthLoopAssessment(
            decision, 0, (), (), tuple(sorted(set(blockers))), 1.0
        )

    direction_set = {(edge.source, edge.destination) for edge in verified_edges}
    closed_pairs = sorted(
        {
            tuple(sorted((left, right)))
            for left, right in direction_set
            if (right, left) in direction_set
        }
    )

    average_edge_score = sum(_edge_score(edge) for edge in verified_edges) / len(verified_edges)
    owned_capture = any(channel.owned for channel in channels)
    max_dependency = max(channel.platform_dependency_risk for channel in channels)
    low_friction_both_ways = False
    meaningful_value_both_ways = False
    for left, right in closed_pairs:
        pair_edges = [
            edge
            for edge in verified_edges
            if {edge.source, edge.destination} == {left, right}
        ]
        if len(pair_edges) >= 2:
            low_friction_both_ways = all(edge.friction <= 2 for edge in pair_edges)
            meaningful_value_both_ways = all(edge.user_value >= 3 for edge in pair_edges)
            if low_friction_both_ways and meaningful_value_both_ways:
                break

    reasons = []
    score = average_edge_score
    if closed_pairs:
        score += 12
        reasons.append("BIDIRECTIONAL_USER_FLOW")
    if owned_capture:
        score += 10
        reasons.append("OWNED_CAPTURE_POINT")
    else:
        score -= 12
        reasons.append("NO_OWNED_CAPTURE_POINT")
    if low_friction_both_ways:
        score += 7
        reasons.append("LOW_FRICTION_RETURN_PATH")
    if meaningful_value_both_ways:
        score += 7
        reasons.append("USER_VALUE_BOTH_DIRECTIONS")
    if any(edge.attribution_quality >= 4 for edge in verified_edges):
        score += 4
        reasons.append("MEASURABLE_ATTRIBUTION")
    if any(edge.reusable_asset_gain >= 4 for edge in verified_edges):
        score += 4
        reasons.append("COMPOUNDING_ASSET")
    score -= max_dependency * 3
    score = round(max(0.0, min(100.0, score)))

    if blockers and any(item in blockers for item in ("DECEPTIVE_TACTIC_REQUIRED", "LEGAL_RISK_TOO_HIGH")):
        decision = LoopDecision.UNSAFE_OR_POLICY_FRAGILE
    elif not closed_pairs:
        decision = LoopDecision.ONE_WAY_AMPLIFIER
    elif max_dependency >= 4 or not owned_capture or not meaningful_value_both_ways:
        decision = LoopDecision.FRAGILE_LOOP
    elif score >= 55:
        decision = LoopDecision.LOOP_READY
    else:
        decision = LoopDecision.FRAGILE_LOOP

    # Conservative: treat loop value as bounded uplift, not viral certainty.
    multiplier = round(1.0 + min(0.8, score / 100.0 * 0.8), 2)

    return GrowthLoopAssessment(
        decision=decision,
        score=score,
        closed_pairs=tuple(closed_pairs),
        reasons=tuple(reasons),
        blockers=tuple(sorted(set(blockers))),
        estimated_loop_multiplier=multiplier,
    )
