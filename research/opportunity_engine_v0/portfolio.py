from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from .engine import Evaluation, evaluate
from .model import Decision, OpportunityCandidate


@dataclass(frozen=True)
class RankedOpportunity:
    candidate: OpportunityCandidate
    evaluation: Evaluation
    allocation: str


_DECISION_PRIORITY = {
    Decision.BUILD_CANDIDATE: 3,
    Decision.MICRO_TEST: 2,
    Decision.WATCH: 1,
    Decision.REJECT: 0,
}


def rank_portfolio(candidates: Iterable[OpportunityCandidate]) -> Tuple[RankedOpportunity, ...]:
    evaluated = [(candidate, evaluate(candidate)) for candidate in candidates]
    evaluated.sort(
        key=lambda pair: (
            _DECISION_PRIORITY[pair[1].decision],
            pair[1].score,
            pair[0].expected_profit_low_yen,
            pair[0].expected_profit_base_yen,
        ),
        reverse=True,
    )

    focus_assigned = False
    ranked = []
    for candidate, result in evaluated:
        if result.decision == Decision.REJECT:
            allocation = "REJECT"
        elif not focus_assigned and result.decision in (Decision.BUILD_CANDIDATE, Decision.MICRO_TEST):
            allocation = "FOCUS"
            focus_assigned = True
        elif result.decision in (Decision.BUILD_CANDIDATE, Decision.MICRO_TEST):
            allocation = "HOLD_AFTER_RESEARCH"
        else:
            allocation = "WATCH"
        ranked.append(RankedOpportunity(candidate, result, allocation))

    return tuple(ranked)
