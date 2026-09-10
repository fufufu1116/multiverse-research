from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import combinations
from typing import Tuple

from .leverage import LeverageOption, LeverageScan, conservative_combined_multiplier, score_leverage


class LoadoutDecision(str, Enum):
    SEARCH_INCOMPLETE = "SEARCH_INCOMPLETE"
    NO_FEASIBLE_LOADOUT = "NO_FEASIBLE_LOADOUT"
    LOADOUT_READY = "LOADOUT_READY"


@dataclass(frozen=True)
class PairInteraction:
    left: str
    right: str
    synergy: int = 0
    overlap: int = 0

    def __post_init__(self) -> None:
        if not self.left.strip() or not self.right.strip() or self.left == self.right:
            raise ValueError("interaction requires two distinct option names")
        for name in ("synergy", "overlap"):
            if not 0 <= getattr(self, name) <= 5:
                raise ValueError(f"{name} must be between 0 and 5")

    @property
    def key(self) -> frozenset[str]:
        return frozenset((self.left, self.right))


@dataclass(frozen=True)
class LoadoutPolicy:
    max_setup_cost_yen: int
    max_setup_days: float
    max_recurring_cost_yen_month: int
    max_owner_hours_month: float
    max_options: int = 3
    min_option_score: int = 25

    def __post_init__(self) -> None:
        for name in (
            "max_setup_cost_yen",
            "max_setup_days",
            "max_recurring_cost_yen_month",
            "max_owner_hours_month",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if not 1 <= self.max_options <= 5:
            raise ValueError("max_options must be between 1 and 5")
        if not 0 <= self.min_option_score <= 100:
            raise ValueError("min_option_score must be between 0 and 100")


@dataclass(frozen=True)
class LoadoutAssessment:
    decision: LoadoutDecision
    selected: Tuple[LeverageOption, ...]
    score: int
    conservative_multiplier: float
    setup_cost_yen: int
    setup_days: float
    recurring_cost_yen_month: int
    owner_hours_month: float
    reasons: Tuple[str, ...]


def _interaction_score(
    options: Tuple[LeverageOption, ...], interactions: Tuple[PairInteraction, ...]
) -> tuple[int, int]:
    by_key = {item.key: item for item in interactions}
    synergy = 0
    overlap = 0
    for left, right in combinations(options, 2):
        relation = by_key.get(frozenset((left.name, right.name)))
        if relation:
            synergy += relation.synergy
            overlap += relation.overlap
    return synergy, overlap


def _feasible(options: Tuple[LeverageOption, ...], policy: LoadoutPolicy) -> bool:
    return (
        sum(item.setup_cost_yen for item in options) <= policy.max_setup_cost_yen
        and sum(item.setup_days for item in options) <= policy.max_setup_days
        and sum(item.recurring_cost_yen_month for item in options)
        <= policy.max_recurring_cost_yen_month
        and sum(item.owner_hours_month for item in options) <= policy.max_owner_hours_month
    )


def optimize_loadout(
    scan: LeverageScan,
    policy: LoadoutPolicy,
    interactions: Tuple[PairInteraction, ...] = (),
) -> LoadoutAssessment:
    """Choose a bounded combination, not merely the strongest-looking single lever.

    The optimizer only uses individually safe leverage options. It rewards
    complementary mechanisms and category diversity, penalizes overlap and
    needless complexity, and respects owner time/cash limits. Claimed output
    multipliers remain conservatively stacked by the underlying leverage layer.
    """
    if not scan.complete:
        return LoadoutAssessment(
            LoadoutDecision.SEARCH_INCOMPLETE, (), 0, 1.0, 0, 0.0, 0, 0.0,
            ("LEVERAGE_SEARCH_INCOMPLETE",),
        )

    safe: list[tuple[LeverageOption, int]] = []
    for item in scan.options:
        item_score, _ = score_leverage(item)
        if item_score is not None and item_score >= policy.min_option_score:
            safe.append((item, item_score))

    candidates: list[tuple[tuple, Tuple[LeverageOption, ...], int, Tuple[str, ...]]] = []
    max_size = min(policy.max_options, len(safe))
    score_by_name = {item.name: score for item, score in safe}

    for size in range(1, max_size + 1):
        for combo in combinations((item for item, _ in safe), size):
            combo = tuple(combo)
            if not _feasible(combo, policy):
                continue
            synergy, overlap = _interaction_score(combo, interactions)
            unique_kinds = len({item.kind for item in combo})
            base = sum(score_by_name[item.name] for item in combo) / len(combo)
            diversity_bonus = min(8, max(0, unique_kinds - 1) * 3)
            interaction_adjustment = synergy * 4 - overlap * 5
            complexity_penalty = max(0, len(combo) - 1) * 2
            multiplier = conservative_combined_multiplier(combo)
            multiplier_bonus = min(10, max(0.0, multiplier - 1.0) * 3)
            total = round(max(0, min(100, base + diversity_bonus + interaction_adjustment - complexity_penalty + multiplier_bonus)))
            reasons = []
            if unique_kinds >= 2:
                reasons.append("DIVERSE_LEVERAGE_STACK")
            if synergy > 0:
                reasons.append("VERIFIED_COMPLEMENTARITY")
            if overlap > 0:
                reasons.append("OVERLAP_DISCOUNTED")
            if all(item.existing_system_share >= 0.80 for item in combo):
                reasons.append("EXISTING_SYSTEM_FIRST")
            if sum(item.owner_hours_month for item in combo) <= max(1.0, policy.max_owner_hours_month * 0.25):
                reasons.append("LOW_OWNER_BURDEN")

            tie_break = (
                total,
                multiplier,
                -sum(item.owner_hours_month for item in combo),
                -sum(item.recurring_cost_yen_month for item in combo),
                -sum(item.setup_cost_yen for item in combo),
                tuple(sorted(item.name for item in combo)),
            )
            candidates.append((tie_break, combo, total, tuple(reasons)))

    if not candidates:
        return LoadoutAssessment(
            LoadoutDecision.NO_FEASIBLE_LOADOUT, (), 0, 1.0, 0, 0.0, 0, 0.0,
            ("NO_SAFE_STACK_WITHIN_BUDGET",),
        )

    _, selected, score, reasons = max(candidates, key=lambda row: row[0])
    return LoadoutAssessment(
        decision=LoadoutDecision.LOADOUT_READY,
        selected=selected,
        score=score,
        conservative_multiplier=conservative_combined_multiplier(selected),
        setup_cost_yen=sum(item.setup_cost_yen for item in selected),
        setup_days=sum(item.setup_days for item in selected),
        recurring_cost_yen_month=sum(item.recurring_cost_yen_month for item in selected),
        owner_hours_month=sum(item.owner_hours_month for item in selected),
        reasons=reasons,
    )


class Capability(str, Enum):
    EVIDENCE = "EVIDENCE"
    DISTRIBUTION = "DISTRIBUTION"
    AUTOMATION = "AUTOMATION"
    MONETIZATION = "MONETIZATION"
    DATA = "DATA"
    REUSE = "REUSE"
    FORECASTING = "FORECASTING"


@dataclass(frozen=True)
class CapabilityProfile:
    evidence: int
    distribution: int
    automation: int
    monetization: int
    data: int
    reuse: int
    forecasting: int

    def __post_init__(self) -> None:
        for name in (
            "evidence", "distribution", "automation", "monetization",
            "data", "reuse", "forecasting",
        ):
            if not 0 <= getattr(self, name) <= 5:
                raise ValueError(f"{name} must be between 0 and 5")

    def level(self, capability: Capability) -> int:
        return getattr(self, capability.value.lower())


@dataclass(frozen=True)
class TrainingAction:
    name: str
    target: Capability
    verified_method: bool
    measurable_outcome: bool
    expected_gain: int
    reusable_learning: int
    setup_cost_yen: int
    setup_days: float
    owner_hours: float
    legal_risk: int
    exposes_core: bool = False
    requires_team: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name is required")
        for name in ("expected_gain", "reusable_learning", "legal_risk"):
            if not 0 <= getattr(self, name) <= 5:
                raise ValueError(f"{name} must be between 0 and 5")
        for name in ("setup_cost_yen", "setup_days", "owner_hours"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True)
class TrainingPlan:
    actions: Tuple[TrainingAction, ...]
    reasons: Tuple[str, ...]


def choose_training_plan(
    profile: CapabilityProfile,
    actions: Tuple[TrainingAction, ...],
    *,
    max_actions: int = 3,
    max_cost_yen: int = 5000,
    max_owner_hours: float = 5.0,
) -> TrainingPlan:
    """Prioritize measurable experiments that strengthen the weakest capabilities."""
    if not 1 <= max_actions <= 5:
        raise ValueError("max_actions must be between 1 and 5")

    ranked = []
    for action in actions:
        if (
            not action.verified_method
            or not action.measurable_outcome
            or action.legal_risk >= 4
            or action.exposes_core
            or action.requires_team
        ):
            continue
        weakness = 5 - profile.level(action.target)
        score = (
            weakness * 7
            + action.expected_gain * 5
            + action.reusable_learning * 5
            - min(action.setup_cost_yen / 1000.0, 10) * 2
            - action.setup_days * 2
            - action.owner_hours * 3
        )
        ranked.append((score, action))

    ranked.sort(key=lambda row: (row[0], row[1].name), reverse=True)
    selected = []
    cost = 0
    hours = 0.0
    used_targets = set()
    for _, action in ranked:
        if len(selected) >= max_actions:
            break
        if cost + action.setup_cost_yen > max_cost_yen or hours + action.owner_hours > max_owner_hours:
            continue
        if action.target in used_targets and any(
            other.target not in used_targets
            and cost + other.setup_cost_yen <= max_cost_yen
            and hours + other.owner_hours <= max_owner_hours
            for _, other in ranked
            if other not in selected
        ):
            continue
        selected.append(action)
        used_targets.add(action.target)
        cost += action.setup_cost_yen
        hours += action.owner_hours

    reasons = []
    if selected:
        reasons.append("WEAKEST_LINKS_FIRST")
    if any(action.reusable_learning >= 4 for action in selected):
        reasons.append("COMPOUNDING_LEARNING")
    if all(action.measurable_outcome for action in selected):
        reasons.append("MEASURABLE_TRAINING")
    return TrainingPlan(tuple(selected), tuple(reasons))
