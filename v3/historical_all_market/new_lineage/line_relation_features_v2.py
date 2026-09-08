from __future__ import annotations

"""Hardened deterministic PRE-only line relation feature encoder for C1/N1.

v2 preserves the v1 feature definitions but adds an explicit input firewall:
fresh RESULT/PAYOUT/ODDS/PREDICTION/HUMAN-COMMENT fields must never be silently
ignored by this PRE-only layer. Suspicious field names fail closed before line
topology is admitted.
"""

from typing import Any, Iterable, Mapping
import re

from line_relation_features_v1 import (
    LineRelationError,
    RunnerLineState,
    own_line_features,
    pair_line_features,
    rank3_context_features,
)
import line_relation_features_v1 as v1


_FORBIDDEN_ASCII_TOKENS = {
    "result", "results", "outcome", "outcomes",
    "payout", "payouts", "payoff", "payoffs", "dividend", "dividends",
    "odds",
    "prediction", "predictions", "forecast", "forecasts",
    "comment", "comments",
    "finish", "finishing",
}
_FORBIDDEN_JP_FRAGMENTS = (
    "結果", "払戻", "オッズ", "予想", "コメント", "着順",
)


def _field_name_tokens(name: Any) -> tuple[str, set[str]]:
    raw = str(name)
    lowered = raw.lower()
    tokens = {x for x in re.split(r"[^a-z0-9]+", lowered) if x}
    return lowered, tokens


def assert_pre_only_input_rows(rows: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Materialize rows and reject forbidden post-decision namespaces by key.

    Values are deliberately not scanned: a rider/source name may legitimately
    contain ordinary text. The firewall is about the schema presented to this
    PRE-only feature layer.
    """
    materialized = list(rows)
    for row_index, row in enumerate(materialized):
        if not isinstance(row, Mapping):
            raise LineRelationError(f"row_must_be_mapping:{row_index}")
        for key in row.keys():
            lowered, tokens = _field_name_tokens(key)
            if tokens & _FORBIDDEN_ASCII_TOKENS:
                bad = sorted(tokens & _FORBIDDEN_ASCII_TOKENS)[0]
                raise LineRelationError(
                    f"forbidden_post_decision_field:{row_index}:{key}:{bad}"
                )
            if any(fragment in str(key) for fragment in _FORBIDDEN_JP_FRAGMENTS):
                raise LineRelationError(
                    f"forbidden_post_decision_field:{row_index}:{key}"
                )
    return materialized


def validate_line_states(rows: Iterable[Mapping[str, Any]]) -> dict[int, RunnerLineState]:
    materialized = assert_pre_only_input_rows(rows)
    states = v1.validate_line_states(materialized)
    # Keirin car numbers are bounded to the admitted race-card domain here.
    if any(car > 9 for car in states):
        raise LineRelationError("car_no_exceeds_keirin_domain")
    return states


def encode_race_line_relations(
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    states = validate_line_states(rows)
    cars = tuple(sorted(states))
    own = {car: own_line_features(states, car) for car in cars}
    pairs = {
        (candidate, context): pair_line_features(states, candidate, context)
        for candidate in cars
        for context in cars
        if candidate != context
    }
    return {
        "cars": cars,
        "own": own,
        "pairs": pairs,
        "input_firewall": "PRE_ONLY_FORBIDDEN_POST_DECISION_FIELD_NAMES_FAIL_CLOSED",
        "result_fields_included": False,
        "payout_fields_included": False,
        "odds_fields_included": False,
        "prediction_fields_included": False,
        "human_comment_fields_included": False,
        "post_race_reconstruction_used": False,
    }
