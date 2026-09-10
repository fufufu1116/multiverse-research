from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class TacticStage(str, Enum):
    VALIDATE = "VALIDATE"
    PROVE_CONVERSION = "PROVE_CONVERSION"
    AUTOMATE = "AUTOMATE"
    ACQUIRE = "ACQUIRE"
    SCALE = "SCALE"
    EXIT_AND_LEARN = "EXIT_AND_LEARN"


class TacticDecision(str, Enum):
    REJECT = "REJECT"
    READY = "READY"


@dataclass(frozen=True)
class TacticStep:
    name: str
    stage: TacticStage
    verified_method: bool
    measurable: bool
    reversible: bool
    spend_yen: int
    owner_hours: float
    learning_value: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name is required")
        if self.spend_yen < 0 or self.owner_hours < 0:
            raise ValueError("spend_yen and owner_hours must be non-negative")
        if not 0 <= self.learning_value <= 5:
            raise ValueError("learning_value must be between 0 and 5")


@dataclass(frozen=True)
class TacticPolicy:
    max_preproof_spend_yen: int
    max_total_owner_hours: float
    demand_life_days: Optional[float] = None
    total_setup_days: Optional[float] = None

    def __post_init__(self) -> None:
        if self.max_preproof_spend_yen < 0 or self.max_total_owner_hours < 0:
            raise ValueError("policy limits must be non-negative")
        if self.demand_life_days is not None and self.demand_life_days <= 0:
            raise ValueError("demand_life_days must be positive when supplied")
        if self.total_setup_days is not None and self.total_setup_days < 0:
            raise ValueError("total_setup_days must be non-negative")


@dataclass(frozen=True)
class TacticAssessment:
    decision: TacticDecision
    score: int
    reasons: Tuple[str, ...]
    hard_failures: Tuple[str, ...]


def assess_tactic_plan(
    steps: Tuple[TacticStep, ...],
    policy: TacticPolicy,
) -> TacticAssessment:
    failures = []
    reasons = []

    if not 3 <= len(steps) <= 7:
        failures.append("TACTIC_HORIZON_MUST_BE_3_TO_7_STEPS")
    if not steps:
        return TacticAssessment(TacticDecision.REJECT, 0, (), tuple(failures))
    if steps[0].stage is not TacticStage.VALIDATE:
        failures.append("VALIDATION_MUST_BE_FIRST")
    if steps[-1].stage is not TacticStage.EXIT_AND_LEARN:
        failures.append("EXIT_AND_LEARNING_MUST_BE_LAST")
    if any(not step.verified_method for step in steps):
        failures.append("UNVERIFIED_TACTIC_METHOD")
    if any(not step.measurable for step in steps):
        failures.append("UNMEASURABLE_TACTIC_STEP")
    if any(not step.reversible for step in steps[:-1]):
        failures.append("IRREVERSIBLE_STEP_BEFORE_EXIT")

    stages = [step.stage for step in steps]
    conversion_index = next(
        (index for index, stage in enumerate(stages) if stage is TacticStage.PROVE_CONVERSION),
        None,
    )
    scale_index = next(
        (index for index, stage in enumerate(stages) if stage is TacticStage.SCALE),
        None,
    )
    automation_index = next(
        (index for index, stage in enumerate(stages) if stage is TacticStage.AUTOMATE),
        None,
    )

    if scale_index is not None and (conversion_index is None or scale_index < conversion_index):
        failures.append("SCALE_BEFORE_CONVERSION_PROOF")
    if automation_index is not None and (conversion_index is None or automation_index < conversion_index):
        failures.append("AUTOMATION_BEFORE_VALUE_PROOF")

    if conversion_index is None:
        preproof_spend = sum(step.spend_yen for step in steps)
    else:
        preproof_spend = sum(step.spend_yen for step in steps[: conversion_index + 1])
    if preproof_spend > policy.max_preproof_spend_yen:
        failures.append("PREPROOF_SPEND_TOO_HIGH")

    owner_hours = sum(step.owner_hours for step in steps)
    if owner_hours > policy.max_total_owner_hours:
        failures.append("OWNER_TIME_BUDGET_EXCEEDED")

    if (
        policy.demand_life_days is not None
        and policy.total_setup_days is not None
        and policy.total_setup_days > policy.demand_life_days * 0.40
    ):
        failures.append("TACTIC_TOO_SLOW_FOR_DEMAND_WINDOW")

    if failures:
        return TacticAssessment(
            decision=TacticDecision.REJECT,
            score=0,
            reasons=(),
            hard_failures=tuple(sorted(set(failures))),
        )

    if conversion_index is not None:
        reasons.append("CONVERSION_PROVEN_BEFORE_SCALE")
    if automation_index is not None and conversion_index is not None and automation_index > conversion_index:
        reasons.append("AUTOMATE_AFTER_VALUE_PROOF")
    if preproof_spend <= max(1000, policy.max_preproof_spend_yen * 0.25):
        reasons.append("CHEAP_BEFORE_PROOF")
    if sum(step.learning_value for step in steps) / len(steps) >= 3.5:
        reasons.append("HIGH_LEARNING_VALUE")

    coverage = len(set(stages))
    learning = sum(step.learning_value for step in steps) / len(steps)
    reversibility = sum(1 for step in steps if step.reversible) / len(steps)
    proof_bonus = 15 if conversion_index is not None else 0
    scale_bonus = 5 if scale_index is not None else 0
    cost_penalty = min(20.0, preproof_spend / max(1, policy.max_preproof_spend_yen) * 10)
    time_penalty = min(15.0, owner_hours / max(1.0, policy.max_total_owner_hours) * 10)
    score = round(
        max(
            0,
            min(
                100,
                coverage * 8 + learning * 8 + reversibility * 10 + proof_bonus + scale_bonus - cost_penalty - time_penalty,
            ),
        )
    )
    return TacticAssessment(TacticDecision.READY, score, tuple(reasons), ())
